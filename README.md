# DT-Árvore de Cenários

Projeto desenvolvido no contexto do convênio **IMA/UFLA/FUNDECC nº 024/2024**, dentro do plano de trabalho:

> **“Raízes da Sanidade: um estudo sobre árvore de cenários para determinação de propriedades de risco para febre aftosa”**

O objetivo do projeto é identificar e priorizar propriedades rurais para ações de vigilância sanitária relacionadas à febre aftosa. Para isso, o sistema combina:

- pré-processamento e consolidação de dados cadastrais;
- dados geográficos e do CAR;
- fatores de risco sanitário;
- movimentações via GTA;
- modelagem probabilística com **Beta-PERT**;
- simulação de **Monte Carlo**;
- cenários binários de risco;
- e otimização matemática para seleção final de propriedades por ESEC.

---

## Visão geral do fluxo

O pipeline completo é executado em quatro etapas principais:

```text
dados brutos
    │
    ▼
scripts/run_preprocess.py
    │
    ▼
data/interim/propriedades_consideradas_interim.csv
    │
    ▼
scripts/run_areas.py
    │
    ▼
data/processed/propriedades_processed.csv
    │
    ▼
scripts/run_risks.py
    │
    ▼
data/processed/propriedades_risco_sanitario.csv
    │
    ▼
scripts/run_all_pipeline.py
    │
    ├── src/legacy/explora_modelo.py
    ├── src/monte_carlo.py
    └── src/seleciona_propriedades.py
    │
    ▼
resultados por Coordenadoria / ESEC
```

Em termos práticos:

```bash
python3 scripts/run_preprocess.py
python3 scripts/run_areas.py
python3 scripts/run_risks.py
python3 scripts/run_all_pipeline.py
```

Essa é a ordem recomendada quando todo o pipeline precisa ser reconstruído desde os dados brutos.

---

# Estrutura do projeto

Uma estrutura simplificada do repositório é:

```text
DT-ARVORE-DE-CENARIOS/
│
├── armazem/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── notebooks/
├── properties-dashboard/
├── results/
├── scripts/
│   ├── run_preprocess.py
│   ├── run_areas.py
│   ├── run_risks.py
│   ├── run_all_pipeline.py
│   ├── run_query.py
│   └── stress_test_monte_carlo.py
│
├── src/
│   ├── integrations/
│   │   └── armazem/
│   ├── legacy/
│   │   └── explora_modelo.py
│   ├── armazem_io.py
│   ├── data_io.py
│   ├── debug_tools.py
│   ├── monte_carlo.py
│   ├── pipeline_runner.py
│   ├── preprocessing.py
│   ├── processador_area_car.py
│   ├── risk_processing.py
│   └── seleciona_propriedades.py
│
├── .env
├── env_armazem.conf
├── env_homolog.conf
├── env.properties
├── requirements.txt
└── README.md
```

---

# 1. Pré-processamento das explorações

Script:

```bash
python3 scripts/run_preprocess.py
```

Arquivo principal:

```text
scripts/run_preprocess.py
```

Essa etapa constrói a primeira base consolidada de propriedades consideradas.

Ela:

1. carrega os dados brutos de exploração pecuária;
2. carrega a base de propriedades com coordenadas;
3. carrega os arquivos territoriais das Coordenadorias/ESECs;
4. normaliza CPF/CNPJ e identificadores;
5. identifica propriedades sem coordenadas;
6. mantém apenas propriedades com coordenadas;
7. adiciona latitude e longitude;
8. interpreta a data de atualização cadastral;
9. mantém explorações bovinas ativas;
10. seleciona a maior exploração bovina por propriedade;
11. calcula o total de bovinos da propriedade;
12. associa cada propriedade à sua ESEC e Coordenadoria;
13. padroniza os nomes das colunas.

### Saída principal

```text
data/interim/propriedades_consideradas_interim.csv
```

Também é gerado um relatório com a quantidade de propriedades por ESEC.

### Regra de representação da propriedade

