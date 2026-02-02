# Intuitive Care - Desafio Técnico (Estágio)

Este repositório contém a solução Full-Stack para o desafio técnico da Intuitive Care. O projeto foi estruturado como um **Monorepo** que abrange todo o ciclo de vida dos dados: Engenharia de Dados (ETL), Enriquecimento (Data Enrichment), Banco de Dados (SQL) e Desenvolvimento Web (Vue.js + Python).

## 📂 Estrutura do Projeto

O projeto foi organizado em módulos independentes que funcionam como um Pipeline de Dados sequencial:

* **`1_etl_ans/`** **(Tarefa 1)**
    * *Função:* Extração (`Extract`).
    * *Descrição:* Scripts responsáveis por varrer o site da ANS via scraping, baixar e consolidar os dados brutos contábeis.
* **`2_transformacao/`** **(Tarefa 2)**
    * *Função:* Transformação (`Transform`).
    * *Descrição:* Scripts que enriquecem os dados cruzando com o cadastro oficial (CADOP), validam regras de negócio, geram as agregações estatísticas e **persistem dados intermediários**.
* **`3_banco_dados/`** **(Tarefa 3)**
    * *Função:* Modelagem e Carga (`Load/Storage`).
    * *Descrição:* Orquestrador em Python e scripts SQL para modelagem do banco de dados relacional (PostgreSQL) e execução de queries analíticas.
* **`4_interface_web/`** **(Tarefa 4)**
    * *Função:* Visualização (`Frontend`).
    * *Descrição:* Aplicação Web (Frontend Vue.js + Backend Python) para visualização dos dados processados.

---

## ⚙️ Pré-requisitos

* **Python 3.10+**
* **PostgreSQL 14+** (Rodando localmente na porta 5432)
* **Gerenciador de pacotes:** `pip`

---

## 🚀 Como Executar o Pipeline de Dados

Para garantir a integridade e rastreabilidade dos dados, a execução deve seguir a ordem abaixo:

### Passo 1: Extração de Dados Brutos (ETL)

Este script conecta-se ao servidor FTP da ANS, identifica os 3 trimestres mais recentes, baixa os arquivos ZIP (lidando com estruturas de pastas variadas) e consolida tudo em um único CSV.

```bash
cd 1_etl_ans
# Crie e ative seu ambiente virtual, se necessário
pip install -r requirements.txt
python main.py
```

- **Saída:** `output/consolidado_despesas.csv`

- **Nota:** O arquivo gerado mantém a coluna **RegistroANS** como chave primária.  
  As colunas **CNPJ** e **Razão Social** são preenchidas com `"N/A"`, pois os arquivos contábeis originais não disponibilizam essas informações.

---

### Passo 2: Transformação, Enriquecimento e Validação

Nesta etapa, o script lê o arquivo bruto, baixa o **Cadastro de Operadoras (CADOP)**, realiza o cruzamento de dados e gera arquivos para análise.

**Atualização:** O script agora salva uma cópia do CADOP bruto (`relatorio_cadop.csv`) para ser consumido posteriormente pelo Banco de Dados, evitando necessidade de novo scraping.

```bash
# Partindo da pasta anterior (1_etl_ans)
cd ../2_transformacao
pip install -r requirements.txt
python main.py
```

### Saídas Geradas

1. `output/despesas_agregadas.csv`  
   *(Dados processados e somados por UF).*

2. `output/Teste_JoaoGabriel.zip`  
   *(Arquivo final compactado).*

3. `output/relatorio_cadop.csv`  
   **(Novo:** Arquivo bruto para carga no Banco de Dados).*

---

### Passo 3: Banco de Dados e Análise SQL

Esta etapa carrega os dados processados em um banco **PostgreSQL**.  
Foi desenvolvido um orquestrador em Python que resolve problemas de permissão de arquivos no Linux (copiando temporariamente para `/tmp`) e injeta os caminhos absolutos corretos nos scripts SQL.

```bash
cd ../3_banco_dados
pip install -r requirements.txt
python main.py
```

O script solicitará seu usuário e senha do PostgreSQL local, criará o banco intuitive_care_db e executará a carga automaticamente.
Para verificar os resultados das queries analíticas via terminal:

```bash
psql -h localhost -U postgres -d intuitive_care_db -f 3_queries_analiticas.sql
```

## 🧠 Trade-offs e Decisões Técnicas (Documentação Obrigatória)

Abaixo estão as justificativas para as abordagens técnicas adotadas em cada etapa do desafio.

---

#### 📋 Tarefa 1: Extração (ETL)

### Scraping Dinâmico vs URL Estática

