# Power BI — Documentación de Medidas DAX
## TechStore.cl Retail Analytics Dashboard

> **Archivo:** `TechStore_Dashboard.pbix`  
> **Fuente de datos:** Vista `retail.v_ventas_enriquecidas` en PostgreSQL  
> **Páginas:** 2 — Dashboard Ejecutivo | Análisis Macroeconómico

---

## 1. Conexión a PostgreSQL

En Power BI Desktop:
1. **Obtener datos** → **PostgreSQL**
2. Servidor: `localhost` (o tu host), Puerto: `5432`
3. Base de datos: `retail_analytics`
4. Importar las siguientes vistas/tablas:
   - `retail.v_ventas_enriquecidas` ← tabla principal
   - `retail.v_kpis_diarios`        ← para gráficos de línea
   - `retail.v_pareto_productos`    ← para Pareto
   - `retail.v_rfm_segmentacion`    ← para matriz RFM

> **Tip:** Usa Modo Importación (no DirectQuery) para mejor
> rendimiento con ~21.500 filas.

---

## 2. Tabla de Medidas

Crear una tabla vacía llamada **`_Medidas`** para organizar
todas las medidas en un solo lugar:
- Inicio → Escribir datos → tabla de 1 columna vacía → renombrar a `_Medidas`

---

## 3. Medidas — Ventas Base

```dax
Ventas Totales =
    SUM(v_ventas_enriquecidas[monto_total_clp])
```

```dax
Número de Órdenes =
    COUNTROWS(v_ventas_enriquecidas)
```

```dax
Unidades Vendidas =
    SUM(v_ventas_enriquecidas[cantidad])
```

```dax
Clientes Únicos =
    DISTINCTCOUNT(v_ventas_enriquecidas[cliente_id])
```

```dax
Ticket Promedio =
    DIVIDE(
        [Ventas Totales],
        [Número de Órdenes]
    )
```

```dax
Descuento Promedio % =
    AVERAGE(v_ventas_enriquecidas[descuento_pct]) * 100
```

```dax
Margen Bruto Total =
    SUM(v_ventas_enriquecidas[margen_bruto_clp])
```

```dax
Margen Bruto % =
    DIVIDE(
        [Margen Bruto Total],
        [Ventas Totales]
    ) * 100
```

---

## 4. Medidas — Comparativo Año a Año (YoY)

```dax
Ventas Año Anterior =
    CALCULATE(
        [Ventas Totales],
        SAMEPERIODLASTYEAR(v_ventas_enriquecidas[fecha])
    )
```

```dax
Crecimiento YoY % =
    DIVIDE(
        [Ventas Totales] - [Ventas Año Anterior],
        [Ventas Año Anterior]
    )
```

```dax
Crecimiento YoY % (Texto) =
    VAR pct = [Crecimiento YoY %]
    RETURN
        IF(
            ISBLANK(pct),
            "Sin comparativo",
            IF(pct >= 0,
               "▲ " & FORMAT(pct, "0.0%"),
               "▼ " & FORMAT(ABS(pct), "0.0%")
            )
        )
```

```dax
Órdenes Año Anterior =
    CALCULATE(
        [Número de Órdenes],
        SAMEPERIODLASTYEAR(v_ventas_enriquecidas[fecha])
    )
```

```dax
Crecimiento Órdenes YoY % =
    DIVIDE(
        [Número de Órdenes] - [Órdenes Año Anterior],
        [Órdenes Año Anterior]
    )
```

---

## 5. Medidas — Análisis Pareto (Página 1)

```dax
% Ventas sobre Total =
    DIVIDE(
        [Ventas Totales],
        CALCULATE([Ventas Totales], ALL(v_ventas_enriquecidas))
    )
```

