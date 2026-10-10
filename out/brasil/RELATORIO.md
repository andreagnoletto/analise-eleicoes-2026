# Brasil inteiro — Boletins de Urna 1º turno 2026 (27 UFs + ZZ)

Dados: `bweb_1t_<UF>_051020261403.zip`, 28 arquivos, SHA-512 conferido em todos (0 falhas). 67,9 milhões de linhas, **509.207 urnas/BUs**. Votação em 04/10/2026. Unidade: 1 linha por urna (seções agregadas estão somadas na agregadora). Todas as urnas constam como `Apurada`. ZZ (exterior) tem `QT_ELEI_BIOM_SEM_HABILITACAO = 0` em todas as 1.309 urnas (sem biometria no exterior) e fica fora dos testes de habilitação manual.

Três critérios de "seção suspeita" rodaram lado a lado:
- **orig**: z_manual > 3 e z_comp > 2 no município, n_mun ≥ 8 (critério original do plano).
- **cal**: idem, mas z calculado em município × quartil nacional de aptos, e aptos ≥ 100 (calibrado no piloto).
- **tard**: z_manual > 3 no município **e** encerramento > 60 min após o horário local previsto, aptos ≥ 100 (pedido na Fase 2: "votos sem digital" × "após o horário").

## Resumo executivo

1. Consistência interna: zero erros nas 28 UFs (aptos = comparecimento + abstenções; manual ≤ comparecimento). Só 2 urnas em MG e 28 no ZZ não têm hora de encerramento.
2. A taxa de habilitação manual **não destaca o Nordeste**: PI (9,0%) lidera, mas RS (8,6%), MS (8,0%) e SC (7,8%) vêm logo atrás; por região, Sul 8,1% > NE 7,1% > CO 6,8% > SE 6,6% > N 5,5%. Controlando por tamanho da seção, série da urna e porte do município, NE fica em 6,8% e Sul em 7,9%.
3. Seções suspeitas: o critério original flagra 116 urnas e 96% delas estão no quartil de seções pequenas; o calibrado flagra **27 em 509 mil** (NE 12, SE 9, N 5, CO 1, S 0). NE tem 0,085‰ contra 0,044‰ no SE, mas são 12 contra 9 casos e os maiores valores por UF são AP, TO, SE e ES. Não há sinal regional.
4. O único padrão regional forte é o **encerramento tardio**: 36% das urnas do NE e 26% do N fecham > 30 min após o horário, contra 3% no Sul. Isso persiste controlando por tamanho, série e porte (NE 37% padronizado), portanto é vazão por eleitor, não composição. Mas os votos sem digital em urnas tardias são proporcionais ao comparecimento nessas urnas em todas as UFs (razão 1,0 a 1,6, e **menor** no NE que no Sul/SE), e, condicionado a fechar tarde, a chance de uma urna ser flagrada por manual alto é menor no NE (BA 12‰, PE 9‰) do que em ES (57‰), PR (35‰), SP (28‰).
5. **Veredito do teste de regionalidade (passo 13): a hipótese "fraude por habilitação manual no Nordeste" não se sustenta nos BUs.** NE não se destaca nos testes 3 e 4 após controles. As urnas que o critério "manual × tardia" seleciona são, na maioria, leitores biométricos inoperantes (taxa manual 80–98%) em capitais de todas as regiões (Belo Horizonte, Cuiabá, Rio, Brasília, Serra, Americana, Caruaru). O que falta para fechar a questão é o log das urnas listadas ao final.

## Teste 1 — consistência (`01_consistencia.csv`)
Zero em `soma_errada`, `comp_maior_aptos`, `manual_maior_comp`, `manual_negativo` e `nao_apurada` em todas as UFs. `sem_hora_enc`: MG 2, ZZ 28. `zero_abstencao` (100% de comparecimento): 15 urnas no país (PA 4, CE 4, BA 2, MG 2, SP 2, RR 1).

## Teste 2 e ranking por UF (`11_ranking_uf.csv`, `11a_ranking_manual.png`, `11_regioes.csv`, `11d_regioes.png`)

