# BU do 2º turno: comparação seção a seção com o 1º turno e as predições P1–P5

Escrito em 27/10/2026, noite de D+2, com o BU completo (28 UFs). Fecha a Fase 1 de `docs/ESCOPO_2T.md`. As predições foram registradas antes dos dados e são verificadas mecanicamente por `comparar_turnos.py`. Reproduzível com:

```bash
TURNO=2 python pipeline_bu.py download --uf ALL          # carimbo 261020260742 em data/2t/STAMP; SHA-512 de cada zip
TURNO=2 python pipeline_bu.py load --uf ALL              # data/2t/bu2026_2t.duckdb
TURNO=2 python pipeline_bu.py analyze --foco CE BA --out out/2t/piloto
TURNO=2 python analise_brasil.py --out out/2t/brasil     # critérios do 1º turno aplicados ao 2º
TURNO=2 python comparar_turnos.py bu --out out/2t/comparacao
TURNO=2 python logs_brasil.py anexar_bu                  # campos bu_* nos parquets dos logs
```

## 1. Dados e publicação

| | |
|---|---|
| Arquivo | `bweb_2t_<UF>_261020260742.zip`, 28 UFs, 141 MB no total, SHA-512 conferido um a um |
| Gerado pelo TSE | 26/10 07h42 (D+1) |
| No catálogo do portal | 27/10 entre 15h59 e 16h21 (D+2; o catálogo registra 18h59 a 19h21 em UTC), 27 UFs. **O zip de RR nunca entrou no catálogo** até as 22h40 (só o seu `.sha512`, duas vezes), mas já estava no CDN (`cdn.tse.jus.br/.../buweb/`), de onde foi baixado com o mesmo hash |
| Linhas carregadas | 2.088.107 |
| Seções apuradas | **499.205** (1º turno: 499.206); Presidente em 28 UFs, Governador em 6 (AC, AM, DF, ES, RN, TO) |
| Consistência (`piloto/01_consistencia.csv`) | 0 seções não apuradas, 0 somas erradas, 0 com comparecimento > aptos ou manual > comparecimento; 27 seções do exterior sem hora de encerramento e 2 linhas de Trípoli (exterior) com cargo nulo e comparecimento 0 |

Em 2022 e 2024 o BU do 2º turno saiu em D+1. Em 2026 o arquivo foi gerado em D+1 e publicado em D+2 à tarde. O vigia (`aguardar_2t.py --auto`) esperava as 28 UFs antes de disparar e, como RR não entrou no catálogo, o download foi feito à mão às 22h44.

**Logs × BU.** Com o BU anexado aos parquets da varredura de logs (`logs_brasil.py anexar_bu`), o comparecimento do BU é igual ao número de votos do log em **499.168 das 499.177 urnas (99,998%)**. O número de habilitações manuais é igual em 496.721 (99,5%); nas 2.456 urnas restantes a diferença é de 1 em 95% dos casos (média 1,04; 3 urnas com diferença maior que 5) e o log é maior em 2.453 delas. As duas fontes descrevem as mesmas seções.

## 2. Panorama nacional (`20_regioes.csv`, `20_uf.csv`, `20a_uf_1t_vs_2t.png`)

Seções pareadas por UF, município, zona e seção: 499.205 (só no 1º turno: 1; só no 2º: 0). Sem o exterior e com aptos ≥ 100 nos dois turnos ficam 497.897 seções.

