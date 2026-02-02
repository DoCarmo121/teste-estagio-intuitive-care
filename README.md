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

# 🧠 Trade-offs e Decisões Técnicas  
**Documentação Obrigatória**

Este documento descreve as principais decisões técnicas adotadas no pipeline de dados, destacando os trade-offs entre performance, qualidade de dados, simplicidade e escalabilidade.

---

## 1. Processamento e Extração (ETL)

### ⚡ Processamento: Memória vs. Incremental vs. Stream

**Decisão:** Abordagem híbrida — *Download via Stream* + *Processamento In-Memory*.

**Justificativa:**

- **Download:**  
  Os arquivos ZIP são baixados em *chunks* de 8 KB, reduzindo picos de memória e tornando o processo mais resiliente a falhas de rede ou arquivos inesperadamente grandes.

- **Processamento:**  
  O volume consolidado dos três trimestres, mesmo após descompactação, permanece abaixo de 2 GB, cabendo confortavelmente na memória RAM.  
  O uso de operações vetorizadas do **Pandas (In-Memory)** é ordens de magnitude mais rápido do que abordagens baseadas em disco ou frameworks distribuídos (ex: Spark), que seriam excessivos para esse cenário.

---

### 📅 Inconsistência de Datas

**Problema:**  
A coluna de data nos CSVs originais apresenta múltiplos formatos inconsistentes (`1T2024`, `01/01/2024`, `jan/24`).

**Decisão:**  
Ignorar a data interna dos arquivos.

**Solução:**  
Utilizar a estrutura de diretórios do FTP da ANS como *Source of Truth*, injetando programaticamente as colunas **Ano** e **Trimestre**.

**Benefício:**  
Elimina ambiguidades e garante consistência temporal 100% confiável.

---

## 2. Transformação e Enriquecimento

### 🔗 Estratégia de Join e Integridade (RegistroANS)

**Decisão:**  
Utilizar `RegistroANS` como chave primária de ligação, com `pandas.merge` (Hash Join).

**Problema:**  
Os arquivos contábeis não possuem CNPJ, apenas o identificador `REG_ANS`.

**Solução:**  

- **Tarefa 1:** Extração fiel dos dados contábeis.  
- **Tarefa 2:** Camada de *Trusted Data*, com download do CADOP oficial e *Left Join* via `RegistroANS`.

**Benefícios:**

- Garante integridade referencial sem depender de dados inexistentes na fonte.
- Hash Join em memória apresenta complexidade **O(N)**, ideal para datasets deste porte.

---

### 🧾 Tratamento de CNPJs Inválidos

**Trade-off:** Fidelidade contábil vs. pureza cadastral.

**Decisão:**  
Manter os registros, mas gerar *log de auditoria*.

**Justificativa:**

- **Prós:**  
  O volume financeiro agregado do setor permanece correto. Remover linhas distorceria o balanço contábil.
- **Contras:**  
  O dataset final contém dados cadastrais inconsistentes, que devem ser tratados na camada de visualização ou consumo.

---

### 🔢 Tratamento de Valores Zerados ou Negativos

**Decisão:**  
Filtragem rigorosa — `valor > 0`.

**Justificativa:**  
Valores negativos (estornos) ou nulos distorcem métricas estatísticas como **média** e **desvio padrão**, que são centrais para a análise solicitada.  
A remoção garante relevância estatística e coerência analítica.

---

### 📉 Estratégia de Ordenação

**Decisão:**  
Ordenação em memória com `df.sort_values` (Quicksort interno).

**Justificativa:**  
Após a agregação (`GROUP BY`), o volume de dados reduz-se drasticamente (para poucos milhares de linhas).  
O custo computacional da ordenação em memória torna-se desprezível, não justificando *external sort* ou uso de banco de dados apenas para essa etapa.

---

## 3. Banco de Dados (SQL)

### 🏗️ Modelagem: Normalização — Opção A vs. Opção B

**Decisão:**  
**Opção B — Modelo Normalizado (Star Schema)**

- **Tabela Dimensão:** `operadoras` (dados cadastrais)
- **Tabela Fato:** `despesas_contabeis` (eventos financeiros)

**Justificativa:**

- **Volume:**  
  As despesas crescem exponencialmente a cada trimestre, enquanto os dados cadastrais são estáveis.
- **Eficiência:**  
  Evita repetição massiva de strings como *Razão Social*, reduzindo armazenamento e I/O.
- **Manutenibilidade:**  
  Atualizações cadastrais exigem alteração em apenas uma linha, garantindo consistência (ACID).

---

### 💲 Tipos de Dados: DECIMAL vs. FLOAT

**Decisão:**  
`DECIMAL(15,2)`

**Justificativa:**  
Tipos `FLOAT` utilizam ponto flutuante binário (IEEE 754), introduzindo erros de precisão (`0.1 + 0.2 ≠ 0.3`).  
Para dados financeiros, **precisão exata é obrigatória**, tornando `DECIMAL` a escolha correta.

---

### 🗓️ Tipos de Dados: DATE vs. VARCHAR

**Decisão:**  
`DATE`

**Justificativa:**  

- Permite ordenação cronológica correta.
- Viabiliza uso eficiente de funções de data, indexação e particionamento.
- O trimestre foi convertido para o primeiro dia do mês correspondente  
  *(ex: 1º trimestre → `2023-01-01`)*.

---

## 4. Queries Analíticas

### 🧠 Operadoras Acima da Média em 2 ou Mais Trimestres

**Decisão:**  
Uso de **CTEs (Common Table Expressions)** + agregação com `HAVING`.

**Estratégia:**

1. **CTE `media_trimestral`:**  
   Calcula a média global de despesas por trimestre.
2. **CTE `performance`:**  
   Compara cada operadora com a média do trimestre (flag 0 ou 1).
3. **Query final:**  
   Soma os flags e filtra operadoras com `SUM >= 2`.

**Justificativa:**

- **Legibilidade:**  
  CTEs tornam a query linear, clara e autodocumentável.
- **Performance:**  
  O *Query Planner* do PostgreSQL consegue materializar as CTEs de forma eficiente, evitando recálculos redundantes da média global.

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
