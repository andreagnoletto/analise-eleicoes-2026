#!/usr/bin/env python3
"""
Fase 2 — análise nacional (passos 11 a 14 do plano). Reusa build_tables() de pipeline_bu.py.
Dois critérios para "seção suspeita" (teste 3), lado a lado:
  orig : z no município (n_mun >= 8), z_manual > 3 e z_comp > 2                     (critério original)
  cal  : z em município × quartil nacional de aptos (n >= 8), idem, e aptos >= 100   (critério calibrado no piloto)

Uso:  python analise_brasil.py --out out/brasil
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd, duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pipeline_bu as pb

REG_ORDEM = ["N", "NE", "CO", "SE", "S", "ZZ"]
COR_REG = dict(zip(REG_ORDEM, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 9, "axes.titlesize": 10, "axes.titlecolor": INK,
                     "legend.frameon": False, "savefig.dpi": 150})
CAPITAIS = {"AC": "RIO BRANCO", "AL": "MACEIÓ", "AM": "MANAUS", "AP": "MACAPÁ", "BA": "SALVADOR",
            "CE": "FORTALEZA", "DF": "BRASÍLIA", "ES": "VITÓRIA", "GO": "GOIÂNIA", "MA": "SÃO LUÍS",
            "MG": "BELO HORIZONTE", "MS": "CAMPO GRANDE", "MT": "CUIABÁ", "PA": "BELÉM",
            "PB": "JOÃO PESSOA", "PE": "RECIFE", "PI": "TERESINA", "PR": "CURITIBA",
            "RJ": "RIO DE JANEIRO", "RN": "NATAL", "RO": "PORTO VELHO", "RR": "BOA VISTA",
            "RS": "PORTO ALEGRE", "SC": "FLORIANÓPOLIS", "SE": "ARACAJU", "SP": "SÃO PAULO", "TO": "PALMAS"}
FLAG_ORIG = "(n_mun >= 8 AND z_manual > 3 AND z_comp > 2)"
FLAG_CAL = "(n_q >= 8 AND zm_q > 3 AND zc_q > 2 AND aptos >= 100)"
# terceiro critério, pedido do usuário: manual alto E encerramento bem após o horário local previsto
FLAG_TARD = "(n_mun >= 8 AND z_manual > 3 AND min_apos_fech > 60 AND aptos >= 100)"


def fmt(n):
    return f"{n:,}".replace(",", ".")


# ------------------------------------------------------------------ tabela base nacional
def base(con):
    cap = " OR ".join(f"(SG_UF='{u}' AND NM_MUNICIPIO='{m}')" for u, m in CAPITAIS.items())
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE b AS
        WITH q AS (
          SELECT *, 'Q' || ntile(4) OVER (ORDER BY aptos) quartil_aptos,
                 (NR_URNA_EFETIVADA::BIGINT // 100000) * 100000 serie_lo,
                 CASE WHEN NR_URNA_EFETIVADA::BIGINT < 2000000 THEN 'serie_<2.0M' ELSE 'serie_>=2.0M' END grupo_serie,
                 sum(aptos) OVER (PARTITION BY SG_UF, CD_MUNICIPIO) eleitores_mun
          FROM z),
        r AS (
          SELECT *,
            (tx_manual - avg(tx_manual) OVER w) / NULLIF(stddev(tx_manual) OVER w,0) zm_q,
            (tx_comp   - avg(tx_comp)   OVER w) / NULLIF(stddev(tx_comp)   OVER w,0) zc_q,
            count(*) OVER w n_q
          FROM q WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO, quartil_aptos))
        SELECT *,
          CASE WHEN {cap} THEN '1_capital' WHEN eleitores_mun > 100000 THEN '2_mais_100k' ELSE '3_ate_100k' END porte,
          {FLAG_ORIG} flag_orig, {FLAG_CAL} flag_cal, {FLAG_TARD} flag_tard, min_apos_fech > 30 tardia
        FROM r""")
    ncap = con.execute("SELECT count(DISTINCT SG_UF) FROM b WHERE porte='1_capital'").fetchone()[0]
    print(f"[base] capitais identificadas: {ncap} de 27")
    lim = con.execute("SELECT quartil_aptos, min(aptos), max(aptos), count(*) FROM b GROUP BY 1 ORDER BY 1").df()
    lim.columns = ["quartil_aptos", "aptos_min", "aptos_max", "n"]
    return lim


