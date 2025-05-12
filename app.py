import streamlit as st
import json
from dotenv import load_dotenv
from utils.db import get_connection, retrieve_user_data, release_connection
from utils.user_data import store_user_data
from utils.vector_utils import retrieve_similar_data as retrieve_similar_data_vector
from utils.memory_manager import get_relevant_memories, format_memory_context
import nest_asyncio
import requests
from utils.auth import get_access_token
from pgvector.psycopg import register_vector
from utils.ms_auth import authenticate_with_microsoft
from components.calendar import render_calendar_events, create_calendar_event, get_event_details, list_all_events
import datetime
import re
import os
import json
# --- Setup ---
nest_asyncio.apply()
load_dotenv()

# Microsoft Authentication Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("MSGRAPH_CLIENT_SECRET")
TENANT_ID = os.getenv("MSGRAPH_TENANT_ID")
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_FILE = "ms_token.json"
SCOPES = ["Calendars.Read", "Calendars.ReadWrite", "User.Read"]

# --- Initialize Database ---
try:
    conn = get_connection()
    if conn:
        register_vector(conn)
        conn.close()
        print("Database initialized successfully.")
    else:
        print("Failed to get database connection.")
except Exception as e:
    print(f"Error initializing database: {e}")

# --- Initialize Session State ---
def init_session_state():
    defaults = {
        "messages": [],
        "context": "",
        "user_id": "default-user",
        "ms_access_token": None,
        "rendered": False,
        "show_events": False,
        "name_corrections": {},
        "last_query": "",
        "recent_events": {},
        "pending_event": None  # Store event details before creation
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
            print(f"Initialized {key} in session state.")
init_session_state()

# --- Authentication ---
if not st.session_state.ms_access_token:
    print("No access token in session state. Attempting authentication...")
    try:
        st.session_state.ms_access_token = authenticate_with_microsoft()
        st.success("Microsoft authentication successful!")
        print("Authentication successful. Access token set.")
    except Exception as e:
        st.error(f"Microsoft authentication failed: {e}")
        print(f"Authentication failed: {e}")

# --- Gemini Response ---
def get_gemini_response(user_message: str, context: str = "") -> str:
    print(f"Generating Gemini response for message: {user_message}")
    access_token = get_access_token()
    if not access_token:
        print("No Gemini access token available.")
        return "🔒 Authentication failed. Please log in again."

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": f"{context}\nUser: {user_message}"}]}]}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0].get('text', '').strip()
        print(f"Gemini response: {response_text}")
        return response_text
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error in Gemini API: {e}")
        return f"⚠️ Gemini API Error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"⚠️ Gemini API Error: {e}"

# --- Utility Functions ---
def should_save_info(info_type: str, info_value: str, user_message: str) -> bool:
    """Determine if information should be saved."""
    print(f"Checking if info should be saved: {info_type} = {info_value}")
    save_rules = {
        "name": True,
        "favorite_color": True,
        "hobby": True,
        "favorite_movie": True,
        "contact": "willing to share" in user_message.lower(),
        "explicit_request": "remember this" in user_message.lower(),
        "other": False
    }
    return save_rules.get(info_type, False)

def store_user_data_persistent(user_id: str, data_key: str, data_value: str):
    """Store user data in the database."""
    print(f"Storing user data: {user_id}, {data_key}, {data_value}")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_data (user_id, data_key, data_value) VALUES (%s, %s, %s) "
                "ON CONFLICT (user_id, data_key) DO UPDATE SET data_value = EXCLUDED.data_value",
                (user_id, data_key, data_value)
            )
        conn.commit()
        print(f"💾 Stored in user_data: {data_key} = {data_value} for user {user_id}")
    except Exception as e:
        print(f"⚠️ Error storing in user_data: {e}")
    finally:
        if conn:
            release_connection(conn)

def normalize_name(query):
    """Apply spelling corrections and normalize query."""
    query = query.lower().strip()
    corrections = st.session_state.get("name_corrections", {})
    for incorrect, correct in corrections.items():
        if incorrect.lower() in query:
            query = query.replace(incorrect.lower(), correct.lower())
    return query