| Região | urnas | manual média | mediana | comparecimento | manual padronizado* |
|---|---|---|---|---|---|
| S | 72.015 | 8,05% | 7,17% | 79,6% | 7,90% |
| NE | 140.828 | 7,14% | 6,29% | 81,8% | 6,83% |
| CO | 38.048 | 6,77% | 6,05% | 78,3% | 7,03% |
| SE | 203.237 | 6,55% | 5,90% | 77,4% | 6,70% |
| N | 43.769 | 5,48% | 4,92% | 80,7% | 5,47% |
| Brasil | 507.898 | 6,84% | | | |

\*padronização direta por célula (quartil de aptos × série da urna < / ≥ 2,0M × porte do município), `13_regionalidade_padronizada.csv`.

Top 8 UFs por taxa manual: PI 9,0%, RS 8,6%, MS 8,0%, RN 8,0%, SC 7,8%, PR 7,7%, BA 7,5%, CE 7,2%. Menores: RR 3,9%, AP 4,5%, DF 4,9%, AC 5,1%. UFs do NE acima da média nacional (6,8%): PI, RN, BA, CE, PB; abaixo: SE, AL, PE, MA.

## Testes 3 e 4 — seções suspeitas (`03_secoes_suspeitas.csv`, `04_suspeitas_por_uf.csv`, `11b_ranking_suspeitas_*.png`, `secoes_flagradas_brasil.csv`)

| Região | orig (n) | orig ‰ | cal (n) | cal ‰ | cal ‰ padronizado | tard (n) | tard ‰ |
|---|---|---|---|---|---|---|---|
| N | 22 | 0,50 | 5 | 0,114 | 0,082 | 63 | 1,44 |
| NE | 51 | 0,36 | 12 | 0,085 | 0,101 | 283 | 2,01 |
| CO | 3 | 0,08 | 1 | 0,026 | 0,024 | 24 | 0,63 |
| SE | 28 | 0,14 | 9 | 0,044 | 0,049 | 75 | 0,37 |
| S | 12 | 0,17 | 0 | 0,000 | 0,000 | 14 | 0,19 |
| Brasil | 116 | 0,23 | 27 | 0,054 | | 459 | 0,90 |

- **orig**: 111 das 116 (96%) estão no quartil Q1 (20–281 aptos). Confirma o diagnóstico do piloto: o critério mede variância de seção pequena. Ranking por UF é liderado por AP (1,05‰, 2 urnas), MA (0,77‰), TO (0,68‰), PA (0,62‰).
- **cal**: 27 urnas no país. Por UF: AP 0,52‰ (1), TO 0,46‰ (2), SE 0,34‰ (2), ES 0,20‰ (2), PI 0,20‰ (2), MS, BA 0,14‰ (5), AM, PE, MA, PA, SP, MG, RJ; zero em 14 UFs. Em 18 das 27 o voto em Lula supera o do município (mediana +6 pp), mas o grupo inclui SP, MG, ES, MS, RJ com desvio para o outro lado. Dois casos são leitores inoperantes (São Paulo z420/s365 com 84% manual; Miguel Alves/PI 89%).
- **tard**: 459 urnas, BA 105, PE 57, CE 50, PA 49. Este critério herda a taxa de atraso da UF: no NE 25–50% das urnas fecham tarde, no Sul 1–3%. Normalizando pelas urnas tardias (`16b_flag_tard_condicional.csv`): ES 57‰, PR 35‰, SP 28‰, GO 27‰, DF 23‰, RS 22‰ … BA 12‰, AL 12‰, CE 12‰, PE 9‰, MA 6‰, RN 3‰. Dentro das urnas que fecham tarde, o NE tem **menos** urnas com manual anômalo que Sul e Sudeste. 67 das 578 urnas flagradas por algum critério têm taxa manual ≥ 50% (leitor inoperante, todas as regiões).

## Teste 5 — encerramento (`05_encerramento_por_uf.csv`, `11c_ranking_encerramento.png`, `16_*.csv`)

