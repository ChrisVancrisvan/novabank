from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import pandas as pd


# CARGAR MODELO

model = SentenceTransformer(
    'all-MiniLM-L6-v2'
)


# CARGAR CONVERSACIONES

conversaciones = pd.read_csv(
    '../data/processed/conversaciones_clean_fixed.csv'
)


# LIMPIEZA TEXTO

conversaciones['input'] = (
    conversaciones['input']
    .fillna('')
    .astype(str)
)

conversaciones['output'] = (
    conversaciones['output']
    .fillna('')
    .astype(str)
)


# CREAR EMBEDDINGS

embeddings = model.encode(
    conversaciones['input'].tolist(),
    show_progress_bar=True
)


# FUNCIÓN PRINCIPAL

def retrieve_context(query):

    query_embedding = model.encode([query])

    similarities = cosine_similarity(
        query_embedding,
        embeddings
    )

    best_match = similarities.argmax()


    matched_input = conversaciones.iloc[
        best_match
    ]['input']


    matched_output = conversaciones.iloc[
        best_match
    ]['output']


    context = f"""
    Pregunta similar encontrada:
    {matched_input}

    Respuesta relacionada:
    {matched_output}
    """


    return context