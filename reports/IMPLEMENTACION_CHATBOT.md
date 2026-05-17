# NovaBank AI — Documentación de Implementación

## Descripción general

NovaBank AI es un chatbot bancario conversacional que combina tres tecnologías:

1. **Clasificación de intenciones con aprendizaje supervisado** para entender cada mensaje del usuario.
2. **Lógica de negocio bancaria propia** para ejecutar operaciones reales sobre la base de datos.
3. **IA externa (LLM)** como redactor personalizado que formatea las respuestas según el perfil del cliente.

El sistema nunca inventa datos. Toda la información (saldos, movimientos, gastos, cashback) viene de la base de datos. El LLM solo redacta; no calcula ni decide.

---

## Arquitectura

```
Flutter (app móvil)
        │
        ▼  POST /chat
┌─────────────────────┐
│     backend/app.py  │  ◄── FastAPI: orquesta todo el flujo
└─────────────────────┘
    │       │       │
    ▼       ▼       ▼
intent  finance   llm
engine  engine   engine
    │       │       │
    ▼       ▼       ▼
  ML    SQLite/  OpenRouter
 model   MySQL    (GPT-OSS)
```

---

## Archivos y su rol en el sistema

### `backend/app.py` — Orquestador principal

Es el único punto de entrada HTTP. Recibe cada mensaje del usuario y decide qué hacer con él siguiendo este orden:

1. Cargar el contexto del usuario (cluster, segmento, cashback, categoría favorita).
2. Verificar si el mensaje es una palabra de cancelación (`cancelar`, `salir`, etc.).
3. Detectar la intención del mensaje con `intent_engine`.
4. Si hay un flujo activo (transferencia o recarga), continuar ese flujo.
5. Si no, ejecutar la lógica del intent detectado.
6. Devolver la respuesta formateada.

**Componentes internos importantes:**

| Función | Qué hace |
|---|---|
| `_load_user_context` | Consulta el perfil del cliente y construye el contexto del cluster |
| `_voice(ctx)` | Retorna el diccionario de texto/emojis correspondiente al cluster del cliente |
| `_personalized_prompt` | Construye el prompt completo que se envía al LLM con datos reales y perfil |
| `_format_transactions` | Formatea la lista de movimientos en texto numerado (fecha — categoría: monto) |
| `_handle_transfer` | Gestiona el flujo multi-turno de transferencia (monto → origen → destino) |
| `_handle_recharge` | Gestiona el flujo multi-turno de recarga celular (número → monto) |
| `_apply_transfer_slots` | Extrae datos del mensaje y los guarda en memoria de conversación |
| `_next_transfer_question` | Determina qué dato falta y genera la pregunta adecuada |
| `_bump_retry` / `_reset_retry` | Control de reintentos por slot para evitar bucles infinitos |

**Personalización por cluster (`CLUSTER_VOICES`):**

Cada cluster tiene su propio conjunto de textos, preguntas y emojis. Las respuestas directas (sin LLM) cambian completamente según el segmento. Claves disponibles en cada entrada:

| Clave | Uso |
|---|---|
| `saludo` | Bienvenida personalizada al inicio de la conversación |
| `done_transfer` / `done_recharge` | Mensaje de éxito al completar la operación |
| `done_transfer_extra` | Frase adicional tras transferencia exitosa |
| `ask_amount_transfer` | Pregunta por el monto a transferir |
| `ask_from` / `ask_to` | Preguntas por cuenta origen y destino |
| `ask_phone` / `ask_recharge_amount` | Preguntas del flujo de recarga |
| `accounts_intro_source` / `accounts_intro_target` | Encabezado de la lista de cuentas |
| `movimientos_intro` | Lambda `(n)` con el encabezado de la lista de movimientos |
| `movimientos_closing` | Frase de cierre tras mostrar movimientos |
| `saldo_intro` / `saldo_closing` | Encabezado y cierre de la consulta de saldo |
| `cashback` | Lambda `(ctx)` que formatea el mensaje de cashback con datos reales |
| `cancel` | Respuesta al cancelar un flujo activo |
| `default` | Respuesta cuando el intent no se reconoce |
| `retry_abort` / `retry_abort_recharge` | Mensaje al agotar reintentos en un flujo |
| `ok` / `money_emoji` / `phone_emoji` | Emojis usados en los mensajes de confirmación |

