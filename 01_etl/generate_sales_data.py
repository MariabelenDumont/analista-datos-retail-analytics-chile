"""
generate_sales_data.py
======================
Generador de dataset sintético de ventas para TechStore.cl
Proyecto: Retail Analytics Chile — portfolio-analista-datos

Genera 4 tablas CSV listas para cargar a PostgreSQL:
  - dim_tiempo.csv       : 731 filas (2024-2025)
  - dim_producto.csv     : 150 SKUs (5 categorías)
  - dim_cliente.csv      : 2.500 clientes chilenos
  - fact_ventas.csv      : ~21.500 transacciones

Correlaciones intencionales:
  - Ventas bajan cuando sube el dólar (importados)
  - Eventos comerciales generan picos (CyberDay, Black Friday, Navidad)
  - Clientes premium menos sensibles a variaciones económicas
  - Productos baratos más sensibles al desempleo

Uso:
    pip install faker pandas numpy
    python generate_sales_data.py

Outputs en ./data/raw/
"""

import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import date, timedelta
import os

# ── Reproducibilidad ──────────────────────────────────────────
fake = Faker("es_CL")
np.random.seed(42)
random.seed(42)

# ── Configuración ─────────────────────────────────────────────
START_DATE = date(2024, 1, 1)
END_DATE   = date(2025, 12, 31)
N_CLIENTES = 2500
BASE_DAILY = 22          # transacciones base por día
OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================
# SECCIÓN 1 — DIM_TIEMPO
# =============================================================
FERIADOS = {
    date(2024,1,1),date(2024,3,29),date(2024,3,30),date(2024,4,1),
    date(2024,5,1),date(2024,5,21),date(2024,6,20),date(2024,7,16),
    date(2024,8,15),date(2024,9,18),date(2024,9,19),date(2024,9,20),
    date(2024,10,12),date(2024,10,31),date(2024,11,1),date(2024,12,8),date(2024,12,25),
    date(2025,1,1),date(2025,4,18),date(2025,4,19),date(2025,4,21),
    date(2025,5,1),date(2025,5,21),date(2025,6,20),date(2025,7,16),
    date(2025,8,15),date(2025,9,18),date(2025,9,19),
    date(2025,10,12),date(2025,10,31),date(2025,11,1),date(2025,12,8),date(2025,12,25)
}

MESES_ES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
            7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
DIAS_ES  = {0:"Lunes",1:"Martes",2:"Miércoles",3:"Jueves",4:"Viernes",5:"Sábado",6:"Domingo"}

def get_evento(d):
    m, dia, y = d.month, d.day, d.year
    if m == 3 and 1 <= dia <= 15:
        return "Vuelta al Cole"
    if m == 5:
        suns = [date(y,5,x) for x in range(1,32) if date(y,5,x).weekday()==6]
        if abs((d - suns[1]).days) <= 3: return "Día de la Madre"
    if m == 6:
        mon1 = next(date(y,6,x) for x in range(1,8) if date(y,6,x).weekday()==0)
        if 0 <= (d - mon1).days <= 2: return "CyberDay"
        suns = [date(y,6,x) for x in range(1,31) if date(y,6,x).weekday()==6]
        if len(suns) >= 3 and abs((d - suns[2]).days) <= 2: return "Día del Padre"
    if m == 9 and 15 <= dia <= 20:
        return "Fiestas Patrias"
    if m == 10:
        mon1 = next(date(y,10,x) for x in range(1,8) if date(y,10,x).weekday()==0)
        if 0 <= (d - mon1).days <= 2: return "CyberMonday"
    if m == 11:
        fris = [date(y,11,x) for x in range(1,31) if date(y,11,x).weekday()==4]
        if 0 <= (d - fris[-1]).days <= 3: return "Black Friday"
    if m == 12 and dia >= 10:
        return "Navidad"
    return "Normal"

