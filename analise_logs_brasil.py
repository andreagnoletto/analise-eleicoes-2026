#!/usr/bin/env python3
"""
Análise nacional dos logs de urna (saída de logs_brasil.py em data/logs_parquet/).
  python analise_logs_brasil.py --out out/logs_brasil
Critérios "tipo Bom Lugar": eleitores habilitados manualmente votando muito mais rápido que os biométricos
da mesma urna, agregando por local de votação. Limites vêm da distribuição nacional (quantis), estratificada por modelo.
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd, duckdb
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import pipeline_bu as pb
import config as cfg

PQ = cfg.PQ.as_posix()
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
                     "axes.titlecolor": INK, "legend.frameon": False, "savefig.dpi": 150})
REG_ORDEM = ["N", "NE", "CO", "SE", "S", "ZZ"]
COR_REG = dict(zip(REG_ORDEM, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    reg_case = " ".join(f"WHEN '{u}' THEN '{r}'" for u, r in pb.REGIAO.items())
    con.execute(f"""CREATE TABLE s_all AS SELECT *, CASE SG_UF {reg_case} END regiao,
                    log_manual*1.0/NULLIF(log_votos,0) tx_manual, frac_manual_ult60/NULLIF(frac_votos_ult60,0) razao_manual_fim,
                    tx_manual_14_17 - tx_manual_8_11 salto_manual_tarde
                    FROM '{PQ}/secoes_*.parquet'""")
    # ZZ (exterior) não tem biometria e vota só para presidente: fica só na validação
    con.execute("CREATE TABLE s AS SELECT * FROM s_all WHERE SG_UF <> 'ZZ'")
    ufs = [r[0] for r in con.execute("SELECT DISTINCT SG_UF FROM s_all ORDER BY 1").fetchall()]
    n = con.execute("SELECT count(*) FROM s").fetchone()[0]
    print(f"[dados] {n} urnas, {len(ufs)} UFs: {' '.join(ufs)}")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)

    # 1. validação contra o BU
    v = con.execute("""SELECT SG_UF, count(*) n, sum(log_votos = bu_comp) comp_bate, sum(log_manual = bu_bio_nh) manual_bate,
                       sum(abs(log_manual - bu_bio_nh) <= 1) manual_bate_1, sum(modelo IS NULL) sem_modelo, sum(t_encerrar IS NULL) sem_encerramento
                       FROM s_all GROUP BY 1 ORDER BY 1""").df()
    v.to_csv(out / "01_validacao_uf.csv", index=False); print("\n[1] validação:\n", v.to_string(index=False))

    # 2. modelo × UF: taxa manual (falha do leitor)
    m = con.execute("""SELECT SG_UF, regiao, modelo, count(*) n, round(avg(tx_manual),4) tx_manual_media,
                       round(100.0*avg((tx_manual >= 0.5)::INT),2) pct_urnas_manual_ge50, round(avg(dur_mediana_s),1) dur_voto_s
                       FROM s GROUP BY 1,2,3 ORDER BY 3,1""").df()
    m.to_csv(out / "02_modelo_uf.csv", index=False)
    mn = con.execute("""SELECT modelo, count(*) n, round(avg(tx_manual),4) tx_manual_media, round(100.0*avg((tx_manual >= 0.5)::INT),2) pct_urnas_manual_ge50,
                        round(avg(dur_mediana_s),1) dur_voto_s, round(avg(min_enc_apos_fech_prev),1) min_apos_fech FROM s GROUP BY 1 ORDER BY 1""").df()
    mn.to_csv(out / "02_modelo_nacional.csv", index=False); print("\n[2] por modelo:\n", mn.to_string(index=False))

    # 3. tempo por voto e encerramento por UF
    t = con.execute("""SELECT SG_UF, regiao, count(*) n, round(quantile_cont(dur_mediana_s,0.5),1) dur_voto_mediana_s,
                       round(quantile_cont(gap_mediano_s,0.5),1) gap_entre_votos_s, round(avg(bu_comp),1) comp_medio,
                       round(quantile_cont(min_enc_apos_fech_prev,0.5),1) min_enc_mediana, round(100.0*avg((min_enc_apos_fech_prev > 30)::INT),1) pct_tardia,
                       round(avg(tx_manual),4) tx_manual, round(avg(dur_manual_med_s),1) dur_manual_s, round(avg(dur_bio_med_s),1) dur_bio_s
                       FROM s GROUP BY 1,2 ORDER BY dur_voto_mediana_s DESC""").df()
    t.to_csv(out / "03_tempo_voto_uf.csv", index=False); print("\n[3] tempo por voto:\n", t.to_string(index=False))

    # 4. distribuições nacionais das métricas de anomalia (quantis), por modelo para a razão de duração
    q = con.execute("""SELECT 'razao_dur_manual_bio' metrica, quantile_cont(razao_dur_manual_bio,[0.001,0.01,0.05,0.5,0.95,0.99,0.999]) q, count(razao_dur_manual_bio) n FROM s WHERE log_manual >= 10 AND log_bio >= 10
                       UNION ALL SELECT 'razao_manual_fim', quantile_cont(razao_manual_fim,[0.001,0.01,0.05,0.5,0.95,0.99,0.999]), count(razao_manual_fim) FROM s WHERE manual_ult60 >= 5
                       UNION ALL SELECT 'gap_mediano_ult60_s', quantile_cont(gap_mediano_ult60_s,[0.001,0.01,0.05,0.5,0.95,0.99,0.999]), count(gap_mediano_ult60_s) FROM s WHERE votos_ult60 >= 10
                       UNION ALL SELECT 'salto_manual_tarde', quantile_cont(salto_manual_tarde,[0.001,0.01,0.05,0.5,0.95,0.99,0.999]), count(salto_manual_tarde) FROM s
                       UNION ALL SELECT 'pct_manual_lt30', quantile_cont(pct_manual_lt30,[0.001,0.01,0.05,0.5,0.95,0.99,0.999]), count(pct_manual_lt30) FROM s WHERE log_manual >= 10""").df()
    q = pd.concat([q.drop(columns="q"), pd.DataFrame(q.q.tolist(), columns=["p0.1", "p1", "p5", "p50", "p95", "p99", "p99.9"]).round(3)], axis=1)
    q.to_csv(out / "04_quantis_nacionais.csv", index=False); print("\n[4] quantis:\n", q.to_string(index=False))
    lim = dict(zip(q.metrica, q["p0.1"])); lim_hi = dict(zip(q.metrica, q["p99.9"]))

    # 5. urnas flagradas (critérios independentes, limites = 0,1% nacional)
    con.execute(f"""CREATE TABLE f AS SELECT *,
        (log_manual >= 10 AND log_bio >= 10 AND razao_dur_manual_bio < {lim['razao_dur_manual_bio']}) f_manual_rapido,
        (manual_ult60 >= 5 AND razao_manual_fim > {lim_hi['razao_manual_fim']}) f_manual_fim,
        (votos_ult60 >= 10 AND gap_mediano_ult60_s < {lim['gap_mediano_ult60_s']}) f_votos_rapidos_fim,
        (salto_manual_tarde > {lim_hi['salto_manual_tarde']}) f_leitor_degrada_tarde,
        (log_manual >= 10 AND pct_manual_lt30 > {lim_hi['pct_manual_lt30']}) f_manual_lt30
        FROM s""")
    fl = con.execute("""SELECT * FROM f WHERE f_manual_rapido OR f_manual_fim OR f_votos_rapidos_fim OR f_leitor_degrada_tarde OR f_manual_lt30
                        ORDER BY razao_dur_manual_bio""").df()
    fl.to_csv(out / "05_urnas_flagradas.csv", index=False)
    cnt = con.execute("""SELECT regiao, count(*) n, sum(f_manual_rapido::INT) manual_rapido, sum(f_manual_fim::INT) manual_fim, sum(f_votos_rapidos_fim::INT) votos_rapidos_fim,
                         sum(f_leitor_degrada_tarde::INT) leitor_degrada_tarde, sum(f_manual_lt30::INT) manual_lt30 FROM f GROUP BY 1 ORDER BY 1""").df()
    cnt.to_csv(out / "05_flags_por_regiao.csv", index=False); print("\n[5] flags por região:\n", cnt.to_string(index=False))
    cu = con.execute("""SELECT SG_UF, count(*) n, sum(f_manual_rapido::INT) manual_rapido, round(1000.0*avg(f_manual_rapido::INT),2) manual_rapido_por_mil,
                        sum(f_manual_fim::INT) manual_fim, sum(f_votos_rapidos_fim::INT) votos_rapidos_fim, sum(f_leitor_degrada_tarde::INT) leitor_degrada_tarde
                        FROM f GROUP BY 1 ORDER BY manual_rapido_por_mil DESC""").df()
    cu.to_csv(out / "05_flags_por_uf.csv", index=False)

    # 6. por local de votação: razão de duração agregada (medianas sobre todos os eleitores do local)
    con.execute(f"""CREATE TABLE loc AS
        WITH e AS (SELECT e.k, e.tipo, e.dur_s, s.SG_UF, s.CD_MUNICIPIO, s.NR_ZONA, s.NR_LOCAL_VOTACAO
                   FROM '{PQ}/eleitores_*.parquet' e JOIN s USING (k) WHERE e.dur_s IS NOT NULL AND e.tipo IN ('manual','biometrica'))
        SELECT SG_UF, CD_MUNICIPIO, NR_ZONA, NR_LOCAL_VOTACAO, count(DISTINCT k) urnas,
               sum((tipo='manual')::INT) n_manual, sum((tipo='biometrica')::INT) n_bio,
               quantile_cont(dur_s, 0.5) FILTER (WHERE tipo='manual') dur_manual_s,
               quantile_cont(dur_s, 0.5) FILTER (WHERE tipo='biometrica') dur_bio_s,
               avg((dur_s < 30)::INT) FILTER (WHERE tipo='manual') pct_manual_lt30,
               avg((dur_s < 30)::INT) FILTER (WHERE tipo='biometrica') pct_bio_lt30
        FROM e GROUP BY 1,2,3,4""")
    con.execute("ALTER TABLE loc ADD COLUMN razao DOUBLE; UPDATE loc SET razao = dur_manual_s / NULLIF(dur_bio_s,0)")
    ql = con.execute("SELECT quantile_cont(razao,[0.001,0.01,0.5]) FROM loc WHERE n_manual >= 30 AND n_bio >= 30").fetchone()[0]
    print(f"\n[6] locais com >=30 manuais e >=30 biométricos: razão p0.1={ql[0]:.3f} p1={ql[1]:.3f} mediana={ql[2]:.3f}")
    locf = con.execute(f"""SELECT l.*, m.NM_MUNICIPIO, round(l.n_manual*1.0/(l.n_manual+l.n_bio),3) tx_manual_local
                           FROM loc l JOIN (SELECT DISTINCT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO FROM s) m USING (SG_UF, CD_MUNICIPIO)
                           WHERE n_manual >= 30 AND n_bio >= 30 AND razao < {ql[0]} ORDER BY razao""").df() if False else None
    # NM_MUNICIPIO não está no parquet de seções; pega do BU
    # nomes de município: do BU do turno; se ainda não publicado, do 1º turno (os nomes não mudam)
    db_nm = pb.DB if pb.DB.exists() else Path("data/bu2026.duckdb")
    bu = duckdb.connect(str(db_nm), read_only=True)
    nm = bu.execute("SELECT DISTINCT SG_UF, CAST(CD_MUNICIPIO AS INT) CD_MUNICIPIO, NM_MUNICIPIO FROM bu").df(); bu.close()
    con.register("nm", nm)
    locf = con.execute(f"""SELECT l.*, nm.NM_MUNICIPIO, round(l.n_manual*1.0/(l.n_manual+l.n_bio),3) tx_manual_local
                           FROM loc l LEFT JOIN nm USING (SG_UF, CD_MUNICIPIO)
                           WHERE n_manual >= 30 AND n_bio >= 30 AND razao < {ql[0]} ORDER BY razao""").df()
    locf.to_csv(out / "06_locais_flagrados_manual_rapido.csv", index=False)
    print(f"[6] locais flagrados (razão < p0.1 = {ql[0]:.3f}): {len(locf)}\n", locf.head(40).to_string(index=False))
    # Bom Lugar como referência
    print("\n[6] referência Bom Lugar/MA local 1104:\n",
          con.execute("SELECT * FROM loc WHERE SG_UF='MA' AND CD_MUNICIPIO=7285 AND NR_LOCAL_VOTACAO=1104").df().to_string(index=False))
    # 6b. por município (o padrão de Bom Lugar apareceu em vários locais do mesmo município)
    con.execute(f"""CREATE TABLE mun AS
        WITH e AS (SELECT e.k, e.tipo, e.dur_s, s.SG_UF, s.CD_MUNICIPIO
                   FROM '{PQ}/eleitores_*.parquet' e JOIN s USING (k) WHERE e.dur_s IS NOT NULL AND e.tipo IN ('manual','biometrica'))
        SELECT SG_UF, CD_MUNICIPIO, count(DISTINCT k) urnas, sum((tipo='manual')::INT) n_manual, sum((tipo='biometrica')::INT) n_bio,
               quantile_cont(dur_s, 0.5) FILTER (WHERE tipo='manual') dur_manual_s,
               quantile_cont(dur_s, 0.5) FILTER (WHERE tipo='biometrica') dur_bio_s,
               avg((dur_s < 30)::INT) FILTER (WHERE tipo='manual') pct_manual_lt30,
               avg((dur_s < 30)::INT) FILTER (WHERE tipo='biometrica') pct_bio_lt30
        FROM e GROUP BY 1,2""")
    con.execute("ALTER TABLE mun ADD COLUMN razao DOUBLE; UPDATE mun SET razao = dur_manual_s / NULLIF(dur_bio_s,0)")
    qm = con.execute("SELECT quantile_cont(razao,[0.001,0.01,0.05,0.5]) FROM mun WHERE n_manual >= 100").fetchone()[0]
    munf = con.execute(f"""SELECT m.*, nm.NM_MUNICIPIO, round(m.n_manual*1.0/(m.n_manual+m.n_bio),3) tx_manual_mun,
                            (SELECT count(*) FROM loc l WHERE l.SG_UF=m.SG_UF AND l.CD_MUNICIPIO=m.CD_MUNICIPIO AND l.n_manual>=30 AND l.n_bio>=30 AND l.razao < {ql[0]}) locais_flagrados
                            FROM mun m LEFT JOIN nm USING (SG_UF, CD_MUNICIPIO) WHERE n_manual >= 100 ORDER BY razao""").df()
    munf.to_csv(out / "06_municipios_razao_duracao.csv", index=False)
    print(f"\n[6b] municípios com >=100 manuais: {len(munf)}; razão p0.1={qm[0]:.3f} p1={qm[1]:.3f} p5={qm[2]:.3f} mediana={qm[3]:.3f}")
    print(munf.head(25).round(3).to_string(index=False))
    # ranking de locais por razão (todos com amostra suficiente), para o relatório
    con.execute("COPY (SELECT l.*, nm.NM_MUNICIPIO FROM loc l LEFT JOIN nm USING (SG_UF, CD_MUNICIPIO) WHERE n_manual >= 30 AND n_bio >= 30 ORDER BY razao) "
                f"TO '{(out / '06_locais_razao_duracao.parquet').as_posix()}' (FORMAT PARQUET)")

    # 7. gráficos
    d = con.execute("SELECT regiao, razao_dur_manual_bio r FROM s WHERE log_manual >= 10 AND log_bio >= 10").df()
    fig, ax = plt.subplots(figsize=(8, 4.2)); bins = np.linspace(0.3, 2.5, 89)
    for reg in REG_ORDEM:
        x = d[d.regiao == reg].r.dropna()
        if len(x) > 50: ax.hist(x.clip(0.3, 2.5), bins=bins, density=True, histtype="step", lw=1.6, color=COR_REG[reg], label=f"{reg} (n={len(x):,})".replace(",", "."))
    ax.axvline(lim["razao_dur_manual_bio"], color=INK, lw=0.9, ls="--"); ax.text(lim["razao_dur_manual_bio"], ax.get_ylim()[1] * 0.9, " p0,1%", fontsize=8)
    ax.set_xlabel("razão: duração mediana do voto manual / biométrico, por urna"); ax.set_ylabel("densidade"); ax.legend()
    ax.set_title("Eleitor habilitado manualmente demora mais (razão > 1) em quase todas as urnas")
    fig.tight_layout(); fig.savefig(out / "07_hist_razao_duracao.png"); plt.close(fig)

    r = con.execute("SELECT SG_UF, regiao, round(avg(tx_manual) FILTER (WHERE modelo='UE2013'),3) ue2013, round(avg(tx_manual) FILTER (WHERE modelo='UE2015'),3) ue2015, round(avg(tx_manual) FILTER (WHERE modelo='UE2020'),3) ue2020, round(avg(tx_manual) FILTER (WHERE modelo='UE2022'),3) ue2022 FROM s GROUP BY 1,2 ORDER BY 1").df()
    fig, ax = plt.subplots(figsize=(11, 4.2)); x = np.arange(len(r)); w = 0.2
    for i, (mod, c) in enumerate([("ue2013", "#eb6834"), ("ue2015", "#eda100"), ("ue2020", "#2a78d6"), ("ue2022", "#1baf7a")]):
        ax.bar(x + (i - 1.5) * w, r[mod].fillna(0), w, color=c, label=mod.upper())
    ax.set_xticks(x); ax.set_xticklabels(r.SG_UF); ax.set_ylabel("taxa média de habilitação manual"); ax.legend(ncol=4)
    ax.set_title("Taxa de habilitação manual por modelo de urna e UF (do log)"); ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(out / "07_manual_por_modelo_uf.png"); plt.close(fig)

    tt = t.sort_values("dur_voto_mediana_s")
    fig, ax = plt.subplots(figsize=(7, 7.5))
    ax.barh(tt.SG_UF, tt.dur_voto_mediana_s, color=[COR_REG.get(x, MUTED) for x in tt.regiao], height=0.65)
    for y, (vv, p) in enumerate(zip(tt.dur_voto_mediana_s, tt.pct_tardia)): ax.text(vv + 0.5, y, f"{vv:.0f} s · {p:.0f}% tardias", va="center", fontsize=7.5, color=INK2)
    ax.set_xlabel("duração mediana do voto (habilitação → voto computado), s"); ax.grid(axis="y", visible=False)
    ax.set_title("Tempo por voto e % de urnas que fecham > 30 min tarde, por UF"); ax.set_xlim(0, tt.dur_voto_mediana_s.max() * 1.35)
    fig.tight_layout(); fig.savefig(out / "07_tempo_voto_uf.png"); plt.close(fig)
    con.execute(f"COPY s TO '{(out / 'secoes_logs_brasil.parquet').as_posix()}' (FORMAT PARQUET)")
    print(f"\nsaídas em {out}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(cfg.OUT / "logs_brasil")); a = ap.parse_args(); main(a.out)
