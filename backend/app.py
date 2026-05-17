from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
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
    normalize_account_reference,
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

# Instrucciones de escritura concretas para el LLM, por cluster
CLUSTER_LLM_STYLE = {
    0: (
        "Redacta en tono ejecutivo y formal. "
        "Trata al cliente de 'usted'. "
        "Frases cortas y directas. "
        "Vocabulario: 'le informamos', 'ha sido registrado', 'quedo a sus ordenes'. "
        "Usa unicamente los emojis ✅ o 💼 si aportan claridad; ningun otro."
    ),
    1: (
        "Redacta en tono amigable, paciente y motivador. "
        "Trata al cliente de 'tu'. "
        "Frases sencillas con ejemplos concretos. "
        "Vocabulario: '¡listo!', '¡ya quedo!', '¡genial!', 'cuando quieras'. "
        "Incluye emojis como 😊 💸 🎉 ✨ para dar calidez a la respuesta."
    ),
    2: (
        "Redacta en tono preciso, tecnico y orientado a datos. "
        "Trata al cliente de 'usted'. "
        "Frases directas sin adornos. "
        "Vocabulario: 'registrado', 'monto exacto', 'periodo analizado', 'sin cambios'. "
        "Sin emojis innecesarios; usa unicamente ✔ si es util."
    ),
    3: (
        "Redacta en tono casual, energico y cercano. "
        "Trata al cliente de 'tu'. "
        "Frases cortas y dinamicas. "
        "Vocabulario: '¡orale!', '¡ya mero!', 'echarle la mano', '¡que onda!'. "
        "Incluye emojis como 🚀 💸 🙌 🎉 para dar energia y dinamismo."
    ),
}

