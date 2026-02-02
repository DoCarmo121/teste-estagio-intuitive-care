-- 1. Tabela de Dimensão: OPERADORAS
CREATE TABLE IF NOT EXISTS operadoras (
    registro_ans INT PRIMARY KEY,
    cnpj VARCHAR(20),
    razao_social VARCHAR(255),
    modalidade VARCHAR(100),
    uf CHAR(2)
);

-- 2. Tabela de Fato: DESPESAS_CONTABEIS
CREATE TABLE IF NOT EXISTS despesas_contabeis (
    id SERIAL PRIMARY KEY,
    registro_ans INT NOT NULL,
    ano INT NOT NULL,
    trimestre INT NOT NULL,
    data_referencia DATE NOT NULL,
    valor_despesa DECIMAL(15, 2) NOT NULL,
    CONSTRAINT fk_operadora FOREIGN KEY (registro_ans) REFERENCES operadoras(registro_ans)
);

-- Índices
CREATE INDEX idx_despesas_ano_tri ON despesas_contabeis(ano, trimestre);
CREATE INDEX idx_despesas_operadora ON despesas_contabeis(registro_ans);

-- 3. Tabela Agregada (Data Mart)
CREATE TABLE IF NOT EXISTS despesas_agregadas_final (
    registro_ans INT,
    cnpj VARCHAR(20),
    razao_social VARCHAR(255),
    uf CHAR(2),
    valor_total DECIMAL(15, 2),
    media_trimestral DECIMAL(15, 2),
    desvio_padrao DECIMAL(15, 2)
);