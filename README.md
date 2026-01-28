# Intuitive Care - Desafio Técnico (Estágio)

Este repositório contém a solução Full-Stack para o desafio técnico da Intuitive Care, estruturada como um **Monorepo** que abrange todo o ciclo de vida dos dados: Engenharia de Dados (ETL), Enriquecimento (Data Enrichment), Banco de Dados (SQL) e Desenvolvimento Web (Vue.js + Python).

## 📂 Estrutura do Projeto

O projeto foi organizado em módulos independentes que funcionam como um Pipeline de Dados sequencial:

* **`1_etl_ans/`**: **(Tarefa 1)** Scripts de extração (`Extract`) responsáveis por varrer o site da ANS, baixar e consolidar os dados brutos contábeis.
* **`2_transformacao/`**: **(Tarefa 2)** Scripts de transformação (`Transform`) que enriquecem os dados cruzando com o cadastro oficial (CADOP), validam regras de negócio e geram as agregações estatísticas.
* **`2_banco_dados/`**: **(Tarefa 3)** Scripts SQL para modelagem do banco de dados relacional e queries analíticas.
* **`3_interface_web/`**: **(Tarefa 4)** Aplicação Web (Frontend Vue.js + Backend Python) para visualização dos dados processados.

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

### Entrada
- Dados públicos do site da ANS  
  (<https://dadosabertos.ans.gov.br/>)

### Saída
- `output/consolidado_despesas.csv`

### Nota
Este arquivo mantém a coluna **RegistroANS** como chave primária e preenche **CNPJ** e **Razão Social** com `"N/A"`, pois os arquivos contábeis originais não possuem essas informações.

### Passo 2: Transformação, Enriquecimento e Validação
Este script lê o arquivo bruto gerado no passo anterior, baixa o Cadastro de Operadoras (CADOP), realiza o cruzamento de dados, aplica validações e gera estatísticas.

```bash
cd 1_etl_ans
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


# 🧠 Trade-offs e Decisões Técnicas  
**(Documentação Obrigatória)**

Este documento descreve as principais decisões técnicas adotadas no pipeline de dados e suas justificativas.

---

## 1. Estratégia de Join e Integridade Referencial  
### 📌 Uso do *RegistroANS*

### Decisão
Utilizar o **RegistroANS** como chave de ligação entre a etapa de extração e a de enriquecimento dos dados.

### Justificativa
Os arquivos de demonstrações contábeis da ANS não possuem **CNPJ** nem **Razão Social**, apenas o identificador `REG_ANS`. Assim, qualquer validação cadastral na etapa inicial seria inviável.

### Solução
- **Tarefa 1:** extração fiel dos dados contábeis, preservando o `RegistroANS`.
- **Tarefa 2:** enriquecimento com o **Cadastro de Operadoras (CADOP)** oficial da ANS, via **Left Join**.

### Benefício
Garante que os dados cadastrais utilizados sejam oficiais e elimina inconsistências causadas por erros manuais.

---

## 2. Validação e Tratamento de Inconsistências

### Datas
Os arquivos apresentavam múltiplos formatos de data.  
**Solução:** a data interna foi ignorada, utilizando-se a estrutura de diretórios da ANS como *Source of Truth* para definir **Ano** e **Trimestre**.

### Valores Zerados ou Negativos
Registros com `Valor ≤ 0` foram removidos.  
**Justificativa:** estornos e valores nulos distorcem métricas estatísticas e não agregam valor à análise de despesas.

### CNPJs Inválidos
A validação ocorre após o enriquecimento.  
CNPJs inválidos são **logados**, mas mantidos caso possuam valores relevantes, evitando mascarar o volume financeiro real do setor.

---

## 3. Processamento de Dados  
### ⚖️ Memória vs. Stream

### Decisão
Processamento **híbrido**.

- **Download:** via stream (chunks de 8 KB) para evitar consumo excessivo de memória.
- **Processamento:** em memória (Pandas).

### Justificativa
O volume total dos dados (MBs) é plenamente comportável em RAM, tornando o processamento in-memory mais simples e eficiente do que soluções distribuídas como Spark ou Dask para este contexto.

---

## ✅ Conclusão
As decisões priorizam confiabilidade, integridade dos dados e performance adequada ao volume real do problema.

~~## 🛠 Tecnologias Utilizadas

* **Linguagem:** [Python](https://www.python.org/)
* **Bibliotecas Principais:**
    pandas: Manipulação de dados, agregações estatísticas e IO.
    requests: Requisições HTTP e download via stream.
    beautifulsoup4: Web Scraping para mapear diretórios do servidor FTP.
    zipfile / shutil: Manipulação de arquivos compactados e sistema de arquivos.