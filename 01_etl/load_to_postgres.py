"""
load_to_postgres.py
===================
Carga los CSVs generados a PostgreSQL usando SQLAlchemy + psycopg2.
Proyecto: Retail Analytics Chile — portfolio-analista-datos

Características:
  - Carga en el orden correcto respetando foreign keys
  - Upsert (INSERT ... ON CONFLICT) — no duplica si ya existen datos
  - Logging con timestamp a consola y archivo
  - Validación de row counts al finalizar
  - Configurable vía .env

Uso:
    # Carga completa (todas las tablas)
    python 01_etl/load_to_postgres.py

    # Solo una tabla específica
    python 01_etl/load_to_postgres.py --tabla dim_tiempo

Requisitos:
    pip install sqlalchemy psycopg2-binary pandas python-dotenv
"""

import os
import sys
import logging
import argparse
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# ── Logging ───────────────────────────────────────────────────
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = f"{LOG_DIR}/load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────
load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5432"),
    "dbname":   os.getenv("DB_NAME",     "retail_analytics"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}
SCHEMA    = "retail"
DATA_DIR  = Path("data/raw")

# ── Orden de carga (respeta foreign keys) ─────────────────────
# fact_ventas SIEMPRE al final — depende de las 3 dimensiones
TABLAS = [
    {
        "nombre":  "dim_tiempo",
        "csv":     "dim_tiempo.csv",
        "pk":      "fecha_id",
        "dtypes":  {
            "fecha_id":           "int",
            "año":                "int",
            "trimestre":          "int",
            "mes":                "int",
            "dia":                "int",
            "numero_dia_semana":  "int",
            "es_fin_semana":      "bool",
            "es_feriado":         "bool",
            "semana_año":         "int",
        },
        "parse_dates": ["fecha"],
    },
    {
        "nombre":  "dim_producto",
        "csv":     "dim_producto.csv",
        "pk":      "producto_id",
        "dtypes":  {
            "producto_id":        "int",
            "precio_lista_clp":   "int",
            "costo_unitario_clp": "int",
            "es_importado":       "bool",
        },
        "parse_dates": [],
    },
    {
        "nombre":  "dim_cliente",
        "csv":     "dim_cliente.csv",
        "pk":      "cliente_id",
        "dtypes":  {"cliente_id": "int"},
        "parse_dates": ["fecha_registro"],
    },
    {
        "nombre":  "dim_indicadores_economicos",
        "csv":     "dim_indicadores_economicos.csv",
        "pk":      "fecha_id",
        "dtypes":  {"fecha_id": "int", "utm": "int"},
        "parse_dates": [],
        "drop_cols": ["fecha"],
    },
    {
        "nombre":  "fact_ventas",
        "csv":     "fact_ventas.csv",
        "pk":      "venta_id",
        "dtypes":  {
            "venta_id":            "int",
            "fecha_id":            "int",
            "cliente_id":          "int",
            "producto_id":         "int",
            "cantidad":            "int",
            "precio_unitario_clp": "int",
            "monto_total_clp":     "int",
        },
        "parse_dates": [],
    },
]

# =============================================================
# FUNCIONES
# =============================================================

def get_engine():
    """Crea y valida la conexión a PostgreSQL."""
    url = (
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    )
    engine = create_engine(url, pool_pre_ping=True)
    # Validar que la conexión funciona
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


