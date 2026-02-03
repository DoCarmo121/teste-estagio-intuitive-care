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
    * *Função:* Visualização (`Frontend` & `Backend`).
    * *Descrição:* API REST com FastAPI e Dashboard interativo com Vue.js 3.

---

## ⚙️ Pré-requisitos

* **Python 3.10+**
* **Node.js 18+** e **npm** (Necessário para a interface web)
* **PostgreSQL 14+** (Rodando localmente na porta 5432)
* **Gerenciador de pacotes:** `pip`

### 🔐 Configuração de Ambiente (.env)

O projeto utiliza variáveis de ambiente para gerenciar credenciais sensíveis.
**Antes de executar**, crie um arquivo chamado `.env` na raiz do projeto com as configurações do seu PostgreSQL local:

```ini
# Arquivo: .env (na raiz do projeto)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=intuitive_care_db
DB_USER=postgres
DB_PASS=sua_senha_aqui
```

### 🐍 Configuração do Ambiente Virtual (Recomendado)

Para manter as dependências isoladas e organizadas, recomenda-se criar um ambiente virtual na raiz do projeto antes de começar:

**No Linux / Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**No Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

⚠️ **Atenção (Windows)**

Se ao tentar ativar aparecer um erro em vermelho informando que **“a execução de scripts foi desabilitada”**, isso é uma trava de segurança do **PowerShell**.

Para resolver, execute o comando abaixo **apenas uma vez** e depois tente ativar novamente:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

# 🚀 Como Executar o Pipeline de Dados

Para garantir a **integridade** e a **rastreabilidade dos dados**, a execução deve seguir rigorosamente a ordem abaixo.

---

## 🟢 Passo 1: Extração de Dados Brutos (ETL)

Este script conecta-se ao **servidor FTP da ANS**, identifica os **3 trimestres mais recentes**, baixa os arquivos ZIP (lidando com estruturas de pastas variadas) e consolida tudo em um único CSV.

### ▶️ Execução

```bash
cd 1_etl_ans
# Crie e ative seu ambiente virtual, se necessário
pip install -r requirements.txt
python main.py
```

### 📤 Saídas Geradas

- `output/consolidado_despesas.csv`
- `output/consolidado_despesas.zip` - Arquivo Compactado

- **Nota:** O arquivo gerado mantém a coluna **RegistroANS** como chave primária.  
  As colunas **CNPJ** e **Razão Social** são preenchidas com `"N/A"`, pois os arquivos contábeis originais não disponibilizam essas informações.

---

## 🟢 Passo 2: Transformação, Enriquecimento e Validação

Nesta etapa, o script lê o arquivo bruto, baixa o **Cadastro de Operadoras (CADOP)**, realiza o cruzamento de dados e gera arquivos para análise.

### 🔄 Atualização

O script agora salva uma cópia do **CADOP bruto** (`relatorio_cadop.csv`) para ser consumido posteriormente pelo **Banco de Dados**, evitando a necessidade de novo scraping.

### ▶️ Execução

```bash
# Partindo da pasta anterior (1_etl_ans)
cd ../2_transformacao
pip install -r requirements.txt
python main.py
```

### 📤 Saídas Geradas

- `output/despesas_agregadas.csv` — Dados processados e somados por UF  
- `output/Teste_JoaoGabriel.zip` — Arquivo final compactado  
- `output/relatorio_cadop.csv` — **Novo:** Arquivo bruto para carga no Banco de Dados  

---

## 🟢 Passo 3: Banco de Dados e Análise SQL

Esta etapa carrega os dados processados em um banco **PostgreSQL**.

Foi desenvolvido um **orquestrador em Python** que:
- Resolve problemas de permissão de arquivos no Linux (copiando temporariamente para `/tmp`);
- Injeta os caminhos absolutos corretos nos scripts SQL.

### ▶️ Execução

```bash
cd ../3_banco_dados
pip install -r requirements.txt
python main.py
```

---

## 🟢 Passo 4: Interface Web e API (Full-Stack)

Esta etapa sobe a **API (Python)** e o **Dashboard (Vue.js)**.  
Você precisará de **dois terminais abertos simultaneamente**.

### 📦 Configuração Inicial
Antes de iniciar os terminais, navegue até a pasta da tarefa e
instale as dependências globais deste módulo:

```bash
cd ../4_interface_web
pip install -r requirements.txt
```

---

### 🐍 Terminal 1: Backend (API)

```bash
cd backend
python main.py
```

- **Documentação e Testes (Swagger):** Acesse `http://localhost:8000/docs` para **visualizar e testar interativamente** 
todas as rotas disponíveis da API:
  - `GET /api/operadoras` — Lista paginada de operadoras  
  - `GET /api/operadoras/{cnpj}` — Detalhes da operadora  
  - `GET /api/operadoras/{cnpj}/despesas` — Histórico de despesas  
  - `GET /api/estatisticas` — KPIs e dados para gráficos

---

### 🎨 Terminal 2: Frontend (Dashboard)

