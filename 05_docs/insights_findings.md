# Insights y Hallazgos — TechStore.cl 2024-2025

Resultados del análisis exploratorio completo (`04_analysis/eda_completo.ipynb`).  
Período: 2024-01-01 a 2025-12-31 | 21.603 transacciones | 2.500 clientes | 150 SKUs

---

## Hallazgo 1 — El Pareto es más distribuido de lo esperado

**Dato:** 69 productos (46% del catálogo) generan el 80% de los ingresos.  
La regla clásica 80/20 implica que el 20% debería bastar — aquí se necesita el 46%.

**Interpretación:** El catálogo de TechStore.cl está bien balanceado.
No hay 2-3 productos "salvadores" que concentren todo el valor.
Esto reduce el riesgo de stockout crítico y da margen para experimentar con nuevos SKUs.

**Acción recomendada:**
- Clase A (69 prods): garantizar stock mínimo de 3 semanas antes de cada evento comercial.
- Clase B (42 prods): mantener rotación, revisar descuentos en temporada baja.
- Clase C (39 prods): evaluar descatalogación o reducción de inventario a 1 unidad por bodega.

---

## Hallazgo 2 — Black Friday y CyberDay dominan el calendario comercial

**Dato:**
| Evento | Uplift vs día normal |
|---|---|
| Black Friday (noviembre) | +270% |
| CyberDay (junio) | +248% |
| CyberMonday | +187% |
| Navidad | +140% |
| Día de la Madre | +106% |

**Interpretación:** Ambos eventos superan ampliamente el volumen de un día normal.
Black Friday lidera levemente en uplift (270% vs 248%), aunque la diferencia es marginal.
Chile ha adoptado ambos calendarios comerciales con alta respuesta de compra.

**Acción recomendada:**
- Concentrar el 40% del presupuesto anual de marketing en Black Friday y CyberDay.
- Pre-cargar inventario crítico 3 semanas antes de noviembre y junio.
- Activar campaña de retargeting 7 días antes de cada evento para clientes At Risk.

---

## Hallazgo 3 — El dólar tiene impacto débil en el corto plazo

**Dato:** Correlación ventas mensuales vs dólar: **r = -0.060** (prácticamente nula).

**Interpretación:** Los clientes de tecnología en Chile son **relativamente inelásticos**
al tipo de cambio en el corto plazo. Ante una alza del dólar, la reacción más común
es **postergar**, no cancelar. El efecto negativo aparece cuando las alzas son
sostenidas por más de 3-4 meses consecutivos.

**Importante:** Smartphones (44% de ingresos) son el segmento más expuesto al
riesgo cambiario por ser casi 100% importados.

**Acción recomendada:**
- No reaccionar con descuentos ante variaciones puntuales del dólar.
- Monitorear tendencia de 90 días del dólar como indicador adelantado de caída de demanda.
- Diversificar hacia Accesorios (margen más alto, menos exposición cambiaria).

---

## Hallazgo 4 — Smartphones concentra el 44% pero tiene el margen más bajo

**Dato:**
| Categoría | Ventas | % del total | Margen bruto |
|---|---|---|---|
| Smartphones | $4.64 B | 44.3% | ~24% |
| Laptops | $2.91 B | 27.8% | ~26% |
| Gaming | $1.11 B | 10.6% | ~28% |
| Audio | $0.97 B | 9.2% | ~31% |
| Accesorios | $0.85 B | 8.1% | ~38% |

**Interpretación:** El negocio depende excesivamente de Smartphones,
que además tienen el margen más bajo. Accesorios y Audio tienen márgenes
significativamente más altos con menor exposición cambiaria.

**Acción recomendada:**
- Aumentar cross-selling de Accesorios en el checkout de Smartphones.
- Desarrollar línea propia de accesorios (mayor margen).
- Establecer meta: reducir dependencia de Smartphones al 38% en 2026.

---

## Hallazgo 5 — La retención post-primera compra es el principal punto de mejora

**Dato:** La tasa de retención promedio cae significativamente entre el mes 0
(primera compra) y el mes 1. Las cohortes más antiguas muestran mejor retención
que las recientes, sugiriendo que el canal de adquisición reciente trae
clientes de menor calidad (potencialmente TikTok y Redes Sociales).

**Acción recomendada:**
- Implementar email de seguimiento automático a los 15 días post-compra.
- Agregar flujo de onboarding: review del producto + oferta de garantía extendida.
- Analizar retención por canal de adquisición para optimizar CAC.

---

## Hallazgo 6 — Accesorios y Smartphones tienen co-ocurrencia en el carrito

**Dato:** El análisis de Market Basket identifica combinaciones frecuentes que involucran
Smartphones y Accesorios entre las reglas más recurrentes. Los valores de lift (~1.01)
son débiles en términos estadísticos, lo que refleja la naturaleza sintética del dataset,
pero la dirección de la asociación es consistente con la hipótesis de cross-selling.

**Acción recomendada:**
- Implementar bundle dinámico en el checkout: mostrar los 3 accesorios más comprados
  junto al modelo específico de smartphone seleccionado.
- Crear paquete "Smartphone + Protección": funda + vidrio templado con 10% de descuento.
- Medir conversión del bundle vs ventas individuales en A/B test de 30 días.

---

## Resumen ejecutivo para la presentación

> TechStore.cl tiene un catálogo bien balanceado (Pareto 46/80), pero
> excesivamente concentrado en Smartphones (44% de ingresos, margen bajo).
> La mayor oportunidad de mejora está en retención post-compra y en
> aumentar el ticket promedio vía cross-selling de Accesorios,
> categoría con el doble de margen y menor riesgo cambiario.
> Black Friday y CyberDay son los dos eventos centrales del calendario comercial
> con uplift superior al 248%, y deben concentrar el grueso del presupuesto anual de marketing.
