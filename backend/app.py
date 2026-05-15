from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

from llm_engine import generate_response
from user_engine import get_user_data
from intent_engine import detect_intent
from finance_engine import (
    get_balance,
    get_expenses,
    get_last_transactions,
    get_operation_accounts,
    transfer_between_accounts,
    recharge_phone,
)
from conversation_memory import conversation_memory
from pdf_engine import (
    generate_transfer_pdf,
    generate_recharge_pdf,
)
from promotions_engine import get_promotions

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:*",
        "http://127.0.0.1",
        "http://127.0.0.1:*",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


FLOW_INTENTS = {"transferencia", "recarga_celular"}
CLEAR_SWITCH_INTENTS = {
    "consultar_saldo",
    "consultar_gastos",
    "ultimos_movimientos",
    "consultar_cashback",
    "recomendaciones",
}
CANCEL_WORDS = {"cancelar", "cancela", "salir", "detener", "reiniciar", "reset"}

CLUSTER_TONES = {
    0: {
        "segment": "Cliente Premium",
        "tone": "directo, ejecutivo y orientado a beneficios premium",
        "focus": "exclusividad, inversiones, viajes, proteccion y limites altos",
    },
    1: {
        "segment": "Cliente Ocasional",
        "tone": "claro, paciente y util, con pasos sencillos",
        "focus": "activar el uso cotidiano, ahorro simple y beneficios de entrada",
    },
    2: {
        "segment": "Cliente Atipico",
        "tone": "preciso, prudente y orientado a control de movimientos",
        "focus": "flujo de dinero, cuentas de negocio, movimientos altos y seguimiento",
    },
    3: {
        "segment": "Cliente Frecuente Estandar",
        "tone": "cercano, agil y practico",
        "focus": "cashback, categorias frecuentes, pagos diarios y lealtad",
    },
}


@app.get("/")
def root():
    return {"message": "NovaBank AI funcionando"}


def _response(user_id, intent, message, bot_response):
    return {
        "user_id": user_id,
        "intent": intent,
        "message_received": message,
        "bot_response": bot_response,
    }


def _load_user_context(user_id):
    user_data = get_user_data(user_id) or {}
    cluster = int(user_data.get("cluster", 3) or 3)
    profile = CLUSTER_TONES.get(cluster, CLUSTER_TONES[3])
    return {
        "data": user_data,
        "cluster": cluster,
        "segment": profile["segment"],
        "tone": profile["tone"],
        "focus": profile["focus"],
        "categoria": user_data.get("categoria_favorita", "General"),
        "cashback": float(user_data.get("cashback_total", 0) or 0),
        "gasto_promedio": float(user_data.get("gasto_promedio", 0) or 0),
        "num_transacciones": int(user_data.get("num_transacciones", 0) or 0),
    }


def _profile_block(ctx):
    return f"""
    PERFIL DEL CLIENTE:
    - Segmento: {ctx['segment']}
    - Cluster: {ctx['cluster']}
    - Categoria favorita: {ctx['categoria']}
    - Cashback acumulado: ${ctx['cashback']:,.2f} MXN
    - Gasto promedio: ${ctx['gasto_promedio']:,.2f} MXN
    - Numero de transacciones: {ctx['num_transacciones']}
    - Tono recomendado: {ctx['tone']}
    - Enfoque comercial: {ctx['focus']}
    """


def _personalized_prompt(ctx, message, real_data, instructions):
    return f"""
    Eres NovaBank AI, asistente bancario conversacional.

    {_profile_block(ctx)}

    MENSAJE DEL CLIENTE:
    "{message}"

    DATOS REALES DISPONIBLES:
    {real_data}

    REGLAS:
    - Responde en espanol mexicano, natural y breve.
    - Usa el perfil para ajustar tono y relevancia.
    - No mezcles temas: contesta solo la intencion actual.
    - No inventes datos, saldos, folios, fechas, beneficios ni comisiones.
    - Si falta un dato, pide solo ese dato.
    - No cierres con preguntas genericas si ya resolviste.

    INSTRUCCIONES DE ESTA RESPUESTA:
    {instructions}
    """


def _first_number(text):
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _digits_only(text):
    return re.sub(r"\D", "", text)


def _normalize_account(text):
    value = text.strip().lower()
    aliases = {
        "debito": "debito",
        "débito": "debito",
        "cuenta debito": "debito",
        "cuenta de debito": "debito",
        "inversion": "inversion",
        "inversión": "inversion",
        "hey inversion": "inversion",
        "negocio": "negocios",
        "negocios": "negocios",
        "cuenta negocio": "negocios",
        "credito": "credito",
        "crédito": "credito",
        "tarjeta credito": "credito",
    }
    return aliases.get(value, value)


