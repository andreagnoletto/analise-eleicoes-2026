#!/usr/bin/env python3
"""
Logs de urna (log.jez) — distribuição temporal das habilitações manuais e dos votos.

Etapas:
  python logs_urna.py selecionar   # amostra: flagradas (A: calibrado, B: manual×tardia) + controles -> out/logs/00_amostra.csv
  python logs_urna.py baixar       # aux.json -> hash -> log.jez (ZIP com logd.dat) em data/logs/raw ; extrai para data/logs/txt
  python logs_urna.py parsear      # out/logs/01_eleitores.csv (1 linha por habilitação) e 02_secoes_metricas.csv
  python logs_urna.py analisar     # resumos por grupo, gráficos, lista de anomalias

Fonte: https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/<pleito>/dados/<uf>/<mun>/<zona>/<secao>/
Mensagens relevantes (logd.dat, Latin-1, campos separados por TAB: data hora, nível, id urna, app, mensagem, hash):
  "Tipo de habilitação do eleitor [biométrica]"                       -> habilitação biométrica
  "Solicitação de dado pessoal do eleitor para habilitação manual"     -> habilitação manual (após 4 tentativas de digital)
  "Eleitor foi habilitado"  /  "O voto do eleitor foi computado"
  "Operador selecionou: Encerrar votação"  /  "Identificação do Modelo de Urna: UE2020"
"""
import argparse, json, random, re, time, zipfile
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np, pandas as pd
import pipeline_bu as pb

PLEITO = "3220"
BASE = f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/{PLEITO}/dados"
OUT = Path("out/logs"); RAW = Path("data/logs/raw"); TXT = Path("data/logs/txt")
DIA = "04/10/2026"
PALETA = ["#eb6834", "#eda100", "#2a78d6", "#1baf7a", "#e87ba4", "#4a3aa7"]
GRUPOS, COR = [], {}   # definidos em analisar() a partir da amostra (grupos de controle contêm "controle" no nome)


def key(r):
    return f"{r.SG_UF.lower()}-{int(r.CD_MUNICIPIO):05d}-{int(r.NR_ZONA):04d}-{int(r.NR_SECAO):04d}"