# ------------------------------------------------------------------ 11. rankings e regiões
def rankings(con, out):
    uf = con.execute("""
        SELECT SG_UF, regiao, count(*) n_secoes, sum(aptos) aptos, sum(comp) comp,
               round(avg(tx_manual),4) media_manual, round(quantile_cont(tx_manual,0.5),4) mediana_manual,
               round(avg(tx_comp),4) media_comp,
               sum(flag_orig) suspeitas_orig, round(1000.0*sum(flag_orig)/count(*),3) por_mil_orig,
               sum(flag_cal) suspeitas_cal, round(1000.0*sum(flag_cal)/count(*),3) por_mil_cal,
               round(100.0*avg(tardia::INT),2) pct_tardia_30min, round(quantile_cont(min_apos_fech,0.5),1) mediana_min_apos_fech,
               round(quantile_cont(min_apos_fech,0.95),1) p95_min_apos_fech
        FROM b GROUP BY 1,2""").df()
    nac = con.execute("""
        SELECT round(avg(tx_manual),4) media_manual, round(1000.0*avg(flag_orig::INT),3) por_mil_orig,
               round(1000.0*avg(flag_cal::INT),3) por_mil_cal, round(100.0*avg(tardia::INT),2) pct_tardia_30min FROM b""").df().iloc[0]
    reg = con.execute("""
        SELECT regiao, count(*) n_secoes, count(DISTINCT SG_UF) n_uf,
               round(avg(tx_manual),4) media_manual, round(quantile_cont(tx_manual,0.5),4) mediana_manual,
               round(avg(tx_comp),4) media_comp,
               sum(flag_orig) suspeitas_orig, round(1000.0*sum(flag_orig)/count(*),3) por_mil_orig,
               sum(flag_cal) suspeitas_cal, round(1000.0*sum(flag_cal)/count(*),3) por_mil_cal,
               round(100.0*avg(tardia::INT),2) pct_tardia_30min, round(quantile_cont(min_apos_fech,0.5),1) mediana_min_apos_fech
        FROM b GROUP BY 1""").df()
    reg["ordem"] = reg.regiao.map(REG_ORDEM.index); reg = reg.sort_values("ordem").drop(columns="ordem")
    for col in ["media_manual", "por_mil_orig", "por_mil_cal", "pct_tardia_30min"]:
        uf[f"{col}_vs_nacional"] = (uf[col] - nac[col]).round(4)
        uf[f"{col}_vs_regiao"] = (uf[col] - uf.regiao.map(reg.set_index("regiao")[col])).round(4)
    uf.sort_values("media_manual", ascending=False).to_csv(out / "11_ranking_uf.csv", index=False)
    reg.to_csv(out / "11_regioes.csv", index=False)
    pd.DataFrame([nac]).to_csv(out / "11_nacional.csv", index=False)

    def barras_uf(col, titulo, xlabel, nome, ref=None, fmt_=lambda v: f"{v:.2f}"):
        d = uf.sort_values(col, ascending=True)
        fig, ax = plt.subplots(figsize=(7.5, 8.5))
        ax.barh(d.SG_UF, d[col], color=[COR_REG[r] for r in d.regiao], height=0.65)
        for y, v in enumerate(d[col]):
            ax.text(v + d[col].max() * 0.01, y, fmt_(v), va="center", fontsize=7.5, color=INK2)
        if ref is not None:
            ax.axvline(ref, color=MUTED, lw=0.9, ls="--"); ax.text(ref, len(d) - 0.3, " média nacional", color=MUTED, fontsize=8)
        ax.set_xlabel(xlabel); ax.set_title(titulo); ax.grid(axis="y", visible=False)
        ax.set_xlim(0, d[col].max() * 1.15)
        hs = [plt.Rectangle((0, 0), 1, 1, color=COR_REG[r]) for r in REG_ORDEM]
        ax.legend(hs, REG_ORDEM, title="região", loc="lower right")
        fig.tight_layout(); fig.savefig(out / nome); plt.close(fig)
    barras_uf("media_manual", "Taxa média de habilitação manual por UF", "QT_ELEI_BIOM_SEM_HABILITACAO / comparecimento (média por seção)",
              "11a_ranking_manual.png", nac.media_manual, lambda v: f"{100*v:.1f}%")
    barras_uf("por_mil_cal", "Seções suspeitas por mil — critério calibrado (município × quartil, aptos ≥ 100)",
              "seções flagradas por mil", "11b_ranking_suspeitas_cal.png", nac.por_mil_cal)
    barras_uf("por_mil_orig", "Seções suspeitas por mil — critério original (z no município)",
              "seções flagradas por mil", "11b_ranking_suspeitas_orig.png", nac.por_mil_orig)
    barras_uf("pct_tardia_30min", "Urnas que encerram > 30 min após o horário local previsto", "% das seções",
              "11c_ranking_encerramento.png", nac.pct_tardia_30min, lambda v: f"{v:.1f}%")

    fig, axes = plt.subplots(1, 4, figsize=(13, 3.8))
    for ax, (col, t, f_) in zip(axes, [("media_manual", "taxa manual média", lambda v: f"{100*v:.1f}%"),
                                      ("por_mil_cal", "suspeitas ‰ (calibrado)", lambda v: f"{v:.2f}"),
                                      ("por_mil_orig", "suspeitas ‰ (original)", lambda v: f"{v:.2f}"),
                                      ("pct_tardia_30min", "% urnas > 30 min tarde", lambda v: f"{v:.1f}%")]):
        ax.bar(reg.regiao, reg[col], color=[COR_REG[r] for r in reg.regiao], width=0.6)
        for x, v in enumerate(reg[col]): ax.text(x, v, f_(v), ha="center", va="bottom", fontsize=8, color=INK2)
        ax.set_title(t); ax.grid(axis="x", visible=False); ax.set_ylim(0, reg[col].max() * 1.25)
    fig.suptitle("Por região — 1º turno 2026", color=INK); fig.tight_layout()
    fig.savefig(out / "11d_regioes.png"); plt.close(fig)
    return uf, reg, nac


