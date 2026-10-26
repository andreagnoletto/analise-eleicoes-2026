#!/usr/bin/env python3
"""Amostra de repetição: mesmas urnas do 1º turno, log do 2º turno. Compara urna a urna e local a local."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, duckdb

ROOT = Path(sys.argv[1]); OUT = ROOT / "out/2t/logs_rep"
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
con = duckdb.connect()
am = pd.read_csv(OUT / "00_amostra.csv")
s2 = pd.read_csv(OUT / "02_secoes_metricas.csv")
el = pd.read_csv(OUT / "01_eleitores.csv", parse_dates=["t_hab", "t_voto"])
el["dur_s"] = (el.t_voto - el.t_hab).dt.total_seconds()
con.register("am", am); con.register("s2", s2); con.register("el", el)
con.execute(f"CREATE TABLE s1 AS SELECT * FROM '{(ROOT / 'out/logs_brasil/secoes_logs_brasil.parquet').as_posix()}'")
con.execute(f"CREATE TABLE l1 AS SELECT * FROM '{(ROOT / 'out/logs_brasil/06_locais_razao_duracao.parquet').as_posix()}'")

# razão de duração manual/biométrico por urna no 2t (≥10 e ≥10), como no 1t
con.execute("""CREATE TABLE rz2 AS
    SELECT k, sum((tipo='manual')::INT) n_man, sum((tipo='biometrica')::INT) n_bio,
           quantile_cont(dur_s,0.5) FILTER (WHERE tipo='manual') dur_man, quantile_cont(dur_s,0.5) FILTER (WHERE tipo='biometrica') dur_bio
    FROM el WHERE dur_s IS NOT NULL GROUP BY k""")
con.execute("""CREATE TABLE j AS
    SELECT s2.k, s2.grupo, s2.SG_UF, s2.modelo modelo_2t, s1.modelo modelo_1t,
           s1.log_votos v1, s2.log_votos v2, s1.log_manual m1, s2.log_manual m2,
           s1.log_manual*1.0/NULLIF(s1.log_votos,0) tx1, s2.log_manual*1.0/NULLIF(s2.log_votos,0) tx2,
           s1.frac_manual_ult60/NULLIF(s1.frac_votos_ult60,0) fim1, s2.frac_manual_ult60/NULLIF(s2.frac_votos_ult60,0) fim2,
           s1.manual_ult60 mu1, s2.manual_ult60 mu2,
           s1.dur_mediana_s dur1, s2.dur_mediana_s dur2, s1.gap_mediano_s gap1, s2.gap_mediano_s gap2,
           s1.min_enc_apos_fech_prev enc1, s2.min_enc_apos_fech_prev enc2,
           s1.n_votos_apos_fech_prev apos1, s2.n_votos_apos_fech_prev apos2,
           s1.razao_dur_manual_bio rz1, CASE WHEN rz2.n_man>=10 AND rz2.n_bio>=10 THEN rz2.dur_man/NULLIF(rz2.dur_bio,0) END rz2,
           s1.max_run_manual run1, s2.max_run_manual run2
    FROM s2 JOIN s1 USING (k) LEFT JOIN rz2 USING (k)""")
n = con.execute("SELECT count(*), sum((modelo_1t=modelo_2t)::INT) FROM j").fetchone()
print(f"urnas pareadas 1t×2t: {n[0]} ; mesmo modelo de urna: {n[1]}")

# 10. por grupo, medianas das mesmas urnas nos dois turnos
g = con.execute("""
    SELECT grupo, count(*) n, sum(v1) votos_1t, sum(v2) votos_2t, sum(m1) manual_1t, sum(m2) manual_2t,
           round(sum(m1)*1.0/sum(v1),4) tx_manual_1t, round(sum(m2)*1.0/sum(v2),4) tx_manual_2t,
           round(median(fim1),2) razao_fim_1t, round(median(fim2),2) razao_fim_2t,
           round(100.0*avg((fim1>1)::INT) FILTER (WHERE mu1>=5),1) pct_fim_gt1_1t, round(100.0*avg((fim2>1)::INT) FILTER (WHERE mu2>=5),1) pct_fim_gt1_2t,
           round(median(dur1),1) dur_voto_1t, round(median(dur2),1) dur_voto_2t, round(median(gap1),0) gap_1t, round(median(gap2),0) gap_2t,
           round(median(enc1),1) enc_1t, round(median(enc2),1) enc_2t, sum(apos1) votos_apos_1t, sum(apos2) votos_apos_2t,
           round(median(rz1),3) razao_dur_1t, round(median(rz2),3) razao_dur_2t, count(rz2) n_razao_2t,
           round(corr(tx1,tx2),3) corr_tx_manual
    FROM j GROUP BY 1 ORDER BY 1""").df()
g.to_csv(OUT / "10_comparacao_1t_2t_por_grupo.csv", index=False)
print("\n[10] mesmas urnas, 1t × 2t, por grupo:\n", g.T.to_string())

# 11. Bom Lugar / Maranhãozinho por local no 2t
con.execute("""CREATE TABLE l2 AS
    SELECT am.SG_UF, am.CD_MUNICIPIO, am.NR_ZONA, am.NR_LOCAL_VOTACAO, count(DISTINCT el.k) urnas,
           sum((tipo='manual')::INT) n_manual, sum((tipo='biometrica')::INT) n_bio,
           quantile_cont(dur_s,0.5) FILTER (WHERE tipo='manual') dur_manual_s, quantile_cont(dur_s,0.5) FILTER (WHERE tipo='biometrica') dur_bio_s,
           avg((dur_s<10)::INT) FILTER (WHERE tipo='manual') pct_manual_lt10, avg((dur_s<10)::INT) FILTER (WHERE tipo='biometrica') pct_bio_lt10
    FROM el JOIN am USING (k) WHERE dur_s IS NOT NULL AND tipo IN ('manual','biometrica') AND am.CD_MUNICIPIO IN (7285, 7927)
    GROUP BY 1,2,3,4""")
bl = con.execute("""SELECT l2.SG_UF, l2.CD_MUNICIPIO, l2.NR_ZONA, l2.NR_LOCAL_VOTACAO, l1.NM_MUNICIPIO, l1.urnas urnas_1t, l2.urnas urnas_2t,
                           l1.n_manual nman_1t, l2.n_manual nman_2t, round(l1.razao,3) razao_1t, round(l2.dur_manual_s/NULLIF(l2.dur_bio_s,0),3) razao_2t,
                           round(l2.dur_manual_s,1) dur_manual_2t, round(l2.dur_bio_s,1) dur_bio_2t, round(l2.pct_manual_lt10,3) manual_lt10_2t, round(l2.pct_bio_lt10,3) bio_lt10_2t
                    FROM l2 LEFT JOIN l1 USING (SG_UF, CD_MUNICIPIO, NR_ZONA, NR_LOCAL_VOTACAO) ORDER BY CD_MUNICIPIO, razao_1t""").df()
bl.to_csv(OUT / "11_bom_lugar_maranhaozinho_locais_1t_2t.csv", index=False)
print("\n[11] Bom Lugar (7285) e Maranhãozinho (7927), por local, razão de duração manual/biométrico:\n", bl.to_string(index=False))
mun = con.execute("""SELECT am.CD_MUNICIPIO, sum((tipo='manual')::INT) n_manual, sum((tipo='biometrica')::INT) n_bio,
                            round(quantile_cont(dur_s,0.5) FILTER (WHERE tipo='manual'),1) dur_man, round(quantile_cont(dur_s,0.5) FILTER (WHERE tipo='biometrica'),1) dur_bio
                     FROM el JOIN am USING (k) JOIN l2 ON l2.SG_UF=am.SG_UF AND l2.CD_MUNICIPIO=am.CD_MUNICIPIO AND l2.NR_ZONA=am.NR_ZONA AND l2.NR_LOCAL_VOTACAO=am.NR_LOCAL_VOTACAO
                     WHERE dur_s IS NOT NULL AND tipo IN ('manual','biometrica') GROUP BY 1""").df()
print("\n[11] por município (2t): \n", mun.to_string(index=False))

# 12. distribuição da razão de duração no 2t, toda a amostra, vs 1t das mesmas urnas
q = con.execute("""SELECT 'razao_dur' m, count(rz1) n1, round(quantile_cont(rz1,0.05),3) p5_1t, round(median(rz1),3) med_1t, round(quantile_cont(rz1,0.95),3) p95_1t,
                          count(rz2) n2, round(quantile_cont(rz2,0.05),3) p5_2t, round(median(rz2),3) med_2t, round(quantile_cont(rz2,0.95),3) p95_2t,
                          round(corr(rz1,rz2),3) corr FROM j
                   UNION ALL
                   SELECT 'razao_manual_fim', count(fim1) , round(quantile_cont(fim1,0.05),3), round(median(fim1),3), round(quantile_cont(fim1,0.95),3),
                          count(fim2), round(quantile_cont(fim2,0.05),3), round(median(fim2),3), round(quantile_cont(fim2,0.95),3), round(corr(fim1,fim2),3)
                   FROM j WHERE mu1 >= 5 AND mu2 >= 5
                   UNION ALL
                   SELECT 'tx_manual', count(tx1), round(quantile_cont(tx1,0.05),3), round(median(tx1),3), round(quantile_cont(tx1,0.95),3),
                          count(tx2), round(quantile_cont(tx2,0.05),3), round(median(tx2),3), round(quantile_cont(tx2,0.95),3), round(corr(tx1,tx2),3) FROM j""").df()
q.to_csv(OUT / "12_distribuicoes_1t_2t.csv", index=False); print("\n[12] distribuições, mesmas urnas:\n", q.to_string(index=False))
# urnas com razão de duração < 0,8 no 2t (limiar p0,1 do 1t) e no 1t
low = con.execute("SELECT k, grupo, modelo_2t, m2, rz1, rz2, tx1, tx2 FROM j WHERE rz2 < 0.8 ORDER BY rz2").df()
low.to_csv(OUT / "12_urnas_razao_dur_lt08_2t.csv", index=False)
print(f"\n[12] urnas com razão de duração < 0,8 no 2t: {len(low)} (das {int(q.loc[0,'n2'])} com ≥10/≥10); no 1t, nas mesmas urnas: "
      f"{con.execute('SELECT count(*) FROM j WHERE rz1 < 0.8').fetchone()[0]}")
print(low.head(25).to_string(index=False))
# manuais no fim: urnas acima do p95 dos controles do 2t
lim = con.execute("SELECT quantile_cont(fim2,0.95) FROM j WHERE mu2>=5 AND grupo LIKE '%controle%'").fetchone()[0]
hi = con.execute(f"SELECT k, grupo, modelo_2t, v2, m2, mu2, round(fim1,2) fim1, round(fim2,2) fim2, run2 FROM j WHERE mu2>=5 AND fim2 > {lim} ORDER BY fim2 DESC").df()
hi.to_csv(OUT / "12_urnas_manual_fim_2t.csv", index=False)
print(f"\n[12] limiar p95 dos controles (razão manual/votos última hora, ≥5 manuais): {lim:.2f}; urnas acima: {len(hi)}\n", hi.head(20).to_string(index=False))

# 13. Bom Lugar e Maranhãozinho urna a urna, nos dois turnos (todas as seções dos dois municípios, qualquer grupo)
u = con.execute("""SELECT j.k, am.NR_LOCAL_VOTACAO loc, j.grupo, j.modelo_2t, j.m1, j.m2, round(j.rz1,2) razao_1t, round(j.rz2,2) razao_2t,
                          round(rz2.dur_man,0) dur_man_2t, round(rz2.dur_bio,0) dur_bio_2t, round(j.tx1,3) tx_manual_1t, round(j.tx2,3) tx_manual_2t,
                          round(j.fim1,2) fim_1t, round(j.fim2,2) fim_2t, j.run1, j.run2
                   FROM j JOIN am USING (k) LEFT JOIN rz2 USING (k) WHERE am.CD_MUNICIPIO IN (7285, 7927) ORDER BY am.CD_MUNICIPIO, loc, j.k""").df()
u.to_csv(OUT / "13_bom_lugar_maranhaozinho_urnas_1t_2t.csv", index=False)
print("\n[13] urna a urna:\n", u.to_string(index=False))
print("\n[13] urnas dos dois municípios com razão < 0,8: 1t", int((u.razao_1t < 0.8).sum()), "| 2t", int((u.razao_2t < 0.8).sum()), "de", int(u.razao_2t.notna().sum()))
