# Eleições 2026 (1º turno): habilitação manual de eleitores nos Boletins de Urna e nos logs de urna

Análise reprodutível de **todos os 499.206 Boletins de Urna (BU)** e de **todos os 499.176 logs de urna disponíveis** do 1º turno de 4 de outubro de 2026, publicados pelo TSE, para testar uma hipótese que circulou após a eleição:

> "A liberação manual de eleitores sem biometria (assinatura do mesário) se concentra no fim da sessão e é usada para votar no lugar de ausentes, sobretudo no Nordeste."

**Resultado:** a hipótese não se sustenta em nenhum nível de análise (BU por UF, seções flagradas com controles, logs de uma amostra dirigida de 1.300 urnas do Nordeste, varredura dos logs de todas as urnas). O encerramento tardio no Nordeste e Norte é explicado, com os próprios logs, por 15 a 25% mais tempo por eleitor e seções maiores. A varredura devolve **um achado localizado** em dois municípios pequenos do Maranhão (Bom Lugar e Maranhãozinho), por um critério diferente do da hipótese, que só a conferência do caderno de votação pode esclarecer. Anomalia não é fraude: cada achado vem com a explicação inocente mais plausível e com o que seria preciso para descartá-la.

*English summary: a reproducible audit of every 2026 Brazilian first-round polling-station report (BU) and every available voting-machine log, testing the claim that manual voter enabling (fingerprint bypass) clusters at the end of the day to cast votes for absentees, with a Northeast framing. The claim fails at every level. Late closing in the Northeast/North is fully explained by longer per-voter time. One localized anomaly in two small municipalities of Maranhão (manually enabled voters vote twice as fast as biometric ones) is documented for human verification.*

---

## Sumário