# ------------------------------------------------------------------ 12. estratificações nacionais
def estratos(con, out):
    tabs = {}
    for estr, nome in [("quartil_aptos", "tamanho_secao"), ("DS_TIPO_URNA", "tipo_urna"),
                       ("serie_lo", "serie_urna_proxy_modelo"), ("porte", "porte_municipio")]:
        t = con.execute(f"""
            SELECT regiao, {estr} estrato, count(*) n, round(avg(tx_manual),4) media_manual,
                   round(avg(tx_comp),4) media_comp, round(100.0*avg(tardia::INT),2) pct_tardia_30min,
                   sum(flag_orig) suspeitas_orig, round(1000.0*avg(flag_orig::INT),3) por_mil_orig,
                   sum(flag_cal) suspeitas_cal, round(1000.0*avg(flag_cal::INT),3) por_mil_cal
            FROM b GROUP BY 1,2""").df()
        t["ordem"] = t.regiao.map(REG_ORDEM.index)
        t = t.sort_values(["estrato", "ordem"]).drop(columns="ordem")
        t.to_csv(out / f"12_estrat_{nome}.csv", index=False); tabs[nome] = t
    comp = con.execute("""
        SELECT quartil_aptos, count(*) n_base, round(100.0*count(*)/sum(count(*)) OVER (),1) pct_base,
               sum(flag_orig) n_flag_orig, round(100.0*sum(flag_orig)/sum(sum(flag_orig)) OVER (),1) pct_flag_orig,
               sum(flag_cal) n_flag_cal, round(100.0*sum(flag_cal)/sum(sum(flag_cal)) OVER (),1) pct_flag_cal
        FROM b GROUP BY 1 ORDER BY 1""").df()
    comp.to_csv(out / "12_flagradas_vs_base_por_quartil.csv", index=False)
    return tabs, comp


