import pandas as pd

from db import engine


# =========================
# OBTENER USUARIO
# =========================

def get_user_data(user_id):


    query = f"""

    SELECT *

    FROM clientes

    WHERE user_id = '{user_id}'

    LIMIT 1

    """


    df = pd.read_sql(

        query,

        engine
    )


    if df.empty:

        return None


    return df.iloc[0].to_dict()