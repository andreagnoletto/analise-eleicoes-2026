# Dados: fontes, formatos e dicionário dos arquivos de saída

## Fontes (TSE)

| Dado | URL | Formato | Tamanho |
|---|---|---|---|
| Boletim de Urna Web, 1º turno | `https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb/bweb_1t_<UF>_051020261403.zip` (+ `.zip.sha512`) | ZIP com CSV `;` Latin-1 e `_leiame-boletimurnaweb.pdf` | 4,7 GB (28 ZIPs), 36 GB extraído |
| Índice de arquivos da seção | `https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/<uf>/<mun5>/<zona4>/<sec4>/p003220-<uf>-m<mun5>-z<zona4>-s<sec4>-aux.json` | JSON (`hashes[].hash`, `hashes[].arq[].nm/tp`) | ~1 KB cada |
| Log de urna | `<pasta da seção>/<hash>/o03220<uf><mun5><zona4><sec4>-log.jez` | ZIP com `logd.dat` (TAB, Latin-1); pode conter outro `.jez` aninhado | 51 GB (499.176 arquivos) |

Página do dataset: <https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna>. Pleito 3220; eleições 6257 e 6259; data da votação 04/10/2026.

Identificador de seção usado em todo o repositório: `k = <uf minúscula>-<município 5 dígitos>-<zona 4 dígitos>-<seção 4 dígitos>`, por exemplo `ma-07285-0066-0121`.

## O que está versionado e o que não está

Versionado em `out/`: todos os CSV, PNG, Markdown e Parquet com menos de 20 MB, mais `out/logs_brasil/secoes_logs_brasil.parquet` (35 MB), porque permite reanalisar a varredura inteira sem baixar 51 GB.

Fora do repositório (ver `.gitignore`): `data/` inteiro, `out/logs/01_eleitores.csv` (12 MB) e `out/logs_ne/01_eleitores.csv` (39 MB). Esses dois são regenerados por `logs_urna.py parsear` em minutos.

## Dicionário: `out/piloto/` e `out/brasil/` (BU)

| Arquivo | Conteúdo |
|---|---|
| `01_consistencia.csv` | teste 1 por UF: inconsistências aritméticas, não apuradas, sem hora, manual negativo |
| `02_manual_por_uf.csv` | taxa manual: média, mediana, p95, seções |
| `03_secoes_suspeitas.csv` | seções com `FLAG_ORIG` (z no município) |
| `04_suspeitas_por_uf.csv` | suspeitas por mil seções |
| `05_encerramento_por_uf.csv` | minutos após o encerramento previsto local: mediana, p95, % > 30/60/120 |
| `06_correlacao_manual_voto.csv` | corr(tx_manual, % candidato) por UF, bruta e intra-município |
| `06a`–`06d_*.png` (piloto) | histograma da taxa manual, scatter manual × comparecimento, ECDF do encerramento, suspeitas por mil |
| `07_secoes_flagradas_detalhe.csv` (piloto) | por seção flagrada: % de cada candidato na seção, no município e diferença em pontos |
| `08_*` (piloto) / `12_*` (brasil) | estratificações: quartil de aptos, `DS_TIPO_URNA`, série da urna (proxy de modelo), porte do município |
| `11_ranking_uf.csv`, `11_regioes.csv`, `11_nacional.csv`, `11a`–`11d_*.png` | rankings nacionais: manual, suspeitas (orig e cal), encerramento tardio, regiões |
| `13_regionalidade_padronizada.csv`, `13_NE_vs_outros_por_celula.csv` | padronização direta por célula (quartil × série × porte) |
| `15_correlacao_manual_voto_uf.csv` | correlações para as 27 UFs |
| `16_*` | manual × encerramento tardio; `16b` = flag condicional ao encerramento tardio |
| `secoes_flagradas_brasil.csv` | **todas as seções com `flag_orig`, `flag_cal` ou `flag_tard`**, com z-scores, horário, série, município |
| `RELATORIO.md` | relatório da fase |

Colunas recorrentes: `aptos`, `comp`, `bio_nh` (manuais), `tx_comp`, `tx_manual`, `z_manual`, `z_comp`, `n_mun` (seções no município), `min_apos_fech` (minutos após o encerramento previsto **local**), `quartil_aptos` (Q1 menor), `serie_lo` (série < 2,0 milhões), `porte` (`1_capital`, `2_mais_100k`, `3_ate_100k`).

