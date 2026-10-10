# Logs de urna (log.jez) — distribuição temporal das habilitações manuais e dos votos

Fonte: `https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/<uf>/<mun>/<zona>/<seção>/` (aux.json → hash → `o03220...-log.jez`). O `log.jez` é um ZIP com `logd.dat` (Latin-1, campos separados por TAB); em urna de contingência traz também um `.jez` aninhado com o log da urna original, que foi concatenado. 358 logs baixados, 0 erros, 89.886 habilitações parseadas. Brutos em `data/logs/raw/`, texto em `data/logs/txt/`.

Validação contra o BU: comparecimento bate em **358/358** seções; habilitações manuais batem em 348/358, e nas 10 restantes o log tem exatamente 1 manual a mais (eleitor habilitado que não concluiu o voto; o BU não o conta).

## Amostra (`00_amostra.csv`)

| Grupo | n | Como foi escolhido |
|---|---|---|
| A_calibrado | 27 | todas as flagradas pelo critério calibrado da análise nacional |
| B_manual_tardia | 25 | maiores z_manual do critério "manual alto e encerramento > 60 min" |
| C_controle_municipio | 156 | 3 seções aleatórias não flagradas do mesmo município de cada flagrada (aptos ≥ 100) |
| D_controle_nacional | 150 | 30 seções aleatórias por região (N, NE, CO, SE, S), aptos ≥ 100 |

Mensagens usadas: `Tipo de habilitação do eleitor [biométrica]`; `Solicitação de dado pessoal do eleitor para habilitação manual` (após 4 tentativas de digital; exige a digital do mesário); `Ano de nascimento digitado...` (eleitor sem biometria cadastrada, não entra em `QT_ELEI_BIOM_SEM_HABILITACAO`); `Eleitor foi habilitado`; `O voto do eleitor foi computado`; `Operador selecionou: Encerrar votação`; `Identificação do Modelo de Urna`.

## Resumo executivo

1. **A habilitação manual não se concentra no fim da sessão em nenhum grupo.** A fração das habilitações manuais na última hora antes do encerramento é igual ou menor que a fração de todos os votos na última hora: A 6,8% vs 7,9%; B 9,5% vs 10,8%; controles do município 7,4% vs 9,0%; controle nacional 5,6% vs 8,4% (agregados ponderados). O perfil horário das manuais acompanha o dos votos ao longo de todo o dia (`04_perfil_horario.png`).
2. Pelo critério "manual concentrado no fim" (razão manual/votos na última hora acima do p95 dos controles, 2,5, com ≥ 5 manuais), **zero** seções dos grupos A e B são anômalas.
3. **Votos após o horário** são continuação de fila: no grupo B o último voto ocorre em mediana 0,7 min antes do encerramento e a parcela de manuais após as 17h (21,8%) é igual à parcela de votos após as 17h (22,7%). O intervalo entre votos na última hora não encurta (B 118 s; controles 106–113 s), o que descarta sequências rápidas de "votos por ausentes".
4. **O grupo B é o modelo UE2013.** 21 das 25 urnas são UE2013; nessa amostra o UE2013 tem taxa manual média de 44% e em 46% das urnas UE2013 metade ou mais dos eleitores foi habilitada manualmente (UE2015 9,8%, UE2020 6,9%, UE2022 6,6%). O leitor biométrico do UE2013 falha em massa, cada habilitação manual leva ~70 s em vez de ~55 s, e a urna fecha tarde. Isso ocorre em SP, MG, RJ, ES, MT, GO, DF, RS, PR tanto quanto na BA, CE e PE.
5. Das 27 do grupo A, 2 são leitores inoperantes (UE2013, 86 manuais em ~100 votos, desde as 8h) e as outras 25 têm manuais espalhadas pelo dia, em linha com os controles (`06_grupoA_timelines.png`). Nenhuma mostra pico de manuais no fim, rajada de manuais ou votos rápidos no fim.

## Números por grupo (`03_resumo_grupos.csv`)