```dax
% Acumulado Pareto =
    VAR VentasProductoActual = [Ventas Totales]
    VAR VentasProductosMayores =
        CALCULATE(
            [Ventas Totales],
            FILTER(
                ALL(v_ventas_enriquecidas[producto_id],
                    v_ventas_enriquecidas[producto_nombre]),
                [Ventas Totales] >= VentasProductoActual
            )
        )
    RETURN
        DIVIDE(
            VentasProductosMayores,
            CALCULATE([Ventas Totales], ALL(v_ventas_enriquecidas))
        )
```

```dax
Clasificación ABC =
    VAR pct = [% Acumulado Pareto]
    RETURN
        SWITCH(
            TRUE(),
            pct <= 0.80, "A — Top 80%",
            pct <= 0.95, "B — Siguiente 15%",
            "C — Último 5%"
        )
```

---

## 6. Medidas — Indicadores Económicos (Página 2)

```dax
Dólar Promedio Período =
    AVERAGE(v_kpis_diarios[dolar])
```

```dax
UF Promedio Período =
    AVERAGE(v_kpis_diarios[uf])
```

```dax
Tasa Desempleo Período =
    AVERAGE(v_kpis_diarios[tasa_desempleo])
```

```dax
Variación Dólar vs Inicio =
    VAR dolar_actual  = AVERAGE(v_kpis_diarios[dolar])
    VAR dolar_inicio  =
        CALCULATE(
            AVERAGE(v_kpis_diarios[dolar]),
            FIRSTDATE(v_kpis_diarios[fecha])
        )
    RETURN
        DIVIDE(dolar_actual - dolar_inicio, dolar_inicio) * 100
```

```dax
-- Correlación simple ventas vs dólar (aproximación lineal DAX)
-- Nota: la correlación exacta se calcula en el notebook Python
Índice Sensibilidad Dólar =
    VAR ventas_norm =
        DIVIDE(
            [Ventas Totales] - MINX(ALL(v_kpis_diarios[fecha]), [Ventas Totales]),
            MAXX(ALL(v_kpis_diarios[fecha]), [Ventas Totales])
              - MINX(ALL(v_kpis_diarios[fecha]), [Ventas Totales])
        )
    RETURN ventas_norm
```

---

## 7. Medidas — RFM (Página 2)

```dax
Clientes Champions =
    CALCULATE(
        [Clientes Únicos],
        v_ventas_enriquecidas[segmento_rfm] = "Champions"
    )
```

```dax
Clientes At Risk =
    CALCULATE(
        [Clientes Únicos],
        v_ventas_enriquecidas[segmento_rfm] = "At Risk"
    )
```

```dax
% Champions sobre Total =
    DIVIDE([Clientes Champions], [Clientes Únicos])
```

```dax
LTV Promedio Cliente =
    DIVIDE(
        [Ventas Totales],
        [Clientes Únicos]
    )
```

---

## 8. Medidas — KPIs con formato para tarjetas

```dax
Ventas Totales (Formato) =
    VAR v = [Ventas Totales]
    RETURN
        IF(v >= 1000000000,
            "$" & FORMAT(v / 1000000000, "0.0") & " B",
            "$" & FORMAT(v / 1000000, "0.0") & " M"
        ) & " CLP"
```

```dax
Ticket Promedio (Formato) =
    "$" & FORMAT([Ticket Promedio] / 1000, "0") & "K CLP"
```

---

## 9. Especificación del Dashboard

### Página 1 — Dashboard Ejecutivo

**Objetivo:** Vista rápida para gerencia. ¿Cómo vamos?

```
┌─────────────────────────────────────────────────────┐
│  [KPI] Ventas   [KPI] Ticket  [KPI] Órdenes  [KPI]  │
│  Totales        Promedio                     YoY %   │
├──────────────────────────┬──────────────────────────┤
│                          │                          │
│  LINE CHART              │  PARETO 80/20            │
│  Ventas diarias/mens.    │  Barras producto +       │
│  vs año anterior         │  línea % acumulado       │
│                          │                          │
├──────────────────────────┴──────────────────────────┤
│                          │                          │
│  TREEMAP                 │  MAPA DE CHILE           │
│  Ventas por categoría    │  Ventas por región       │
│                          │  (burbuja por monto)     │
├──────────────────────────┴──────────────────────────┤
│  SLICERS: Año | Mes | Categoría | Región | Canal    │
└─────────────────────────────────────────────────────┘
```