Segmentos:


| Cluster | Segmento | Estilo |
|---|---|---|
| 0 | Cliente Premium | Formal, ejecutivo, emojis mínimos (✅ 💼) |
| 1 | Cliente Ocasional | Amigable, paciente, emojis de apoyo (😊 💸 🎉) |
| 2 | Cliente Atípico | Preciso, orientado a datos, control total (✔ 📊) |
| 3 | Frecuente Estándar | Casual, ágil, energético (🚀 💳 👛) |

Las respuestas que sí pasan por el LLM (gastos, recomendaciones) reciben el perfil del cluster en el prompt para que el modelo ajuste tono y relevancia.

---

### `backend/intent_engine.py` — Detección de intención

Capa delgada que encapsula la llamada al clasificador ML. Devuelve el intent detectado y los datos extraídos del mensaje (monto, cuentas, días, límite, teléfono).

Si el modelo no está entrenado o no existe, devuelve `desconocido` con una etiqueta especial para que el sistema pueda manejarlo sin romper el flujo.

```python
def detect_intent(message) -> dict:
    # Retorna: {"intent": "...", "amount": ..., "from_account": ..., ...}
```

---

### `backend/ml_intent_classifier.py` — Clasificador supervisado + extracción de entidades

Este archivo hace dos cosas distintas:

**1. Clasificación de intención:**

Carga el modelo entrenado (`models/intent_classifier.joblib`) y predice la intención del mensaje. Si la confianza es menor al umbral (`min_confidence=0.34`), devuelve `desconocido` en lugar de una predicción poco confiable.

**2. Extracción de entidades (slot filling inicial):**

Usa expresiones regulares para extraer datos estructurados del primer mensaje:

| Función | Extrae |
|---|---|
| `_extract_amount` | Monto numérico (ignora `$` y `,`) |
| `_extract_days` | Periodo en días ("hoy"→1, "semana"→7, "mes"→30, o número explícito) |
| `_extract_limit` | Número de movimientos solicitados (1–10) |
| `_extract_phone` | Número de 10 dígitos |
| `_extract_account` | Tipo de cuenta por palabra clave o por ID `PRD-XXXX` |

La función `_extract_account` usa marcadores con `\b` (word boundary) para evitar falsos positivos. Por ejemplo, la preposición "a" en "quiero hacer una transferencia" **no** se interpreta como cuenta destino porque requiere que la palabra anterior sea un marcador exacto como "a", "hacia" o "para" seguido de una palabra de cuenta válida.

---

### `backend/train_intent_classifier.py` — Entrenamiento del modelo

Script independiente que entrena y guarda el clasificador. Se ejecuta una sola vez (o cuando se necesite reentrenar).

**Flujo de entrenamiento:**

```
CSV de conversaciones reales
        │
        ▼
Etiquetado débil (weak labeling)
con reglas regex por intent
        │
        ▼
Ejemplos sintéticos adicionales
(SYNTHETIC_EXAMPLES por intent)
        │
        ▼
Entrenamiento de 2 modelos:
  - Naive Bayes (MultinomialNB)
  - Regresión Logística
        │
        ▼
Selección del mejor por accuracy
        │
        ▼
Guardado en models/intent_classifier.joblib
Reporte en models/intent_classifier_report.json
```

**Datos de entrada:**

- `data/processed/conversaciones_clean.csv` — conversaciones reales etiquetadas por debilidad con `INTENT_KEYWORDS`.
- `SYNTHETIC_EXAMPLES` — ejemplos escritos a mano para cada intent, garantizando al menos una representación balanceada.

**Pipeline del modelo:**

```
TfidfVectorizer(ngram_range=(1,2), min_df=2)
        │
        ▼
MultinomialNB  o  LogisticRegression(class_weight="balanced")
```

El vectorizador convierte texto a representación TF-IDF con bigramas. `class_weight="balanced"` en LR compensa clases minoritarias en el dataset.

**Intenciones soportadas:**

```
consultar_saldo    consultar_gastos    ultimos_movimientos
transferencia      recarga_celular     consultar_cashback
recomendaciones    soporte             saludo    desconocido
```

---

### `backend/finance_engine.py` — Operaciones bancarias reales

Toda la lógica que toca la base de datos vive aquí. No hay SQL en `app.py`.

