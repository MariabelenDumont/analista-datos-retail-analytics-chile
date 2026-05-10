"""
extract_mindicador_api.py
=========================
Extrae indicadores económicos REALES de Chile desde mindicador.cl
Proyecto: Retail Analytics Chile — portfolio-analista-datos

Indicadores extraídos:
  - UF           (diario)   — Unidad de Fomento
  - Dólar        (hábil)    — Tipo de cambio observado
  - Euro         (hábil)    — Tipo de cambio
  - IPC          (mensual)  — Índice de Precios al Consumidor
  - UTM          (mensual)  — Unidad Tributaria Mensual
  - Desempleo    (mensual)  — Tasa de desocupación
  - IMACEC       (mensual)  — Indicador de actividad económica

Output:
  data/raw/dim_indicadores_economicos.csv (731 filas, una por día)

API: https://mindicador.cl — pública, sin key, sin rate limit estricto

Uso:
    python 01_etl/extract_mindicador_api.py
"""

import pandas as pd
import requests
import time
import os
from datetime import date, datetime
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

# ── Configuración ─────────────────────────────────────────────
START_DATE   = date(2024, 1, 1) ## fecha hardcodeada, se puede parametrizar si se desea usar desde la terminal de forma dinámica
END_DATE     = date(2025, 12, 31) ## fecha hardcodeada, se puede parametrizar si se desea usar desde la terminal de forma dinámica
BASE_URL     = "https://mindicador.cl/api"
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw"
OUTPUT_FILE  = f"{OUTPUT_DIR}/dim_indicadores_economicos.csv"
SLEEP_SEC    = 0.4   # pausa entre llamadas para no saturar la API
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "extract_mindicador_api.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Indicadores a extraer ──────────────────────────────────────
# freq: "daily" → valor por cada día hábil
#       "monthly" → un valor por mes (se expande a todos los días del mes)
INDICADORES = {
    "uf":             {"freq": "daily",   "col": "uf"},
    "dolar":          {"freq": "daily",   "col": "dolar"},
    "euro":           {"freq": "daily",   "col": "euro"},
    "ipc":            {"freq": "monthly", "col": "ipc_mensual"},
    "utm":            {"freq": "monthly", "col": "utm"},
    "tasa_desempleo": {"freq": "monthly", "col": "tasa_desempleo"},
    "imacec":         {"freq": "monthly", "col": "imacec"},
}

# =============================================================
# FUNCIONES
# =============================================================
def setup_logger():
    logger = logging.getLogger("extract_mindicador_api")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

def fetch_serie(indicador: str, año: int, logger) -> pd.DataFrame:
    """
    Descarga la serie histórica de un indicador para un año dado.
    Retorna DataFrame con columnas [fecha (date), valor (float)].
    """
    url = f"{BASE_URL}/{indicador}/{año}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        serie = resp.json().get("serie", [])
        rows = []
        for reg in serie:
            # Fecha viene como ISO 8601 con zona horaria UTC
            fecha = pd.to_datetime(reg["fecha"]).date()
            rows.append({"fecha": fecha, "valor": float(reg["valor"])})
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["fecha", "valor"])
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error {indicador}/{año}: {e}")
        return pd.DataFrame(columns=["fecha", "valor"])
    except requests.exceptions.ConnectionError:
        logger.warning(f"Sin conexión al descargar {indicador}/{año}")
        return pd.DataFrame(columns=["fecha", "valor"])
    except Exception as e:
        logger.exception(f"Error inesperado {indicador}/{año}")
        return pd.DataFrame(columns=["fecha", "valor"])


def fetch_indicador_periodo(indicador: str, start: date, end: date, logger) -> pd.DataFrame:
    """
    Descarga un indicador para todos los años en el rango start..end.
    Filtra al rango exacto y elimina duplicados.
    """
    años = range(start.year, end.year + 1)
    frames = []
    for año in años:
        df = fetch_serie(indicador, año, logger)
        time.sleep(SLEEP_SEC)
        frames.append(df)

    if not frames or all(f.empty for f in frames):
        return pd.DataFrame(columns=["fecha", "valor"])

    combined = pd.concat(frames, ignore_index=True)
    combined = (
        combined
        .drop_duplicates("fecha")
        .sort_values("fecha")
        .query("fecha >= @start and fecha <= @end")
        .reset_index(drop=True)
    )
    return combined


