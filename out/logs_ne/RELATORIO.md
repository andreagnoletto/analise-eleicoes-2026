# Logs de urna — Nordeste, 1.000 urnas suspeitas com fechamento no horário normal

Pergunta: se um mesário "vota por ausentes" no fim da sessão, a urna fecha na hora (sem fila) e as habilitações manuais se concentram no fim. Esta amostra isola exatamente esse cenário.

## Amostra (`00_amostra.csv`)
Universo: 88.630 urnas do NE apuradas, com ≥ 100 aptos, em municípios com ≥ 8 seções, encerradas até 30 min após as 17h.
- **E_NE_suspeitas_horario_normal (1.000)**: maiores z da taxa manual dentro do município, com comparecimento acima da média do município. z_manual de 2,3 a 14,2; taxa manual mediana 14,3%. BA 235, CE 192, MA 168, PE 119, PI 77, PB 72, RN 59, SE 46, AL 32.
- **F_NE_controle_horario_normal (300)**: aleatórias do mesmo universo, fora das suspeitas. Taxa manual mediana 5,7%.

1.300 logs baixados (0 erros), 270.356 habilitações. Comparecimento bate com o BU em 1.300/1.300; manuais batem em 1.272/1.300 e as 28 restantes diferem em 1 (habilitação manual sem voto concluído). Modelos: UE2020 443 / UE2022 405 / UE2015 108 / UE2013 44 nas suspeitas; proporções semelhantes nos controles.

## Resumo executivo
1. **Não há concentração de habilitações manuais no fim da sessão.** Suspeitas: 7,2% das manuais na última hora contra 8,6% dos votos; controles: 7,6% contra 9,4%. Mediana por urna da razão manual/votos na última hora: 0,79 (suspeitas) e 0,71 (controles); p95: 2,1 contra 2,6. As suspeitas são, se algo, *menos* concentradas no fim que os controles (`04_perfil_horario.png`, `05_scatter_ultima_hora.png`).
2. Pelo limite dos controles (razão > 2,6 com ≥ 5 manuais na última hora): **3 urnas em 1.000** suspeitas e 1 em 300 controles, mesma taxa (0,3%). Das 3, duas são leitor biométrico que degradou às 15h (todos os eleitores seguintes põem o dedo, falham 4 vezes, votam em ~67 s com intervalos de 140 a 270 s) e uma tem 5 manuais em 13 votos na última hora.
3. Votos após as 17h: nenhum por construção (urnas fecharam no horário). O último voto ocorre em mediana 7,7 min antes do encerramento nas suspeitas e 6,1 nos controles. Intervalo entre votos na última hora: 131 s contra 109 s; votos rápidos no fim (intervalo mediano < 81 s): 1,6% das suspeitas contra 4,0% dos controles.
4. A taxa manual alta das suspeitas é espalhada pelo dia inteiro e sobe com a idade do modelo (UE2013 31%, UE2015 21%, UE2020/2022 15%). Sequências e rajadas de manuais (158 e 104 urnas) são consequência direta da taxa alta, não de concentração horária.
5. **Um achado novo, de outra natureza:** nas três urnas do local de votação 1104 de **Bom Lugar/MA (zona 66, seções 41, 121 e 312)** os eleitores habilitados manualmente votam em ~32 s (mediana) contra ~54 s dos biométricos da mesma urna, e 40% deles votam em menos de 30 s (biométricos: 1 a 4%). Em 1.508 urnas com ≥ 10 manuais e ≥ 10 biométricos, essas são as únicas com razão abaixo de 0,8 (0,59 / 0,60 / 0,57); a mediana nacional é 1,25 (eleitor manual normalmente demora *mais*). O padrão vale o dia todo, em três urnas de modelos diferentes (UE2020 e UE2022), e o local tem 21 a 24% de manual (município 11%) e 92 a 95% de comparecimento (município 81%). O voto em presidente dessas seções (60% e 71% Lula) não desvia do município (69%). Não dá para dizer pelo log quem votou; é o único ponto deste estudo que recomendo conferir em caderno de votação (assinaturas dos habilitados manualmente) e, se possível, nas digitais coletadas (`wsqman.jez`).

## Números por grupo (`03_resumo_grupos.csv`)

