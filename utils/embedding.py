import requests
from utils.auth import get_access_token
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_embedding(text: str) -> list:
    """Generate an embedding from Gemini API."""
    access_token = get_access_token()
    if not access_token:
        logging.error("Authentication failed for embedding API.")
        return None

    url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "models/embedding-001",
        "content": {"parts": [{"text": text}]}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        logging.debug(f"Embedding API response: {data}")  # 👈 Add this line

        embedding = data.get("embedding", {}).get("values")

        if not embedding or not isinstance(embedding, list) or len(embedding) != 768:
            logging.error("Embedding is missing or invalid format.")
            return None

        return embedding
    except requests.exceptions.RequestException as e:
        logging.error(f"Embedding API error: {e}")
        return None