def build_dim_tiempo():
    rows = []
    cur, fid = START_DATE, 1
    while cur <= END_DATE:
        rows.append({
            "fecha_id":           fid,
            "fecha":              cur.isoformat(),
            "año":                cur.year,
            "trimestre":          (cur.month - 1) // 3 + 1,
            "mes":                cur.month,
            "nombre_mes":         MESES_ES[cur.month],
            "dia":                cur.day,
            "nombre_dia_semana":  DIAS_ES[cur.weekday()],
            "numero_dia_semana":  cur.weekday() + 1,
            "es_fin_semana":      cur.weekday() >= 5,
            "es_feriado":         cur in FERIADOS,
            "evento_comercial":   get_evento(cur),
            "semana_año":         cur.isocalendar()[1],
        })
        cur += timedelta(days=1)
        fid += 1
    return pd.DataFrame(rows)

# =============================================================
# SECCIÓN 2 — DIM_PRODUCTO
# =============================================================
CATALOGO = {
    "Laptops": {
        "subcats": ["Ultrabooks","Gaming Laptops","Workstations","Chromebooks","2 en 1"],
        "marcas":  ["Apple","Dell","HP","Lenovo","ASUS","MSI","Acer"],
        "p_min":450000,"p_max":3500000,"margen":0.22,
        "pais":"China/Taiwan","n":30,"sens_dolar":0.75,
    },
    "Smartphones": {
        "subcats": ["Gama Alta","Gama Media","Gama Baja","Reacondicionados"],
        "marcas":  ["Apple","Samsung","Xiaomi","Motorola","Realme","OPPO"],
        "p_min":80000,"p_max":1800000,"margen":0.28,
        "pais":"China/Corea del Sur","n":35,"sens_dolar":0.70,
    },
    "Accesorios": {
        "subcats": ["Cables y Cargadores","Cases y Fundas","Teclados y Mouse","Webcams","Hubs USB","Pendrives"],
        "marcas":  ["Anker","Belkin","Logitech","Ugreen","WD","Kingston","Generic"],
        "p_min":3000,"p_max":120000,"margen":0.48,
        "pais":"China","n":40,"sens_dolar":0.25,
    },
    "Gaming": {
        "subcats": ["Headsets Gaming","Sillas Gaming","Monitores Gaming","Controles","Escritorios Gaming"],
        "marcas":  ["Razer","HyperX","Corsair","Secretlab","Logitech G","SteelSeries"],
        "p_min":25000,"p_max":900000,"margen":0.33,
        "pais":"China/USA","n":25,"sens_dolar":0.55,
    },
    "Audio": {
        "subcats": ["Audífonos Over-ear","Auriculares TWS","Parlantes Portátiles","Soundbars","Micrófonos"],
        "marcas":  ["Sony","JBL","Bose","Apple","Jabra","Marshall","Audio-Technica"],
        "p_min":15000,"p_max":700000,"margen":0.32,
        "pais":"China/Japón","n":20,"sens_dolar":0.50,
    },
}

ADJETIVOS = ["Pro","Plus","Air","Max","Ultra","Lite","SE","Neo","X","S","One","Mini",""]

def build_dim_producto():
    rows, pid = [], 1
    for cat, cfg in CATALOGO.items():
        for _ in range(cfg["n"]):
            sub    = random.choice(cfg["subcats"])
            marca  = random.choice(cfg["marcas"])
            precio = round(np.random.uniform(cfg["p_min"], cfg["p_max"]) / 1000) * 1000
            costo  = round(precio * (1 - cfg["margen"]) / 500) * 500
            adj    = random.choice(ADJETIVOS)
            yr     = random.randint(2022, 2025)
            nombre = " ".join(filter(None, [marca, sub, adj, str(yr)]))
            rows.append({
                "producto_id":       pid,
                "sku":               f"{cat[:3].upper()}-{str(pid).zfill(4)}",
                "nombre":            nombre,
                "categoria":         cat,
                "subcategoria":      sub,
                "marca":             marca,
                "precio_lista_clp":  int(precio),
                "costo_unitario_clp":int(costo),
                "es_importado":      True,
                "pais_origen":       cfg["pais"],
                # col interna para generación — NO se exporta al CSV final
                "_sens_dolar": round(cfg["sens_dolar"] + np.random.uniform(-0.15, 0.15), 2),
            })
            pid += 1
    return pd.DataFrame(rows)

