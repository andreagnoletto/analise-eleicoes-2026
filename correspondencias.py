#!/usr/bin/env python3
"""
Correspondências esperadas/efetivadas (TSE, Dados Abertos): qual urna física (NR_URNA) foi designada a cada seção.

Uso, enquanto o BU do 2º turno não sai:
  python correspondencias.py download     # CESP_2t (esperada, 24/10), CEFT_1t (efetivada, 05/10), CESP_1t (esperada, 04/10); SHA-512 conferido
  python correspondencias.py load         # data/2t/corresp.duckdb: cesp_2t, ccont_2t, ceft_1t, cesp_1t
  python correspondencias.py comparar     # out/2t/comparacao/26_* e 27_*: validação, mesma urna 1t→2t (provisório) e P4 pelos logs

A "esperada" do 2º turno é a urna planejada; a "efetivada" (ainda não publicada) é a que de fato votou. No 1º turno as duas
diferem em poucas seções (contingência); o item 26 mede essa diferença para calibrar o quanto o provisório pode errar.
"""
import argparse, hashlib, os, sys, time, zipfile
from pathlib import Path
os.environ.setdefault("TURNO", "2")
import requests, duckdb, pandas as pd, numpy as np
import config as cfg

RAW = cfg.DATA / "corresp_raw"; CSV = cfg.DATA / "corresp_csv"; DB = cfg.DATA / "corresp.duckdb"
OUT = cfg.OUT / "comparacao"; DB_BU_1T = Path("data/bu2026.duckdb")
LOGS_1T = Path("out/logs_brasil/secoes_logs_brasil.parquet"); LOGS_2T = cfg.OUT / "logs_brasil" / "secoes_logs_brasil.parquet"
CKAN = "https://dadosabertos.tse.jus.br/api/3/action/package_show"
DATASETS = ["resultados-2026-correspondencias-esperadas-e-efetivadas-2-turno",
            "resultados-2026-correspondencias-esperadas-e-efetivadas-1-turno"]
# carimbos: esperada 2t (véspera), efetivada 1t (D+1), esperada 1t (dia da eleição; a de 03/10 é a versão anterior)
ARQUIVOS = {"cesp_2t": "CESP_2t_{uf}_241020261231.zip",      # esperada 2t, véspera
            "cesp_2t_dia": "CESP_2t_{uf}_251020261345.zip",  # esperada 2t, dia da eleição
            "ceft_2t": "CEFT_2t_{uf}_261020261201.zip",      # efetivada 2t (gerada 26/10 12h01; no portal em 27/10 entre 9h50 e 10h24 de Brasília; o catálogo registra horários em UTC)
            "ceft_1t": "CEFT_1t_{uf}_051020261049.zip", "cesp_1t": "CESP_1t_{uf}_041020261259.zip"}
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "ZZ"]
H = {"User-Agent": "Mozilla/5.0"}
K_SQL = ("lower(SG_UF) || '-' || lpad(CAST(CAST(CD_MUNICIPIO AS INT) AS VARCHAR), 5, '0') || '-' || "
         "lpad(CAST(CAST(NR_ZONA AS INT) AS VARCHAR), 4, '0') || '-' || lpad(CAST(CAST(NR_SECAO AS INT) AS VARCHAR), 4, '0')")


