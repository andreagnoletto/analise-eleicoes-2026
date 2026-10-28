# Correspondências de urna: mesma urna física 1º → 2º turno e a predição P4, antes do BU

Escrito em 27/10/2026, D+2 do 2º turno, com o BU do 2º turno ainda não publicado. Primeira versão pela manhã com a correspondência *esperada*; refeito com a *efetivada*, que entrou no portal entre 9h50 e 10h24 (horário de Brasília; o catálogo registra 12h50 a 13h24 em UTC). Reproduzível com:

```bash
python correspondencias.py download   # 140 arquivos, SHA-512 conferido um a um
python correspondencias.py load       # data/2t/corresp.duckdb
python correspondencias.py comparar   # out/2t/comparacao/26_*, 27_*, 28_*
```

## 1. O que são estes dados

O TSE publica, por UF, a **correspondência esperada** (que urna, pelo número de série, foi carregada para cada seção; sai na véspera e de novo no dia) e a **correspondência efetivada** (qual urna de fato votou em cada seção, e por que meio o BU chegou à totalização; sai depois da eleição). As duas diferem quando a urna da seção falha e uma de contingência a substitui.

| Arquivo | Turno | Gerado | Conteúdo | Linhas |
|---|---|---|---|---|
| `CESP_1t_<UF>_041020261259` | 1º | 04/10 12h59 | esperada, versão do dia da eleição | 499.177 |
| `CEFT_1t_<UF>_051020261049` | 1º | 05/10 10h49 | efetivada (esperada + efetivada + origem do voto) | 499.207 |
| `CESP_2t_<UF>_241020261231` | 2º | 24/10 12h31 | esperada, véspera | 499.166 |
| `CESP_2t_<UF>_251020261345` | 2º | 25/10 13h45 | esperada, dia da eleição | 499.178 |
| `CEFT_2t_<UF>_261020261201` | 2º | 26/10 12h01 (no portal em 27/10, 9h50 a 10h24) | efetivada | 499.207 |

No 1º turno a efetivada saiu 3 h 14 antes do BU (10h49 → 14h03). No 2º turno ela foi gerada em 26/10 ao meio-dia, mas só apareceu no portal na manhã de 27/10, e o BU só entrou no portal às 16h de 27/10 (ver `RELATORIO.md`).

**Nota operacional.** A API CKAN do portal (`package_show`) é servida por um cache (`Cache-Control: max-age=3600`) que em 27/10 devolveu por horas uma versão de 24/10 do conjunto, enquanto a busca (`package_search`) e a página HTML já mostravam os arquivos novos. Todo acesso à API em `aguardar_2t.py` e `correspondencias.py` passou a usar parâmetro anticache e `Cache-Control: no-cache`; o vigia foi reiniciado com a correção.

## 2. Validação contra o BU do 1º turno (`26_corresp_validacao_1t.csv`)

| Teste | Resultado |
|---|---|
| Seções apuradas no BU 1t × seções na efetivada 1t | 499.206 de 499.206 têm correspondência |
| `NR_URNA_EFETIVADA` do BU = urna efetivada do arquivo | **100,0 %** (0 divergências) |
| Esperada da véspera ≠ efetivada | 0,61 % (3.032 seções) |
| Esperada do dia ≠ efetivada | 0,61 % (3.034 seções) |
| Origem do voto ≠ "Urna Eletrônica" | 80 seções: 50 "BU gerado por RED em urna de seção", 31 "Sistema de apuração" |

A fonte bate exatamente com o BU: a urna efetivada do arquivo de correspondência pode substituir `NR_URNA_EFETIVADA` do BU sem perda.

## 3. O 2º turno (`26_corresp_validacao_2t.csv`)

| | |
|---|---|
| Seções na efetivada 2t | 499.207 |
| Esperada da véspera ≠ efetivada | 0,60 % (3.019 seções) |
| Esperada do dia ≠ efetivada | 0,54 % (2.686 seções) |
| Origem do voto ≠ "Urna Eletrônica" | 45 seções: 29 "Sistema de apuração", 14 "RED em urna de seção", 2 "RED em urna de contingência" |

