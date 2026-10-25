"""
Configuração por turno. Todos os scripts importam daqui; o turno vem da variável de ambiente TURNO (1 ou 2).

  TURNO=1 (padrão): caminhos idênticos aos da análise original do 1º turno (data/, out/).
  TURNO=2:          data/2t/ e out/2t/, pleito 3221, dia 25/10/2026.

O carimbo (STAMP) do arquivo de BU do 2º turno só é conhecido quando o TSE publica
(padrão DDMMAAAAHHMM do momento da geração, ex.: 2022 -> 311020221535, 2024 -> 281020241046).
`aguardar_2t.py` descobre e grava em data/2t/STAMP; também pode ser passado em STAMP_2T=... no ambiente.
"""
import os
from pathlib import Path

TURNO = int(os.environ.get("TURNO", "1"))
if TURNO not in (1, 2):
    raise SystemExit(f"TURNO={TURNO} inválido; use 1 ou 2")

_T = {
    1: dict(tag="1t", stamp="051020261403", pleito="3220", dia="04/10/2026",
            eleicoes={"6257": "Federal (Presidente)", "6259": "Estadual"}),
    2: dict(tag="2t", stamp=None, pleito="3221", dia="25/10/2026",
            eleicoes={"6258": "Federal (Presidente)", "6260": "Estadual (Governador)"}),
}[TURNO]

TAG, PLEITO, DIA, ELEICOES = _T["tag"], _T["pleito"], _T["dia"], _T["eleicoes"]

# --- caminhos -------------------------------------------------------------------------------
if TURNO == 1:
    DATA = Path("data"); OUT = Path("out"); DB = DATA / "bu2026.duckdb"
else:
    DATA = Path("data/2t"); OUT = Path("out/2t"); DB = DATA / "bu2026_2t.duckdb"
RAW = DATA / "raw"                 # ZIPs do BU (nunca alterados)
CSV = DATA / "csv"                 # CSVs extraídos (podem ser apagados após o load)
LOGS_RAW = DATA / "logs" / "raw"   # log.jez brutos
LOGS_TXT = DATA / "logs" / "txt"   # logd.dat extraídos (amostras)
PQ = DATA / "logs_parquet"         # métricas por urna e habilitações (varredura nacional)
STAMP_FILE = DATA / "STAMP"

# --- carimbo do BU ---------------------------------------------------------------------------
def _stamp():
    if _T["stamp"]:
        return _T["stamp"]
    env = os.environ.get(f"STAMP_{TAG.upper()}")
    if env:
        return env.strip()
    if STAMP_FILE.exists():
        s = STAMP_FILE.read_text().strip()
        if s:
            return s
    return None

STAMP = _stamp()

def exigir_stamp():
    """Usado por download/load: para com mensagem clara se o carimbo do 2º turno ainda não é conhecido."""
    if STAMP is None:
        raise SystemExit(f"Carimbo do BU do {TAG} ainda desconhecido. Rode `python aguardar_2t.py --once` "
                         f"(ou --auto), ou defina STAMP_{TAG.upper()}=DDMMAAAAHHMM.")
    return STAMP

def gravar_stamp(stamp):
    DATA.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text(stamp.strip())

# --- URLs --------------------------------------------------------------------------------------
BU_BASE = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb"
DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna"
LOGS_BASE = f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/{PLEITO}/dados"

def bu_zip(uf, stamp=None):
    return f"bweb_{TAG}_{uf}_{stamp or exigir_stamp()}.zip"

def aux_url(uf, mun, zona, sec):
    """uf minúscula, mun 5 dígitos, zona e seção 4 dígitos (strings já formatadas)."""
    return f"{LOGS_BASE}/{uf}/{mun}/{zona}/{sec}/p00{PLEITO}-{uf}-m{mun}-z{zona}-s{sec}-aux.json"

def resumo():
    return (f"TURNO={TURNO} ({TAG}) pleito={PLEITO} dia={DIA} stamp={STAMP or '?'} "
            f"DB={DB} OUT={OUT}")

if __name__ == "__main__":
    print(resumo())
