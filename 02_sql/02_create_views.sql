-- =============================================================
-- 02_create_views.sql
-- Vistas para consumo en Power BI y análisis en Python
-- Motor: PostgreSQL 15+
--
-- Ejecutar después de 01_create_schema.sql y cargar los datos
-- =============================================================

SET search_path TO retail, public;

-- =============================================================
-- v_ventas_enriquecidas
-- Vista principal que Power BI conecta directamente.
-- Une fact_ventas con todas las dimensiones e indicadores.
-- =============================================================
DROP VIEW IF EXISTS v_ventas_enriquecidas CASCADE;

CREATE VIEW v_ventas_enriquecidas AS
SELECT
    -- Hechos
    fv.venta_id,
    fv.cantidad,
    fv.precio_unitario_clp,
    fv.descuento_pct,
    fv.monto_total_clp,
    fv.canal_venta,
    fv.metodo_pago,

    -- Margen bruto calculado
    fv.monto_total_clp - (dp.costo_unitario_clp * fv.cantidad) AS margen_bruto_clp,
    ROUND(
        (fv.monto_total_clp - dp.costo_unitario_clp * fv.cantidad)::NUMERIC
        / NULLIF(fv.monto_total_clp, 0) * 100, 2
    )                                                           AS margen_bruto_pct,

    -- Precio en UF (para análisis de valor real)
    ROUND(fv.monto_total_clp / NULLIF(ie.uf, 0), 4)            AS monto_total_uf,

    -- Dimensión tiempo
    dt.fecha,
    dt.año,
    dt.trimestre,
    dt.mes,
    dt.nombre_mes,
    dt.nombre_dia_semana,
    dt.es_fin_semana,
    dt.es_feriado,
    dt.evento_comercial,
    dt.semana_año,

    -- Dimensión producto
    dp.producto_id,
    dp.sku,
    dp.nombre              AS producto_nombre,
    dp.categoria,
    dp.subcategoria,
    dp.marca,
    dp.precio_lista_clp,
    dp.es_importado,
    dp.pais_origen,

    -- Dimensión cliente
    dc.cliente_id,
    dc.nombre              AS cliente_nombre,
    dc.region,
    dc.comuna,
    dc.segmento_rfm,
    dc.canal_adquisicion,
    dc.fecha_registro,

    -- Indicadores económicos del día de la compra
    ie.uf,
    ie.dolar,
    ie.euro,
    ie.ipc_mensual,
    ie.tasa_desempleo,
    ie.imacec

FROM fact_ventas           fv
JOIN dim_tiempo            dt ON fv.fecha_id    = dt.fecha_id
JOIN dim_producto          dp ON fv.producto_id = dp.producto_id
JOIN dim_cliente           dc ON fv.cliente_id  = dc.cliente_id
LEFT JOIN dim_indicadores_economicos ie ON fv.fecha_id = ie.fecha_id;

COMMENT ON VIEW v_ventas_enriquecidas IS
    'Vista principal para Power BI y EDA. Une fact_ventas con todas las dimensiones e indicadores del día.';


-- =============================================================
-- v_kpis_diarios
-- Agregación diaria: métricas de negocio + indicadores macro.
-- Ideal para gráficos de línea en Power BI (ventas vs dólar).
-- =============================================================
DROP VIEW IF EXISTS v_kpis_diarios CASCADE;

CREATE VIEW v_kpis_diarios AS
SELECT
    dt.fecha,
    dt.año,
    dt.trimestre,
    dt.mes,
    dt.nombre_mes,
    dt.nombre_dia_semana,
    dt.es_fin_semana,
    dt.es_feriado,
    dt.evento_comercial,

    -- KPIs de ventas
    COUNT(fv.venta_id)                                          AS numero_ordenes,
    COALESCE(SUM(fv.monto_total_clp), 0)                        AS ventas_totales_clp,
    COALESCE(SUM(fv.cantidad), 0)                               AS unidades_vendidas,
    COUNT(DISTINCT fv.cliente_id)                               AS clientes_unicos,
    ROUND(AVG(fv.monto_total_clp), 0)                           AS ticket_promedio_clp,
    ROUND(AVG(fv.descuento_pct) * 100, 2)                       AS descuento_promedio_pct,

    -- Margen bruto del día
    COALESCE(
        SUM(fv.monto_total_clp - dp.costo_unitario_clp * fv.cantidad), 0
    )                                                           AS margen_bruto_clp,

    -- Indicadores económicos del día
    ie.uf,
    ie.dolar,
    ie.euro,
    ie.ipc_mensual,
    ie.tasa_desempleo,
    ie.imacec

FROM dim_tiempo dt
LEFT JOIN fact_ventas fv
    ON dt.fecha_id = fv.fecha_id
LEFT JOIN dim_producto dp
    ON fv.producto_id = dp.producto_id
LEFT JOIN dim_indicadores_economicos ie
    ON dt.fecha_id = ie.fecha_id
GROUP BY
    dt.fecha, dt.año, dt.trimestre, dt.mes, dt.nombre_mes,
    dt.nombre_dia_semana, dt.es_fin_semana, dt.es_feriado,
    dt.evento_comercial,
    ie.uf, ie.dolar, ie.euro, ie.ipc_mensual, ie.tasa_desempleo, ie.imacec
ORDER BY dt.fecha;

COMMENT ON VIEW v_kpis_diarios IS
    'Un registro por día con KPIs de negocio e indicadores macro. Base para gráfico ventas vs dólar.';


