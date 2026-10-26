# 2º turno, logs de urna: as mesmas urnas investigadas no 1º turno

Noite da eleição (25/10/2026, 22h–23h40). O BU do 2º turno ainda não foi publicado; os logs de urna já estão no portal de resultados (pleito 3221). Esta é a primeira leitura, com a amostra mais informativa possível sem o BU: **as mesmas 1.725 urnas selecionadas no 1º turno**, agora com o log do 2º turno, o que permite comparar urna a urna.

## Amostra (`00_amostra.csv`)
Grupos do 1º turno, com os mesmos nomes: A_calibrado (27), B_manual_tardia (25), C_controle_municipio (156), D_controle_nacional (150), E_NE_suspeitas_horario_normal (993), F_NE_controle_horario_normal (300) e I_bom_lugar_maranhaozinho (74: todas as seções dos dois municípios). Logs obtidos: **1.725 de 1.725** (379.059 habilitações); 58 só foram publicados entre 22h18 e 23h36. Modelo de urna igual ao do 1º turno em 1.720. Sem BU não há validação de comparecimento; os campos `bu_*` estão vazios e serão preenchidos por `logs_brasil.py anexar_bu` quando o CSV sair.

## Resumo executivo
1. **Habilitação manual no fim da sessão: de novo, não existe.** Em todos os grupos a fração das manuais na última hora é menor que a fração dos votos (suspeitas E: 4,4% contra 5,2%; controles F: 4,7% contra 5,4%; Bom Lugar: 4,0% contra 4,4%). Pelo limiar dos controles (razão > 3,3 com ≥ 5 manuais na última hora): 1 urna em 993 suspeitas e 1 em 300 controles.
2. **Votos após o horário previsto: praticamente zero.** 58 votos em 200.932 nas suspeitas (0,03%) e 27 em 70.972 nos controles; no 1º turno, nas mesmas urnas, foram 1.460 e 748. Todas as urnas encerraram em mediana 1,0 a 1,4 min após o horário local (no 1º turno: 3 a 126 min conforme o grupo).
3. **O voto do 2º turno dura 10 a 12 s** (habilitação → computado), contra 54 a 64 s no 1º turno; o intervalo entre votos caiu de 103–130 s para 71–87 s. Isso é a cédula de um cargo. As predições P1 (encerramento tardio cai), L1 (duração cai) e L4 (sem manuais no fim) registradas em `docs/ESCOPO_2T.md` se confirmam na amostra.
4. **A taxa de habilitação manual é propriedade da urna e do eleitorado.** Correlação urna a urna entre turnos: 0,80 a 0,83 nos grupos C, D, E e F. Controles: 6,2% → 6,3% e 6,5% → 6,7%. Suspeitas do NE: 15,5% → 13,4% (regressão à média esperada, pois foram selecionadas pelo extremo do 1º turno). O grupo B (leitor degradado em UE2013) caiu de 72% para 40%, corr 0,28: a falha do leitor foi do dia.
5. **Bom Lugar e Maranhãozinho: a anomalia do 1º turno não se repetiu.** No 1º turno, 24 das 76 urnas tinham eleitores manuais votando em menos de 0,8 do tempo dos biométricos; no 2º turno, 2 de 58. Por local de votação: 1120 0,59 → 0,92; 1104 0,59 → 0,82; 1198 0,59 → 1,64; 1171 0,60 → 1,10; Maranhãozinho 1104 0,59 → 1,00. Nos dois municípios o voto manual dura 12 s e o biométrico 11 s. A urna de Maranhãozinho z101 s138, a mais sugestiva do 1º turno (18 manuais nos últimos 90 min, em sequências, votando em 36 s contra 68 s), teve no 2º turno 2 manuais nos últimos 90 min, sem sequências, 13 s contra 12 s. **Ressalva:** com cédula de um cargo todo voto é rápido e a razão perde poder de discriminar (mediana da amostra 1,24 → 1,18; p5 0,92 → 0,89; correlação urna a urna da razão entre turnos só 0,27). O 2º turno descarta uma prática local que apareceria em qualquer cédula; não resolve o que aconteceu no 1º turno, que continua dependendo do caderno de votação.

## Mesmas urnas, 1º × 2º turno (`10_comparacao_1t_2t_por_grupo.csv`)

| grupo | n | manual 1t → 2t | razão manual/votos última hora (mediana) | voto (s) | encerramento (min após horário) | votos após o horário | razão duração manual/bio | corr manual |
|---|---|---|---|---|---|---|---|---|
| A_calibrado | 27 | 17,6% → 13,1% | 1,13 → 0,65 | 60 → 11 | 6,3 → 1,3 | 541 → 1 | 1,18 → 1,07 | 0,68 |
| B_manual_tardia | 25 | 72,1% → 39,8% | 1,03 → 0,82 | 54 → 12 | 125,7 → 1,4 | 1.550 → 0 | 1,03 → 1,00 | 0,28 |
| C_controle_municipio | 156 | 6,8% → 7,1% | 0,76 → 0,68 | 56 → 11 | 6,9 → 1,0 | 1.739 → 11 | 1,24 → 1,22 | 0,80 |
| D_controle_nacional | 150 | 6,2% → 6,3% | 0,44 → 0,00 | 55 → 10 | 3,7 → 1,0 | 942 → 11 | 1,28 → 1,18 | 0,83 |
| E_NE_suspeitas | 993 | 15,5% → 13,4% | 0,79 → 0,67 | 64 → 11 | 3,3 → 1,3 | 1.460 → 58 | 1,25 → 1,18 | 0,82 |
| F_NE_controle | 300 | 6,5% → 6,7% | 0,71 → 0,00 | 58 → 10 | 5,1 → 1,1 | 748 → 27 | 1,29 → 1,20 | 0,83 |
| I_bom_lugar_maranhaozinho | 74 | 9,2% → 7,8% | 1,19 → 0,00 | 64 → 11 | 5,6 → 1,0 | 340 → 1 | 0,97 → 1,09 | 0,53 |

