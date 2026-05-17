import pandas as pd

from db import engine


# =========================
# OBTENER USUARIO
# =========================

def get_user_data(user_id):

    query = f"""
    SELECT f.cluster,
           f.gasto_promedio,
           f.cashback_total,
           f.categoria_favorita,
           f.num_transacciones
    FROM features f
    WHERE f.user_id = '{user_id}'
    LIMIT 1
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        return None

    return df.iloc[0].to_dict()