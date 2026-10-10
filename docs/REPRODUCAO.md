# Reprodução passo a passo

Tempos medidos em um notebook Windows 11 com conexão doméstica. Disco total necessário: cerca de 100 GB. Nada em `data/raw` é alterado; tudo o que os scripts escrevem vai para `data/` (intermediários) e `out/` (resultados).

## Ambiente

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Versões com que o estudo foi rodado: Python 3.12.10, duckdb 1.5.6, pandas 3.0.6, matplotlib 3.11.2, requests 2.34.2. Não há dependência de pyarrow: Parquet é lido e escrito pelo DuckDB.

## Etapas

| Etapa | Comando | Tempo | Disco acrescentado |
|---|---|---|---|
| Download do BU (1 UF, teste) | `python pipeline_bu.py download --uf AC` | < 1 min | 20 MB |
| Download do BU (28 arquivos) | `python pipeline_bu.py download --uf <todas>` | 20 a 40 min | 4,7 GB em `data/raw` |
| Carga em DuckDB | `python pipeline_bu.py load --uf <todas>` | ~40 min | 36 GB em `data/csv` + 4,2 GB `data/bu2026.duckdb` |
| Piloto | `pipeline_bu.py analyze --foco CE BA` e `piloto_extras.py` | 2 min | < 1 MB |
| Brasil (BU) | `python analise_brasil.py --out out/brasil` | 3 min | < 1 MB |
| Logs, amostra 358 | `logs_urna.py selecionar / baixar / parsear / analisar --out out/logs` | 10 min | 50 MB |
| Logs, NE 1.300 | idem com `selecionar_ne` e `--out out/logs_ne` | 25 min | 150 MB |
| Varredura nacional | `python logs_brasil.py scan --uf ALL --workers 32` | **15,5 h** | 51 GB em `data/logs/raw` + 950 MB Parquet |
| Análise da varredura | `python analise_logs_brasil.py --out out/logs_brasil` | 3 min | 40 MB |

`reproduzir.sh` encadeia tudo. Para um teste rápido do ambiente, rode só a primeira linha (AC) e `load --uf AC`.

Os CSVs extraídos em `data/csv` podem ser apagados depois da carga (36 GB); o `load` só os usa uma vez. O `load` é incremental: UFs já na tabela `bu` são puladas.

## O que esperar de cada script

### `pipeline_bu.py`
- `download`: baixa `.zip` e `.zip.sha512`, confere o hash, **para com erro** se não bater. Não refaz download de arquivo já presente e válido.
- `load`: extrai o CSV da UF, carrega com `read_csv(delim=';', encoding='latin-1', all_varchar=true)`. Primeira UF cria a tabela; as demais fazem `INSERT ... BY NAME`.
- `analyze`: testes 1 a 6 (ver `docs/METODOLOGIA.md`). Teste 1 deve dar zero; se não der, pare e investigue antes de seguir.

### `logs_urna.py`
- `selecionar` / `selecionar_ne`: precisa do DuckDB carregado e, para `selecionar`, de `out/brasil/secoes_flagradas_brasil.csv`.
- `baixar`: grava `data/logs/raw/<k>-log.jez` e o texto extraído em `data/logs/txt/<k>.logd.dat`. Pula arquivos existentes.
- `parsear`: `01_eleitores.csv` (uma linha por habilitação) e `02_secoes_metricas.csv`.
- `analisar`: resumo por grupo, gráficos, limites dos controles e lista de anomalias.

### `logs_brasil.py scan`
- Ordem: UFs menores primeiro, SP por último, para falhar cedo.
- Cada seção: 1 GET do `aux.json` + 1 GET do `log.jez`, 4 tentativas com backoff; o ZIP é validado antes de gravar. Arquivos já presentes em `data/logs/raw` não são baixados de novo, então **o scan é retomável**: basta rodar o mesmo comando.
- Saída por UF: `data/logs_parquet/secoes_<UF>.parquet` e `eleitores_<UF>_<nnn>.parquet` (partes de ~4.000 urnas). Falhas em `data/logs_parquet/falhas.csv`. Progresso em `out/logs_brasil/progresso.log`.
- Para refazer uma UF, apague os Parquet dela (os `.jez` ficam e serão reutilizados).
- O portal do TSE respondeu a 32 conexões simultâneas sem bloqueio durante toda a varredura; o cabeçalho de rate-limit indicava 2.000 req/s. Não há motivo para ir além disso.

## Problemas conhecidos e como foram tratados

| Sintoma | Causa | Tratamento |
|---|---|---|
| `load` falha por falta de espaço | CSVs ocupam 36 GB | liberar disco; o load é incremental, basta rodar de novo |
| `analyze` acusa seções sem hora de encerramento | 28 seções no exterior e 2 em MG não têm `DT_ENCERRAMENTO` nem log no portal | são contadas em `01_consistencia.csv` e excluídas dos testes de horário |
| Votos do log abaixo do BU em algumas urnas | urna de contingência; o `log.jez` contém outro `.jez` com o log da urna original | `extrair_logs()` extrai recursivamente |
| Comparecimento do log ≠ BU em ~26 urnas | log de contingência incompleto | listadas em `01_validacao_uf.csv`; não afetam agregados |
| `HTTPSConnectionPool` / `list index out of range` no scan | queda de conexão / seção sem arquivo de log | retry automático; o que sobrar vai para `falhas.csv`. Na execução original: 22 no RS (recuperadas ao rodar de novo), 28 ZZ e 2 MG (sem arquivo) |
| `py7zr` reclama que não é 7z | `log.jez` de 2026 é ZIP | `zipfile`; `py7zr` não é necessário |
| Consultas com `CD_MUNICIPIO = '07285'` vazias | o BU grava sem zero à esquerda | usar `'7285'` ou `CAST(CD_MUNICIPIO AS INT)` |
| HEAD no CDN retorna `Content-Length: 1` | comportamento do CDN para algumas UFs | o tamanho real está no ETag; os scripts não dependem do HEAD |

## Reanalisar sem baixar nada

Os agregados suficientes para refazer as fases 2 e 5 estão versionados:

- `out/brasil/secoes_flagradas_brasil.csv`: todas as seções com qualquer flag do BU, com z-scores e horário;
- `out/logs_brasil/secoes_logs_brasil.parquet`: 497.895 urnas × 48 métricas do log;
- `out/logs_brasil/06_locais_razao_duracao.parquet` e `06_municipios_razao_duracao.csv`: agregações por local e município.

Com DuckDB:

```sql
SELECT SG_UF, regiao, count(*) urnas, round(avg(razao_dur_manual_bio),3) razao_media
FROM 'out/logs_brasil/secoes_logs_brasil.parquet'
WHERE log_manual >= 10 AND log_bio >= 10
GROUP BY ALL ORDER BY razao_media;
```

Os arquivos por habilitação (`01_eleitores.csv` das fases 3 e 4 e `data/logs_parquet/eleitores_*.parquet`, 118 milhões de linhas) não estão versionados e são regenerados por `parsear` e `scan`.