def build_dim_indicadores(start: date, end: date, logger) -> pd.DataFrame:
    """
    Construye la tabla dim_indicadores_economicos con una fila por día.

    - Indicadores diarios (UF, dólar, euro): forward-fill para fines de semana
      y feriados. El primer día usa backward-fill si es feriado.
    - Indicadores mensuales (IPC, UTM, desempleo, IMACEC): el valor del mes
      se replica en todos los días de ese mes.
    """
    # Calendario base — una fila por día
    calendario = pd.DataFrame({
        "fecha": pd.date_range(start, end, freq="D").date
    })

    logger.info("Descargando indicadores desde mindicador.cl")
    logger.info(f"Período: {start} -> {end}")
    print()

    for nombre, cfg in INDICADORES.items():
        col = cfg["col"]
        logger.info(f"Procesando [{col}]")

        df_serie = fetch_indicador_periodo(nombre, start, end, logger)

        if df_serie.empty:
            logger.warning(f"{col}: sin datos, la columna quedará vacía")
            calendario[col] = None
            continue

        df_serie = df_serie.rename(columns={"valor": col})
        calendario = calendario.merge(df_serie, on="fecha", how="left")

        # Fill strategy
        calendario[col] = calendario[col].ffill().bfill()

        n = df_serie[col].notna().sum()
        logger.info(f"{col}: {n} puntos expandidos a {len(calendario)} días")

    # Agregar fecha_id (1-based, sincronizado con dim_tiempo)
    calendario.insert(0, "fecha_id", range(1, len(calendario) + 1))
    calendario["fecha"] = calendario["fecha"].astype(str)

    # Redondear
    rounding = {
        "uf": 2, "dolar": 2, "euro": 2,
        "ipc_mensual": 2, "utm": 0,
        "tasa_desempleo": 2, "imacec": 2
    }
    for col, dec in rounding.items():
        if col in calendario.columns:
            calendario[col] = calendario[col].round(dec)
            if dec == 0:
                calendario[col] = calendario[col].astype(int)

    return calendario


# =============================================================
# VALIDACIÓN
# =============================================================

def validar(df: pd.DataFrame, logger) -> bool:
    """Valida que el DataFrame esté completo y dentro de rangos esperados."""
    ok = True
    logger.info("🔍 Validando datos...")

    # Sin nulos
    nulls = df.isnull().sum()
    cols_con_nulls = nulls[nulls > 0]
    if not cols_con_nulls.empty:
        logger.warning(f"Columnas con nulos: {cols_con_nulls.to_dict()}")
        ok = False
    else:
        logger.info("Sin valores nulos")

    # Rango de fechas completo
    n_esperado = (END_DATE - START_DATE).days + 1
    if len(df) != n_esperado:
        logger.warning(f"  ⚠️  Filas esperadas: {n_esperado}, encontradas: {len(df)}")
        ok = False
    else:
        logger.info(f"  ✅ Filas correctas: {len(df)}")

    # Rangos razonables (Chile 2024-2025)
    checks = {
        "uf":             (35000, 42000), # valores harcodeados basados en tendencias recientes, pueden ajustarse según contexto
        "dolar":          (800,   1100), # valores harcodeados basados en tendencias recientes, pueden ajustarse según contexto
        "euro":           (850,   1200), # valores harcodeados basados en tendencias recientes, pueden ajustarse según contexto
        "tasa_desempleo": (5.0,   12.0), # valores harcodeados basados en tendencias recientes, pueden ajustarse según contexto
    }
    for col, (lo, hi) in checks.items():
        if col not in df.columns: continue
        mn, mx = df[col].min(), df[col].max()
        if mn < lo or mx > hi:
            logger.warning(f"{col} fuera de rango esperado: [{mn}, {mx}] (esperado [{lo}, {hi}])")
            ok = False
        else:
            logger.info(f"{col}: [{mn}, {mx}]")

    return ok


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":
    logger = setup_logger()
    logger.info("=" * 58)
    logger.info("Extracción de Indicadores Económicos — mindicador.cl")
    logger.info("=" * 58)   
    try:

        df = build_dim_indicadores(START_DATE, END_DATE, logger)

        valido = validar(df, logger)

        df.to_csv(OUTPUT_FILE, index=False)
        size_kb = os.path.getsize(OUTPUT_FILE) / 1024

        logger.info(f"Archivo guardado en {OUTPUT_FILE} ({size_kb:.1f} KB)")

        logger.info("Resumen de valores (promedios 2024-2025)")
        resumen = {
            "UF promedio":         f"${df['uf'].mean():,.2f}",
            "Dólar promedio":      f"${df['dolar'].mean():,.2f}",
            "Euro promedio":       f"${df['euro'].mean():,.2f}",
            "IPC promedio/mes":    f"{df['ipc_mensual'].mean():,.2f}%",
            "Desempleo promedio":  f"{df['tasa_desempleo'].mean():,.2f}%",
            "IMACEC promedio":     f"{df['imacec'].mean():,.2f}%",
        }
        for k, v in resumen.items():
            logger.info(f"{k:<25} {v}")

        if not valido:
            logger.warning("Revisa los warnings antes de cargar a PostgreSQL")
        else:
            logger.info("Datos validados. Siguiente paso: load_to_postgres.py")
    except Exception:
            logger.exception("Fallo inesperado en la ejecución principal")
            raise