def urls_ckan():
    urls = {}
    for ds in DATASETS:
        # a API é servida por um cache (max-age 3600; em 27/10 devolveu versão de 24/10 por horas): parâmetro anticache
        j = requests.get(CKAN, params={"id": ds, "nocache": int(time.time())}, headers={**H, "Cache-Control": "no-cache"}, timeout=60).json()["result"]
        for x in j["resources"]:
            urls[x["url"].rsplit("/", 1)[-1]] = x["url"]
    return urls


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    urls = urls_ckan()
    faltam = [a.format(uf=uf) for a in ARQUIVOS.values() for uf in UFS if a.format(uf=uf) not in urls]
    if faltam:
        sys.exit(f"[download] {len(faltam)} arquivos não listados no CKAN, p.ex. {faltam[:3]}; nada baixado")
    for a in ARQUIVOS.values():
        for uf in UFS:
            nome = a.format(uf=uf)
            for ext in ("", ".sha512"):
                dst = RAW / (nome + ext)
                if dst.exists() and dst.stat().st_size > 0:
                    continue
                with requests.get(urls[nome + ext], headers=H, timeout=600, stream=True) as r:
                    r.raise_for_status()
                    tmp = dst.with_suffix(dst.suffix + ".part")
                    with open(tmp, "wb") as f:
                        for ch in r.iter_content(1 << 20):
                            f.write(ch)
                    tmp.replace(dst)
            esperado = (RAW / (nome + ".sha512")).read_text().split()[0].lower()
            obtido = hashlib.sha512((RAW / nome).read_bytes()).hexdigest()
            if esperado != obtido:
                sys.exit(f"[download] HASH FALHOU em {nome}: esperado {esperado[:16]}…, obtido {obtido[:16]}…  PARANDO.")
            print(f"[download] {nome} {((RAW / nome).stat().st_size / 1e6):.1f} MB hash OK", flush=True)
    print(f"[download] {len(ARQUIVOS) * len(UFS)} arquivos conferidos")


def load():
    CSV.mkdir(parents=True, exist_ok=True)
    for a in ARQUIVOS.values():
        for uf in UFS:
            with zipfile.ZipFile(RAW / a.format(uf=uf)) as z:
                for i in z.infolist():
                    if i.filename.lower().endswith(".csv") and not (CSV / i.filename).exists():
                        z.extract(i, CSV)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    for tab, pat in [("cesp_2t", "csec_2t_*_241020261231.csv"), ("ccont_2t", "ccont_2t_*_241020261231.csv"),
                     ("cesp_2t_dia", "csec_2t_*_251020261345.csv"), ("ccont_2t_dia", "ccont_2t_*_251020261345.csv"),
                     ("ceft_2t", "ceft_2t_*.csv"), ("ceft_1t", "ceft_1t_*.csv"), ("cesp_1t", "csec_1t_*.csv")]:
        con.execute(f"""CREATE TABLE {tab} AS SELECT * FROM read_csv('{(CSV / pat).as_posix()}', delim=';', header=true, quote='"',
                        all_varchar=true, encoding='latin-1', union_by_name=true)""")
        n, ufs = con.execute(f"SELECT count(*), count(DISTINCT SG_UF) FROM {tab}").fetchone()
        print(f"[load] {tab}: {n:,} linhas, {ufs} UFs")
    con.close()


