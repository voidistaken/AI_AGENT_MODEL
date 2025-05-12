from utils.db import get_connection , release_connection
import numpy as np
from typing import Optional
from utils.embedding import generate_embedding
import logging
logger = logging.getLogger(__name__)
from utils.db import  get_connection,release_connection


def store_user_data(
    user_id: int,
    message_text: str,
    session_id: Optional[str] = None,
    embedding: Optional[list] = None,
    conn=None
):
    """
    Store a user's message and its embedding in the database.
    If no embedding is provided, generate one using the Gemini API.
    """
    local_conn = False
    try:
        if conn is None:
            conn = get_connection()
            local_conn = True

        # Generate embedding if not provided
        if embedding is None:
            embedding = generate_embedding(message_text)

        # Insert the user message (with embedding) into user_messages table
        sql = """
            INSERT INTO user_messages (user_id, session_id, message_text, embedding)
            VALUES (%s, %s, %s, %s)
        """
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, session_id, message_text, embedding))

    except Exception as e:
        logger.error("Error storing user message for user_id %s: %s", user_id, e)
        raise
    finally:
        if local_conn:
            release_connection(conn)

