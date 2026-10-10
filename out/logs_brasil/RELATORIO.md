# Logs de urna — varredura nacional (509.155 urnas, 1º turno 2026)

Fonte: portal de resultados do TSE, uma requisição `aux.json` + um `log.jez` por seção. Script `logs_brasil.py` (32 conexões, retomável), 15,5 h de execução, `.jez` brutos em `data/logs/raw/` (~51 GB), métricas por urna e 1 linha por habilitação em `data/logs_parquet/` (Parquet). Análise em `analise_logs_brasil.py`.

Cobertura: 509.207 urnas apuradas no BU; 509.155 processadas. Faltam 52: 28 no exterior (ZZ) e 2 em MG sem arquivo de log no portal (as mesmas sem hora de encerramento no BU) e 22 no RS que falharam por conexão e foram recuperadas depois (incluídas). ZZ (sem biometria, só presidente) entra apenas na validação.

**Validação contra o BU:** comparecimento do log = `QT_COMPARECIMENTO` em 509.129 de 509.155 urnas (99,995%); habilitações manuais = `QT_ELEI_BIOM_SEM_HABILITACAO` em 98,1% e a ±1 em 99,9% (a diferença de 1 é um eleitor habilitado manualmente que não concluiu o voto).

## Resumo executivo

1. **Habilitação manual concentrada no fim da sessão: não existe como fenômeno.** Em 497.895 urnas, a razão entre a fração das manuais na última hora e a fração dos votos na última hora tem mediana 1,6 (entre urnas com ≥ 5 manuais na última hora), p99 de 4,6, e as 10 urnas acima do p99,9 (0,002%) têm 5 a 9 manuais cada, espalhadas por 9 UFs, sem cluster. Votos rápidos no fim (intervalo mediano < 69 s) também ficam no nível de ruído e sem concentração regional.
2. **Eleitor habilitado manualmente demora mais para votar em 95% das urnas** (razão duração manual/biométrico: mediana 1,26; p5 0,98; p0,1 0,80), em todas as regiões, com a mesma distribuição (`07_hist_razao_duracao.png`).
3. **O critério de Bom Lugar aponta para Bom Lugar.** Agregando por local de votação (68.018 locais com ≥ 30 manuais e ≥ 30 biométricos), 67 ficam abaixo do p0,1 (razão < 0,91). Agregando por município (5.520 com ≥ 100 manuais), **Bom Lugar/MA é o município mais anômalo do país** (razão 0,785; o segundo é Maranhãozinho/MA com 0,967; o p0,1 nacional é 1,026). Em Bom Lugar, 17 das 39 urnas elegíveis foram flagradas (esperado por acaso: 0,04), 6 dos 14 locais, e 16% dos eleitores manuais votam em menos de 30 s contra 0,5% dos biométricos. Em Maranhãozinho, 7 de 25 urnas (esperado 0,03), 3 de 6 locais. O terceiro, Coroatá/MA, tem 3 de 137 (22× o esperado); do quarto em diante (Palmas, Nova Iguaçu, Salvador…) está em 1 a 8× o esperado, compatível com acaso em municípios grandes.
4. Maranhãozinho tem ainda a urna z101 s138 com o padrão mais sugestivo da varredura: UE2020 com leitor funcionando (biométricos intercalados votando em 68 s), e duas sequências de 6 e 8 eleitores manuais consecutivos entre 15h18 e 16h39, cada um com 4 tentativas de digital e votando em 23 a 47 s. 9 das 10 últimas habilitações são manuais.
5. **Subprodutos:** taxa de falha do leitor por modelo: UE2013 11,2%, UE2015 9,7%, UE2020 e UE2022 6,1% (1,1% das UE2013 têm ≥ 50% de manual). Tempo mediano por voto por UF: MA e PI 63 s, PA 62 s, BA 60 s, contra SP e RS 52 s, SC 51 s, DF 50 s. Essa diferença de 15 a 25% no tempo por eleitor, com seções maiores, explica o encerramento tardio no NE e N sem nenhum voto a mais.

## Validação (`01_validacao_uf.csv`)
Comparecimento bate em todas as UFs com ≤ 4 exceções por UF (SP 4, RJ 3, MG 2, PR 2, BA/ES/RN/PA 1), todas urnas de contingência com log incompleto. Modelo identificado em 100%.

## Por modelo (`02_modelo_nacional.csv`, `02_modelo_uf.csv`, `07_manual_por_modelo_uf.png`)

| Modelo | urnas | taxa manual média | urnas com ≥ 50% manual | voto (s) | encerramento (min após 17h, média) |
|---|---|---|---|---|---|
| UE2013 | 10.893 | 11,2% | 1,09% | 57,8 | 22,7 |
| UE2015 | 87.780 | 9,7% | 0,02% | 59,5 | 21,7 |
| UE2020 | 200.451 | 6,1% | 0,00% | 55,6 | 15,0 |
| UE2022 | 198.749 | 6,1% | 0,00% | 55,4 | 14,9 |

O efeito do modelo é o mesmo em todas as UFs: onde há UE2013/UE2015, a taxa manual sobe 3 a 6 pontos.

## Tempo por voto e encerramento (`03_tempo_voto_uf.csv`, `07_tempo_voto_uf.png`)
Voto mediano (habilitação → computado): MA 63 s, PI 63, PA 62, AC 61, BA 60, TO 59, AL 59, AM 59, CE 58 … RJ 54, PR 53, RS 52, SP 51,5, SC 51, DF 50. Intervalo entre votos: 117 s no MA contra 94 s em SC. Com 250 a 275 eleitores por urna, a diferença acumulada é de 1 a 1,5 h de votação por dia, que é exatamente o atraso observado no encerramento (BA mediana +18 min, AL +31, PE +30 contra Sul +1 a +2).