# --- Handle Send Message ---
def handle_send_message(user_message: str) -> str:
    """Process user message and generate bot response."""
    print(f"Handling user message: {user_message}")
    st.session_state.last_user_message = user_message
    user_id = st.session_state.user_id

    # Pre-process common calendar commands
    user_message_lower = user_message.lower().strip()
    if "list all events" in user_message_lower or "list me all calendar events" in user_message_lower:
        if not st.session_state.ms_access_token:
            return "⚠️ Please authenticate with Microsoft first. Try refreshing the page."
        return list_all_events(st.session_state.ms_access_token)
    
    if "create this event" in user_message_lower and st.session_state.pending_event:
        event = st.session_state.pending_event
        if not st.session_state.ms_access_token:
            return "⚠️ Please authenticate with Microsoft first. Try refreshing the page."
        result = create_calendar_event(
            st.session_state.ms_access_token,
            event["subject"],
            event["start_time"],
            event["end_time"],
            event["attendees"],
            event["location"],
            event["description"]
        )
        st.session_state.pending_event = None
        return result

    # Check for spelling corrections
    correction_match = re.match(r"no the correct spelling is (\w+)", user_message_lower)
    if correction_match:
        correct_spelling = correction_match.group(1)
        last_query = st.session_state.get("last_query", "")
        if last_query:
            st.session_state.name_corrections[last_query.lower()] = correct_spelling
            store_user_data_persistent(user_id, f"name_correction_{last_query.lower()}", correct_spelling)
            return f"Got it! I've updated the spelling to **{correct_spelling}**. Please repeat your request with the correct spelling."
        return "Please provide the name you were correcting."

    # Check recent events cache
    if "event of meeting with" in user_message_lower or "details of" in user_message_lower:
        query = normalize_name(user_message.split("with")[-1].strip())
        if query in st.session_state.recent_events:
            return st.session_state.recent_events[query]

    # Detect intent using Gemini
    intent_prompt = f"""You are connected to the user's Microsoft Calendar (Outlook) via the Microsoft Graph API. Do NOT reference Google Calendar or other calendar apps. Analyze the user message: "{user_message}"
    Identify the intent and extract relevant details. Respond in JSON format:
    - Create event: {{"intent": "create_event", "subject": "...", "start_time": "YYYY-MM-DDTHH:MM:SS", "end_time": "YYYY-MM-DDTHH:MM:SS", "attendees": ["..."], "location": "...", "description": "..."}}
    - Get event details: {{"intent": "get_event_details", "query": "..."}}
    - List all events: {{"intent": "list_all_events"}}
    - General query: {{"intent": "general"}}
    Rules:
    - Use ISO 8601 format for times (e.g., "2025-05-12T14:19:00").
    - If end_time is not specified, assume 1-hour duration.
    - If no specific date, assume tomorrow.
    - For dates like "5/12/2025", convert to "2025-05-12".
    - Location defaults to "Kitea" if not specified.
    - Attendees are optional; treat as names (not emails).
    - Subject should include the person’s name (e.g., "Meeting with The Weeknd").
    - For event details, extract name or date (e.g., "Taha", "2025-05-15").
    Examples:
    - "list all events" → {{"intent": "list_all_events"}}
    - "event of meeting with Mr. Taha" → {{"intent": "get_event_details", "query": "Taha"}}
    - "create meeting with The Weeknd location Kitea start time 2:19pm 5/12/2025 finish date 3:18pm 5/13/2025" → {{"intent": "create_event", "subject": "Meeting with The Weeknd", "start_time": "2025-05-12T14:19:00", "end_time": "2025-05-13T15:18:00", "attendees": [], "location": "Kitea", "description": ""}}
    - "details of my meeting on 2025-05-15" → {{"intent": "get_event_details", "query": "2025-05-15"}}
    - "yes all of the information is correct" → {{"intent": "confirm_event"}}
    """
    intent_response = get_gemini_response(intent_prompt)
    print(f"Intent response: {intent_response}")

    try:
        intent_data = json.loads(intent_response)
    except json.JSONDecodeError:
        intent_data = {"intent": "general"}
        print("Failed to parse intent response as JSON. Defaulting to general intent.")

    # Handle calendar-related intents
    if not st.session_state.ms_access_token:
        return "⚠️ Please authenticate with Microsoft first. Try refreshing the page."

    if intent_data["intent"] == "create_event":
        subject = intent_data.get("subject", "Meeting")
        start_time = intent_data.get("start_time")
        end_time = intent_data.get("end_time")
        attendees = intent_data.get("attendees", [])
        location = intent_data.get("location", "Kitea")
        description = intent_data.get("description")

        if start_time and end_time:
            # Store pending event for confirmation
            st.session_state.pending_event = {
                "subject": subject,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
                "location": location,
                "description": description
            }
            start_dt = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
            end_dt = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
            return (
                f"Please confirm the event details:\n"
                f"- **Subject**: {subject}\n"
                f"- **Start**: {start_dt}\n"
                f"- **End**: {end_dt}\n"
                f"- **Location**: {location}\n"
                f"- **Attendees**: {', '.join(attendees) or 'None'}\n"
                f"- **Description**: {description or 'None'}\n"
                f"Reply with 'create this event' to proceed."
            )
        return "⚠️ Please provide a valid start time and end time (e.g., '5/12/2025 2:19pm')."

    elif intent_data["intent"] == "confirm_event" and st.session_state.pending_event:
        event = st.session_state.pending_event
        result = create_calendar_event(
            st.session_state.ms_access_token,
            event["subject"],
            event["start_time"],
            event["end_time"],
            event["attendees"],
            event["location"],
            event["description"]
        )
        st.session_state.pending_event = None
        return result

    elif intent_data["intent"] == "get_event_details":
        query = normalize_name(intent_data.get("query", ""))
        if query:
            st.session_state.last_query = query
            details = get_event_details(st.session_state.ms_access_token, query)
            if not details.startswith("⚠️") and not details.startswith("No events"):
                st.session_state.recent_events[query] = details
            return details
        return "⚠️ Please specify the meeting or person (e.g., 'meeting with Mr. Taha')."

    elif intent_data["intent"] == "list_all_events":
        return list_all_events(st.session_state.ms_access_token)

    # Handle general queries and info saving
    prompt_analysis = f"""You are a helpful AI connected to Microsoft Calendar. For the user message: "{user_message}"
    Respond with:
    - "NAME: [name]" for first-time name
    - "UPDATE NAME: [name]" for name update
    - "FAVORITE COLOR: [color]" for favorite color
    - "HOBBY: [hobby]" for hobby
    - "FAVORITE MOVIE: [movie]" for favorite movie
    - "REMEMBER: [info]" for other info to remember
    - "NONE" if no info to remember"""
    
    analysis_response = get_gemini_response(prompt_analysis)
    print(f"🤖 Analysis Response: {analysis_response}")

    info_to_save = None
    info_type = None
    if ":" in analysis_response and "NONE" not in analysis_response:
        parts = analysis_response.split(":", 1)
        info_type = parts[0].strip().lower().replace(" ", "_")
        info_value = parts[1].strip()
        info_to_save = (info_type, info_value)
        if info_type == "update_name":
            info_type = "name"

    if info_to_save and should_save_info(info_to_save[0], info_to_save[1], user_message):
        store_user_data_persistent(user_id, info_to_save[0], info_to_save[1])
        print(f"💾 AI saved {info_to_save[0]}: {info_to_save[1]}")
    elif "NONE" in analysis_response:
        print("🤖 No specific information to remember.")

    relevant_memories = get_relevant_memories(user_id, user_message, top_n=3)
    memory_context = format_memory_context(user_id, relevant_memories, user_message)
    print(f"Memory context: {memory_context}")

    response = get_gemini_response(user_message, f"You are a helpful assistant connected to Microsoft Calendar. {memory_context} Based on this, answer the user's question.")
    cleaned_response = response.strip().replace("bot:", "").replace("Gemini:", "")
    store_user_data(int(user_id) if user_id.isdigit() else user_id, user_message, cleaned_response)
    st.session_state.context += f"\nUser: {user_message}\nBot: {cleaned_response}"
    print(f"Bot response: {cleaned_response}")
    return cleaned_response