-- =============================================================
-- v_rfm_segmentacion
-- Cálculo RFM completo por cliente con scores y segmento.
-- Fecha de corte: último día del período (2025-12-31).
-- =============================================================
DROP VIEW IF EXISTS v_rfm_segmentacion CASCADE;

CREATE VIEW v_rfm_segmentacion AS
WITH ventas_base AS (
    SELECT
        fv.cliente_id,
        MAX(dt.fecha)              AS ultima_compra,
        COUNT(fv.venta_id)         AS frecuencia,
        SUM(fv.monto_total_clp)    AS monetario
    FROM fact_ventas fv
    JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
    GROUP BY fv.cliente_id
),
rfm_scores AS (
    SELECT
        vb.cliente_id,
        dc.nombre            AS cliente_nombre,
        dc.region,
        dc.segmento_rfm,
        vb.ultima_compra,
        -- Recency: días desde la última compra
        DATE '2025-12-31' - vb.ultima_compra                   AS recency_dias,
        vb.frecuencia,
        vb.monetario,
        -- Scores 1-5 por quintil
        NTILE(5) OVER (ORDER BY (DATE '2025-12-31' - vb.ultima_compra) DESC) AS r_score,
        NTILE(5) OVER (ORDER BY vb.frecuencia)                               AS f_score,
        NTILE(5) OVER (ORDER BY vb.monetario)                                AS m_score
    FROM ventas_base vb
    JOIN dim_cliente dc ON vb.cliente_id = dc.cliente_id
)
SELECT
    cliente_id,
    cliente_nombre,
    region,
    segmento_rfm,
    ultima_compra,
    recency_dias,
    frecuencia,
    monetario,
    r_score,
    f_score,
    m_score,
    -- RFM Score compuesto (100*R + 10*F + M)
    r_score * 100 + f_score * 10 + m_score                     AS rfm_score_compuesto,
    -- Ticket promedio
    ROUND(monetario::NUMERIC / NULLIF(frecuencia, 0), 0)        AS ticket_promedio_clp,
    -- Categoría de valor
    CASE
        WHEN r_score >= 4 AND f_score >= 4              THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3              THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2              THEN 'New'
        WHEN r_score >= 3 AND f_score <= 2              THEN 'Potential'
        WHEN r_score = 2                                THEN 'At Risk'
        WHEN r_score = 1 AND f_score >= 3               THEN 'Hibernating'
        ELSE                                                 'Lost'
    END                                                         AS segmento_calculado
FROM rfm_scores
ORDER BY rfm_score_compuesto DESC;

COMMENT ON VIEW v_rfm_segmentacion IS
    'RFM completo por cliente. Fecha de corte 2025-12-31. Scores 1-5 por quintil.';


-- =============================================================
-- v_pareto_productos
-- Ranking de productos con % acumulado de ventas (regla 80/20).
-- Ideal para el gráfico de Pareto en Power BI.
-- =============================================================
DROP VIEW IF EXISTS v_pareto_productos CASCADE;

CREATE VIEW v_pareto_productos AS
WITH ventas_por_producto AS (
    SELECT
        dp.producto_id,
        dp.sku,
        dp.nombre           AS producto_nombre,
        dp.categoria,
        dp.subcategoria,
        dp.marca,
        dp.precio_lista_clp,
        COUNT(fv.venta_id)  AS numero_ventas,
        SUM(fv.cantidad)    AS unidades_vendidas,
        SUM(fv.monto_total_clp)                                 AS ventas_totales_clp,
        SUM(fv.monto_total_clp - dp.costo_unitario_clp * fv.cantidad) AS margen_bruto_clp
    FROM dim_producto dp
    LEFT JOIN fact_ventas fv ON dp.producto_id = fv.producto_id
    GROUP BY
        dp.producto_id, dp.sku, dp.nombre, dp.categoria,
        dp.subcategoria, dp.marca, dp.precio_lista_clp
),
total AS (
    SELECT SUM(ventas_totales_clp) AS total_ventas FROM ventas_por_producto
)
SELECT
    vp.producto_id,
    vp.sku,
    vp.producto_nombre,
    vp.categoria,
    vp.subcategoria,
    vp.marca,
    vp.precio_lista_clp,
    vp.numero_ventas,
    vp.unidades_vendidas,
    vp.ventas_totales_clp,
    vp.margen_bruto_clp,
    ROUND(vp.ventas_totales_clp::NUMERIC / NULLIF(t.total_ventas, 0) * 100, 4)
                                                                AS pct_sobre_total,
    -- % acumulado (para trazar la línea del Pareto)
    ROUND(
        SUM(vp.ventas_totales_clp) OVER (
            ORDER BY vp.ventas_totales_clp DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )::NUMERIC / NULLIF(t.total_ventas, 0) * 100, 4
    )                                                           AS pct_acumulado,
    -- Clasificación ABC
    CASE
        WHEN SUM(vp.ventas_totales_clp) OVER (
            ORDER BY vp.ventas_totales_clp DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )::NUMERIC / NULLIF(t.total_ventas, 0) <= 0.80        THEN 'A'
        WHEN SUM(vp.ventas_totales_clp) OVER (
            ORDER BY vp.ventas_totales_clp DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )::NUMERIC / NULLIF(t.total_ventas, 0) <= 0.95        THEN 'B'
        ELSE                                                        'C'
    END                                                         AS clasificacion_abc,
    RANK() OVER (ORDER BY vp.ventas_totales_clp DESC)           AS ranking
FROM ventas_por_producto vp
CROSS JOIN total t
ORDER BY ranking;

COMMENT ON VIEW v_pareto_productos IS
    'Ranking de productos con % acumulado y clasificación ABC. Base para gráfico Pareto en Power BI.';