# ------------------------------------------------------------------ 13. regionalidade controlada
def regionalidade(con, out):
    # células = quartil × grupo de série × porte. Padronização direta: aplica as taxas de cada região
    # aos pesos nacionais das células -> taxa "como se" toda região tivesse a mesma composição.
    cel = con.execute("""
        SELECT regiao, quartil_aptos, grupo_serie, porte, count(*) n,
               avg(tx_manual) media_manual, avg(flag_orig::INT) tx_orig, avg(flag_cal::INT) tx_cal, avg(tardia::INT) tx_tardia
        FROM b GROUP BY 1,2,3,4""").df()
    peso = con.execute("""
        SELECT quartil_aptos, grupo_serie, porte, count(*)*1.0/sum(count(*)) OVER () w FROM b GROUP BY 1,2,3""").df()
    m = cel.merge(peso, on=["quartil_aptos", "grupo_serie", "porte"])
    bruto = con.execute("""
        SELECT regiao, round(avg(tx_manual),4) manual_bruto, round(1000*avg(flag_orig::INT),3) por_mil_orig_bruto,
               round(1000*avg(flag_cal::INT),3) por_mil_cal_bruto, round(100*avg(tardia::INT),2) pct_tardia_bruto
        FROM b GROUP BY 1""").df()
    rows = []
    for r, g in m.groupby("regiao"):
        wsum = g.w.sum()  # células presentes na região (ZZ não tem todas)
        rows.append({"regiao": r, "cobertura_celulas": round(wsum, 3),
                     "manual_padronizado": round((g.media_manual * g.w).sum() / wsum, 4),
                     "por_mil_orig_padronizado": round(1000 * (g.tx_orig * g.w).sum() / wsum, 3),
                     "por_mil_cal_padronizado": round(1000 * (g.tx_cal * g.w).sum() / wsum, 3),
                     "pct_tardia_padronizado": round(100 * (g.tx_tardia * g.w).sum() / wsum, 2)})
    pad = bruto.merge(pd.DataFrame(rows), on="regiao")
    pad["ordem"] = pad.regiao.map(REG_ORDEM.index); pad = pad.sort_values("ordem").drop(columns="ordem")
    pad.to_csv(out / "13_regionalidade_padronizada.csv", index=False)
    # NE vs resto, célula a célula (razão de taxas)
    ne = cel[cel.regiao == "NE"].set_index(["quartil_aptos", "grupo_serie", "porte"])
    outros = con.execute("""
        SELECT quartil_aptos, grupo_serie, porte, count(*) n, avg(tx_manual) media_manual,
               avg(flag_orig::INT) tx_orig, avg(flag_cal::INT) tx_cal, avg(tardia::INT) tx_tardia
        FROM b WHERE regiao <> 'NE' AND regiao <> 'ZZ' GROUP BY 1,2,3""").df().set_index(["quartil_aptos", "grupo_serie", "porte"])
    cc = ne.join(outros, lsuffix="_NE", rsuffix="_outros", how="inner").reset_index()
    cc["razao_manual"] = (cc.media_manual_NE / cc.media_manual_outros).round(3)
    cc["razao_por_mil_cal"] = (cc.tx_cal_NE / cc.tx_cal_outros.replace(0, np.nan)).round(3)
    cc["razao_por_mil_orig"] = (cc.tx_orig_NE / cc.tx_orig_outros.replace(0, np.nan)).round(3)
    cc["razao_tardia"] = (cc.tx_tardia_NE / cc.tx_tardia_outros.replace(0, np.nan)).round(3)
    cols = ["quartil_aptos", "grupo_serie", "porte", "n_NE", "n_outros", "media_manual_NE", "media_manual_outros",
            "razao_manual", "tx_cal_NE", "tx_cal_outros", "razao_por_mil_cal", "tx_orig_NE", "tx_orig_outros",
            "razao_por_mil_orig", "tx_tardia_NE", "tx_tardia_outros", "razao_tardia"]
    cc = cc[cols].drop(columns="regiao", errors="ignore")
    for c in cc.columns:
        if cc[c].dtype == float: cc[c] = cc[c].round(4)
    cc.to_csv(out / "13_NE_vs_outros_por_celula.csv", index=False)
    return pad, cc