## Quantis nacionais e flags (`04_quantis_nacionais.csv`, `05_*.csv`)

| Métrica | n | p0,1 | p1 | p50 | p99 | p99,9 |
|---|---|---|---|---|---|---|
| razão duração manual/biométrico (≥ 10 e ≥ 10) | 399.038 | 0,80 | 0,90 | 1,26 | 2,07 | 2,55 |
| razão manual/votos na última hora (≥ 5 manuais) | 9.851 | 0,50 | 0,68 | 1,59 | 4,57 | 6,86 |
| intervalo mediano entre votos na última hora (s) | 439.796 | 69 | 75 | 106 | 272 | 351 |
| salto da taxa manual 8–11h → 14–17h | 496.256 | −0,24 | −0,16 | −0,02 | 0,10 | 0,18 |

Flags a 0,1% nacional, por região (N / NE / CO / SE / S): manuais rápidos 54 / 185 / 19 / 105 / 26; manuais no fim 2 / 4 / 1 / 2 / 1; votos rápidos no fim 20 / 160 / 12 / 121 / 98; leitor degrada à tarde 55 / 91 / 40 / 227 / 84. Proporcionais ao número de urnas, exceto "manuais rápidos" no NE (185 em 140 mil, 1,3‰), puxado por MA (69) e BA (66).

## Por local e município (`06_locais_flagrados_manual_rapido.csv`, `06_municipios_razao_duracao.csv`)

| Município | urnas | manuais | razão duração | manuais < 30 s | biométricos < 30 s | locais flagrados | urnas flagradas / esperado |
|---|---|---|---|---|---|---|---|
| Bom Lugar/MA | 45 | 1.060 | **0,785** | 16,0% | 0,5% | 6 de 14 | 17 / 0,04 |
| Maranhãozinho/MA | 31 | 466 | **0,967** | 4,9% | 0,4% | 3 de 6 | 7 / 0,03 |
| Santa Rosa do Purus/AC | 16 | 118 | 0,973 | 0% | 0,1% | 0 | 0 |
| Guaribas/PI | 17 | 326 | 1,000 | 0% | 0,2% | 0 | 0 |
| Coroatá/MA | 160 | — | — | — | — | 2 | 3 / 0,14 |
| mediana nacional (5.520 municípios) | | | 1,311 | | | | |

Bom Lugar, locais: 1120 (0,59), 1104 (0,59), 1198 (0,59), 1171 (0,60), 1015 (0,72), 1210 (0,78); os outros 8 locais do município estão entre 0,93 e 1,16, isto é, normais. Maranhãozinho: 1104 (0,59), 1058 (0,84), 1120 (0,89); os outros 3 normais. No BU, Bom Lugar tem comparecimento 81% e manual 11,4% (município); Maranhãozinho 80% e 7,1%. Voto em presidente: 68,9% e 70,3% Lula, na faixa do interior do MA.

## Anomalia ≠ fraude
| Achado | Explicação inocente | O que descarta |
|---|---|---|
| Bom Lugar e Maranhãozinho: eleitores manuais votam 2× mais rápido, em vários locais | eleitores com digital gasta chegam em grupo com cola; ou mesários "ajudam" a digitar, o que já é irregular mas não é voto por ausente | caderno de votação (assinaturas dos habilitados manualmente), `wsqman.jez` (digitais coletadas), depoimento dos mesários; comparar com 2022 nos mesmos locais |
| Maranhãozinho z101 s138: sequências de manuais no fim, rápidos, com leitor funcionando | grupo de eleitores rurais chegando junto no fim da tarde | idem; esta urna é a prioridade |
| 10 urnas com manuais no fim no país | acaso (0,002%) e grupos de eleitores | nenhuma repete em outro critério |
| NE e N fecham tarde | 15 a 25% mais tempo por voto, seções maiores | medido no log; não resta nada a explicar |

## Conclusão
A varredura de todas as urnas confirma, agora sem amostragem, que não existe habilitação manual concentrada no fim da sessão nem em escala nacional nem regional, e que o encerramento tardio do NE e N é tempo de votação por eleitor. O critério que surgiu em Bom Lugar, quando aplicado ao país inteiro, devolve Bom Lugar como o município mais anômalo do Brasil e Maranhãozinho como o segundo, ambos com múltiplos locais de votação e muito acima do acaso, e nada comparável em outra parte. Isso é um achado localizado, de dois municípios pequenos do Maranhão (19,6 mil eleitores somados), que só o caderno de votação pode esclarecer.

## Arquivos (`out/logs_brasil/`)
`01_validacao_uf.csv`, `02_modelo_nacional.csv`, `02_modelo_uf.csv`, `03_tempo_voto_uf.csv`, `04_quantis_nacionais.csv`, `05_urnas_flagradas.csv`, `05_flags_por_regiao.csv`, `05_flags_por_uf.csv`, `06_locais_flagrados_manual_rapido.csv`, `06_locais_razao_duracao.parquet` (68.018 locais), `06_municipios_razao_duracao.csv` (5.520 municípios), `07_hist_razao_duracao.png`, `07_manual_por_modelo_uf.png`, `07_tempo_voto_uf.png`, `secoes_logs_brasil.parquet` (497.895 urnas × 48 métricas), `progresso.log`.
