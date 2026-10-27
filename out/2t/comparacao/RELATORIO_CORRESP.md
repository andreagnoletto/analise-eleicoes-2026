# Correspondências de urna: mesma urna física 1º → 2º turno e a predição P4, antes do BU

Escrito em 27/10/2026, D+2 do 2º turno, com o BU do 2º turno ainda não publicado. Reproduzível com:

```bash
python correspondencias.py download   # 84 arquivos, SHA-512 conferido um a um
python correspondencias.py load       # data/2t/corresp.duckdb
python correspondencias.py comparar   # out/2t/comparacao/26_*, 27_*, 28_*
```

## 1. O que são estes dados

O TSE publica, por UF, a **correspondência esperada** (que urna, pelo número de série, foi carregada para cada seção; sai na véspera) e a **correspondência efetivada** (qual urna de fato votou em cada seção; sai no dia seguinte, antes do BU). As duas diferem quando a urna da seção falha e uma de contingência a substitui.

| Arquivo | Turno | Publicado | Conteúdo | Linhas |
|---|---|---|---|---|
| `CESP_1t_<UF>_041020261259` | 1º | 04/10 12h59 | esperada, versão do dia da eleição | 499.177 |
| `CEFT_1t_<UF>_051020261049` | 1º | 05/10 10h49 | efetivada (esperada + efetivada + origem do voto) | 499.207 |
| `CESP_2t_<UF>_241020261231` | 2º | 24/10 12h31 | esperada | 499.166 |
| `CEFT_2t` | 2º | **não publicada** em 27/10 11h40 | | |

No 1º turno a efetivada saiu 3 h 14 antes do BU (10h49 → 14h03). A efetivada do 2º turno é, portanto, o aviso prévio da publicação do BU, e `aguardar_2t.py` já vigia o conjunto do BU a cada 10 min.

## 2. Validação contra o BU do 1º turno (`26_corresp_validacao_1t.csv`)

| Teste | Resultado |
|---|---|
| Seções apuradas no BU 1t × seções na efetivada 1t | 499.206 de 499.206 têm correspondência |
| `NR_URNA_EFETIVADA` do BU = urna efetivada do arquivo | **100,0 %** (0 divergências) |
| Esperada da véspera ≠ efetivada | 0,61 % (3.032 seções) |
| Esperada do dia ≠ efetivada | 0,61 % (3.034 seções) |
| Origem do voto ≠ "Urna Eletrônica" | 80 seções: 50 "BU gerado por RED em urna de seção", 31 "Sistema de apuração" (uma delas também com urna trocada) |

A fonte bate exatamente com o BU. A "esperada" erra a urna em 0,6 % das seções, que é a taxa de substituição por contingência no dia. É esse o erro máximo esperado do provisório do 2º turno na seção 3.

## 3. Mesma urna física entre os turnos, provisório (`26_mesma_urna_1t_2t_provisorio_uf.csv`, `26_origem_urna_2t.csv`)

| | |
|---|---|
| Seções pareadas (no BU 1t e na esperada 2t) | 499.166 |
| Só no 1º turno | 40 (28 no exterior, 12 no país: SE 5, RN 2, RJ 2, AC/MG/MT 1; seções agregadas) |
| Só no 2º turno | 0 |
| **Mesma urna física** (esperada 2t = efetivada 1t) | **99,71 %** |
| Urna que não votou em seção no 1º turno (contingência/reserva/nova) | 0,28 % |
| Urna que estava em outra seção no 1º turno | 0,01 % |
| UFs com menos repetição | RR 98,7 %, SE 99,1 %, ES 99,4 % |
| Urnas de contingência previstas para o 2º turno (`ccont_2t`) | 48.815 (SP 10.459, RJ 3.703, MG 3.675, BA 3.660, RS 3.042) |

Quando a efetivada do 2º turno sair, cerca de 0,6 % destas seções (≈ 3 mil) deverão mudar de "mesma urna" para "trocada". Isso aumenta o grupo trocado, mas não muda o quadro nacional.

## 4. Predição P4, verificação provisória pelos logs (`27_p4_provisorio*.csv`)

P4, registrada em `docs/ESCOPO_2T.md` antes dos dados: *"Taxa manual persiste na mesma urna física: corr(1t, 2t) > 0,5 nas urnas mantidas e maior que nas trocadas"*. Aqui a taxa manual é `log_manual / log_votos` da varredura de logs dos dois turnos (seções com ≥ 50 votos nos dois), e "mesma urna" é a da seção 3.

| Grupo | n | Pearson r | Spearman ρ | mediana tx 1t | mediana tx 2t |
|---|---|---|---|---|---|
| mesma urna | 495.790 | **0,821** | 0,794 | 6,1 % | 6,1 % |
| urna trocada | 1.451 | **0,458** | 0,797 | 6,8 % | 6,8 % |
| mesma urna, sem dias de falha total do leitor (tx > 0,5) | 495.629 | 0,829 | 0,794 | | |
| urna trocada, sem dias de falha total | 1.442 | 0,779 | 0,797 | | |