def _format_money(value):
    return f"${float(value):,.2f} MXN"


def _format_account_line(account, include_capabilities=False):
    line = (
        f"- {account['nombre_producto']} ({account['tipo_producto']}, "
        f"ID {account['producto_id']}): {_format_money(account['saldo_actual'])} "
        f"[{account['estatus']}]"
    )

    details = []
    if account.get("limite_credito") is not None:
        details.append(f"limite {_format_money(account['limite_credito'])}")
    if account.get("monto_mensualidad") is not None:
        details.append(f"mensualidad {_format_money(account['monto_mensualidad'])}")
    if account.get("tasa_interes_anual") is not None:
        details.append(f"tasa {account['tasa_interes_anual']:.2f}%")
    if details:
        line += " | " + ", ".join(details)

    if include_capabilities:
        capabilities = []
        if account.get("can_transfer_from"):
            capabilities.append("origen transferencia")
        if account.get("can_transfer_to"):
            capabilities.append("destino/pago")
        if account.get("can_recharge_from"):
            capabilities.append("recarga")
        line += " | disponible para: " + (
            ", ".join(capabilities) if capabilities else "consulta solamente"
        )

    return line


def _format_accounts(accounts, include_capabilities=False):
    if not accounts:
        return "- No hay cuentas disponibles para esta operacion."
    return "\n".join(
        _format_account_line(account, include_capabilities)
        for account in accounts
    )


def _bump_retry(memory, slot):
    retries = memory.setdefault("retries", {})
    retries[slot] = retries.get(slot, 0) + 1
    return retries[slot]


def _reset_retry(memory, slot):
    memory.setdefault("retries", {}).pop(slot, None)


def _save(user_id, memory):
    conversation_memory[user_id] = memory


def _clear(user_id):
    conversation_memory[user_id] = {}


def _should_switch_topic(memory, detected_intent):
    active_intent = memory.get("intent")
    if not active_intent:
        return False
    if detected_intent in (None, "desconocido", active_intent):
        return False
    return detected_intent in CLEAR_SWITCH_INTENTS or detected_intent in FLOW_INTENTS


def _next_transfer_question(memory, user_id):
    if "amount" not in memory:
        source_accounts = get_operation_accounts(user_id, "transfer_source")
        return (
            "Cuanto deseas transferir?\n\n"
            "Cuentas disponibles como origen:\n"
            f"{_format_accounts(source_accounts)}"
        )
    if "from_account" not in memory:
        source_accounts = get_operation_accounts(user_id, "transfer_source")
        return (
            "Desde que cuenta quieres transferir? Puedes decirme el tipo o el ID.\n\n"
            "Cuentas disponibles como origen:\n"
            f"{_format_accounts(source_accounts)}"
        )
    if "to_account" not in memory:
        target_accounts = get_operation_accounts(user_id, "transfer_target")
        return (
            "A que cuenta destino quieres transferir? Puedes decirme el tipo o el ID.\n\n"
            "Cuentas disponibles como destino/pago:\n"
            f"{_format_accounts(target_accounts)}"
        )
    return None


def _next_recharge_question(memory, user_id):
    if "phone_number" not in memory:
        source_accounts = get_operation_accounts(user_id, "recharge_source")
        return (
            "Que numero celular de 10 digitos quieres recargar?\n\n"
            "La recarga puede salir de:\n"
            f"{_format_accounts(source_accounts)}"
        )
    if "amount" not in memory:
        source_accounts = get_operation_accounts(user_id, "recharge_source")
        return (
            "Cuanto quieres recargar?\n\n"
            "Cuentas disponibles para pagar la recarga:\n"
            f"{_format_accounts(source_accounts)}"
        )
    return None


def _apply_transfer_slots(memory, intent_data, message):
    pending = memory.get("pending_slot")
    if intent_data.get("amount") is not None and "amount" not in memory:
        memory["amount"] = float(intent_data["amount"])
        _reset_retry(memory, "amount")
    if intent_data.get("from_account") and "from_account" not in memory:
        memory["from_account"] = _normalize_account(intent_data["from_account"])
        _reset_retry(memory, "from_account")
    if intent_data.get("to_account") and "to_account" not in memory:
        memory["to_account"] = _normalize_account(intent_data["to_account"])
        _reset_retry(memory, "to_account")

    if pending == "amount" and "amount" not in memory:
        amount = _first_number(message)
        if amount is not None and amount > 0:
            memory["amount"] = amount
            _reset_retry(memory, "amount")
    elif pending == "from_account" and "from_account" not in memory:
        memory["from_account"] = _normalize_account(message)
        _reset_retry(memory, "from_account")
    elif pending == "to_account" and "to_account" not in memory:
        memory["to_account"] = _normalize_account(message)
        _reset_retry(memory, "to_account")