- [Principais resultados](#principais-resultados)
- [Como o estudo foi feito](#como-o-estudo-foi-feito)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Reprodução](#reprodução)
- [Dados](#dados)
- [Limitações e regras do estudo](#limitações-e-regras-do-estudo)
- [Como contribuir](#como-contribuir)
- [Licença e citação](#licença-e-citação)

## Principais resultados

Os relatórios completos, com tabelas, gráficos e a lista de seções, estão em `out/*/RELATORIO.md`. Em resumo:

| Pergunta | Resposta | Onde |
|---|---|---|
| A taxa de habilitação manual é maior no Nordeste? | Não. Sul 8,1% > Nordeste 7,1%. O que determina a taxa é o **modelo da urna** (UE2013 11,2%, UE2015 9,7%, UE2020/2022 6,1%), presente em todas as UFs. | `out/brasil`, `out/logs_brasil` |
| Há seções com manual anormalmente alto *e* comparecimento anormalmente alto, dentro do seu município? | 27 em 499 mil no critério calibrado (z dentro do município × tamanho da seção). Nordeste 12, Sudeste 9. Compatível com o acaso. | `out/brasil/secoes_flagradas_brasil.csv` |
| As habilitações manuais se concentram no fim da sessão? | **Não, em nenhuma escala.** Nas 1.000 urnas mais suspeitas do NE fechadas no horário, a fração de manuais na última hora (7,2%) é *menor* que a fração de votos (8,6%), igual aos controles. Nas 497.895 urnas do país, as 10 urnas acima do p99,9 têm 5 a 9 manuais cada, em 9 UFs. | `out/logs_ne`, `out/logs_brasil` |
| Há votos após o horário? | Só continuação de fila. O NE e N fecham tarde (36% e 26% das seções > 30 min, contra 3% no Sul) porque o voto demora mais: MA e PI 63 s por eleitor contra 50 a 52 s em DF, SC, SP, RS. Acumulado em 250 eleitores, isso é 1 a 1,5 h. | `out/logs_brasil/03_tempo_voto_uf.csv` |
| Sobrou algo? | Sim, de outra natureza. Em 95% das urnas o eleitor habilitado manualmente demora **mais** para votar que o biométrico (razão mediana 1,26). Em **Bom Lugar/MA** a razão é 0,785, a menor dos 5.520 municípios com ≥ 100 manuais; 17 das 39 urnas elegíveis são flagradas (esperado por acaso 0,04), em 6 dos 14 locais de votação. **Maranhãozinho/MA** é o segundo (0,967; 7 urnas, esperado 0,03). A urna zona 101 seção 138 de Maranhãozinho tem sequências de 6 e 8 eleitores manuais consecutivos votando em 23 a 47 s com o leitor funcionando para os demais. O voto em presidente nesses municípios não desvia do interior do MA. | `out/logs_brasil/06_*`, `out/logs_bomlugar` |

## Como o estudo foi feito

O estudo avançou em fases, cada uma com relatório próprio. A ordem importa: cada fase foi desenhada com os resultados da anterior.

1. **Piloto (BU, 4 UFs)** — CE e BA (foco) contra RS e PR (controle). Testes de consistência, distribuição da taxa manual, z-scores dentro do município, horário de encerramento, correlação com voto. `out/piloto/`.
2. **Brasil (BU, 27 UFs + exterior)** — rankings por UF e região, estratificação por tamanho de seção, modelo de urna (proxy pelo número de série, depois confirmado nos logs) e porte do município, padronização direta para testar regionalidade. `out/brasil/`.
3. **Logs, amostra dirigida (358 urnas)** — seções flagradas no BU e controles do mesmo município e nacionais. Primeira leitura do log eleitor a eleitor. `out/logs/`.
4. **Logs, Nordeste (1.300 urnas)** — as 1.000 urnas do NE com maior z de manual, comparecimento acima da média e fechadas no horário (o cenário em que "votar por ausentes" deixaria rastro), mais 300 controles. Surgiu o achado de Bom Lugar. `out/logs_ne/`, `out/logs_bomlugar/`.
5. **Logs, varredura nacional (499.176 urnas)** — o critério de Bom Lugar (razão de duração do voto manual/biométrico) e os demais aplicados a todas as urnas, com quantis nacionais e agregação por local de votação e município. `out/logs_brasil/`.

A metodologia detalhada, incluindo o mapeamento do layout do BU 2026, as mensagens do log usadas e cada critério com seus limiares, está em [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).

## Estrutura do repositório

```
.
├── pipeline_bu.py          # download (com SHA-512), carga em DuckDB e testes básicos do BU
├── piloto_extras.py        # gráficos, detalhe das seções flagradas e estratificações do piloto
├── analise_brasil.py       # análise nacional do BU: rankings, estratos, regionalidade, flags
├── logs_urna.py            # logs de urna por amostra: selecionar, baixar, parsear, analisar
├── logs_brasil.py          # varredura nacional dos logs (paralela, retomável) -> Parquet
├── analise_logs_brasil.py  # análise da varredura: quantis, flags, locais e municípios
├── reproduzir.sh           # encadeia tudo, na ordem (ver docs/REPRODUCAO.md antes)
├── config.py               # TURNO=1|2: pleito, carimbo, dia, caminhos (data/, out/ ou data/2t/, out/2t/)
├── aguardar_2t.py          # vigia a publicação do 2º turno; --auto baixa, carrega e analisa o BU
├── comparar_turnos.py      # 1º × 2º turno por seção e por urna, com as predições registradas
├── correspondencias.py     # correspondências esperadas/efetivadas do TSE: urna física por seção; mesma urna 1t→2t e P4 provisório
├── requirements.txt
├── docs/
│   ├── METODOLOGIA.md      # layout, testes, critérios, limiares, mensagens do log
│   ├── REPRODUCAO.md       # passo a passo, tempos, disco, o que pode falhar
│   ├── DADOS.md            # fontes, URLs, formatos, dicionário dos arquivos de saída
│   └── ESCOPO_2T.md        # escopo do 2º turno, escrito antes dos dados: fases, predições, saídas
├── out/                    # resultados (versionados; arquivos > 20 MB ficam fora, ver DADOS.md)
│   ├── piloto/             # fase 1  + RELATORIO.md
│   ├── brasil/             # fase 2  + RELATORIO.md
│   ├── logs/               # fase 3  + RELATORIO.md
│   ├── logs_ne/            # fase 4  + RELATORIO.md
│   ├── logs_bomlugar/      # 3 urnas do local 1104 de Bom Lugar/MA
│   └── logs_brasil/        # fase 5  + RELATORIO.md
└── data/                   # NÃO versionado (~100 GB); criado pelos scripts
    ├── raw/                # 28 ZIPs do TSE (4,7 GB), nunca alterados
    ├── csv/                # CSVs extraídos (36 GB)
    ├── bu2026.duckdb       # banco com os 67,9 milhões de linhas do BU (4,2 GB)
    ├── logs/raw/           # 499 mil log.jez (51 GB)
    ├── logs/txt/           # logs extraídos das amostras (fases 3 e 4)
    └── logs_parquet/       # métricas por urna e 118 milhões de habilitações (950 MB)
```

## Reprodução

Requisitos: Python 3.12, cerca de 100 GB de disco livre, conexão estável. Testado no Windows 11 (PowerShell e Git Bash); os scripts não têm nada específico de sistema.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Fase 1: piloto (4 UFs, ~15 min)
python pipeline_bu.py download --uf CE BA RS PR
python pipeline_bu.py load     --uf CE BA RS PR
python pipeline_bu.py analyze  --foco CE BA --out out/piloto
python piloto_extras.py        --uf CE BA RS PR --foco CE BA --out out/piloto

# Fase 2: Brasil (28 arquivos, ~1 h de download + carga)
python pipeline_bu.py download --uf AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ
python pipeline_bu.py load     --uf AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ
python analise_brasil.py       --out out/brasil

# Fases 3 e 4: logs por amostra (~10 min cada)
python logs_urna.py selecionar    --out out/logs    && python logs_urna.py baixar --out out/logs \
  && python logs_urna.py parsear  --out out/logs    && python logs_urna.py analisar --out out/logs
python logs_urna.py selecionar_ne --out out/logs_ne && python logs_urna.py baixar --out out/logs_ne \
  && python logs_urna.py parsear  --out out/logs_ne && python logs_urna.py analisar --out out/logs_ne

# Fase 5: varredura nacional (15,5 h com 32 conexões; retomável)
python logs_brasil.py scan --uf ALL --workers 32
python analise_logs_brasil.py --out out/logs_brasil
```

`reproduzir.sh` executa exatamente essa sequência. Detalhes, tempos por etapa, uso de disco e os erros já conhecidos (e como foram tratados) estão em [`docs/REPRODUCAO.md`](docs/REPRODUCAO.md). Quem quiser apenas reanalisar sem baixar nada pode partir de `out/logs_brasil/secoes_logs_brasil.parquet` (497.895 urnas × 48 métricas) e de `out/brasil/secoes_flagradas_brasil.csv`.

## 2º turno (25/10/2026)

O escopo do 2º turno foi fixado **antes** da publicação dos dados, em [`docs/ESCOPO_2T.md`](docs/ESCOPO_2T.md): mesma pipeline com `TURNO=2` (pleito 3221), comparação seção a seção e urna a urna com o 1º turno, e dez predições registradas (encerramento tardio encolhe com a cédula curta, taxa manual persiste na mesma urna física, Bom Lugar repete ou não) verificadas mecanicamente por `comparar_turnos.py`. Para acompanhar a publicação:

```bash
python aguardar_2t.py --once
```

Resultados já publicados do 2º turno (logs, antes do BU): [`out/2t/logs_rep/RELATORIO.md`](out/2t/logs_rep/RELATORIO.md) (as mesmas 1.725 urnas do 1º turno) e [`out/2t/logs_brasil/RELATORIO.md`](out/2t/logs_brasil/RELATORIO.md) (varredura nacional, 499.177 urnas). Em resumo: a hipótese não se sustenta de novo, o encerramento tardio do Nordeste desapareceu com a cédula de um cargo, e Bom Lugar não repetiu.

Enquanto o BU do 2º turno não sai, as correspondências esperadas e efetivadas do TSE (publicadas entre 24 e 27/10) dizem qual urna física votou em cada seção, o que permitiu verificar a predição P4 (persistência da taxa manual na mesma urna) com a taxa manual dos logs: [`out/2t/comparacao/RELATORIO_CORRESP.md`](out/2t/comparacao/RELATORIO_CORRESP.md). 99,1% das seções votaram na mesma urna nos dois turnos; a taxa manual de uma seção no 1º turno prevê a do 2º com ρ ≈ 0,8 tanto na mesma urna quanto em urna trocada, ou seja, ela é uma propriedade do eleitorado da seção, não do dia nem da mesa. O leitor pesa só nos extremos: a falha total do sensor (UE2013, 11‰) repete em 62% das urnas mantidas e em 12% das trocadas.

## Dados

Todos os dados são públicos e vêm do TSE:

- **Boletins de Urna (BU web):** <https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna>. Um ZIP por UF, com SHA-512 publicado ao lado. O hash é verificado em todo download; se falhar, o script para.
- **Logs de urna (`log.jez`):** portal de resultados, `https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/<uf>/<município>/<zona>/<seção>/`. Um arquivo por seção, localizado pelo `aux.json` da seção.

Os brutos não são redistribuídos aqui (100 GB) e **nunca são alterados** pelos scripts. O dicionário das colunas usadas e de todos os arquivos de saída está em [`docs/DADOS.md`](docs/DADOS.md).

## Limitações e regras do estudo

- **Anomalia ≠ fraude.** Nenhum achado deste repositório prova irregularidade. O log não identifica o eleitor. Para cada achado, o relatório traz a explicação inocente mais plausível e o que seria necessário para descartá-la (caderno de votação, arquivo de digitais `wsqman.jez`, comparação com 2022).
- **Sem Lei de Benford** em votos por seção: o teste é inadequado para esse dado e foi excluído por decisão de desenho.
- **Horários são do relógio local da urna.** AC fecha às 15h locais; AM, MT, MS, RO e RR às 16h; demais às 17h. Todas as métricas de "minutos após o encerramento previsto" levam isso em conta.
- **`DS_TIPO_URNA` no BU 2026 não é o modelo da urna**, é o status da apuração. O modelo vem do log (`Identificação do Modelo de Urna`); no BU usamos o número de série apenas como proxy.
- **Seções agregadas** (`DS_SECOES_AGREGADAS`) não têm BU próprio e aparecem dentro da seção principal.
- **Cobertura dos logs:** 499.176 de 499.206 urnas apuradas. Faltam 28 no exterior e 2 em MG sem arquivo de log no portal; 22 falhas de conexão no RS foram recuperadas. O comparecimento do log bate com o BU em 99,997% das urnas.
- **Os limiares são escolhas.** z > 3 dentro do município, aptos ≥ 100, quantis nacionais p0,1 / p99,9: todos estão documentados e são parâmetros nos scripts. Mudá-los muda a lista de seções flagradas, não as conclusões.

## Como contribuir

Correções, novos testes e replicações independentes são bem-vindos. Abra uma issue descrevendo a hipótese que quer testar e o que seria um resultado positivo e um negativo antes de escrever código. Pull requests devem:

- manter `data/raw` intocado e escrever só em `out/`;
- incluir, para qualquer novo "achado", a explicação inocente mais plausível e o que a descartaria;
- não introduzir testes que o próprio relatório já descarta como inadequados (Benford em seção).

Quem tiver acesso ao caderno de votação ou aos arquivos `wsqman.jez` das seções listadas em `out/logs_brasil/06_locais_flagrados_manual_rapido.csv` pode fechar a única questão em aberto do estudo.

## Licença e citação

Código sob licença MIT (ver `LICENSE`). Os dados são do TSE e seguem os termos de uso dos Dados Abertos do TSE. Relatórios e figuras em `out/` podem ser reproduzidos com atribuição a este repositório.

```
Agnoletto, A. (2026). Eleições 2026, 1º turno: habilitação manual nos Boletins de Urna e logs de urna.
Repositório GitHub. Dados: TSE, Boletim de Urna Web (arquivos 051020261403) e logs de urna.
```