**Catálogo de productos (`PRODUCT_CATALOG`):**

Define todos los productos bancarios disponibles y sus capacidades:

- `can_transfer_from` — puede ser cuenta origen de una transferencia.
- `can_transfer_to` — puede recibir transferencias o pagos.
- `can_recharge_from` — puede pagar recargas de celular.

Esto evita errores en tiempo de ejecución: el sistema nunca intenta transferir desde una tarjeta de crédito ni recargar desde un seguro.

**Aliases de cuenta (`ACCOUNT_ALIASES`):**

Mapea palabras del usuario a tipos de producto internos:

```
"debito"   → "cuenta_debito"
"inversion" → "inversion_hey"
"negocios" → "cuenta_negocios"
"credito"  → "tarjeta_credito_hey"
```

**Funciones principales:**

| Función | Descripción |
|---|---|
| `get_balance(user_id)` | Retorna todos los productos del usuario con saldos |
| `get_expenses(user_id, days)` | Suma gastos del periodo desde `transacciones` |
| `get_last_transactions(user_id, limit)` | Últimos N movimientos ordenados por fecha |
| `get_operation_accounts(user_id, operation)` | Filtra cuentas por capacidad (origen, destino, recarga) |
| `transfer_between_accounts(...)` | Ejecuta la transferencia: actualiza saldos e inserta transacción |
| `recharge_phone(...)` | Descuenta saldo de cuenta origen e inserta transacción de recarga |
| `normalize_account_reference(account)` | Convierte alias de usuario al tipo interno |

---

### `backend/llm_engine.py` — Conexión a IA externa

Usa el cliente oficial de OpenAI apuntado al proxy de OpenRouter, que ofrece acceso a modelos de terceros.

```python
model = "openai/gpt-oss-120b:free"
base_url = "https://openrouter.ai/api/v1"
```

**Rol del LLM en el sistema:**

El LLM **no detecta intenciones** ni **toma decisiones bancarias**. Su único rol es redactar. Recibe un prompt que ya contiene:

- El dato bancario real calculado por el backend (gasto total, lista de movimientos, promociones).
- El perfil del cliente (cluster, tono, categoría favorita, cashback).
- Instrucciones precisas de formato y tono.

Se usa exclusivamente para los intents que requieren redacción narrativa:

| Intent | Por qué usa LLM |
|---|---|
| `consultar_gastos` | Resume el gasto con observaciones relevantes al perfil |
| `recomendaciones` | Redacta las 3 promociones generadas con tono personalizado |

Los demás intents usan respuestas directas generadas por código, más rápidas y sin costo de llamada a API:

| Intent | Respuesta directa |
|---|---|
| `consultar_saldo` | Lista de productos con saldos formateada por código |
| `ultimos_movimientos` | Lista numerada de movimientos con `_format_transactions` |
| `saludo` | Texto de bienvenida personalizado por cluster |
| `consultar_cashback` | Frase con monto real y categoría favorita |
| `transferencia` | Flujo multi-turno con confirmación y folio PDF |
| `recarga_celular` | Flujo multi-turno con confirmación y folio PDF |
| `soporte` | Respuesta del voice por defecto |

---

### `backend/promotions_engine.py` — Generador de promociones personalizadas

Construye un prompt detallado con el perfil del cluster y los datos del usuario, y llama al LLM para que genere exactamente 3 promociones en formato JSON estructurado.

La respuesta del LLM se parsea como JSON. Si el parseo falla, devuelve lista vacía con bandera de error (sin romper el flujo del chat).

Cada cluster tiene un `enfoque_promociones` distinto:

- **Premium:** lounges, seguros de viaje, inversiones, límites altos.
- **Ocasional:** bonos de bienvenida, cashback en primeras compras, cero comisiones.
- **Atípico:** cuentas empresariales, meses sin intereses en montos grandes, asesoría.
- **Frecuente Estándar:** cashback en categorías favoritas, puntos, recompensas por lealtad.

---

### `backend/user_engine.py` — Datos del cliente

Consulta el perfil del cliente desde la tabla `clientes`. Retorna datos como:

- `cluster` — segmento (0–3).
- `categoria_favorita` — categoría MCC de mayor gasto.
- `cashback_total` — cashback acumulado.
- `gasto_promedio` — ticket promedio por transacción.
- `num_transacciones` — volumen total de movimientos.
- `transacciones_internacionales` — cantidad de compras en el extranjero.

