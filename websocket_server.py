import asyncio
import nest_asyncio
import websockets
import requests
from dotenv import load_dotenv
import os
import google.auth
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import json
from google.oauth2.credentials import Credentials  

nest_asyncio.apply()

load_dotenv()

CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE')  
SCOPES = ['https://www.googleapis.com/auth/generative-language.retriever']

conversation_history = []

def authenticate_with_google():
    credentials = None
    token_file = 'token.json'

    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as token:
                credentials_data = json.load(token)
                credentials = Credentials.from_authorized_user_info(credentials_data)
        except Exception as e:
            print(f"Error loading credentials from token file: {e}")

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                credentials = None  
        if not credentials:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_FILE,
                    scopes=SCOPES
                )
                credentials = flow.run_local_server(port=2222)
            except Exception as e:
                print(f"OAuth2 authentication failed: {e}")
                return None

        try:
            with open(token_file, 'w') as token:
                token.write(credentials.to_json())
        except Exception as e:
            print(f"Error saving credentials to token file: {e}")

    return credentials

def get_gemini_response(user_message):
    credentials = authenticate_with_google()
    if not credentials:
        return "Authentication failed."

    access_token = credentials.token
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_message}
                ]
            }
        ]
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            candidates = response.json().get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0].get("text", "No response text found.")
            else:
                return "No candidates returned from Gemini."
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error calling Gemini API: {e}"

async def handle_client(websocket):
    print(f"New connection from {websocket.remote_address}")
    
    try:
        while True:
            message = await websocket.recv()
            print(f"Received message: {message}")

            conversation_history.append(f"User: {message}")

            # Limit the context to the last 10 messages
            context = "\n".join(conversation_history[-10:])

            gemini_response = await asyncio.to_thread(get_gemini_response, context)

            cleaned_response = gemini_response.replace("Bot:", "").strip()

            conversation_history.append(f"Bot: {cleaned_response}")

            await websocket.send(cleaned_response)
    except websockets.exceptions.ConnectionClosedError:
        print(f"Connection closed by client: {websocket.remote_address}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

async def start_server():
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")
    await server.wait_closed()
async def send_message_to_ws(message):
    try:
        async with websockets.connect('ws://localhost:8765') as ws:
            await ws.send(message)
            return await ws.recv()
    except Exception:
        return None

if __name__ == "__main__":
    asyncio.run(start_server())
