from datetime import datetime, timedelta
import uuid

import pandas as pd
from sqlalchemy import text

from db import engine


PRODUCT_CATALOG = {
    "cuenta_debito": {
        "nombre": "Cuenta Debito",
        "descripcion": "Cuenta de dinero disponible para pagos, transferencias y recargas.",
        "can_transfer_from": True,
        "can_transfer_to": True,
        "can_recharge_from": True,
    },
    "cuenta_negocios": {
        "nombre": "Cuenta Negocios",
        "descripcion": "Cuenta operativa para flujo de negocio.",
        "can_transfer_from": True,
        "can_transfer_to": True,
        "can_recharge_from": True,
    },
    "inversion_hey": {
        "nombre": "Inversion Hey",
        "descripcion": "Producto de inversion con saldo consultable.",
        "can_transfer_from": True,
        "can_transfer_to": True,
        "can_recharge_from": True,
    },
    "tarjeta_credito_hey": {
        "nombre": "Tarjeta Credito Hey",
        "descripcion": "Linea de credito; puede recibir pagos, no se usa como saldo disponible.",
        "can_transfer_from": False,
        "can_transfer_to": True,
        "can_recharge_from": False,
    },
    "tarjeta_credito_negocios": {
        "nombre": "Tarjeta Credito Negocios",
        "descripcion": "Linea de credito empresarial; puede recibir pagos.",
        "can_transfer_from": False,
        "can_transfer_to": True,
        "can_recharge_from": False,
    },
    "tarjeta_credito_garantizada": {
        "nombre": "Tarjeta Credito Garantizada",
        "descripcion": "Tarjeta de credito respaldada por garantia; puede recibir pagos.",
        "can_transfer_from": False,
        "can_transfer_to": True,
        "can_recharge_from": False,
    },
    "credito_nomina": {
        "nombre": "Credito Nomina",
        "descripcion": "Credito de nomina; producto de deuda, no cuenta transaccional.",
        "can_transfer_from": False,
        "can_transfer_to": True,
        "can_recharge_from": False,
    },
    "credito_personal": {
        "nombre": "Credito Personal",
        "descripcion": "Credito personal; producto de deuda, no cuenta transaccional.",
        "can_transfer_from": False,
        "can_transfer_to": True,
        "can_recharge_from": False,
    },
    "credito_auto": {
        "nombre": "Credito Auto",
        "descripcion": "Credito automotriz; producto de deuda, no cuenta transaccional.",
        "can_transfer_from": False,
        "can_transfer_to": True,
        "can_recharge_from": False,
    },
    "seguro_vida": {
        "nombre": "Seguro Vida",
        "descripcion": "Seguro contratado; no tiene saldo operativo.",
        "can_transfer_from": False,
        "can_transfer_to": False,
        "can_recharge_from": False,
    },
    "seguro_compras": {
        "nombre": "Seguro Compras",
        "descripcion": "Seguro para compras; no tiene saldo operativo.",
        "can_transfer_from": False,
        "can_transfer_to": False,
        "can_recharge_from": False,
    },
}

ACCOUNT_ALIASES = {
    "debito": "cuenta_debito",
    "débito": "cuenta_debito",
    "cuenta debito": "cuenta_debito",
    "cuenta de debito": "cuenta_debito",
    "inversion": "inversion_hey",
    "inversión": "inversion_hey",
    "hey inversion": "inversion_hey",
    "negocio": "cuenta_negocios",
    "negocios": "cuenta_negocios",
    "cuenta negocio": "cuenta_negocios",
    "credito": "tarjeta_credito_hey",
    "crédito": "tarjeta_credito_hey",
    "tarjeta credito": "tarjeta_credito_hey",
    "tarjeta hey": "tarjeta_credito_hey",
    "nomina": "credito_nomina",
    "credito nomina": "credito_nomina",
    "personal": "credito_personal",
    "credito personal": "credito_personal",
    "auto": "credito_auto",
    "credito auto": "credito_auto",
    "vida": "seguro_vida",
    "seguro vida": "seguro_vida",
    "compras": "seguro_compras",
    "seguro compras": "seguro_compras",
    "garantizada": "tarjeta_credito_garantizada",
    "credito garantizada": "tarjeta_credito_garantizada",
}


