from ml_intent_classifier import predict_intent


def detect_intent(message):
    result = predict_intent(message)

    if result is None:
        return {
            "intent": "desconocido",
            "model": "ml_model_not_found",
        }

    return result
