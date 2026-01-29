# Intuitive Care - Desafio Técnico (Estágio)

Este repositório contém a solução Full-Stack para o desafio técnico da Intuitive Care. O projeto foi estruturado como um **Monorepo** que abrange todo o ciclo de vida dos dados: Engenharia de Dados (ETL), Enriquecimento (Data Enrichment), Banco de Dados (SQL) e Desenvolvimento Web (Vue.js + Python).

## 📂 Estrutura do Projeto

O projeto foi organizado em módulos independentes que funcionam como um Pipeline de Dados sequencial:

* **`1_etl_ans/`** **(Tarefa 1)**
    * *Função:* Extração (`Extract`).
    * *Descrição:* Scripts responsáveis por varrer o site da ANS, baixar e consolidar os dados brutos contábeis.
* **`2_transformacao/`** **(Tarefa 2)**
    * *Função:* Transformação (`Transform`).
    * *Descrição:* Scripts que enriquecem os dados cruzando com o cadastro oficial (CADOP), validam regras de negócio e geram as agregações estatísticas.
* **`2_banco_dados/`** **(Tarefa 3)**
    * *Função:* Modelagem (`Load/Storage`).
    * *Descrição:* Scripts SQL para modelagem do banco de dados relacional e queries analíticas.
* **`3_interface_web/`** **(Tarefa 4)**
    * *Função:* Visualização (`Frontend`).
    * *Descrição:* Aplicação Web (Frontend Vue.js + Backend Python) para visualização dos dados processados.

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

- **Entrada:**  
  Dados do site da ANS  
  https://dadosabertos.ans.gov.br/

- **Saída:**  
  `output/consolidado_despesas.csv`

- **Nota:**  
  O arquivo gerado mantém a coluna **RegistroANS** como **chave primária**.  
  As colunas **CNPJ** e **Razão Social** são preenchidas com `"N/A"`, pois os arquivos contábeis originais não disponibilizam essas informações.

---

## Passo 2: Transformação, Enriquecimento e Validação

- Lê o arquivo bruto gerado no Passo 1.
- Baixa o **Cadastro de Operadoras (CADOP)**.
- Realiza o **cruzamento dos dados** pelo campo **RegistroANS**.
- Enriquece os registros com **CNPJ** e **Razão Social**.
- Aplica **validações de consistência** nos dados.
- Gera **estatísticas e métricas** para análise final.


```bash
# Partindo da pasta anterior (1_etl_ans)
cd ../2_transformacao
pip install -r requirements.txt
python main.py
```

 ## 4. Fluxo de Processamento — Tarefa 2

### Entrada
- `../1_etl_ans/output/consolidado_despesas.csv`

### Processamento
- Download automático do **CADOP (Operadoras Ativas)**.
- Join entre as tabelas utilizando o **RegistroANS**.
- Validação de **CNPJs** e **valores contábeis**.
- Cálculo de **média trimestral** e **desvio padrão**.

### Saída
- `output/despesas_agregadas.csv`
- Arquivo **ZIP** final com os resultados.


## 🧠 Trade-offs e Decisões Técnicas (Documentação Obrigatória)

Abaixo estão as justificativas para as abordagens técnicas adotadas, conforme solicitado na avaliação.

---

## 1. Estratégia de Join e Integridade Referencial

### 🔗 Decisão (Chave de Ligação)
**Utilizar o RegistroANS como chave (Foreign Key) em vez do CNPJ.**

**Justificativa:**  
Os arquivos contábeis brutos da ANS (fonte primária) não contêm o campo **CNPJ**. Dessa forma, qualquer tentativa de realizar o *join* por CNPJ seria inviável na etapa inicial do pipeline.  
O **RegistroANS** é o identificador único, oficial e imutável garantido pela própria agência reguladora, sendo a escolha mais segura para garantir integridade referencial.

---

### ⚙️ Decisão (Processamento do Join)
**Utilização de `pandas.merge` (Hash Join em memória).**

**Justificativa:**  
O volume de dados consolidado (3 trimestres) somado ao Cadastro de Operadoras (≈ 1.200 registros) cabe confortavelmente em memória RAM (< 1 GB).  
Nessas condições, o processamento em memória é **ordens de magnitude mais rápido** do que o uso de bancos de dados intermediários ou frameworks distribuídos, que introduziriam complexidade desnecessária.

---

### 📎 Tratamento de Registros “Sem Match”
**Utilização de Left Join.**

**Justificativa:**  
A prioridade do projeto é preservar a **integridade dos dados financeiros**.  
Caso uma operadora possua despesas registradas, mas não esteja presente no cadastro ativo (por exemplo, operadora extinta ou com status alterado), o registro financeiro é mantido e a **Razão Social é preenchida como "Desconhecida"**.  
Essa abordagem evita a perda de informações e garante que o total consolidado de despesas permaneça correto.

---

## 2. Validação e Tratamento de Inconsistências

### 💰 Valores Zerados ou Negativos
**Solução:** Filtragem dos registros com `Valor > 0`.

**Justificativa:**  
Valores zerados, nulos ou negativos geralmente representam estornos ou lançamentos não efetivos.  
Manter esses registros distorceria métricas estatísticas como **média** e **desvio padrão**, comprometendo a análise financeira.

---

### 🧾 CNPJs Inválidos
**Solução:** Validação na etapa 2 (pós-enriquecimento) com *logging* para auditoria.

**Justificativa:**  
CNPJs matematicamente inválidos são registrados em log, mas **não removidos do relatório final**.  
A exclusão desses dados mascararia o volume financeiro real do setor, o que seria um erro crítico em uma análise contábil e regulatória.

---

## 3. Estratégia de Ordenação e Agregação

### 📊 Decisão de Ordenação
**Uso de `sort_values` (Quicksort) em memória.**

**Justificativa:**  
Após a agregação (por Operadora e UF), o dataset final contém apenas **alguns milhares de linhas**.  
Algoritmos de ordenação em memória com complexidade **O(N log N)** são praticamente instantâneos nesse cenário, tornando desnecessárias técnicas como *external sort* ou indexação em banco de dados.

---

### 📈 Métricas Estatísticas Escolhidas
Além da **soma total de despesas**, foram calculadas:

- **Média Trimestral**
- **Desvio Padrão**

**Objetivo:**  
Identificar operadoras com **volatilidade financeira atípica**, como gastos concentrados em um único trimestre, o que pode indicar eventos extraordinários ou inconsistências operacionais.

---

## 🛠 Tecnologias Utilizadas

### 🔤 Linguagem
- **Python 3.10+**

### 📚 Bibliotecas Principais
- **pandas**: Manipulação de dados, agregações estatísticas e operações de entrada/saída (IO).
- **requests**: Requisições HTTP e download de arquivos via *stream*.
- **zipfile / shutil**: Manipulação e extração de arquivos compactados.