# ------------------------------------------------------------------ selecionar
def selecionar(n_ctrl_mun=3, n_ctrl_nac=150, seed=2026):
    import duckdb
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(pb.DB), read_only=True)
    pb.build_tables(con)
    fl = pd.read_csv("out/brasil/secoes_flagradas_brasil.csv")
    A = fl[fl.flag_cal].copy(); A["grupo"] = "A_calibrado"
    B = fl[fl.flag_tard & ~fl.flag_cal].sort_values("z_manual", ascending=False).head(25).copy(); B["grupo"] = "B_manual_tardia"
    cols = ["grupo", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO",
            "aptos", "comp", "bio_nh", "tx_manual", "tx_comp", "z_manual", "min_apos_fech"]
    flag = pd.concat([A, B])[cols]
    flag["ref"] = flag.apply(key, axis=1)
    z = con.execute("""SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO, aptos, comp, bio_nh,
                              tx_manual, tx_comp, z_manual, min_apos_fech, regiao
                       FROM z WHERE aptos >= 100 AND SG_UF <> 'ZZ'""").df()
    for c in ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]:
        z[c] = z[c].astype(int); flag[c] = flag[c].astype(int)
    z["k"] = z.apply(key, axis=1)
    flagk = set(flag.apply(key, axis=1))
    rng = random.Random(seed)
    ctrl = []
    for _, f in flag.iterrows():
        pool = z[(z.SG_UF == f.SG_UF) & (z.CD_MUNICIPIO == f.CD_MUNICIPIO) & ~z.k.isin(flagk)]
        for i in rng.sample(range(len(pool)), min(n_ctrl_mun, len(pool))):
            r = pool.iloc[i].to_dict(); r["grupo"] = "C_controle_municipio"; r["ref"] = f.ref; ctrl.append(r)
    pool = z[~z.k.isin(flagk)]
    por_reg = n_ctrl_nac // 5
    for reg in ["N", "NE", "CO", "SE", "S"]:
        p = pool[pool.regiao == reg]
        for i in rng.sample(range(len(p)), por_reg):
            r = p.iloc[i].to_dict(); r["grupo"] = "D_controle_nacional"; r["ref"] = ""; ctrl.append(r)
    am = pd.concat([flag, pd.DataFrame(ctrl)[cols + ["ref"]]], ignore_index=True)
    am = am.drop_duplicates(subset=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"])
    am["k"] = am.apply(key, axis=1)
    am.to_csv(OUT / "00_amostra.csv", index=False)
    print(am.grupo.value_counts().to_string()); print(f"total {len(am)} seções -> {OUT/'00_amostra.csv'}")


def extrair_logs(blob):
    """O log.jez é um ZIP com logd.dat; em urna de contingência traz também um .jez aninhado com o log
    da urna original. Retorna os conteúdos dos logd.dat em ordem cronológica (aninhados primeiro)."""
    import io
    partes = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for n in zf.namelist():
            if n.lower().endswith(".jez"): partes.extend(extrair_logs(zf.read(n)))
        for n in zf.namelist():
            if n.lower().endswith(".dat"): partes.append(zf.read(n))
    return partes


# ------------------------------------------------------------------ baixar
def baixar(pausa=0.15):
    import requests
    am = pd.read_csv(OUT / "00_amostra.csv")
    RAW.mkdir(parents=True, exist_ok=True); TXT.mkdir(parents=True, exist_ok=True)
    s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (analise-bu-2026)"
    ok = err = 0
    for _, r in am.iterrows():
        uf = r.SG_UF.lower(); mun = f"{int(r.CD_MUNICIPIO):05d}"; zona = f"{int(r.NR_ZONA):04d}"; sec = f"{int(r.NR_SECAO):04d}"
        k = r.k; dst = RAW / f"{k}-log.jez"; txt = TXT / f"{k}.logd.dat"
        try:
            if not dst.exists():
                aux = s.get(f"{BASE}/{uf}/{mun}/{zona}/{sec}/p00{PLEITO}-{uf}-m{mun}-z{zona}-s{sec}-aux.json", timeout=60)
                aux.raise_for_status(); j = aux.json()
                (RAW / f"{k}-aux.json").write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
                h = j["hashes"][-1]; nm = [a["nm"] for a in h["arq"] if a["tp"] == "log"][0]
                lg = s.get(f"{BASE}/{uf}/{mun}/{zona}/{sec}/{h['hash']}/{nm}", timeout=120); lg.raise_for_status()
                dst.write_bytes(lg.content); time.sleep(pausa)
            if not txt.exists():
                txt.write_bytes(b"\n".join(extrair_logs(dst.read_bytes())))
            ok += 1
        except Exception as e:
            err += 1; print(f"[erro] {k}: {e}")
    print(f"[baixar] ok={ok} erro={err}")


# ------------------------------------------------------------------ parsear
RE_LINHA = re.compile(r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\t(\w+)\t(\d+)\t(\w+)\t(.*?)\t[0-9A-F]+\s*$")


def parse_log(path):
    """Retorna (eleitores: lista de dicts, info: dict) de um logd.dat."""
    ev = []
    for raw in path.read_bytes().decode("latin-1").splitlines():
        m = RE_LINHA.match(raw)
        if not m: continue
        ts, nivel, _, app, msg = m.groups()
        ev.append((datetime.strptime(ts, "%d/%m/%Y %H:%M:%S"), app, msg))
    info = {"modelo": None, "t_encerrar": None, "t_abre": None, "t_zeresima": None, "n_linhas": len(ev)}
    for t, app, msg in ev:
        if msg.startswith("Identificação do Modelo de Urna:"): info["modelo"] = msg.split(":")[-1].strip()
    dia = [e for e in ev if e[0].strftime("%d/%m/%Y") == DIA and e[1] == "VOTA"]
    eleitores = []; cur = {"tipo": None, "t_manual_req": None, "t_bio": None, "tent": 0}
    for t, app, msg in dia:
        if "zerésima" in msg and info["t_zeresima"] is None: info["t_zeresima"] = t
        if msg == "Tipo de habilitação do eleitor [biométrica]": cur["tipo"] = "biometrica"; cur["t_bio"] = t
        elif msg == "Solicitação de dado pessoal do eleitor para habilitação manual": cur["tipo"] = "manual"; cur["t_manual_req"] = t
        elif msg.startswith("Solicita digital. Tentativa"): cur["tent"] += 1
        elif msg.startswith("Ano de nascimento digitado") and cur["tipo"] is None: cur["tipo"] = "sem_biometria"
        elif msg == "Eleitor foi habilitado":
            eleitores.append({"t_hab": t, "tipo": cur["tipo"] or "outro", "tentativas": cur["tent"],
                              "t_manual_req": cur["t_manual_req"], "t_voto": None})
            cur = {"tipo": None, "t_manual_req": None, "t_bio": None, "tent": 0}
        elif msg == "O voto do eleitor foi computado":
            if eleitores and eleitores[-1]["t_voto"] is None: eleitores[-1]["t_voto"] = t
        elif msg == "Operador selecionou: Encerrar votação": info["t_encerrar"] = t
        elif msg == "Operador encerrou ciclo de registro de mesários" and info["t_abre"] is None and not eleitores: info["t_abre"] = t
    return eleitores, info


def parsear():
    am = pd.read_csv(OUT / "00_amostra.csv")
    rows, secs = [], []
    for _, r in am.iterrows():
        p = TXT / f"{r.k}.logd.dat"
        if not p.exists(): continue
        el, info = parse_log(p)
        fech = datetime.strptime(f"{DIA} {pb.FECH_LOCAL.get(r.SG_UF, '17:00:00')}", "%d/%m/%Y %H:%M:%S")
        t_enc = info["t_encerrar"]
        votos = [e for e in el if e["t_voto"] is not None]
        man = [e for e in el if e["tipo"] == "manual"]
        for e in el:
            rows.append({"k": r.k, "grupo": r.grupo, "SG_UF": r.SG_UF, **e,
                         "dur_s": (e["t_voto"] - e["t_hab"]).total_seconds() if e["t_voto"] else None,
                         "min_antes_enc": (t_enc - e["t_hab"]).total_seconds() / 60 if t_enc else None,
                         "min_apos_fech_prev": (e["t_hab"] - fech).total_seconds() / 60})
        def frac(lst, cond):
            return sum(cond(e) for e in lst) / len(lst) if lst else np.nan
        ult = lambda m: (lambda e: t_enc is not None and (t_enc - e["t_hab"]).total_seconds() <= m * 60)
        apos = lambda e: e["t_hab"] >= fech
        tv = sorted(e["t_voto"] for e in votos)
        gaps_fim = [(b - a).total_seconds() for a, b in zip(tv, tv[1:]) if t_enc and (t_enc - b).total_seconds() <= 3600]
        gaps_all = [(b - a).total_seconds() for a, b in zip(tv, tv[1:])]
        # maior sequência de manuais consecutivos e máximo de manuais em 15 min
        run = best = 0
        for e in el:
            run = run + 1 if e["tipo"] == "manual" else 0; best = max(best, run)
        tm = sorted(e["t_hab"] for e in man); max15 = 0
        for i, a in enumerate(tm):
            j = i
            while j < len(tm) and (tm[j] - a).total_seconds() <= 900: j += 1
            max15 = max(max15, j - i)
        secs.append({"k": r.k, "grupo": r.grupo, "SG_UF": r.SG_UF, "NM_MUNICIPIO": r.NM_MUNICIPIO, "NR_ZONA": r.NR_ZONA,
                     "NR_SECAO": r.NR_SECAO, "ref": r.ref, "modelo": info["modelo"],
                     "bu_aptos": r.aptos, "bu_comp": r.comp, "bu_bio_nh": r.bio_nh, "bu_min_apos_fech": r.min_apos_fech,
                     "log_habilitados": len(el), "log_votos": len(votos),
                     "log_bio": sum(e["tipo"] == "biometrica" for e in el), "log_manual": len(man),
                     "log_sem_biometria": sum(e["tipo"] == "sem_biometria" for e in el),
                     "log_outro": sum(e["tipo"] == "outro" for e in el),
                     "bate_comp": len(votos) == r.comp, "bate_manual": len(man) == r.bio_nh,
                     "t_abre": info["t_abre"], "t_zeresima": info["t_zeresima"], "t_encerrar": t_enc,
                     "primeiro_voto": tv[0] if tv else None, "ultimo_voto": tv[-1] if tv else None,
                     "min_enc_apos_fech_prev": (t_enc - fech).total_seconds() / 60 if t_enc else None,
                     "min_ultimo_voto_antes_enc": (t_enc - tv[-1]).total_seconds() / 60 if (t_enc and tv) else None,
                     "frac_votos_ult60": frac(el, ult(60)), "frac_manual_ult60": frac(man, ult(60)),
                     "frac_votos_ult30": frac(el, ult(30)), "frac_manual_ult30": frac(man, ult(30)),
                     "n_votos_apos_fech_prev": sum(apos(e) for e in el), "n_manual_apos_fech_prev": sum(apos(e) for e in man),
                     "frac_votos_apos_fech_prev": frac(el, apos), "frac_manual_apos_fech_prev": frac(man, apos),
                     "manual_ult60": sum(ult(60)(e) for e in man), "votos_ult60": sum(ult(60)(e) for e in el),
                     "dur_mediana_s": np.median([(e["t_voto"] - e["t_hab"]).total_seconds() for e in votos]) if votos else np.nan,
                     "dur_mediana_manual_s": np.median([(e["t_voto"] - e["t_hab"]).total_seconds() for e in man if e["t_voto"]]) if any(e["t_voto"] for e in man) else np.nan,
                     "gap_mediano_s": np.median(gaps_all) if gaps_all else np.nan,
                     "gap_mediano_ult60_s": np.median(gaps_fim) if gaps_fim else np.nan,
                     "max_run_manual": best, "max_manual_15min": max15,
                     "tent_media_manual": np.mean([e["tentativas"] for e in man]) if man else np.nan})
    pd.DataFrame(rows).to_csv(OUT / "01_eleitores.csv", index=False)
    s = pd.DataFrame(secs); s.to_csv(OUT / "02_secoes_metricas.csv", index=False)
    print(f"[parsear] {len(s)} seções, {len(rows)} habilitações")
    print("bate com o BU — comparecimento:", s.bate_comp.sum(), "/", len(s), "| manual:", s.bate_manual.sum(), "/", len(s))
    print(s[~s.bate_comp | ~s.bate_manual][["k", "grupo", "bu_comp", "log_votos", "log_habilitados", "bu_bio_nh", "log_manual", "log_sem_biometria", "log_outro"]].to_string(index=False))
    return s


# ------------------------------------------------------------------ analisar
def selecionar_ne(n_susp=1000, n_ctrl=300, max_min_apos=30, seed=2026):
    """Nordeste, urnas que fecharam no horário normal (até max_min_apos min após 17h), aptos >= 100.
    Suspeitas: maiores z_manual no município com comparecimento acima da média do município (z_comp > 0).
    Controles: aleatórias do NE com as mesmas restrições de horário e tamanho, fora das suspeitas."""
    import duckdb
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(pb.DB), read_only=True)
    pb.build_tables(con)
    z = con.execute(f"""SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO, aptos, comp, bio_nh,
                               tx_manual, tx_comp, z_manual, z_comp, n_mun, min_apos_fech
                        FROM z WHERE regiao = 'NE' AND aptos >= 100 AND n_mun >= 8
                          AND min_apos_fech BETWEEN -30 AND {max_min_apos}""").df()
    for c in ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]: z[c] = z[c].astype(int)
    z["k"] = z.apply(key, axis=1)
    susp = z[z.z_comp > 0].sort_values("z_manual", ascending=False).head(n_susp).copy()
    susp["grupo"] = "E_NE_suspeitas_horario_normal"; susp["ref"] = ""
    pool = z[~z.k.isin(set(susp.k))]
    ctrl = pool.sample(n=n_ctrl, random_state=seed).copy()
    ctrl["grupo"] = "F_NE_controle_horario_normal"; ctrl["ref"] = ""
    cols = ["grupo", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO",
            "aptos", "comp", "bio_nh", "tx_manual", "tx_comp", "z_manual", "z_comp", "min_apos_fech", "ref", "k"]
    am = pd.concat([susp, ctrl])[cols]
    am.to_csv(OUT / "00_amostra.csv", index=False)
    print(am.grupo.value_counts().to_string())
    print("universo NE no horário normal, aptos>=100:", len(z), "| suspeitas: z_manual de", round(susp.z_manual.min(), 2), "a", round(susp.z_manual.max(), 2),
          "| tx_manual mediana suspeitas", round(susp.tx_manual.median(), 3), "vs controles", round(ctrl.tx_manual.median(), 3))
    print(am.groupby("grupo").SG_UF.value_counts().unstack(fill_value=0).to_string())


