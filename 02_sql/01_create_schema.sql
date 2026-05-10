-- =============================================================
-- 01_create_schema.sql
-- Esquema estrella para Retail Analytics Chile — TechStore.cl
-- Motor: PostgreSQL 15+
--
-- Ejecutar en orden:
--   psql -U postgres -d retail_analytics -f 01_create_schema.sql
-- =============================================================

-- -------------------------------------------------------------
-- Base de datos (ejecutar como superuser si no existe)
-- -------------------------------------------------------------
-- CREATE DATABASE retail_analytics
--     WITH ENCODING = 'UTF8'
--          LC_COLLATE = 'es_CL.UTF-8'
--          LC_CTYPE   = 'es_CL.UTF-8'
--          TEMPLATE   = template0;

-- \c retail_analytics

-- -------------------------------------------------------------
-- Schema
-- -------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS retail;
SET search_path TO retail, public;

-- =============================================================
-- DIMENSIONES
-- =============================================================

-- -------------------------------------------------------------
-- dim_tiempo
-- -------------------------------------------------------------
DROP TABLE IF EXISTS dim_tiempo CASCADE;

CREATE TABLE dim_tiempo (
    fecha_id            INTEGER         PRIMARY KEY,
    fecha               DATE            NOT NULL UNIQUE,
    año                 SMALLINT        NOT NULL,
    trimestre           SMALLINT        NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    mes                 SMALLINT        NOT NULL CHECK (mes BETWEEN 1 AND 12),
    nombre_mes          VARCHAR(20)     NOT NULL,
    dia                 SMALLINT        NOT NULL CHECK (dia BETWEEN 1 AND 31),
    nombre_dia_semana   VARCHAR(15)     NOT NULL,
    numero_dia_semana   SMALLINT        NOT NULL CHECK (numero_dia_semana BETWEEN 1 AND 7),
    es_fin_semana       BOOLEAN         NOT NULL DEFAULT FALSE,
    es_feriado          BOOLEAN         NOT NULL DEFAULT FALSE,
    evento_comercial    VARCHAR(40)     NOT NULL DEFAULT 'Normal',
    semana_año          SMALLINT        NOT NULL
);

COMMENT ON TABLE  dim_tiempo                    IS 'Calendario 2024-2025 con atributos temporales y eventos comerciales chilenos';
COMMENT ON COLUMN dim_tiempo.evento_comercial   IS 'CyberDay | CyberMonday | Black Friday | Navidad | Día de la Madre | Día del Padre | Vuelta al Cole | Fiestas Patrias | Normal';

-- -------------------------------------------------------------
-- dim_producto
-- -------------------------------------------------------------
DROP TABLE IF EXISTS dim_producto CASCADE;

CREATE TABLE dim_producto (
    producto_id         INTEGER         PRIMARY KEY,
    sku                 VARCHAR(20)     NOT NULL UNIQUE,
    nombre              VARCHAR(120)    NOT NULL,
    categoria           VARCHAR(30)     NOT NULL,
    subcategoria        VARCHAR(60)     NOT NULL,
    marca               VARCHAR(50)     NOT NULL,
    precio_lista_clp    INTEGER         NOT NULL CHECK (precio_lista_clp > 0),
    costo_unitario_clp  INTEGER         NOT NULL CHECK (costo_unitario_clp > 0),
    es_importado        BOOLEAN         NOT NULL DEFAULT TRUE,
    pais_origen         VARCHAR(50)
);

COMMENT ON TABLE  dim_producto                  IS '150 SKUs en 5 categorías: Laptops, Smartphones, Accesorios, Gaming, Audio';
COMMENT ON COLUMN dim_producto.categoria        IS 'Laptops | Smartphones | Accesorios | Gaming | Audio';

-- -------------------------------------------------------------
-- dim_cliente
-- -------------------------------------------------------------
DROP TABLE IF EXISTS dim_cliente CASCADE;

CREATE TABLE dim_cliente (
    cliente_id          INTEGER         PRIMARY KEY,
    nombre              VARCHAR(100)    NOT NULL,
    email               VARCHAR(120)    NOT NULL UNIQUE,
    region              VARCHAR(50)     NOT NULL,
    comuna              VARCHAR(60)     NOT NULL,
    segmento_rfm        VARCHAR(20)     NOT NULL DEFAULT 'New',
    fecha_registro      DATE            NOT NULL,
    canal_adquisicion   VARCHAR(40)     NOT NULL
);

COMMENT ON TABLE  dim_cliente                   IS '2.500 clientes en 10 regiones de Chile';
COMMENT ON COLUMN dim_cliente.segmento_rfm      IS 'Champions | Loyal | Potential | New | At Risk | Hibernating | Lost';
COMMENT ON COLUMN dim_cliente.canal_adquisicion IS 'Orgánico | Google Ads | Facebook/Instagram | Referido | Email Marketing | TikTok';

-- -------------------------------------------------------------
-- dim_indicadores_economicos
-- -------------------------------------------------------------
DROP TABLE IF EXISTS dim_indicadores_economicos CASCADE;

CREATE TABLE dim_indicadores_economicos (
    fecha_id            INTEGER         PRIMARY KEY REFERENCES dim_tiempo(fecha_id),
    uf                  NUMERIC(10,2)   NOT NULL,
    dolar               NUMERIC(8,2)    NOT NULL,
    euro                NUMERIC(8,2)    NOT NULL,
    ipc_mensual         NUMERIC(5,2),
    utm                 INTEGER,
    tasa_desempleo      NUMERIC(5,2),
    imacec              NUMERIC(6,2)
);