| Região | n | manual 1t | manual 2t | comparecimento 1t | 2t | encerramento mediano 1t | 2t | > 30 min tarde 1t | 2t |
|---|---|---|---|---|---|---|---|---|---|
| CO | 38.048 | 6,77 % | 6,49 % | 78,3 % | 79,9 % | 4 min | 1 min | 10,4 % | 0,13 % |
| N | 43.769 | 5,48 % | 5,53 % | 80,7 % | 78,6 % | 7 | 1 | 26,2 % | 0,07 % |
| NE | 140.828 | 7,14 % | 7,37 % | 81,8 % | 83,4 % | 14 | 1 | 36,4 % | 1,56 % |
| S | 72.015 | 8,05 % | 7,91 % | 79,6 % | 81,9 % | 2 | 1 | 3,1 % | 0,02 % |
| SE | 203.237 | 6,55 % | 6,58 % | 77,4 % | 79,7 % | 3 | 1 | 7,7 % | 2,61 % |
| **BR** | **497.897** | **6,86 %** | **6,90 %** | **79,3 %** | **81,0 %** | **4** | **1** | **17,0 %** | **1,52 %** |

A taxa manual por UF vai de 4,1 % (RR) a 9,3 % (PI) no 2º turno, e a variação entre turnos fica entre −0,57 pp (MS) e +0,43 pp (AL) em todas as 27 UFs. O comparecimento subiu 1,7 pp no país e caiu só no Norte (−2,0 pp). O encerramento tardio (> 30 min após o horário local) caiu de 17 % para 1,5 %; o que restou está em RJ (8,8 %), PE (3,4 %), BA (3,0 %) e PB (3,0 %), as UFs da prorrogação até as 19h determinada pelo STF, já explicada no relatório dos logs.

## 3. As cinco predições (`24_predicoes.csv`)

| | Predição registrada | Observado | |
|---|---|---|---|
| P1 | Encerramento tardio (> 30 min) cai em **todas** as regiões | N 26,2 % → 0,1 %; NE 36,4 % → 1,6 %; CO 10,4 % → 0,1 %; SE 7,7 % → 2,6 %; S 3,1 % → 0,0 % | **✓** |
| P2 | NE e N continuam fechando depois do Sul (mediana), mas a diferença encolhe | NE − S na mediana: 12 min → **0 min** | **✗** |
| P3 | Taxa manual nacional estável (± 1,5 pp) | 6,86 % → 6,90 % | **✓** |
| P4 | corr(1t, 2t) da taxa manual > 0,5 nas urnas mantidas e maior que nas trocadas | mesma urna 0,804; trocada 0,542 | **✓** |
| P5 | Seções com Δmanual e Δcomparecimento conjuntamente anômalos ≤ 0,2 ‰, nenhuma região > 2× a média | 89 seções, 0,180 ‰; NE 0,279 ‰ = 1,55× a média | **✓** |

**P1 e P2, lidas juntas.** O atraso de encerramento do 1º turno era tempo de cédula. Com um cargo (dois nas seis UFs com governador), o atraso sumiu em todo o país, e sumiu por inteiro: a diferença Nordeste–Sul na mediana foi de 12 minutos a zero. P2 previa que sobraria uma diferença menor (eleitorado mais lento no NE) e **falhou**, mas na direção que reforça a explicação pela cédula, não na que a enfraquece: não há resíduo regional a explicar. A coluna "se errar" da tabela de predições ("diferença regional tem outra causa") valia para o caso de a diferença não encolher; não é este.

**P3.** A taxa nacional é a mesma com cédula longa e curta, com mesários sorteados de novo ou não, em dois domingos com três semanas de intervalo.

**P4, com a taxa manual oficial do BU.** O critério é atendido. Por série da urna e situação da urna (seções com aptos ≥ 100, `22_persistencia_serie.csv`):

| Série da urna | Urna | n | corr(1t, 2t) | manual 1t | manual 2t |
|---|---|---|---|---|---|
| nova (≥ 2.000.000) | mesma | 394.483 | 0,791 | 6,10 % | 6,14 % |
| nova | trocada | 2.544 | 0,704 | 6,21 % | 6,29 % |
| antiga (< 2.000.000) | mesma | 96.261 | 0,818 | 9,81 % | 9,88 % |
| antiga | trocada | 1.842 | 0,380 | 11,77 % | 11,50 % |

