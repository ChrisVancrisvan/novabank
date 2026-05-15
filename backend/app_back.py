from fastapi import FastAPI
from pydantic import BaseModel

from llm_engine import generate_response

from user_engine import get_user_data

from intent_engine import detect_intent

from finance_engine import (
    get_balance,
    get_expenses,
    get_last_transactions,
    transfer_between_accounts,
    recharge_phone
)

from conversation_memory import (
    conversation_memory
)

from pdf_engine import (
    generate_transfer_pdf,
    generate_recharge_pdf
)

app = FastAPI()


# =========================
# MODELO REQUEST
# =========================

class ChatRequest(BaseModel):

    user_id: str
    message: str


# =========================
# ROOT
# =========================

@app.get("/")
def root():

    return {
        "message": "NovaBank AI funcionando"
    }


# =========================
# CHATBOT
# =========================

@app.post("/chat")
def chat(request: ChatRequest):


    # =========================
    # DETECTAR INTENCIÓN
    # =========================

    intent_data = detect_intent(
        request.message
    )

    intent = intent_data.get(
        "intent",
        "desconocido"
    )

    memory = conversation_memory.get(

        request.user_id,

    {}
    )

    # =========================
    # RESET SI CAMBIA INTENT
    # =========================

    if (

        memory.get("intent")

        and

        memory.get("intent") != intent

    ):

        conversation_memory[
            request.user_id
        ] = {}

        memory = {}

    # =========================
    # CONTINUAR TRANSFERENCIA
    # =========================

    if memory.get("intent") == "transferencia":


        if "amount" not in memory:


            numbers = [

                int(s)

                for s in request.message.split()

                if s.isdigit()
            ]


            if len(numbers) > 0:

                memory["amount"] = numbers[0]


        elif "from_account" not in memory:


            memory["from_account"] = (
                request.message.lower()
            )


        elif "to_account" not in memory:


            memory["to_account"] = (
                request.message.lower()
            )


        conversation_memory[
            request.user_id
        ] = memory


        # EJECUTAR

        if (

            "amount" in memory

            and

            "from_account" in memory

            and

            "to_account" in memory
        ):


            transfer_result = transfer_between_accounts(

                request.user_id,

                memory["from_account"],

                memory["to_account"],

                memory["amount"]
            )


            conversation_memory[
                request.user_id
            ] = {}


            return {

                "user_id":
                request.user_id,

                "intent":
                "transferencia",

                "message_received":
                request.message,

                "bot_response":
                "Transferencia realizada exitosamente."
            }


        if "amount" not in memory:


            return {

                "user_id":
                request.user_id,

                "intent":
                "transferencia",

                "message_received":
                request.message,

                "bot_response":
                "¿Cuánto deseas transferir?"
            }


        if "from_account" not in memory:


            return {

                "user_id":
                request.user_id,

                "intent":
                "transferencia",

                "message_received":
                request.message,

                "bot_response":
                "¿Desde qué cuenta deseas transferir?"
            }


        if "to_account" not in memory:


            return {

                "user_id":
                request.user_id,

                "intent":
                "transferencia",

                "message_received":
                request.message,

                "bot_response":
                "¿A qué cuenta deseas transferir?"
            }


    # =========================
    # CONTINUAR RECARGA
    # =========================

    if memory.get("intent") == "recarga_celular":


        # TELÉFONO

        if "phone_number" not in memory:


            phone = request.message.strip()


            if phone.isdigit():


                if len(phone) == 10:

                    memory["phone_number"] = phone


                else:


                    return {

                        "user_id":
                        request.user_id,

                        "intent":
                        "recarga_celular",

                        "message_received":
                        request.message,

                        "bot_response":
                        "El número debe tener exactamente 10 dígitos."
                    }


            else:


                return {

                    "user_id":
                    request.user_id,

                    "intent":
                    "recarga_celular",

                    "message_received":
                    request.message,

                    "bot_response":
                    "El número solo debe contener números."
                }


        # MONTO

        elif "amount" not in memory:


            numbers = [

                int(s)

                for s in request.message.split()

                if s.isdigit()
            ]


            if len(numbers) > 0:

                memory["amount"] = numbers[0]


        conversation_memory[
            request.user_id
        ] = memory


        # EJECUTAR RECARGA

        if (

            "phone_number" in memory

            and

            "amount" in memory
        ):


            recharge_result = recharge_phone(

                request.user_id,

                memory["phone_number"],

                memory["amount"]
            )


            if "error" in recharge_result:


                return {

                    "user_id":
                    request.user_id,

                    "intent":
                    "recarga_celular",

                    "message_received":
                    request.message,

                    "bot_response":
                    recharge_result["error"]
                }


            pdf_result = generate_recharge_pdf(

                request.user_id,

                memory["phone_number"],

                memory["amount"],

                recharge_result['new_balance']
            )


            conversation_memory[
                request.user_id
            ] = {}


            return {

                "user_id":
                request.user_id,

                "intent":
                "recarga_celular",

                "message_received":
                request.message,

                "bot_response":
                f"""

    Recarga realizada exitosamente.

    Número:
    {memory['phone_number']}

    Monto:
    ${memory['amount']:,.2f} MXN

    Folio:
    {pdf_result['folio']}

    PDF:
    {pdf_result['pdf_path']}
    """
            }


        if "phone_number" not in memory:


            return {

                "user_id":
                request.user_id,

                "intent":
                "recarga_celular",

                "message_received":
                request.message,

                "bot_response":
                "¿Qué número deseas recargar?"
            }


        if "amount" not in memory:


            return {

                "user_id":
                request.user_id,

                "intent":
                "recarga_celular",

                "message_received":
                request.message,

                "bot_response":
                "¿Cuánto deseas recargar?"
            }




    # =========================
    # DATOS USUARIO
    # =========================

    user_data = get_user_data(
        request.user_id
    )


    cluster = user_data.get(
        'cluster',
        'N/A'
    )

    categoria = user_data.get(
        'categoria_favorita',
        'General'
    )

    cashback = user_data.get(
        'cashback_total',
        0
    )


    # ==================================================
    # CONSULTAR SALDO
    # ==================================================

    if intent == "consultar_saldo":


        balance_data = get_balance(
            request.user_id
        )


        # SI HAY ERROR

        if "error" in balance_data:

            bot_response = (
                balance_data["error"]
            )


        # SI TIENE VARIAS CUENTAS

        elif balance_data.get(
            "multiple_accounts"
        ):


            accounts = balance_data[
                "accounts"
            ]


            account_text = ""


            for acc in accounts:

                account_text += f"""

    Producto:
    {acc['tipo_producto']}

    ID:
    {acc['producto_id']}

    Saldo:
    ${acc['saldo_actual']:,.2f} MXN

    """


                bot_response = f"""
    Tienes varias cuentas disponibles:

    {account_text}

    Indícame cuál deseas consultar.
    """


        # UNA SOLA CUENTA

        else:


            prompt = f"""
            Eres NovaBank AI.


            PERFIL USUARIO:

            - Cluster:
            {cluster}

            - Categoría favorita:
            {categoria}


            MENSAJE:

            "{request.message}"


            DATOS REALES:

            Producto:
            {balance_data['tipo_producto']}

            Saldo:
            ${balance_data['saldo_actual']:,.2f} MXN


            INSTRUCCIONES:

            - responde breve
            - responde natural
            - NO inventes datos
            - NO agregar información extra
            - SOLO responder lo solicitado
            - personaliza tono según perfil
            """


            bot_response = generate_response(
                prompt
            )


    # ==================================================
    # CONSULTAR GASTOS
    # ==================================================

    elif intent == "consultar_gastos":


        days = intent_data.get(
            "days",
            30
        )


        expense_data = get_expenses(
            request.user_id,
            days
        )


        prompt = f"""
        Eres NovaBank AI.


        PERFIL USUARIO:

        - Cluster:
        {cluster}

        - Categoría favorita:
        {categoria}

        - Cashback:
        ${cashback:,.2f} MXN


        MENSAJE:

        "{request.message}"


        DATOS REALES:

        Periodo:
        {days} días

        Gasto total:
        ${expense_data['total_expenses']:,.2f} MXN

        Número de transacciones:
        {expense_data['transactions']}


        INSTRUCCIONES:

        - responde breve
        - responde claro
        - NO inventes datos
        - SOLO responder lo solicitado
        - NO dar consejos si no se piden
        - NO mencionar cashback si no se pide
        - personaliza tono según perfil
        """


        bot_response = generate_response(
            prompt
        )


    # ==================================================
    # ÚLTIMOS MOVIMIENTOS
    # ==================================================

    elif intent == "ultimos_movimientos":


        limit = intent_data.get(
            "limit",
            5
        )


        movements = get_last_transactions(
            request.user_id,
            limit
        )


        prompt = f"""
        Eres NovaBank AI.


        MENSAJE:

        "{request.message}"


        MOVIMIENTOS REALES:

        {movements}


        INSTRUCCIONES:

        - SOLO mostrar movimientos
        - responder breve
        - responder claro
        - NO inventes datos
        - NO recomendar nada
        - NO mencionar cashback
        - NO analizar hábitos
        - NO agregar información extra
        """


        bot_response = generate_response(
            prompt
        )
    
        # ==================================================
    # TRANSFERENCIA ENTRE CUENTAS
    # ==================================================

    elif intent == "transferencia":

        conversation_memory[
            request.user_id
        ] = {

            "intent":
            "transferencia"
        }


        amount = intent_data.get(
            "amount"
        )

        from_account = intent_data.get(
            "from_account"
        )

        to_account = intent_data.get(
            "to_account"
        )


        # VALIDAR DATOS FALTANTES

        if amount is None:


            bot_response = (
                "¿Cuánto dinero deseas transferir?"
            )


        elif from_account is None:


            bot_response = (
                "¿Desde qué cuenta deseas transferir?"
            )


        elif to_account is None:


            bot_response = (
                "¿A qué cuenta deseas transferir?"
            )


        else:


            transfer_result = transfer_between_accounts(

                request.user_id,

                from_account,

                to_account,

                amount
            )


            # SI HAY ERROR

            if "error" in transfer_result:


                bot_response = (
                    transfer_result["error"]
                )


            else:


                prompt = f"""
                Eres NovaBank AI.


                PERFIL USUARIO:

                - Cluster:
                {cluster}

                - Categoría favorita:
                {categoria}


                DATOS REALES:

                Transferencia exitosa.

                Monto:
                ${amount:,.2f} MXN

                Cuenta origen:
                {transfer_result['from_account']}

                Cuenta destino:
                {transfer_result['to_account']}


                NUEVOS SALDOS:

                Origen:
                ${transfer_result['new_source_balance']:,.2f}

                Destino:
                ${transfer_result['new_target_balance']:,.2f}


                INSTRUCCIONES:

                - responde breve
                - responde natural
                - NO inventes datos
                - NO agregar información extra
                - confirmar transferencia
                """


                bot_response = generate_response(
                    prompt
                )

    # ==================================================
    # RECARGA CELULAR
    # ==================================================

    elif intent == "recarga_celular":


        conversation_memory[
            request.user_id
        ] = {

            "intent":
            "recarga_celular"
        }


        phone_number = intent_data.get(
            "phone_number"
        )

        amount = intent_data.get(
            "amount"
        )


        if phone_number is None:


            bot_response = (
                "¿Qué número deseas recargar?"
            )


        elif amount is None:


            conversation_memory[
                request.user_id
            ]["phone_number"] = (
                phone_number
            )


            bot_response = (
                "¿Cuánto deseas recargar?"
            )


        else:


            recharge_result = recharge_phone(

                request.user_id,

                phone_number,

                amount
            )

            pdf_result = generate_recharge_pdf(

                request.user_id,

                phone_number,

                amount,

                recharge_result['new_balance']
            )


            if "error" in recharge_result:


                bot_response = (
                    recharge_result["error"]
                )


            else:


                bot_response = f"""

Recarga realizada exitosamente.

Número:
{phone_number}

Monto:
${amount:,.2f} MXN

Nuevo saldo:
${recharge_result['new_balance']:,.2f} MXN

Folio:
{pdf_result['folio']}

PDF:
{pdf_result['pdf_path']}

"""


                conversation_memory[
                    request.user_id
                ] = {}


    # ==================================================
    # INTENCIÓN DESCONOCIDA
    # ==================================================

    else:

        bot_response = (
            "Todavía no sé resolver esa operación."
        )


    # =========================
    # RESPONSE FINAL
    # =========================

    return {

        "user_id":
        request.user_id,

        "intent":
        intent,

        "message_received":
        request.message,

        "bot_response":
        bot_response
    }