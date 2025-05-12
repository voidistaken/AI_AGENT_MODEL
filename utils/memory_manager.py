# utils/memory_manager.py
from utils.db import retrieve_similar_data
from utils.embedding import generate_embedding
from utils.db import retrieve_similar_data, retrieve_user_data

def get_relevant_memories(user_id: str, query: str, top_n: int = 3):
    query_embedding = generate_embedding(query)
    if query_embedding:
        relevant_data = retrieve_similar_data(user_id, query, top_k=top_n)
        return relevant_data
    else:
        return []

def format_memory_context(user_id: str, memories: list, last_user_message: str) -> str:
    """
    Formats a list of memories into a context string for the LLM prompt,
    including specific user information conditionally.
    """
    context_parts = []
    user_name = retrieve_user_data(user_id, "name")
    favorite_color = retrieve_user_data(user_id, "favorite_color")
    hobby = retrieve_user_data(user_id, "hobby")

    if user_name:
        context_parts.append(f"The user's name is {user_name}.")

    if favorite_color:
        # Only include favorite color if the user's question is related to colors
        if any(keyword in last_user_message.lower() for keyword in ["color", "favourite", "like"]):
            context_parts.append(f"The user's favorite color is {favorite_color}.")

    if hobby:
        # Only include hobby if the user's question is related to hobbies or activities
        if any(keyword in last_user_message.lower() for keyword in ["hobby", "play", "do", "activity"]):
            context_parts.append(f"The user's favorite hobby is {hobby}.")

    if memories:
        context_parts.append("Previously, you and the user discussed:")
        for memory in memories:
            context_parts.append(memory.strip())

    return " ".join(context_parts)