def _apply_recharge_slots(memory, intent_data, message):
    pending = memory.get("pending_slot")
    if intent_data.get("phone_number") and "phone_number" not in memory:
        memory["phone_number"] = _digits_only(str(intent_data["phone_number"]))
        _reset_retry(memory, "phone_number")
    if intent_data.get("amount") is not None and "amount" not in memory:
        memory["amount"] = float(intent_data["amount"])
        _reset_retry(memory, "amount")

    if pending == "phone_number" and "phone_number" not in memory:
        phone = _digits_only(message)
        if len(phone) == 10:
            memory["phone_number"] = phone
            _reset_retry(memory, "phone_number")
    elif pending == "amount" and "amount" not in memory:
        amount = _first_number(message)
        if amount is not None and amount > 0:
            memory["amount"] = amount
            _reset_retry(memory, "amount")


def _handle_transfer(user_id, message, intent_data, memory, ctx):
    memory["intent"] = "transferencia"
    _apply_transfer_slots(memory, intent_data, message)

    missing_question = _next_transfer_question(memory, user_id)
    if missing_question:
        slot = (
            "amount"
            if "amount" not in memory
            else "from_account"
            if "from_account" not in memory
            else "to_account"
        )
        memory["pending_slot"] = slot
        retries = _bump_retry(memory, slot)
        _save(user_id, memory)

        if retries > 2:
            _clear(user_id)
            return _response(
                user_id,
                "transferencia",
                message,
                "Para evitar errores, pause la transferencia. Puedes iniciarla otra vez con monto, cuenta origen y cuenta destino.",
            )

        return _response(user_id, "transferencia", message, missing_question)

    transfer_result = transfer_between_accounts(
        user_id,
        memory["from_account"],
        memory["to_account"],
        memory["amount"],
    )
    _clear(user_id)

    if "error" in transfer_result:
        return _response(user_id, "transferencia", message, transfer_result["error"])

    pdf_result = generate_transfer_pdf(
        user_id,
        memory["amount"],
        transfer_result["from_account"],
        transfer_result["to_account"],
        transfer_result["new_source_balance"],
        transfer_result["new_target_balance"],
    )
    bot_response = (
        f"Listo, transferencia realizada.\n\n"
        f"Monto: ${memory['amount']:,.2f} MXN\n"
        f"Origen: {transfer_result['from_account']} ({transfer_result['from_account_id']})\n"
        f"Destino: {transfer_result['to_account']} ({transfer_result['to_account_id']})\n"
        f"Folio: {pdf_result['folio']}\n"
        f"PDF: {pdf_result['pdf_path']}"
    )
    if ctx["cluster"] == 2:
        bot_response += "\n\nLa registre como movimiento de transferencia para tu control."
    return _response(user_id, "transferencia", message, bot_response)


def _handle_recharge(user_id, message, intent_data, memory):
    memory["intent"] = "recarga_celular"
    _apply_recharge_slots(memory, intent_data, message)

    if "phone_number" in memory and len(memory["phone_number"]) != 10:
        memory.pop("phone_number", None)

    missing_question = _next_recharge_question(memory, user_id)
    if missing_question:
        slot = "phone_number" if "phone_number" not in memory else "amount"
        memory["pending_slot"] = slot
        retries = _bump_retry(memory, slot)
        _save(user_id, memory)

        if retries > 2:
            _clear(user_id)
            return _response(
                user_id,
                "recarga_celular",
                message,
                "Pause la recarga para evitar errores. Intenta de nuevo con numero de 10 digitos y monto.",
            )

        return _response(user_id, "recarga_celular", message, missing_question)

    recharge_result = recharge_phone(
        user_id,
        memory["phone_number"],
        memory["amount"],
    )

    if "error" in recharge_result:
        _clear(user_id)
        return _response(user_id, "recarga_celular", message, recharge_result["error"])

    pdf_result = generate_recharge_pdf(
        user_id,
        memory["phone_number"],
        memory["amount"],
        recharge_result["new_balance"],
    )
    _clear(user_id)

    bot_response = (
        f"Recarga realizada.\n\n"
        f"Numero: {memory['phone_number']}\n"
        f"Monto: ${memory['amount']:,.2f} MXN\n"
        f"Cuenta origen: {recharge_result['source_account']} ({recharge_result['source_account_id']})\n"
        f"Nuevo saldo: ${recharge_result['new_balance']:,.2f} MXN\n"
        f"Folio: {pdf_result['folio']}\n"
        f"PDF: {pdf_result['pdf_path']}"
    )
    return _response(user_id, "recarga_celular", message, bot_response)