| Métrica (mediana por seção, salvo indicação) | A | B | C ctrl mun. | D ctrl nac. |
|---|---|---|---|---|
| votos (soma) | 5.831 | 6.823 | 39.908 | 37.283 |
| habilitações manuais (soma) | 1.025 | 4.922 | 2.726 | 2.294 |
| fração dos votos na última hora | 6,9% | 10,0% | 9,4% | 8,3% |
| fração das manuais na última hora | 5,7% | 9,7% | 6,7% | 4,0% |
| razão manual/votos na última hora | 1,13 | 1,03 | 0,76 | 0,44 |
| idem, agregado ponderado | 0,86 | 0,88 | 0,82 | 0,67 |
| fração de votos após 17h local (ponderado) | 9,3% | 22,7% | 4,4% | 2,5% |
| fração de manuais após 17h local (ponderado) | 5,3% | 21,8% | 2,9% | 1,1% |
| encerramento (min após 17h local) | 6 | 126 | 7 | 4 |
| último voto antes do encerramento (min) | 2,4 | 0,7 | 3,8 | 5,9 |
| duração do voto (habilitação → computado, s) | 60 | 54 | 56 | 55 |
| duração do voto manual (s) | 69 | 55 | 69 | 71 |
| intervalo entre votos, dia todo (s) | 124 | 130 | 103 | 103 |
| intervalo entre votos, última hora (s) | 155 | 118 | 106 | 113 |
| maior sequência de manuais consecutivos (máx.) | 34 | 201 | 4 | 5 |
| máx. de manuais em 15 min | 6 | 11 | 5 | 5 |
| tentativas de digital antes do manual | 4,0 | 4,0 | 4,0 | 4,0 |

## Critérios de anomalia (limites tirados dos controles, `07_limites_anomalias.csv`) e contagem (`08_secoes_com_anomalia.csv`)

| Anomalia | Limite | A (27) | B (25) | C (156) | D (150) |
|---|---|---|---|---|---|
| manuais concentradas no fim (razão > 2,5 e ≥ 5 manuais na última hora) | p95 ctrl | **0** | **0** | 0 | 0 |
| sequência de manuais consecutivos > 3 | p95 ctrl | 6 | 25 | 7 | 2 |
| > 4 manuais em 15 min | p95 ctrl | 3 | 24 | 2 | 3 |
| votos rápidos na última hora (intervalo mediano < 81 s, ≥ 10 votos) | p5 ctrl | 1 | 1 | 11 | 5 |
| > 10% dos votos após as 17h locais | fixo | 8 | 25 | 27 | 11 |

Leitura: as sequências e rajadas de manuais do grupo B (e das 2 urnas UE2013 do grupo A) são leitor inoperante: todos os eleitores passam a manual, em ordem, o dia inteiro, cada um após 4 tentativas de digital e com a digital do mesário. Votos após as 17h aparecem em 27 controles do mesmo município, isto é, são fila local. O critério "votos rápidos no fim" acusa 5–7% dos controles por construção e 1 em A e 1 em B.

## Anomalia ≠ fraude: o que cada achado significa

| Achado | Explicação inocente | Situação após o log |
|---|---|---|
| 27 seções com manual e comparecimento altos no BU | seções pequenas ou atípicas; leitor inoperante | manuais distribuídas pelo dia como nos controles; 2 leitores inoperantes confirmados. Nada restou para explicar. |
| 459 seções "manual × tardia" no BU | leitor biométrico do UE2013 falha em massa, votação lenta, fila | confirmado nas 25 testadas: 21 UE2013, manuais o dia inteiro, último voto a 0,7 min do encerramento |
| NE/N fecham mais tarde | votação mais lenta por eleitor | intervalo entre votos nos controles do NE é semelhante ao resto (103 s); o atraso vem do volume na fila, não de votos extras |

## O que o log não cobre
Quem votou (o log não identifica o eleitor) e se os eleitores habilitados manualmente eram de fato as pessoas certas. Para isso só a conferência presencial de cadernos de votação ou a auditoria de `wsqman.jez` (digitais coletadas nas habilitações manuais) pelo TSE.

## Arquivos (`out/logs/`)
`00_amostra.csv`, `01_eleitores.csv` (89.886 linhas: seção, tipo de habilitação, tentativas, hora, duração, minutos antes do encerramento), `02_secoes_metricas.csv`, `03_resumo_grupos.csv`, `04_perfil_horario.png`, `05_scatter_ultima_hora.png`, `06_grupoA_timelines.png`, `07_limites_anomalias.csv`, `08_secoes_com_anomalia.csv`.