# =============================================================
# SECCIÓN 3 — DIM_CLIENTE
# =============================================================
REGIONES = {
    "Metropolitana":  (["Las Condes","Providencia","Santiago","Ñuñoa","La Florida",
                         "Maipú","Puente Alto","Vitacura","La Reina","Peñalolén",
                         "San Miguel","Macul","Lo Barnechea","Estación Central","Quilicura"], 0.40),
    "Valparaíso":     (["Valparaíso","Viña del Mar","Quilpué","Villa Alemana","San Antonio"], 0.15),
    "Biobío":         (["Concepción","Talcahuano","Chiguayante","Hualpén","Los Ángeles"], 0.12),
    "La Araucanía":   (["Temuco","Padre Las Casas","Villarrica","Angol","Victoria"], 0.07),
    "Los Lagos":      (["Puerto Montt","Osorno","Castro","Puerto Varas","Ancud"], 0.06),
    "Maule":          (["Talca","Curicó","Linares","Cauquenes","Constitución"], 0.06),
    "O'Higgins":     (["Rancagua","San Fernando","Pichilemu","Santa Cruz","Rengo"], 0.05),
    "Antofagasta":    (["Antofagasta","Calama","Tocopilla","Mejillones","Taltal"], 0.04),
    "Coquimbo":       (["La Serena","Coquimbo","Ovalle","Illapel","Vicuña"], 0.03),
    "Los Ríos":       (["Valdivia","La Unión","Panguipulli","Río Bueno","Corral"], 0.02),
}
CANALES_ADQ = ["Orgánico","Google Ads","Facebook/Instagram","Referido","Email Marketing","TikTok"]

def build_dim_cliente():
    reg_names  = list(REGIONES.keys())
    reg_probs  = [v[1] for v in REGIONES.values()]
    reg_comunas= [v[0] for v in REGIONES.values()]
    rows = []
    for i in range(N_CLIENTES):
        ri     = np.random.choice(len(reg_names), p=reg_probs)
        region = reg_names[ri]
        rows.append({
            "cliente_id":       i + 1,
            "nombre":           fake.name(),
            "email":            fake.email(),
            "region":           region,
            "comuna":           random.choice(reg_comunas[ri]),
            "segmento_rfm":     "Pendiente",   # se actualiza al final
            "fecha_registro":   fake.date_between(date(2023,1,1), date(2025,6,30)).isoformat(),
            "canal_adquisicion":random.choice(CANALES_ADQ),
            "_es_premium":      random.random() < 0.15,  # col interna
        })
    return pd.DataFrame(rows)

# =============================================================
# SECCIÓN 4 — INDICADORES ECONÓMICOS SIMULADOS
# =============================================================
def build_dolar_serie():
    """Dólar simulado con tendencia alcista y shock ago-sep 2024."""
    n = (END_DATE - START_DATE).days + 1
    trend  = np.linspace(950, 1020, n)
    noise  = np.cumsum(np.random.normal(0, 2.5, n))
    shock  = np.zeros(n)
    shock[210:260] = np.linspace(0, 60, 50)
    shock[260:310] = np.linspace(60, 20, 50)
    shock[310:]    = 20
    return np.clip(trend + noise + shock, 850, 1100)

DESEMPLEO = {
    **{(2024,m): v for m,v in zip(range(1,13), [8.5,8.8,8.6,8.4,8.7,8.9,8.8,8.5,8.3,8.2,8.0,7.9])},
    **{(2025,m): v for m,v in zip(range(1,13), [8.1,8.3,8.2,8.0,7.9,7.8,7.6,7.5,7.4,7.3,7.2,7.1])},
}

