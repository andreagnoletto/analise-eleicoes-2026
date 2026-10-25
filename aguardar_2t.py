#!/usr/bin/env python3
"""
Vigia da publicação dos dados do 2º turno (25/10/2026, pleito 3221).

  python aguardar_2t.py --once                 # verifica agora e sai
  python aguardar_2t.py                        # verifica a cada 10 min até o BU aparecer
  python aguardar_2t.py --auto                 # ao detectar o BU: grava o carimbo, baixa as 28 UFs, carrega,
                                               # roda analise_brasil.py e segue vigiando os logs de urna
O que verifica:
  1. BU: recursos do dataset "resultados-2026-boletim-de-urna" (API CKAN, com fallback para a página HTML)
     procurando bweb_2t_<UF>_<carimbo>.zip. Em 2022 e 2024 o BU do 2º turno saiu no dia seguinte à eleição.
  2. Logs de urna: aux.json de seções-sonda no pleito 3221 (os arquivos aparecem progressivamente na
     noite da eleição, por seção totalizada).
  3. Disco livre (BU do 2º turno: ~45 GB; varredura de logs: +55 GB).
Nunca inicia a varredura nacional dos logs (15 h, 51 GB): isso é decisão do usuário.
"""
import argparse, os, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
import requests

os.environ["TURNO"] = "2"
import config as cfg
import pipeline_bu as pb

CKAN = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=resultados-2026-boletim-de-urna"
RE_ZIP = re.compile(r"bweb_2t_([A-Z]{2})_(\d{12})\.zip(?!\.sha)")
# seções-sonda para os logs: Bom Lugar/MA (achado do 1º turno), 1ª seção do AC, uma de SP e uma do exterior
SONDAS = [("ma", "07285", "0066", "0041"), ("ac", "01120", "0001", "0001"),
          ("sp", "71072", "0001", "0001"), ("zz", "29890", "0001", "0001")]
LOG = cfg.OUT / "aguardar.log"
GB = 1 << 30


def log(msg):
    linha = f"{datetime.now():%d/%m %H:%M:%S} {msg}"
    print(linha, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def checar_bu(sess):
    """-> (stamp, ufs) ou (None, set()). Lê a API CKAN; se falhar, raspa a página HTML."""
    texto = ""
    try:
        j = sess.get(CKAN, timeout=60).json()
        texto = " ".join(r.get("url", "") + " " + r.get("name", "") for r in j["result"]["resources"])
    except Exception as e:
        log(f"  CKAN indisponível ({type(e).__name__}); tentando a página HTML")
        try:
            texto = sess.get(cfg.DATASET_URL, timeout=60).text
        except Exception as e2:
            log(f"  página HTML indisponível ({type(e2).__name__})")
            return None, set()
    achados = RE_ZIP.findall(texto)
    if not achados:
        return None, set()
    stamps = sorted({s for _, s in achados})
    if len(stamps) > 1:
        log(f"  AVISO: mais de um carimbo publicado para o 2t: {stamps}; usando o mais recente")
    stamp = stamps[-1]
    ufs = {uf for uf, s in achados if s == stamp}
    return stamp, ufs


def checar_logs(sess):
    ok = 0
    for uf, mun, zona, sec in SONDAS:
        try:
            if sess.head(cfg.aux_url(uf, mun, zona, sec), timeout=30).status_code == 200:
                ok += 1
        except Exception:
            pass
    return ok


def disco_gb():
    return shutil.disk_usage(".").free / GB


def rodar(*args):
    cmd = [sys.executable, *args]
    log("  $ " + " ".join(cmd[1:]))
    r = subprocess.run(cmd, env={**os.environ, "TURNO": "2"})
    if r.returncode != 0:
        log(f"  FALHOU (exit {r.returncode}); parando. Resolva e rode os passos manualmente.")
        sys.exit(r.returncode)


def fase_bu(stamp):
    cfg.gravar_stamp(stamp)
    log(f"  carimbo gravado em {cfg.STAMP_FILE}: {stamp}")
    if disco_gb() < 50:
        log(f"  disco livre {disco_gb():.0f} GB < 50 GB; libere espaço e rode manualmente"); sys.exit(2)
    rodar("pipeline_bu.py", "download", "--uf", "ALL")
    rodar("pipeline_bu.py", "load", "--uf", "ALL")
    rodar("pipeline_bu.py", "analyze", "--foco", "CE", "BA", "--out", str(cfg.OUT / "piloto"))
    rodar("analise_brasil.py", "--out", str(cfg.OUT / "brasil"))
    if Path("data/bu2026.duckdb").exists():
        rodar("comparar_turnos.py", "bu", "--out", str(cfg.OUT / "comparacao"))
    else:
        log("  BU do 1º turno não está em data/bu2026.duckdb; comparar_turnos.py bu fica para depois")
    log("  FASE 1 (BU) concluída. Relatórios em " + str(cfg.OUT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="verifica uma vez e sai")
    ap.add_argument("--auto", action="store_true", help="ao detectar o BU, baixa, carrega e analisa")
    ap.add_argument("--intervalo", type=int, default=10, help="minutos entre verificações")
    a = ap.parse_args()
    sess = requests.Session(); sess.headers["User-Agent"] = "Mozilla/5.0 (analise-bu-2026)"
    bu_feito = cfg.STAMP is not None and cfg.DB.exists()
    while True:
        stamp, ufs = checar_bu(sess)
        n_logs = checar_logs(sess)
        bu_txt = f"BU 2t: {len(ufs)}/28 UFs, carimbo {stamp}" if stamp else "BU 2t: ainda não publicado"
        log(f"{bu_txt} | logs 2t: {n_logs}/{len(SONDAS)} sondas | disco livre {disco_gb():.0f} GB")
        if stamp and not bu_feito:
            if len(ufs) < 28:
                log(f"  publicação parcial ({sorted(ufs)}); aguardando as 28 UFs")
            elif a.auto:
                fase_bu(stamp); bu_feito = True
            else:
                log(f"  Para começar: TURNO=2 python pipeline_bu.py download --uf ALL --stamp {stamp}")
                if not a.once:
                    return
        if n_logs == len(SONDAS):
            log("  Logs de urna do 2t disponíveis nas sondas. Próximo passo (decisão sua): "
                "TURNO=2 python logs_urna.py selecionar_2t ... e depois logs_brasil.py scan --uf ALL")
            if bu_feito or not a.auto:
                return
        if a.once:
            return
        time.sleep(a.intervalo * 60)


if __name__ == "__main__":
    main()
