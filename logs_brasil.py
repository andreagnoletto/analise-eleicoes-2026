#!/usr/bin/env python3
"""
Varredura nacional dos logs de urna: baixa (paralelo, retomável), parseia em memória e grava Parquet por UF.

  python logs_brasil.py scan --uf RR AC ...     # ou --uf ALL (menores primeiro, SP por último)
  python logs_brasil.py scan --uf ALL --workers 16

Saídas:
  data/logs/raw/<k>-log.jez              brutos (mantidos; o aux.json não é guardado nesta etapa)
  data/logs_parquet/secoes_<UF>.parquet  1 linha por urna, métricas
  data/logs_parquet/eleitores_<UF>_<n>.parquet  1 linha por habilitação (partes de ~4.000 urnas)
  data/logs_parquet/falhas.csv           seções que falharam (para reprocessar)
  out/logs_brasil/progresso.log
Reusa parse_log()/extrair_logs() de logs_urna.py.
"""
import argparse, io, json, sys, threading, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import numpy as np, pandas as pd
import pipeline_bu as pb
import logs_urna as lu

PQ = Path("data/logs_parquet"); OUT = Path("out/logs_brasil"); RAW = lu.RAW
ORDEM = "ZZ RR AP AC TO RO SE DF AL MS RN AM MT ES PI PB GO SC MA PA PE CE PR RS BA RJ MG SP".split()


def log(msg):
    linha = f"{datetime.now():%H:%M:%S} {msg}"
    print(linha, flush=True)
    with open(OUT / "progresso.log", "a", encoding="utf-8") as f: f.write(linha + "\n")


# ------------------------------------------------------------------ download de 1 seção
def baixar_uma(sess, r, tentativas=4):
    uf = r.SG_UF.lower(); mun = f"{int(r.CD_MUNICIPIO):05d}"; zona = f"{int(r.NR_ZONA):04d}"; sec = f"{int(r.NR_SECAO):04d}"
    dst = RAW / f"{r.k}-log.jez"
    if dst.exists() and dst.stat().st_size > 0: return dst.read_bytes()
    base = f"{lu.BASE}/{uf}/{mun}/{zona}/{sec}"
    for t in range(tentativas):
        try:
            aux = sess.get(f"{base}/p00{lu.PLEITO}-{uf}-m{mun}-z{zona}-s{sec}-aux.json", timeout=60)
            if aux.status_code in (429, 500, 502, 503, 504): raise IOError(f"HTTP {aux.status_code} aux")
            aux.raise_for_status(); j = aux.json()
            h = j["hashes"][-1]; nm = [a["nm"] for a in h["arq"] if a["tp"] == "log"][0]
            lg = sess.get(f"{base}/{h['hash']}/{nm}", timeout=120)
            if lg.status_code in (429, 500, 502, 503, 504): raise IOError(f"HTTP {lg.status_code} log")
            lg.raise_for_status()
            blob = lg.content
            zipfile.ZipFile(io.BytesIO(blob)).testzip()   # valida antes de gravar
            dst.write_bytes(blob); return blob
        except Exception as e:
            if t == tentativas - 1: raise
            time.sleep(2 * (t + 1))


