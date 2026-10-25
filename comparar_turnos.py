#!/usr/bin/env python3
"""
Comparação 1º × 2º turno, seção a seção e urna a urna.

  python comparar_turnos.py bu   [--db1 data/bu2026.duckdb] [--db2 data/2t/bu2026_2t.duckdb] [--out out/2t/comparacao]
  python comparar_turnos.py logs [--p1 out/logs_brasil/secoes_logs_brasil.parquet] [--p2 out/2t/logs_brasil/secoes_logs_brasil.parquet]
                                 [--l1 out/logs_brasil/06_locais_razao_duracao.parquet] [--l2 out/2t/logs_brasil/06_locais_razao_duracao.parquet]

Predições registradas antes dos dados do 2º turno (docs/ESCOPO_2T.md, seção 4); este script só calcula e marca.
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd, duckdb
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import pipeline_bu as pb

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
                     "axes.titlecolor": INK, "legend.frameon": False, "savefig.dpi": 150})
COR_T = {"1t": "#2a78d6", "2t": "#eb6834"}
REG_ORDEM = ["N", "NE", "CO", "SE", "S"]
FECH_CASE = " ".join(f"WHEN '{u}' THEN TIME '{h}'" for u, h in pb.FECH_LOCAL.items())
REG_CASE = " ".join(f"WHEN '{u}' THEN '{r}'" for u, r in pb.REGIAO.items())


def secao_sql(cat):
    """Uma linha por seção apurada do catálogo `cat` (t1 ou t2), com as mesmas definições de pipeline_bu.build_tables."""
    return f"""
    WITH s AS (
      SELECT DISTINCT SG_UF, CAST(CD_MUNICIPIO AS INT) CD_MUNICIPIO, NM_MUNICIPIO, CAST(NR_ZONA AS INT) NR_ZONA,
             CAST(NR_SECAO AS INT) NR_SECAO, CAST(NR_LOCAL_VOTACAO AS INT) NR_LOCAL_VOTACAO, NR_URNA_EFETIVADA,
             CAST(QT_APTOS AS INT) aptos, CAST(QT_COMPARECIMENTO AS INT) comp, CAST(QT_ABSTENCOES AS INT) abst,
             CAST(QT_ELEI_BIOM_SEM_HABILITACAO AS INT) bio_nh,
             CAST(TRY_CAST(DT_ENCERRAMENTO AS TIMESTAMP) AS TIME) t_enc, CD_TIPO_URNA = '1' apurada
      FROM {cat}.bu WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%')
    SELECT *, comp*1.0/NULLIF(aptos,0) tx_comp, bio_nh*1.0/NULLIF(comp,0) tx_manual,
           date_diff('minute', CASE SG_UF {FECH_CASE} ELSE TIME '17:00:00' END, t_enc) min_apos_fech,
           CASE SG_UF {REG_CASE} ELSE '?' END regiao,
           TRY_CAST(NR_URNA_EFETIVADA AS BIGINT) < 2000000 serie_lo
    FROM s WHERE apurada"""


def votos_sql(cat):
    """Votos nominais para Presidente por seção e candidato, com o total de votos nominais da seção."""
    return f"""
    SELECT SG_UF, CAST(NR_ZONA AS INT) NR_ZONA, CAST(NR_SECAO AS INT) NR_SECAO, NR_VOTAVEL, NM_VOTAVEL,
           CAST(QT_VOTOS AS INT) votos, sum(CAST(QT_VOTOS AS INT)) OVER (PARTITION BY SG_UF, NR_ZONA, NR_SECAO) tot
    FROM {cat}.bu WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%' AND CD_TIPO_VOTAVEL = '1'"""


def comparar_bu(db1, db2, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"ATTACH '{Path(db1).as_posix()}' AS t1 (READ_ONLY); ATTACH '{Path(db2).as_posix()}' AS t2 (READ_ONLY)")
    con.execute(f"CREATE TABLE s1 AS {secao_sql('t1')}"); con.execute(f"CREATE TABLE s2 AS {secao_sql('t2')}")
    n1, n2 = con.execute("SELECT (SELECT count(*) FROM s1), (SELECT count(*) FROM s2)").fetchone()
    # pareamento por seção (UF, município, zona, seção)
    con.execute("""
        CREATE TABLE p AS
        SELECT s1.SG_UF, s1.regiao, s1.CD_MUNICIPIO, s1.NM_MUNICIPIO, s1.NR_ZONA, s1.NR_SECAO,
               s1.NR_LOCAL_VOTACAO loc_1t, s2.NR_LOCAL_VOTACAO loc_2t,
               s1.NR_URNA_EFETIVADA urna_1t, s2.NR_URNA_EFETIVADA urna_2t, s1.NR_URNA_EFETIVADA = s2.NR_URNA_EFETIVADA mesma_urna,
               s1.serie_lo serie_lo_1t, s2.serie_lo serie_lo_2t,
               s1.aptos aptos_1t, s2.aptos aptos_2t, s1.comp comp_1t, s2.comp comp_2t, s1.bio_nh manual_1t, s2.bio_nh manual_2t,
               s1.tx_comp tx_comp_1t, s2.tx_comp tx_comp_2t, s1.tx_manual tx_manual_1t, s2.tx_manual tx_manual_2t,
               s1.min_apos_fech enc_1t, s2.min_apos_fech enc_2t,
               s2.tx_manual - s1.tx_manual d_manual, s2.tx_comp - s1.tx_comp d_comp, s2.min_apos_fech - s1.min_apos_fech d_enc
        FROM s1 JOIN s2 USING (SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO)""")
    npar, nurna = con.execute("SELECT count(*), sum(mesma_urna::INT) FROM p").fetchone()
    so1 = con.execute("SELECT count(*) FROM s1 ANTI JOIN s2 USING (SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO)").fetchone()[0]
    so2 = con.execute("SELECT count(*) FROM s2 ANTI JOIN s1 USING (SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO)").fetchone()[0]
    print(f"[pareamento] 1t {n1:,} seções, 2t {n2:,}; pareadas {npar:,}; só 1t {so1:,}; só 2t {so2:,}; mesma urna física {nurna:,} ({100*nurna/npar:.1f}%)".replace(",", "."))
    pd.DataFrame([dict(secoes_1t=n1, secoes_2t=n2, pareadas=npar, so_1t=so1, so_2t=so2, mesma_urna=nurna)]).to_csv(out / "20_pareamento.csv", index=False)

    # 20. por UF e região
    agg = """count(*) n, round(avg(tx_manual_1t),4) manual_1t, round(avg(tx_manual_2t),4) manual_2t,
             round(avg(tx_comp_1t),4) comp_1t, round(avg(tx_comp_2t),4) comp_2t,
             round(quantile_cont(enc_1t,0.5),1) enc_med_1t, round(quantile_cont(enc_2t,0.5),1) enc_med_2t,
             round(100.0*avg((enc_1t>30)::INT),2) pct_tardia_1t, round(100.0*avg((enc_2t>30)::INT),2) pct_tardia_2t,
             round(100.0*avg(mesma_urna::INT),1) pct_mesma_urna"""
    uf = con.execute(f"SELECT SG_UF, regiao, {agg} FROM p GROUP BY 1,2 ORDER BY 2,1").df(); uf.to_csv(out / "20_uf.csv", index=False)
    reg = con.execute(f"SELECT regiao, {agg} FROM p WHERE regiao <> 'ZZ' GROUP BY 1 ORDER BY 1").df(); reg.to_csv(out / "20_regioes.csv", index=False)
    nac = con.execute(f"SELECT 'BR' regiao, {agg} FROM p WHERE regiao <> 'ZZ'").df()
    print("\n[20] regiões:\n", pd.concat([reg, nac]).to_string(index=False))

    # 21. todas as seções pareadas
    con.execute(f"COPY p TO '{(out / '21_secoes.parquet').as_posix()}' (FORMAT PARQUET)")

    # 22. persistência da taxa manual (hardware): mesma urna física × urna diferente
    pers = con.execute("""
        SELECT SG_UF, regiao, count(*) n,
               round(corr(tx_manual_1t, tx_manual_2t),3) corr_manual,
               round(corr(tx_manual_1t, tx_manual_2t) FILTER (WHERE mesma_urna),3) corr_mesma_urna,
               round(corr(tx_manual_1t, tx_manual_2t) FILTER (WHERE NOT mesma_urna),3) corr_urna_diferente,
               sum(mesma_urna::INT) n_mesma_urna,
               round(corr(tx_comp_1t, tx_comp_2t),3) corr_comp, round(corr(enc_1t, enc_2t),3) corr_enc
        FROM p WHERE regiao <> 'ZZ' AND aptos_1t >= 100 GROUP BY 1,2 ORDER BY 2,1""").df()
    pers.to_csv(out / "22_persistencia_uf.csv", index=False)
    pers_br = con.execute("""
        SELECT serie_lo_1t serie_antiga, mesma_urna, count(*) n, round(corr(tx_manual_1t, tx_manual_2t),3) corr_manual,
               round(avg(tx_manual_1t),4) manual_1t, round(avg(tx_manual_2t),4) manual_2t
        FROM p WHERE regiao <> 'ZZ' AND aptos_1t >= 100 GROUP BY 1,2 ORDER BY 1,2""").df()
    pers_br.to_csv(out / "22_persistencia_serie.csv", index=False)
    print("\n[22] persistência da taxa manual por série da urna × mesma urna:\n", pers_br.to_string(index=False))

    # 23. flag de variação conjunta: manual E comparecimento sobem juntos, muito acima do município
    con.execute("""
        CREATE TABLE zd AS
        SELECT *, (d_manual - avg(d_manual) OVER w)/NULLIF(stddev(d_manual) OVER w,0) z_dmanual,
                  (d_comp   - avg(d_comp)   OVER w)/NULLIF(stddev(d_comp)   OVER w,0) z_dcomp,
                  count(*) OVER w n_mun
        FROM p WHERE regiao <> 'ZZ' AND aptos_1t >= 100 AND aptos_2t >= 100
        WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO)""")
    fl = con.execute("""SELECT * FROM zd WHERE n_mun >= 8 AND z_dmanual > 3 AND z_dcomp > 2 ORDER BY z_dmanual DESC""").df()
    fl.to_csv(out / "23_flag_delta.csv", index=False)
    con.execute("ALTER TABLE zd ADD COLUMN flag_delta BOOLEAN; UPDATE zd SET flag_delta = coalesce(n_mun>=8 AND z_dmanual>3 AND z_dcomp>2, FALSE)")
    fl_uf = con.execute("""SELECT SG_UF, regiao, count(*) n, sum(flag_delta::INT) flag_delta,
                                  round(1000.0*sum(flag_delta::INT)/count(*),3) por_mil
                           FROM zd GROUP BY 1,2 ORDER BY por_mil DESC""").df()
    fl_uf.to_csv(out / "23_flag_delta_uf.csv", index=False)
    print(f"\n[23] seções com Δmanual > 3σ E Δcomparecimento > 2σ no município: {len(fl)}\n", fl_uf.head(12).to_string(index=False))

    # 24. predições registradas (docs/ESCOPO_2T.md §4)
    r = reg.set_index("regiao"); b = nac.iloc[0]
    tem_ne_s = {"NE", "S"} <= set(r.index)
    pred = [
        dict(id="P1", predicao="tempo de cédula menor -> encerramento tardio (>30 min) cai em TODAS as regiões",
             valor=f"{', '.join(f'{k}: {r.loc[k,'pct_tardia_1t']:.1f}%→{r.loc[k,'pct_tardia_2t']:.1f}%' for k in REG_ORDEM if k in r.index)}",
             ok=bool(all(r.loc[k, "pct_tardia_2t"] < r.loc[k, "pct_tardia_1t"] for k in REG_ORDEM if k in r.index))),
        dict(id="P2", predicao="NE e N continuam fechando mais tarde que o Sul (mediana), mas a diferença absoluta encolhe",
             valor=(f"NE−S mediana: {r.loc['NE','enc_med_1t']-r.loc['S','enc_med_1t']:.1f} → {r.loc['NE','enc_med_2t']-r.loc['S','enc_med_2t']:.1f} min"
                    if tem_ne_s else "n/d (faltam NE ou S)"),
             ok=bool(0 < r.loc["NE", "enc_med_2t"] - r.loc["S", "enc_med_2t"] < r.loc["NE", "enc_med_1t"] - r.loc["S", "enc_med_1t"]) if tem_ne_s else None),
        dict(id="P3", predicao="taxa manual nacional estável (±1,5 pp): é propriedade do leitor e do eleitorado, não do dia",
             valor=f"{100*b.manual_1t:.2f}% → {100*b.manual_2t:.2f}%", ok=bool(abs(b.manual_2t - b.manual_1t) <= 0.015)),
        dict(id="P4", predicao="taxa manual persiste na mesma urna física: corr(1t,2t) > 0,5 em urnas mantidas, e maior que em urnas trocadas",
             valor=f"mesma urna {pers_br[pers_br.mesma_urna==True].corr_manual.mean():.3f}; trocada {pers_br[pers_br.mesma_urna==False].corr_manual.mean():.3f}",
             ok=bool(pers_br[pers_br.mesma_urna == True].corr_manual.mean() > 0.5 and
                     pers_br[pers_br.mesma_urna == True].corr_manual.mean() > pers_br[pers_br.mesma_urna == False].corr_manual.mean())),
        dict(id="P5", predicao="seções com Δmanual e Δcomparecimento conjuntamente anômalos: ≤ 0,2‰ e sem concentração regional (nenhuma região > 2× a média)",
             valor=f"{len(fl)} seções; por mil por região: " + ", ".join(f"{k}: {v:.3f}" for k, v in
                   con.execute("SELECT regiao, 1000.0*sum(flag_delta::INT)/count(*) FROM zd GROUP BY 1 ORDER BY 1").fetchall()),
             ok=None),
    ]
    pred = pd.DataFrame(pred); pred.to_csv(out / "24_predicoes.csv", index=False)
    print("\n[24] predições:\n", pred.to_string(index=False))

    # 25. votos: variação da fatia dos finalistas × variação da taxa manual, intra-município
    con.execute(f"CREATE TABLE v1 AS {votos_sql('t1')}"); con.execute(f"CREATE TABLE v2 AS {votos_sql('t2')}")
    fin = con.execute("SELECT NR_VOTAVEL, any_value(NM_VOTAVEL) nm FROM v2 GROUP BY 1 ORDER BY 1").df()
    print("\n[25] votáveis no 2t (Presidente):", ", ".join(f"{r.NR_VOTAVEL} {r.nm}" for r in fin.itertuples()))
    con.execute("""
        CREATE TABLE sh AS
        SELECT p.SG_UF, p.regiao, p.CD_MUNICIPIO, p.NR_ZONA, p.NR_SECAO, v2.NR_VOTAVEL, v2.NM_VOTAVEL,
               v1.votos*1.0/NULLIF(v1.tot,0) share_1t, v2.votos*1.0/NULLIF(v2.tot,0) share_2t,
               v2.votos*1.0/NULLIF(v2.tot,0) - v1.votos*1.0/NULLIF(v1.tot,0) d_share, p.d_manual, p.d_comp
        FROM p JOIN v2 USING (SG_UF, NR_ZONA, NR_SECAO) LEFT JOIN v1 USING (SG_UF, NR_ZONA, NR_SECAO, NR_VOTAVEL)
        WHERE p.regiao <> 'ZZ' AND p.aptos_1t >= 100""")
    cv = con.execute("""
        WITH d AS (SELECT *, d_share - avg(d_share) OVER w dd_share, d_manual - avg(d_manual) OVER w dd_manual, d_comp - avg(d_comp) OVER w dd_comp
                   FROM sh WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO, NR_VOTAVEL))
        SELECT SG_UF, regiao, NR_VOTAVEL, any_value(NM_VOTAVEL) candidato, count(*) n,
               round(corr(d_manual, d_share),3) corr_dmanual_dshare, round(corr(dd_manual, dd_share),3) corr_intra_mun,
               round(corr(d_comp, d_share),3) corr_dcomp_dshare
        FROM d GROUP BY 1,2,3 ORDER BY 2,1,3""").df()
    cv.to_csv(out / "25_votos_delta_uf.csv", index=False)
    print("\n[25] corr(Δmanual, Δfatia) por UF e candidato (bruta e intra-município):\n", cv.to_string(index=False))

    # gráficos
    fig, axes = plt.subplots(1, 2, figsize=(11, 6.5), sharey=True)
    u = uf[uf.regiao != "ZZ"].sort_values(["regiao", "SG_UF"]).reset_index(drop=True); y = np.arange(len(u))
    for ax, (c1, c2, tit, fmt) in zip(axes, [("manual_1t", "manual_2t", "taxa de habilitação manual (média das seções)", lambda v: f"{100*v:.1f}%"),
                                          ("pct_tardia_1t", "pct_tardia_2t", "% de seções encerradas > 30 min após o horário local", lambda v: f"{v:.0f}%")]):
        ax.hlines(y, u[c1], u[c2], color=GRID, lw=2)
        ax.scatter(u[c1], y, color=COR_T["1t"], s=28, zorder=3, label="1º turno"); ax.scatter(u[c2], y, color=COR_T["2t"], s=28, zorder=3, label="2º turno")
        ax.set_yticks(y); ax.set_yticklabels(u.SG_UF + "  " + u.regiao); ax.set_title(tit); ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _, f=fmt: f(v)))
    axes[0].legend(loc="lower right"); fig.suptitle("1º × 2º turno por UF", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(out / "20a_uf_1t_vs_2t.png"); plt.close(fig)

    d = con.execute("SELECT regiao, d_manual, d_comp FROM zd USING SAMPLE 60000").df()
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    cor = dict(zip(REG_ORDEM, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
    for rg in REG_ORDEM:
        dd = d[d.regiao == rg]; ax.scatter(dd.d_comp, dd.d_manual, s=4, alpha=0.25, color=cor[rg], label=f"{rg} ({len(dd):,})".replace(",", "."), rasterized=True)
    if len(fl): ax.scatter(fl.d_comp, fl.d_manual, s=30, facecolors="none", edgecolors=INK, lw=0.9, label=f"flag Δ ({len(fl)})", zorder=4)
    ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Δ comparecimento (2t − 1t), fração dos aptos"); ax.set_ylabel("Δ taxa de habilitação manual (2t − 1t)")
    ax.set_title("Variação conjunta de comparecimento e habilitação manual, por seção (amostra de 60 mil)")
    ax.legend(markerscale=3, loc="upper left"); fig.tight_layout(); fig.savefig(out / "23a_scatter_delta.png", dpi=170); plt.close(fig)
    print(f"\nsaídas em {out}/")


def comparar_logs(p1, p2, l1, l2, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE TABLE a AS SELECT * FROM '{Path(p1).as_posix()}'"); con.execute(f"CREATE TABLE b AS SELECT * FROM '{Path(p2).as_posix()}'")
    con.execute("CREATE TABLE j AS SELECT a.k, a.SG_UF, a.regiao, a.CD_MUNICIPIO, a.NR_ZONA, a.NR_SECAO, a.NR_LOCAL_VOTACAO, a.modelo modelo_1t, b.modelo modelo_2t, "
                "a.log_votos v_1t, b.log_votos v_2t, a.log_manual m_1t, b.log_manual m_2t, a.log_bio bio_1t, b.log_bio bio_2t, "
                "a.dur_mediana_s dur_1t, b.dur_mediana_s dur_2t, a.gap_mediano_s gap_1t, b.gap_mediano_s gap_2t, "
                "a.min_enc_apos_fech_prev enc_1t, b.min_enc_apos_fech_prev enc_2t, "
                "a.razao_dur_manual_bio rz_1t, b.razao_dur_manual_bio rz_2t, a.frac_manual_ult60/NULLIF(a.frac_votos_ult60,0) fim_1t, "
                "b.frac_manual_ult60/NULLIF(b.frac_votos_ult60,0) fim_2t, a.pct_manual_lt30 lt30_1t, b.pct_manual_lt30 lt30_2t "
                "FROM a JOIN b USING (k)")
    n = con.execute("SELECT count(*), (SELECT count(*) FROM a), (SELECT count(*) FROM b) FROM j").fetchone()
    print(f"[logs] urnas pareadas {n[0]:,} (1t {n[1]:,}, 2t {n[2]:,})".replace(",", "."))
    # 30. modelo e tempo
    mo = con.execute("""SELECT modelo_2t modelo, count(*) n, round(avg(m_1t*1.0/NULLIF(v_1t,0)),4) manual_1t, round(avg(m_2t*1.0/NULLIF(v_2t,0)),4) manual_2t,
                               round(quantile_cont(dur_1t,0.5),1) dur_1t, round(quantile_cont(dur_2t,0.5),1) dur_2t,
                               round(avg(enc_1t),1) enc_1t, round(avg(enc_2t),1) enc_2t
                        FROM j WHERE modelo_1t = modelo_2t GROUP BY 1 ORDER BY 1""").df()
    mo.to_csv(out / "30_modelo.csv", index=False); print("\n[30] por modelo (urnas que mantiveram o modelo):\n", mo.to_string(index=False))
    tu = con.execute("""SELECT SG_UF, regiao, count(*) n, round(quantile_cont(dur_1t,0.5),1) dur_1t, round(quantile_cont(dur_2t,0.5),1) dur_2t,
                               round(quantile_cont(gap_1t,0.5),1) gap_1t, round(quantile_cont(gap_2t,0.5),1) gap_2t,
                               round(quantile_cont(enc_1t,0.5),1) enc_1t, round(quantile_cont(enc_2t,0.5),1) enc_2t,
                               round(quantile_cont(fim_1t,0.5),2) fim_1t, round(quantile_cont(fim_2t,0.5),2) fim_2t
                        FROM j GROUP BY 1,2 ORDER BY 2,1""").df()
    tu.to_csv(out / "30_uf_tempo.csv", index=False); print("\n[30] tempo por voto e encerramento por UF:\n", tu.to_string(index=False))
    # 31. razão de duração por local: 1t × 2t
    con.execute(f"CREATE TABLE la AS SELECT * FROM '{Path(l1).as_posix()}'"); con.execute(f"CREATE TABLE lb AS SELECT * FROM '{Path(l2).as_posix()}'")
    # local de votação é único dentro da zona (o número se repete entre zonas do mesmo município)
    con.execute("""CREATE TABLE lj AS SELECT la.SG_UF, la.CD_MUNICIPIO, la.NR_ZONA, la.NR_LOCAL_VOTACAO, la.NM_MUNICIPIO, la.n_manual nm_1t, lb.n_manual nm_2t,
                   la.razao razao_1t, lb.razao razao_2t FROM la JOIN lb USING (SG_UF, CD_MUNICIPIO, NR_ZONA, NR_LOCAL_VOTACAO)""")
    q1 = con.execute("SELECT quantile_cont(razao_1t,0.001), quantile_cont(razao_2t,0.001), corr(razao_1t, razao_2t), count(*) FROM lj WHERE nm_1t>=30 AND nm_2t>=30").fetchone()
    print(f"\n[31] locais pareados {q1[3]:,}: p0,1 razão 1t {q1[0]:.3f}, 2t {q1[1]:.3f}; corr(1t,2t) {q1[2]:.3f}".replace(",", "."))
    flag1 = con.execute(f"SELECT * FROM lj WHERE nm_1t >= 30 AND razao_1t < {q1[0]} ORDER BY razao_1t").df()
    flag1["repete_2t"] = flag1.razao_2t < q1[1]
    flag1.to_csv(out / "31_locais_flagrados_1t_no_2t.csv", index=False)
    print(f"[31] locais flagrados no 1t: {len(flag1)}; repetem abaixo do p0,1 no 2t: {int(flag1.repete_2t.sum())} "
          f"(esperado por acaso ≈ {0.001*len(flag1):.2f})")
    alvo = con.execute("SELECT * FROM lj WHERE SG_UF='MA' AND CD_MUNICIPIO IN (7285, 7927) ORDER BY CD_MUNICIPIO, razao_1t").df()
    alvo.to_csv(out / "31_bom_lugar_maranhaozinho.csv", index=False); print("\n[31] Bom Lugar (7285) e Maranhãozinho (7927), por local:\n", alvo.to_string(index=False))
    # 32. persistência por urna
    pu = con.execute("""SELECT regiao, count(*) n, round(corr(rz_1t, rz_2t),3) corr_razao_dur, round(corr(fim_1t, fim_2t),3) corr_manual_fim,
                               round(corr(m_1t*1.0/NULLIF(v_1t,0), m_2t*1.0/NULLIF(v_2t,0)),3) corr_tx_manual
                        FROM j WHERE m_1t >= 10 AND bio_1t >= 10 AND m_2t >= 10 AND bio_2t >= 10 GROUP BY 1 ORDER BY 1""").df()
    pu.to_csv(out / "32_persistencia_urna.csv", index=False); print("\n[32] persistência por urna (≥10 manuais e ≥10 biométricos nos dois turnos):\n", pu.to_string(index=False))
    # 33. predições
    pred = pd.DataFrame([
        dict(id="L1", predicao="duração mediana do voto cai em todas as UFs (cédula de 1–2 cargos contra 5–6)",
             valor=f"{int((tu.dur_2t < tu.dur_1t).sum())}/{len(tu)} UFs", ok=bool((tu.dur_2t < tu.dur_1t).all())),
        dict(id="L2", predicao="ordem das UFs por tempo de voto se mantém (MA/PI/PA no topo): corr de postos > 0,7",
             valor=f"{tu.dur_1t.rank().corr(tu.dur_2t.rank()):.3f}", ok=bool(tu.dur_1t.rank().corr(tu.dur_2t.rank()) > 0.7)),
        dict(id="L3", predicao="taxa manual por modelo se repete (UE2013 > UE2015 > UE2020 ≈ UE2022), diferença por modelo < 2 pp",
             valor=", ".join(f"{r.modelo}: {100*r.manual_1t:.1f}%→{100*r.manual_2t:.1f}%" for r in mo.itertuples()),
             ok=bool((abs(mo.manual_2t - mo.manual_1t) < 0.02).all())),
        dict(id="L4", predicao="manuais no fim da sessão continuam sem concentração: mediana da razão manual/votos na última hora ≤ 1 por UF",
             valor=f"{int((tu.fim_2t <= 1).sum())}/{len(tu)} UFs", ok=bool((tu.fim_2t <= 1).all())),
        dict(id="L5", predicao="Bom Lugar: se o padrão é operacional/estável, os locais 1104, 1120, 1198, 1171 repetem razão < 0,8; se foi do dia, voltam a > 1",
             valor="; ".join(f"{int(r.NR_LOCAL_VOTACAO)}: {r.razao_1t:.2f}→{r.razao_2t:.2f}" for r in alvo[alvo.CD_MUNICIPIO == 7285].itertuples()), ok=None),
    ])
    pred.to_csv(out / "33_predicoes_logs.csv", index=False); print("\n[33] predições (logs):\n", pred.to_string(index=False))
    print(f"\nsaídas em {out}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bu", "logs"])
    ap.add_argument("--db1", default="data/bu2026.duckdb"); ap.add_argument("--db2", default="data/2t/bu2026_2t.duckdb")
    ap.add_argument("--p1", default="out/logs_brasil/secoes_logs_brasil.parquet"); ap.add_argument("--p2", default="out/2t/logs_brasil/secoes_logs_brasil.parquet")
    ap.add_argument("--l1", default="out/logs_brasil/06_locais_razao_duracao.parquet"); ap.add_argument("--l2", default="out/2t/logs_brasil/06_locais_razao_duracao.parquet")
    ap.add_argument("--out", default="out/2t/comparacao")
    a = ap.parse_args()
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
    if a.cmd == "bu": comparar_bu(a.db1, a.db2, a.out)
    else: comparar_logs(a.p1, a.p2, a.l1, a.l2, a.out)
