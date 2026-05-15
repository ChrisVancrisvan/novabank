from pathlib import Path

import pandas as pd


# CARGAR FEATURES

DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'processed'

features = pd.read_csv(
    DATA_DIR / 'features.csv'
)


# FUNCIÓN PRINCIPAL

def get_user_data(user_id):

    user = features[
        features['user_id'] == user_id
    ]


    if user.empty:

        return None


    return {

        'cluster':
        int(user['cluster'].values[0]),


        'gasto_total':
        float(user['gasto_total'].values[0]),


        'cashback_total':
        float(user['cashback_total'].values[0]),


        'categoria_favorita':
        str(user['categoria_favorita'].values[0]),


        'num_transacciones':
        int(user['num_transacciones'].values[0])
    }