def comparar():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB.as_posix()}' AS c (READ_ONLY); ATTACH '{DB_BU_1T.as_posix()}' AS b (READ_ONLY)")
    con.execute(f"""CREATE TABLE bu1 AS
        SELECT DISTINCT {K_SQL} k, SG_UF, NR_URNA_EFETIVADA urna_bu FROM b.bu
        WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%' AND CD_TIPO_URNA = '1'""")
    con.execute(f"CREATE TABLE e1 AS SELECT {K_SQL} k, SG_UF, NR_URNA_ESPERADA urna_esp1, NR_URNA_EFETIVADA urna_ef1, CD_ORIGEM_VOTO, TP_DIVERGENCIA FROM c.ceft_1t")
    con.execute(f"CREATE TABLE p1 AS SELECT {K_SQL} k, NR_URNA_ESPERADA urna_esp1_dia FROM c.cesp_1t")
    con.execute(f"""CREATE TABLE p2 AS SELECT {K_SQL} k, SG_UF, NR_URNA_ESPERADA urna_esp2, NR_URNA_EFETIVADA urna_ef2,
                    CD_ORIGEM_VOTO origem2, TP_DIVERGENCIA div2 FROM c.ceft_2t""")
    con.execute(f"CREATE TABLE v2 AS SELECT {K_SQL} k, NR_URNA_ESPERADA urna_esp2_vesp FROM c.cesp_2t")
    # 26a validação: efetivada (arquivo de correspondência) × NR_URNA_EFETIVADA do BU, 1º turno
    v = con.execute("""
        SELECT b.SG_UF uf, count(*) secoes_bu, count(e.k) com_corresp, sum(e.urna_ef1 = b.urna_bu) mesma_urna_que_bu,
               sum(e.urna_esp1 <> e.urna_ef1) esperada_ne_efetivada, sum(p.urna_esp1_dia <> e.urna_ef1) esperada_dia_ne_efetivada,
               sum(e.CD_ORIGEM_VOTO <> 'U') origem_nao_urna
        FROM bu1 b LEFT JOIN e1 e USING (k) LEFT JOIN p1 p USING (k) GROUP BY 1 ORDER BY 1""").df()
    tot = v.drop(columns="uf").sum(); tot["uf"] = "BR"; v = pd.concat([v, tot.to_frame().T], ignore_index=True)
    v["pct_mesma_urna_que_bu"] = (100 * v.mesma_urna_que_bu / v.com_corresp).astype(float).round(3)
    v["pct_esperada_ne_efetivada"] = (100 * v.esperada_ne_efetivada / v.com_corresp).astype(float).round(2)
    v["pct_esperada_dia_ne_efetivada"] = (100 * v.esperada_dia_ne_efetivada / v.com_corresp).astype(float).round(2)
    v.to_csv(OUT / "26_corresp_validacao_1t.csv", index=False)
    br = v[v.uf == "BR"].iloc[0]
    print(f"[26] 1t: {int(br.secoes_bu):,} seções no BU, {int(br.com_corresp):,} com correspondência, "
          f"{br.pct_mesma_urna_que_bu}% mesma urna que o BU; esperada≠efetivada {br.pct_esperada_ne_efetivada}% (véspera) / "
          f"{br.pct_esperada_dia_ne_efetivada}% (dia); origem≠urna {int(br.origem_nao_urna):,}")
    # 26c o mesmo para o 2º turno: esperada (véspera e dia) × efetivada, origem do voto
    v2 = con.execute("""
        SELECT p.SG_UF uf, count(*) secoes, sum(v.urna_esp2_vesp <> p.urna_ef2) esperada_vesp_ne_efetivada,
               sum(p.urna_esp2 <> p.urna_ef2) esperada_dia_ne_efetivada, sum(p.origem2 <> 'U') origem_nao_urna
        FROM p2 p LEFT JOIN v2 v USING (k) GROUP BY 1 ORDER BY 1""").df()
    tot = v2.drop(columns="uf").sum(); tot["uf"] = "BR"; v2 = pd.concat([v2, tot.to_frame().T], ignore_index=True)
    v2["pct_esperada_vesp_ne_efetivada"] = (100 * v2.esperada_vesp_ne_efetivada / v2.secoes).astype(float).round(2)
    v2["pct_esperada_dia_ne_efetivada"] = (100 * v2.esperada_dia_ne_efetivada / v2.secoes).astype(float).round(2)
    v2.to_csv(OUT / "26_corresp_validacao_2t.csv", index=False)
    br2 = v2[v2.uf == "BR"].iloc[0]
    print(f"[26] 2t: {int(br2.secoes):,} seções na efetivada; esperada≠efetivada {br2.pct_esperada_vesp_ne_efetivada}% (véspera) / "
          f"{br2.pct_esperada_dia_ne_efetivada}% (dia); origem≠urna {int(br2.origem_nao_urna):,}")
    # 26b mesma urna 1t (efetivada, BU) → 2t (efetivada, arquivo de correspondência)
    con.execute("""CREATE TABLE m AS
        SELECT coalesce(b.k, p.k) k, coalesce(b.SG_UF, p.SG_UF) SG_UF, b.urna_bu, p.urna_esp2, p.urna_ef2, p.origem2,
               b.k IS NOT NULL em_1t, p.k IS NOT NULL em_2t, (b.urna_bu = p.urna_ef2) mesma_urna
        FROM bu1 b FULL OUTER JOIN p2 p USING (k)""")
    mu = con.execute("""
        SELECT SG_UF uf, sum(em_1t) secoes_1t, sum(em_2t) secoes_2t, sum(em_1t AND em_2t) pareadas,
               sum(em_1t AND NOT em_2t) so_1t, sum(em_2t AND NOT em_1t) so_2t, sum(mesma_urna) mesma_urna,
               round(100.0*sum(mesma_urna)/sum(em_1t AND em_2t), 2) pct_mesma_urna
        FROM m GROUP BY 1 ORDER BY 1""").df()
    tot = mu.drop(columns=["uf", "pct_mesma_urna"]).sum(); tot["uf"] = "BR"; tot["pct_mesma_urna"] = round(100 * tot.mesma_urna / tot.pareadas, 2)
    mu = pd.concat([mu, tot.to_frame().T], ignore_index=True)
    mu.to_csv(OUT / "26_mesma_urna_1t_2t_provisorio_uf.csv", index=False)
    br = mu[mu.uf == "BR"].iloc[0]
    print(f"[26] 1t→2t: {int(br.pareadas):,} seções pareadas ({int(br.so_1t):,} só no 1t, {int(br.so_2t):,} só no 2t); "
          f"mesma urna física (efetivada nos dois turnos) em {br.pct_mesma_urna}%")
    # urnas do 2t que eram de outra seção no 1t / que não votaram no 1t (contingência, reserva, nova)
    con.execute("CREATE TABLE u1 AS SELECT urna_bu urna, min(k) k1 FROM bu1 GROUP BY 1")
    orig = con.execute("""
        SELECT CASE WHEN mesma_urna THEN 'mesma seção'
                    WHEN u1.urna IS NOT NULL THEN 'outra seção no 1t'
                    ELSE 'não votou no 1t (contingência/reserva/nova)' END origem_urna_2t, count(*) n,
               round(100.0*count(*)/sum(count(*)) OVER (), 2) pct
        FROM m LEFT JOIN u1 ON u1.urna = m.urna_ef2 WHERE em_1t AND em_2t GROUP BY 1 ORDER BY n DESC""").df()
    orig.to_csv(OUT / "26_origem_urna_2t.csv", index=False)
    print("[26] origem da urna efetivada do 2t:", "; ".join(f"{r.origem_urna_2t} {r.pct}%" for r in orig.itertuples()))
    # 27 P4 provisório pelos logs: corr(tx_manual 1t, tx_manual 2t) por mesma urna × trocada
    con.execute(f"""CREATE TABLE l AS
        SELECT m.k, m.SG_UF, m.mesma_urna, a.modelo modelo_1t, b.modelo modelo_2t,
               a.log_manual*1.0/NULLIF(a.log_votos,0) tx1, b.log_manual*1.0/NULLIF(b.log_votos,0) tx2, a.log_votos v1, b.log_votos v2
        FROM m JOIN '{LOGS_1T.as_posix()}' a USING (k) JOIN '{LOGS_2T.as_posix()}' b USING (k)
        WHERE m.em_1t AND m.em_2t AND a.log_votos >= 50 AND b.log_votos >= 50""")
    l = con.execute("SELECT * FROM l").df()

    def corr(g):
        if len(g) < 30 or g.tx1.std() == 0 or g.tx2.std() == 0:
            return pd.Series({"n": len(g), "pearson": np.nan, "spearman": np.nan, "tx1_med": np.nan, "tx2_med": np.nan})
        return pd.Series({"n": len(g), "pearson": g.tx1.corr(g.tx2), "spearman": g.tx1.rank().corr(g.tx2.rank()),
                          "tx1_med": g.tx1.median(), "tx2_med": g.tx2.median()})

    l["grupo"] = np.where(l.mesma_urna, "mesma urna", "urna trocada")
    g_br = l.groupby("grupo").apply(corr, include_groups=False).reset_index(); g_br.insert(0, "uf", "BR")
    g_uf = l.groupby(["SG_UF", "grupo"]).apply(corr, include_groups=False).reset_index().rename(columns={"SG_UF": "uf"})
    # sem os dias de falha total do leitor (tx > 0,5 em algum turno): mede a persistência "normal"
    g_sem = l[(l.tx1 <= 0.5) & (l.tx2 <= 0.5)].groupby("grupo").apply(corr, include_groups=False).reset_index(); g_sem.insert(0, "uf", "BR sem tx>0,5")
    p4 = pd.concat([g_br, g_sem, g_uf], ignore_index=True)
    for c in ["pearson", "spearman", "tx1_med", "tx2_med"]:
        p4[c] = p4[c].astype(float).round(4)
    p4.to_csv(OUT / "27_p4_provisorio_logs.csv", index=False)
    # por modelo (do 2t), só mesma urna: o leitor é o mesmo
    g_mod = l[l.mesma_urna].groupby("modelo_2t").apply(corr, include_groups=False).reset_index()
    g_mod.to_csv(OUT / "27_p4_provisorio_por_modelo.csv", index=False)
    mesma = g_br[g_br.grupo == "mesma urna"].iloc[0]; troc = g_br[g_br.grupo == "urna trocada"].iloc[0]
    ok = (mesma.pearson > 0.5) and (mesma.pearson > troc.pearson)
    pd.DataFrame([{"id": "P4 (provisório, logs + correspondência esperada)",
                   "predicao": "corr(tx manual 1t, 2t) > 0,5 nas urnas mantidas e maior que nas trocadas",
                   "n_mesma": int(mesma.n), "corr_mesma": round(mesma.pearson, 3), "spearman_mesma": round(mesma.spearman, 3),
                   "n_trocada": int(troc.n), "corr_trocada": round(troc.pearson, 3), "spearman_trocada": round(troc.spearman, 3),
                   "ok": bool(ok)}]).to_csv(OUT / "27_p4_provisorio.csv", index=False)
    print(f"[27] P4 provisório: mesma urna n={int(mesma.n):,} r={mesma.pearson:.3f} (ρ={mesma.spearman:.3f}); "
          f"trocada n={int(troc.n):,} r={troc.pearson:.3f} (ρ={troc.spearman:.3f}) → {'ok' if ok else 'NÃO'}")
    print("[27] por modelo (mesma urna):", "; ".join(f"{r.modelo_2t} n={int(r.n):,} r={r.pearson:.3f}" for r in g_mod.itertuples()))
    # 28 falha total do leitor (tx manual > 0,5 com ≥ 50 votos): frequência por modelo no 1t e repetição no 2t, mesma urna × trocada
    f_mod = con.execute("""SELECT modelo_1t modelo, count(*) n, sum(tx1 > 0.5) falha_1t, round(1000.0*sum(tx1 > 0.5)/count(*), 2) por_mil
                           FROM l GROUP BY 1 ORDER BY 1""").df()
    f_mod.to_csv(OUT / "28_falha_leitor_modelo_1t.csv", index=False)
    f_rep = con.execute("""SELECT CASE WHEN mesma_urna THEN 'mesma urna' ELSE 'urna trocada' END grupo, count(*) n, sum(tx1 > 0.5) falha_1t,
                                  sum(tx1 > 0.5 AND tx2 > 0.5) falha_ambos, sum(tx1 <= 0.5 AND tx2 > 0.5) falha_so_2t,
                                  round(100.0*sum(tx1 > 0.5 AND tx2 > 0.5)/NULLIF(sum(tx1 > 0.5), 0), 1) pct_repete
                           FROM l GROUP BY 1 ORDER BY 1""").df()
    f_rep.to_csv(OUT / "28_falha_leitor_repeticao.csv", index=False)
    con.execute("""SELECT k, SG_UF, mesma_urna, modelo_1t, modelo_2t, round(tx1, 3) tx1, round(tx2, 3) tx2, v1, v2
                   FROM l WHERE tx1 > 0.5 OR tx2 > 0.5 ORDER BY abs(tx1 - tx2) DESC""").df().to_csv(OUT / "28_falha_leitor_secoes.csv", index=False)
    print("[28] falha do leitor no 1t por modelo (‰):", "; ".join(f"{r.modelo} {r.por_mil}" for r in f_mod.itertuples()))
    print("[28] repetição no 2t:", "; ".join(f"{r.grupo}: {int(r.falha_1t)} falhas no 1t, {int(r.falha_ambos)} repetiram ({r.pct_repete}%), {int(r.falha_so_2t)} novas" for r in f_rep.itertuples()))
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["download", "load", "comparar"])
    a = ap.parse_args(); print("[config]", cfg.resumo())
    {"download": download, "load": load, "comparar": comparar}[a.cmd]()