def get_product_info(tipo_producto):
    tipo_producto = str(tipo_producto).strip().lower()
    return PRODUCT_CATALOG.get(
        tipo_producto,
        {
            "nombre": str(tipo_producto).replace("_", " ").title(),
            "descripcion": "Producto bancario.",
            "can_transfer_from": False,
            "can_transfer_to": False,
            "can_recharge_from": False,
        },
    )


def normalize_account_reference(account):
    value = str(account).strip().lower()
    return ACCOUNT_ALIASES.get(value, value)


def _to_float(value):
    try:
        if pd.isna(value) or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _is_active(account):
    return str(account.get("estatus", "")).strip().lower() == "activo"


def _account_payload(row):
    tipo_producto = str(row["tipo_producto"]).strip()
    info = get_product_info(tipo_producto)
    return {
        "producto_id": str(row["producto_id"]).strip(),
        "user_id": str(row["user_id"]).strip(),
        "tipo_producto": tipo_producto,
        "nombre_producto": info["nombre"],
        "descripcion_producto": info["descripcion"],
        "saldo_actual": float(row["saldo_actual"]),
        "estatus": str(row["estatus"]).strip(),
        "limite_credito": _to_float(row.get("limite_credito")),
        "utilizacion_pct": _to_float(row.get("utilizacion_pct")),
        "tasa_interes_anual": _to_float(row.get("tasa_interes_anual")),
        "plazo_meses": _to_float(row.get("plazo_meses")),
        "monto_mensualidad": _to_float(row.get("monto_mensualidad")),
        "fecha_apertura": str(row.get("fecha_apertura", "")),
        "fecha_ultimo_movimiento": str(row.get("fecha_ultimo_movimiento", "")),
        "can_transfer_from": bool(info["can_transfer_from"]),
        "can_transfer_to": bool(info["can_transfer_to"]),
        "can_recharge_from": bool(info["can_recharge_from"]),
    }


def _find_account(user_accounts, account_reference, capability=None):
    normalized = normalize_account_reference(account_reference)

    for acc in user_accounts:
        if acc["producto_id"].strip().lower() == normalized:
            if capability is None or acc.get(capability):
                return acc

    matches = [
        acc
        for acc in user_accounts
        if acc["tipo_producto"].strip().lower() == normalized
        and (capability is None or acc.get(capability))
    ]

    if not matches:
        return None

    active_matches = [acc for acc in matches if _is_active(acc)]
    return active_matches[0] if active_matches else matches[0]


def get_user_accounts(user_id):
    query = f"""
    SELECT *
    FROM productos
    WHERE user_id = '{user_id}'
    ORDER BY producto_id
    """

    user_accounts = pd.read_sql(query, engine)
    return [_account_payload(row) for _, row in user_accounts.iterrows()]


def get_operation_accounts(user_id, operation):
    accounts = get_user_accounts(user_id)

    if operation == "transfer_source":
        return [a for a in accounts if _is_active(a) and a["can_transfer_from"]]
    if operation == "transfer_target":
        return [a for a in accounts if _is_active(a) and a["can_transfer_to"]]
    if operation == "recharge_source":
        return [a for a in accounts if _is_active(a) and a["can_recharge_from"]]

    return accounts


def get_balance(user_id, producto_id=None):
    user_accounts = get_user_accounts(user_id)

    if not user_accounts:
        return {"error": "Usuario sin cuentas", "accounts": []}

    if producto_id is None:
        return {
            "multiple_accounts": len(user_accounts) > 1,
            "accounts": user_accounts,
        }

    account = _find_account(user_accounts, producto_id)
    if account is None:
        return {"error": "Cuenta no encontrada", "accounts": user_accounts}

    return {
        "multiple_accounts": False,
        "accounts": [account],
        "producto_id": account["producto_id"],
        "tipo_producto": account["tipo_producto"],
        "nombre_producto": account["nombre_producto"],
        "descripcion_producto": account["descripcion_producto"],
        "saldo_actual": account["saldo_actual"],
    }


def get_expenses(user_id, days=30):
    limit_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    query = f"""
    SELECT *
    FROM transacciones
    WHERE user_id = '{user_id}'
    AND fecha_hora >= '{limit_date}'
    AND monto > 0
    """

    user_transactions = pd.read_sql(query, engine)
    total_expenses = user_transactions["monto"].sum()
    return {
        "days": days,
        "total_expenses": round(float(total_expenses), 2),
        "transactions": len(user_transactions),
    }