@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    lowered = message.lower()
    user_id = request.user_id

    if lowered in CANCEL_WORDS:
        _clear(user_id)
        return _response(
            user_id,
            "cancelar",
            request.message,
            "Listo, cancele el flujo actual. Dime que operacion quieres hacer ahora.",
        )

    ctx = _load_user_context(user_id)
    intent_data = detect_intent(message)
    intent = intent_data.get("intent", "desconocido")
    memory = conversation_memory.get(user_id, {})

    if _should_switch_topic(memory, intent):
        _clear(user_id)
        memory = {}

    active_intent = memory.get("intent") or intent

    if active_intent == "transferencia":
        return _handle_transfer(user_id, request.message, intent_data, memory, ctx)

    if active_intent == "recarga_celular":
        return _handle_recharge(user_id, request.message, intent_data, memory)

    _clear(user_id)

    if intent == "consultar_saldo":
        balance_data = get_balance(user_id)

        if "error" in balance_data:
            bot_response = balance_data["error"]
        else:
            accounts = balance_data.get("accounts", [])
            account_blocks = []

            for acc in accounts:
                account_blocks.append(
                    f"Producto: {acc['tipo_producto']}\n"
                    f"Nombre: {acc['nombre_producto']}\n"
                    f"ID: {acc['producto_id']}\n"
                    f"Descripcion: {acc['descripcion_producto']}\n"
                    f"Estatus: {acc['estatus']}\n"
                    f"Saldo: {_format_money(acc['saldo_actual'])}"
                )

            bot_response = (
                "Estos son todos tus productos:\n\n"
                + "\n\n".join(account_blocks)
                + "\n\nPara operar, dime el tipo o el ID del producto que quieres usar."
            )

    elif intent == "consultar_gastos":
        days = int(intent_data.get("days", 30) or 30)
        expense_data = get_expenses(user_id, days)
        real_data = (
            f"Periodo: {days} dias\n"
            f"Gasto total: ${expense_data['total_expenses']:,.2f} MXN\n"
            f"Numero de transacciones: {expense_data['transactions']}"
        )
        prompt = _personalized_prompt(
            ctx,
            request.message,
            real_data,
            "Resume el gasto del periodo. Puedes agregar una observacion de una sola frase basada en perfil, categoria favorita o cashback.",
        )
        bot_response = generate_response(prompt)

    elif intent == "ultimos_movimientos":
        limit = int(intent_data.get("limit", 5) or 5)
        limit = max(1, min(limit, 10))
        movements = get_last_transactions(user_id, limit)
        prompt = _personalized_prompt(
            ctx,
            request.message,
            f"Movimientos reales: {movements}",
            "Muestra solo los movimientos en lista breve con fecha, categoria y monto. No recomiendes ni analices habitos.",
        )
        bot_response = generate_response(prompt)

    elif intent == "consultar_cashback":
        bot_response = (
            f"Llevas ${ctx['cashback']:,.2f} MXN de cashback acumulado. "
            f"Por tu perfil {ctx['segment']}, conviene enfocarlo en {ctx['categoria']}."
        )

    elif intent == "recomendaciones":
        promo_data = get_promotions(ctx["data"])

        if "error" in promo_data:
            bot_response = "No pude generar promociones personalizadas en este momento."
        else:
            promociones = promo_data.get("promociones", [])
            if not promociones:
                bot_response = "No hay promociones disponibles por el momento."
            else:
                prompt = _personalized_prompt(
                    ctx,
                    request.message,
                    f"Promociones generadas: {promociones}",
                    "Presenta exactamente 3 promociones. Resalta el beneficio principal y conecta cada una con el segmento del cliente.",
                )
                bot_response = generate_response(prompt)

    else:
        bot_response = (
            f"Puedo ayudarte con saldo, movimientos, gastos, cashback, promociones, "
            f"transferencias y recargas. Para tu perfil {ctx['segment']}, tambien puedo "
            f"priorizar recomendaciones de {ctx['categoria']}."
        )

    return _response(user_id, intent, request.message, bot_response)
