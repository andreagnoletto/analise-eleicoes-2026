#!/usr/bin/env python3
"""
Extras do piloto (passos 6, 7 e 8 do plano) — gráficos, detalhe das seções flagradas e
estratificações. Reusa build_tables() de pipeline_bu.py (tabelas temp secao / m / z).

Uso:  python piloto_extras.py --uf CE BA RS PR --foco CE BA --out out/piloto
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd, duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import pipeline_bu as pb

# paleta categórica validada (dataviz/validate_palette.js: ALL CHECKS PASS, modo light)
COR = {"CE": "#2a78d6", "BA": "#eb6834", "RS": "#1baf7a", "PR": "#eda100"}
COR_EXTRA = ["#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SURF = "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 9, "axes.titlesize": 10, "axes.titlecolor": INK,
                     "legend.frameon": False, "savefig.dpi": 150})
FLAG = "n_mun >= 8 AND z_manual > 3 AND z_comp > 2"


def cor_uf(ufs):
    extra = iter(COR_EXTRA)
    return {u: COR.get(u) or next(extra) for u in ufs}


def faixa_serie(n):
    lo = (int(n) // 100000) * 100000
    return f"{lo/1e6:.1f}M–{(lo+100000)/1e6:.1f}M"


# ------------------------------------------------------------------ 6. gráficos
def graficos(con, ufs, foco, out):
    cores = cor_uf(ufs)
    z = con.execute(f"SELECT * FROM z WHERE SG_UF IN ({','.join(map(repr, ufs))})").df()
    z["flag"] = (z.n_mun >= 8) & (z.z_manual > 3) & (z.z_comp > 2)
    ctrl = [u for u in ufs if u not in foco]

    # (a) histograma da taxa manual — mesma escala, densidade
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True, sharex=True)
    bins = np.linspace(0, 0.5, 51)
    for ax, grupo, titulo in [(axes[0], foco, "foco: " + " / ".join(foco)),
                              (axes[1], ctrl, "controle: " + " / ".join(ctrl))]:
        for u in grupo:
            v = z.loc[z.SG_UF == u, "tx_manual"].clip(upper=0.5)
            ax.hist(v, bins=bins, density=True, histtype="step", lw=1.8, color=cores[u],
                    label=f"{u}  (mediana {v.median():.3f}, n={len(v):,})".replace(",", "."))
        ax.set_title(titulo); ax.legend(loc="upper right")
    axes[0].set_ylabel("densidade (seções)")
    fig.supxlabel("taxa de habilitação manual = QT_ELEI_BIOM_SEM_HABILITACAO / comparecimento", color=INK2, fontsize=9)
    fig.suptitle("Habilitação manual por seção — 1º turno 2026 (valores > 0,5 agrupados em 0,5)", color=INK)
    fig.tight_layout(); fig.savefig(out / "06a_hist_manual.png"); plt.close(fig)

    # (b) scatter manual × comparecimento, cor = z_manual no município (divergente, cinza no 0)
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#eb6834"])
    norm = Normalize(-3, 3)
    n = len(ufs); ncol = 2; nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(11, 4.6 * nrow), sharex=True, sharey=True)
    for ax, u in zip(np.ravel(axes), ufs):
        d = z[z.SG_UF == u].sample(frac=1, random_state=1)
        sc = ax.scatter(d.tx_manual, d.tx_comp, c=d.z_manual.clip(-3, 3), cmap=cmap, norm=norm,
                        s=4, alpha=0.55, linewidths=0)
        f = d[d.flag]
        ax.scatter(f.tx_manual, f.tx_comp, s=46, facecolors="none", edgecolors=INK, linewidths=1.1,
                   label=f"flagradas (teste 3): {len(f)}")
        ax.set_title(f"{u} — {len(d):,} seções apuradas".replace(",", "."))
        ax.set_xlim(0, 0.6); ax.set_ylim(0.4, 1.02); ax.legend(loc="lower right")
    for ax in np.ravel(axes)[n:]: ax.axis("off")
    for ax in np.ravel(axes)[-ncol:]: ax.set_xlabel("taxa de habilitação manual")
    for ax in np.ravel(axes)[::ncol]: ax.set_ylabel("taxa de comparecimento")
    cb = fig.colorbar(sc, ax=np.ravel(axes).tolist(), shrink=0.6, pad=0.02)
    cb.set_label("z-score da taxa manual dentro do município (cortado em ±3)")
    fig.suptitle("Habilitação manual × comparecimento por seção", color=INK)
    fig.savefig(out / "06b_scatter_manual_comp.png", bbox_inches="tight"); plt.close(fig)

    # (c) hora de encerramento — ECDF dos minutos após o fechamento LOCAL previsto
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for u in ufs:
        v = np.sort(z.loc[z.SG_UF == u, "min_apos_fech"].dropna().values)
        y = np.arange(1, len(v) + 1) / len(v)
        p30 = (v > 30).mean() * 100
        ax.step(v, y, where="post", lw=1.8, color=cores[u],
                label=f"{u}: {p30:.1f}% fecham >30 min depois; p95 = {np.percentile(v, 95):.0f} min")
    for x in (30, 60, 120):
        ax.axvline(x, color=MUTED, lw=0.8, ls=":"); ax.text(x + 2, 0.02, f"+{x} min", color=MUTED, fontsize=8)
    ax.set_xlim(-10, 240); ax.set_ylim(0, 1.02)
    ax.set_xlabel("minutos entre o horário local previsto de encerramento (17h) e o encerramento da urna")
    ax.set_ylabel("fração acumulada de seções"); ax.legend(loc="lower right")
    ax.set_title("Encerramento da votação por UF (ECDF) — valores > 240 min não mostrados")
    fig.tight_layout(); fig.savefig(out / "06c_encerramento_ecdf.png"); plt.close(fig)

    # (d) seções suspeitas por mil, por UF
    por_uf = z[z.n_mun >= 8].groupby("SG_UF").agg(n=("flag", "size"), suspeitas=("flag", "sum"))
    por_uf["por_mil"] = 1000 * por_uf.suspeitas / por_uf.n
    por_uf = por_uf.loc[ufs]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    bars = ax.bar(por_uf.index, por_uf.por_mil, width=0.55, color=[cores[u] for u in por_uf.index])
    for b, (u, r) in zip(bars, por_uf.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01,
                f"{r.por_mil:.2f}‰\n({int(r.suspeitas)} de {int(r.n):,})".replace(",", "."),
                ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_ylabel("seções flagradas por mil (teste 3)"); ax.set_ylim(0, por_uf.por_mil.max() * 1.45)
    ax.set_title("Teste 3: z_manual > 3 e z_comp > 2 no município (n_mun ≥ 8)")
    ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(out / "06d_suspeitas_por_mil.png"); plt.close(fig)
    return z


# ------------------------------------------------------------------ 7. detalhe das flagradas
def detalhe_flagradas(con, out):
    con.execute("""
        CREATE OR REPLACE TEMP TABLE v AS
        SELECT SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO, CD_TIPO_VOTAVEL, NR_VOTAVEL, NM_VOTAVEL,
               CAST(QT_VOTOS AS INT) votos
        FROM bu WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%'
    """)
    cand = con.execute("""
        SELECT NR_VOTAVEL, any_value(NM_VOTAVEL) nm, sum(votos) tot FROM v
        GROUP BY 1 ORDER BY tot DESC""").df()
    cand["rotulo"] = cand.NR_VOTAVEL + "_" + cand.nm.str.replace(r"\s+", "_", regex=True)
    rot = dict(zip(cand.NR_VOTAVEL, cand.rotulo))

    fl = con.execute(f"""
        SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO,
               DS_TIPO_URNA, NR_URNA_EFETIVADA, DS_SECOES_AGREGADAS,
               aptos, comp, bio_nh, round(tx_comp,3) tx_comp, round(tx_manual,3) tx_manual,
               round(z_manual,2) z_manual, round(z_comp,2) z_comp, n_mun,
               DT_ABERTURA, DT_ENCERRAMENTO, min_apos_fech
        FROM z WHERE {FLAG} ORDER BY z_manual DESC""").df()
    fl.insert(fl.columns.get_loc("NR_URNA_EFETIVADA") + 1, "faixa_serie_urna_proxy_modelo",
              fl.NR_URNA_EFETIVADA.map(faixa_serie))

    sec = con.execute(f"""
        WITH f AS (SELECT SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO FROM z WHERE {FLAG}),
        s AS (SELECT v.SG_UF, v.CD_MUNICIPIO, v.NR_ZONA, v.NR_SECAO, NR_VOTAVEL,
                     votos * 100.0 / sum(votos) OVER (PARTITION BY v.SG_UF, v.NR_ZONA, v.NR_SECAO) pct
              FROM v JOIN f USING (SG_UF, NR_ZONA, NR_SECAO)),
        mu AS (SELECT SG_UF, CD_MUNICIPIO, NR_VOTAVEL,
                      sum(votos) * 100.0 / sum(sum(votos)) OVER (PARTITION BY SG_UF, CD_MUNICIPIO) pct_mun
               FROM v GROUP BY 1,2,3)
        SELECT s.*, mu.pct_mun FROM s LEFT JOIN mu USING (SG_UF, CD_MUNICIPIO, NR_VOTAVEL)""").df()
    key = ["SG_UF", "NR_ZONA", "NR_SECAO"]
    ps = sec.pivot_table(index=key, columns="NR_VOTAVEL", values="pct", aggfunc="first")
    pm = sec.pivot_table(index=key, columns="NR_VOTAVEL", values="pct_mun", aggfunc="first")
    cols = [c for c in cand.NR_VOTAVEL if c in ps.columns]
    wide = pd.DataFrame(index=ps.index)
    for c in cols:
        wide[f"pct_secao_{rot[c]}"] = ps[c].round(2)
        wide[f"pct_mun_{rot[c]}"] = pm[c].round(2)
        wide[f"dif_pp_{rot[c]}"] = (ps[c] - pm[c]).round(2)
    det = fl.merge(wide.reset_index(), on=key, how="left")
    det.to_csv(out / "07_secoes_flagradas_detalhe.csv", index=False)
    return det, cand


# ------------------------------------------------------------------ 8. estratificações
def estratos(con, ufs, out):
    ufs_sql = ",".join(map(repr, ufs))
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE zs AS
        SELECT *,
          'Q' || ntile(4) OVER (ORDER BY aptos) AS quartil_aptos,
          (NR_URNA_EFETIVADA::BIGINT // 100000) * 100000 AS serie_lo,
          CASE WHEN min_apos_fech <= 0 THEN '0_ate_17h' WHEN min_apos_fech <= 30 THEN '1_ate_30min'
               WHEN min_apos_fech <= 60 THEN '2_30_60min' WHEN min_apos_fech <= 120 THEN '3_60_120min'
               ELSE '4_mais_120min' END AS faixa_enc,
          ({FLAG}) AS flag
        FROM z WHERE SG_UF IN ({ufs_sql})""")
    lim = con.execute("SELECT quartil_aptos, min(aptos), max(aptos), count(*) FROM zs GROUP BY 1 ORDER BY 1").df()
    lim.columns = ["quartil_aptos", "aptos_min", "aptos_max", "n"]
    lim.to_csv(out / "08_quartis_aptos_limites.csv", index=False)

    def tabela(estrato, nome):
        base = con.execute(f"""
            SELECT SG_UF, {estrato} AS estrato, count(*) n,
                   round(avg(tx_manual),4) media_manual, round(avg(tx_comp),4) media_comp,
                   round(avg(min_apos_fech),1) media_min_apos_fech,
                   sum(flag) FILTER (WHERE n_mun >= 8) suspeitas_z_municipio,
                   round(1000.0 * sum(flag) FILTER (WHERE n_mun >= 8) / count(*) FILTER (WHERE n_mun >= 8), 2) por_mil_z_municipio
            FROM zs GROUP BY 1,2""").df()
        # z recalculado DENTRO do estrato (município × estrato): a seção continua "suspeita"
        # quando comparada só com seções parecidas?
        re = con.execute(f"""
            WITH r AS (
              SELECT SG_UF, {estrato} AS estrato,
                (tx_manual - avg(tx_manual) OVER w) / NULLIF(stddev(tx_manual) OVER w,0) zm,
                (tx_comp   - avg(tx_comp)   OVER w) / NULLIF(stddev(tx_comp)   OVER w,0) zc,
                count(*) OVER w nn
              FROM zs WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO, {estrato}))
            SELECT SG_UF, estrato, sum(nn >= 8 AND zm > 3 AND zc > 2) suspeitas_z_estrato,
                   round(1000.0 * sum(nn >= 8 AND zm > 3 AND zc > 2) / count(*) FILTER (WHERE nn >= 8), 2) por_mil_z_estrato
            FROM r GROUP BY 1,2""").df()
        t = base.merge(re, on=["SG_UF", "estrato"]).sort_values(["estrato", "SG_UF"])
        t.to_csv(out / f"08_estrat_{nome}.csv", index=False)
        return t
    t_tam = tabela("quartil_aptos", "tamanho_secao")
    t_tipo = tabela("DS_TIPO_URNA", "tipo_urna")
    t_ser = tabela("serie_lo", "serie_urna_proxy_modelo")
    # distribuição das flagradas por estrato vs base
    comp = con.execute("""
        SELECT quartil_aptos, count(*) n_base, sum(flag) n_flag,
               round(100.0*count(*)/sum(count(*)) OVER (),1) pct_base,
               round(100.0*sum(flag)/sum(sum(flag)) OVER (),1) pct_flag
        FROM zs WHERE n_mun >= 8 GROUP BY 1 ORDER BY 1""").df()
    comp.to_csv(out / "08_flagradas_vs_base_por_quartil.csv", index=False)
    return t_tam, t_tipo, t_ser, comp


