import os
import msal
import threading
import webbrowser
from flask import Flask, request
import time
import json

# Microsoft Authentication Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("MSGRAPH_CLIENT_SECRET")
TENANT_ID = os.getenv("MSGRAPH_TENANT_ID")
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_FILE = "ms_token.json"  # Store tokens in a file
CACHE_FILE = "token_cache.json"  # Store MSAL cache
SCOPES = ["Calendars.Read", "User.Read"]

app = Flask(__name__)
auth_code = None
msal_app = None  # Declare msal_app globally

def start_flask():
    print("Starting Flask server on port 8000...")
    app.run(port=8000)

@app.route("/callback")
def callback():
    global auth_code
    auth_code = request.args.get("code")
    print(f"Received auth code: {auth_code}")
    return "Authentication successful! You can close this window."

def get_msal_app():
    """Initialize the MSAL application with a persistent token cache."""
    global msal_app
    if not msal_app:
        print("Initializing MSAL application...")
        authority = f"https://login.microsoftonline.com/{TENANT_ID}"
        # Initialize a serializable token cache
        cache = msal.SerializableTokenCache()
        if os.path.exists(CACHE_FILE):
            print(f"Loading token cache from {CACHE_FILE}...")
            with open(CACHE_FILE, "r") as f:
                cache.deserialize(f.read())
        msal_app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=authority,
            client_credential=CLIENT_SECRET,
            token_cache=cache
        )
        # Save cache changes after initialization
        try:
            with open(CACHE_FILE, "w") as f:
                f.write(msal_app.token_cache.serialize())
            print(f"Saved initial token cache to {CACHE_FILE}.")
        except Exception as e:
            print(f"Error saving token cache: {e}")
    return msal_app

def save_token(token_data):
    """Save the token data to a file."""
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)
        print(f"Saved token data to {TOKEN_FILE}.")
        # Also save the MSAL cache
        msal_app = get_msal_app()
        with open(CACHE_FILE, "w") as f:
            f.write(msal_app.token_cache.serialize())
        print(f"Saved MSAL cache to {CACHE_FILE}.")
    except Exception as e:
        print(f"Error saving token or cache: {e}")

def load_token():
    """Load the token data from the file."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                print(f"Loaded token data from {TOKEN_FILE}.")
                return json.load(f)
        except Exception as e:
            print(f"Error loading token data: {e}")
            return None
    print(f"No token file found at {TOKEN_FILE}.")
    return None

def authenticate_with_microsoft():
    """
    Authenticates with Microsoft and returns an access token. Handles both
    initial authentication and token refresh without prompting if a valid token exists.
    """
    global auth_code
    msal_app = get_msal_app()
    token_data = load_token()

    if token_data:
        print("Attempting silent token acquisition...")
        try:
            # Retrieve accounts from MSAL cache
            accounts = msal_app.get_accounts()
            print(f"🔍 Found {len(accounts)} accounts in MSAL cache.")
            if accounts:
                # Use the first account for silent token acquisition
                result = msal_app.acquire_token_silent(scopes=SCOPES, account=accounts[0])
                if "access_token" in result:
                    print("✅ Successfully acquired token silently (using refresh token).")
                    save_token(result)  # Save refreshed token data
                    return result["access_token"]
                else:
                    print("❌ Failed to acquire token silently. Error:", result.get("error_description", "Unknown error"))
            else:
                print("❌ No accounts found in MSAL cache. Checking token data for account info.")
                # Try to extract account info from token_data
                if "id_token_claims" in token_data:
                    username = token_data["id_token_claims"].get("preferred_username")
                    print(f"Found username in token data: {username}")
                    account = msal_app.get_accounts(username=username)
                    if account:
                        result = msal_app.acquire_token_silent(scopes=SCOPES, account=account[0])
                        if "access_token" in result:
                            print("✅ Successfully acquired token silently using token data account.")
                            save_token(result)
                            return result["access_token"]
                        else:
                            print("❌ Failed to acquire token silently with token data account. Error:", result.get("error_description", "Unknown error"))
                    else:
                        print("❌ No account found for username in token data.")
                else:
                    print("❌ No id_token_claims in token data.")
        except Exception as e:
            print(f"Error during silent token acquisition: {e}")
            auth_code = None

    # If no token or silent acquisition failed, initiate login
    print("🔐 Initiating new authentication flow.")
    auth_code = None
    threading.Thread(target=start_flask, daemon=True).start()
    auth_url = msal_app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)
    print(f"Opening auth URL: {auth_url}")
    webbrowser.open(auth_url)

    while not auth_code:
        time.sleep(1)

    token_response = msal_app.acquire_token_by_authorization_code(
        auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )

    if "access_token" in token_response:
        print("✅ Successfully acquired token using authorization code.")
        save_token(token_response)
        return token_response["access_token"]
    else:
        print("❌ Token request failed.")
        print("🔍 Response from Microsoft:", token_response)
        raise Exception(f"Authentication failed: {token_response.get('error_description', 'Unknown error')}")