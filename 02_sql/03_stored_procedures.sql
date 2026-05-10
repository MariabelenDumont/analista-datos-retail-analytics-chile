-- =============================================================
-- 03_stored_procedures.sql
-- Procedimientos almacenados para lógica de negocio en BD
-- Motor: PostgreSQL 15+
-- =============================================================

SET search_path TO retail, public;

-- =============================================================
-- sp_calcular_segmentacion_rfm
-- Recalcula el segmento RFM de todos los clientes activos.
-- Actualiza la columna segmento_rfm en dim_cliente.
-- Solo modifica filas que cambiaron (IS DISTINCT FROM).
-- =============================================================
CREATE OR REPLACE PROCEDURE sp_calcular_segmentacion_rfm(
    p_fecha_corte DATE DEFAULT '2025-12-31'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_actualizados  INTEGER := 0;
    v_inicio        TIMESTAMP := clock_timestamp();
BEGIN
    RAISE NOTICE 'Calculando segmentación RFM con fecha de corte: %', p_fecha_corte;

    WITH rfm_base AS (
        SELECT
            fv.cliente_id,
            MAX(dt.fecha)           AS ultima_compra,
            COUNT(fv.venta_id)      AS frecuencia,
            SUM(fv.monto_total_clp) AS monetario
        FROM fact_ventas fv
        JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
        WHERE dt.fecha <= p_fecha_corte
        GROUP BY fv.cliente_id
    ),
    rfm_scores AS (
        SELECT
            cliente_id,
            NTILE(5) OVER (ORDER BY (p_fecha_corte - ultima_compra) DESC) AS r,
            NTILE(5) OVER (ORDER BY frecuencia)                           AS f,
            NTILE(5) OVER (ORDER BY monetario)                            AS m
        FROM rfm_base
    ),
    rfm_segmentos AS (
        SELECT
            cliente_id,
            CASE
                WHEN r >= 4 AND f >= 4  THEN 'Champions'
                WHEN r >= 3 AND f >= 3  THEN 'Loyal'
                WHEN r >= 4 AND f <= 2  THEN 'New'
                WHEN r >= 3 AND f <= 2  THEN 'Potential'
                WHEN r = 2              THEN 'At Risk'
                WHEN r = 1 AND f >= 3   THEN 'Hibernating'
                ELSE                        'Lost'
            END AS segmento_nuevo
        FROM rfm_scores
    )
    UPDATE dim_cliente dc
    SET    segmento_rfm = rs.segmento_nuevo
    FROM   rfm_segmentos rs
    WHERE  dc.cliente_id = rs.cliente_id
      AND  dc.segmento_rfm IS DISTINCT FROM rs.segmento_nuevo;

    GET DIAGNOSTICS v_actualizados = ROW_COUNT;

    RAISE NOTICE 'RFM completado: % clientes actualizados en % ms.',
        v_actualizados,
        EXTRACT(MILLISECONDS FROM clock_timestamp() - v_inicio)::INTEGER;

    COMMIT;
END;
$$;

COMMENT ON PROCEDURE sp_calcular_segmentacion_rfm IS
    'Recalcula RFM de todos los clientes. Usa IS DISTINCT FROM para actualizar solo filas que cambiaron.';


-- =============================================================
-- sp_reporte_ventas_mensual
-- Reporte ejecutivo de un mes con comparativo YoY.
-- Imprime resultado via RAISE NOTICE (visible en pgAdmin/psql).
-- =============================================================
CREATE OR REPLACE PROCEDURE sp_reporte_ventas_mensual(
    p_año   SMALLINT,
    p_mes   SMALLINT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_ventas_mes        BIGINT;
    v_ventas_mes_ant    BIGINT;
    v_ordenes           INTEGER;
    v_clientes          INTEGER;
    v_ticket_prom       NUMERIC;
    v_top_categoria     VARCHAR(30);
    v_top_canal         VARCHAR(30);
    v_dolar_prom        NUMERIC;
    v_crecimiento_pct   NUMERIC;
BEGIN
    IF p_mes NOT BETWEEN 1 AND 12 THEN
        RAISE EXCEPTION 'Mes inválido: %. Debe ser 1-12.', p_mes;
    END IF;

    -- KPIs del mes solicitado
    SELECT
        COALESCE(SUM(fv.monto_total_clp), 0),
        COUNT(fv.venta_id),
        COUNT(DISTINCT fv.cliente_id),
        ROUND(AVG(fv.monto_total_clp), 0)
    INTO v_ventas_mes, v_ordenes, v_clientes, v_ticket_prom
    FROM fact_ventas fv
    JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
    WHERE dt.año = p_año AND dt.mes = p_mes;

    -- Mismo mes, año anterior
    SELECT COALESCE(SUM(fv.monto_total_clp), 0)
    INTO v_ventas_mes_ant
    FROM fact_ventas fv
    JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
    WHERE dt.año = p_año - 1 AND dt.mes = p_mes;

    v_crecimiento_pct := CASE
        WHEN v_ventas_mes_ant = 0 THEN NULL
        ELSE ROUND((v_ventas_mes - v_ventas_mes_ant)::NUMERIC / v_ventas_mes_ant * 100, 2)
    END;

    -- Categoría top
    SELECT dp.categoria INTO v_top_categoria
    FROM fact_ventas fv
    JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
    JOIN dim_producto dp ON fv.producto_id = dp.producto_id
    WHERE dt.año = p_año AND dt.mes = p_mes
    GROUP BY dp.categoria
    ORDER BY SUM(fv.monto_total_clp) DESC
    LIMIT 1;

    -- Canal top
    SELECT fv.canal_venta INTO v_top_canal
    FROM fact_ventas fv
    JOIN dim_tiempo  dt ON fv.fecha_id = dt.fecha_id
    WHERE dt.año = p_año AND dt.mes = p_mes
    GROUP BY fv.canal_venta
    ORDER BY COUNT(*) DESC
    LIMIT 1;

    -- Dólar promedio del mes
    SELECT ROUND(AVG(ie.dolar), 2) INTO v_dolar_prom
    FROM dim_indicadores_economicos ie
    JOIN dim_tiempo dt ON ie.fecha_id = dt.fecha_id
    WHERE dt.año = p_año AND dt.mes = p_mes;

    RAISE NOTICE '============================================================';
    RAISE NOTICE '  REPORTE EJECUTIVO — %/% (TechStore.cl)', p_mes, p_año;
    RAISE NOTICE '============================================================';
    RAISE NOTICE '  Ventas totales:      $% CLP', TO_CHAR(v_ventas_mes, 'FM999,999,999,999');
    RAISE NOTICE '  Crecimiento YoY:     %%', v_crecimiento_pct;
    RAISE NOTICE '  Número de órdenes:   %', v_ordenes;
    RAISE NOTICE '  Clientes únicos:     %', v_clientes;
    RAISE NOTICE '  Ticket promedio:     $% CLP', TO_CHAR(v_ticket_prom, 'FM999,999,999');
    RAISE NOTICE '  Categoría top:       %', v_top_categoria;
    RAISE NOTICE '  Canal top:           %', v_top_canal;
    RAISE NOTICE '  Dólar promedio mes:  $% CLP', v_dolar_prom;
    RAISE NOTICE '============================================================';
END;
$$;

COMMENT ON PROCEDURE sp_reporte_ventas_mensual IS
    'Reporte ejecutivo mensual: ventas, YoY, ticket, top categoría/canal, dólar promedio.';


-- =============================================================
-- Ejemplos de uso
-- =============================================================

/*
-- Recalcular segmentación RFM
CALL retail.sp_calcular_segmentacion_rfm('2025-12-31');

-- Reporte de noviembre 2025 (Black Friday)
CALL retail.sp_reporte_ventas_mensual(2025, 11);

-- Reporte de junio 2024 (CyberDay)
CALL retail.sp_reporte_ventas_mensual(2024, 6);
*/