def analisar():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    global GRUPOS, COR
    GRUPOS = sorted(pd.read_csv(OUT / "00_amostra.csv").grupo.unique()); COR = dict(zip(GRUPOS, PALETA))
    INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7",
                         "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                         "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
                         "font.size": 9, "axes.titlesize": 10, "axes.titlecolor": INK, "legend.frameon": False, "savefig.dpi": 150})
    s = pd.read_csv(OUT / "02_secoes_metricas.csv", parse_dates=["t_encerrar", "primeiro_voto", "ultimo_voto"])
    el = pd.read_csv(OUT / "01_eleitores.csv", parse_dates=["t_hab", "t_voto"])
    s["razao_manual_vs_votos_ult60"] = s.frac_manual_ult60 / s.frac_votos_ult60.replace(0, np.nan)
    s["razao_manual_vs_votos_apos"] = s.frac_manual_apos_fech_prev / s.frac_votos_apos_fech_prev.replace(0, np.nan)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)

    # resumo por grupo
    agg = {"k": "count", "log_votos": "sum", "log_manual": "sum", "modelo": lambda x: x.value_counts().to_dict(),
           "frac_votos_ult60": "median", "frac_manual_ult60": "median", "razao_manual_vs_votos_ult60": "median",
           "frac_votos_apos_fech_prev": "median", "frac_manual_apos_fech_prev": "median",
           "min_enc_apos_fech_prev": "median", "min_ultimo_voto_antes_enc": "median",
           "dur_mediana_s": "median", "dur_mediana_manual_s": "median", "gap_mediano_s": "median", "gap_mediano_ult60_s": "median",
           "max_run_manual": "max", "max_manual_15min": "max", "tent_media_manual": "median"}
    res = s.groupby("grupo").agg(agg).rename(columns={"k": "n_secoes"})
    # agregado ponderado: manuais na última hora / total de manuais, e votos na última hora / total de votos
    for g, d in s.groupby("grupo"):
        res.loc[g, "pond_frac_manual_ult60"] = d.manual_ult60.sum() / d.log_manual.sum()
        res.loc[g, "pond_frac_votos_ult60"] = d.votos_ult60.sum() / d.log_votos.sum()
        res.loc[g, "pond_frac_manual_apos"] = d.n_manual_apos_fech_prev.sum() / d.log_manual.sum()
        res.loc[g, "pond_frac_votos_apos"] = d.n_votos_apos_fech_prev.sum() / d.log_votos.sum()
    res = res.round(3); res.to_csv(OUT / "03_resumo_grupos.csv"); print(res.T.to_string())

    # perfil horário: manuais e votos por hora do dia (minutos antes do encerramento), por grupo
    el["h"] = el.t_hab.dt.hour + el.t_hab.dt.minute / 60
    el["min_antes_enc_bin"] = (el.min_antes_enc // 30 * 30).clip(upper=540)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for g in GRUPOS:
        d = el[el.grupo == g]
        if d.empty: continue
        for ax, (col, lab) in zip(axes, [("h", "hora local da habilitação"), ("min_antes_enc", "minutos antes do encerramento da urna")]):
            tot = d[col].dropna(); man = d.loc[d.tipo == "manual", col].dropna()
            bins = np.arange(7, 21.5, 0.5) if col == "h" else np.arange(0, 570, 30)
            ht, _ = np.histogram(tot, bins=bins); hm, _ = np.histogram(man, bins=bins)
            x = (bins[:-1] + bins[1:]) / 2
            ax.plot(x, ht / ht.sum(), color=COR[g], lw=1.6, label=f"{g} — todos os votos")
            ax.plot(x, hm / max(hm.sum(), 1), color=COR[g], lw=1.6, ls="--", label=f"{g} — habilitações manuais")
            ax.set_xlabel(lab)
    axes[0].set_ylabel("fração das habilitações (bins de 30 min)"); axes[1].invert_xaxis()
    axes[0].legend(fontsize=7, ncol=2); axes[0].set_title("Perfil ao longo do dia"); axes[1].set_title("Perfil relativo ao encerramento")
    fig.suptitle("Logs de urna: quando ocorrem as habilitações manuais vs todos os votos", color=INK)
    fig.tight_layout(); fig.savefig(OUT / "04_perfil_horario.png"); plt.close(fig)

    # scatter: fração de votos na última hora × fração de manuais na última hora
    fig, ax = plt.subplots(figsize=(6.5, 6))
    for g in GRUPOS:
        d = s[s.grupo == g]
        ax.scatter(d.frac_votos_ult60, d.frac_manual_ult60, s=28 if g[0] in "AB" else 12, color=COR[g],
                   alpha=0.85 if g[0] in "AB" else 0.5, label=f"{g} (n={len(d)})", edgecolors="white", linewidths=0.4)
    ax.plot([0, 0.6], [0, 0.6], color=MUTED, lw=0.9, ls="--"); ax.text(0.45, 0.47, "manual ∝ votos", color=MUTED, fontsize=8)
    ax.set_xlabel("fração de TODOS os votos na última hora antes do encerramento")
    ax.set_ylabel("fração das habilitações MANUAIS na última hora"); ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Se mesários 'votassem por ausentes' no fim, os pontos ficariam acima da diagonal")
    fig.tight_layout(); fig.savefig(OUT / "05_scatter_ultima_hora.png"); plt.close(fig)

    # small multiples do primeiro grupo (flagradas): as 40 com manuais mais concentradas no fim
    g0 = GRUPOS[0]
    A = s[s.grupo == g0].sort_values("razao_manual_vs_votos_ult60", ascending=False).head(40)
    n = len(A); ncol = 4; nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(15, 2.6 * nrow), sharex=True)
    for ax, (_, r) in zip(np.ravel(axes), A.iterrows()):
        d = el[el.k == r.k]; bins = np.arange(7, 21.5, 0.5)
        ax.hist(d.h, bins=bins, color="#9ec5f4", label="votos"); ax.hist(d.loc[d.tipo == "manual", "h"], bins=bins, color=COR[g0], label="manuais")
        if pd.notna(r.t_encerrar): ax.axvline(r.t_encerrar.hour + r.t_encerrar.minute / 60, color=INK, lw=0.9, ls="--")
        ax.set_title(f"{r.SG_UF} {r.NM_MUNICIPIO[:18]} z{r.NR_ZONA} s{r.NR_SECAO} — {r.modelo} — {r.log_manual}/{r.log_votos} manuais", fontsize=7.5)
        ax.set_xlim(7, 21)
    for ax in np.ravel(axes)[n:]: ax.axis("off")
    np.ravel(axes)[0].legend(fontsize=7)
    fig.suptitle(f"{g0}: votos (azul claro) e habilitações manuais por meia hora, {n} seções com manuais mais concentradas no fim; tracejado = encerramento", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.985)); fig.savefig(OUT / "06_timelines_flagradas.png"); plt.close(fig)

    # anomalias: manuais concentrados no fim, votos após o horário, sequências de manuais, votos rápidos no fim
    ctrl = s[s.grupo.str.contains("controle")]
    lim_razao = ctrl.razao_manual_vs_votos_ult60.quantile(0.95)
    lim_run = ctrl.max_run_manual.quantile(0.95); lim_15 = ctrl.max_manual_15min.quantile(0.95)
    lim_gap = ctrl.gap_mediano_ult60_s.quantile(0.05)
    s["anom_manual_fim"] = (s.razao_manual_vs_votos_ult60 > lim_razao) & (s.manual_ult60 >= 5)
    s["anom_run_manual"] = s.max_run_manual > lim_run
    s["anom_rajada_manual"] = s.max_manual_15min > lim_15
    s["anom_votos_rapidos_fim"] = (s.gap_mediano_ult60_s < lim_gap) & (s.votos_ult60 >= 10)
    s["anom_votos_apos_fech"] = s.frac_votos_apos_fech_prev > 0.10
    s["n_anom"] = s[[c for c in s.columns if c.startswith("anom_")]].sum(axis=1)
    lims = pd.DataFrame({"limite": ["razao_manual_vs_votos_ult60 p95 ctrl", "max_run_manual p95 ctrl", "max_manual_15min p95 ctrl", "gap_mediano_ult60_s p5 ctrl"],
                         "valor": [lim_razao, lim_run, lim_15, lim_gap]})
    lims.to_csv(OUT / "07_limites_anomalias.csv", index=False); print("\nlimites (controles):\n", lims.to_string(index=False))
    s.to_csv(OUT / "02_secoes_metricas.csv", index=False)
    cols = ["k", "grupo", "modelo", "bu_comp", "log_manual", "min_enc_apos_fech_prev", "min_ultimo_voto_antes_enc", "frac_votos_ult60",
            "frac_manual_ult60", "razao_manual_vs_votos_ult60", "frac_votos_apos_fech_prev", "max_run_manual", "max_manual_15min",
            "gap_mediano_s", "gap_mediano_ult60_s", "n_anom"]
    print("\n[anomalias por grupo]\n", s.groupby("grupo")[[c for c in s.columns if c.startswith("anom_")]].sum().to_string())
    an = s[s.n_anom > 0].sort_values(["n_anom", "razao_manual_vs_votos_ult60"], ascending=False)
    an[cols + [c for c in s.columns if c.startswith("anom_")]].to_csv(OUT / "08_secoes_com_anomalia.csv", index=False)
    print("\n[seções com alguma anomalia]\n", an[cols].to_string(index=False))
    for g in [g for g in GRUPOS if "controle" not in g]:
        d = s[s.grupo == g]
        print(f"\n[{g}: top 40 por razão manual/votos na última hora]\n", d.sort_values("razao_manual_vs_votos_ult60", ascending=False).head(40)[cols].to_string(index=False))
    print("\n[modelo × grupo]\n", pd.crosstab(s.grupo, s.modelo).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selecionar", "selecionar_ne", "baixar", "parsear", "analisar"])
    ap.add_argument("--out", default="out/logs", help="pasta da amostra/saídas (ex.: out/logs_ne)")
    a = ap.parse_args()
    OUT = Path(a.out)
    {"selecionar": selecionar, "selecionar_ne": selecionar_ne, "baixar": baixar, "parsear": parsear, "analisar": analisar}[a.cmd]()