# --- Message Send Handler ---
def send():
    """Handle chatbot send button click."""
    user_message = st.session_state.chat_input
    if user_message and user_message.strip():
        print(f"Sending message: {user_message}")
        st.session_state.messages.append({"role": "user", "text": user_message})
        response = handle_send_message(user_message)
        st.session_state.messages.append({"role": "bot", "text": response})
        st.session_state.chat_input = ""
    else:
        print("No message to send.")

# --- UI Rendering ---
try:
    st.markdown("""
    <style>
        .user-msg, .bot-msg { background-color: #40414f; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: left; }
        .stTextInput>div>div>input { background-color: #1e1e1e; color: #ffffff; }
        section[data-testid="stSidebar"] { width: 400px !important; float: right; order: 1; }
        .stApp { display: flex; flex-direction: row-reverse; }
        .stApp > div:first-child { order: 1; margin-right: 300px; }
    </style>
    """, unsafe_allow_html=True)
    print("Applied custom styling.")
except Exception as e:
    print(f"Error applying custom styling: {e}")
    st.error(f"Error applying custom styling: {e}")

try:
    with st.sidebar:
        st.title("💬 AI Assistant")
        st.write("Powered by Kitea")
        print("Rendering sidebar...")
        for msg in st.session_state.messages:
            css_class = "user-msg" if msg["role"] == "user" else "bot-msg"
            st.markdown(f"<div class='{css_class}'>{msg['text']}</div>", unsafe_allow_html=True)
            print(f"Rendered message: {msg['text']}")
        st.text_input("Type your message...", key="chat_input")
        st.button("Send", on_click=send)
        print("Sidebar rendering complete.")
    st.session_state.rendered = True
    print("Set rendered flag to True after sidebar.")
except Exception as e:
    print(f"Error rendering sidebar: {e}")
    st.error(f"Error rendering sidebar: {e}")

try:
    st.title("📊 Your Dashboard")
    st.write("View your upcoming calendar events and interact with the AI assistant.")
    print("Rendered dashboard title and description.")

    if st.button("Show My Calendar Events"):
        st.session_state.show_events = True
        print("Show My Calendar Events button clicked. Set show_events to True.")

    if st.session_state.show_events:
        if st.session_state.ms_access_token:
            render_calendar_events(st.session_state.ms_access_token)
        else:
            st.error("Please authenticate with Microsoft first.")
            print("No access token. Prompted for authentication.")
    st.session_state.rendered = True
    print("Set rendered flag to True after dashboard.")
except Exception as e:
    print(f"Error rendering dashboard: {e}")
    st.error(f"Error rendering dashboard: {e}")

if not st.session_state.rendered:
    st.warning("The application failed to render. Please check the terminal for errors or try refreshing the page.")
    print("Displayed fallback warning message.")