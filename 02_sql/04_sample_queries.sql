-- =============================================================
-- 04_sample_queries.sql
-- Consultas de ejemplo para análisis y demostración
-- Motor: PostgreSQL 15+
-- Incluir en el README del portfolio
-- =============================================================

SET search_path TO retail, public;

-- =============================================================
-- BLOQUE 1 — Ventas vs Indicadores Económicos
-- Demuestra la correlación central del proyecto
-- =============================================================

-- 1.1 Promedio de ventas mensuales vs dólar promedio
SELECT
    dt.año,
    dt.mes,
    dt.nombre_mes,
    ROUND(AVG(ie.dolar), 2)                      AS dolar_promedio,
    SUM(fv.monto_total_clp)                       AS ventas_totales_clp,
    COUNT(fv.venta_id)                            AS numero_ordenes,
    ROUND(AVG(fv.monto_total_clp), 0)             AS ticket_promedio_clp
FROM fact_ventas fv
JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
JOIN dim_indicadores_economicos ie ON fv.fecha_id = ie.fecha_id
GROUP BY dt.año, dt.mes, dt.nombre_mes
ORDER BY dt.año, dt.mes;


SET search_path TO retail, public;
-- 1.2 Impacto del dólar en ventas de productos importados
-- Agrupa días en 4 rangos de dólar y compara ventas
SELECT
    CASE
        WHEN ie.dolar < 900  THEN 'Dólar bajo (<$900)'
        WHEN ie.dolar < 950  THEN 'Dólar medio-bajo ($900-$950)'
        WHEN ie.dolar < 1000 THEN 'Dólar medio-alto ($950-$1.000)'
        ELSE                      'Dólar alto (>$1.000)'
    END                                           AS rango_dolar,
    COUNT(DISTINCT dt.fecha)                      AS dias_en_rango,
    COUNT(fv.venta_id)                            AS ordenes_totales,
    ROUND(COUNT(fv.venta_id)::NUMERIC
        / NULLIF(COUNT(DISTINCT dt.fecha), 0), 1) AS ordenes_por_dia,
    ROUND(AVG(fv.monto_total_clp), 0)             AS ticket_promedio_clp
FROM dim_tiempo dt
LEFT JOIN fact_ventas fv ON dt.fecha_id = fv.fecha_id
LEFT JOIN dim_indicadores_economicos ie ON dt.fecha_id = ie.fecha_id
JOIN dim_producto dp ON fv.producto_id = dp.producto_id
WHERE dp.es_importado = TRUE
GROUP BY rango_dolar
ORDER BY MIN(ie.dolar);


-- =============================================================
-- BLOQUE 2 — Estacionalidad y Eventos Comerciales
-- =============================================================
SET search_path TO retail, public;
-- 2.1 Performance por evento comercial (ventas vs día normal)
WITH dias_normales AS (
    SELECT
        ROUND(COUNT(fv.venta_id)::NUMERIC
            / NULLIF(COUNT(DISTINCT dt.fecha_id), 0), 2) AS ordenes_dia_normal
    FROM dim_tiempo dt
    LEFT JOIN fact_ventas fv ON dt.fecha_id = fv.fecha_id
    WHERE dt.evento_comercial = 'Normal'
)
SELECT
    dt.evento_comercial,
    COUNT(DISTINCT dt.fecha_id)                   AS dias_activos,
    COUNT(fv.venta_id)                            AS ordenes_totales,
    ROUND(COUNT(fv.venta_id)::NUMERIC
        / NULLIF(COUNT(DISTINCT dt.fecha_id), 0), 1) AS ordenes_por_dia,
    ROUND(
        COUNT(fv.venta_id)::NUMERIC
        / NULLIF(COUNT(DISTINCT dt.fecha_id), 0)
        / dn.ordenes_dia_normal * 100 - 100, 1
    )                                             AS uplift_vs_normal_pct,
    ROUND(AVG(fv.descuento_pct) * 100, 2)         AS descuento_promedio_pct,
    SUM(fv.monto_total_clp)                       AS ventas_totales_clp
FROM dim_tiempo dt
LEFT JOIN fact_ventas fv ON dt.fecha_id = fv.fecha_id
CROSS JOIN dias_normales dn
GROUP BY dt.evento_comercial, dn.ordenes_dia_normal
ORDER BY ordenes_por_dia DESC;

SET search_path TO retail, public;
-- 2.2 Comparativo año a año por mes (YoY)
SELECT
    dt.mes,
    dt.nombre_mes,
    SUM(CASE WHEN dt.año = 2024 THEN fv.monto_total_clp ELSE 0 END) AS ventas_2024,
    SUM(CASE WHEN dt.año = 2025 THEN fv.monto_total_clp ELSE 0 END) AS ventas_2025,
    ROUND(
        (SUM(CASE WHEN dt.año = 2025 THEN fv.monto_total_clp ELSE 0 END)
       - SUM(CASE WHEN dt.año = 2024 THEN fv.monto_total_clp ELSE 0 END))::NUMERIC
        / NULLIF(SUM(CASE WHEN dt.año = 2024 THEN fv.monto_total_clp ELSE 0 END), 0)
        * 100, 2
    )                                             AS crecimiento_yoy_pct