def get_last_transactions(user_id, limit=5):
    query = f"""
    SELECT *
    FROM transacciones
    WHERE user_id = '{user_id}'
    ORDER BY fecha_hora DESC
    LIMIT {limit}
    """

    user_transactions = pd.read_sql(query, engine)
    results = []

    for _, row in user_transactions.iterrows():
        results.append(
            {
                "fecha": str(row["fecha_hora"]),
                "monto": float(row["monto"]),
                "categoria": str(row["categoria_mcc"]),
            }
        )

    return results


def transfer_between_accounts(user_id, from_account, to_account, amount):
    user_accounts = get_user_accounts(user_id)
    source = _find_account(user_accounts, from_account, "can_transfer_from")
    target = _find_account(user_accounts, to_account, "can_transfer_to")

    if source is None:
        return {"error": "Cuenta origen no encontrada o no disponible para transferir"}

    if target is None:
        return {"error": "Cuenta destino no encontrada o no disponible para recibir transferencia"}

    if source["producto_id"] == target["producto_id"]:
        return {"error": "La cuenta origen y destino no pueden ser la misma"}

    if source["saldo_actual"] < amount:
        return {"error": "Saldo insuficiente"}

    new_source_balance = source["saldo_actual"] - amount
    new_target_balance = target["saldo_actual"] + amount

    source_query = f"""
    UPDATE productos
    SET saldo_actual = {new_source_balance}
    WHERE producto_id = '{source['producto_id']}'
    """

    target_query = f"""
    UPDATE productos
    SET saldo_actual = {new_target_balance}
    WHERE producto_id = '{target['producto_id']}'
    """

    transaction_id = str(uuid.uuid4())
    insert_query = f"""
    INSERT INTO transacciones (
        transaccion_id,
        user_id,
        monto,
        categoria_mcc,
        fecha_hora
    )
    VALUES (
        '{transaction_id}',
        '{user_id}',
        {amount},
        'transferencia',
        NOW()
    )
    """

    with engine.begin() as conn:
        conn.execute(text(source_query))
        conn.execute(text(target_query))
        conn.execute(text(insert_query))

    return {
        "success": True,
        "from_account": source["tipo_producto"],
        "from_account_id": source["producto_id"],
        "to_account": target["tipo_producto"],
        "to_account_id": target["producto_id"],
        "amount": amount,
        "new_source_balance": new_source_balance,
        "new_target_balance": new_target_balance,
    }


def recharge_phone(user_id, phone_number, amount, from_account=None):
    if len(phone_number) != 10:
        return {"error": "El numero debe tener 10 digitos"}

    if not phone_number.isdigit():
        return {"error": "El numero solo debe contener digitos"}

    user_accounts = get_user_accounts(user_id)
    if not user_accounts:
        return {"error": "Usuario sin cuentas"}

    if from_account:
        source_account = _find_account(user_accounts, from_account, "can_recharge_from")
    else:
        source_account = next(
            (
                acc
                for acc in user_accounts
                if _is_active(acc)
                and acc["can_recharge_from"]
                and acc["saldo_actual"] >= amount
            ),
            None,
        )

    if source_account is None:
        return {"error": "No encontre una cuenta activa disponible para hacer la recarga"}

    if source_account["saldo_actual"] < amount:
        return {"error": "Saldo insuficiente"}

    new_balance = source_account["saldo_actual"] - amount
    update_query = f"""
    UPDATE productos
    SET saldo_actual = {new_balance}
    WHERE producto_id = '{source_account['producto_id']}'
    """

    transaction_id = str(uuid.uuid4())
    insert_query = f"""
    INSERT INTO transacciones (
        transaccion_id,
        user_id,
        monto,
        categoria_mcc,
        fecha_hora
    )
    VALUES (
        '{transaction_id}',
        '{user_id}',
        {amount},
        'recarga_celular',
        NOW()
    )
    """

    with engine.begin() as conn:
        conn.execute(text(update_query))
        conn.execute(text(insert_query))

    return {
        "success": True,
        "phone_number": phone_number,
        "amount": amount,
        "source_account": source_account["tipo_producto"],
        "source_account_id": source_account["producto_id"],
        "new_balance": new_balance,
    }
