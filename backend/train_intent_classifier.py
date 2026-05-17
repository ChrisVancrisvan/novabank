from pathlib import Path
import json
import re

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "conversaciones_clean.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier.joblib"
REPORT_PATH = MODEL_DIR / "intent_classifier_report.json"

INTENT_KEYWORDS = {
    "saludo": [
        r"^hola\b",
        r"^buenos dias\b",
        r"^buenos días\b",
        r"^buen dia\b",
        r"^buen día\b",
        r"^buenas tardes\b",
        r"^buenas noches\b",
        r"^hey\b",
        r"^que tal\b",
        r"^qué tal\b",
        r"^saludos\b",
    ],
    "consultar_saldo": [
        r"\bsaldo\b",
        r"cuanto tengo",
        r"cuánto tengo",
        r"dinero disponible",
        r"estado de cuenta",
        r"mi cuenta",
    ],
    "consultar_gastos": [
        r"\bgast[oa]s?\b",
        r"cuanto he gastado",
        r"cuánto he gastado",
        r"consumo",
        r"mis compras",
        r"en que gaste",
        r"en qué gasté",
    ],
    "ultimos_movimientos": [
        r"ultimos movimientos",
        r"últimos movimientos",
        r"ultimas compras",
        r"últimas compras",
        r"movimientos recientes",
        r"transacciones recientes",
    ],
    "recarga_celular": [
        r"recarga",
        r"recargar",
        r"tiempo aire",
        r"celular",
        r"telefono",
        r"teléfono",
    ],
    "transferencia": [
        r"transferir",
        r"transferencia",
        r"pasar dinero",
        r"mandar dinero",
        r"enviar dinero",
        r"mover dinero",
    ],
    "consultar_cashback": [
        r"cashback",
        r"recompensa",
        r"recompensas",
        r"puntos",
    ],
    "recomendaciones": [
        r"promocion",
        r"promoción",
        r"promociones",
        r"oferta",
        r"descuento",
        r"beneficio",
        r"que me conviene",
        r"qué me conviene",
        r"recomienda",
    ],
    "soporte": [
        r"ayuda",
        r"soporte",
        r"problema",
        r"no puedo",
        r"error",
        r"bloque",
        r"aclaracion",
        r"aclaración",
        r"reembolso",
        r"cargo no reconocido",
    ],
}

SYNTHETIC_EXAMPLES = {
    "consultar_saldo": [
        "quiero consultar mi saldo",
        "cuanto tengo en mi cuenta",
        "dime el saldo de mis productos",
        "cuanto dinero tengo disponible",
        "muestrame todas mis cuentas",
    ],
    "consultar_gastos": [
        "cuanto he gastado esta semana",
        "dime mis gastos del mes",
        "cuanto gaste hoy",
        "en que he gastado los ultimos 30 dias",
        "consulta mis gastos de hoy",
        "cuanto llevo gastado este mes",
        "dame el total de gastos",
        "revisa mis consumos de la semana",
        "cuanto dinero he usado ultimamente",
        "analiza mis gastos recientes",
    ],
    "ultimos_movimientos": [
        "muestrame mis ultimos movimientos",
        "quiero ver mis ultimas 10 compras",
        "dame mis transacciones recientes",
        "ultimos 5 movimientos",
        "ver movimientos recientes",
        "lista mis ultimas transacciones",
        "dame mis ultimos cargos",
        "quiero revisar mis movimientos",
        "muestra las ultimas compras",
        "ensename los ultimos pagos",
        "ultimos movimientos de mi cuenta",
        "ver ultimas operaciones",
        "historial reciente de movimientos",
        "cuales fueron mis ultimas compras",
    ],
    "recarga_celular": [
        "quiero hacer una recarga de celular",
        "recarga 100 pesos al 8112345678",
        "poner tiempo aire",
        "necesito recargar mi telefono",
    ],
    "transferencia": [
        "quiero transferir 500 pesos",
        "pasar dinero de debito a inversion",
        "hacer una transferencia",
        "mover 300 de mi cuenta de negocios",
    ],
    "consultar_cashback": [
        "cuanto cashback tengo",
        "muestrame mis recompensas",
        "cuantos puntos tengo acumulados",
    ],
    "recomendaciones": [
        "que promociones tengo",
        "que beneficios me convienen",
        "recomiendame ofertas personalizadas",
        "hay descuentos para mi",
    ],
    "soporte": [
        "tengo un problema con mi tarjeta",
        "necesito ayuda con un cargo no reconocido",
        "no puedo entrar a mi cuenta",
        "quiero levantar una aclaracion",
    ],
    "saludo": [
        "hola",
        "hola buen dia",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "hey que tal",
        "que tal",
        "saludos",
        "hola nova",
        "hola necesito ayuda",
        "buen dia como estas",
        "hola otra vez",
        "hola de nuevo",
    ],
    "desconocido": [
        "gracias",
        "ok",
        "500",
        "debito",
    ],
}


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def weak_label(text):
    lowered = normalize_text(text)
    if not lowered or len(lowered) < 3:
        return None

    for intent, patterns in INTENT_KEYWORDS.items():
        if any(re.search(pattern, lowered) for pattern in patterns):
            return intent

    if len(lowered.split()) <= 2:
        return "desconocido"

    return None


def build_training_frame():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"No existe el dataset: {DATA_PATH}")

    conversations = pd.read_csv(DATA_PATH, usecols=["input"])
    conversations["text"] = conversations["input"].fillna("").astype(str)
    conversations["intent"] = conversations["text"].apply(weak_label)
    labeled = conversations.dropna(subset=["intent"])[["text", "intent"]]

    synthetic_rows = [
        {"text": text, "intent": intent}
        for intent, examples in SYNTHETIC_EXAMPLES.items()
        for text in examples
    ]

    data = pd.concat([labeled, pd.DataFrame(synthetic_rows)], ignore_index=True)
    data = data.drop_duplicates(subset=["text", "intent"])
    return data


def train():
    data = build_training_frame()
    train_df, test_df = train_test_split(
        data,
        test_size=0.2,
        random_state=42,
        stratify=data["intent"],
    )

    candidates = {
        "naive_bayes": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
                ("model", MultinomialNB()),
            ]
        ),
        "logistic_regression": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        n_jobs=None,
                    ),
                ),
            ]
        ),
    }

    results = {}
    best_name = None
    best_score = -1
    best_model = None

    for name, model in candidates.items():
        model.fit(train_df["text"], train_df["intent"])
        predictions = model.predict(test_df["text"])
        score = accuracy_score(test_df["intent"], predictions)
        results[name] = {
            "accuracy": score,
            "classification_report": classification_report(
                test_df["intent"],
                predictions,
                output_dict=True,
                zero_division=0,
            ),
        }
        if score > best_score:
            best_name = name
            best_score = score
            best_model = model

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(
        {
            "model_name": best_name,
            "model": best_model,
            "labels": sorted(data["intent"].unique().tolist()),
            "training_rows": len(data),
            "accuracy": best_score,
        },
        MODEL_PATH,
    )

    report = {
        "best_model": best_name,
        "best_accuracy": best_score,
        "training_rows": len(data),
        "label_counts": data["intent"].value_counts().to_dict(),
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Modelo guardado en: {MODEL_PATH}")
    print(f"Reporte guardado en: {REPORT_PATH}")
    print(f"Mejor modelo: {best_name} ({best_score:.4f})")


if __name__ == "__main__":
    train()
