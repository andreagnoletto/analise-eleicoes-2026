# Piloto — Boletins de Urna 1º turno 2026: CE e BA (foco) vs RS e PR (controle)

Dados: `bweb_1t_<UF>_051020261403.zip` (TSE, dados abertos), SHA-512 conferido em todas as UFs (AC, CE, BA, RS, PR).
Votação ocorreu em **04/10/2026** (domingo); `05102026` no nome do arquivo é a data de geração.
Unidade de análise: 1 linha por urna/BU (seções agregadas não têm BU próprio e já estão somadas na seção agregadora).
Todas as 116.200 urnas das 5 UFs estão com `DS_TIPO_URNA = Apurada`.

## Resumo executivo

1. Consistência interna (aptos = comparecimento + abstenções, manual ≤ comparecimento) deu **zero erros** nas 4 UFs do piloto e no AC.
2. A taxa de habilitação manual **não é maior no Nordeste**: RS 8,6% e PR 7,7% superam BA 7,5% e CE 7,2% (média por seção); as distribuições têm a mesma forma.
3. O teste central (manual > 3σ e comparecimento > 2σ dentro do município) flagra 30 seções em 113.930 (BA 13, CE 8, RS 5, PR 4). **28 das 30 estão no quartil de seções menores** (≤ 275 aptos); recalculando o z dentro de município × quartil de tamanho sobram 9 (BA 7, CE 1, PR 1, RS 0). O sinal é, em grande parte, artefato de variância em seções pequenas.
4. A diferença regional real está no **encerramento**: 41% das urnas na BA e 35% no CE fecham mais de 30 min após as 17h, contra 3% no PR e 2% no RS. Isso é quase todo explicado por tamanho da seção (fila): seções grandes na BA/CE fecham em mediana +54 min; seções pequenas, +2–3 min, igual ao Sul.
5. A correlação entre taxa manual e voto em Lula existe em CE (+0,33) e BA (+0,23), mas cai para +0,15 / +0,09 dentro do município, é ~0 no PR e **negativa no RS** (−0,11, onde manual correlaciona com Flávio Bolsonaro). Padrão compatível com perfil socioeconômico do eleitorado (biometria falha mais em eleitores idosos/rurais), não com fraude direcionada. Nenhum achado do piloto exige explicação não inocente; a próxima etapa discriminante é o log das urnas.

## Ajustes feitos no script (`pipeline_bu.py`)

| Item | Antes | Depois | Motivo |
|---|---|---|---|
| Coluna de habilitação manual | `QT_ELEITORES_BIOMETRIA_NH` | `QT_ELEI_BIOM_SEM_HABILITACAO` | Layout 2026; definição no `_leiame-boletimurnaweb.pdf` do ZIP: "eleitores com biometria, mas que não foram habilitados por meio dela" |
| Hora de abertura/encerramento | `HR_ABERTURA`/`HR_ENCERRAMENTO` (`%H:%M:%S`) | `DT_ABERTURA`/`DT_ENCERRAMENTO` (`YYYY-MM-DD HH:MM:SS`, cast para TIMESTAMP) | Layout 2026 |
| Encerramento tardio | comparação fixa com 17:30/18:00/19:00 | `min_apos_fech` = minutos após o fechamento **local** previsto (17h; AC 15h; AM/MT/MS/RO/RR 16h; ZZ 17h local) | Os horários da urna estão no relógio local (AC abre 06:00 e fecha 15:00) |
| Filtro de urnas | nenhum | testes 2–6 só em `CD_TIPO_URNA = '1'` (Apurada); teste 1 conta as demais | Urnas anuladas/não instaladas têm quantidades inválidas |
| Região | NE vs "outros" | N / NE / CO / SE / S / ZZ | Fase 2 |
| `UFS_ALL` | 27 UFs | + ZZ | Fase 2 |
| Saída | `out/` | `--out` (padrão `out/piloto`) | Regra do projeto |
| Estrutura | SQL das tabelas dentro de `analyze()` | `build_tables(con)` reutilizável | Usado por `piloto_extras.py` |

Script novo `piloto_extras.py`: gráficos (06a–06d), detalhe das flagradas (07), estratificações (08), extras de interpretação (09–11).

**Ponto a confirmar:** `DS_TIPO_URNA` no buweb é o status de apuração (Apurada / Não apurada / Anulada…), não o modelo da urna (UE2009/2015/2020). Usei como *proxy* a faixa de série de `NR_URNA_EFETIVADA` (lotes de 100 mil), sem rotular modelos. Se houver tabela oficial série→modelo, ela entra sem mudar o resto.

## Resultado de cada teste

### Teste 1 — consistência interna (`01_consistencia.csv`)
Zero em todas as colunas de erro nas 5 UFs (soma errada, comparecimento > aptos, manual > comparecimento, manual negativo, sem hora de encerramento, não apurada). Há 2 seções na BA e 4 no CE com abstenção zero (comparecimento 100%), listadas como curiosidade, não erro.

### Teste 2 — distribuição da habilitação manual (`02_manual_por_uf.csv`, `06a_hist_manual.png`)