# ------------------------------------------------------------------ 14. lista nacional de flagradas
def flagradas(con, out):
    con.execute("""
        CREATE OR REPLACE TEMP TABLE v AS
        SELECT SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO, NR_VOTAVEL, NM_VOTAVEL, CAST(QT_VOTOS AS INT) votos
        FROM bu WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%'""")
    cand = con.execute("SELECT NR_VOTAVEL, any_value(NM_VOTAVEL) nm, sum(votos) tot FROM v GROUP BY 1 ORDER BY tot DESC").df()
    cand["rotulo"] = cand.NR_VOTAVEL + "_" + cand.nm.str.replace(r"\s+", "_", regex=True)
    rot = dict(zip(cand.NR_VOTAVEL, cand.rotulo))
    fl = con.execute("""
        SELECT SG_UF, regiao, CD_MUNICIPIO, NM_MUNICIPIO, porte, NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO,
               DS_TIPO_URNA, NR_URNA_EFETIVADA, serie_lo faixa_serie_urna_proxy_modelo, DS_SECOES_AGREGADAS,
               aptos, quartil_aptos, comp, bio_nh, round(tx_comp,3) tx_comp, round(tx_manual,3) tx_manual,
               round(z_manual,2) z_manual, round(z_comp,2) z_comp, n_mun,
               round(zm_q,2) z_manual_quartil, round(zc_q,2) z_comp_quartil, n_q,
               flag_orig, flag_cal, flag_tard, DT_ABERTURA, DT_ENCERRAMENTO, min_apos_fech
        FROM b WHERE flag_orig OR flag_cal OR flag_tard ORDER BY z_manual DESC""").df()
    sec = con.execute("""
        WITH f AS (SELECT SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO FROM b WHERE flag_orig OR flag_cal OR flag_tard),
        s AS (SELECT v.SG_UF, v.CD_MUNICIPIO, v.NR_ZONA, v.NR_SECAO, NR_VOTAVEL,
                     votos * 100.0 / sum(votos) OVER (PARTITION BY v.SG_UF, v.NR_ZONA, v.NR_SECAO) pct
              FROM v JOIN f USING (SG_UF, NR_ZONA, NR_SECAO)),
        mu AS (SELECT SG_UF, CD_MUNICIPIO, NR_VOTAVEL,
                      sum(votos) * 100.0 / sum(sum(votos)) OVER (PARTITION BY SG_UF, CD_MUNICIPIO) pct_mun
               FROM v WHERE (SG_UF, CD_MUNICIPIO) IN (SELECT DISTINCT SG_UF, CD_MUNICIPIO FROM f) GROUP BY 1,2,3)
        SELECT s.*, mu.pct_mun FROM s LEFT JOIN mu USING (SG_UF, CD_MUNICIPIO, NR_VOTAVEL)""").df()
    key = ["SG_UF", "NR_ZONA", "NR_SECAO"]
    ps = sec.pivot_table(index=key, columns="NR_VOTAVEL", values="pct", aggfunc="first")
    pm = sec.pivot_table(index=key, columns="NR_VOTAVEL", values="pct_mun", aggfunc="first")
    wide = pd.DataFrame(index=ps.index)
    for c in [c for c in cand.NR_VOTAVEL if c in ps.columns]:
        wide[f"pct_secao_{rot[c]}"] = ps[c].round(2); wide[f"pct_mun_{rot[c]}"] = pm[c].round(2)
        wide[f"dif_pp_{rot[c]}"] = (ps[c] - pm[c]).round(2)
    det = fl.merge(wide.reset_index(), on=key, how="left")
    det.to_csv(out / "secoes_flagradas_brasil.csv", index=False)
    return det, cand


def tardias(con, out):
    """Votos sem digital × encerramento tardio: quantos dos votos manuais de cada UF ocorreram em urnas
    que fecharam > 30 / > 60 min após o horário local previsto, e taxa manual por faixa de encerramento."""
    t = con.execute("""
        SELECT SG_UF, regiao, count(*) n_secoes,
               sum(bio_nh) votos_manual, sum(comp) comparecimento,
               sum(min_apos_fech > 30) secoes_tardias_30, sum(min_apos_fech > 60) secoes_tardias_60,
               sum(bio_nh) FILTER (WHERE min_apos_fech > 30) manual_em_tardias_30,
               sum(bio_nh) FILTER (WHERE min_apos_fech > 60) manual_em_tardias_60,
               round(100.0 * sum(bio_nh) FILTER (WHERE min_apos_fech > 60) / sum(bio_nh), 2) pct_manual_em_tardias_60,
               round(100.0 * sum(comp) FILTER (WHERE min_apos_fech > 60) / sum(comp), 2) pct_comp_em_tardias_60,
               round(avg(tx_manual) FILTER (WHERE min_apos_fech <= 30), 4) tx_manual_no_horario,
               round(avg(tx_manual) FILTER (WHERE min_apos_fech > 60), 4) tx_manual_tardias_60,
               round(corr(min_apos_fech, tx_manual), 3) corr_atraso_manual,
               sum(flag_tard) suspeitas_tard, round(1000.0*avg(flag_tard::INT),3) por_mil_tard
        FROM b GROUP BY 1,2 ORDER BY pct_manual_em_tardias_60 DESC""").df()
    t.to_csv(out / "16_manual_x_encerramento_uf.csv", index=False)
    f = con.execute("""
        SELECT regiao, CASE WHEN min_apos_fech <= 0 THEN '0_ate_horario' WHEN min_apos_fech <= 30 THEN '1_ate_30min'
                            WHEN min_apos_fech <= 60 THEN '2_30_60min' WHEN min_apos_fech <= 120 THEN '3_60_120min'
                            ELSE '4_mais_120min' END faixa_enc,
               count(*) n, round(avg(tx_manual),4) media_manual, round(avg(tx_comp),4) media_comp, round(avg(aptos),1) media_aptos
        FROM b GROUP BY 1,2 ORDER BY 2,1""").df()
    f.to_csv(out / "16_manual_por_faixa_encerramento_regiao.csv", index=False)
    return t, f


