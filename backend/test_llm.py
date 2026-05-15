from llm_engine import generate_response


prompt = """
Eres un asistente bancario.
Saluda al usuario.
"""


response = generate_response(
    prompt
)

print(response)