# Textos y emojis diferenciados por cluster para respuestas directas (no LLM)
CLUSTER_VOICES = {
    0: {  # Premium: formal, ejecutivo, sin exceso de emojis
        "done_transfer": "Transferencia ejecutada exitosamente. ✅",
        "done_recharge": "Recarga procesada correctamente. ✅",
        "done_transfer_extra": "La operación quedó registrada en su historial.",
        "ask_amount_transfer": "¿Cuál es el monto que desea transferir?",
        "ask_from": "¿Desde qué cuenta desea originar el movimiento?",
        "ask_to": "¿Hacia qué cuenta desea dirigir la transferencia?",
        "ask_phone": "¿A qué número de 10 dígitos desea realizar la recarga?",
        "ask_recharge_amount": "¿Por qué monto desea recargar?",
        "accounts_intro_source": "Cuentas disponibles como origen:",
        "accounts_intro_target": "Cuentas disponibles como destino:",
        "cancel": "Entendido. El flujo fue cancelado. Quedo a sus órdenes para lo que necesite.",
        "default": (
            "Puedo asistirle con consultas de saldo, movimientos, gastos, "
            "cashback, promociones, transferencias y recargas."
        ),
        "saldo_intro": "Aquí tiene el resumen de sus productos.",
        "saldo_closing": "Para operar un producto específico, indique el tipo o su ID.",
        "cashback": lambda ctx: (
            f"Su cashback acumulado es de ${ctx['cashback']:,.2f} MXN. 💼 "
            f"Por su perfil {ctx['segment']}, le recomendamos aplicarlo en {ctx['categoria']}."
        ),
        "retry_abort": (
            "Para garantizar la seguridad de la operación, pausé el proceso. "
            "Puede iniciarlo nuevamente indicando monto, cuenta origen y cuenta destino."
        ),
        "retry_abort_recharge": (
            "Para evitar errores, pausé la recarga. "
            "Por favor intente de nuevo con un número de 10 dígitos y el monto deseado."
        ),
        "saludo": "Bienvenido a NovaBank AI. ¿En qué puedo asistirle hoy?",
        "movimientos_intro": lambda n: f"Sus últimos {n} movimiento{'s' if n != 1 else ''} registrado{'s' if n != 1 else ''}:",
        "movimientos_closing": "Para mayor detalle, consulte su estado de cuenta.",
        "ok": "✅",
        "money_emoji": "💼",
        "phone_emoji": "📱",
    },
    1: {  # Ocasional: amigable, paciente, con emojis de apoyo
        "done_transfer": "¡Tu transferencia quedó lista! 🎉",
        "done_recharge": "¡Recarga realizada con éxito! 📱✨",
        "done_transfer_extra": "¡Recuerda que puedes revisar tus movimientos cuando quieras! 😊",
        "ask_amount_transfer": "¿Cuánto quieres transferir? 💸 (Ejemplo: 500 o $1,200)",
        "ask_from": "¿Desde cuál de tus cuentas quieres mandar el dinero? 💳",
        "ask_to": "¿Y a cuál cuenta se lo enviamos? 📤",
        "ask_phone": "¿A qué número de celular (10 dígitos) quieres recargar? 📱",
        "ask_recharge_amount": "¿Cuánto quieres poner de saldo? 💵",
        "accounts_intro_source": "Estas son tus cuentas disponibles 👇",
        "accounts_intro_target": "Puedes enviarlo a cualquiera de estas cuentas 👇",
        "cancel": "¡Sin problema! Cancelé todo 😊 Cuando quieras, dime qué necesitas.",
        "default": (
            "Puedo ayudarte con tu saldo, movimientos, gastos, cashback, "
            "promociones, transferencias y recargas. ¿Con qué empezamos? 😊"
        ),
        "saldo_intro": "¡Aquí están todas tus cuentas! 😊",
        "saldo_closing": "¿Quieres hacer algo con alguna? Solo dime el tipo o el ID 👆",
        "cashback": lambda ctx: (
            f"¡Tienes ${ctx['cashback']:,.2f} MXN de cashback acumulado! ✨ "
            f"Como cliente {ctx['segment']}, te conviene usarlo en {ctx['categoria']} 😊"
        ),
        "retry_abort": (
            "¡Uy, algo salió mal con varios intentos! 😅 Pausé la transferencia para evitar errores. "
            "Inténtala de nuevo indicando el monto, tu cuenta de origen y la cuenta destino."
        ),
        "retry_abort_recharge": (
            "¡Ups! Pausé la recarga por seguridad 😅 "
            "Inténtala de nuevo con el número de 10 dígitos y el monto."
        ),
        "saludo": "¡Hola! 😊 Me da gusto saludarte. Soy NovaBank AI, estoy aquí para ayudarte. ¿Con qué empezamos?",
        "movimientos_intro": lambda n: f"¡Aquí están tus últimos {n} movimiento{'s' if n != 1 else ''}! 😊",
        "movimientos_closing": "¿Ves algo que no reconoces? Puedo ayudarte a aclararlo 💬",
        "ok": "✅",
        "money_emoji": "💵",
        "phone_emoji": "📱",
    },
    2: {  # Atípico: preciso, orientado a datos, control total
        "done_transfer": "Movimiento ejecutado. ✔",
        "done_recharge": "Recarga registrada. ✔",
        "done_transfer_extra": "Registrado como movimiento de transferencia para su control.",
        "ask_amount_transfer": "Indique el monto exacto de la transferencia.",
        "ask_from": "¿Cuál es la cuenta de origen para el cargo?",
        "ask_to": "¿Cuál es la cuenta destino para el abono?",
        "ask_phone": "Proporcione el número de 10 dígitos para la recarga.",
        "ask_recharge_amount": "Indique el monto de la recarga.",
        "accounts_intro_source": "Cuentas habilitadas como origen:",
        "accounts_intro_target": "Cuentas habilitadas como destino:",
        "cancel": "Operación cancelada. No se registraron cambios.",
        "default": (
            "Puedo apoyarle con consulta de saldos, movimientos, gastos por periodo, "
            "cashback, promociones, transferencias y recargas."
        ),
        "saldo_intro": "Resumen de sus productos activos:",
        "saldo_closing": "Para operar, indique el tipo de producto o su ID.",
        "cashback": lambda ctx: (
            f"Cashback acumulado: ${ctx['cashback']:,.2f} MXN. 📊 "
            f"Perfil: {ctx['segment']}. Categoría sugerida: {ctx['categoria']}."
        ),
        "retry_abort": (
            "Pausé el proceso por exceso de intentos. "
            "Inicie nuevamente indicando monto, cuenta origen y cuenta destino."
        ),
        "retry_abort_recharge": (
            "Pausé la recarga por exceso de intentos. "
            "Indique número de 10 dígitos y monto para reiniciar."
        ),
        "saludo": "Hola. Soy NovaBank AI. ¿Con qué operación le puedo apoyar hoy?",
        "movimientos_intro": lambda n: f"Registro: últimos {n} movimiento{'s' if n != 1 else ''}.",
        "movimientos_closing": "Para análisis por periodo, use 'consultar gastos'.",
        "ok": "✔",
        "money_emoji": "📊",
        "phone_emoji": "📲",
    },
    3: {  # Frecuente Estándar: casual, ágil, con energía
        "done_transfer": "¡Transferencia lista! 🚀",
        "done_recharge": "¡Saldo cargado al celu! 📱🔋",
        "done_transfer_extra": "¡Tus saldos ya se actualizaron! 🙌",
        "ask_amount_transfer": "¿Cuánto le mandas? 💸",
        "ask_from": "¿De cuál de tus cuentas sale el dinero? 💳",
        "ask_to": "¿Y a cuál le llega? 👇",
        "ask_phone": "¿A qué celu (10 dígitos) le ponemos saldo? 📱",
        "ask_recharge_amount": "¿Cuánto le echamos de saldo? 💰",
        "accounts_intro_source": "Tus cuentas disponibles 👇",
        "accounts_intro_target": "¿A cuál le llega? Elige una 👇",
        "cancel": "¡Órale, cancelé todo! 👌 Cuando quieras volvemos a intentarlo.",
        "default": (
            "Te puedo echar la mano con saldo, movimientos, gastos, cashback, "
            "promos, transferencias y recargas. ¿Qué necesitas? 🙌"
        ),
        "saldo_intro": "¡Aquí van todos tus productos! 👛",
        "saldo_closing": "Dime cuál quieres usar, con el tipo o el ID 💳",
        "cashback": lambda ctx: (
            f"¡Llevas ${ctx['cashback']:,.2f} MXN de cashback acumulado! 🎉 "
            f"Con tu perfil {ctx['segment']}, el mayor retorno está en {ctx['categoria']} 💰"
        ),
        "retry_abort": (
            "¡Demasiados intentos! 😬 Pausé la transferencia. "
            "Vuélvela a intentar indicando monto, cuenta origen y cuenta destino."
        ),
        "retry_abort_recharge": (
            "¡Pausé la recarga! 🔄 "
            "Inténtala de nuevo con el número de 10 dígitos y el monto."
        ),
        "saludo": "¡Hola! 👋 ¿Qué onda? Soy NovaBank AI, dime en qué te echo la mano 🚀",
        "movimientos_intro": lambda n: f"Tus últimos {n} movimiento{'s' if n != 1 else ''} 👇",
        "movimientos_closing": "¿Ves algo raro? Cuéntame y lo revisamos 🙌",
        "ok": "✅",
        "money_emoji": "💸",
        "phone_emoji": "📱",
    },
}


