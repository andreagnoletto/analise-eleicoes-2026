#!/usr/bin/env python3
"""
Pipeline de análise de Boletins de Urna (BU) — Eleições 2026, 1º turno.
Foco: hipótese de habilitação manual (sem biometria) concentrada no fim da sessão.

Uso:
  python pipeline_bu.py download  --uf CE BA          # baixa + verifica SHA-512
  python pipeline_bu.py load      --uf CE BA ...      # carrega CSVs em DuckDB
  python pipeline_bu.py analyze   --foco CE BA --out out/piloto   # roda os testes, gera CSVs

Requisitos: pip install -r requirements.txt (duckdb, pandas, matplotlib, requests)
"""
import argparse, hashlib, os, sys, zipfile, glob
from pathlib import Path

BASE = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb"
STAMP = "051020261403"
DATA = Path("data"); RAW = DATA / "raw"; CSV = DATA / "csv"; OUT = Path("out")
DB = DATA / "bu2026.duckdb"
UFS_ALL = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split()
NORDESTE = "AL BA CE MA PB PE PI RN SE".split()
REGIAO = {**{u: "N"  for u in "AC AM AP PA RO RR TO".split()},
          **{u: "NE" for u in NORDESTE},
          **{u: "CO" for u in "DF GO MT MS".split()},
          **{u: "SE" for u in "ES MG RJ SP".split()},
          **{u: "S"  for u in "PR RS SC".split()},
          "ZZ": "ZZ"}
# Hora LOCAL prevista de encerramento da votação (DT_ABERTURA/DT_ENCERRAMENTO vêm no relógio local da
# urna: no AC a urna abre 06:00 e fecha 15:00, equivalentes a 08h–17h de Brasília). ZZ (exterior):
# 17h no horário local de cada país.
FECH_LOCAL = {**{u: "17:00:00" for u in UFS_ALL}, "AC": "15:00:00",
              **{u: "16:00:00" for u in "AM MT MS RO RR".split()}}