| UF (top) | % > 30 min | mediana (min) | UF (base) | % > 30 min | mediana |
|---|---|---|---|---|---|
| AL | 50,6 | 32 | RO | 1,1 | 3 |
| PE | 49,2 | 30 | SP | 1,9 | 3 |
| BA | 41,3 | 19 | RS | 2,2 | 1 |
| AM | 41,3 | 20 | PR | 3,1 | 2 |
| RN | 38,5 | 16 | RR | 4,1 | 3 |
| CE | 34,8 | 13 | SC | 4,5 | 1 |
| PA | 32,7 | 12 | MS | 5,2 | 3 |
| AP | 32,4 | 11 | DF | 6,1 | 6 |

Horário local respeitado (AC 15h; AM/MT/MS/RO/RR 16h). O atraso cresce com o tamanho da seção em todas as regiões, mas no NE e N o nível é 3 a 15 vezes maior que no resto **em cada célula** de tamanho × série × porte (`13_NE_vs_outros_por_celula.csv`, coluna `razao_tardia`). Não é composição: é tempo por eleitor. Explicação inocente mais plausível: votação mais lenta (eleitor leva mais tempo nos 5 cargos, mais eleitores com dificuldade, menos mesários por seção); para descartar, o log de urna dá a duração média de cada voto por seção.

Votos sem digital em urnas tardias (`16_manual_x_encerramento_uf.csv`): a parcela dos votos manuais da UF que ocorre em urnas que fecham > 60 min é quase igual à parcela do comparecimento nessas urnas (BA 32,0% vs 27,7%; AL 37,8% vs 36,7%; PE 33,8% vs 30,9%; MG 6,0% vs 5,0%; PR 1,5% vs 1,0%). A razão é 1,0–1,2 no NE e 1,3–1,6 no Sul/SE/CO. A taxa manual sobe com o atraso em todas as regiões (NE 7,3% → 9,0%; S 8,2% → 12,2%; CO 7,2% → 10,8%), compatível com "habilitação manual atrasa a fila", não com "fila tardia gera manual".

## Teste 6 — manual × voto (`06_correlacao_manual_voto.csv`, `15_correlacao_manual_voto_uf.csv`)
Correlação intra-município entre taxa manual e voto em Lula: máximo CE +0,15, RJ +0,13, PI +0,12, BA +0,09; negativa em RS (−0,07), SP (−0,08), MS (−0,10), SC. A correlação bruta é maior (AL +0,44, CE +0,33, PI +0,30, PE +0,28) e cai 60–85% dentro do município: é composição de eleitorado (municípios rurais/pobres têm mais falha biométrica e mais voto em Lula). Comparecimento alto correlaciona com Flávio Bolsonaro no CE (+0,26), PE (+0,35), AL (+0,40), oposto do que "votar por ausentes para Lula" produziria.

## Estratificações (passo 12, `12_estrat_*.csv`)
- **Tamanho** (quartis nacionais: Q1 20–281, Q2 281–327, Q3 327–362, Q4 362–930 aptos): taxa manual cai com o tamanho em todas as regiões (NE 8,1% → 6,0%; S 10,1% → 6,8%). Flags orig concentradas em Q1 em todas as regiões; flags cal distribuídas (Q1 13, Q2 5, Q3 5, Q4 4).
- **Tipo de urna** (`DS_TIPO_URNA`): só "Apurada". Não estratifica.
- **Série da urna** (proxy de modelo): séries 1,6M–1,8M têm taxa manual 10–13% em todas as regiões; séries ≥ 2,0M, 5–8%. Flags tard concentradas na série 1,6M (leitores mais antigos).
- **Porte do município**: taxa manual maior em municípios < 100 mil eleitores em todas as regiões (NE 7,7% vs capital 5,8%; S 9,2% vs 6,2%). Flags cal: NE capitais 4, >100k 3, <100k 5; SE 1/3/5.

## Teste de regionalidade (passo 13)
Com controle simultâneo por quartil de aptos, série da urna e porte do município (`13_regionalidade_padronizada.csv`, `13_NE_vs_outros_por_celula.csv`):
- taxa manual NE/outros por célula: entre 0,88 e 1,13 (mediana 0,96). Sem destaque.
- suspeitas cal: NE padronizado 0,10‰ vs SE 0,05‰, N 0,08‰; diferença de 12 contra 9 urnas, não significativa.
- encerramento tardio: NE 37% padronizado vs S 2,4%, razão por célula 1,5 a 16. **Destaque real, mas explicável por vazão** e sem reflexo em manual anômalo condicional.

