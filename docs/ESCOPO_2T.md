# Escopo: 2º turno (25/10/2026)

Escrito em 25/10/2026, antes da publicação dos dados. Fixa o que será testado, com que critérios e em que ordem, para que a análise comece no momento em que o TSE publicar e não seja desenhada depois de ver os resultados. As predições da seção 4 ficam registradas aqui e são verificadas mecanicamente por `comparar_turnos.py`.

## 1. O que já se sabe e o que o 2º turno acrescenta

O 1º turno (relatórios em `out/*/RELATORIO.md`) concluiu que a habilitação manual não se concentra no fim da sessão em nenhuma escala, que o encerramento tardio do NE e N é tempo por eleitor, e que o único achado localizado é a razão de duração do voto manual/biométrico em Bom Lugar e Maranhãozinho (MA).

O 2º turno é uma **segunda medição dos mesmos 509 mil pontos, em outro dia, com cédula mais curta** (Presidente em todo o país; Governador só nas UFs com 2º turno estadual). Isso permite três coisas que o 1º turno sozinho não permitia:

1. **Teste de predições**: o modelo "encerramento tardio = tempo por eleitor × tamanho da seção" prevê que o atraso encolhe com uma cédula de 1 a 2 cargos. Se o NE continuar fechando tão tarde quanto no 1º turno com cédula curta, a explicação do 1º turno fica enfraquecida.
2. **Persistência**: taxa de habilitação manual é propriedade do leitor biométrico e do eleitorado da seção. Deve se repetir na mesma urna física (`NR_URNA_EFETIVADA`) e no mesmo eleitorado. O que *muda* entre turnos, além do que o modelo e o eleitorado explicam, é o que merece atenção.
3. **Repetição do achado de Bom Lugar**: se a razão de duração < 0,8 se repetir nos mesmos locais de votação com outros mesários sorteados ou os mesmos, é prática local estável (operacional ou populacional). Se desaparecer, foi do dia. Qualquer dos dois resultados é informativo e nenhum é prova de fraude.

## 2. Dados

| Item | 1º turno | 2º turno |
|---|---|---|
| Data | 04/10/2026 | 25/10/2026 |
| Pleito (portal de resultados) | 3220 | **3221** (confirmado em `comum/config/ele-c.json`) |
| Eleições | 6257 Federal, 6259 Estadual | **6258** Federal, **6260** Estadual; o pleito 3221 também carrega 3 suplementares municipais em SP (Narandiba, Macedônia, Martinópolis), que são ignoradas |
| BU | `bweb_1t_<UF>_051020261403.zip` | `bweb_2t_<UF>_<DDMMAAAAHHMM>.zip`; carimbo desconhecido até a publicação. Em 2022 saiu em 31/10 15:35 (D+1); em 2024 em 28/10 10:46 (D+1) |
| Logs | `arquivo-urna/3220/dados/...` | `arquivo-urna/3221/dados/...`, `o03221<uf><mun><zona><sec>-log.jez`; aparecem progressivamente na noite da eleição |
| Cargos no BU | Presidente, Governador, Senador, Dep. Federal, Dep. Estadual/Distrital | Presidente (todas as UFs); Governador (UFs com 2º turno) |

Mesmas regras do 1º turno: SHA-512 conferido em todo download (falhou → para); `data/` nunca alterado depois de baixado; horários no relógio local da urna (AC 15h, AM/MT/MS/RO/RR 16h, demais 17h); sem Lei de Benford; anomalia ≠ fraude, com explicação inocente e o que a descartaria para cada achado.

**Estado do ambiente em 25/10:** os dados brutos do 1º turno foram apagados do disco. O BU do 1º turno está sendo baixado de novo (4,7 GB, ~1 h) porque a comparação seção a seção precisa dele. Os logs do 1º turno (51 GB, 15,5 h) **não** serão rebaixados: as métricas por urna e por local estão versionadas em `out/logs_brasil/secoes_logs_brasil.parquet` e `06_locais_razao_duracao.parquet`, e urnas específicas podem ser rebaixadas uma a uma com `logs_urna.py baixar`.