```bash
# Partindo da raiz do projeto
cd 4_interface_web/frontend
npm install        # Instala dependências do Vue, Axios e Chart.js
npm run dev        # Inicia o servidor de desenvolvimento
```

- **Acesso:** O Dashboard estará disponível em `http://localhost:5173/`

- **Funcionalidades:**
  - Tabela paginada  
  - Busca por CNPJ ou Nome  
  - Gráfico de despesas por UF  
  - Modal de detalhes históricos

---

# 🧠 Trade-offs e Decisões Técnicas  
## Documentação Obrigatória

Este documento descreve as principais **decisões técnicas** adotadas no pipeline de dados e na aplicação web, destacando os **trade-offs entre performance, qualidade de dados, simplicidade e escalabilidade**.

---

## 1. Processamento e Extração (ETL)

### ⚡ Processamento: Memória vs. Incremental vs. Stream

**Decisão:** Abordagem híbrida — **Download via Stream + Processamento In-Memory**

**Justificativa:**

- **Download:**  
  Os arquivos ZIP são baixados em *chunks* de 8 KB, reduzindo picos de memória e tornando o processo mais resiliente a falhas de rede.

- **Processamento:**  
  O volume consolidado dos três trimestres, mesmo após descompactação, permanece abaixo de 2 GB.  
  O uso de operações vetorizadas do **Pandas (In-Memory)** é ordens de magnitude mais rápido do que abordagens baseadas em disco ou frameworks distribuídos (ex: Spark) para este cenário.

---

### 📅 Inconsistência de Datas

- **Problema:**  
  A coluna de data nos CSVs originais apresenta múltiplos formatos inconsistentes (`1T2024`, `01/01/2024`, `jan/24`).

- **Decisão:**  
  Ignorar a data interna dos arquivos.

- **Solução:**  
  Utilizar a estrutura de diretórios do FTP da ANS como *Source of Truth*, injetando programaticamente as colunas **Ano** e **Trimestre**.

- **Benefício:**  
  Elimina ambiguidades e garante consistência temporal **100% confiável**.

---

## 2. Transformação e Enriquecimento

### 🔗 Estratégia de Join e Integridade (RegistroANS)

- **Decisão:**  
  Utilizar **RegistroANS** como chave primária de ligação, com `pandas.merge` (*Hash Join*).

- **Problema:**  
  Os arquivos contábeis não possuem CNPJ, apenas o identificador **REG_ANS**.

- **Solução:**  
  O pipeline foi dividido:
  - **Tarefa 1:** Extração fiel do dado contábil.
  - **Tarefa 2:** Camada de *Trusted Data*, baixando o **CADOP oficial** e realizando um **Left Join**.

- **Benefício:**  
  Garante integridade referencial sem depender de dados inexistentes na fonte.

---

### 🧾 Tratamento de CNPJs Inválidos

- **Trade-off:** Fidelidade contábil vs. pureza cadastral  
- **Decisão:** Manter os registros, mas gerar **log de auditoria**.

**Justificativa:**  
Remover linhas distorceria o balanço contábil total do setor.  
Optou-se por manter o dado financeiro correto, delegando a limpeza cadastral para a camada de visualização.

---

### 🔢 Tratamento de Valores Zerados

- **Decisão:** Filtragem rigorosa — `valor > 0`

**Justificativa:**  
Valores negativos (estornos) ou nulos distorcem métricas estatísticas como **média** e **desvio padrão**, centrais para a análise solicitada.

---

### 📉 Estratégia de Ordenação

- **Decisão:** Ordenação em memória com `df.sort_values` (Quicksort interno)

**Justificativa:**  
O custo computacional da ordenação em memória para o dataset agregado (milhares de linhas) é desprezível, não justificando o uso de banco de dados apenas para essa etapa.

---

## 3. Banco de Dados (SQL)

### 🏗️ Modelagem: Normalização — Opção A vs. Opção B

**Decisão:** Opção B — **Modelo Normalizado (Star Schema)**

- **Tabela Dimensão:** `operadoras` (dados cadastrais)  
- **Tabela Fato:** `despesas_contabeis` (eventos financeiros)

**Justificativa:**

- **Volume:**  
  As despesas crescem exponencialmente, enquanto os dados cadastrais são estáveis.  
  Evita repetição massiva de strings (ex: *Razão Social*), economizando I/O.

- **Manutenibilidade:**  
  Atualizações cadastrais exigem alteração em apenas uma linha (**ACID**).

---

### 💲 Tipos de Dados: DECIMAL vs. FLOAT

- **Decisão:** `DECIMAL(15,2)`

**Justificativa:**  
Tipos `FLOAT` utilizam ponto flutuante binário (IEEE 754), introduzindo erros de precisão  
(ex: `0.1 + 0.2 ≠ 0.3`).  
Para dados financeiros, **precisão exata é obrigatória**.

---

### 🗓️ Tipos de Dados: DATE vs. VARCHAR

- **Decisão:** `DATE`

