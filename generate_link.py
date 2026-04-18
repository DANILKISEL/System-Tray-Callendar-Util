#!/usr/bin/env python3
"""
Generate a Google Meet link for a calendar event.

Usage:
    ./generate_link.py '<json_event_string>'

The script creates a temporary event via Google Calendar API,
adds Google Meet conferencing, and returns the Meet URL.
"""

import sys
import json
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Path to token and credentials
TOKEN_PATH = Path(__file__).parent / 'token.pickle'
CREDENTIALS_PATH = Path(__file__).parent / 'credentials.json'


def get_authenticated_service():
    """Authenticate and return Google Calendar API service."""
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    "credentials.json not found. Download from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def create_meeting_link(event_data):
    """
    Create a temporary Google Calendar event with Meet conferencing.
    Returns the Google Meet URL.
    """
    service = get_authenticated_service()

    # Parse input JSON
    try:
        input_event = json.loads(event_data)
    except json.JSONDecodeError:
        # If input is already a dict (from subprocess call)
        input_event = event_data

    # Use event details from calendar if available
    summary = input_event.get('title', 'Meeting')
    start_time = input_event.get('startDate')
    end_time = input_event.get('endDate')

    # Fallback times if not provided
    if not start_time:
        start_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat() + 'Z'
    if not end_time:
        end_time = (datetime.utcnow() + timedelta(minutes=65)).isoformat() + 'Z'

    # Create event body with conference data
    event_body = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{datetime.now().timestamp()}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            }
        },
    }

    # Insert event
    created_event = service.events().insert(
        calendarId='primary',
        conferenceDataVersion=1,
        body=event_body
    ).execute()

    # Extract Google Meet link
    conference_data = created_event.get('conferenceData', {})
    entry_points = conference_data.get('entryPoints', [])
    for ep in entry_points:
        if ep.get('entryPointType') == 'video':
            meet_link = ep.get('uri')
            if meet_link:
                # Optionally delete the temporary event to keep calendar clean
                # service.events().delete(calendarId='primary', eventId=created_event['id']).execute()
                return meet_link

    raise ValueError("No Google Meet link found in created event.")


def main():
    if len(sys.argv) != 2:
        print("Usage: generate_link.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    event_json_str = sys.argv[1]

    try:
        meet_link = create_meeting_link(event_json_str)
        print(meet_link)
    except Exception as e:
        print(f"Error generating Meet link: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()