## Dicionário: `out/logs/`, `out/logs_ne/`, `out/logs_bomlugar/` (amostras de logs)

| Arquivo | Conteúdo |
|---|---|
| `00_amostra.csv` | seções selecionadas, grupo (`A_calibrado`, `B_manual_tardia`, `C_controle_municipio`, `D_controle_nacional`; `E_NE_suspeitas_horario_normal`, `F_NE_controle_horario_normal`), dados do BU e `k` |
| `01_eleitores.csv` | **uma linha por habilitação**: `k`, `grupo`, `t_hab`, `tipo` (`biometrica`, `manual`, `sem_biometria`), `tentativas`, `t_voto`, `dur_s` |
| `02_secoes_metricas.csv` | métricas por urna (subconjunto das 48 da varredura) + `modelo` |
| `03_resumo_grupos.csv` | medianas e somas por grupo |
| `04_perfil_horario.png` | fração de votos e de manuais por hora do dia, por grupo |
| `05_scatter_ultima_hora.png` | fração de manuais × fração de votos na última hora |
| `06_timelines_flagradas.png` | linha do tempo das urnas com manuais mais concentradas no fim |
| `07_limites_anomalias.csv` | p95/p5 do grupo de controle usados como limiar |
| `08_secoes_com_anomalia.csv` | urnas acima dos limiares, por anomalia |
| `09_duracao_manual_vs_bio.csv`, `10_razao_duracao_todas_amostras.csv` (NE) | razão de duração manual/biométrico por urna |

## Dicionário: `out/logs_brasil/` (varredura nacional)

| Arquivo | Conteúdo |
|---|---|
| `01_validacao_uf.csv` | por UF: urnas, comparecimento bate com BU, manuais batem, modelo identificado |
| `02_modelo_nacional.csv`, `02_modelo_uf.csv` | por modelo (UE2013/2015/2020/2022): urnas, taxa manual, % com ≥ 50% manual, duração do voto, encerramento |
| `03_tempo_voto_uf.csv` | por UF: duração mediana do voto, intervalo entre votos, encerramento |
| `04_quantis_nacionais.csv` | p0,1 … p99,9 das métricas usadas nas flags, com n |
| `05_urnas_flagradas.csv` | urnas com qualquer flag (`f_manual_rapido`, `f_manual_fim`, `f_votos_rapidos_fim`, `f_leitor_degrada_tarde`, `f_manual_lt30`) |
| `05_flags_por_regiao.csv`, `05_flags_por_uf.csv` | contagem de flags |
| `06_locais_flagrados_manual_rapido.csv` | locais de votação com razão de duração < p0,1 (≥ 30 manuais e ≥ 30 biométricos) |
| `06_locais_razao_duracao.parquet` | **todos** os 68.018 locais elegíveis |
| `06_municipios_razao_duracao.csv` | 5.520 municípios com ≥ 100 manuais, ordenados pela razão, com locais flagrados |
| `07_hist_razao_duracao.png`, `07_manual_por_modelo_uf.png`, `07_tempo_voto_uf.png` | figuras |
| `secoes_logs_brasil.parquet` | **497.895 urnas × 48 métricas** (ver `docs/METODOLOGIA.md` §4.4) + `SG_UF`, `CD_MUNICIPIO`, `NR_ZONA`, `NR_SECAO`, `NR_LOCAL_VOTACAO`, `regiao` |
| `progresso.log` | log da execução do scan (tempos, falhas, validação por UF) |

## Intermediários em `data/` (não versionados)

| Caminho | Conteúdo |
|---|---|
| `data/raw/*.zip`, `*.zip.sha512` | brutos do TSE, nunca alterados |
| `data/csv/*.csv` | CSVs extraídos; podem ser apagados após o `load` |
| `data/bu2026.duckdb` | tabela `bu` (67,9 milhões de linhas, todas as colunas como texto) |
| `data/logs/raw/<k>-log.jez` | logs brutos |
| `data/logs/txt/<k>.logd.dat` | texto extraído (só amostras) |
| `data/logs_parquet/secoes_<UF>.parquet` | métricas por urna, por UF |
| `data/logs_parquet/eleitores_<UF>_<nnn>.parquet` | uma linha por habilitação, 118 milhões no total |
| `data/logs_parquet/falhas.csv` | seções que falharam no scan |
