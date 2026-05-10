# Business Case — TechStore.cl Retail Analytics

## Contexto del Negocio

TechStore.cl es un retailer chileno de tecnología de consumo fundado en 2019.
Opera en formato **direct-to-consumer** a través de 4 canales digitales:
Web, App Móvil, Marketplace (MercadoLibre, Falabella.com) y Redes Sociales.

Su catálogo cubre 5 categorías: Laptops, Smartphones, Accesorios, Gaming y Audio,
con 150 SKUs activos al cierre de 2025.

**Facturación 2024-2025:** $10.5 B CLP anualizados  
**Base de clientes activos:** 2.500 (compraron al menos una vez en el período)  
**Regiones con presencia:** 10 regiones de Chile, concentración en RM (58%)

---

## Desafío

El equipo comercial enfrenta tres preguntas sin respuesta clara:

1. **¿Dónde está concentrado el valor?**  
   El equipo de compras no sabe si está sobreinventariando productos de baja rotación
   mientras los mejores SKUs se quedan sin stock en eventos clave.

2. **¿Qué clientes merecen inversión diferenciada?**  
   El equipo de CRM envía la misma campaña a todos los clientes, sin distinguir
   entre un cliente que compra mensualmente $3M y uno que compró una vez hace 8 meses.

3. **¿El contexto macro afecta las decisiones de compra?**  
   Con el dólar fluctuando entre $877 y $1.012 CLP en el período, el equipo
   no sabe si las alzas cambiarias deprimen las ventas de importados
   o si los clientes absorben el impacto sin cambiar su comportamiento.

---

## Preguntas de Negocio

| # | Pregunta | Área | Análisis |
|---|---|---|---|
| 1 | ¿Qué 20% de productos genera el 80% de ingresos? | Compras/Inventario | Pareto ABC |
| 2 | ¿Cómo segmentar clientes por valor real y comportamiento? | CRM/Marketing | RFM + K-Means |
| 3 | ¿El alza del dólar reduce ventas de productos importados? | Pricing/Finanzas | Correlación macro |
| 4 | ¿Cuánto retenemos a los clientes mes a mes? | Customer Success | Cohortes |
| 5 | ¿Qué productos se compran juntos? | Ecommerce/UX | Market Basket |
| 6 | ¿Cuánto venderemos en Q1 2026? | Planificación | Forecast Prophet |

---

## Stack Tecnológico del Proyecto

| Capa | Tecnología | Justificación |
|---|---|---|
| Generación de datos | Python (Faker, NumPy) | Datos sintéticos realistas con comportamiento estacional |
| Indicadores macro | Python + API mindicador.cl | Datos reales del Banco Central de Chile |
| Almacenamiento | PostgreSQL 15 (esquema estrella) | Estándar industria para DWH, soporta vistas y SPs |
| Transformación | SQL (Views + Stored Procedures) | Lógica de negocio vive junto a los datos |
| Visualización | Power BI + DAX | Herramienta estándar en empresas chilenas |
| Análisis avanzado | Python (pandas, scikit-learn, Prophet) | K-Means, Market Basket, Forecast |

---

## Alcance y Limitaciones

**Dentro del alcance:**
- Análisis descriptivo, diagnóstico y predictivo de ventas 2024-2025
- Segmentación de clientes con técnicas de clustering
- Impacto de indicadores macroeconómicos en ventas

**Fuera del alcance:**
- Datos de costos de publicidad o CAC por canal (no disponibles)
- Análisis de devoluciones y garantías
- Integración con sistemas de inventario en tiempo real
- Datos de competidores o market share

**Limitaciones de los datos:**
- Los datos de ventas son **sintéticos** (generados con distribuciones realistas)
- Los indicadores económicos son **reales** (mindicador.cl, Banco Central)
- La base de clientes es estática (no simula churns reales)