def correlacoes(con, cand, out):
    top = cand.head(4).NR_VOTAVEL.tolist()
    corr = con.execute(f"""
        WITH s AS (
          SELECT v.SG_UF, v.CD_MUNICIPIO, v.NR_ZONA, v.NR_SECAO, NR_VOTAVEL, any_value(NM_VOTAVEL) nm,
                 sum(votos) * 1.0 / NULLIF(any_value(b.comp),0) vshare, any_value(b.tx_manual) tx_manual,
                 any_value(b.tx_comp) tx_comp
          FROM v JOIN b USING (SG_UF, NR_ZONA, NR_SECAO)
          WHERE NR_VOTAVEL IN ({",".join(map(repr, top))}) GROUP BY 1,2,3,4,5),
        d AS (SELECT *, vshare - avg(vshare) OVER w dvshare, tx_manual - avg(tx_manual) OVER w dmanual,
                     tx_comp - avg(tx_comp) OVER w dcomp
              FROM s WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO, NR_VOTAVEL))
        SELECT SG_UF, NR_VOTAVEL, nm, count(*) n, round(corr(tx_manual, vshare),3) corr_manual_voto,
               round(corr(tx_comp, vshare),3) corr_comp_voto,
               round(corr(dmanual, dvshare),3) corr_manual_voto_intra_mun,
               round(corr(dcomp, dvshare),3) corr_comp_voto_intra_mun
        FROM d GROUP BY 1,2,3 ORDER BY 2,1""").df()
    corr.to_csv(out / "15_correlacao_manual_voto_uf.csv", index=False)
    return corr


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(pb.cfg.OUT / "brasil"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
    con = duckdb.connect(str(pb.DB), read_only=True)
    pb.build_tables(con)
    lim = base(con); lim.to_csv(out / "12_quartis_aptos_limites.csv", index=False)
    print("[base] quartis nacionais de aptos:\n", lim.to_string(index=False))
    uf, reg, nac = rankings(con, out)
    print("\n[11] nacional:\n", pd.DataFrame([nac]).to_string(index=False))
    print("\n[11] regiões:\n", reg.to_string(index=False))
    print("\n[11] ranking UF (por taxa manual):\n", uf.sort_values("media_manual", ascending=False)[
        ["SG_UF", "regiao", "n_secoes", "media_manual", "por_mil_orig", "por_mil_cal", "pct_tardia_30min", "mediana_min_apos_fech"]].to_string(index=False))
    tabs, comp = estratos(con, out)
    for k, t in tabs.items(): print(f"\n[12] {k}:\n", t.to_string(index=False))
    print("\n[12] flagradas vs base por quartil:\n", comp.to_string(index=False))
    pad, cc = regionalidade(con, out)
    print("\n[13] regionalidade — bruto vs padronizado por (quartil × série × porte):\n", pad.to_string(index=False))
    print("\n[13] NE vs outros por célula:\n", cc.to_string(index=False))
    det, cand = flagradas(con, out)
    print(f"\n[14] {len(det)} seções flagradas (orig: {int(det.flag_orig.sum())}, cal: {int(det.flag_cal.sum())}, "
          f"tard: {int(det.flag_tard.sum())}) -> secoes_flagradas_brasil.csv")
    t16, f16 = tardias(con, out)
    print("\n[16] votos sem digital × encerramento tardio, por UF:\n", t16.to_string(index=False))
    print("\n[16] taxa manual por faixa de encerramento e região:\n", f16.to_string(index=False))
    corr = correlacoes(con, cand, out)
    print("\n[15] correlação manual × voto por UF:\n", corr.to_string(index=False))