Mesma taxa de substituição por contingência que no 1º turno (0,6 %) e menos BUs fora da urna (45 contra 80).

## 4. Mesma urna física entre os turnos (`26_mesma_urna_1t_2t_provisorio_uf.csv`, `26_origem_urna_2t.csv`)

Urna efetivada nos dois turnos; "provisório" no nome do arquivo refere-se só à taxa manual da seção 5, que ainda vem dos logs e não do BU.

| | |
|---|---|
| Seções pareadas (BU 1t × efetivada 2t) | 499.206 |
| Só no 1º turno | 0 |
| Só no 2º turno | 1 (Buenos Aires, zona 1, seção 91; BU pelo sistema de apuração) |
| **Mesma urna física nos dois turnos** | **99,11 %** (494.771) |
| Urna que não votou em seção no 1º turno (contingência, reserva, nova) | 0,87 % (4.354) |
| Urna que estava em outra seção no 1º turno | 0,02 % (81) |
| UFs com menos repetição | SE 97,8 %, exterior 98,3 %, RR 98,4 %, AP 98,6 % |
| UFs com mais repetição | MG 99,4 %, TO 99,3 % |

Pela esperada, de manhã, a repetição parecia 99,71 %; a efetivada baixou para 99,11 % porque inclui as substituições do dia 25 e as do dia 4 (urnas de contingência do 1º turno que voltaram às suas seções de origem ou foram trocadas de novo).

## 5. Predição P4, verificada pelos logs (`27_p4_provisorio*.csv`)

P4, registrada em `docs/ESCOPO_2T.md` antes dos dados: *"Taxa manual persiste na mesma urna física: corr(1t, 2t) > 0,5 nas urnas mantidas e maior que nas trocadas"*. Taxa manual = `log_manual / log_votos` da varredura de logs dos dois turnos (seções com ≥ 50 votos nos dois); "mesma urna" é a da seção 4.

| Grupo | n | Pearson r | Spearman ρ | mediana tx 1t | mediana tx 2t |
|---|---|---|---|---|---|
| mesma urna | 492.847 | **0,830** | 0,794 | 6,1 % | 6,1 % |
| urna trocada | 4.406 | **0,490** | 0,799 | 7,0 % | 7,1 % |
| mesma urna, sem dias de falha total do leitor (tx > 0,5) | 492.735 | 0,830 | 0,793 | | |
| urna trocada, sem dias de falha total | 4.348 | 0,731 | 0,797 | | |

**Critério registrado: atendido** (0,83 > 0,5 e 0,83 > 0,49). Mas a leitura literal enganaria, por dois motivos.

1. A correlação de **postos** é igual nos dois grupos (0,79 e 0,80) em todas as UFs com n ≥ 100 (ρ entre 0,70 e 0,85 nas trocadas). A ordem das seções por taxa manual se mantém de um turno para o outro independentemente da máquina.
2. O grupo "trocada" é **selecionado pela falha**: 43 das 138 seções com falha total do leitor no 1º turno (31 %) tiveram a urna trocada para o 2º, contra 0,9 % das seções em geral. Dias de leitor ruim entram nesse grupo com taxa alta no 1º turno e normal no 2º, e é isso que derruba o Pearson (0,49; 0,73 sem os casos acima de 0,5). Não é que a máquina explique a taxa; é que as máquinas que falharam foram trocadas.

Conclusão: **a taxa de habilitação manual é uma propriedade do eleitorado da seção**, não do leitor e muito menos do dia ou da mesa. Uma seção que teve 12 % de manuais em 4 de outubro teve algo próximo disso em 25 de outubro, com a mesma urna ou com outra, com outros mesários sorteados ou os mesmos. O leitor pesa nos extremos (seção 6). O mecanismo escrito na tabela de predições ("leitor é a causa dominante") estava errado; a predição em si não.