**Critério registrado: atendido** (0,82 > 0,5 e 0,82 > 0,46). Mas a leitura literal enganaria. A correlação de **postos** é igual nos dois grupos (0,79 e 0,80), e a diferença de Pearson vem de nove seções em que o leitor praticamente não funcionou em um dos turnos (taxa manual de 0,87 a 0,98 num dia e 0,07 a 0,20 no outro, quase todas UE2013 substituídas por UE2015). Sem elas, a diferença entre mesma urna e urna trocada cai para 0,05 (0,83 contra 0,78).

Conclusão provisória: **a taxa de habilitação manual é uma propriedade do eleitorado da seção**, não do leitor e muito menos do dia ou da mesa. Uma seção que teve 12 % de manuais em 4 de outubro teve algo próximo disso em 25 de outubro, com a mesma urna ou com outra, com outros mesários sorteados ou os mesmos. O leitor pesa só nos extremos (seção 5). O mecanismo escrito na tabela de predições ("leitor é a causa dominante") estava errado; a predição em si não.

Por modelo, só nas mesmas urnas: UE2013 r = 0,73 (n 11.199), UE2015 0,82 (86.760), UE2020 0,78 (199.718), UE2022 0,80 (198.113). Por UF, nas mesmas urnas, de RR 0,63 e AP 0,68 a CE e AL 0,85; nas trocadas com n ≥ 30, de ES 0,24 (ρ 0,84; 60 seções, uma delas a de 0,98 → 0,07) a PA 0,92.

Para a hipótese do estudo: um mecanismo de "votar por ausentes" via habilitação manual precisaria fazer a taxa de uma seção se afastar do seu padrão do 1º turno em lugares específicos. O teste direto disso é o `flag_delta` (Δmanual e Δcomparecimento conjuntamente anômalos no município, predição P5), que depende do comparecimento do BU do 2º turno.

## 5. Falha total do leitor (`28_falha_leitor_*.csv`)

Definição operacional: seção com ≥ 50 votos em que mais da metade dos eleitores foi habilitada manualmente (tx > 0,5). É o que se espera quando o sensor biométrico não lê.

| Modelo (1º turno) | seções | com falha total | por mil |
|---|---|---|---|
| UE2013 | 10.866 | 119 | **10,95 ‰** |
| UE2015 | 87.673 | 17 | 0,19 ‰ |
| UE2020 | 200.243 | 1 | 0,00 ‰ |
| UE2022 | 198.538 | 1 | 0,01 ‰ |

| 2º turno | falhas no 1t | repetiram no 2t | novas no 2t |
|---|---|---|---|
| mesma urna | 133 | **64 (48 %)** | 28 |
| urna trocada | 5 | **0** | 4 |

Metade das urnas que falharam no 1º turno e voltaram à mesma seção falharam de novo; nenhuma das 5 que foram trocadas. É um sinal de hardware (sensor), concentrado no modelo mais antigo, e explica as taxas manuais extremas sem recorrer a conduta da mesa. A lista das 170 seções com falha total em algum dos turnos está em `28_falha_leitor_secoes.csv`.

## 6. Anomalia ≠ fraude: explicações inocentes e o que as descartaria

| Observação | Explicação inocente mais plausível | O que seria preciso para descartá-la |
|---|---|---|
| Taxa manual de uma seção se repete entre turnos (r ≈ 0,8) mesmo com urna trocada | É o eleitorado: eleitores sem biometria cadastrada e dedos que o sensor não lê (idosos, trabalho manual) votam na mesma seção nos dois turnos | Nada a descartar: é o comportamento esperado e o oposto do que a hipótese do estudo previa |
| Nove seções com tx 0,87–0,98 num turno e normal no outro, com troca de urna | Sensor defeituoso identificado e substituído pela contingência | Caderno de ocorrências da seção (fora dos dados abertos) |
| 48 % das falhas totais repetem na mesma urna; 0 % nas trocadas | Defeito de hardware persistente em UE2013 | Com a efetivada do 2º turno: se as "mesmas urnas" que repetiram forem na verdade substituições do dia, a leitura muda |
| 0,61 % das seções mudam de urna no dia | Substituição por contingência | É o procedimento padrão, registrado em `TP_DIVERGENCIA = C` |

## 7. O que ainda falta e o que muda com o BU

1. `CEFT_2t` (efetivada): substitui a esperada em `mesma_urna` e marca as ~3 mil substituições do dia 25.
2. BU do 2º turno: taxa manual oficial (`QT_ELEI_BIOM_SEM_HABILITACAO / QT_COMPARECIMENTO`), comparecimento e encerramento por seção; refaz P4 (`comparar_turnos.py bu`, item 22) e permite P1, P2, P3 e P5.
3. Nenhum número desta nota entra nos relatórios finais sem ser recalculado com a efetivada e o BU.
