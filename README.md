# TechStore.cl — Retail Analytics Chile

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power_BI-Dashboard-F2C811?logo=powerbi&logoColor=black)
![Jupyter](https://img.shields.io/badge/Jupyter-EDA-F37626?logo=jupyter&logoColor=white)
![Status](https://img.shields.io/badge/Status-Completo-green)

Proyecto de análisis de datos de extremo a extremo para un retailer chileno de tecnología.
Cubre el ciclo completo: ETL → SQL → Power BI → EDA con Machine Learning.

> **Stack:** Python · PostgreSQL · Power BI · scikit-learn · Prophet

---

## Preguntas de Negocio

| Pregunta | Técnica | Resultado |
|---|---|---|
| ¿Qué productos generan el 80% de ingresos? | Pareto ABC | 69 prods (46%) → 80% ventas |
| ¿Cómo segmentar clientes por valor real? | RFM + K-Means | 4 segmentos accionables |
| ¿El dólar afecta las ventas de importados? | Correlación | r = -0.02 (impacto bajo c/p) |
| ¿Cuánto retenemos clientes mes a mes? | Cohortes | Caída significativa mes 1 |
| ¿Qué productos se compran juntos? | Market Basket | Smartphones → Accesorios |
| ¿Cuánto venderemos en Q1 2026? | Prophet | Forecast con IC 95% |

---

## Estructura del Proyecto

```
retail-analytics-chile/
│
├── 01_etl/
│   ├── generate_sales_data.py         # Genera datos sintéticos de ventas
│   ├── extract_mindicador_api.py      # Descarga indicadores reales de Chile
│   └── load_to_postgres.py           # Carga CSVs a PostgreSQL con upsert
│
├── 02_sql/
│   ├── 01_create_schema.sql          # DDL: tablas, índices, foreign keys
│   ├── 02_create_views.sql           # 4 vistas para Power BI y análisis
│   ├── 03_stored_procedures.sql      # SPs: RFM update + reporte mensual
│   └── 04_sample_queries.sql         # Consultas de ejemplo y demostración
│
├── 03_powerbi/
│   └── measures_documentation.md    # 28 medidas DAX + especificación del dashboard
│
├── 04_analysis/
│   └── eda_completo.ipynb            # EDA: Pareto, RFM, correlaciones, cohortes, forecast
│
├── 05_docs/
│   ├── data_dictionary.md            # Descripción de cada columna de cada tabla
│   ├── business_case.md              # Contexto de negocio y preguntas a responder
│   └── insights_findings.md         # 6 hallazgos accionables con datos reales
│
├── data/
│   └── raw/                          # CSVs generados (no subir a git el fact_ventas)
│       ├── dim_tiempo.csv             # 731 filas
│       ├── dim_producto.csv           # 150 SKUs
│       ├── dim_cliente.csv            # 2.500 clientes
│       ├── dim_indicadores_economicos.csv  # Datos reales Banco Central
│       └── fact_ventas.csv            # 21.567 transacciones
│
├── .env.example                       # Variables de entorno (copiar a .env)
├── requirements.txt                   # Dependencias Python
└── README.md
```

---

## Setup Rápido

### 1. Clonar e instalar dependencias
```bash
git clone https://github.com/MariabelenDumont
cd data-analyst-portfolio/retail-analytics-chile
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL
```

### 3. Generar los datos
```bash
# Datos sintéticos de ventas
python 01_etl/generate_sales_data.py

# Indicadores económicos reales desde mindicador.cl
python 01_etl/extract_mindicador_api.py
```

### 4. Crear el schema y cargar datos en PostgreSQL
```bash
# Crear tablas, vistas y stored procedures
psql -U postgres -d retail_analytics -f 02_sql/01_create_schema.sql
psql -U postgres -d retail_analytics -f 02_sql/02_create_views.sql
psql -U postgres -d retail_analytics -f 02_sql/03_stored_procedures.sql

# Cargar todos los CSVs con upsert automático
python 01_etl/load_to_postgres.py
```

### 5. Calcular segmentación RFM
```sql
-- En pgAdmin o psql
CALL retail.sp_calcular_segmentacion_rfm('2025-12-31');
```

### 6. Abrir el notebook EDA
```bash
jupyter notebook 04_analysis/eda_completo.ipynb
```

---

## Flujo de Actualización Diaria (Producción)

```bash
# 1. Bajar nuevos indicadores del Banco Central
python 01_etl/extract_mindicador_api.py

# 2. Cargar solo la tabla de indicadores (upsert — no afecta otros datos)
python 01_etl/load_to_postgres.py --tabla dim_indicadores_economicos

# 3. Recalcular segmentos RFM con la fecha de hoy
psql -U postgres -d retail_analytics -c "CALL retail.sp_calcular_segmentacion_rfm(CURRENT_DATE);"
```

Automatizable con `cron` o Apache Airflow en un DAG diario.

---

## Modelo de Datos (Star Schema)

```
             dim_tiempo
                 │
  dim_cliente ──────── fact_ventas ──── dim_producto
                 │
     dim_indicadores_economicos
```

**Tablas:** 4 dimensiones + 1 tabla de hechos  
**Vistas:** v_ventas_enriquecidas · v_kpis_diarios · v_rfm_segmentacion · v_pareto_productos  
**Índices:** 8 índices de performance en columnas de filtro frecuente

---

## Principales Hallazgos

- **Pareto:** 69 productos (46%) generan el 80% de los ingresos — catálogo equilibrado
- **Estacionalidad:** CyberDay +279% de órdenes vs día normal, supera a Black Friday (+253%)
- **Macro:** Correlación ventas vs dólar = -0.02 (impacto débil en corto plazo)
- **Categorías:** Smartphones = 44% de ingresos pero menor margen; Accesorios = mayor margen
- **Cross-sell:** Smartphones → Accesorios es la regla de asociación más fuerte
- **Retención:** Oportunidad clara de mejorar la experiencia post-primera compra

Ver análisis completo en `05_docs/insights_findings.md`

---

## Herramientas y Técnicas

| Área | Herramienta / Técnica |
|---|---|
| ETL | Python, pandas, requests, SQLAlchemy |
| Base de datos | PostgreSQL 15, Star Schema, Views, Stored Procedures |
| Visualización | Power BI, DAX (28 medidas) |
| Clustering | K-Means (scikit-learn), Silhouette Score |
| Asociación | Apriori, mlxtend |
| Series de tiempo | Prophet (Meta) |
| Estadística | Correlación de Pearson, regresión lineal, scipy |
| Análisis | Pareto ABC, RFM, Cohortes, Market Basket |

---

## Autor

**Mariabelén Dumont**  
Analista de Datos · Santiago, Chile  
[LinkedIn] https://www.linkedin.com/in/mariabelen-dumonts · [Portfolio](https://github.com/MariabelenDumont)

---

*Datos de ventas sintéticos generados con Faker y distribuciones realistas.  
Indicadores económicos reales: Banco Central de Chile vía [mindicador.cl](https://mindicador.cl)*