# ------------------------------------------------------------------ métricas de 1 urna
def metricas(r, el, info):
    fech = datetime.strptime(f"{lu.DIA} {pb.FECH_LOCAL.get(r.SG_UF, '17:00:00')}", "%d/%m/%Y %H:%M:%S")
    t_enc = info["t_encerrar"]
    votos = [e for e in el if e["t_voto"] is not None]
    man = [e for e in el if e["tipo"] == "manual"]; bio = [e for e in el if e["tipo"] == "biometrica"]
    dur = lambda lst: [(e["t_voto"] - e["t_hab"]).total_seconds() for e in lst if e["t_voto"]]
    dm, db = dur(man), dur(bio)
    ult = lambda m: (lambda e: t_enc is not None and (t_enc - e["t_hab"]).total_seconds() <= m * 60)
    frac = lambda lst, cond: (sum(cond(e) for e in lst) / len(lst)) if lst else np.nan
    tv = sorted(e["t_voto"] for e in votos)
    gaps = [(b - a).total_seconds() for a, b in zip(tv, tv[1:])]
    gaps_fim = [(b - a).total_seconds() for a, b in zip(tv, tv[1:]) if t_enc and (t_enc - b).total_seconds() <= 3600]
    run = best = 0
    for e in el:
        run = run + 1 if e["tipo"] == "manual" else 0; best = max(best, run)
    tm = sorted(e["t_hab"] for e in man); max15 = 0
    for i, a in enumerate(tm):
        j = i
        while j < len(tm) and (tm[j] - a).total_seconds() <= 900: j += 1
        max15 = max(max15, j - i)
    # taxa manual por bloco do dia (detecta leitor que degrada no meio do dia)
    def tx_bloco(h0, h1):
        b = [e for e in el if h0 <= e["t_hab"].hour < h1 and e["tipo"] in ("manual", "biometrica")]
        return (sum(e["tipo"] == "manual" for e in b) / len(b)) if len(b) >= 10 else np.nan
    return {"k": r.k, "SG_UF": r.SG_UF, "CD_MUNICIPIO": int(r.CD_MUNICIPIO), "NR_ZONA": int(r.NR_ZONA), "NR_SECAO": int(r.NR_SECAO),
            "NR_LOCAL_VOTACAO": int(r.NR_LOCAL_VOTACAO), "modelo": info["modelo"],
            "bu_aptos": int(r.aptos), "bu_comp": int(r.comp), "bu_bio_nh": int(r.bio_nh), "bu_min_apos_fech": r.min_apos_fech,
            "log_habilitados": len(el), "log_votos": len(votos), "log_bio": len(bio), "log_manual": len(man),
            "log_sem_biometria": sum(e["tipo"] == "sem_biometria" for e in el), "log_outro": sum(e["tipo"] == "outro" for e in el),
            "t_encerrar": t_enc, "primeiro_voto": tv[0] if tv else None, "ultimo_voto": tv[-1] if tv else None,
            "min_enc_apos_fech_prev": (t_enc - fech).total_seconds() / 60 if t_enc else np.nan,
            "min_ultimo_voto_antes_enc": (t_enc - tv[-1]).total_seconds() / 60 if (t_enc and tv) else np.nan,
            "frac_votos_ult60": frac(el, ult(60)), "frac_manual_ult60": frac(man, ult(60)),
            "votos_ult60": sum(ult(60)(e) for e in el), "manual_ult60": sum(ult(60)(e) for e in man),
            "n_votos_apos_fech_prev": sum(e["t_hab"] >= fech for e in el), "n_manual_apos_fech_prev": sum(e["t_hab"] >= fech for e in man),
            "dur_mediana_s": np.median(dur(votos)) if votos else np.nan,
            "dur_manual_med_s": np.median(dm) if dm else np.nan, "dur_manual_p25_s": np.percentile(dm, 25) if dm else np.nan,
            "dur_bio_med_s": np.median(db) if db else np.nan, "dur_bio_p25_s": np.percentile(db, 25) if db else np.nan,
            "razao_dur_manual_bio": (np.median(dm) / np.median(db)) if (dm and db and np.median(db) > 0) else np.nan,
            "pct_manual_lt30": (np.mean([d < 30 for d in dm]) if dm else np.nan), "pct_bio_lt30": (np.mean([d < 30 for d in db]) if db else np.nan),
            "gap_mediano_s": np.median(gaps) if gaps else np.nan, "gap_mediano_ult60_s": np.median(gaps_fim) if gaps_fim else np.nan,
            "max_run_manual": best, "max_manual_15min": max15,
            "tent_media_manual": np.mean([e["tentativas"] for e in man]) if man else np.nan,
            "tx_manual_8_11": tx_bloco(8, 11), "tx_manual_11_14": tx_bloco(11, 14), "tx_manual_14_17": tx_bloco(14, 17), "tx_manual_17_": tx_bloco(17, 24)}