# ------------------------------------------------------------------ extras de interpretação
def extras(con, ufs, cand, out):
    ufs_sql = ",".join(map(repr, ufs))
    top = cand.head(6).NR_VOTAVEL.tolist()
    # 9. correlação manual × voto, todas as UFs, bruta e dentro do município (demeaned)
    corr = con.execute(f"""
        WITH s AS (
          SELECT v.SG_UF, v.CD_MUNICIPIO, v.NR_ZONA, v.NR_SECAO, NR_VOTAVEL, any_value(NM_VOTAVEL) nm,
                 sum(votos) * 1.0 / NULLIF(any_value(z.comp),0) vshare, any_value(z.tx_manual) tx_manual,
                 any_value(z.tx_comp) tx_comp
          FROM v JOIN z USING (SG_UF, NR_ZONA, NR_SECAO)
          WHERE v.SG_UF IN ({ufs_sql}) AND NR_VOTAVEL IN ({",".join(map(repr, top))})
          GROUP BY 1,2,3,4,5),
        d AS (
          SELECT *, vshare - avg(vshare) OVER w dvshare, tx_manual - avg(tx_manual) OVER w dmanual,
                 tx_comp - avg(tx_comp) OVER w dcomp
          FROM s WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO, NR_VOTAVEL))
        SELECT SG_UF, NR_VOTAVEL, nm, count(*) n,
               round(corr(tx_manual, vshare),3) corr_manual_voto,
               round(corr(tx_comp, vshare),3) corr_comp_voto,
               round(corr(dmanual, dvshare),3) corr_manual_voto_intra_mun,
               round(corr(dcomp, dvshare),3) corr_comp_voto_intra_mun
        FROM d GROUP BY 1,2,3 ORDER BY 2, 1""").df()
    corr.to_csv(out / "09_correlacao_manual_voto_todas_ufs.csv", index=False)
    # 10. encerramento por tamanho de seção (fila?)
    enc = con.execute("""
        SELECT SG_UF, quartil_aptos, count(*) n, round(avg(comp),1) media_comp_abs,
               round(quantile_cont(min_apos_fech,0.5),1) mediana_min, round(quantile_cont(min_apos_fech,0.95),1) p95_min,
               round(100.0*sum(min_apos_fech>30)/count(*),1) pct_apos_30min
        FROM zs GROUP BY 1,2 ORDER BY 2,1""").df()
    enc.to_csv(out / "10_encerramento_por_tamanho.csv", index=False)
    # 11. taxa manual por faixa de encerramento — se a habilitação manual se concentra no fim,
    #     urnas que fecham tarde deveriam ter taxa manual maior
    man = con.execute("""
        SELECT SG_UF, faixa_enc, count(*) n, round(avg(tx_manual),4) media_manual,
               round(quantile_cont(tx_manual,0.5),4) mediana_manual, round(avg(tx_comp),4) media_comp,
               round(avg(aptos),1) media_aptos,
               round(corr(min_apos_fech, tx_manual),3) corr_min_manual
        FROM zs GROUP BY 1,2 ORDER BY 2,1""").df()
    man.to_csv(out / "11_manual_por_faixa_encerramento.csv", index=False)
    return corr, enc, man


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", nargs="*", default=["CE", "BA", "RS", "PR"])
    ap.add_argument("--foco", nargs="*", default=["CE", "BA"])
    ap.add_argument("--out", default="out/piloto")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(pb.DB), read_only=True)
    pb.build_tables(con)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    z = graficos(con, a.uf, a.foco, out); print("[6] gráficos salvos")
    det, cand = detalhe_flagradas(con, out)
    print(f"[7] {len(det)} seções flagradas -> 07_secoes_flagradas_detalhe.csv")
    t_tam, t_tipo, t_ser, comp = estratos(con, a.uf, out)
    print("\n[8] limites dos quartis de aptos:\n", pd.read_csv(out / "08_quartis_aptos_limites.csv").to_string(index=False))
    print("\n[8] por tamanho de seção:\n", t_tam.to_string(index=False))
    print("\n[8] por tipo de urna (DS_TIPO_URNA):\n", t_tipo.to_string(index=False))
    print("\n[8] por faixa de série da urna (proxy de modelo):\n", t_ser.to_string(index=False))
    print("\n[8] flagradas vs base por quartil:\n", comp.to_string(index=False))
    corr, enc, man = extras(con, a.uf, cand, out)
    print("\n[9] correlação manual × voto (bruta e intra-município):\n", corr.to_string(index=False))
    print("\n[10] encerramento por tamanho:\n", enc.to_string(index=False))
    print("\n[11] taxa manual por faixa de encerramento:\n", man.to_string(index=False))