- **Decisão:** Scraping dinâmico com **BeautifulSoup**.

- **Justificativa:**  
  As URLs no site da ANS mudam frequentemente (troca de ano ou versão do arquivo).  
  O script varre automaticamente a estrutura de pastas do FTP para localizar o dado mais recente, tornando a solução **resiliente a mudanças estruturais** e reduzindo manutenção manual.

---

#### 📋 Tarefa 2: Transformação e Enriquecimento

### 1. Estratégia de Join e Integridade

- **Decisão:** Utilizar o **RegistroANS** como chave (Foreign Key) em vez do CNPJ.

  - **Justificativa:**  
    Os arquivos contábeis brutos não contêm CNPJ.  
    O **RegistroANS** é o identificador único e imutável definido pela agência reguladora, garantindo integridade referencial.

- **Decisão:** Utilização de `pandas.merge` (**Hash Join em memória**).

  - **Justificativa:**  
    O volume total de dados, somado ao cadastro (≈ 1.200 registros), cabe confortavelmente na RAM (< 1 GB).  
    O processamento em memória é **ordens de magnitude mais rápido** do que o uso de bancos intermediários ou escrita em disco.

---

### 2. Validação e Tratamento de Dados

- **CNPJs inválidos:** Mantidos, com geração de logs de aviso.

  - **Justificativa:**  
    A exclusão desses registros mascararia o volume financeiro real do setor.  
    Priorizou-se a **fidelidade contábil** em detrimento da pureza cadastral.

- **Valores zerados:** Removidos.

  - **Justificativa:**  
    Esses registros distorcem métricas estatísticas como média, soma e desvio padrão, impactando análises analíticas.

---

#### 📋 Tarefa 3: Banco de Dados (SQL)

### 1. Modelagem: Normalização vs Desnormalização

- **Escolha:** Abordagem híbrida (**Star Schema**).

  - **Tabela Dimensão (`operadoras`):**  
    Armazena dados cadastrais estáveis das operadoras.

  - **Tabela Fato (`despesas_contabeis`):**  
    Armazena eventos financeiros, referenciando a operadora por ID.

  - **Tabela Agregada (`despesas_agregadas_final`):**  
    Estrutura desnormalizada para leitura e análise rápida.

- **Justificativa:**  
  As despesas crescem exponencialmente ao longo do tempo, enquanto os dados cadastrais permanecem majoritariamente estáveis.  
  Repetir strings como **Razão Social** na tabela de fatos aumentaria uso de armazenamento e I/O.  
  A normalização otimiza atualizações cadastrais, enquanto a tabela agregada acelera consultas analíticas.

---

### 2. Tipos de Dados (Data Types)

- **Valores Monetários:** `DECIMAL(15, 2)` vs `FLOAT`.

  - **Decisão:** `DECIMAL(15, 2)`.

  - **Justificativa:**  
    Tipos `FLOAT` utilizam ponto flutuante binário, introduzindo erros de arredondamento em operações financeiras.  
    `DECIMAL` garante **precisão exata**, essencial para dados contábeis.

- **Datas:** `DATE` vs `VARCHAR`.

  - **Decisão:** `DATE`.

  - **Justificativa:**  
    `VARCHAR` impede ordenação cronológica correta e dificulta indexação.  
    O trimestre foi convertido para `DATE` (dia 01 do mês inicial do trimestre), facilitando séries temporais, filtros e índices.

---

### 3. Tratamento de Inconsistências na Importação

- **Encoding:**  
  Conversão explícita de **LATIN1** (CADOP) e **UTF-8** (Despesas) nos comandos `COPY`, evitando corrupção de caracteres.

- **Limpeza de Strings:**  
  Uso de `REGEXP_REPLACE` no SQL para sanitizar o campo **RegistroANS** antes da conversão para inteiro.

- **Truncagem de UF:**  
  Tratamento de registros onde a UF vinha como `"N/A"` (3 caracteres) para uma coluna `CHAR(2)`.  
  Aplicou-se `LEFT(uf, 2)` combinado com `NULLIF`, garantindo que o pipeline não falhasse.

---

## 🛠 Tecnologias Utilizadas

### 🔤 Linguagem e Bibliotecas

- **Python 3.10+**
- **pandas:** Manipulação de dados e agregações.
- **requests / BeautifulSoup:** Scraping e download de arquivos.
- **psycopg2 / SQLAlchemy:** Conectividade com banco de dados.

---

### 🗄️ Banco de Dados

- **PostgreSQL 14+**  
  Banco de dados relacional utilizado para armazenamento, modelagem e análise analítica.