Uma propriedade pode possuir mais de uma exploração. Nessa etapa, o pipeline seleciona como linha representativa aquela com maior quantidade de bovinos, mas preserva em uma coluna separada o total de bovinos agregado da propriedade.

---

# 2. Enriquecimento com CAR, área e densidade bovina

Script:

```bash
python3 scripts/run_areas.py
```

Essa etapa parte de:

```text
data/interim/propriedades_consideradas_interim.csv
```

e cruza as propriedades com informações do CAR e do shapefile de imóveis.

O fluxo é:

```text
propriedade
   │
   ▼
mapeamento propriedade → CAR
   │
   ▼
CAR → geometria / área
   │
   ▼
num_area
   │
   ▼
densidade_bovinos
```

### Operações realizadas

- carregamento do shapefile de imóveis;
- seleção das colunas relevantes;
- vínculo entre código da propriedade e código CAR;
- vínculo entre CAR e geometria;
- obtenção de `num_area`;
- preenchimento de áreas ausentes pela mediana das propriedades do mesmo município;
- remoção de colunas auxiliares;
- cálculo da densidade bovina.

A densidade é calculada por:

```text
densidade_bovinos = total_de_bovinos / num_area
```

Valores infinitos são convertidos para nulos.

### Saída principal

```text
data/processed/propriedades_processed.csv
```

---

# 3. Cálculo dos fatores de risco sanitário

Script:

```bash
python3 scripts/run_risks.py
```

Essa etapa recebe:

```text
data/processed/propriedades_processed.csv
```

e calcula os cinco fatores de risco utilizados pela árvore de cenários:

```text
risco_gtas
risco_densidade_bovinos
risco_suinos
risco_lixoes
risco_eventos
```

Ao final, também é criada:

```text
qtd_riscos_altos
```

com a quantidade de fatores classificados como `alto` para cada propriedade.

---

## 3.1 Risco associado a suínos

O risco de suínos é calculado a partir do relatório específico de suinocultura.

Entre os fatores identificados pelo código estão:

- `SUINOS_S_1`;
- `LAVAGEM`;
- `BAIXA_BIOSSEGURIDADE`;
- `NAO_TECNIFICADA`;
- `GRANJA_COM_VULNERABILIDADE_ALTA`.

A classificação final é binária:

```text
baixo
alto
```

Uma propriedade é classificada como `alto` quando possui pelo menos um dos fatores de risco identificados.

---

## 3.2 Risco associado a lixões

Para cada propriedade é calculada a menor distância até um lixão usando distância de Haversine.

A regra principal é:

```text
distância até lixão <= 3 km  → alto
distância até lixão > 3 km   → baixo
```

Existe ainda uma regra complementar proveniente do relatório de suínos, capaz de classificar algumas propriedades como risco alto de lixões conforme o código identificado em `Suinos_COD`.

---

## 3.3 Risco associado a eventos

Os estabelecimentos de eventos passam inicialmente por um filtro de alto risco usando o percentil 75 de variáveis como:

```text
n_eventos_realizados
n_gta
```

Depois é calculada a distância mínima entre cada propriedade e os eventos considerados.

Regra padrão:

```text
distância até evento <= 3 km → alto
distância até evento > 3 km  → baixo
```

---

## 3.4 Risco de densidade bovina

A densidade bovina já deve existir antes desta etapa.

A classificação usa o percentil 75:

```text
densidade >= Q75 → alto
densidade <  Q75 → baixo
```

No final do pipeline, esse risco é recalculado regionalmente por Coordenadoria.

---

## 3.5 Risco associado às GTAs

O pipeline utiliza dados de GTA de entrada em propriedades de Minas Gerais.

São consideradas, entre outras, bases de:

- entradas com origem em Minas Gerais;
- entradas com origem em outros estados;
- saídas de propriedades mineiras.

Antes da agregação, movimentações com mesma:

```text
data
origem
destino
```

são consolidadas.

Por propriedade são calculados:

```text
total_movimentacoes_gtas
total_animais_gtas
```

O risco de GTA é classificado pelo percentil 75 do número de movimentações.