| UF | n seções | média manual | mediana | p95 | p99 | média comparecimento |
|---|---|---|---|---|---|---|
| RS | 27.547 | 8,59% | 7,59% | 17,3% | 24,1% | 78,8% |
| PR | 27.142 | 7,68% | 6,94% | 14,7% | 19,7% | 79,5% |
| BA | 35.476 | 7,52% | 6,57% | 15,5% | 21,5% | 80,3% |
| CE | 23.765 | 7,21% | 6,16% | 15,4% | 21,0% | 84,4% |
| AC | 2.270 | 5,11% | 4,57% | 10,4% | 14,3% | 79,7% |

### Teste 3 — seções com manual > 3σ e comparecimento > 2σ no município (`03_secoes_suspeitas.csv`, `07_secoes_flagradas_detalhe.csv`, `06b_scatter_manual_comp.png`)
30 seções (BA 13, CE 8, RS 5, PR 4). Características: 20 têm < 150 aptos e 12 têm < 100; a maior taxa manual é 94,5% (São Francisco do Conde/BA, zona 162, seção 153; a seção 46 da mesma zona tem 62%), padrão típico de leitor biométrico inoperante na seção inteira.
Voto: em 19 das 30 o percentual de Lula na seção supera o do município (média +3,5 pp, mediana +7,4 pp), mas as seções flagradas no RS desviam fortemente para Flávio Bolsonaro (Pelotas 60/123: +38 pp; 60/133: +51 pp). Ou seja, as flagradas são seções *atípicas* do município (pequenas, rurais ou especiais), e o desvio de voto segue o perfil local, não uma direção única.

### Teste 4 — suspeitas por mil (`04_suspeitas_por_uf.csv`, `06d_suspeitas_por_mil.png`)
BA 0,37‰ · CE 0,34‰ · RS 0,18‰ · PR 0,15‰. Com piso de 100 aptos: BA 0,23‰ · PR 0,15‰ · CE 0,13‰ · RS 0,11‰. Contagens de 3 a 13 por UF; a diferença NE × Sul não é estatisticamente distinguível de ruído neste n.

### Teste 5 — hora de encerramento (`05_encerramento_por_uf.csv`, `06c_encerramento_ecdf.png`, `10_encerramento_por_tamanho.csv`)

| UF | mediana (min após 17h local) | p95 | % > 30 min | % > 60 min | % > 120 min |
|---|---|---|---|---|---|
| BA | 19 | 130 | 41,3% | 24,2% | 6,3% |
| CE | 13 | 106 | 34,8% | 18,1% | 3,3% |
| AC (15h local) | 3 | 49 | 9,1% | 3,1% | 0,4% |
| PR | 2 | 20 | 3,1% | 0,9% | 0,05% |
| RS | 1 | 13 | 2,2% | 0,5% | 0,02% |

Por tamanho: no quartil maior (355–482 aptos) BA e CE fecham em mediana +54 min e ~70% passam de 30 min; no quartil menor, 5–6%, igual ao Sul. PR/RS fecham em +2–3 min em qualquer tamanho. A diferença regional é de **vazão por eleitor** (fila), não de seções isoladas.

### Teste 6 — correlação manual × voto (`06_correlacao_manual_voto.csv`, `09_correlacao_manual_voto_todas_ufs.csv`)

| UF | corr(manual, Lula) | idem intra-município | corr(comparecimento, Lula) | corr(manual, F. Bolsonaro) |
|---|---|---|---|---|
| CE | +0,33 | +0,15 | −0,25 | −0,33 |
| BA | +0,23 | +0,09 | +0,03 | −0,18 |
| PR | +0,05 | +0,02 | −0,24 | +0,04 |
| RS | −0,11 | −0,07 | −0,47 | +0,14 |

Se mesários votassem por ausentes a favor de um candidato, comparecimento e manual deveriam correlacionar positivamente com esse candidato nas mesmas seções. No CE o comparecimento alto correlaciona com Flávio Bolsonaro (+0,26), o oposto do manual. Nos controles o sinal do manual inverte conforme o perfil rural/urbano local.

### Extra — taxa manual por faixa de encerramento (`11_manual_por_faixa_encerramento.csv`)
A taxa manual cresce com o atraso de fechamento em **todas** as UFs (BA 7,2% → 10,1%; CE 7,0% → 9,9%; PR 7,5% → 12,5%; RS 8,5% → 12,4% nas faixas tardias). Explicação mais plausível: cada habilitação manual demora mais e atrasa a fila (causalidade manual → atraso), não o contrário.

## Explicações alternativas testadas (`08_*.csv`)

