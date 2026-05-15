import json

from llm_engine import generate_response


def detect_intent(message):


    prompt = f"""
    Eres un clasificador de intención
    para un asistente financiero.

    Analiza el mensaje del usuario.

    Debes devolver SOLO JSON válido.


    INTENCIONES:

    - consultar_saldo
    - consultar_gastos
    - ultimos_movimientos
    - recarga_celular
    - transferencia
    - consultar_cashback
    - recomendaciones


    # =========================
    # CONSULTAR GASTOS
    # =========================

    Detecta rango temporal.

    REGLAS:

    - hoy = 1 día
    - semana = 7 días
    - mes = 30 días
    - últimos X días = X


    # =========================
    # ÚLTIMOS MOVIMIENTOS
    # =========================

    Si el usuario pide:

    - últimos gastos
    - últimos movimientos
    - últimas compras

    SIEMPRE usar:

    "intent": "ultimos_movimientos"

    Detecta cantidad solicitada.

    Ejemplo:

    "últimos 10 gastos"


    # =========================
    # TRANSFERENCIAS
    # =========================

    Detecta:

    - monto
    - cuenta origen
    - cuenta destino

    Si faltan datos,
    deja campos vacíos.


    MENSAJE:

    "{message}"


    IMPORTANTE:

    - SOLO JSON
    - NO markdown
    - NO explicación

    # =========================
    # RECARGA DE CELULAR
    # =========================

    Detecta:

    - monto
    - cuenta origen
    - numero de 10 digitos 
    

    Si faltan datos,
    deja campos vacíos.


    MENSAJE:

    "{message}"


    IMPORTANTE:

    - SOLO JSON
    - NO markdown
    - NO explicación

    # =========================
    # EJEMPLOS
    # =========================


    {{
        "intent": "consultar_saldo"
    }}


    {{
        "intent": "consultar_gastos",
        "days": 7
    }}


    {{
        "intent": "ultimos_movimientos",
        "limit": 10
    }}


    {{
        "intent": "transferencia",
        "amount": 500,
        "from_account": "ahorro",
        "to_account": "debito"
    }}


    {{
        "intent": "transferencia",
        "amount": 300
    }}

    {{
        "intent": "recarga_celular",
        "phone_number": "8123456789",
        "amount": 200
    }}


    {{
        "intent": "recarga_celular",
        "amount": 100
    }}
    """


    response = generate_response(
        prompt
    )


    try:


        start = response.find('{')

        end = response.rfind('}') + 1

        clean_json = response[start:end]

        data = json.loads(clean_json)

        return data


    except:


        return {
            "intent": "desconocido"
        }