## 3. Fases

### Fase 0, agora (concluída com este documento)
- `config.py`: toda a pipeline parametrizada por `TURNO` (1 ou 2). Com `TURNO=2`, tudo vai para `data/2t/` e `out/2t/`; o 1º turno continua reproduzível sem mudança.
- `aguardar_2t.py`: vigia a publicação (API CKAN dos Dados Abertos, página HTML como reserva, sondas de `aux.json` no pleito 3221, disco livre). Com `--auto`, ao detectar as 28 UFs: grava o carimbo, baixa, confere hashes, carrega, roda as análises de BU e a comparação. **Nunca** inicia a varredura nacional de logs.
- `comparar_turnos.py`: comparação 1º × 2º turno (BU e logs) com as predições da seção 4.
- `logs_urna.py selecionar_2t`: amostra dirigida de logs do 2º turno (seção 3, Fase 2).
- Recarga do BU do 1º turno em `data/bu2026.duckdb`.

### Fase 1, BU (D+1, ~2 h depois da publicação)
```bash
python aguardar_2t.py --auto            # ou, manualmente, quando o carimbo for conhecido:
TURNO=2 python pipeline_bu.py download --uf ALL --stamp DDMMAAAAHHMM
TURNO=2 python pipeline_bu.py load     --uf ALL
TURNO=2 python pipeline_bu.py analyze  --foco CE BA --out out/2t/piloto
TURNO=2 python analise_brasil.py       --out out/2t/brasil
python comparar_turnos.py bu           --out out/2t/comparacao
```
Entregas: `out/2t/brasil/` (os mesmos 11 a 16 do 1º turno, agora para o 2º), `out/2t/comparacao/` (20 a 25, seção 5), `out/2t/RELATORIO_BU.md`. Teste 1 (consistência) tem de dar zero; se não der, parar.

**PARE AQUI**: a lista de seções para a amostra de logs e a decisão de rodar a varredura nacional (15 h, 51 GB) são do usuário.

### Fase 2, logs por amostra (D+1 ou D+2, ~1 h)
```bash
TURNO=2 python logs_urna.py selecionar_2t --out out/2t/logs
TURNO=2 python logs_urna.py baixar  --out out/2t/logs
TURNO=2 python logs_urna.py parsear --out out/2t/logs
TURNO=2 python logs_urna.py analisar --out out/2t/logs
```
Grupos: G = todas as `flag_cal` do 2º turno; H = até 100 seções com Δmanual e Δcomparecimento (2t − 1t) conjuntamente anômalos no município; I = **todas** as 76 seções de Bom Lugar e Maranhãozinho; J = 2 controles do mesmo município por seção de G e H; K = 150 controles nacionais. Métricas e limiares (p95/p5 dos controles) iguais aos do 1º turno.

### Fase 3, varredura nacional de logs (após confirmação; 15 h, ~51 GB)
```bash
TURNO=2 python logs_brasil.py scan --uf ALL --workers 32
TURNO=2 python analise_logs_brasil.py --out out/2t/logs_brasil
python comparar_turnos.py logs --out out/2t/comparacao
```
Entregas: `out/2t/logs_brasil/` (01 a 07 e o Parquet de 48 métricas), `out/2t/comparacao/30_*` a `33_*`, `out/2t/RELATORIO.md` final.

## 4. Predições registradas (verificadas por `comparar_turnos.py`)

Derivadas dos mecanismos identificados no 1º turno. Uma predição que falhe obriga a rever a explicação correspondente, não a hipótese original.