# =============================================================
# SECCIÓN 5 — FACT_VENTAS
# =============================================================
CANALES_VENTA = ["Web","App Móvil","Marketplace","Redes Sociales"]
METODOS_PAGO  = ["Tarjeta Crédito","Débito","Transferencia","WebPay","Cuotas sin interés"]
CANAL_W       = [0.35, 0.30, 0.25, 0.10]

EVENTO_MULT = {
    "CyberDay":4.0,"CyberMonday":3.5,"Black Friday":3.0,"Navidad":2.5,
    "Día de la Madre":2.0,"Día del Padre":1.6,"Vuelta al Cole":1.8,
    "Fiestas Patrias":1.3,"Normal":1.0,
}

def dolar_impact(dolar_val, dolar_mean, dolar_std, sens, es_premium):
    z = (dolar_val - dolar_mean) / dolar_std
    adj = sens * (0.3 if es_premium else 1.0)
    return max(0.45, 1 - z * adj * 0.22)

def build_fact_ventas(dim_tiempo, dim_producto, dim_cliente, dolar_serie):
    prod_list   = dim_producto.to_dict("records")
    cli_map     = {r["cliente_id"]: r for r in dim_cliente.to_dict("records")}
    cli_ids     = list(cli_map.keys())

    # Pesos de venta por categoría (accesorios venden más unidades)
    cat_w = {"Accesorios":4.0,"Smartphones":2.5,"Audio":2.0,"Gaming":1.5,"Laptops":1.0}
    pw = np.array([cat_w.get(p["categoria"],1.0) for p in prod_list])
    pw = pw / pw.sum()

    dolar_mean = dolar_serie.mean()
    dolar_std  = dolar_serie.std()

    rows, vid = [], 1
    for _, tr in dim_tiempo.iterrows():
        d_cur    = date.fromisoformat(tr["fecha"])
        day_idx  = (d_cur - START_DATE).days
        dolar_hoy= dolar_serie[day_idx]
        desem    = DESEMPLEO.get((d_cur.year, d_cur.month), 8.5)
        desemp_m = max(0.6, 1 - (desem - 7.0) * 0.05)

        n_trans  = int(np.random.poisson(
            BASE_DAILY
            * EVENTO_MULT.get(tr["evento_comercial"], 1.0)
            * (1.4 if tr["es_fin_semana"] else 1.0)
            * (1.12 if d_cur.year == 2025 else 1.0)
        ))

        prod_idx = np.random.choice(len(prod_list), size=n_trans, p=pw)
        cli_samp = random.choices(cli_ids, k=n_trans)

        for i in range(n_trans):
            prod = prod_list[prod_idx[i]]
            cli  = cli_map[cli_samp[i]]

            dol_m = dolar_impact(dolar_hoy, dolar_mean, dolar_std,
                                 prod["_sens_dolar"], cli["_es_premium"])
            emp_m = desemp_m if prod["precio_lista_clp"] < 300000 else 1.0

            if random.random() > (dol_m * emp_m):
                continue

            cantidad = random.choices([1,2,3],[0.60,0.30,0.10])[0]                        if prod["categoria"] == "Accesorios" else 1

            ev = tr["evento_comercial"]
            if ev in ["CyberDay","CyberMonday","Black Friday"]:
                desc = round(random.uniform(0.10, 0.38), 2)
            elif ev in ["Navidad","Día de la Madre"]:
                desc = round(random.uniform(0.05, 0.20), 2)
            elif ev in ["Vuelta al Cole","Fiestas Patrias"]:
                desc = round(random.uniform(0.03, 0.15), 2)
            else:
                desc = random.choices([0.0,0.0,0.05,0.10],[0.55,0.20,0.15,0.10])[0]

            rows.append({
                "venta_id":            vid,
                "fecha_id":            tr["fecha_id"],
                "cliente_id":          cli["cliente_id"],
                "producto_id":         prod["producto_id"],
                "cantidad":            cantidad,
                "precio_unitario_clp": prod["precio_lista_clp"],
                "descuento_pct":       desc,
                "monto_total_clp":     round(prod["precio_lista_clp"] * cantidad * (1 - desc)),
                "canal_venta":         np.random.choice(CANALES_VENTA, p=CANAL_W),
                "metodo_pago":         random.choice(METODOS_PAGO),
            })
            vid += 1
    return pd.DataFrame(rows)