@app.get("/")
def root():
    return {"message": "NovaBank AI funcionando"}


@app.get("/vouchers/{filename}")
def download_voucher(filename: str):
    filepath = os.path.join("vouchers", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)


def _response(user_id, intent, message, bot_response):
    return {
        "user_id": user_id,
        "intent": intent,
        "message_received": message,
        "bot_response": bot_response,
    }


def _load_user_context(user_id):
    user_data = get_user_data(user_id) or {}
    raw_cluster = user_data.get("cluster")
    cluster = int(raw_cluster) if raw_cluster is not None else 3
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


def _voice(ctx):
    return CLUSTER_VOICES.get(ctx["cluster"], CLUSTER_VOICES[3])


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
    style = CLUSTER_LLM_STYLE.get(ctx["cluster"], CLUSTER_LLM_STYLE[3])
    return f"""
    Eres NovaBank AI, asistente bancario conversacional.

    {_profile_block(ctx)}

    ESTILO DE ESCRITURA OBLIGATORIO (cluster {ctx['cluster']} - {ctx['segment']}):
    {style}

    MENSAJE DEL CLIENTE:
    "{message}"

    DATOS REALES DISPONIBLES:
    {real_data}

    REGLAS:
    - Responde en espanol mexicano siguiendo EXACTAMENTE el estilo de escritura indicado arriba.
    - No mezcles temas: contesta solo la intencion actual.
    - No inventes datos, saldos, folios, fechas, beneficios ni comisiones.
    - Si falta un dato, pide solo ese dato.
    - No cierres con preguntas genericas si ya resolviste.

    INSTRUCCIONES DE ESTA RESPUESTA:
    {instructions}
    """


