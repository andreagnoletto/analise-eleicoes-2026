# Metodologia

Este documento descreve, com os limiares exatos usados nos scripts, cada etapa do estudo. A ordem é a ordem em que o trabalho foi feito, porque cada fase foi desenhada com os resultados da anterior.

## 1. Hipótese e o que seria evidência

Hipótese testada: *a habilitação manual de eleitores (sem reconhecimento biométrico, liberada por assinatura do mesário ou presidente de seção) se concentra no fim da sessão e é usada para registrar votos no lugar de eleitores ausentes, com maior incidência no Nordeste.*

Se fosse verdade, deveria aparecer, em ordem crescente de especificidade:

1. no BU, seções com taxa de habilitação manual **e** comparecimento simultaneamente anômalos em relação ao seu próprio município;
2. no BU, concentração regional dessas seções além do que tamanho da seção, modelo de urna e porte do município explicam;
3. nos logs, habilitações manuais concentradas na última hora da votação, em proporção maior que a dos votos em geral;
4. nos logs, votos em ritmo acelerado no fim da sessão (sem fila, intervalo curto entre votos), especialmente em urnas que fecharam no horário.

Evidência negativa em (3) e (4) refuta a hipótese mesmo que (1) e (2) existissem, porque (3) e (4) são o mecanismo.

## 2. Fonte e layout do Boletim de Urna 2026

Arquivos `bweb_1t_<UF>_051020261403.zip` do dataset *Resultados 2026 – Boletim de Urna* (Dados Abertos do TSE), um por UF mais `ZZ` (exterior), com SHA-512 publicado ao lado. CSV separado por `;`, Latin-1, uma linha por (seção, cargo, votável). O layout está no `_leiame-boletimurnaweb.pdf` dentro de cada ZIP; nenhuma coluna foi mapeada por suposição.

Colunas usadas e observações que importam:

| Coluna | Uso | Observação |
|---|---|---|
| `QT_APTOS`, `QT_COMPARECIMENTO`, `QT_ABSTENCOES` | base da seção | |
| `QT_ELEI_BIOM_SEM_HABILITACAO` | **habilitações manuais** (eleitores com biometria cadastrada que não foram habilitados por ela) | é a coluna do layout 2026 para o que o pedido original chamava `QT_ELEITORES_BIOMETRIA_NH` |
| `DT_ABERTURA`, `DT_ENCERRAMENTO` | horário de abertura/encerramento, `YYYY-MM-DD HH:MM:SS` | **relógio local da urna**. AC abre 06:00 e fecha 15:00; AM, MT, MS, RO e RR fecham 16:00; demais 17:00; ZZ 17:00 local |
| `CD_TIPO_URNA`, `DS_TIPO_URNA` | status de apuração | **não é o modelo da urna**; só "Apurada" no 1º turno |
| `NR_URNA_EFETIVADA` | número de série | usado como *proxy* de modelo no BU (série < 2,0 milhões ≈ modelos antigos); o modelo real vem do log |
| `DS_SECOES_AGREGADAS` | seções agregadas | não têm BU próprio; aparecem na seção principal |
| `CD_MUNICIPIO`, `NM_MUNICIPIO`, `NR_ZONA`, `NR_SECAO`, `NR_LOCAL_VOTACAO`, `SG_UF` | chaves | `CD_MUNICIPIO` vem **sem zero à esquerda** (`7285`, não `07285`) |
| `DS_CARGO_PERGUNTA`, `NR_VOTAVEL`, `NM_VOTAVEL`, `QT_VOTOS`, `CD_TIPO_VOTAVEL` | votos | correlações e detalhe das seções flagradas (Presidente) |

Carga: DuckDB, `read_csv` com `all_varchar`, uma tabela `bu` com 67,9 milhões de linhas. A partir dela, `pipeline_bu.build_tables()` cria:

- `secao`: uma linha por seção (distinct das linhas de Presidente), com `aptos`, `comp`, `abst`, `bio_nh`, hora de encerramento e `min_apos_fech` = minutos entre o encerramento previsto local e o observado;
- `m`: taxas `tx_comp = comp/aptos`, `tx_manual = bio_nh/comp`, região, flag de apurada;
- `z`: z-scores de `tx_manual` e `tx_comp` **dentro do município** (`PARTITION BY SG_UF, CD_MUNICIPIO`), com `n_mun` = seções do município.

## 3. Testes no BU (fases 1 e 2)