# =============================================================
# SECCIÓN 6 — RFM (post-ventas)
# =============================================================
def calcular_rfm(fact_ventas, dim_tiempo):
    fv = fact_ventas.merge(dim_tiempo[["fecha_id","fecha"]], on="fecha_id")
    fv["fecha_dt"] = pd.to_datetime(fv["fecha"])
    corte = pd.Timestamp(END_DATE)

    rfm = fv.groupby("cliente_id").agg(
        ultima=("fecha_dt","max"),
        frec=("venta_id","count"),
        monto=("monto_total_clp","sum")
    ).reset_index()
    rfm["recency"] = (corte - rfm["ultima"]).dt.days
    rfm["r"] = pd.qcut(rfm["recency"], 5, labels=[5,4,3,2,1]).astype(int)
    rfm["f"] = pd.qcut(rfm["frec"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    rfm["m"] = pd.qcut(rfm["monto"], 5, labels=[1,2,3,4,5]).astype(int)

    def seg(row):
        r, f = row["r"], row["f"]
        if r >= 4 and f >= 4: return "Champions"
        if r >= 3 and f >= 3: return "Loyal"
        if r >= 4 and f <= 2: return "New"
        if r >= 3 and f <= 2: return "Potential"
        if r == 2:            return "At Risk"
        if r == 1 and f >= 3: return "Hibernating"
        return "Lost"

    rfm["segmento_rfm"] = rfm.apply(seg, axis=1)
    return rfm.set_index("cliente_id")["segmento_rfm"]

# =============================================================
# MAIN
# =============================================================
if __name__ == "__main__":
    print("🚀 Generando dataset sintético TechStore.cl...")

    print("   [1/5] Dimensión tiempo...")
    dt = build_dim_tiempo()

    print("   [2/5] Dimensión producto...")
    dp = build_dim_producto()

    print("   [3/5] Dimensión cliente...")
    dc = build_dim_cliente()

    print("   [4/5] Generando transacciones (puede tardar ~30 seg)...")
    dolar = build_dolar_serie()
    fv    = build_fact_ventas(dt, dp, dc, dolar)

    print("   [5/5] Calculando segmentación RFM...")
    seg_map = calcular_rfm(fv, dt)
    dc["segmento_rfm"] = dc["cliente_id"].map(seg_map).fillna("New")

    # Guardar — sin columnas internas
    dt.to_csv(f"{OUTPUT_DIR}/dim_tiempo.csv", index=False)
    dp.drop(columns=["_sens_dolar"]).to_csv(f"{OUTPUT_DIR}/dim_producto.csv", index=False)
    dc.drop(columns=["_es_premium"]).to_csv(f"{OUTPUT_DIR}/dim_cliente.csv", index=False)
    fv.to_csv(f"{OUTPUT_DIR}/fact_ventas.csv", index=False)

    # Serie dólar de referencia (la ETL real la reemplazará con mindicador.cl)
    n = (END_DATE - START_DATE).days + 1
    dates = [START_DATE + timedelta(days=i) for i in range(n)]
    pd.DataFrame({"fecha":[d.isoformat() for d in dates], "dolar_simulado": dolar.round(2)})       .to_csv(f"{OUTPUT_DIR}/dolar_serie_referencia.csv", index=False)

    print(f"\n✅ Dataset generado exitosamente en ./{OUTPUT_DIR}/")
    print(f"   dim_tiempo.csv    → {len(dt):,} filas")
    print(f"   dim_producto.csv  → {len(dp):,} filas")
    print(f"   dim_cliente.csv   → {len(dc):,} filas")
    print(f"   fact_ventas.csv   → {len(fv):,} transacciones")
    print(f"\n💰 Ventas totales: ${fv['monto_total_clp'].sum()/1e9:.2f} mil millones CLP")