def _first_number(text):
    # Limpiar símbolo de peso y comas de miles para no alterar el monto
    text_clean = text.replace("$", "").replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text_clean)
    if not match:
        return None
    return float(match.group(0))


def _digits_only(text):
    return re.sub(r"\D", "", text)


def _normalize_account(text):
    value = text.strip().lower()
    keywords = {
        "debito": "debito",
        "débito": "debito",
        "inversion": "inversion",
        "inversión": "inversion",
        "negocio": "negocios",
        "negocios": "negocios",
        "credito": "credito",
        "crédito": "credito",
    }

    for word, alias in keywords.items():
        if re.search(rf"\b{word}\b", value):
            return alias

    prd_match = re.search(r"\bprd-\d+\b", value)
    if prd_match:
        return prd_match.group(0)

    match = re.search(r"\b\d+\b", value)
    if match:
        return match.group(0)

    return value


def _format_money(value):
    return f"${float(value):,.2f} MXN"


def _format_account_line(account, show_balance=False):
    line = f"- {account['nombre_producto']} (ID: {account['producto_id']})"
    if show_balance:
        line += f" — Saldo: {_format_money(account['saldo_actual'])}"
    return line


def _format_accounts(accounts, show_balance=False):
    if not accounts:
        return "- No hay cuentas disponibles para esta operacion."
    return "\n".join(_format_account_line(a, show_balance) for a in accounts)


def _format_transactions(movements):
    lines = []
    for i, tx in enumerate(movements, 1):
        fecha = str(tx["fecha"])[:10]
        categoria = str(tx["categoria"]).replace("_", " ").title()
        monto = _format_money(tx["monto"])
        lines.append(f"{i}. {fecha} — {categoria}: {monto}")
    return "\n".join(lines)


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


def _next_transfer_question(memory, user_id, voice):
    if "amount" not in memory:
        return voice["ask_amount_transfer"]

    if "from_account" not in memory:
        source_accounts = get_operation_accounts(user_id, "transfer_source")
        return (
            f"{voice['ask_from']}\n\n"
            f"{voice['accounts_intro_source']}\n"
            f"{_format_accounts(source_accounts, show_balance=True)}"
        )

    if "to_account" not in memory:
        selected_type = normalize_account_reference(memory["from_account"])
        target_accounts = [
            a for a in get_operation_accounts(user_id, "transfer_target")
            if a["tipo_producto"].lower() != selected_type
        ]
        return (
            f"{voice['ask_to']}\n\n"
            f"{voice['accounts_intro_target']}\n"
            f"{_format_accounts(target_accounts)}"
        )

    return None


def _next_recharge_question(memory, user_id, voice):
    if "phone_number" not in memory:
        source_accounts = get_operation_accounts(user_id, "recharge_source")
        return (
            f"{voice['ask_phone']}\n\n"
            f"La recarga puede salir de:\n"
            f"{_format_accounts(source_accounts)}"
        )
    if "amount" not in memory:
        return voice["ask_recharge_amount"]
    return None