**Configuración de visuales:**

| Visual | Campo X/Eje | Campo Y/Valores | Leyenda |
|---|---|---|---|
| KPI Cards | — | Medidas base | — |
| Line chart | `fecha` (mes) | `Ventas Totales` + `Ventas Año Anterior` | `año` |
| Pareto | `producto_nombre` | `Ventas Totales` (barras) + `% Acumulado Pareto` (línea) | — |
| Treemap | `categoria` | `Ventas Totales` | `subcategoria` |
| Mapa | `region` | `Ventas Totales` (tamaño burbuja) | — |

---

### Página 2 — Análisis Macroeconómico

**Objetivo:** ¿Por qué las ventas se comportan así?

```
┌──────────────────────────────────────────────────────┐
│  DUAL-AXIS LINE CHART                                │
│  Ventas mensuales (barras) vs Dólar (línea)          │
│  Storytelling: "Cuando el dólar sube, las ventas    │
│  de importados caen"                                 │
├──────────────────────┬───────────────────────────────┤
│                      │                               │
│  SCATTER PLOT        │  COMBO CHART                  │
│  Desempleo vs Ventas │  Ventas por cat. vs IPC       │
│  (por mes)           │  mensual                      │
│                      │                               │
├──────────────────────┴───────────────────────────────┤
│                      │                               │
│  MATRIZ RFM          │  TABLA DINÁMICA               │
│  Segmento | #Clientes│  Importados vs Nacionales     │
│  | Ventas | % Ventas │  según variación dólar        │
│                      │                               │
├──────────────────────┴───────────────────────────────┤
│  KPI: Dólar promedio | Correlación (texto del EDA)   │
└──────────────────────────────────────────────────────┘
```

**Configuración de visuales:**

| Visual | Campo X | Campo Y (eje izq) | Campo Y2 (eje der) |
|---|---|---|---|
| Dual-axis | `fecha` (mes) | `Ventas Totales` | `Dólar Promedio Período` |
| Scatter | `tasa_desempleo` | `Ventas Totales` | — |
| Combo | `nombre_mes` | `Ventas Totales` | `ipc_mensual` |
| Matriz RFM | `segmento_rfm` | `Clientes Únicos` + `Ventas Totales` + `LTV Promedio` | — |

---

## 10. Configuración de Slicers (Página 1)

| Slicer | Campo | Tipo | Valores por defecto |
|---|---|---|---|
| Período | `año` | Lista | Todos |
| Mes | `nombre_mes` | Desplegable | Todos |
| Categoría | `categoria` | Lista | Todos |
| Región | `region` | Desplegable | Todos |
| Canal de venta | `canal_venta` | Lista | Todos |
| Evento comercial | `evento_comercial` | Lista | Todos |

> **Tip:** Sincronizar slicers de Año y Mes entre ambas páginas
> para mantener consistencia al navegar.

---

## 11. Formato y estilo recomendado

- **Colores principales:** `#01696F` (verde teal) para barras primarias, `#964219` (naranja) para líneas secundarias
- **Fuente:** Segoe UI, 11px cuerpo, 14px títulos de visual
- **Fondo:** Gris muy claro `#F7F6F2` para el canvas
- **KPI positivo:** `#437A22` (verde), **KPI negativo:** `#A12C7B` (rojo/rosa)
- **Logos/título:** "TechStore.cl — Retail Analytics" con el período en subtítulo dinámico:

```dax
Título Dinámico =
    "Ventas " &
    MINX(ALL(v_ventas_enriquecidas[año]), v_ventas_enriquecidas[año])
    & " – " &
    MAXX(ALL(v_ventas_enriquecidas[año]), v_ventas_enriquecidas[año])
```