| # | Teste | Definição | Resultado nacional |
|---|---|---|---|
| 1 | Consistência | `aptos = comp + abst`, `bio_nh ≤ comp`, `bio_nh ≥ 0`, seção apurada, hora de encerramento presente | zero inconsistências aritméticas; 30 seções sem hora (28 ZZ, 2 MG) |
| 2 | Distribuição da taxa manual | média, mediana, p95 por UF e região | S 8,1% > NE 7,1%; determinado pelo modelo da urna |
| 3 | Seções suspeitas | `FLAG_ORIG`: `n_mun ≥ 8 AND z_manual > 3 AND z_comp > 2` (critério do pedido original). `FLAG_CAL`: o mesmo, com z calculado dentro de município **× quartil nacional de aptos** e `aptos ≥ 100` (calibrado no piloto, onde 28 das 30 flagradas originais eram seções minúsculas). `FLAG_TARD`: `n_mun ≥ 8 AND z_manual > 3 AND min_apos_fech > 60 AND aptos ≥ 100` | orig: concentradas em seções pequenas; cal: 27 no país (NE 12, SE 9); tard: dominado por falha de leitor em UE2013 nas capitais de todas as regiões |
| 4 | Suspeitas por mil seções por UF | | sem padrão regional |
| 5 | Encerramento | mediana, p95, % > 30/60/120 min após o horário local | NE 36%, N 26%, S 3% com > 30 min; persiste sob controles |
| 6 | Correlação manual × voto | por UF e intra-município (demeaned) | positiva com Lula no NE, encolhe intra-município, inverte no RS: efeito composicional |

Estratificações (fase 2): quartil nacional de `aptos`; proxy de modelo pela série; porte do município (capital / > 100 mil eleitores / ≤ 100 mil). Regionalidade: **padronização direta** da taxa manual e das flags por célula (quartil × série × porte), comparando NE com as demais regiões célula a célula (`13_*`). Se o NE não se destacar após isso, o relatório diz isso.

**Excluído por desenho:** Lei de Benford em votos por seção.

## 4. Logs de urna

### 4.1 Localização e formato

Para cada seção, `https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/<uf>/<mun5>/<zona4>/<sec4>/p003220-<uf>-m<mun>-z<zona>-s<sec>-aux.json` lista os arquivos e seus hashes. O log é o arquivo com `tp = "log"` (`o03220<uf><mun><zona><sec>-log.jez`), em `<pasta>/<hash>/<arquivo>`.

`log.jez` é um ZIP comum (não 7z) com `logd.dat`: Latin-1, campos separados por TAB: data-hora, nível, id da urna, aplicativo, mensagem, hash. Em urnas de contingência o ZIP contém outro `.jez` com o log da urna original; `extrair_logs()` extrai recursivamente e concatena. Sem isso o número de votos do log fica abaixo do BU.

### 4.2 Mensagens usadas no parser (`logs_urna.parse_log`)

| Mensagem | Significado | Uso |
|---|---|---|
| `Identificação do Modelo de Urna: UE2013/2015/2020/2022` | modelo | estratificação |
| `Tipo de habilitação do eleitor [biométrica]` | digital reconhecida | tipo = biométrica |
| `Solicitação de dado pessoal do eleitor para habilitação manual` | após 4 tentativas de digital sem reconhecimento; exige digital do mesário | tipo = manual |
| `Ano de nascimento digitado…` (sem mensagem de tipo antes) | eleitor sem biometria cadastrada | tipo = sem_biometria |
| `Eleitor foi habilitado` | fim da habilitação | `t_hab` |
| `O voto do eleitor foi computado` | voto concluído | `t_voto`; duração = `t_voto − t_hab` |
| `Capturada a digital. Tentativa k de k` | tentativas | `tentativas` |
| `Operador selecionou: Encerrar votação` | encerramento | `t_encerrar` |
| `Dado digitado não confere` | mesário errou o dado pessoal na habilitação manual | taxa por 100 manuais |

Validação: comparecimento do log = `QT_COMPARECIMENTO` em 99,997% das 499.176 urnas; manuais = `QT_ELEI_BIOM_SEM_HABILITACAO` em 98,4% e a ±1 em 99,9% (a diferença de 1 é habilitação manual sem voto concluído).

### 4.3 Amostras (fases 3 e 4)

- **Fase 3** (`logs_urna.py selecionar`): A = todas as `FLAG_CAL` (27); B = 25 maiores z entre `FLAG_TARD` não-cal; C = 3 controles aleatórios do mesmo município por flagrada; D = 150 controles nacionais aleatórios com `aptos ≥ 100`. Total 358.
- **Fase 4** (`selecionar_ne`): universo NE, `aptos ≥ 100`, `n_mun ≥ 8`, `min_apos_fech` entre −30 e +30 (fechou no horário). E = 1.000 maiores `z_manual` com `z_comp > 0`; F = 300 aleatórias fora de E. Esse é o cenário em que "votar por ausentes" deixaria rastro: urna sem fila, manual alto, comparecimento alto.

