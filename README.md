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

 - Entrada: Dados do site da ANS (https://dadosabertos.ans.gov.br/).
 - Saída: Arquivo output/consolidado_despesas.csv.
 - Nota: Este arquivo mantém a coluna RegistroANS como chave primária e preenche CNPJ/Razão Social com "N/A", pois os arquivos contábeis originais não possuem esses dados.

### Passo 2: Transformação, Enriquecimento e Validação
Este script lê o arquivo bruto gerado no passo anterior, baixa o Cadastro de Operadoras (CADOP), realiza o cruzamento de dados, aplica validações e gera estatísticas.

```bash
cd 1_etl_ans
cd ../2_transformacao
pip install -r requirements.txt
python main.py
```

 - Entrada: ../1_etl_ans/output/consolidado_despesas.csv.
 - Processamento: 1. Download automático do CADOP (Operadoras Ativas). 2. Join entre tabelas usando RegistroANS. 3. Validação de CNPJs e valores. 4. Cálculo de média trimestral e desvio padrão.
 - Saída: Arquivo output/despesas_agregadas.csv e arquivo ZIP final.

### Trade-offs e Decisões Técnicas (Documentação Obrigatória)
Abaixo estão as justificativas para as abordagens técnicas adotadas, conforme solicitado na avaliação.

1. Estratégia de Join e Integridade Referencial (O Caso "RegistroANS")

Decisão: Utilizar o RegistroANS como chave de ligação (Foreign Key) entre a etapa de extração e a de enriquecimento.

    Problema: Os arquivos CSV de demonstrações contábeis da ANS (fonte primária da Tarefa 1) não possuem as colunas de CNPJ ou Razão Social, apenas o código identificador REG_ANS. Tentar validar CNPJ na primeira etapa seria impossível sem dados externos.

    Solução: O Pipeline foi dividido. A Tarefa 1 foca em extrair o dado contábil fielmente (preservando o RegistroANS). A Tarefa 2 atua como uma camada de "Trusted Data", baixando o Cadastro de Operadoras (CADOP) oficial e realizando um Left Join.

    Benefício: Garante que os dados cadastrais (Razão Social, CNPJ) sejam os oficiais da ANS, eliminando riscos de erros de digitação que poderiam existir nos arquivos contábeis manuais.

2. Validação e Tratamento de Inconsistências

    Datas Inconsistentes: A coluna de data interna dos arquivos CSV originais variava drasticamente de formato (1T2024, 01/01/2024, jan/24).

        Solução: A data interna foi ignorada. O script utiliza a estrutura de diretórios do servidor da ANS (Source of Truth) para injetar as colunas Ano e Trimestre de forma 100% confiável.

    Valores Zerados/Negativos:

        Solução: Filtrados e removidos (Valor > 0). Para fins de análise de volume de despesas, estornos (valores negativos) ou registros nulos não agregam valor estatístico e distorceriam o cálculo da média e do desvio padrão.

    CNPJs Inválidos:

        Solução: A validação ocorre na etapa 2, após o enriquecimento. CNPJs matematicamente inválidos são logados no terminal para auditoria, mas mantidos no relatório final se possuírem valores contábeis relevantes. Remover esses dados mascararia o volume financeiro real do setor.

3. Processamento de Dados (Memória vs. Stream)

Decisão: Processamento híbrido.

    Download: Feito via Stream (chunks de 8KB) para evitar que o download de arquivos grandes lote a memória RAM antes do processamento.

    Processamento: Feito In-Memory (Pandas) acumulando DataFrames em listas.

    Justificativa: Os demonstrativos trimestrais da ANS, mesmo acumulados, possuem volume de dados (MBs) perfeitamente comportável na RAM de computadores modernos, tornando o processamento em memória muito mais rápido do que abordagens em disco (como Spark ou Dask) para este volume específico.


~~## 🛠 Tecnologias Utilizadas

* **Linguagem:** [Python](https://www.python.org/)
* **Bibliotecas Principais:**
    pandas: Manipulação de dados, agregações estatísticas e IO.
    requests: Requisições HTTP e download via stream.
    beautifulsoup4: Web Scraping para mapear diretórios do servidor FTP.
    zipfile / shutil: Manipulação de arquivos compactados e sistema de arquivos.