Por UF, nas mesmas urnas, de 0,63 (RR) e 0,68 (AP) a 0,86 (RS, CE, AL). A leitura feita em `RELATORIO_CORRESP.md` com a taxa dos logs se mantém: a correlação de postos é igual com e sem troca de urna, o grupo trocado é selecionado pelas falhas do leitor (por isso o Pearson baixo nas urnas antigas trocadas), e a taxa manual é uma propriedade do **eleitorado da seção**. A taxa de comparecimento da seção também persiste (corr 0,60 a 0,94 por UF).

**P5** é o teste direto da hipótese do estudo e tem a seção 4.

## 4. As 89 seções com manual e comparecimento subindo juntos (`23_flag_delta.csv`, `23a_scatter_delta.png`)

Critério registrado: dentro do município (n ≥ 8 seções), Δ da taxa manual acima de 3 desvios **e** Δ da taxa de comparecimento acima de 2 desvios, seções com aptos ≥ 100 nos dois turnos, fora o exterior. Elegíveis: 494.281. Flagradas: **89 (0,180 ‰)**.

| | |
|---|---|
| Por região (‰) | CO 0,026; N 0,139; NE 0,279; S 0,126; SE 0,168 |
| Por UF, mais altas | MA 13 (0,73 ‰), SE 4 (0,68 ‰), AM 3 (0,37 ‰), PE 7 (0,33 ‰), ES 3, BA 10, RJ 9, MG 11 |
| Esperado se Δmanual e Δcomparecimento fossem independentes | 1.307 seções passam o corte de manual e 11.768 o de comparecimento; produto: 31. Permutando Δcomparecimento dentro de cada município 20 vezes: média 31, de 21 a 45 |
| Correlação entre os dois z no país | 0,025 |
| Mesma urna física nos dois turnos | 86 de 89 |
| Dias de falha total do leitor (manual > 50 %) no 2º turno | 1 de 89 (Lauro de Freitas/BA, z180 s149, 219 manuais em 319; urna trocada) |
| Série antiga | 16 de 89 (18 %; na base, 20 %) |
| Comparecimento médio | 71,9 % → 80,0 % (país: 79,3 % → 81,0 %) |
| Taxa manual mediana | 7,2 % → 14,7 % |
| Encerramento | 33 min mais cedo, em média, no 2º turno |
| **Fatia de Lula entre os dois finalistas, em relação ao município** | **−0,25 pp ± 0,24 pp** (variação do 1º para o 2º turno nas 89, descontada a variação do município) |

Há cerca de três vezes mais seções com os dois saltos juntos do que o acaso daria. A associação é fraca no país inteiro (correlação 0,025 entre os z) e tem explicação inocente direta: quem faltou no 1º turno e veio no 2º é, em média, mais velho e tem mais dedos que o sensor não lê ou biometria não cadastrada; além disso, fila maior leva mesários a liberar manualmente depois das tentativas falhas. O que um mecanismo de "votar por ausentes" teria de produzir, e não produz, é deslocamento do voto: nas 89 seções a fatia do candidato que venceu não se moveu em relação ao município (−0,25 pp, dentro do erro). Os maiores casos:

| UF | Município | Zona | Seção | comparecimento 1t → 2t | manuais 1t → 2t | manual 2t | mesma urna | Lula vs município, Δ |
|---|---|---|---|---|---|---|---|---|
| BA | Lauro de Freitas | 180 | 149 | 253 → 319 | 41 → 219 | 69 % | não | −3,2 pp |
| MA | Viana | 20 | 172 | 121 → 129 | 14 → 39 | 30 % | sim | +0,6 pp |
| PE | Jaboatão dos Guararapes | 118 | 355 | 327 → 352 | 24 → 53 | 15 % | sim | −1,2 pp |
| AM | Atalaia do Norte | 42 | 37 | 107 → 128 | 10 → 29 | 23 % | sim | −3,9 pp |
| MA | Imperatriz | 65 | 587 | 279 → 301 | 15 → 41 | 14 % | sim | −3,7 pp |
| MG | Uberlândia | 278 | 515 | 239 → 268 | 19 → 43 | 16 % | sim | −2,2 pp |
| MG | Belo Horizonte | 39 | 168 | 281 → 365 | 0 → 34 | 9 % | não | −1,1 pp |
| MA | Olho d'Água das Cunhãs | 87 | 54 | 175 → 187 | 6 → 29 | 16 % | sim | −1,7 pp |

