import os
import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import streamlit as st
from dotenv import load_dotenv
import json
from google.oauth2.credentials import Credentials

TOKEN_FILE = 'token.json'

load_dotenv()

CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", "client_secret.json")
SCOPES = ['https://www.googleapis.com/auth/generative-language.retriever']

def authenticate_with_google():
    credentials = None
    # Temporarily force re-authentication
    credentials = None
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            print(f"Using client secret file: {CLIENT_SECRET_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                scopes=SCOPES
            )
            credentials = flow.run_local_server(port=8888)

        with open(TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())

    return credentials

def get_access_token():
    """Fetch or refresh the current access token, and re-authenticate if needed."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token_file:
            credentials = Credentials.from_authorized_user_info(json.load(token_file))

            if credentials and credentials.valid:
                return credentials.token
            elif credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                save_credentials(credentials)
                return credentials.token

    # If we reach here, no valid token → perform authentication flow
    credentials = authenticate_with_google()
    if credentials and credentials.valid:
        return credentials.token
    return None


def save_credentials(credentials):
    """Save the credentials to token.json"""
    with open(TOKEN_FILE, 'w') as token_file:
        token_file.write(credentials.to_json())  

def logout():
    """Logout by deleting the token.json file"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)