Assim como a densidade bovina, esse risco é recalculado dentro de cada Coordenadoria.

---

## Saída consolidada de risco

Ao final de `run_risks.py` é criado:

```text
data/processed/propriedades_risco_sanitario.csv
```

Esse arquivo é a entrada principal da árvore de cenários.

---

# 4. Execução da árvore de cenários

Para processar todas as Coordenadorias e ESECs:

```bash
python3 scripts/run_all_pipeline.py
```

Esse script:

1. carrega `propriedades_risco_sanitario.csv`;
2. identifica automaticamente todos os pares únicos:

```text
coordenadoria
esec
```

3. executa o pipeline individual para cada combinação;
4. registra sucesso, erro e tempo de execução;
5. gera um resumo consolidado.

### Resumo da execução

```text
results/resumo_execucao_pipeline_todas_esecs.csv
```

---

# Pipeline individual de uma ESEC

A função central é:

```python
run_single_pipeline(coordenadoria_nome, esec_nome)
```

definida em:

```text
src/pipeline_runner.py
```

Internamente, a sequência é:

```text
load_propriedades_risco_sanitario()
              │
              ▼
      explora_modelo.main()
              │
              ▼
       monte_carlo.main()
              │
              ▼
 seleciona_propriedades.main()
```

---

# 5. Geração dos parâmetros Beta-PERT

Arquivo:

```text
src/legacy/explora_modelo.py
```

Para cada ESEC, o código calcula a frequência observada de risco alto para os cinco fatores:

```text
gtas
densidade_bovinos
suinos
eventos
lixoes
```

Para cada fator:

```text
x = número de propriedades classificadas como alto
n = número total de propriedades da ESEC
```

A proporção observada é:

```text
p̂ = x / n
```

Em seguida, é calculado um intervalo de confiança de Wilson de 95%.

Os parâmetros utilizados no PERT são:

```text
mínimo = limite inferior de Wilson
moda   = p̂
máximo = limite superior de Wilson
```

A parametrização clássica utiliza:

```text
λ = 4
```

A média PERT de cada fator é calculada por:

```text
(min + λ × mode + max) / (λ + 2)
```

Essas médias são posteriormente normalizadas, gerando os pesos de relevância de cada fator.

### Saída

Para cada ESEC é gerado:

```text
results/<coordenadoria>/<esec>/<esec>_pert.json
```

contendo:

```json
{
    "resultados_pert_dict": {},
    "relevancia_dos_riscos": {},
    "#exploracoes_consideradas": 0
}
```

Também podem ser produzidos histogramas Beta-PERT.

---

# 6. Simulação de Monte Carlo

Arquivo:

```text
src/monte_carlo.py
```

O Monte Carlo representa os cinco fatores como variáveis binárias:

```text
A = Alto
B = Baixo
```

A ordem adotada é:

```text
1. GTAs
2. Densidade bovina
3. Suínos
4. Lixões
5. Eventos
```

Como existem cinco fatores binários:

```text
2⁵ = 32 cenários possíveis
```

Exemplos:

```text
BBBBB
ABBBB
AABBB
ABABA
AAAAA
```

### Exemplo

```text
AABBB
│││││
││││└─ Eventos
│││└── Lixões
││└─── Suínos
│└──── Densidade bovina
└───── GTAs
```

Nesse cenário:

- GTA = alto;
- densidade bovina = alto;
- suínos = baixo;
- lixões = baixo;
- eventos = baixo.

---

## Distribuição PERT

Para cada fator, uma probabilidade é sorteada da distribuição PERT.

Essa probabilidade é então utilizada para decidir se o fator assume:

```text
Alto
ou
Baixo
```

A execução padrão utilizada pelo pipeline é:

```text
10.000 simulações por ESEC
```

---

## Cenário de especialista

O código também permite inserir cenários guiados por especialista.

Atualmente existe:

```python
'AABBB': 0.05
```

Isso reserva aproximadamente 5% das simulações para esse padrão.

---

# 7. Sensibilidade e risco residual

Para fatores ativos no cenário, são sorteadas sensibilidades individuais.

