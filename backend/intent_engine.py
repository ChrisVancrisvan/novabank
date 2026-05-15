import json
from llm_engine import generate_response


def detect_intent(message):
    prompt = f"""
    Eres un clasificador de intencion para un asistente financiero.
    Devuelve SOLO JSON valido, sin markdown ni explicacion.

    INTENCIONES DISPONIBLES:
    - consultar_saldo
    - consultar_gastos
    - ultimos_movimientos
    - recarga_celular
    - transferencia
    - consultar_cashback
    - recomendaciones
    - desconocido

    REGLAS GENERALES:
    - Si el mensaje solo es un numero, una cuenta suelta ("debito", "inversion")
      o una respuesta corta sin verbo, usa "desconocido". El orquestador decidira
      si es dato pendiente de un flujo.
    - No mezcles intenciones. Elige solo la intencion principal.
    - No inventes campos. Si no aparecen, usa null o valores por defecto.
    - "saldo", "cuanto tengo", "mi cuenta" -> consultar_saldo.
    - "cashback", "recompensas acumuladas" -> consultar_cashback.

    consultar_gastos:
    - hoy -> days: 1
    - semana -> days: 7
    - mes -> days: 30
    - ultimos X dias -> days: X
    - si no menciona periodo -> days: 30

    ultimos_movimientos:
    - usar para "ultimos gastos", "ultimas compras", "ultimos movimientos".
    - detecta cantidad, por ejemplo "ultimos 10 movimientos" -> limit: 10.
    - si no menciona cantidad -> limit: 5.

    transferencia:
    - usar cuando el usuario pide transferir, pasar dinero o mover dinero.
    - amount: numero entero o decimal, null si no aparece.
    - from_account: cuenta origen, null si no aparece.
    - to_account: cuenta destino, null si no aparece.

    recarga_celular:
    - usar cuando el usuario pide recargar celular/telefono.
    - phone_number: string de 10 digitos, null si no aparece.
    - amount: numero, null si no aparece.

    recomendaciones:
    - promociones, ofertas, beneficios, descuentos, recomendaciones, sugerencias,
      "que me conviene".

    EJEMPLOS:
    {{"intent": "consultar_saldo"}}
    {{"intent": "consultar_gastos", "days": 7}}
    {{"intent": "ultimos_movimientos", "limit": 10}}
    {{"intent": "transferencia", "amount": 500, "from_account": "debito", "to_account": "inversion"}}
    {{"intent": "transferencia", "amount": 300, "from_account": null, "to_account": null}}
    {{"intent": "recarga_celular", "phone_number": "8123456789", "amount": 200}}
    {{"intent": "recarga_celular", "phone_number": null, "amount": 100}}
    {{"intent": "consultar_cashback"}}
    {{"intent": "recomendaciones"}}
    {{"intent": "desconocido"}}

    MENSAJE DEL USUARIO:
    "{message}"
    """

    response = generate_response(prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        clean_json = response[start:end]
        data = json.loads(clean_json)
        if "intent" not in data:
            return {"intent": "desconocido"}
        return data
    except Exception:
        return {"intent": "desconocido"}