Limiares de anomalia nas amostras: p95 (ou p5) do grupo de controle para cada métrica (`07_limites_anomalias.csv`).

### 4.4 Métricas por urna (`logs_brasil.metricas`, 48 colunas)

Identificação e BU: `k`, `modelo`, `bu_aptos`, `bu_comp`, `bu_bio_nh`, `bu_min_apos_fech`.
Contagens do log: `log_habilitados`, `log_votos`, `log_bio`, `log_manual`, `log_sem_biometria`, `log_outro`.
Tempo: `t_encerrar`, `primeiro_voto`, `ultimo_voto`, `min_enc_apos_fech_prev`, `min_ultimo_voto_antes_enc`.
Fim da sessão: `frac_votos_ult60`, `frac_manual_ult60`, `votos_ult60`, `manual_ult60`, `n_votos_apos_fech_prev`, `n_manual_apos_fech_prev`.
Duração do voto (habilitado → computado): `dur_mediana_s`, `dur_manual_med_s`, `dur_manual_p25_s`, `dur_bio_med_s`, `dur_bio_p25_s`, `razao_dur_manual_bio`, `pct_manual_lt30`, `pct_bio_lt30`.
Ritmo: `gap_mediano_s`, `gap_mediano_ult60_s`, `max_run_manual` (maior sequência de manuais consecutivos), `max_manual_15min`, `tent_media_manual`.
Degradação do leitor: `tx_manual_8_11`, `tx_manual_11_14`, `tx_manual_14_17`, `tx_manual_17_`.

### 4.5 Flags nacionais (`analise_logs_brasil.py`)

Quantis calculados sobre as 497.895 urnas (sem ZZ), com mínimos de contagem para evitar razões instáveis:

| Flag | Condição | Limiar nacional |
|---|---|---|
| `f_manual_rapido` | `log_manual ≥ 10 AND log_bio ≥ 10 AND razao_dur_manual_bio < p0,1` | 0,80 |
| `f_manual_fim` | `manual_ult60 ≥ 5 AND (frac_manual_ult60 / frac_votos_ult60) > p99,9` | 6,86 |
| `f_votos_rapidos_fim` | `votos_ult60 ≥ 10 AND gap_mediano_ult60_s < p0,1` | 69 s |
| `f_leitor_degrada_tarde` | salto `tx_manual_14_17 − tx_manual_8_11 > p99,9` | 0,18 |
| `f_manual_lt30` | `log_manual ≥ 10 AND pct_manual_lt30 > p99,9` | |

Agregações: por **local de votação** (`loc`, 68.018 locais com ≥ 30 manuais e ≥ 30 biométricos; razão de duração = soma das durações manuais / soma das biométricas; flag se < p0,1 = 0,91) e por **município** (`mun`, 5.520 com ≥ 100 manuais; p0,1 = 1,026; mediana 1,311). "Esperado por acaso" de urnas flagradas em um município = 0,001 × urnas elegíveis.

## 5. Por que a razão de duração importa

Um eleitor habilitado manualmente passou por 4 tentativas de digital e pela digitação de dados pessoais; é em geral um eleitor com mais dificuldade (idade, trabalho manual). Em 95% das urnas ele demora **mais** para votar que o biométrico da mesma urna (mediana 1,26×). Uma urna, um local ou um município onde os manuais votam sistematicamente **mais rápido** que os biométricos inverte essa relação e precisa de explicação. O log não diz qual; as explicações inocentes possíveis (eleitores em grupo com "cola", mesário operando de forma diferente) e as que não são estão listadas nos relatórios. É esse, e só esse, o critério que aponta para Bom Lugar e Maranhãozinho.

## 6. Decisões de desenho que podem ser contestadas

- Z-scores dentro do município assumem que o município é o grupo de comparação certo. Para municípios com menos de 8 seções não há z.
- Os quartis de `aptos` são nacionais, não por UF.
- Limiares p0,1 / p99,9 geram, por construção, ~500 flags em 500 mil urnas. O que interessa não é o número, é se as flags se concentram (por local, município, região) além do acaso.
- A duração do voto inclui o tempo de deslocamento até a cabine; isso é igual para manuais e biométricos da mesma urna, por isso a razão é usada, não a duração absoluta.
- "Última hora" é relativa ao encerramento observado, não ao previsto. Votos após o horário previsto são contados à parte (`n_votos_apos_fech_prev`).