A Sensibilidade Unitária utilizada pelo código é:

```text
SeU = 1 - ∏(1 - sensibilidade_i)
```

A Sensibilidade Composta é:

```text
CSe = 1 - (1 - SeU)^n
```

onde `n` corresponde ao número de explorações consideradas.

O risco-base do cenário é calculado a partir dos pesos de relevância dos fatores classificados como alto.

Depois é aplicado o ajuste de sensibilidade:

```text
risco_ajustado = risco_base × (1 - SeU)
```

A classificação final do escore é:

```text
0  a 33  → Baixo
>33 a 66 → Médio
>66       → Alto
```

---

# 8. Resultados do Monte Carlo

Entre os resultados agregados por cenário estão:

```text
ocorrencias
probabilidade_%
risco_medio
seu_medio
cse_medio
n_comp_ativos_medio
```

Também são produzidos:

- top cenários;
- simulações detalhadas;
- gráficos de distribuição PERT;
- gráficos de risco;
- análises de influência dos fatores.

Os arquivos ficam organizados em:

```text
results/<coordenadoria>/<esec>/
```

---

# 9. Associação entre cenários e propriedades reais

Arquivo:

```text
src/seleciona_propriedades.py
```

Após o Monte Carlo, cada cenário é traduzido novamente para os cinco campos de risco das propriedades.

Exemplo:

```text
AABBB
```

corresponde a:

```text
risco_gtas                = alto
risco_densidade_bovinos   = alto
risco_suinos              = baixo
risco_lixoes              = baixo
risco_eventos             = baixo
```

As propriedades da ESEC são filtradas de acordo com essa combinação.

Inicialmente são considerados cenários cuja probabilidade seja de pelo menos:

```text
1%
```

O cenário `BBBBB` é colocado ao final da ordenação.

---

# 10. Cenários de especialista na seleção

Na etapa de seleção, um cenário é considerado de especialista quando:

```python
codigo_cenario.count("A") >= 2
```

ou quando é especificamente:

```text
ABBBB
```

Também existe um peso adicional em função do número de fatores classificados como alto.

Esse peso influencia a priorização dos cenários durante a seleção.

---

# 11. Otimização matemática

A seleção final das propriedades é formulada como um problema de Programação Linear Inteira usando **PuLP**.

Para cada propriedade existe uma variável binária:

```text
xᵢ = 1 → propriedade selecionada
xᵢ = 0 → propriedade não selecionada
```

A função objetivo prioriza propriedades com:

- maior número de movimentações GTA;
- maior quantidade de animais movimentados.

Também existem variáveis de penalidade associadas aos cenários de especialista.

O código utiliza:

```text
Big M = 1.000.000
```

para penalizar violações dessas condições.

---

## Capacidade da ESEC

A capacidade é obtida do arquivo:

```text
data/Capacidade_esecs.xls
```

São consideradas as colunas:

```text
PLANEJAMENTO
QUANTITATIVO NA LISTA ÁRVORE DE CENÁRIOS
```

O limite principal é calculado como:

```text
threshold_risk =
ceil(
    1.5 × max(
        planejamento,
        quantitativo_na_lista
    )
)
```

Existe ainda tratamento específico quando o cenário principal é:

```text
BABBB
```

---

## Cobertura municipal

O modelo busca garantir cobertura das propriedades válidas por município.

O parâmetro atual é:

```text
lower_bound_propriedades_por_municipio = 5
```

O valor efetivamente exigido é limitado pela quantidade de propriedades válidas disponíveis no município.

---

# 12. Resultado final por ESEC

Quando o solver encontra uma solução ótima, é criado:

```text
<esec>_exploracoes_ordenadas_por_risco.csv
```

As propriedades selecionadas são ordenadas por:

```text
total_movimentacoes_gtas
total_animais_gtas
```

em ordem decrescente.

Caso o modelo não encontre solução ótima, é criado um arquivo:

```text
<esec>_ERRO.txt
```

---

# Execução completa

A forma mais simples de reconstruir todo o pipeline é:

