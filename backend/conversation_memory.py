# MEMORIA TEMPORAL

conversation_memory = {}


def get_memory(user_id):
    return conversation_memory.get(user_id, {})


def save_memory(user_id, memory):
    conversation_memory[user_id] = memory


def clear_memory(user_id):
    conversation_memory[user_id] = {}
