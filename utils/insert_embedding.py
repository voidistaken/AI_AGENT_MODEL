import numpy as np
from dotenv import load_dotenv
import os
from utils.db import get_connection, release_connection
from pgvector.psycopg import register_vector  # Updated import path
from psycopg import sql  # For safer SQL composition
from embedding import generate_embedding
# Load environment variables
load_dotenv()

def main():
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            raise Exception("Failed to get database connection")

        # Register vector extension for this connection
        register_vector(conn)

        with conn:
            with conn.cursor() as cur:
                # Create vector extension if not exists
                cur.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS vector"))

                user_id = "user1"
                data_key = "bio"
                data_value = "This is the user's bio or custom data"

                # Generate embedding using your function
                embedding = generate_embedding(data_value)
                if embedding is None:
                    print("⚠️ Failed to generate embedding.")
                    return
                embedding_list = embedding

                # Insert or update using parameterized query
                cur.execute(
                    sql.SQL("""
                        INSERT INTO user_data (user_id, data_key, data_value, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, data_key)
                        DO UPDATE SET
                            data_value = EXCLUDED.data_value,
                            embedding = EXCLUDED.embedding,
                            updated_at = CURRENT_TIMESTAMP
                        """),
                    (user_id, data_key, data_value, embedding_list)
                )

                print(f"✅ Inserted/updated embedding for user_id={user_id}, key={data_key}")
                print(f"🔢 Embedding length: {len(embedding_list)}")

                # Verification attempt (within the cursor's scope)
                # cur.execute("SELECT embedding FROM user_data WHERE user_id = %s AND data_key = %s", (user_id, data_key))
                # inserted_embedding = cur.fetchone()
                # if inserted_embedding and inserted_embedding[0]:
                #     print(f"✅ Verified embedding length: {len(inserted_embedding[0])}")
                # else:
                #     print("❌ No embedding found after insertion")

    except Exception as e:
        print(f"❌ Error inserting embedding: {e}")
        # Consider more specific error handling here
        # from psycopg import errors
    finally:
        if conn:
            release_connection(conn)

if __name__ == "__main__":
    main()