**Justificativa:**  
Permite ordenação cronológica correta e uso eficiente de indexação.  
O trimestre foi convertido para o primeiro dia do mês correspondente  
(ex: 1º tri → `2023-01-01`).

---

## 4. Queries Analíticas

### 🧠 Lógica Analítica (Query 3)

- **Decisão:** Uso de **CTEs (Common Table Expressions)** + agregação com `HAVING`

**Justificativa:**  
CTEs tornam a query **linear e autodocumentável**.  
O *Query Planner* do PostgreSQL materializa as CTEs de forma eficiente, evitando recálculos redundantes da média global.

---

## 5. Interface Web e API (Full-Stack)

Abaixo estão as justificativas para as decisões arquiteturais adotadas no **Backend** e **Frontend**, conforme solicitado na **Tarefa 4**.

---

### 🏗️ 4.2.1. Escolha do Framework Backend

- **Decisão:** Opção B — **FastAPI**

**Justificativa:**

- **Performance:**  
  Utiliza o padrão **ASGI (assíncrono)**, lidando com requisições de I/O de forma não-bloqueante, sendo significativamente mais rápido que o Flask.

- **Segurança:**  
  O uso do **Pydantic** garante tipagem forte e validação automática de dados.

- **Documentação:**  
  Gera nativamente o **Swagger UI** (`/docs`), facilitando testes e atendendo aos requisitos do desafio.

---

### 📄 4.2.2. Estratégia de Paginação

- **Decisão:** Opção A — **Offset-based** (`LIMIT + OFFSET`)

**Justificativa:**

- **UX:**  
  Em dashboards administrativos, o usuário espera poder pular páginas  
  (ex: “Ir para a página 5”).

- **Performance:**  
  Dado o volume de dados (milhares de registros), o custo do `OFFSET` é desprezível.  
  A complexidade do *Cursor-based* não se justifica neste contexto.

---

### 🚀 4.2.3. Cache vs. Queries Diretas

- **Decisão:** Opção A — **Query Direta**

**Justificativa:**

- **Estabilidade:**  
  Os dados da ANS mudam trimestralmente e permanecem estáticos durante o uso da aplicação.

- **Simplicidade:**  
  O PostgreSQL executa essas agregações em milissegundos.  
  Adicionar Redis ou tabelas pré-calculadas seria **overengineering**.

---

### 📦 4.2.4. Estrutura de Resposta da API

- **Decisão:** Opção B — **Dados + Metadados**

```json
{ "data": [...], "total": 100 }
```
- **Justificativa:** Para que o Frontend possa renderizar os controles
de paginação corretamente (ex: saber quando desabilitar o botão "Próximo"), 
 ele precisa conhecer o total de registros disponíveis no banco.

## 🔍 4.3.1. Estratégia de Busca/Filtro (Frontend)

- **Decisão:** Opção A — **Busca no Servidor**

- **Justificativa:**
  - **Escalabilidade:** Filtrar no cliente exigiria baixar todo o banco de dados para o navegador, o que é inviável (alto payload).
  - **Performance:** A busca no servidor utiliza índices do banco (`ILIKE`), economizando banda e processamento do usuário.

---

## 🧩 4.3.2. Gerenciamento de Estado

- **Decisão:** Opção C — **Composables / Reactivity API (Vue 3)**

- **Justificativa:**  
  A aplicação possui um escopo focado (dashboard único).  
  Utilizar bibliotecas globais como **Vuex** ou **Pinia** adicionaria *boilerplate* desnecessário.  
  Variáveis reativas (`ref`) são suficientes, simples e modulares para este cenário.

---

## ⚡ 4.3.3. Performance da Tabela

- **Decisão:** **Paginação no Servidor**

- **Justificativa:**  
  Renderizar milhares de linhas no DOM degrada significativamente a performance do navegador.  
  Ao paginar no servidor (trazendo 10 itens por vez), a interface permanece fluida independentemente do tamanho do banco.

---

## 🛡️ 4.3.4. Tratamento de Erros e Loading

### Implementação

- **Loading:**  
  Feedback visual ("Carregando...") durante requisições assíncronas.

- **Erros:**  
  Blocos `try/catch` capturam falhas de rede e exibem alertas no console.

- **Dados Vazios:**  
  Tratamento explícito para buscas sem resultados  
  ("Nenhum registro encontrado"), evitando telas em branco confusas.

---

## 🛠 Tecnologias Utilizadas

### 🔤 Linguagens e Bibliotecas

- **Python 3.10+**
- **pandas** — Manipulação de dados e agregações
- **requests / BeautifulSoup** — Scraping e download de arquivos
- **psycopg2 / SQLAlchemy** — Conectividade com banco de dados
- **FastAPI / Uvicorn** — API e servidor assíncrono
- **Vue.js 3 / Vite** — Frontend e build tool

---

### 🗄️ Banco de Dados

- **PostgreSQL 14+**  
  Banco de dados relacional utilizado para armazenamento, modelagem e análises analíticas.

---

