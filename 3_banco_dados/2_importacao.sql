-- Limpa tabelas antes de começar
TRUNCATE TABLE despesas_agregadas_final;
TRUNCATE TABLE despesas_contabeis CASCADE;
TRUNCATE TABLE operadoras CASCADE;

-- 1. CARGA OPERADORAS
CREATE TEMP TABLE staging_cadop (
    registro_ans TEXT, cnpj TEXT, razao_social TEXT, modalidade TEXT, uf TEXT
);

COPY staging_cadop FROM '{PATH_CADOP}'
WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'LATIN1');

INSERT INTO operadoras (registro_ans, cnpj, razao_social, modalidade, uf)
SELECT DISTINCT
    CAST(NULLIF(REGEXP_REPLACE(registro_ans, '\D','','g'), '') AS INTEGER),
    cnpj,
    razao_social,
    modalidade,
    CASE WHEN LENGTH(uf) > 2 THEN LEFT(uf, 2) ELSE NULLIF(uf, 'N/A') END
FROM staging_cadop
WHERE registro_ans IS NOT NULL
ON CONFLICT (registro_ans) DO NOTHING;

-- 2. CARGA DESPESAS
CREATE TEMP TABLE staging_despesas (
    registro_ans TEXT, cnpj TEXT, razao_social TEXT, ano INT, trimestre INT, valor TEXT
);

COPY staging_despesas FROM '{PATH_DESPESAS}'
WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');

INSERT INTO despesas_contabeis (registro_ans, ano, trimestre, data_referencia, valor_despesa)
SELECT
    CAST(NULLIF(REGEXP_REPLACE(s.registro_ans, '\D','','g'), '') AS INTEGER),
    s.ano, s.trimestre,
    MAKE_DATE(s.ano, ((s.trimestre - 1) * 3) + 1, 1),
    CAST(REPLACE(s.valor, ',', '.') AS DECIMAL(15,2))
FROM staging_despesas s
JOIN operadoras o ON CAST(NULLIF(REGEXP_REPLACE(s.registro_ans, '\D','','g'), '') AS INTEGER) = o.registro_ans;

-- 3. CARGA AGREGADA
CREATE TEMP TABLE staging_agregada (
    registro_ans TEXT, cnpj TEXT, razao_social TEXT, uf TEXT,
    valor_total TEXT, media TEXT, desvio TEXT, qtd TEXT
);

COPY staging_agregada FROM '{PATH_AGREGADO}'
WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');

INSERT INTO despesas_agregadas_final
SELECT
    CAST(NULLIF(REGEXP_REPLACE(registro_ans, '\D','','g'), '') AS INTEGER),
    cnpj,
    razao_social,
    LEFT(uf,2),
    CAST(REPLACE(valor_total, ',', '.') AS DECIMAL(15,2)),
    CAST(REPLACE(media, ',', '.') AS DECIMAL(15,2)),
    CAST(REPLACE(desvio, ',', '.') AS DECIMAL(15,2))
FROM staging_agregada;