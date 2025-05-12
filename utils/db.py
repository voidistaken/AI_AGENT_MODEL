# utils/db.py
import os
import psycopg
from psycopg import sql  # For safe SQL composition
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from utils.embedding import generate_embedding # Import generate_embedding here
load_dotenv()

DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

_conn = None

def get_connection():
    global _conn
    if _conn is None or _conn.closed:
        try:
            _conn = psycopg.connect(DB_URL)
            _conn.autocommit = True
            register_vector(_conn)
        except Exception as e:
            print(f"DB connection error: {e}")
            _conn = None
    return _conn

def release_connection(conn):
    if conn and not conn.closed:
        conn.close()

def retrieve_similar_data(user_id: str, query: str, top_k: int = 3):
    query_embedding = generate_embedding(query)
    print("📡 Query Embedding:", query_embedding[:5] if query_embedding else "None")

    if not query_embedding:
        print("❌ No embedding generated")
        return []

    conn = get_connection()
    if not conn:
        print("❌ Failed to get DB connection")
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    SELECT message_text, embedding <=> %s::vector AS distance
                    FROM user_messages
                    WHERE user_id = %s AND embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """), (query_embedding, user_id, query_embedding, top_k)
            )

            results = cur.fetchall()

        print("📊 Raw Results:", results)
        filtered = [row[0] for row in results]  # We only need the message text for context
        print("✅ Filtered:", filtered)
        return filtered
    except Exception as e:
        print(f"🔥 Error retrieving similar data: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def retrieve_user_data(user_id: str, data_key: str):
    conn = get_connection()
    if conn is None:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data_value FROM user_data WHERE user_id = %s AND data_key = %s",
                    (user_id, data_key)
                )
                result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error retrieving user data: {e}")
        return None
    finally:
        if conn:
            release_connection(conn)