Por modelo, só nas mesmas urnas: UE2013 r = 0,80 (n 10.365), UE2015 0,82 (86.311), UE2020 0,78 (198.686), UE2022 0,80 (197.485). Por UF, nas mesmas urnas, de RR 0,63 e AP 0,68 a CE e AL 0,86; nas trocadas com n ≥ 100, Pearson de ES 0,34 a SC 0,73, Spearman de 0,70 (SE) a 0,85 (SC).

Para a hipótese do estudo: um mecanismo de "votar por ausentes" via habilitação manual precisaria fazer a taxa de uma seção se afastar do seu padrão do 1º turno em lugares específicos. O teste direto disso é o `flag_delta` (Δmanual e Δcomparecimento conjuntamente anômalos no município, predição P5), que depende do comparecimento do BU do 2º turno.

## 6. Falha total do leitor (`28_falha_leitor_*.csv`)

Definição operacional: seção com ≥ 50 votos em que mais da metade dos eleitores foi habilitada manualmente (tx > 0,5). É o que se espera quando o sensor biométrico não lê.

| Modelo (1º turno) | seções | com falha total | por mil |
|---|---|---|---|
| UE2013 | 10.866 | 119 | **10,95 ‰** |
| UE2015 | 87.673 | 17 | 0,19 ‰ |
| UE2020 | 200.243 | 1 | 0,00 ‰ |
| UE2022 | 198.538 | 1 | 0,01 ‰ |

| 2º turno | falhas no 1t | repetiram no 2t | novas no 2t |
|---|---|---|---|
| mesma urna | 95 | **59 (62 %)** | 17 |
| urna trocada | 43 | **5 (12 %)** | 15 |

Quase dois terços das urnas que falharam no 1º turno e voltaram à mesma seção falharam de novo; das trocadas, uma em oito. É um sinal de hardware (sensor), concentrado no modelo mais antigo, e explica as taxas manuais extremas sem recorrer a conduta da mesa. A lista das 170 seções com falha total em algum dos turnos está em `28_falha_leitor_secoes.csv`; os maiores saltos são UE2013 com 0,94 a 0,98 num turno e 0,07 a 0,12 no outro (ES 56995 z26 s651, BA 38830 z162 s153, MA 8494 z93 s326).

## 7. Anomalia ≠ fraude: explicações inocentes e o que as descartaria

| Observação | Explicação inocente mais plausível | O que seria preciso para descartá-la |
|---|---|---|
| Taxa manual de uma seção se repete entre turnos (ρ ≈ 0,8) mesmo com urna trocada | É o eleitorado: eleitores sem biometria cadastrada e dedos que o sensor não lê (idosos, trabalho manual) votam na mesma seção nos dois turnos | Nada a descartar: é o comportamento esperado e o oposto do que a hipótese do estudo previa |
| Pearson mais baixo no grupo de urna trocada | Seleção: urnas são trocadas porque falharam; o grupo concentra dias de leitor ruim | Já tratado: sem os dias de falha total, 0,73; Spearman igual |
| 62 % das falhas totais repetem na mesma urna; 12 % nas trocadas | Defeito de hardware persistente em UE2013 | Caderno de ocorrências da seção (fora dos dados abertos) |
| 0,6 % das seções mudam de urna no dia | Substituição por contingência | É o procedimento padrão, registrado em `TP_DIVERGENCIA = C` |

## 8. O que falta e o que muda com o BU

1. BU do 2º turno: taxa manual oficial (`QT_ELEI_BIOM_SEM_HABILITACAO / QT_COMPARECIMENTO`), comparecimento e encerramento por seção; refaz P4 (`comparar_turnos.py bu`, item 22) com a mesma partição de urna desta nota e permite P1, P2, P3 e P5.
2. A partição mesma urna × trocada desta nota é definitiva; a taxa manual (logs) será substituída pela do BU nos relatórios finais.