# ---------------------------------------------------------------- download
def download(ufs):
    import requests
    RAW.mkdir(parents=True, exist_ok=True)
    for uf in ufs:
        name = f"bweb_1t_{uf}_{STAMP}.zip"
        dst = RAW / name
        if not dst.exists():
            print(f"[download] {name}")
            with requests.get(f"{BASE}/{name}", stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        # hash
        h_txt = requests.get(f"{BASE}/{name}.sha512", timeout=60).text.split()[0].lower()
        h = hashlib.sha512()
        with open(dst, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        ok = h.hexdigest() == h_txt
        print(f"[sha512] {uf}: {'OK' if ok else 'FALHOU — arquivo corrompido ou alterado'}")
        if not ok:
            sys.exit(1)

# ---------------------------------------------------------------- load
def load(ufs):
    """Carga incremental: extrai o CSV de cada UF e insere na tabela bu (UF já carregada é pulada)."""
    import duckdb
    CSV.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    tem_tabela = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='bu'").fetchone()[0] > 0
    ja = set(r[0] for r in con.execute("SELECT DISTINCT SG_UF FROM bu").fetchall()) if tem_tabela else set()
    for uf in ufs:
        if uf in ja:
            print(f"[load] {uf}: já carregada, pulando"); continue
        z = RAW / f"bweb_1t_{uf}_{STAMP}.zip"
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if m.lower().endswith(".csv"):
                    zf.extract(m, CSV)
        f = str(CSV / f"bweb_1t_{uf}_{STAMP}.csv")
        src = f"""SELECT * FROM read_csv({f!r}, delim=';', header=true, encoding='latin-1',
                               all_varchar=true, ignore_errors=false)"""
        if not tem_tabela:
            con.execute(f"CREATE TABLE bu AS {src}"); tem_tabela = True
        else:
            con.execute(f"INSERT INTO bu BY NAME {src}")
        n = con.execute("SELECT count(*) FROM bu WHERE SG_UF = ?", [uf]).fetchone()[0]
        print(f"[load] {uf}: {n:,} linhas".replace(",", "."))
    cols = [c[0] for c in con.execute("DESCRIBE bu").fetchall()]
    print("[load] colunas:", ", ".join(cols))
    # Layout 2026 (conferido no _leiame-boletimurnaweb.pdf dentro do ZIP):
    #   QT_ELEITORES_BIOMETRIA_NH -> QT_ELEI_BIOM_SEM_HABILITACAO ("quantidade de eleitoras e eleitores
    #   com biometria, mas que não foram habilitados por meio dela");
    #   HR_ABERTURA / HR_ENCERRAMENTO -> DT_ABERTURA / DT_ENCERRAMENTO ("data e hora de abertura /
    #   encerramento da urna eletrônica para votação", formato 'YYYY-MM-DD HH:MM:SS', relógio local).
    need = ["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "QT_ELEI_BIOM_SEM_HABILITACAO",
            "DT_ABERTURA", "DT_ENCERRAMENTO", "NR_ZONA", "NR_SECAO", "CD_MUNICIPIO",
            "NM_MUNICIPIO", "SG_UF", "DS_CARGO_PERGUNTA", "NR_VOTAVEL", "NM_VOTAVEL",
            "QT_VOTOS", "CD_TIPO_VOTAVEL", "NR_URNA_EFETIVADA", "DS_TIPO_URNA"]
    missing = [c for c in need if c not in cols]
    if missing:
        print("[load] AVISO: layout 2026 não tem as colunas esperadas:", missing)
        print("       Ajuste os nomes em analyze() antes de rodar.")
    print("[load] linhas:", con.execute("SELECT count(*) FROM bu").fetchone()[0])

# ---------------------------------------------------------------- analyze
def build_tables(con):
    """Cria as tabelas temporárias secao (1 linha por urna/BU), m (taxas) e z (z-scores no município)."""

    # Uma linha por seção (o BU repete os campos de seção para cada votável; usamos
    # o cargo Presidente para deduplicar — qualquer cargo serve, os campos são iguais).
    con.execute("""
        CREATE OR REPLACE TEMP TABLE secao AS
        SELECT DISTINCT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO,
               NR_URNA_EFETIVADA, CD_TIPO_URNA, DS_TIPO_URNA, DS_SECOES_AGREGADAS,
               CAST(QT_APTOS AS INT) aptos,
               CAST(QT_COMPARECIMENTO AS INT) comp,
               CAST(QT_ABSTENCOES AS INT) abst,
               CAST(QT_ELEI_BIOM_SEM_HABILITACAO AS INT) bio_nh,
               DT_ABERTURA, DT_ENCERRAMENTO,
               CAST(TRY_CAST(DT_ENCERRAMENTO AS TIMESTAMP) AS TIME) AS t_enc
        FROM bu WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%'
    """)
    # minutos entre o horário LOCAL previsto de encerramento e o encerramento efetivo da urna
    fech_case = " ".join(f"WHEN '{u}' THEN TIME '{h}'" for u, h in FECH_LOCAL.items())
    reg_case = " ".join(f"WHEN '{u}' THEN '{r}'" for u, r in REGIAO.items())
    con.execute(f"""
        ALTER TABLE secao ADD COLUMN min_apos_fech INT;
        UPDATE secao SET min_apos_fech =
            date_diff('minute', CASE SG_UF {fech_case} ELSE TIME '17:00:00' END, t_enc);
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE m AS
        SELECT *,
               comp * 1.0 / NULLIF(aptos,0)       AS tx_comp,
               bio_nh * 1.0 / NULLIF(comp,0)      AS tx_manual,
               (abst + comp) - aptos              AS err_soma,
               CASE SG_UF {reg_case} ELSE '?' END AS regiao,
               CD_TIPO_URNA = '1'                 AS apurada   -- DS_TIPO_URNA = 'Apurada'
        FROM secao
    """)

    con.execute("""
        CREATE OR REPLACE TEMP TABLE z AS
        SELECT *,
          (tx_manual - avg(tx_manual) OVER w) / NULLIF(stddev(tx_manual) OVER w,0) z_manual,
          (tx_comp   - avg(tx_comp)   OVER w) / NULLIF(stddev(tx_comp)   OVER w,0) z_comp,
          count(*) OVER w n_mun
        FROM m WHERE apurada WINDOW w AS (PARTITION BY SG_UF, CD_MUNICIPIO)
    """)
    return con

def analyze(foco, out="out/piloto"):
    import duckdb, pandas as pd
    OUT = Path(out); OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    build_tables(con)

    # 1. Consistência interna (deve dar zero)
    inc = con.execute("""
        SELECT SG_UF, count(*) n_secoes,
               sum(NOT apurada)   nao_apurada,
               sum(t_enc IS NULL) sem_hora_enc,
               sum(err_soma <> 0) soma_errada,
               sum(comp > aptos)  comp_maior_aptos,
               sum(bio_nh > comp) manual_maior_comp,
               sum(bio_nh < 0)    manual_negativo,
               sum(abst = 0)      zero_abstencao
        FROM m GROUP BY 1 ORDER BY 1""").df()
    inc.to_csv(OUT / "01_consistencia.csv", index=False); print(inc.to_string(index=False))

    # 2. Distribuição de habilitação manual por UF — NE vs controle
    dist = con.execute("""
        SELECT SG_UF, regiao, count(*) n,
               round(avg(tx_manual),4) media_manual,
               round(quantile_cont(tx_manual,0.5),4) mediana,
               round(quantile_cont(tx_manual,0.95),4) p95,
               round(quantile_cont(tx_manual,0.99),4) p99,
               round(avg(tx_comp),4) media_comp
        FROM m WHERE apurada GROUP BY 1,2 ORDER BY media_manual DESC""").df()
    dist.to_csv(OUT / "02_manual_por_uf.csv", index=False); print(dist.to_string(index=False))

    # 3. O teste central: habilitação manual alta E comparecimento alto E encerramento tardio,
    #    comparado com a própria vizinhança (município) — z-scores dentro do município.
    flag = con.execute(f"""
        SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, NR_URNA_EFETIVADA, DS_TIPO_URNA,
               aptos, comp, bio_nh,
               round(tx_comp,3) tx_comp, round(tx_manual,3) tx_manual,
               round(z_manual,2) z_manual, round(z_comp,2) z_comp, n_mun,
               DT_ENCERRAMENTO, min_apos_fech
        FROM z
        WHERE n_mun >= 8 AND z_manual > 3 AND z_comp > 2
        ORDER BY z_manual DESC""").df()
    flag.to_csv(OUT / "03_secoes_suspeitas.csv", index=False)
    print(f"\n[3] seções com manual>3σ E comparecimento>2σ no município: {len(flag)}")
    print(flag.head(40).to_string(index=False))

    # 4. Taxa de "suspeitas" por UF — se a hipótese NE for verdadeira, NE deve sobrar aqui
    por_uf = con.execute("""
        SELECT SG_UF, regiao, count(*) n,
               sum(z_manual > 3 AND z_comp > 2) suspeitas,
               round(1000.0*sum(z_manual > 3 AND z_comp > 2)/count(*),2) por_mil
        FROM z WHERE n_mun >= 8 GROUP BY 1,2 ORDER BY por_mil DESC""").df()
    por_uf.to_csv(OUT / "04_suspeitas_por_uf.csv", index=False); print(por_uf.to_string(index=False))

    # 5. Encerramento tardio: distribuição da hora de encerramento por UF
    enc = con.execute("""
        SELECT SG_UF, regiao, count(*) n,
               round(quantile_cont(min_apos_fech,0.5),1) mediana_min,
               round(quantile_cont(min_apos_fech,0.95),1) p95_min,
               sum(min_apos_fech > 30)  apos_30min,
               sum(min_apos_fech > 60)  apos_60min,
               sum(min_apos_fech > 120) apos_120min,
               round(100.0*sum(min_apos_fech > 30)/count(*),2) pct_apos_30min
        FROM m WHERE apurada GROUP BY 1,2 ORDER BY pct_apos_30min DESC""").df()
    enc.to_csv(OUT / "05_encerramento_por_uf.csv", index=False); print(enc.to_string(index=False))

    # 6. Correlação manual × comparecimento × voto no candidato líder (padrão Klimek)
    #    Se mesários "votam pelos ausentes" para um candidato, seções com manual alto
    #    devem mostrar comparecimento alto E desvio do voto para esse candidato.
    kl = con.execute(f"""
        WITH v AS (
          SELECT SG_UF, NR_ZONA, NR_SECAO, NR_VOTAVEL, NM_VOTAVEL,
                 CAST(QT_VOTOS AS INT) votos,
                 sum(CAST(QT_VOTOS AS INT)) OVER (PARTITION BY SG_UF,NR_ZONA,NR_SECAO) tot
          FROM bu WHERE DS_CARGO_PERGUNTA ILIKE 'Presidente%' AND CD_TIPO_VOTAVEL='1'
        )
        SELECT v.SG_UF, v.NM_VOTAVEL,
               corr(z.tx_manual, v.votos*1.0/NULLIF(v.tot,0)) corr_manual_voto,
               corr(z.tx_comp,   v.votos*1.0/NULLIF(v.tot,0)) corr_comp_voto,
               count(*) n
        FROM v JOIN z USING (SG_UF, NR_ZONA, NR_SECAO)
        WHERE v.SG_UF IN ({",".join(repr(u) for u in foco)})
        GROUP BY 1,2 HAVING n > 500 ORDER BY 1, corr_manual_voto DESC""").df()
    kl.to_csv(OUT / "06_correlacao_manual_voto.csv", index=False); print(kl.to_string(index=False))
    print(f"\nResultados em {OUT}/")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["download", "load", "analyze"])
    ap.add_argument("--uf", nargs="*", default=NORDESTE + ["SP", "RS", "MG", "PR"])
    ap.add_argument("--foco", nargs="*", default=["CE", "BA"])
    ap.add_argument("--out", default="out/piloto", help="pasta de saída do analyze")
    a = ap.parse_args()
    {"download": lambda: download(a.uf), "load": lambda: load(a.uf),
     "analyze": lambda: analyze(a.foco, a.out)}[a.cmd]()
