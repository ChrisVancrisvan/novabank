import re
from pathlib import Path

import joblib


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "intent_classifier.joblib"

INTENTS = {
    "consultar_saldo",
    "consultar_gastos",
    "ultimos_movimientos",
    "recarga_celular",
    "transferencia",
    "consultar_cashback",
    "recomendaciones",
    "soporte",
    "saludo",
    "desconocido",
}

_MODEL = None


def _load_model():
    global _MODEL
    if _MODEL is None and MODEL_PATH.exists():
        _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def _extract_amount(message):
    # Remover signos y comas antes de extraer para evitar que 1,500 se vuelva 1.5
    text_clean = str(message).replace("$", "").replace(",", "")
    match = re.search(r"\b\d+(?:\.\d+)?\b", text_clean)
    if not match:
        return None
    return float(match.group(0))


def _extract_days(message):
    lowered = message.lower()
    if "hoy" in lowered:
        return 1
    if "semana" in lowered:
        return 7
    if "mes" in lowered:
        return 30

    match = re.search(r"(?:ultimos|últimos|hace)\s+(\d+)\s+dias", lowered)
    if match:
        return int(match.group(1))

    return 30


def _extract_limit(message):
    match = re.search(r"\b(\d{1,2})\b", message)
    if not match:
        return 5
    return max(1, min(int(match.group(1)), 10))


def _extract_phone(message):
    direct_match = re.search(r"(?<!\d)(\d{10})(?!\d)", message)
    if direct_match:
        return direct_match.group(1)

    digit_groups = re.findall(r"\d+", message)
    for group in digit_groups:
        if len(group) == 10:
            return group

    return None


def _extract_account(message, markers):
    lowered = message.lower()
    account_words = {
        "debito": "debito",
        "débito": "debito",
        "inversion": "inversion",
        "inversión": "inversion",
        "negocios": "negocios",
        "negocio": "negocios",
        "credito": "credito",
        "crédito": "credito",
        "nomina": "credito_nomina",
        "personal": "credito_personal",
        "auto": "credito_auto",
    }

    for marker in markers:
        pattern = rf"\b{marker}\b\s+(?:mi\s+)?(?:cuenta\s+)?([a-záéíóúñ_ -]+)"
        match = re.search(pattern, lowered)
        if match:
            candidate = match.group(1).strip().split()[0]
            if candidate in account_words:
                return account_words[candidate]

    for word, normalized in account_words.items():
        if re.search(rf"\b{word}\b", lowered):
            return normalized

    product_match = re.search(r"\bPRD-\d+\b", message, re.IGNORECASE)
    if product_match:
        return product_match.group(0).upper()

    return None


def _enrich_intent(intent, message, confidence=None, model_name=None):
    result = {
        "intent": intent if intent in INTENTS else "desconocido",
    }

    if confidence is not None:
        result["confidence"] = round(float(confidence), 4)
    if model_name:
        result["model"] = model_name

    if result["intent"] == "consultar_gastos":
        result["days"] = _extract_days(message)
    elif result["intent"] == "ultimos_movimientos":
        result["limit"] = _extract_limit(message)
    elif result["intent"] == "transferencia":
        result["amount"] = _extract_amount(message)
        result["from_account"] = _extract_account(
            message,
            ["desde", "de", "origen"],
        )
        result["to_account"] = _extract_account(
            message,
            ["a", "hacia", "para", "destino"],
        )
    elif result["intent"] == "recarga_celular":
        result["phone_number"] = _extract_phone(message)
        result["amount"] = _extract_amount(message)

    return result


def predict_intent(message, min_confidence=0.34):
    model_bundle = _load_model()
    if model_bundle is None:
        return None

    text = str(message).strip()
    if not text:
        return {"intent": "desconocido", "model": "ml_empty"}

    classifier = model_bundle["model"]
    model_name = model_bundle.get("model_name", "supervised_ml")
    predicted = classifier.predict([text])[0]

    confidence = None
    if hasattr(classifier, "predict_proba"):
        probabilities = classifier.predict_proba([text])[0]
        confidence = max(probabilities)

    if confidence is not None and confidence < min_confidence:
        return {
            "intent": "desconocido",
            "confidence": round(float(confidence), 4),
            "model": model_name,
        }

    return _enrich_intent(predicted, text, confidence, model_name)
