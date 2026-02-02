-- QUERY 1: Top 5 operadoras com maior crescimento percentual
WITH limites AS (
    SELECT
        d.registro_ans,
        o.razao_social,
        FIRST_VALUE(d.valor_despesa) OVER (PARTITION BY d.registro_ans ORDER BY d.data_referencia) as valor_inicial,
        FIRST_VALUE(d.valor_despesa) OVER (PARTITION BY d.registro_ans ORDER BY d.data_referencia DESC) as valor_final
    FROM despesas_contabeis d
    JOIN operadoras o ON d.registro_ans = o.registro_ans
)
SELECT DISTINCT
    registro_ans,
    razao_social,
    valor_inicial,
    valor_final,
    ROUND(((valor_final - valor_inicial) / NULLIF(valor_inicial, 0)) * 100, 2) as crescimento_pct
FROM limites
WHERE valor_inicial > 0
ORDER BY crescimento_pct DESC
LIMIT 5;

-- QUERY 2: Top 5 Estados + Média por operadora
SELECT
    o.uf,
    SUM(d.valor_despesa) as despesa_total_estado,
    ROUND(SUM(d.valor_despesa) / COUNT(DISTINCT d.registro_ans), 2) as media_por_operadora
FROM despesas_contabeis d
JOIN operadoras o ON d.registro_ans = o.registro_ans
WHERE o.uf IS NOT NULL
GROUP BY o.uf
ORDER BY despesa_total_estado DESC
LIMIT 5;

-- QUERY 3: Operadoras acima da média em 2+ trimestres
WITH media_trimestral AS (
    SELECT ano, trimestre, AVG(valor_despesa) as media_geral
    FROM despesas_contabeis
    GROUP BY ano, trimestre
),
performance AS (
    SELECT
        d.registro_ans,
        CASE WHEN d.valor_despesa > m.media_geral THEN 1 ELSE 0 END as superou_media
    FROM despesas_contabeis d
    JOIN media_trimestral m ON d.ano = m.ano AND d.trimestre = m.trimestre
)
SELECT
    p.registro_ans,
    o.razao_social,
    SUM(p.superou_media) as qtd_trimestres_acima
FROM performance p
JOIN operadoras o ON p.registro_ans = o.registro_ans
GROUP BY p.registro_ans, o.razao_social
HAVING SUM(p.superou_media) >= 2;