import requests
import datetime
import streamlit as st
import pandas as pd

def get_calendar_events(access_token, query=None, date_range_days=30):
    """Fetch calendar events from Microsoft Graph API, optionally filtered by query."""
    print(f"Fetching calendar events with query: {query}")
    url = "https://graph.microsoft.com/v1.0/me/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    end_date = (datetime.datetime.now() + datetime.timedelta(days=date_range_days)).isoformat() + "Z"
    params = {
        "$filter": f"start/dateTime ge '{datetime.datetime.now().isoformat()}Z' and start/dateTime le '{end_date}'",
        "$select": "subject,start,end,location,bodyPreview,attendees",
        "$top": 100
    }
    if query:
        query = query.lower().replace("mr.", "").strip()
        params["$filter"] += f" and (contains(tolower(subject), '{query}') or contains(tolower(attendees/emailAddress/name), '{query}'))"
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        events = response.json().get("value", [])
        print(f"Retrieved {len(events)} calendar events.")
        return events
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching calendar events: {e}")
        return f"⚠️ Error fetching calendar events: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return f"⚠️ Error fetching calendar events: {e}"

def create_calendar_event(access_token, subject, start_time, end_time, attendees=None, location=None, description=None):
    """Create a new event in the Microsoft Calendar."""
    print(f"Creating calendar event: {subject}")
    url = "https://graph.microsoft.com/v1.0/me/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        start_dt = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00") if start_time.endswith("Z") else start_time)
        end_dt = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00") if end_time.endswith("Z") else end_time)
        body = {
            "subject": subject,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC"
            },
            "location": {"displayName": location or "Kitea"},
            "body": {"content": description or "", "contentType": "text"}
        }
        if attendees:
            body["attendees"] = [{"emailAddress": {"address": attendee, "name": attendee}, "type": "required"} for attendee in attendees]
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        event = response.json()
        start = datetime.datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        return f"Event created successfully: **{subject}** on {start} at {location or 'Kitea'}."
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error creating calendar event: {e}")
        return f"⚠️ Error creating event: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return f"⚠️ Error creating event: {e}"

def render_calendar_events(access_token, query=None):
    """Render calendar events as a table and expandable details."""
    print(f"Rendering calendar events with query: {query}")
    events = get_calendar_events(access_token, query=query)
    if isinstance(events, str):
        st.error(events)
        print(f"Displayed error: {events}")
        return
    if not events:
        st.info("No upcoming events found in the next 30 days.")
        print("No upcoming events found.")
        return

    st.subheader("Upcoming Calendar Events")
    event_data = []
    for event in events:
        subject = event.get("subject", "No subject")
        start = event.get("start", {}).get("dateTime", "No start time")
        end = event.get("end", {}).get("dateTime", "No end time")
        location = event.get("location", {}).get("displayName", "No location")
        description = event.get("bodyPreview", "No description")
        attendees = event.get("attendees", [])

        if start != "No start time":
            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            start = start_dt.strftime("%Y-%m-%d %H:%M")
        if end != "No end time":
            end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
            end = end_dt.strftime("%Y-%m-%d %H:%M")

        attendee_names = [attendee["emailAddress"]["name"] for attendee in attendees if attendee.get("emailAddress", {}).get("name")]
        attendees_display = ", ".join(attendee_names) if attendee_names else "No attendees"

        event_data.append({
            "Subject": subject,
            "Start Time": start,
            "End Time": end,
            "Location": location,
            "Description": description,
            "Attendees": attendees_display
        })

    df = pd.DataFrame(event_data)
    st.table(df[["Subject", "Start Time", "End Time", "Location"]])
    print("Rendered events table.")

    st.markdown("### Event Details")
    for event in event_data:
        with st.expander(f"{event['Subject']} ({event['Start Time']})"):
            st.write(f"**Start Time:** {event['Start Time']}")
            st.write(f"**End Time:** {event['End Time']}")
            st.write(f"**Location:** {event['Location']}")
            st.write(f"**Description:** {event['Description']}")
            st.write(f"**Attendees:** {event['Attendees']}")
        print(f"Rendered event details for: {event['Subject']}")

def get_event_details(access_token, query):
    """Get details of specific events matching the query."""
    print(f"Fetching details for events matching: {query}")
    events = get_calendar_events(access_token, query=query)
    if isinstance(events, str):
        return events
    if not events:
        return f"No events found matching '{query}' in the next 30 days. Try specifying a date (e.g., 'on 2025-05-15') or check the spelling."

    details = []
    for event in events:
        subject = event.get("subject", "No subject")
        start = event.get("start", {}).get("dateTime", "No start time")
        end = event.get("end", {}).get("dateTime", "No end time")
        location = event.get("location", {}).get("displayName", "No location")
        description = event.get("bodyPreview", "No description")
        attendees = event.get("attendees", [])
        attendee_names = [attendee["emailAddress"]["name"] for attendee in attendees if attendee.get("emailAddress", {}).get("name")]
        attendees_display = ", ".join(attendee_names) if attendee_names else "No attendees"

        if start != "No start time":
            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            start = start_dt.strftime("%Y-%m-%d %H:%M")
        if end != "No end time":
            end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
            end = end_dt.strftime("%Y-%m-%d %H:%M")

        details.append(
            f"**{subject}**\n"
            f"- **Start**: {start}\n"
            f"- **End**: {end}\n"
            f"- **Location**: {location}\n"
            f"- **Description**: {description}\n"
            f"- **Attendees**: {attendees_display}"
        )
    return "\n\n".join(details)

def list_all_events(access_token):
    """List all events in the next 30 days as text."""
    print("Listing all calendar events...")
    events = get_calendar_events(access_token)
    if isinstance(events, str):
        return events
    if not events:
        return "No upcoming events found in the next 30 days."

    event_list = []
    for event in events:
        subject = event.get("subject", "No subject")
        start = event.get("start", {}).get("dateTime", "No start time")
        if start != "No start time":
            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            start = start_dt.strftime("%Y-%m-%d %H:%M")
        event_list.append(f"- {subject} at {start}")
    return "\n".join(event_list) or "No upcoming events found."