COMMENT ON TABLE  dim_indicadores_economicos            IS 'Indicadores económicos reales de Chile. Fuente: mindicador.cl (Banco Central)';
COMMENT ON COLUMN dim_indicadores_economicos.uf         IS 'Unidad de Fomento en pesos — diaria';
COMMENT ON COLUMN dim_indicadores_economicos.dolar      IS 'Dólar observado en pesos — días hábiles, forward-fill en fines de semana';
COMMENT ON COLUMN dim_indicadores_economicos.ipc_mensual IS 'Variación mensual del IPC en % — valor de mes expandido a días';
COMMENT ON COLUMN dim_indicadores_economicos.tasa_desempleo IS 'Tasa de desocupación en % — trimestral publicada por INE';
COMMENT ON COLUMN dim_indicadores_economicos.imacec     IS 'Índice mensual de actividad económica en % — Banco Central';

-- =============================================================
-- TABLA DE HECHOS
-- =============================================================

-- -------------------------------------------------------------
-- fact_ventas
-- -------------------------------------------------------------
DROP TABLE IF EXISTS fact_ventas CASCADE;

CREATE TABLE fact_ventas (
    venta_id            INTEGER         PRIMARY KEY,
    fecha_id            INTEGER         NOT NULL REFERENCES dim_tiempo(fecha_id),
    cliente_id          INTEGER         NOT NULL REFERENCES dim_cliente(cliente_id),
    producto_id         INTEGER         NOT NULL REFERENCES dim_producto(producto_id),
    cantidad            SMALLINT        NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario_clp INTEGER         NOT NULL CHECK (precio_unitario_clp > 0),
    descuento_pct       NUMERIC(4,2)    NOT NULL DEFAULT 0 CHECK (descuento_pct BETWEEN 0 AND 1),
    monto_total_clp     INTEGER         NOT NULL CHECK (monto_total_clp > 0),
    canal_venta         VARCHAR(30)     NOT NULL,
    metodo_pago         VARCHAR(40)     NOT NULL
);

COMMENT ON TABLE  fact_ventas                       IS '~21.500 transacciones TechStore.cl 2024-2025';
COMMENT ON COLUMN fact_ventas.descuento_pct         IS 'Descuento como decimal: 0.10 = 10%';
COMMENT ON COLUMN fact_ventas.monto_total_clp       IS 'precio_unitario * cantidad * (1 - descuento_pct)';
COMMENT ON COLUMN fact_ventas.canal_venta           IS 'Web | App Móvil | Marketplace | Redes Sociales';
COMMENT ON COLUMN fact_ventas.metodo_pago           IS 'Tarjeta Crédito | Débito | Transferencia | WebPay | Cuotas sin interés';

-- =============================================================
-- ÍNDICES DE PERFORMANCE
-- =============================================================

-- fact_ventas — los más consultados en Power BI
CREATE INDEX idx_fact_ventas_fecha_id    ON fact_ventas(fecha_id);
CREATE INDEX idx_fact_ventas_cliente_id  ON fact_ventas(cliente_id);
CREATE INDEX idx_fact_ventas_producto_id ON fact_ventas(producto_id);
CREATE INDEX idx_fact_ventas_canal_venta ON fact_ventas(canal_venta);

-- dim_tiempo — filtros frecuentes
CREATE INDEX idx_dim_tiempo_año          ON dim_tiempo(año);
CREATE INDEX idx_dim_tiempo_mes          ON dim_tiempo(año, mes);
CREATE INDEX idx_dim_tiempo_evento       ON dim_tiempo(evento_comercial);

-- dim_cliente — segmentación
CREATE INDEX idx_dim_cliente_region      ON dim_cliente(region);
CREATE INDEX idx_dim_cliente_segmento    ON dim_cliente(segmento_rfm);

-- dim_producto — filtros de categoría
CREATE INDEX idx_dim_producto_categoria  ON dim_producto(categoria);
CREATE INDEX idx_dim_producto_marca      ON dim_producto(marca);

-- =============================================================
-- CARGA DESDE CSV desde la terminal
-- (Ejecutar después de subir los archivos al servidor) solo si no se pre-cargaron con Python
-- =============================================================

/*
\copy retail.dim_tiempo                FROM 'data/raw/dim_tiempo.csv'
    WITH (FORMAT CSV, HEADER true, DELIMITER ',');

\copy retail.dim_producto              FROM 'data/raw/dim_producto.csv'
    WITH (FORMAT CSV, HEADER true, DELIMITER ',');

\copy retail.dim_cliente               FROM 'data/raw/dim_cliente.csv'
    WITH (FORMAT CSV, HEADER true, DELIMITER ',');

\copy retail.dim_indicadores_economicos FROM 'data/raw/dim_indicadores_economicos.csv'
    WITH (FORMAT CSV, HEADER true, DELIMITER ',');

\copy retail.fact_ventas               FROM 'data/raw/fact_ventas.csv'
    WITH (FORMAT CSV, HEADER true, DELIMITER ',');
*/

-- Verificar carga
/*
SELECT 'dim_tiempo'                 AS tabla, COUNT(*) AS filas FROM retail.dim_tiempo
UNION ALL SELECT 'dim_producto',               COUNT(*) FROM retail.dim_producto
UNION ALL SELECT 'dim_cliente',                COUNT(*) FROM retail.dim_cliente
UNION ALL SELECT 'dim_indicadores_economicos', COUNT(*) FROM retail.dim_indicadores_economicos
UNION ALL SELECT 'fact_ventas',                COUNT(*) FROM retail.fact_ventas;
*/
