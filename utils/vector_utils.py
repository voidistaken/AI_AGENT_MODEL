# vector_utils.py (or you might rename this to db_utils.py or similar)
import psycopg
from pgvector.psycopg import register_vector
import logging
from typing import Optional
import numpy as np
from dotenv import load_dotenv
from utils.db import get_connection, release_connection
from utils.embedding import generate_embedding

load_dotenv()
logger = logging.getLogger(__name__)

def retrieve_similar_data(user_id: str, query: str, top_k: int = 3):
    """
    Retrieves the top_k most similar messages from user_messages
    for a given user query.
    """
    query_embedding = generate_embedding(query)
    print("📡 Query Embedding:", query_embedding[:5] if query_embedding else "None")

    if not query_embedding:
        print("❌ No embedding generated for query")
        return []

    conn = get_connection()
    if not conn:
        print("❌ Failed to get DB connection")
        return []

    results = []
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                psycopg.sql.SQL("""
                    SELECT message_text, (embedding <-> %s::vector) AS distance
                    FROM user_messages
                    WHERE user_id = %s AND embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT %s;
                """),
                (query_embedding, user_id, top_k)
            )
            results = cursor.fetchall()
            print("📊 Similar Messages Retrieved:", results)
            return [row[0] for row in results] # Return only the message text
    except psycopg.Error as e:
        print(f"Database error in retrieve_similar_data: {e}")
    finally:
        if conn:
            release_connection(conn)
    return results

def insert_or_update_embedding(data_key: str, data_value: str, user_id: Optional[int] = None, conn=None):
    """
    This function seems intended for a different table ('embeddings').
    For storing user messages, please use the store_user_data function in user_data.py.
    We will focus on retrieve_similar_data for memory retrieval from user_messages.
    """
    logger.warning("insert_or_update_embedding in vector_utils is likely not used for user messages.")
    local_conn = False
    try:
        if conn is None:
            conn = get_connection()
            local_conn = True

        embedding = generate_embedding(data_value)

        sql = """
            INSERT INTO embeddings (data_key, data_value, embedding, user_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (data_key) DO UPDATE
            SET data_value = EXCLUDED.data_value,
                embedding = EXCLUDED.embedding;
        """
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, (data_key, data_value, embedding, user_id))

    except Exception as e:
        logger.error(f"Error in insert_or_update_embedding for key %s: %s", data_key, e)
        raise
    finally:
        if local_conn:
            release_connection(conn)

# You might want to remove or rename search_similar_embeddings
# and use retrieve_similar_data instead throughout your project.