FROM fact_ventas fv
JOIN dim_tiempo dt ON fv.fecha_id = dt.fecha_id
GROUP BY dt.mes, dt.nombre_mes
ORDER BY dt.mes;


-- =============================================================
-- BLOQUE 3 — Análisis de Clientes
-- =============================================================
SET search_path TO retail, public;
-- 3.1 Distribución de segmentos RFM con métricas
SELECT
    dc.segmento_rfm,
    COUNT(DISTINCT dc.cliente_id)                 AS num_clientes,
    ROUND(COUNT(DISTINCT dc.cliente_id)::NUMERIC
        / SUM(COUNT(DISTINCT dc.cliente_id)) OVER () * 100, 1) AS pct_clientes,
    ROUND(AVG(fv.monto_total_clp), 0)             AS ticket_promedio_clp,
    SUM(fv.monto_total_clp)                       AS ventas_totales_clp,
    ROUND(SUM(fv.monto_total_clp)::NUMERIC
        / SUM(SUM(fv.monto_total_clp)) OVER () * 100, 1) AS pct_ventas
FROM dim_cliente dc
JOIN fact_ventas fv ON dc.cliente_id = fv.cliente_id
GROUP BY dc.segmento_rfm
ORDER BY ventas_totales_clp DESC;

SET search_path TO retail, public;
-- 3.2 Top 10 clientes por valor total (LTV)
SELECT
    dc.cliente_id,
    dc.nombre,
    dc.region,
    dc.segmento_rfm,
    COUNT(fv.venta_id)                            AS total_compras,
    SUM(fv.monto_total_clp)                       AS ltv_clp,
    ROUND(AVG(fv.monto_total_clp), 0)             AS ticket_promedio_clp,
    MIN(dt.fecha)                                 AS primera_compra,
    MAX(dt.fecha)                                 AS ultima_compra
FROM dim_cliente dc
JOIN fact_ventas fv ON dc.cliente_id = fv.cliente_id
JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
GROUP BY dc.cliente_id, dc.nombre, dc.region, dc.segmento_rfm
ORDER BY ltv_clp DESC
LIMIT 10;


-- =============================================================
-- BLOQUE 4 — Análisis de Productos
-- =============================================================
SET search_path TO retail, public;
-- 4.1 Top 20 productos — regla Pareto 80/20
SELECT ranking, sku, producto_nombre, categoria, marca,
       ventas_totales_clp, pct_sobre_total, pct_acumulado, clasificacion_abc
FROM v_pareto_productos
WHERE ranking <= 20;


-- 4.2 Ventas por categoría con margen
SELECT
    dp.categoria,
    COUNT(DISTINCT dp.producto_id)                AS num_productos,
    COUNT(fv.venta_id)                            AS num_ordenes,
    SUM(fv.cantidad)                              AS unidades_vendidas,
    SUM(fv.monto_total_clp)                       AS ventas_totales_clp,
    SUM(fv.monto_total_clp
        - dp.costo_unitario_clp * fv.cantidad)    AS margen_bruto_clp,
    ROUND(
        SUM(fv.monto_total_clp - dp.costo_unitario_clp * fv.cantidad)::NUMERIC
        / NULLIF(SUM(fv.monto_total_clp), 0) * 100, 2
    )                                             AS margen_bruto_pct,
    ROUND(AVG(fv.descuento_pct) * 100, 2)         AS descuento_promedio_pct
FROM fact_ventas fv
JOIN dim_producto dp ON fv.producto_id = dp.producto_id
GROUP BY dp.categoria
ORDER BY ventas_totales_clp DESC;


-- =============================================================
-- BLOQUE 5 — KPIs Ejecutivos
-- =============================================================
SET search_path TO retail, public;
SELECT
    -- Período
    MIN(dt.fecha)                                 AS fecha_inicio,
    MAX(dt.fecha)                                 AS fecha_fin,

    -- Volumen
    COUNT(fv.venta_id)                            AS total_ordenes,
    COUNT(DISTINCT fv.cliente_id)                 AS total_clientes,
    COUNT(DISTINCT fv.producto_id)                AS productos_vendidos,

    -- Ingresos
    SUM(fv.monto_total_clp)                       AS ingresos_totales_clp,
    ROUND(AVG(fv.monto_total_clp), 0)             AS ticket_promedio_clp,
    MAX(fv.monto_total_clp)                       AS venta_maxima_clp,

    -- Margen
    SUM(fv.monto_total_clp
        - dp.costo_unitario_clp * fv.cantidad)    AS margen_bruto_total_clp,
    ROUND(
        SUM(fv.monto_total_clp - dp.costo_unitario_clp * fv.cantidad)::NUMERIC
        / NULLIF(SUM(fv.monto_total_clp), 0) * 100, 2
    )                                             AS margen_bruto_pct,

    -- Descuentos
    ROUND(AVG(fv.descuento_pct) * 100, 2)         AS descuento_promedio_pct,
    COUNT(CASE WHEN fv.descuento_pct > 0 THEN 1 END) AS ordenes_con_descuento

FROM fact_ventas fv
JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
JOIN dim_producto dp ON fv.producto_id = dp.producto_id;