def linhas_eleitores(r, el, info):
    t_enc = info["t_encerrar"]
    return [{"k": r.k, "SG_UF": r.SG_UF, "t_hab": e["t_hab"], "tipo": e["tipo"], "tentativas": e["tentativas"],
             "dur_s": (e["t_voto"] - e["t_hab"]).total_seconds() if e["t_voto"] else np.nan,
             "min_antes_enc": (t_enc - e["t_hab"]).total_seconds() / 60 if t_enc else np.nan} for e in el]


def parse_blob(blob):
    partes = lu.extrair_logs(blob)
    tmp = Path(OUT / f"_tmp_{threading.get_ident()}.dat"); tmp.write_bytes(b"\n".join(partes))
    try: return lu.parse_log(tmp)
    finally: tmp.unlink(missing_ok=True)


# ------------------------------------------------------------------ varredura de 1 UF
def scan_uf(uf, workers, con_bu, chunk=4000):
    import requests, duckdb
    dst_sec = PQ / f"secoes_{uf}.parquet"
    if dst_sec.exists(): log(f"[{uf}] já processada, pulando"); return
    secs = con_bu.execute("""SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO, aptos, comp, bio_nh, min_apos_fech
                             FROM z WHERE SG_UF = ?""", [uf]).df()
    for c in ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]: secs[c] = secs[c].astype(int)
    secs["k"] = secs.apply(lu.key, axis=1)
    n = len(secs); log(f"[{uf}] {n} urnas, {workers} conexões")
    local = threading.local()
    def sess():
        if not hasattr(local, "s"):
            local.s = requests.Session(); local.s.headers["User-Agent"] = "Mozilla/5.0 (analise-bu-2026)"
        return local.s
    def tarefa(r):
        blob = baixar_uma(sess(), r)
        el, info = parse_blob(blob)
        return r, el, info
    met, ele, falhas, parte, feito, t0 = [], [], [], 0, 0, time.time()
    pq = duckdb.connect()
    def flush_ele():
        nonlocal ele, parte
        if not ele: return
        df = pd.DataFrame(ele); pq.register("df", df)
        pq.execute(f"COPY df TO '{(PQ / f'eleitores_{uf}_{parte:03d}.parquet').as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        pq.unregister("df"); ele = []; parte += 1
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(tarefa, r): r.k for _, r in secs.iterrows()}
        for f in as_completed(futs):
            feito += 1
            try:
                r, el, info = f.result()
                met.append(metricas(r, el, info)); ele.extend(linhas_eleitores(r, el, info))
            except Exception as e:
                falhas.append({"uf": uf, "k": futs[f], "erro": str(e)[:200]})
            if len(ele) > chunk * 250: flush_ele()
            if feito % 1000 == 0 or feito == n:
                el_s = time.time() - t0
                log(f"[{uf}] {feito}/{n} ({100*feito/n:.0f}%) {el_s/60:.1f} min, {feito/el_s:.1f} urnas/s, falhas {len(falhas)}")
    flush_ele()
    df = pd.DataFrame(met); pq.register("df", df)
    pq.execute(f"COPY df TO '{dst_sec.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)"); pq.unregister("df")
    if falhas:
        pd.DataFrame(falhas).to_csv(PQ / "falhas.csv", mode="a", header=not (PQ / "falhas.csv").exists(), index=False)
    log(f"[{uf}] concluída: {len(df)} urnas em {(time.time()-t0)/60:.1f} min, {len(falhas)} falhas; "
        f"comp bate {int((df.log_votos == df.bu_comp).sum())}/{len(df)}, manual bate {int((df.log_manual == df.bu_bio_nh).sum())}/{len(df)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["scan"])
    ap.add_argument("--uf", nargs="+", required=True); ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    PQ.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    import duckdb
    con = duckdb.connect(str(pb.DB), read_only=True); pb.build_tables(con)
    ufs = ORDEM if a.uf == ["ALL"] else a.uf
    for uf in ufs:
        try: scan_uf(uf, a.workers, con)
        except Exception as e:
            log(f"[{uf}] ERRO FATAL: {e}"); raise
    log("varredura concluída")