```bash
python3 scripts/run_preprocess.py
python3 scripts/run_areas.py
python3 scripts/run_risks.py
python3 scripts/run_all_pipeline.py
```

---

# Execução somente da árvore de cenários

Se o arquivo abaixo já estiver atualizado:

```text
data/processed/propriedades_risco_sanitario.csv
```

não é necessário repetir todo o pré-processamento.

Basta executar:

```bash
python3 scripts/run_all_pipeline.py
```

---

# Execução de uma única ESEC

Também é possível executar programaticamente uma única combinação:

```python
from src.pipeline_runner import run_single_pipeline

run_single_pipeline(
    coordenadoria_nome="Oliveira",
    esec_nome="Lavras",
)
```

Isso executará:

```text
explora_modelo
    ↓
Monte Carlo
    ↓
seleção de propriedades
```

apenas para a ESEC informada.

---

# Dependências

As dependências Python do projeto são mantidas em:

```text
requirements.txt
```

Instalação:

```bash
python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

Entre as bibliotecas utilizadas no código estão:

- pandas;
- numpy;
- geopandas;
- scipy;
- statsmodels;
- scikit-learn;
- matplotlib;
- seaborn;
- PuLP;
- requests;
- python-dotenv.

---

# Integração com o Armazém

O projeto possui suporte em desenvolvimento para leitura direta do **Armazém** via GraphQL.

Arquivos relacionados:

```text
src/armazem_io.py
src/integrations/armazem/
scripts/run_query.py
```

O loader principal suporta duas fontes:

```text
csv
armazem
```

Atualmente o comportamento padrão de:

```python
load_propriedades_risco_sanitario()
```

é utilizar:

```text
csv
```

ou seja:

```text
data/processed/propriedades_risco_sanitario.csv
```

---

## Variáveis de ambiente do Armazém

O módulo `src/armazem_io.py` utiliza:

```text
ARMAZEM_HOST
ARMAZEM_PORT
ARMAZEM_PROTOCOL
ARMAZEM_GRAPHQL_PATH
ARMAZEM_API_KEY
```

Defaults existentes no código:

```text
ARMAZEM_PORT=9100
ARMAZEM_PROTOCOL=http
ARMAZEM_GRAPHQL_PATH=/graphql
```

`ARMAZEM_HOST` e `ARMAZEM_API_KEY` precisam ser configurados quando a integração direta for utilizada.

---

# Execução manual de query GraphQL

O script:

```text
scripts/run_query.py
```

permite executar um arquivo `.graphql`.

Exemplo:

```bash
python3 scripts/run_query.py nome_da_query.graphql
```

O resultado é salvo em:

```text
results/queries/
```

Essa ferramenta é independente do fluxo principal descrito anteriormente.

---

# Teste de desempenho do Monte Carlo

O arquivo:

```text
scripts/stress_test_monte_carlo.py
```

executa testes com:

```text
1.000
10.000
50.000
100.000
```

simulações.

São medidos:

- tempo de execução;
- memória utilizada;
- pico de memória.

Execução:

```bash
python3 scripts/stress_test_monte_carlo.py
```

Esse script é destinado a testes e não faz parte da execução normal do pipeline.

---

# Diretórios de dados

## `data/raw`

Dados de entrada originais utilizados pelo pipeline.

Exemplos de fontes utilizadas pelo código:

- exploração pecuária;
- propriedades com coordenadas;
- estrutura territorial das Coordenadorias;
- CAR;
- shapefile de imóveis;
- suínos;
- lixões;
- estabelecimentos de eventos;
- GTAs.

## `data/interim`

Dados intermediários.

Principal arquivo:

```text
propriedades_consideradas_interim.csv
```

## `data/processed`

Dados consolidados e prontos para etapas posteriores.

Principais arquivos:

```text
propriedades_processed.csv
propriedades_risco_sanitario.csv
```

## `results`

Resultados das simulações, diagnósticos, relatórios e seleção final de propriedades.

---

# Principais módulos

| Arquivo | Responsabilidade |
|---|---|
| `src/data_io.py` | Leitura e escrita dos datasets do projeto |
| `src/preprocessing.py` | Limpeza, transformação e enriquecimento dos dados |
| `src/risk_processing.py` | Cálculo dos fatores de risco |
| `src/legacy/explora_modelo.py` | Estimativa PERT e pesos dos fatores |
| `src/monte_carlo.py` | Simulação dos 32 cenários |
| `src/seleciona_propriedades.py` | Associação dos cenários às propriedades e otimização |
| `src/pipeline_runner.py` | Pipeline individual de uma ESEC |
| `src/armazem_io.py` | Leitura opcional diretamente do Armazém |
| `src/processador_area_car.py` | Funções específicas relacionadas ao CAR/área |

---

# Ordem de execução resumida

Se houver dúvida sobre o que rodar, use este quadro:

| Ordem | Comando | Resultado |
|---:|---|---|
| 1 | `python3 scripts/run_preprocess.py` | `propriedades_consideradas_interim.csv` |
| 2 | `python3 scripts/run_areas.py` | `propriedades_processed.csv` |
| 3 | `python3 scripts/run_risks.py` | `propriedades_risco_sanitario.csv` |
| 4 | `python3 scripts/run_all_pipeline.py` | resultados por Coordenadoria/ESEC |

---

# Observações técnicas

Alguns pontos merecem atenção durante futuras refatorações.

### 1. SeU

A implementação atual calcula:

```text
SeU = 1 - ∏(1 - pᵢ)
```

Alguns comentários existentes no código ainda descrevem essa grandeza como “produto das sensibilidades”. O comportamento implementado deve ser considerado a referência do código até eventual revisão conceitual.

### 2. Cenários de especialista

No modelo de otimização, as cotas associadas a cenários de especialista são implementadas por restrições superiores acompanhadas de variável de penalidade. Portanto, o nome “quota mínima” utilizado em alguns trechos não representa literalmente todas as restrições do modelo.

### 3. Propriedades sem movimentação GTA

Após a solução do modelo, a lista exportada mantém apenas propriedades cuja quantidade de movimentações GTA seja maior que zero. Essa filtragem ocorre depois da otimização.

### 4. `run_esecs.sh`

Existe/ existiu uma estratégia antiga baseada em um shell script com listas manuais de ESECs e Coordenadorias.

O fluxo atual é preferível:

```bash
python3 scripts/run_all_pipeline.py
```

porque os pares Coordenadoria/ESEC são obtidos diretamente da base consolidada.

---

# Convenções dos cenários

| Letra | Significado |
|---|---|
| `A` | fator de risco alto |
| `B` | fator de risco baixo |

Ordem:

| Posição | Fator |
|---:|---|
| 1 | GTAs |
| 2 | Densidade bovina |
| 3 | Suínos |
| 4 | Lixões |
| 5 | Eventos |

Exemplo:

```text
ABAAB
```

significa:

```text
GTAs               → Alto
Densidade bovina   → Baixo
Suínos             → Alto
Lixões             → Alto
Eventos            → Baixo
```

---

# Objetivo final

O objetivo do pipeline não é apenas atribuir um escore abstrato de risco.

O processo completo transforma dados cadastrais, sanitários, geográficos e de movimentação em uma lista operacional de propriedades priorizadas por ESEC:

```text
dados
  ↓
riscos individuais
  ↓
probabilidades
  ↓
cenários
  ↓
simulação
  ↓
otimização
  ↓
propriedades prioritárias
```

Essa lista pode apoiar o planejamento de ações de vigilância sanitária para febre aftosa no âmbito do Instituto Mineiro de Agropecuária.

---

## Projeto

**Pesquisa, Desenvolvimento e Inovação Aplicados à Modernização Tecnológica do Instituto Mineiro de Agropecuária – IMA**

Convênio nº **024/2024 – IMA/UFLA/FUNDECC**

Plano de Trabalho:

**Raízes da Sanidade: um estudo sobre árvore de cenários para determinação de propriedades de risco para febre aftosa**