---

### `backend/conversation_memory.py` — Memoria conversacional temporal

Diccionario en memoria RAM indexado por `user_id`. Guarda el estado del flujo multi-turno:

```python
{
  "intent": "transferencia",
  "amount": 500.0,
  "from_account": "debito",
  "to_account": "inversion",
  "pending_slot": "to_account",
  "retries": {"to_account": 1}
}
```

Se borra al completar la operación o al cancelar. No persiste entre reinicios del servidor (diseño intencional para simplicidad).

---

### `backend/pdf_engine.py` — Generación de comprobantes

Genera un PDF de comprobante al finalizar una transferencia o recarga. Devuelve:

- `folio` — identificador único de la operación.
- `pdf_path` — ruta local del archivo generado en `backend/vouchers/`.

---

### `backend/db.py` — Conexión a base de datos

Crea el engine de SQLAlchemy que usan `finance_engine` y `user_engine`. La cadena de conexión se carga desde variables de entorno (`.env`).

---

## Flujo completo de un mensaje

```
Usuario: "quiero transferir 500 pesos de débito a inversión"
        │
        ▼
app.py: _load_user_context  →  cluster=3 (Frecuente Estándar)
        │
        ▼
intent_engine.detect_intent
        │
        ▼
ml_intent_classifier.predict_intent
  - TF-IDF vectoriza el texto
  - LogisticRegression predice: "transferencia" (confianza 0.87)
  - _extract_amount extrae: 500.0
  - _extract_account con marcador "de": "debito"
  - _extract_account con marcador "a": detecta "inversion" ← requiere \b
        │
        ▼
_handle_transfer
  - Guarda slots en memoria: amount=500, from_account="debito"
  - _next_transfer_question: falta to_account
  - Pregunta: "¿Y a cuál le llega? 👇"  (voz de cluster 3)
        │
        ▼
Usuario: "inversión"
        │
        ▼
_apply_transfer_slots (pending="to_account")
  - Guarda: to_account="inversion"
        │
        ▼
transfer_between_accounts
  - Valida cuentas, saldo, capacidades
  - Actualiza saldos en BD
  - Inserta registro en transacciones
        │
        ▼
generate_transfer_pdf  →  comprobante PDF
        │
        ▼
Respuesta: "¡Transferencia lista! 🚀
           💸 Monto: $500.00 MXN
           Origen: cuenta_debito (PRD-0001)
           Destino: inversion_hey (PRD-0002)
           ✅ Folio: TRF-XXXX
           Comprobante: backend/vouchers/voucher_XXXX.pdf
           ¡Tus saldos ya se actualizaron! 🙌"
```

---

## Flujo de entrenamiento del modelo

```bash
# 1. Preparar datos (si aplica)
python backend/convertir_datos.py

# 2. Entrenar y guardar el modelo
python backend/train_intent_classifier.py

# Salida:
# models/intent_classifier.joblib   ← modelo listo para producción
# models/intent_classifier_report.json ← métricas y accuracy por intent
```

---

## Iniciar el servidor

```bash
uvicorn backend.app:app --reload --port 8000
```

Endpoint principal:

```
POST /chat
Body: { "user_id": "USR-001", "message": "quiero ver mi saldo" }
```

---

## Consideraciones de diseño

| Decisión | Razón |
|---|---|
| Clasificador local (no LLM para intents) | Control total de latencia y costos; el modelo ML es determinista |
| Weak labeling + ejemplos sintéticos | El CSV de conversaciones reales no viene con etiquetas; las reglas regex bootstrapean el entrenamiento |
| Slot filling turn-by-turn | Permite conversaciones naturales sin pedir todo en un solo mensaje |
| `pending_slot` en memoria | Evita que el bot llene el slot equivocado cuando el usuario responde solo una cosa |
| Word boundary `\b` en extracción de cuentas | Previene falsos positivos como la "a" al final de "una" o "transferencia" |
| LLM solo para redacción | Separa responsabilidades: el backend garantiza los datos, el LLM garantiza el tono |
| `CLUSTER_VOICES` separado de `CLUSTER_TONES` | `CLUSTER_TONES` va al prompt del LLM; `CLUSTER_VOICES` controla las respuestas directas del código |