Medianas de 0,00 na razão da última hora refletem urnas sem nenhuma manual na última hora (com 10 a 20 manuais por urna e 5% dos votos na última hora, isso é o esperado).

## Anomalias pelos limiares dos controles (`07_limites_anomalias.csv`, `08_secoes_com_anomalia.csv`)

| anomalia (limiar) | A (27) | B (25) | C (156) | D (150) | E (993) | F (300) | I (74) |
|---|---|---|---|---|---|---|---|
| manuais no fim (razão > 3,3, ≥ 5 manuais) | 0 | 0 | 0 | 0 | 1 | 1 | 0 |
| sequência de manuais > 3 | 2 | 18 | 3 | 1 | 98 | 7 | 7 |
| > 5 manuais em 15 min | 6 | 20 | 4 | 3 | 108 | 10 | 3 |
| votos rápidos na última hora (intervalo < 72 s) | 0 | 0 | 12 | 4 | 32 | 11 | 1 |
| votos após o horário > 10% | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Sequências e rajadas acompanham a taxa manual (grupos E e B), como no 1º turno, e não o horário. Votos rápidos no fim: 3,2% das suspeitas contra 3,7% dos controles do NE.

## Bom Lugar e Maranhãozinho (`11_*_locais_1t_2t.csv`, `13_*_urnas_1t_2t.csv`)
Urnas com razão < 0,8 (≥ 10 manuais e ≥ 10 biométricos): 1º turno 24 de 76; 2º turno 2 de 58. As duas são do local 1104 de Bom Lugar: s121 (0,59 → 0,50: 25 manuais votando em 5 s, biométricos em 10 s) e s312 (0,60 → 0,73). A terceira urna do local, s41, foi de 0,57 para 1,09. Esse local é o único em que algo do 1º turno sobrevive, em uma urna. Na amostra inteira, 40 das 1.531 urnas elegíveis ficam abaixo de 0,8 no 2º turno (28 no 1º), espalhadas por grupos e UFs: ao nível de urna, com votos de 10 s, a razão é quase ruído.

## Anomalia ≠ fraude
| Achado | Explicação inocente | O que descarta |
|---|---|---|
| Bom Lugar não repete | o padrão do 1º turno (manuais 2× mais rápidos) dependia de uma cédula longa; com um cargo, ninguém tem vantagem por "saber o voto" | nada a descartar no 2º turno; o 1º turno continua pedindo o caderno de votação |
| s121 do local 1104: manuais em 5 s | eleitor que digita 2 números e confirma; 5 s é o mínimo físico | caderno de votação dessa seção |
| 2 urnas com manuais no fim (1 suspeita, 1 controle) | 5 a 7 manuais em poucas dezenas de votos | mesma taxa nos controles |

## Conclusão
No 2º turno, nas mesmas 1.725 urnas que foram o cenário mais favorável à hipótese no 1º turno, não há habilitação manual concentrada no fim, não há votos após o horário, e todas as urnas fecham no horário porque o voto dura 11 s. A taxa manual se repete urna a urna, o que confirma que é leitor e eleitorado. O achado de Bom Lugar não se repete, com a ressalva de que a cédula curta tira poder do teste. Próximos passos: anexar o BU quando sair, e a varredura nacional em andamento (`out/2t/logs_brasil/progresso.log`).

## Arquivos (`out/2t/logs_rep/`)
Gerados por `logs_urna.py selecionar_repeticao | baixar | parsear | analisar --out out/2t/logs_rep` (com `TURNO=2`) e `comparar_amostra_2t.py`: `00_amostra.csv`, `01_eleitores.csv` (379 mil habilitações, não versionado), `02_secoes_metricas.csv`, `03_resumo_grupos.csv`, `04_perfil_horario.png`, `05_scatter_ultima_hora.png`, `06_timelines_flagradas.png`, `07_limites_anomalias.csv`, `08_secoes_com_anomalia.csv`, `10_comparacao_1t_2t_por_grupo.csv`, `11_bom_lugar_maranhaozinho_locais_1t_2t.csv`, `12_distribuicoes_1t_2t.csv`, `12_urnas_razao_dur_lt08_2t.csv`, `12_urnas_manual_fim_2t.csv`, `13_bom_lugar_maranhaozinho_urnas_1t_2t.csv`.