| Explicação | Resultado |
|---|---|
| Tamanho da seção | **Confirmada como principal fator.** Quartil Q1 (20–275 aptos) tem 25% da base e 93% das flagradas. Taxa manual média cai monotonicamente com o tamanho em todas as UFs (BA 8,8% → 6,5%; RS 11,0% → 7,2%). Z recalculado em município × quartil: 30 → 9 flagradas (BA 7, CE 1, PR 1, RS 0). |
| Modelo de urna (`DS_TIPO_URNA`) | Não testável: a coluna só tem "Apurada". |
| Modelo de urna (proxy: faixa de série) | Séries 1,6M–1,8M têm taxa manual 10–13% em todas as 4 UFs, contra 5–8% nas séries 2,0M+. Efeito de equipamento, igual no NE e no Sul. Flagradas se espalham por todas as faixas (BA tem 4 em 1,6–1,8M, 4 em 2,4M). |
| Fila (encerramento tardio) | Explicada por tamanho de seção e menor vazão em BA/CE; não discrimina seções individuais nessas UFs porque 35–41% delas são "tardias". |
| Perfil do eleitorado (manual ↔ voto) | Correlação bruta encolhe 60% dentro do município e inverte de sinal no RS. |

Para descartar de vez o resto: (a) nome/tipo do local de votação das flagradas (dataset "eleitorado por local de votação") para identificar seções especiais (presídios, hospitais, aldeias, quartéis); (b) **log de urna (.logjez)** para ver em que horário as habilitações manuais ocorreram — é o único dado que testa diretamente a hipótese "manual concentrado no fim".

## Thresholds — avaliação

- `z_manual > 3 e z_comp > 2` no município: como estão, selecionam principalmente seções pequenas (variância ∝ 1/√n). Sob normalidade e independência o esperado seria ~3–4 seções em 114 mil; vieram 30, todas de ruído de amostragem pequena.
- `n_mun ≥ 8`: inócuo (exclui 0,4% das seções), pode ficar.
- Z binomial puro (esperado = taxa do município): liberal demais (218 flags na BA), porque a taxa manual tem sobredispersão real entre seções.
- Recomendação para a Fase 2: manter z empírico 3/2, mas calculado **dentro de município × quartil de aptos** e com piso de **100 aptos** (seções menores reportadas à parte), e exigir também `min_apos_fech > 30` como terceiro critério só fora do NE (onde não discrimina). Alternativa: z quase-binomial com fator de sobredispersão estimado por UF.

## Seções para baixar o log de urna (.logjez)

Prioridade A — sobrevivem ao z em município × quartil, ou indicam leitor biométrico inoperante:

| UF | Município | Zona | Seção | Aptos | Comp. | Manual | Enc. (min após 17h) |
|---|---|---|---|---|---|---|---|
| BA | Eunápolis | 203 | 316 | 141 | 132 | 20 | +1 |
| CE | Acopiara | 60 | 283 | 63 | 60 | 19 | +2 |
| BA | Salvador | 4 | 243 | 377 | 330 | 41 | +165 |
| BA | Salvador | 4 | 242 | 377 | 347 | 41 | +201 |
| BA | Barra do Choça | 139 | 228 | 277 | 244 | 35 | +4 |
| BA | São Francisco do Conde | 162 | 153 | 223 | 200 | 189 | +36 |
| BA | São Francisco do Conde | 162 | 46 | 272 | 236 | 146 | +2 |
| PR | São José dos Pinhais | 8 | 443 | 362 | 319 | 39 | +6 |
| BA | Itamaraju | 172 | 98 | 403 | 331 | 36 | +248 |
| BA | Salvador | 8 | 687 | 56 | 53 | 7 | +4 |

Prioridade B — demais flagradas do teste 3 original (`03_secoes_suspeitas.csv`): BA Paulo Afonso 181/215; CE Pedra Branca 59/102 e 59/112; PR Araucária 50/82; BA Salvador 15/393; BA Iaçu 193/143; CE Caucaia 37/628 e 123/570; RS Cachoeira do Sul 10/321; CE Jucás 43/117; BA Paramirim 111/229; BA Senhor do Bonfim 45/319; BA Sento Sé 96/119; CE Tauá 19/258; RS Sant'Ana do Livramento 30/214; BA Riachão do Jacuípe 114/265; CE Banabuiú 6/411; BA Juazeiro 47/348; PR Tijucas do Sul 199/117; RS São Lourenço do Sul 80/90; PR Fazenda Rio Grande 144/36; RS Pelotas 60/123 e 60/133; PR Guarapuava 43/406.

Lista completa com z nas duas versões: `08_flagradas_z_municipio_vs_z_quartil.csv`.

## Arquivos

`01_consistencia.csv`, `02_manual_por_uf.csv`, `03_secoes_suspeitas.csv`, `04_suspeitas_por_uf.csv`, `05_encerramento_por_uf.csv`, `06_correlacao_manual_voto.csv`, `06a_hist_manual.png`, `06b_scatter_manual_comp.png`, `06c_encerramento_ecdf.png`, `06d_suspeitas_por_mil.png`, `07_secoes_flagradas_detalhe.csv`, `08_quartis_aptos_limites.csv`, `08_estrat_tamanho_secao.csv`, `08_estrat_tipo_urna.csv`, `08_estrat_serie_urna_proxy_modelo.csv`, `08_flagradas_vs_base_por_quartil.csv`, `08_flagradas_z_municipio_vs_z_quartil.csv`, `09_correlacao_manual_voto_todas_ufs.csv`, `10_encerramento_por_tamanho.csv`, `11_manual_por_faixa_encerramento.csv`.
