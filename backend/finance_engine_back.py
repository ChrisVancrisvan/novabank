import pandas as pd

from datetime import datetime, timedelta


# =========================
# CARGAR DATASETS LIMPIOS
# =========================

transacciones = pd.read_csv(
    '../data/processed/transacciones_clean.csv'
)

productos = pd.read_csv(
    '../data/processed/productos_clean.csv'
)


# =========================
# FORMATO FECHAS
# =========================

transacciones['fecha_hora'] = pd.to_datetime(
    transacciones['fecha_hora'],
    #dayfirst=True
)


# =========================
# OBTENER CUENTAS USUARIO
# =========================

def get_user_accounts(user_id):


    user_accounts = productos[

        productos['user_id']
        == user_id

    ]


    results = []


    for _, row in user_accounts.iterrows():

        results.append({

            "producto_id":
            row['producto_id'],

            "tipo_producto":
            row['tipo_producto'],

            "saldo_actual":
            float(row['saldo_actual']),

            "estatus":
            row['estatus']
        })


    return results


# =========================
# CONSULTAR SALDO
# =========================

def get_balance(
    user_id,
    producto_id=None
):


    user_accounts = get_user_accounts(
        user_id
    )


    # SI NO EXISTE USUARIO

    if len(user_accounts) == 0:

        return {
            "error":
            "Usuario sin cuentas"
        }


    # SI SOLO TIENE UNA CUENTA

    if len(user_accounts) == 1:

        account = user_accounts[0]

        return {

            "multiple_accounts":
            False,

            "producto_id":
            account['producto_id'],

            "tipo_producto":
            account['tipo_producto'],

            "saldo_actual":
            account['saldo_actual']
        }


    # SI TIENE VARIAS Y NO ESPECIFICA

    if producto_id is None:

        return {

            "multiple_accounts":
            True,

            "accounts":
            user_accounts
        }


    # BUSCAR CUENTA ESPECÍFICA

    selected_account = None


    for account in user_accounts:

        if account['producto_id'] == producto_id:

            selected_account = account

            break


    # SI NO EXISTE

    if selected_account is None:

        return {

            "error":
            "Cuenta no encontrada"
        }


    return {

        "multiple_accounts":
        False,

        "producto_id":
        selected_account['producto_id'],

        "tipo_producto":
        selected_account['tipo_producto'],

        "saldo_actual":
        selected_account['saldo_actual']
    }


# =========================
# CONSULTAR GASTOS
# =========================

def get_expenses(
    user_id,
    days=30
):


    # FECHA ACTUAL

    now = datetime.now()


    # FECHA LÍMITE

    limit_date = now - timedelta(
        days=days
    )


    # FILTRAR USUARIO

    user_transactions = transacciones[

        (transacciones['user_id'] == user_id)

        &

        (transacciones['fecha_hora'] >= limit_date)

        &

        (transacciones['monto'] > 0)

    ]


    # SUMAR GASTOS

    total_expenses = user_transactions[
        'monto'
    ].sum()


    return {

        "days":
        days,

        "total_expenses":
        round(total_expenses, 2),

        "transactions":
        len(user_transactions)
    }


# =========================
# ÚLTIMOS MOVIMIENTOS
# =========================

def get_last_transactions(
    user_id,
    limit=5
):


    user_transactions = transacciones[

        transacciones['user_id']
        == user_id

    ]


    user_transactions = user_transactions.sort_values(
        by='fecha_hora',
        ascending=False
    )


    last_transactions = user_transactions.head(
        limit
    )


    results = []


    for _, row in last_transactions.iterrows():

        results.append({

            "fecha":
            str(row['fecha_hora']),

            "monto":
            float(row['monto']),

            "categoria":
            str(row['categoria_mcc'])
        })


    return results

# =========================
# TRANSFERENCIA ENTRE CUENTAS
# =========================

def transfer_between_accounts(
    user_id,
    from_account,
    to_account,
    amount
):


    user_accounts = get_user_accounts(
        user_id
    )


    source = None
    target = None


    # BUSCAR CUENTAS

    ACCOUNT_ALIASES = {

        "debito":
        "cuenta_debito",

        "débito":
        "cuenta_debito",

        "inversion":
        "inversion_hey",

        "inversión":
        "inversion_hey",

        "negocios":
        "cuenta_negocios",

        "credito":
        "tarjeta_credito_hey",

        "crédito":
        "tarjeta_credito_hey"
    }


    from_account_real = ACCOUNT_ALIASES.get(
        from_account.lower(),
        from_account.lower()
    )

    to_account_real = ACCOUNT_ALIASES.get(
        to_account.lower(),
        to_account.lower()
    )


    for acc in user_accounts:


        acc_type = acc[
            'tipo_producto'
        ].lower()


        if from_account_real == acc_type:

            source = acc


        if to_account_real == acc_type:

            target = acc


    # VALIDAR EXISTENCIA

    if source is None:

        return {
            "error":
            "Cuenta origen no encontrada"
        }


    if target is None:

        return {
            "error":
            "Cuenta destino no encontrada"
        }


    # VALIDAR SALDO

    if source['saldo_actual'] < amount:

        return {
            "error":
            "Saldo insuficiente"
        }


    # SIMULACIÓN TRANSFERENCIA

    source['saldo_actual'] -= amount

    target['saldo_actual'] += amount


    return {

        "success":
        True,

        "from_account":
        source['tipo_producto'],

        "to_account":
        target['tipo_producto'],

        "amount":
        amount,

        "new_source_balance":
        source['saldo_actual'],

        "new_target_balance":
        target['saldo_actual']
    }


# =========================
# RECARGA CELULAR
# =========================

def recharge_phone(

    user_id,

    phone_number,

    amount
):


    # VALIDAR NÚMERO

    if len(phone_number) != 10:

        return {

            "error":
            "El número debe tener 10 dígitos"
        }


    if not phone_number.isdigit():

        return {

            "error":
            "El número solo debe contener dígitos"
        }


    # OBTENER CUENTA

    balance_data = get_balance(
        user_id
    )


    # VALIDAR SALDO

    if balance_data.get(
        "saldo_actual",
        0
    ) < amount:

        return {

            "error":
            "Saldo insuficiente"
        }


    # SIMULAR DESCUENTO

    new_balance = (

        balance_data['saldo_actual']

        - amount
    )


    return {

        "success":
        True,

        "phone_number":
        phone_number,

        "amount":
        amount,

        "new_balance":
        new_balance
    }