def leer_csv(cfg: dict) -> pd.DataFrame:
    """Lee y prepara un CSV con los tipos correctos."""
    path = DATA_DIR / cfg["csv"]
    if not path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {path}")

    df = pd.read_csv(
        path,
        dtype=str,                       # leer todo como string primero        
        low_memory=False,
    ).dropna(how="all")   ## eliminar filas completamente vacías (si las hay)

    # Castear columnas con tipos definidos
    for col, tipo in cfg["dtypes"].items():
        if col not in df.columns:
            continue
        if tipo == "int":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif tipo == "bool":
            df[col] = df[col].map({"True": True, "False": False, "1": True, "0": False})
        elif tipo == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in cfg.get("parse_dates", []):
        if col in df.columns:
            parsed = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
            if parsed.isna().any():
                bad = df.loc[parsed.isna(), col].dropna().head(5).tolist()
                raise ValueError(f"Column {col} contiene fechas inválidas en {cfg['csv']}")
            df[col] = parsed.dt.date

    for col in cfg.get("drop_cols", []):
        if col in df.columns:
            df = df.drop(columns=[col])

    if cfg["nombre"] == "dim_cliente" and "email" in df.columns:
        df["email"] = df["email"].astype(str).str.strip().str.lower()
        dup_emails = df[df.duplicated(subset=["email"], keep=False)].sort_values("email")
        if not dup_emails.empty:
            log.warning(f"dim_cliente: se detectaron {dup_emails['email'].nunique()} emails duplicados en el CSV; se conservará la última ocurrencia por email.")
            df = df.drop_duplicates(subset=["email"], keep="last")
        if "cliente_id" in df.columns:
            dup_ids = df[df.duplicated(subset=["cliente_id"], keep=False)].sort_values("cliente_id")
            if not dup_ids.empty:
                log.warning(f"dim_cliente: se detectaron {dup_ids['cliente_id'].nunique()} cliente_id duplicados; se conservará la última ocurrencia por cliente_id.")
                df = df.drop_duplicates(subset=["cliente_id"], keep="last")

    return df

def filtrar_fact_ventas(engine, df: pd.DataFrame) -> pd.DataFrame:
    with engine.connect() as conn:
        clientes = set(pd.read_sql(text(f"SELECT cliente_id FROM {SCHEMA}.dim_cliente"), conn)["cliente_id"].astype(int))
        productos = set(pd.read_sql(text(f"SELECT producto_id FROM {SCHEMA}.dim_producto"), conn)["producto_id"].astype(int))
        fechas = set(pd.read_sql(text(f"SELECT fecha_id FROM {SCHEMA}.dim_tiempo"), conn)["fecha_id"].astype(int))

    antes = len(df)
    df = df[df["cliente_id"].isin(clientes) & df["producto_id"].isin(productos) & df["fecha_id"].isin(fechas)].copy()
    descartadas = antes - len(df)
    if descartadas:
        log.warning(f"fact_ventas: se descartaron {descartadas} filas por claves foráneas inexistentes.")
    return df


def upsert_tabla(engine, df: pd.DataFrame, cfg: dict) -> int:
    """
    Carga un DataFrame a PostgreSQL usando INSERT ... ON CONFLICT DO UPDATE.
    Actualiza todas las columnas si la PK ya existe.
    Retorna el número de filas procesadas.
    """
    tabla = cfg["nombre"]
    pk = cfg["pk"]
    conflict_target = cfg.get("conflict_target", pk)
    schema_tbl = f"{SCHEMA}.{tabla}"
    cols = list(df.columns)
    cols_str = ", ".join(cols)
    vals_str = ", ".join([f":{c}" for c in cols])
    excluded_cols = set(cfg.get("update_exclude", [])) | {conflict_target}
    update_cols = [c for c in cols if c not in excluded_cols]

    if not update_cols:
        conflict_clause = f"ON CONFLICT ({conflict_target}) DO NOTHING"
    else:
        update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        conflict_clause = f"ON CONFLICT ({conflict_target}) DO UPDATE SET {update_str}"

    upsert_sql = text(f"""
        INSERT INTO {schema_tbl} ({cols_str})
        VALUES ({vals_str})
        {conflict_clause}
    """)

    rows = df.to_dict(orient="records")
    BATCH_SIZE = 1000
    total = 0

    with engine.begin() as conn:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            conn.execute(upsert_sql, batch)
            total += len(batch)
            log.info(f"   {tabla}: {total:,}/{len(rows):,} filas insertadas/actualizadas...")

    return total


def contar_filas(engine, tabla: str) -> int:
    """Cuenta las filas actuales en una tabla."""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{tabla}"))
        return result.scalar()


