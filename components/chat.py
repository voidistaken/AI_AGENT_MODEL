import os
import asyncio
import requests
import streamlit as st
import websockets
import nest_asyncio
from dotenv import load_dotenv

from utils.auth import get_access_token, authenticate_with_google, logout
from utils.db import get_connection , retrieve_similar_data
from utils.user_data import store_user_data, retrieve_user_data
nest_asyncio.apply()
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WS_SERVER_URL = os.getenv('WS_SERVER_URL', 'ws://localhost:8765')
USER_ID = "default-user"  


def ensure_authenticated():
    access_token = get_access_token()
    if not access_token:
        st.warning("You are not authenticated. Please log in.")
        authenticate_with_google()
        st.success("Authentication successful!")
    return get_access_token()


def get_gemini_response(user_message, context=""):
    access_token = ensure_authenticated()
    if not access_token:
        return "Authentication failed. Please log in again."

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro:generateContent"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    prompt = f"""You are Kitea AI, a helpful assistant. Use the following context to answer the user question.\n\nContext:\n{context}\n\nUser: {user_message}\nKitea:"""

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
    else:
        return f"Error: {response.status_code} - {response.text}"


async def send_message_to_ws(message):
    try:
        async with websockets.connect(WS_SERVER_URL) as ws:
            print(f"Connected to WebSocket server at {WS_SERVER_URL}")
            await ws.send(message)
            response = await ws.recv()
            return response
    except Exception as e:
        print(f"WebSocket error: {e}")
        return f"WebSocket error: {e}"


def handle_send_message(user_message):
    return asyncio.run(send_message_to_ws(user_message))


def display_chat():
    st.set_page_config(page_title="Kitea AI", layout="centered")
    st.title("💬 Kitea AI Chat Assistant")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    user_message = st.text_input("Type your message and press Enter:", key="input")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Logout"):
            logout()
            st.session_state.clear()
            st.success("Logged out.")
            st.experimental_rerun()

    if user_message and st.button("Send"):
        st.session_state.chat_history.append(f"👤 **You**: {user_message}")

        similar_memories = retrieve_similar_data(USER_ID, user_message, top_k=3) # Corrected top_k
        context = "\n".join(similar_memories) # Adjusted context formatting

        response = get_gemini_response(user_message, context)

        store_user_data(USER_ID, user_message, response)

        st.session_state.chat_history.append(f"🤖 **Kitea**: {response}")

    st.divider()
    for message in st.session_state.chat_history:
        st.markdown(message)


if __name__ == "__main__":
    display_chat()