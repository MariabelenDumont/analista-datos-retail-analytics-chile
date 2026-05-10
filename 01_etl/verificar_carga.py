import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
SCHEMA = 'retail'
DATA_DIR = Path('data/raw')
OUT = Path('output')
OUT.mkdir(exist_ok=True)

TABLES = [
    ('dim_tiempo.csv', 'dim_tiempo', 'fecha_id', ['fecha_id']),
    ('dim_producto.csv', 'dim_producto', 'producto_id', ['producto_id']),
    ('dim_cliente.csv', 'dim_cliente', 'cliente_id', ['cliente_id']),
    ('dim_indicadores_economicos.csv', 'dim_indicadores_economicos', 'fecha_id', ['fecha_id']),
]


def eng():
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','')}@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','portfolio_data_analytics')}"
    )


def read_csv(name, key_cols):
    df = pd.read_csv(DATA_DIR / name, dtype=str, low_memory=False).dropna(how='all')
    for c in key_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')
    if name == 'dim_cliente.csv' and 'email' in df.columns:
        df['email'] = df['email'].astype(str).str.strip().str.lower()
    return df


def load_db(table):
    with eng().connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM {SCHEMA}.{table}"), conn)


def compare_dimension(csv_name, table, key_col, key_cols):
    src = read_csv(csv_name, key_cols)
    db = load_db(table)
    src_keys = set(src[key_col].dropna().astype(int))
    db_keys = set(db[key_col].dropna().astype(int))
    missing_in_db = sorted(src_keys - db_keys)
    extra_in_db = sorted(db_keys - src_keys)
    dup_src = int(src[key_col].duplicated().sum()) if key_col in src.columns else None
    dup_db = int(db[key_col].duplicated().sum()) if key_col in db.columns else None
    return {
        'tabla': table,
        'csv_rows': len(src),
        'db_rows': len(db),
        'csv_distinct_keys': len(src_keys),
        'db_distinct_keys': len(db_keys),
        'missing_in_db': len(missing_in_db),
        'extra_in_db': len(extra_in_db),
        'csv_duplicate_keys': dup_src,
        'db_duplicate_keys': dup_db,
        'missing_samples': missing_in_db[:10],
        'extra_samples': extra_in_db[:10],
        'status': 'OK' if len(missing_in_db) == 0 and len(extra_in_db) == 0 else 'REVISAR'
    }


def compare_fact():
    src = read_csv('fact_ventas.csv', ['venta_id', 'fecha_id', 'cliente_id', 'producto_id'])
    with eng().connect() as conn:
        clientes = set(pd.read_sql(text(f"SELECT cliente_id FROM {SCHEMA}.dim_cliente"), conn)['cliente_id'].astype(int))
        productos = set(pd.read_sql(text(f"SELECT producto_id FROM {SCHEMA}.dim_producto"), conn)['producto_id'].astype(int))
        fechas = set(pd.read_sql(text(f"SELECT fecha_id FROM {SCHEMA}.dim_tiempo"), conn)['fecha_id'].astype(int))
        db = pd.read_sql(text(f"SELECT venta_id, fecha_id, cliente_id, producto_id FROM {SCHEMA}.fact_ventas"), conn)

    valid = src['cliente_id'].isin(clientes) & src['producto_id'].isin(productos) & src['fecha_id'].isin(fechas)
    expected = src.loc[valid].copy()
    expected_ids = set(expected['venta_id'].dropna().astype(int))
    db_ids = set(db['venta_id'].dropna().astype(int))

    missing_in_db = sorted(expected_ids - db_ids)
    extra_in_db = sorted(db_ids - expected_ids)
    discarded = src.loc[~valid, ['venta_id', 'fecha_id', 'cliente_id', 'producto_id']]

    return {
        'tabla': 'fact_ventas',
        'csv_rows': len(src),
        'db_rows': len(db),
        'expected_loadable_rows': len(expected),
        'missing_in_db': len(missing_in_db),
        'extra_in_db': len(extra_in_db),
        'discarded_rows': len(discarded),
        'missing_samples': missing_in_db[:10],
        'extra_samples': extra_in_db[:10],
        'discarded_samples': discarded.head(20).to_dict(orient='records'),
        'status': 'OK' if len(missing_in_db) == 0 and len(extra_in_db) == 0 else 'REVISAR'
    }


rows = []
for csv_name, table, key_col, key_cols in TABLES:
    rows.append(compare_dimension(csv_name, table, key_col, key_cols))
rows.append(compare_fact())

summary = pd.DataFrame(rows)
summary.to_csv(OUT / 'reporte_verificacion_carga.csv', index=False)
print(summary[['tabla', 'status', 'csv_rows', 'db_rows']].to_string(index=False))
print(f"\nArchivo generado: {OUT / 'reporte_verificacion_carga.csv'}")