Conclusão: se a hipótese fosse verdadeira, NE deveria se destacar nos testes 3 e 4 com controles. Não se destaca.

## Explicações alternativas e o que falta para descartá-las

| Achado | Explicação inocente mais plausível | O que descarta |
|---|---|---|
| 27 urnas cal com manual e comparecimento altos | seções pequenas/especiais com eleitorado atípico; 2 leitores inoperantes | nome do local de votação; log de urna (horário das habilitações manuais) |
| NE/N fecham tarde | votação mais lenta por eleitor, menos mesários | duração média do voto no log; eleitores por mesário |
| 67 urnas com manual ≥ 50% | leitor biométrico inoperante desde a abertura | log: habilitações manuais distribuídas o dia todo (inocente) ou só no fim (suspeito) |
| manual ↔ voto em Lula no NE | composição de eleitorado (idade, trabalho rural) | correlação intra-município já reduz; log por seção fecha |

## Seções para baixar o log de urna (.logjez)

**Prioridade A** — 27 urnas do critério calibrado (`secoes_flagradas_brasil.csv`, `flag_cal = True`): SP São Paulo 420/365; PI Miguel Alves 17/158; ES Fundão 14/179; PI Teresina 98/422; BA Eunápolis 203/316; SP Mairiporã 237/48; SE Aracaju 1/291; RJ Angra dos Reis 147/262; TO Porto Nacional 3/168; SE Itabaiana 9/250; BA Salvador 4/243 e 4/242; SP Vargem Grande do Sul 229/86; MS Chapadão do Sul 48/21; TO Peixe 20/103; AP Macapá 10/488; BA Juazeiro 47/312; PA Salinópolis 64/10; MG Teófilo Otoni 269/447; MA Mirador 72/87; PE Vitória de Santo Antão 18/75; SP Praia Grande 317/449; MG Santo Antônio do Retiro 237/395; AM Carauari 21/96; BA Itamaraju 172/98; ES São Mateus 21/1033; PE Jaboatão dos Guararapes 118/358.

**Prioridade B** — urnas do critério manual × tardia com maior z_manual (todas com leitor aparentemente inoperante; o log mostra se as habilitações manuais foram ao longo do dia ou no fim): MG Belo Horizonte 334/253; MT Cuiabá 1/879; RJ Rio de Janeiro 10/302, 214/325, 9/236, 188/329; SP Americana 384/230; ES Serra 26/651; SP Embu das Artes 391/164; PE Caruaru 105/324; DF Brasília 10/115; BA Candeias 127/326; CE Granja 25/117; PR Cambé 78/261; CE Sobral 24/330; CE Morada Nova 47/36; CE Massapê 45/89; RS Camaquã 12/212; RN Natal 3/473; CE Nova Russas 48/41; MA Caxias 4/283; BA Lauro de Freitas 180/386 e 180/331; GO Trindade 49/175; PI Batalha 45/32.

**Prioridade C** — demais 459 urnas `flag_tard` e 116 `flag_orig`, em `secoes_flagradas_brasil.csv` (ordenado por z_manual, com percentual de cada candidato a presidente na seção vs município).

## Arquivos em `out/brasil/`
`01`–`06` (saída do `analyze`, foco = 9 UFs do NE), `11_ranking_uf.csv`, `11_regioes.csv`, `11_nacional.csv`, `11a_ranking_manual.png`, `11b_ranking_suspeitas_cal.png`, `11b_ranking_suspeitas_orig.png`, `11c_ranking_encerramento.png`, `11d_regioes.png`, `12_quartis_aptos_limites.csv`, `12_estrat_tamanho_secao.csv`, `12_estrat_tipo_urna.csv`, `12_estrat_serie_urna_proxy_modelo.csv`, `12_estrat_porte_municipio.csv`, `12_flagradas_vs_base_por_quartil.csv`, `13_regionalidade_padronizada.csv`, `13_NE_vs_outros_por_celula.csv`, `secoes_flagradas_brasil.csv`, `15_correlacao_manual_voto_uf.csv`, `16_manual_x_encerramento_uf.csv`, `16_manual_por_faixa_encerramento_regiao.csv`, `16b_flag_tard_condicional.csv`.
