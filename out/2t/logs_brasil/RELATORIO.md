# Logs de urna — varredura nacional do 2º turno (499.177 urnas, 25/10/2026)

Varredura de 25/10 22h às 26/10 21h32 (23,5 h, 24 conexões, `logs_brasil.py scan` e `retry`), feita **antes da publicação do BU do 2º turno** (ainda não disponível nos Dados Abertos às 21h30 de 26/10): a lista de seções veio do BU do 1º turno e os campos `bu_*` estão nulos, a preencher com `logs_brasil.py anexar_bu` quando o CSV sair. Análise em `analise_logs_brasil.py` e comparação com o 1º turno em `comparar_turnos.py logs` (`out/2t/comparacao/30_*` a `33_*`).

Cobertura: **499.177 das 499.206 seções** do BU do 1º turno (497.896 sem o exterior). Faltam 29 sem arquivo de log no portal (28 no exterior, 1 em SP). Na primeira passada, 406 falhas (376 do exterior ainda não totalizadas às 22h da eleição, 23 de SC por conexão, 7 de RR/AP); 377 recuperadas no `retry`. Modelo de urna identificado em 100%; 4 urnas sem registro de encerramento. Urnas pareadas com o 1º turno: 497.894.

## Resumo executivo
1. **Habilitação manual concentrada no fim da sessão: não existe, pela terceira vez.** Em todas as 27 UFs a mediana da razão entre a fração das manuais na última hora e a fração dos votos é ≤ 0,68. Acima do p99,9 nacional (razão > 10, ≥ 5 manuais na última hora): 3 urnas em 497.896, com 5 a 10 manuais cada (São Valério do Sul/RS, 2; São Francisco do Conde/BA, 1). Predição L4 confirmada.
2. **Encerramento no horário em todo o país.** Mediana por UF de 0,5 a 3,3 min após o horário local (1º turno: 1,2 a 31,4). A diferença Nordeste–Sul desapareceu: BA 1,6 min contra SC 0,5 (no 1º turno 18,5 contra 1,3); AL 1,3 (31,4); PE 1,9 (29,5). Urnas > 30 min tarde: 1,5% (1º turno: 19%).
3. **O voto dura 10 s** (habilitação → computado) em 21 UFs e **16 a 17 s nas 6 UFs com 2º turno para governador** (AC, AM, DF, ES, RN, TO, conferidas no portal do TSE), contra 51 a 63 s no 1º turno. O custo de um cargo a mais é 6 a 7 s. Predição L1 confirmada em 27/27 UFs. A predição L2 (ordem das UFs por tempo de voto se mantém, ρ > 0,7) **falhou** (ρ = 0,50) porque a cédula do 2º turno não é igual entre UFs, o que a predição não previu; entre as 21 UFs com um só cargo, MA, PI e PA continuam as mais lentas (11 s contra 10 s).
4. **A taxa manual é do leitor e do eleitorado, não do dia.** Por modelo: UE2013 11,0% (1º turno 11,1%), UE2015 9,8% (9,7%), UE2020 6,2% (6,1%), UE2022 6,2% (6,1%). Correlação urna a urna entre turnos: 0,76 a 0,81 em todas as regiões. Predição L3 confirmada.
5. **O critério de Bom Lugar, aplicado ao país no 2º turno, não devolve Bom Lugar nem nenhum outro cluster.** A razão de duração manual/biométrico tem mediana 1,19 (1º turno 1,26) e p0,1 de 0,62 (0,80); com votos de 10 s ela é quantizada e ruidosa (correlação urna a urna entre turnos 0,22 a 0,25). 393 urnas abaixo do p0,1, proporcionais às regiões (SE 1,0‰, CO 0,8‰, NE 0,7‰, S 0,5‰, N 0,5‰); por município, só capitais grandes aparecem (São Paulo 54, Rio 14, Salvador 13, Belo Horizonte 11). 58 locais de votação abaixo do p0,1 (0,818), espalhados por 20 UFs; nenhum município tem mais de 2. Dos 66 locais flagrados no 1º turno, 2 repetem (esperado 0,07): Ibotirama/BA z173 local 1171 (0,90 → 0,73) e Nhamundá/AM z43 local 1430 (0,91 → 0,80), ambos no limite nos dois turnos. **Bom Lugar caiu da 1ª para a 156ª posição** entre 5.515 municípios (razão 0,785 → 1,09; 0 locais flagrados); Maranhãozinho da 2ª para a 192ª (0,97 → 1,09). Predição L5: o padrão não era estável; a ressalva de poder do teste com cédula curta vale (ver `out/2t/logs_rep/RELATORIO.md`).
6. **A prorrogação até as 19h, vista pelos logs.** 7.577 urnas (1,5%) encerraram mais de 30 min após o horário, e em RJ, SP, BA, PE, PB e SE de 83% a 98% delas encerraram entre 18h55 e 19h10, concentradas por zona (Niterói z144: 314 de 335 urnas; Petrópolis z65: 297 de 345; Rio de Janeiro z238, z9, z245, z234, z122, z120; Itaboraí z104; no RJ, 8,8% das urnas). É o efeito da decisão do STF (ministro Zanin) que, no fim da tarde de 25/10, prorrogou a votação até as 19h nas seções ainda abertas, a pedido da campanha de Lula por restrições no transporte, executada pelo TSE e pelos TREs (fontes: [Agência Brasil](https://agenciabrasil.ebc.com.br/politica/noticia/2026-10/tse-secoes-eleitorais-ainda-abertas-devem-manter-votacao-ate-19h), [TRE-RJ via Agência Brasil](https://agenciabrasil.ebc.com.br/justica/noticia/2026-10/tre-rj-diz-que-secoes-eleitorais-ficarao-abertas-ate-19h), [Poder360](https://www.poder360.com.br/poder-eleicoes-2026/zanin-prorroga-votacao-do-2o-turno-ate-19h/), [Forbes](https://forbes.com.br/geral/2026/10/secoes-eleitorais-ainda-abertas-devem-manter-votacao-ate-as-19h-determina-tse/)). Os logs batem com os números divulgados: votos entre 18h e 19h, RJ 875 (divulgado 879), SP 639 (636), BA 287 (285). No total, 31.060 votos após o horário local previsto, dos quais 2.512 por habilitação manual (8,1%, a mesma taxa do dia). A prorrogação, portanto, não concentrou habilitações manuais e as urnas que ficaram abertas receberam em mediana 0 votos no período.

## Validação (`01_validacao_uf.csv`)
Sem BU do 2º turno, a conferência de comparecimento e de manuais fica pendente; `anexar_bu` a fará por urna quando o CSV for publicado. Modelo identificado em 499.177; 4 urnas sem encerramento (ES, RS, SC, ZZ).

## Por modelo (`02_modelo_nacional.csv`, `02_modelo_uf.csv`, `07_manual_por_modelo_uf.png`)

| Modelo | urnas | taxa manual média | urnas com ≥ 50% manual | voto (s) | encerramento (min após o horário, média) |
|---|---|---|---|---|---|
| UE2013 | 11.434 | 11,0% | 0,73% | 12,0 | 3,6 |
| UE2015 | 87.212 | 9,8% | 0,01% | 12,4 | 3,5 |
| UE2020 | 200.504 | 6,2% | 0,00% | 10,4 | 3,7 |
| UE2022 | 198.746 | 6,2% | 0,00% | 10,4 | 3,3 |

## Tempo por voto e encerramento (`03_tempo_voto_uf.csv`, `07_tempo_voto_uf.png`, `../comparacao/30_uf_tempo.csv`)
Voto mediano: ES, TO, AC 17 s; AM, RN, DF 16 s; PI, MA, PA 11 s; demais 10 s. Intervalo entre votos: 63 a 91 s (1º turno 94 a 118). Encerramento mediano (min após o horário local): RJ 2,1, PE 1,9, BA 1,6, SP 1,6, MT 1,4, RO 1,5, demais ≤ 1,4; o 1º turno ia de 1,2 (RS) a 31,4 (AL).

## Quantis nacionais e flags (`04_quantis_nacionais.csv`, `05_*.csv`)

| Métrica | n | p0,1 | p1 | p50 | p99 | p99,9 |
|---|---|---|---|---|---|---|
| razão duração manual/biométrico (≥ 10 e ≥ 10) | 401.617 | 0,62 | 0,75 | 1,19 | 2,14 | 3,20 |
| razão manual/votos na última hora (≥ 5 manuais) | 2.058 | 0,67 | 0,83 | 2,11 | 5,68 | 10,1 |
| intervalo mediano entre votos na última hora (s) | 348.041 | 47 | 56 | 134 | 327 | 395 |
| salto da taxa manual 8–11h → 14–17h | 494.569 | −0,20 | −0,14 | −0,01 | 0,11 | 0,19 |

Só 2.058 urnas têm ≥ 5 manuais na última hora (9.851 no 1º turno): com 10 a 20 manuais por urna e 5% dos votos na última hora, a maioria não tem nenhuma. A métrica "manuais em < 30 s" perdeu sentido (94% dos manuais votam em menos de 30 s) e não gera flag.

Flags a 0,1% nacional, por região (N / NE / CO / SE / S): manuais rápidos 22 / 102 / 31 / 200 / 38; manuais no fim 0 / 1 / 0 / 0 / 2; votos rápidos no fim 25 / 141 / 14 / 78 / 84; leitor degrada à tarde 52 / 126 / 68 / 166 / 76. Por mil urnas, nenhuma região passa de 2× a média em nenhuma flag; "votos rápidos no fim" é maior no S (1,2‰) e NE (1,0‰).

## Comparação com o 1º turno (`../comparacao/`)
| Arquivo | Resultado |
|---|---|
| `30_modelo.csv` | taxa manual por modelo igual nos dois turnos (diferença ≤ 0,2 pp); duração 54–58 s → 10–12 s; encerramento 15–23 min → 3–4 min |
| `30_uf_tempo.csv` | duração, intervalo e encerramento por UF nos dois turnos |
| `31_locais_flagrados_1t_no_2t.csv` | 66 locais flagrados no 1º turno; 2 repetem (esperado 0,07) |
| `31_bom_lugar_maranhaozinho.csv` | os 14 locais pareados dos dois municípios: 0,59–1,16 → 0,82–1,25 |
| `32_persistencia_urna.csv` | corr(1t, 2t) por urna: taxa manual 0,76–0,81; razão de duração 0,22–0,25; manuais no fim 0,09–0,11 |
| `33_predicoes_logs.csv` | L1 ✓, L2 ✗ (cédula desigual entre UFs), L3 ✓, L4 ✓, L5 não repetiu |

## Anomalia ≠ fraude
| Achado | Explicação inocente | O que descarta |
|---|---|---|
| 7.577 urnas encerradas às 19h, quase sem votos após as 17h | prorrogação determinada pelo STF para as seções ainda abertas; confirmada por notícias e pelos totais por UF, que batem com os logs a ±4 votos | explicado |
| 3 urnas com manuais no fim | 5 a 10 manuais em 7 a 23 votos | nenhuma repete em outro critério |
| 58 locais com manuais em 7 s contra 10–11 s | com um cargo, 7 s é o mínimo físico (2 dígitos e confirma); razão quantizada | nenhum cluster por município; 2 repetem do 1º turno, no limite |
| Bom Lugar e Maranhãozinho voltam ao normal | o padrão do 1º turno dependia da cédula longa | o 1º turno continua pedindo o caderno de votação |

## Conclusão
Nas 499.177 urnas do 2º turno, com os mesmos critérios do 1º turno: não há habilitação manual concentrada no fim da sessão em nenhuma UF, região ou cluster; não há votos após o horário; o encerramento tardio do Nordeste desapareceu junto com a cédula longa, como o modelo de tempo por eleitor previa; a taxa manual por modelo e por urna é a mesma dos dois turnos. O único achado localizado do 1º turno (Bom Lugar e Maranhãozinho) não se repete e esses municípios estão na mediana nacional. A prorrogação até as 19h determinada pelo STF aparece nos logs como 7,6 mil urnas abertas até essa hora, com 31 mil votos após o horário no país (8,1% manuais, igual ao resto do dia) e totais por UF idênticos aos divulgados pela Justiça Eleitoral. Pendências: anexar o BU quando publicado (validação de comparecimento, predições P1–P5 e comparação por seção).

## Arquivos (`out/2t/logs_brasil/`)
`01_validacao_uf.csv`, `02_modelo_nacional.csv`, `02_modelo_uf.csv`, `03_tempo_voto_uf.csv`, `04_quantis_nacionais.csv`, `05_urnas_flagradas.csv`, `05_flags_por_regiao.csv`, `05_flags_por_uf.csv`, `06_locais_flagrados_manual_rapido.csv`, `06_locais_razao_duracao.parquet`, `06_municipios_razao_duracao.csv`, `07_hist_razao_duracao.png`, `07_manual_por_modelo_uf.png`, `07_tempo_voto_uf.png`, `secoes_logs_brasil.parquet` (497.896 urnas × 48 métricas, `bu_*` nulos), `progresso.log`. Brutos: `data/2t/logs/raw` (~50 GB), `data/2t/logs_parquet`.