def validar_carga(engine, resultados: dict, tablas_intentadas: list):
    log.info("")
    log.info("=" * 55)
    log.info("  VALIDACIÓN DE CARGA")
    log.info("=" * 55)
    log.info(f"  {'Tabla':<35} {'Esperado':>9} {'En BD':>9} {'Estado':>8}")
    log.info(f"  {'─'*35} {'─'*9} {'─'*9} {'─'*8}")

    todo_ok = True
    for tabla in tablas_intentadas:
        esperado = resultados.get(tabla, 0)
        try:
            en_bd = contar_filas(engine, tabla)
            ok = esperado > 0 and en_bd >= esperado
            estado = "✅ OK" if ok else "❌ ERROR"
            if not ok:
                todo_ok = False
            log.info(f"  {tabla:<35} {esperado:>9,} {en_bd:>9,} {estado:>8}")
        except Exception:
            todo_ok = False
            log.info(f"  {tabla:<35} {esperado:>9,} {'-':>9} {'❌ ERROR':>8}")

    log.info("=" * 55)
    if todo_ok:
        log.info("  ✅ Todas las tablas cargadas correctamente.")
    else:
        log.warning("  ⚠️  Algunas tablas fallaron o tienen menos filas de lo esperado.")
    return todo_ok


# =============================================================
# MAIN
# =============================================================

def main(tabla_filtro: str = None):
    log.info("=" * 55)
    log.info("  CARGA A POSTGRESQL — TechStore Retail Analytics")
    log.info("=" * 55)
    log.info(f"  Host:   {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    log.info(f"  DB:     {DB_CONFIG['dbname']}")
    log.info(f"  Schema: {SCHEMA}")
    log.info(f"  Log:    {log_file}")
    log.info("")

    log.info("🔌 Conectando a PostgreSQL...")
    try:
        engine = get_engine()
        log.info("   Conexión exitosa ✅")
    except Exception as e:
        log.error(f"   No se pudo conectar: {e}")
        log.error("   Verifica que PostgreSQL esté corriendo y el .env esté configurado.")
        sys.exit(1)

    tablas_a_cargar = TABLAS
    if tabla_filtro:
        tablas_a_cargar = [t for t in TABLAS if t["nombre"] == tabla_filtro]
        if not tablas_a_cargar:
            log.error(f"Tabla '{tabla_filtro}' no encontrada. Opciones: {[t['nombre'] for t in TABLAS]}")
            sys.exit(1)

    resultados = {}
    tablas_intentadas = [t["nombre"] for t in tablas_a_cargar]
    inicio_total = time.time()

    for cfg in tablas_a_cargar:
        tabla = cfg["nombre"]
        log.info(f"📦 Cargando {tabla}...")
        inicio = time.time()

        try:
            df = leer_csv(cfg)
            if cfg["nombre"] == "fact_ventas":
                df = filtrar_fact_ventas(engine, df)
            log.info(f"   CSV leído: {len(df):,} filas, {len(df.columns)} columnas")
            filas = upsert_tabla(engine, df, cfg)
            elapsed = time.time() - inicio
            log.info(f"   ✅ {tabla}: {filas:,} filas en {elapsed:.1f}s")
            resultados[tabla] = filas
        except FileNotFoundError as e:
            log.error(f"   ❌ {e}")
        except SQLAlchemyError as e:
            log.error(f"   ❌ Error SQL en {tabla}: {e}")
        except Exception as e:
            log.error(f"   ❌ Error inesperado en {tabla}: {e}")

        log.info("")

    if resultados:
        validar_carga(engine, resultados, tablas_intentadas)

    elapsed_total = time.time() - inicio_total
    log.info(f"\n⏱️  Tiempo total: {elapsed_total:.1f}s")
    log.info("")
    log.info("🚀 Siguiente paso:")
    log.info("   1. Abrir pgAdmin → Query Tool")
    log.info("   2. Ejecutar: CALL retail.sp_calcular_segmentacion_rfm('2025-12-31');")
    log.info("   3. Abrir Power BI → conectar a v_ventas_enriquecidas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Carga CSVs de TechStore a PostgreSQL con upsert."
    )
    parser.add_argument(
        "--tabla",
        type=str,
        default=None,
        help="Cargar solo una tabla específica (opcional). "
             "Opciones: dim_tiempo, dim_producto, dim_cliente, "
             "dim_indicadores_economicos, fact_ventas",
    )
    args = parser.parse_args()
    main(tabla_filtro=args.tabla)