| Id | Predição | Mecanismo do 1º turno | O que uma falha significaria |
|---|---|---|---|
| P1 | Encerramento tardio (> 30 min) cai em **todas** as regiões | tempo por eleitor × tamanho da seção; cédula 3× menor | atraso não é tempo de cédula |
| P2 | NE e N continuam fechando depois do Sul, mas a diferença absoluta (mediana) encolhe | diferença de 15 a 25% no tempo por eleitor se aplica a um voto mais curto | diferença regional tem outra causa |
| P3 | Taxa manual nacional estável (± 1,5 pp) | falha do leitor e eleitorado, não o dia | |
| P4 | Taxa manual persiste na mesma urna física: corr(1t, 2t) > 0,5 nas urnas mantidas e maior que nas trocadas | leitor é a causa dominante | leitor não explica a taxa |
| P5 | Seções com Δmanual e Δcomparecimento conjuntamente anômalos: ≤ 0,2‰, sem região acima de 2× a média | sem mecanismo de "votar por ausentes" | o 2º turno teria o padrão que o 1º não teve |
| L1 | Duração mediana do voto cai em todas as UFs | cédula | |
| L2 | Ordem das UFs por tempo de voto se mantém (ρ de Spearman > 0,7), MA/PI/PA no topo | característica do eleitorado | |
| L3 | Taxa manual por modelo se repete (UE2013 > UE2015 > UE2020 ≈ UE2022), diferença < 2 pp | hardware | |
| L4 | Mediana por UF da razão manual/votos na última hora ≤ 1 | sem concentração no fim | o 2º turno teria concentração |
| L5 | Bom Lugar, locais 1104, 1120, 1198, 1171: razão < 0,8 de novo (prática estável) **ou** > 1 (foi do dia). Registrado sem direção | | ambos os resultados são informativos |

## 5. Saídas novas (`out/2t/comparacao/`)

| Arquivo | Conteúdo |
|---|---|
| `20_pareamento.csv`, `20_uf.csv`, `20_regioes.csv`, `20a_uf_1t_vs_2t.png` | seções pareadas (UF, município, zona, seção), % com a mesma urna física; manual, comparecimento, encerramento nos dois turnos |
| `21_secoes.parquet` | todas as seções pareadas com os campos dos dois turnos e os deltas |
| `22_persistencia_uf.csv`, `22_persistencia_serie.csv` | corr(1t, 2t) da taxa manual: mesma urna × urna trocada, série antiga × nova |
| `23_flag_delta.csv`, `23_flag_delta_uf.csv`, `23a_scatter_delta.png` | seções com Δmanual > 3σ e Δcomparecimento > 2σ dentro do município (`aptos ≥ 100` nos dois turnos, `n_mun ≥ 8`) |
| `24_predicoes.csv` | P1 a P5 com valor observado e ok/não |
| `25_votos_delta_uf.csv` | corr(Δmanual, Δfatia do candidato) por UF, bruta e intra-município |
| `30_modelo.csv`, `30_uf_tempo.csv` | logs: manual por modelo e tempo por voto nos dois turnos |
| `31_locais_flagrados_1t_no_2t.csv`, `31_bom_lugar_maranhaozinho.csv` | razão de duração por local: os flagrados do 1º turno repetem? Bom Lugar e Maranhãozinho local a local |
| `32_persistencia_urna.csv`, `33_predicoes_logs.csv` | corr por urna das métricas de log; L1 a L5 |

## 6. O que fica explicitamente fora
- Governador: a hipótese é sobre habilitação, que é por seção e independe do cargo; o cargo entra só em correlações, e a correlação com voto em presidente já cobre isso. Governador pode ser adicionado em `comparar_turnos.py` se o usuário pedir.
- Comparação com 2022: outra pipeline (layout diferente), fora deste escopo.
- Qualquer inferência sobre eleitores individuais: o log não identifica o eleitor.

## 7. Decisões que ficam para o usuário
1. Rodar `aguardar_2t.py --auto` (baixa e analisa o BU sozinho ao detectar) ou disparar manualmente.
2. Após a Fase 1: confirmar a amostra de logs e autorizar a varredura nacional (15 h, 51 GB).
3. Se L5 repetir Bom Lugar: o relatório recomendará de novo a conferência do caderno de votação; o estudo não tem como ir além disso.
