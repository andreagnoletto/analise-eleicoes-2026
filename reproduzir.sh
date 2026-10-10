#!/usr/bin/env bash
# Reproduz o estudo inteiro, na ordem das fases. Leia docs/REPRODUCAO.md antes:
# precisa de ~100 GB de disco e a varredura nacional (fase 5) leva ~15 h.
#
#   bash reproduzir.sh            # tudo
#   bash reproduzir.sh piloto     # só a fase 1
#   bash reproduzir.sh brasil     # fases 1 e 2 (BU de todas as UFs)
#   bash reproduzir.sh logs       # fases 1 a 4 (sem a varredura nacional)
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python}
WORKERS=${WORKERS:-32}
ATE=${1:-tudo}

TODAS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ"

echo "== Fase 1: piloto (CE BA vs RS PR)"
$PY pipeline_bu.py download --uf CE BA RS PR
$PY pipeline_bu.py load     --uf CE BA RS PR
$PY pipeline_bu.py analyze  --foco CE BA --out out/piloto
$PY piloto_extras.py        --uf CE BA RS PR --foco CE BA --out out/piloto
[ "$ATE" = piloto ] && exit 0

echo "== Fase 2: BU de todas as UFs"
$PY pipeline_bu.py download --uf $TODAS
$PY pipeline_bu.py load     --uf $TODAS
$PY analise_brasil.py       --out out/brasil
[ "$ATE" = brasil ] && exit 0

echo "== Fase 3: logs, amostra de flagradas e controles"
for cmd in selecionar baixar parsear analisar; do $PY logs_urna.py $cmd --out out/logs; done

echo "== Fase 4: logs, 1.000 urnas do NE fechadas no horário + 300 controles"
$PY logs_urna.py selecionar_ne --out out/logs_ne
for cmd in baixar parsear analisar; do $PY logs_urna.py $cmd --out out/logs_ne; done
[ "$ATE" = logs ] && exit 0

echo "== Fase 5: varredura nacional dos logs (retomável; ~15 h com $WORKERS conexões)"
$PY logs_brasil.py scan --uf ALL --workers "$WORKERS"
$PY analise_logs_brasil.py --out out/logs_brasil

echo "== Concluído. Relatórios em out/*/RELATORIO.md"
