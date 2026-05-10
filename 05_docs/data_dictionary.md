# Diccionario de Datos — TechStore.cl Retail Analytics

Fuente: esquema `retail` en PostgreSQL 15+  
Período: 2024-01-01 a 2025-12-31  
Motor generador: `01_etl/generate_sales_data.py` + `01_etl/extract_mindicador_api.py`

---

## fact_ventas

Tabla de hechos principal. Cada fila es una transacción de venta.

| Columna | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `venta_id` | INTEGER PK | Identificador único de la transacción | 10001 |
| `fecha_id` | INTEGER FK→dim_tiempo | Llave de fecha en formato YYYYMMDD | 20240115 |
| `cliente_id` | INTEGER FK→dim_cliente | Identificador del cliente | 1042 |
| `producto_id` | INTEGER FK→dim_producto | Identificador del producto | 23 |
| `cantidad` | SMALLINT | Unidades compradas en la orden | 2 |
| `precio_unitario_clp` | INTEGER | Precio efectivo pagado por unidad (con descuento ya aplicado si aplica) | 849990 |
| `descuento_pct` | NUMERIC(4,2) | Descuento como decimal: 0.10 = 10% | 0.10 |
| `monto_total_clp` | INTEGER | `precio_unitario * cantidad * (1 - descuento_pct)` | 1529982 |
| `canal_venta` | VARCHAR(30) | Canal por donde se realizó la compra | Web |
| `metodo_pago` | VARCHAR(40) | Método de pago utilizado | Tarjeta Crédito |

**Valores posibles:**
- `canal_venta`: Web · App Móvil · Marketplace · Redes Sociales
- `metodo_pago`: Tarjeta Crédito · Débito · Transferencia · WebPay · Cuotas sin interés

---

## dim_tiempo

Calendario completo 2024-2025 con atributos temporales y eventos comerciales chilenos.

| Columna | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `fecha_id` | INTEGER PK | Fecha en formato YYYYMMDD | 20240601 |
| `fecha` | DATE | Fecha calendario | 2024-06-01 |
| `año` | SMALLINT | Año | 2024 |
| `trimestre` | SMALLINT | Trimestre (1-4) | 2 |
| `mes` | SMALLINT | Mes (1-12) | 6 |
| `nombre_mes` | VARCHAR(20) | Nombre del mes en español | Junio |
| `dia` | SMALLINT | Día del mes (1-31) | 1 |
| `nombre_dia_semana` | VARCHAR(15) | Nombre del día en español | Sábado |
| `numero_dia_semana` | SMALLINT | Número del día (1=Lunes, 7=Domingo) | 6 |
| `es_fin_semana` | BOOLEAN | True si es sábado o domingo | True |
| `es_feriado` | BOOLEAN | True si es feriado nacional chileno | False |
| `evento_comercial` | VARCHAR(40) | Evento comercial activo ese día | CyberDay |
| `semana_año` | SMALLINT | Número de semana ISO (1-53) | 22 |

**Valores posibles `evento_comercial`:**
CyberDay · CyberMonday · Black Friday · Navidad · Día de la Madre · Día del Padre · Vuelta al Cole · Fiestas Patrias · Normal

---

## dim_producto

Catálogo de 150 SKUs en 5 categorías de tecnología.

| Columna | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `producto_id` | INTEGER PK | Identificador único del producto | 1 |
| `sku` | VARCHAR(20) | Código SKU interno | LAP-001 |
| `nombre` | VARCHAR(120) | Nombre completo del producto | MacBook Pro 14" M3 |
| `categoria` | VARCHAR(30) | Categoría principal | Laptops |
| `subcategoria` | VARCHAR(60) | Subcategoría específica | Ultrabooks Premium |
| `marca` | VARCHAR(50) | Marca del producto | Apple |
| `precio_lista_clp` | INTEGER | Precio de lista (sin descuento) en pesos | 1899990 |
| `costo_unitario_clp` | INTEGER | Costo del producto para el retailer | 1330000 |
| `es_importado` | BOOLEAN | True si el producto es importado | True |
| `pais_origen` | VARCHAR(50) | País de fabricación | China |

**Categorías y SKUs:**
- Laptops (30 SKUs) · Smartphones (35 SKUs) · Accesorios (40 SKUs) · Gaming (25 SKUs) · Audio (20 SKUs)

---

## dim_cliente

Base de 2.500 clientes distribuidos en 10 regiones de Chile.

| Columna | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `cliente_id` | INTEGER PK | Identificador único del cliente | 1042 |
| `nombre` | VARCHAR(100) | Nombre completo (sintético) | María González López |
| `email` | VARCHAR(120) | Email único del cliente | m.gonzalez@email.cl |
| `region` | VARCHAR(50) | Región de Chile | Región Metropolitana |
| `comuna` | VARCHAR(60) | Comuna dentro de la región | Las Condes |
| `segmento_rfm` | VARCHAR(20) | Segmento RFM calculado por SP | Champions |
| `fecha_registro` | DATE | Fecha de creación de la cuenta | 2023-03-15 |
| `canal_adquisicion` | VARCHAR(40) | Canal por donde llegó el cliente | Google Ads |

**Valores posibles `segmento_rfm`:**
Champions · Loyal · Potential · New · At Risk · Hibernating · Lost

**Valores posibles `canal_adquisicion`:**
Orgánico · Google Ads · Facebook/Instagram · Referido · Email Marketing · TikTok

---

## dim_indicadores_economicos

Indicadores macroeconómicos reales de Chile, fuente Banco Central vía mindicador.cl.

| Columna | Tipo | Descripción | Fuente | Frecuencia |
|---|---|---|---|---|
| `fecha_id` | INTEGER PK/FK | Llave de fecha | — | Diaria |
| `uf` | NUMERIC(10,2) | Unidad de Fomento en CLP | Banco Central | Diaria |
| `dolar` | NUMERIC(8,2) | Dólar observado en CLP | Banco Central | Hábil (forward-fill fines de semana) |
| `euro` | NUMERIC(8,2) | Euro en CLP | Banco Central | Hábil (forward-fill fines de semana) |
| `ipc_mensual` | NUMERIC(5,2) | Variación mensual del IPC en % | INE | Mensual (expandido a días) |
| `utm` | INTEGER | Unidad Tributaria Mensual en CLP | SII | Mensual (expandido a días) |
| `tasa_desempleo` | NUMERIC(5,2) | Tasa de desocupación en % | INE | Trimestral (expandido a días) |
| `imacec` | NUMERIC(6,2) | Índice mensual de actividad económica en % | Banco Central | Mensual (expandido a días) |

> **Nota forward-fill:** Los indicadores de frecuencia hábil (dólar, euro) mantienen el último valor conocido durante fines de semana y feriados.

---

## Vistas calculadas

### v_ventas_enriquecidas
JOIN completo de `fact_ventas` con todas las dimensiones. Columnas adicionales calculadas:
- `margen_bruto_clp` = `monto_total_clp - costo_unitario_clp * cantidad`
- `margen_bruto_pct` = `margen_bruto_clp / monto_total_clp * 100`
- `monto_total_uf` = `monto_total_clp / uf`

### v_kpis_diarios
Agregación diaria con KPIs de ventas + indicadores macroeconómicos del día.

### v_rfm_segmentacion
RFM completo por cliente con scores 1-5 por quintil y segmento calculado en SQL.

### v_pareto_productos
Ranking de productos con % acumulado de ventas y clasificación ABC.