| Métrica (mediana por urna, salvo indicação) | Suspeitas (1.000) | Controles (300) |
|---|---|---|
| votos (soma) | 200.224 | 70.043 |
| habilitações manuais (soma) | 31.020 | 4.552 |
| fração dos votos na última hora | 8,4% | 9,3% |
| fração das manuais na última hora | 6,7% | 6,7% |
| razão manual/votos na última hora | 0,79 | 0,71 |
| idem, agregado ponderado | 0,84 | 0,81 |
| encerramento (min após 17h) | 3,3 | 5,1 |
| último voto antes do encerramento (min) | 7,7 | 6,1 |
| duração do voto (s) | 64 | 58 |
| duração do voto manual (s) | 79 | 76 |
| intervalo entre votos, dia (s) | 126 | 111 |
| intervalo entre votos, última hora (s) | 131 | 109 |
| tentativas de digital antes do manual | 4,0 | 4,0 |

## Anomalias (limites nos controles, `07_limites_anomalias.csv`; lista em `08_secoes_com_anomalia.csv`)

| Anomalia | Suspeitas | Controles |
|---|---|---|
| manuais concentradas no fim (razão > 2,6, ≥ 5 manuais) | 3 (0,3%) | 1 (0,3%) |
| sequência de manuais > 3 | 158 | 3 |
| > 4 manuais em 15 min | 104 | 0 |
| votos rápidos na última hora | 16 (1,6%) | 12 (4,0%) |
| > 10% dos votos após as 17h | 0 | 0 |
| manuais muito mais rápidos que biométricos no fim (razão < 0,82, `09_duracao_manual_vs_bio.csv`) | 10 (duas de Bom Lugar; as outras 8 entre 0,67 e 0,80, dentro do que se vê em controles ao longo do dia) | 1 |

As 3 urnas "manual no fim": São Luís z10 s282 (UE2013; leitor degradado a partir das 15h: 42 manuais em 46 eleitores, 175 capturas de digital sem reconhecimento, votos de 67 s, intervalos de 140 a 270 s); Bom Lugar z66 s121 (ver item 5); Vicência/PE z109 s51 (5 manuais em 13 votos na última hora, biometria funcionando, votos de 61 s).

"Dado digitado não confere" (mesário digita dado pessoal errado na habilitação manual): 2,6 por 100 manuais nas suspeitas, 2,5 nos controles.

## Anomalia ≠ fraude
| Achado | Explicação inocente | O que descarta |
|---|---|---|
| 1.000 urnas com manual alto e comparecimento alto fechando no horário | eleitorado com biometria ruim (idade, trabalho rural) e modelos antigos; manuais espalhadas pelo dia como nos controles | nada restou a explicar no eixo temporal |
| leitor degradando às 15h (São Luís s282) | sensor sujo/aquecido; eleitores reais põem o dedo e falham | foto do eleitor é exibida ao mesário em cada habilitação; conferir caderno |
| Bom Lugar local 1104: manuais votam 2× mais rápido | eleitores com "cola" e digital gasta chegando em grupo; ou operação diferente do mesário | caderno de votação e `wsqman.jez`; não resolvível pelo log |

## Conclusão
No cenário mais favorável à hipótese (NE, urna fechada na hora, manual e comparecimento altos), as 1.000 urnas mais suspeitas do BU não mostram habilitação manual concentrada no fim da sessão nem votos após o horário. A hipótese original não se sustenta. O estudo deixa um único caso para verificação humana, Bom Lugar/MA local 1104, por um critério diferente (velocidade do voto dos habilitados manualmente), que não é prova de nada sem o caderno de votação.

## Arquivos (`out/logs_ne/`)
`00_amostra.csv`, `01_eleitores.csv`, `02_secoes_metricas.csv`, `03_resumo_grupos.csv`, `04_perfil_horario.png`, `05_scatter_ultima_hora.png`, `06_timelines_flagradas.png` (40 urnas com manuais mais concentradas no fim), `07_limites_anomalias.csv`, `08_secoes_com_anomalia.csv`, `09_duracao_manual_vs_bio.csv`, `10_razao_duracao_todas_amostras.csv`. Bom Lugar: `out/logs_bomlugar/`.