Lauro de Freitas é um dia de leitor morto numa urna de contingência (69 % de manuais é falha de sensor, não conduta). Belo Horizonte z39 s168 é o inverso: no 1º turno a urna não registrou nenhuma habilitação manual, no 2º outra urna registrou 9 %, que é a taxa normal da cidade; a anomalia é o zero do 1º turno.

## 5. Votos (`25_votos_delta_uf.csv`)

Para cada UF e cada finalista, correlação entre a variação da taxa manual e a variação da fatia do candidato nos votos nominais, bruta e dentro do município:

- Δmanual × Δfatia, intra-município: entre **−0,034 e +0,040** nas 27 UFs e nos dois candidatos. Zero.
- Δcomparecimento × Δfatia: até +0,30 (AP, Bolsonaro), +0,23 (RR, Bolsonaro), +0,21 (AC); até −0,17 (MS, PR, SC, Bolsonaro). Onde o comparecimento variou, o voto variou junto, para um lado ou para o outro. É mobilização, e não tem relação com a habilitação manual.

## 6. Os critérios de "seção suspeita" do 1º turno, aplicados ao 2º (`../brasil/`)

Os três critérios de `analise_brasil.py` rodaram sobre o BU do 2º turno com as mesmas definições do 1º.

| Critério | 1º turno | 2º turno | Seções que repetem | Repetição esperada ao acaso |
|---|---|---|---|---|
| **orig** (z_manual > 3 e z_comp > 2 no município) | 116 (0,232 ‰) | 107 (0,214 ‰) | **28** | 0,03 |
| **cal** (idem, em município × quartil de aptos, aptos ≥ 100) | 27 (0,054 ‰) | 41 (0,082 ‰) | **7** | 0,002 |
| **tard** (z_manual > 3 e encerramento > 60 min) | 459 | 50 | 4 | |

As 50 do critério **tard** estão em SP (20), RJ (12), BA (11), PE e PB, com encerramento mediano 121 min após o horário: são as zonas da prorrogação do STF. Nenhuma das 41 do critério **cal** é dia de falha total do leitor (taxa manual mediana 17 %, aptos mediano 288); por região, NE 22, SE 8, N 7, S 3, CO 1 (NE 0,156 ‰, 1,9× a média nacional).

A repetição é o dado novo. Sete das 27 seções calibradas do 1º turno voltam a ser flagradas no 2º, quando o acaso daria zero, e com os **mesmos números** nos dois turnos:

| UF | Município | Zona | Seção | aptos | comparecimento 1t / 2t | manuais 1t / 2t | Lula vs município 1t / 2t |
|---|---|---|---|---|---|---|---|
| BA | Eunápolis | 203 | 316 | 141 | 132 / 125 | 20 / 18 | +21,7 pp / +22,6 pp |
| BA | Juazeiro | 47 | 312 | 338 | 306 / 310 | 35 / 38 | +18,5 / +18,9 |
| BA | Salvador | 4 | 243 | 377 | 330 / 346 | 41 / 40 | +16,0 / +18,4 |
| PE | Vitória de Santo Antão | 18 | 75 | 108 | 101 / 107 | 15 / 18 | −2,1 / −3,4 |
| SP | Mairiporã | 237 | 48 | 288 | 258 / 259 | 41 / 49 | −9,4 / −9,3 |
| SP | Praia Grande | 317 | 449 | 365 | 307 / 317 | 48 / 53 | +2,7 / +0,8 |
| SP | Vargem Grande do Sul | 229 | 86 | 340 | 285 / 293 | 51 / 50 | −6,7 / −5,7 |