def _apply_transfer_slots(memory, intent_data, message):
    pending = memory.get("pending_slot")

    if pending:
        # Mid-flow: solo llenar el slot que se pidió explícitamente
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
    else:
        # Primer mensaje: extraer todos los slots disponibles del NLP
        if intent_data.get("amount") is not None:
            memory["amount"] = float(intent_data["amount"])
            _reset_retry(memory, "amount")
        if intent_data.get("from_account"):
            memory["from_account"] = _normalize_account(intent_data["from_account"])
            _reset_retry(memory, "from_account")
        if intent_data.get("to_account"):
            to = _normalize_account(intent_data["to_account"])
            if to != memory.get("from_account"):
                memory["to_account"] = to
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
    voice = _voice(ctx)
    memory["intent"] = "transferencia"
    _apply_transfer_slots(memory, intent_data, message)

    missing_question = _next_transfer_question(memory, user_id, voice)
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
                voice["retry_abort"],
            )

        return _response(user_id, "transferencia", message, missing_question)

    transfer_result = transfer_between_accounts(
        user_id,
        memory["from_account"],
        memory["to_account"],
        memory["amount"],
    )

    if "error" in transfer_result:
        error_msg = transfer_result["error"]
        # Errores recuperables: re-preguntar sin borrar toda la memoria
        if "destino" in error_msg or "misma" in error_msg:
            memory.pop("to_account", None)
            memory.pop("pending_slot", None)
            memory.setdefault("retries", {}).pop("to_account", None)
            selected_type = normalize_account_reference(memory.get("from_account", ""))
            target_accounts = [
                a for a in get_operation_accounts(user_id, "transfer_target")
                if a["tipo_producto"].lower() != selected_type
            ]
            prompt_msg = (
                f"{error_msg}.\n\n"
                f"{voice['ask_to']}\n\n"
                f"{voice['accounts_intro_target']}\n"
                f"{_format_accounts(target_accounts)}"
            )
            memory["pending_slot"] = "to_account"
            _save(user_id, memory)
            return _response(user_id, "transferencia", message, prompt_msg)
        # Error no recuperable (ej. saldo insuficiente): cancelar flujo
        _clear(user_id)
        return _response(user_id, "transferencia", message, error_msg)

    _clear(user_id)

    pdf_result = generate_transfer_pdf(
        user_id,
        memory["amount"],
        transfer_result["from_account"],
        transfer_result["to_account"],
        transfer_result["new_source_balance"],
        transfer_result["new_target_balance"],
    )

    ok = voice["ok"]
    money_emoji = voice["money_emoji"]
    bot_response = (
        f"{voice['done_transfer']}\n\n"
        f"{money_emoji} Monto: ${memory['amount']:,.2f} MXN\n"
        f"Origen: {transfer_result['from_account']} ({transfer_result['from_account_id']})\n"
        f"Destino: {transfer_result['to_account']} ({transfer_result['to_account_id']})\n"
        f"{ok} Folio: {pdf_result['folio']}\n"
        f"Comprobante: {pdf_result['pdf_path']}\n\n"
        f"{voice['done_transfer_extra']}"
    )
    return _response(user_id, "transferencia", message, bot_response)


def _handle_recharge(user_id, message, intent_data, memory, ctx):
    voice = _voice(ctx)
    memory["intent"] = "recarga_celular"
    _apply_recharge_slots(memory, intent_data, message)

    if "phone_number" in memory and len(memory["phone_number"]) != 10:
        memory.pop("phone_number", None)

    missing_question = _next_recharge_question(memory, user_id, voice)
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
                voice["retry_abort_recharge"],
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

    ok = voice["ok"]
    phone_emoji = voice["phone_emoji"]
    bot_response = (
        f"{voice['done_recharge']}\n\n"
        f"{phone_emoji} Número: {memory['phone_number']}\n"
        f"Monto recargado: ${memory['amount']:,.2f} MXN\n"
        f"Cuenta usada: {recharge_result['source_account']} ({recharge_result['source_account_id']})\n"
        f"Saldo restante en cuenta: ${recharge_result['new_balance']:,.2f} MXN\n"
        f"{ok} Folio: {pdf_result['folio']}\n"
        f"Comprobante: {pdf_result['pdf_path']}"
    )
    return _response(user_id, "recarga_celular", message, bot_response)


@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    lowered = message.lower()
    user_id = request.user_id

    ctx = _load_user_context(user_id)
    voice = _voice(ctx)

    if lowered in CANCEL_WORDS:
        _clear(user_id)
        return _response(
            user_id,
            "cancelar",
            request.message,
            voice["cancel"],
        )

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
        return _handle_recharge(user_id, request.message, intent_data, memory, ctx)

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
                f"{voice['saldo_intro']}\n\n"
                + "\n\n".join(account_blocks)
                + f"\n\n{voice['saldo_closing']}"
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
        if not movements:
            bot_response = "No encontré movimientos recientes."
        else:
            bot_response = (
                f"{voice['movimientos_intro'](len(movements))}\n\n"
                f"{_format_transactions(movements)}\n\n"
                f"{voice['movimientos_closing']}"
            )

    elif intent == "consultar_cashback":
        bot_response = voice["cashback"](ctx)

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

    elif intent == "saludo":
        bot_response = voice["saludo"]

    else:
        bot_response = voice["default"]

    return _response(user_id, intent, request.message, bot_response)
