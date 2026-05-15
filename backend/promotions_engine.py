import json
from llm_engine import generate_response


# =========================
# PERFILES DE CLUSTER
# =========================

CLUSTER_PROFILES = {

    0: {
        "nombre": "Cliente Premium",
        "descripcion": (
            "Alto poder adquisitivo, ticket promedio elevado, "
            "viajero frecuente con transacciones internacionales, "
            "genera mucho cashback."
        ),
        "enfoque_promociones": (
            "beneficios exclusivos, lounges, seguros de viaje, "
            "recompensas premium, productos de inversión, "
            "experiencias VIP, límites de crédito elevados."
        )
    },

    1: {
        "nombre": "Cliente Ocasional",
        "descripcion": (
            "Uso esporádico del banco, pocas transacciones, "
            "gasto total bajo, poco o nulo cashback."
        ),
        "enfoque_promociones": (
            "incentivos para aumentar frecuencia de uso, "
            "bonos de bienvenida, cashback en primeras compras, "
            "promociones en categorías cotidianas como supermercado "
            "y gasolina, cero comisiones para enganchar."
        )
    },

    2: {
        "nombre": "Cliente Atípico",
        "descripcion": (
            "Patrón de transacciones inusual, movimientos concentrados "
            "o de alto volumen, posiblemente uso para negocios o "
            "actividad financiera no convencional."
        ),
        "enfoque_promociones": (
            "productos para negocios, cuentas empresariales, "
            "meses sin intereses en montos grandes, "
            "asesoría financiera personalizada, "
            "productos de ahorro e inversión para flujos altos."
        )
    },

    3: {
        "nombre": "Cliente Frecuente Estándar",
        "descripcion": (
            "Uso cotidiano del banco, muchas transacciones de ticket "
            "bajo-medio, cashback moderado, cliente fiel y constante."
        ),
        "enfoque_promociones": (
            "maximizar cashback en categorías favoritas, "
            "descuentos en comercios frecuentes, "
            "programas de puntos, promociones en servicios digitales, "
            "recompensas por lealtad y uso constante."
        )
    }
}


# =========================
# GENERAR PROMOCIONES
# =========================

def get_promotions(user_data: dict) -> dict:

    user_id   = user_data.get("user_id", "desconocido")
    cluster   = user_data.get("cluster", 3)
    categoria = user_data.get("categoria_favorita", "transferencia")
    cashback  = user_data.get("cashback_total", 0)
    gasto_promedio           = user_data.get("gasto_promedio", 0)
    num_transacciones        = user_data.get("num_transacciones", 0)
    transacciones_internacionales = user_data.get("transacciones_internacionales", 0)

    perfil = CLUSTER_PROFILES.get(cluster, CLUSTER_PROFILES[3])

    prompt = f"""
    Eres el motor de promociones de NovaBank, un banco digital mexicano.

    Tu tarea es generar exactamente 3 promociones personalizadas para este usuario.
    Las promociones deben ser MUY específicas a su perfil, no genéricas.

    ────────────────────────────────────────
    PERFIL DEL USUARIO
    ────────────────────────────────────────
    Segmento:         {perfil['nombre']}
    Descripción:      {perfil['descripcion']}
    Categoría favorita: {categoria}
    Cashback acumulado: ${cashback:,.2f} MXN
    Gasto promedio por transacción: ${gasto_promedio:,.2f} MXN
    Número de transacciones: {num_transacciones}
    Transacciones internacionales: {transacciones_internacionales}

    ────────────────────────────────────────
    ENFOQUE DE PROMOCIONES PARA ESTE SEGMENTO
    ────────────────────────────────────────
    {perfil['enfoque_promociones']}

    ────────────────────────────────────────
    INSTRUCCIONES
    ────────────────────────────────────────
    - Genera exactamente 3 promociones
    - Cada promoción debe sentirse hecha para este usuario específico,
      no para cualquier cliente
    - Usa el gasto promedio y categoría favorita para hacer las
      promociones relevantes y creíbles
    - Si tiene transacciones internacionales, al menos una promoción
      debe tocar ese ángulo
    - Si tiene cashback acumulado, menciona cómo puede aprovecharlo
    - Tono: cercano, directo, en español mexicano
    - Montos y porcentajes deben ser realistas para un banco mexicano

    ────────────────────────────────────────
    FORMATO DE RESPUESTA
    ────────────────────────────────────────
    Responde SOLO con JSON válido, sin markdown ni explicación.
    Estructura exacta:

    {{
        "promociones": [
            {{
                "titulo": "Título corto y atractivo",
                "descripcion": "Descripción de 1-2 oraciones explicando el beneficio",
                "beneficio": "El beneficio concreto en una frase (ej: 5% cashback, 0 comisiones 3 meses)",
                "categoria": "La categoría o producto al que aplica"
            }}
        ]
    }}
    """

    response = generate_response(prompt)

    try:
        start = response.find('{')
        end   = response.rfind('}') + 1
        clean_json = response[start:end]
        data = json.loads(clean_json)
        return {
            "user_id":     user_id,
            "segmento":    perfil["nombre"],
            "promociones": data.get("promociones", [])
        }

    except Exception:
        return {
            "user_id":     user_id,
            "segmento":    perfil["nombre"],
            "promociones": [],
            "error":       "No se pudieron generar promociones"
        }