Comparecimento, manuais e inclinação política iguais em dois domingos diferentes é a assinatura de uma **característica da seção** (quem está inscrito nela), não de um evento do dia. Essas seções têm mais comparecimento e mais eleitores sem biometria que o resto do município e votam de forma estável; o critério as flagra porque mede exatamente isso. O que confirmaria a leitura é o perfil etário e de cadastro biométrico da seção, que não está nos dados abertos; o que a derrubaria seria o voto se deslocando entre os turnos, e ele não se desloca.

## 7. Anomalia ≠ fraude

| Observação | Explicação inocente mais plausível | O que seria preciso para descartá-la |
|---|---|---|
| 89 seções com manual e comparecimento subindo juntos, 3× o acaso | eleitores que faltaram no 1º turno e vieram no 2º têm mais biometria ilegível ou não cadastrada; fila maior leva a liberar manualmente | voto deslocado nessas seções em relação ao município; não há (−0,25 pp ± 0,24) |
| NE com 0,279 ‰ nessas seções, 1,55× a média | NE tem maior taxa manual e maior salto de comparecimento (+1,7 pp); o critério é relativo ao município, mas a variância de Δ é maior onde o nível é maior | o mesmo teste de voto por UF: Δmanual × Δfatia entre −0,03 e +0,01 nas 9 UFs do NE |
| 7 de 27 seções "suspeitas" do 1º turno repetem no 2º com os mesmos números | característica do eleitorado da seção | perfil da seção (fora dos dados abertos); deslocamento de voto entre turnos, que não ocorre |
| Encerramento tardio sobrou em RJ, PE, BA, PB | prorrogação até as 19h pelo STF; totais por UF batem com os logs | explicado no relatório dos logs |
| Lauro de Freitas z180 s149: 219 manuais em 319 | falha total do sensor numa urna de contingência | caderno de ocorrências da seção |
| Belo Horizonte z39 s168: 0 → 34 manuais | o zero do 1º turno é que é raro (sensor perfeito ou registro incompleto); 9 % é a taxa da cidade | log da urna do 1º turno |
| P2 falhou: diferença NE–S foi a zero | a diferença do 1º turno era toda tempo de cédula | nada a descartar; a predição previa resíduo e não houve |

## 8. Conclusão

A hipótese do estudo era que a habilitação manual se concentra no fim da sessão e é usada para votar por ausentes, com destaque no Nordeste. O BU do 2º turno, comparado seção a seção com o do 1º, diz o mesmo que os logs dos dois turnos e o BU do 1º: a taxa manual é a mesma nos dois domingos (6,86 % e 6,90 %) e é uma propriedade estável de cada seção (correlação 0,80 entre turnos), independente da urna, da mesa e do dia; o encerramento tardio era a cédula e sumiu com ela, no Nordeste como em todo lugar; as seções em que manual e comparecimento subiram juntos são 0,18 ‰, não se concentram regionalmente além do registrado e não movem o voto; as seções "suspeitas" que repetem entre turnos repetem com os mesmos números, que é o que o eleitorado faz e a fraude não. Quatro das cinco predições registradas antes dos dados se confirmaram, e a quinta falhou por sobrar menos diferença regional do que o previsto.

O único achado localizado de todo o estudo continua sendo o do 1º turno (Bom Lugar e Maranhãozinho, MA, eleitores manuais votando duas vezes mais rápido), que não se repetiu no 2º turno e para o qual a recomendação é a mesma: conferir o caderno de votação dessas seções.

## 9. O que fica

1. `data/2t/csv` (CSVs extraídos do BU do 2º turno) e `data/csv` (30 GB, 1º turno) podem ser apagados; os DuckDB bastam. Os 50 GB de logs brutos do 2º turno em `data/2t/logs/raw` só são necessários para refazer a varredura. Decisão do usuário.
2. Governador nas seis UFs e comparação com 2022 ficam fora do escopo, como registrado em `docs/ESCOPO_2T.md`.
