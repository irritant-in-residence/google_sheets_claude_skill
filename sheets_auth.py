#!/usr/bin/env python3
"""
sheets_auth.py — Google Sheets OAuth helper.

Handles OAuth2 flow, token caching, and returns an authenticated
Google Sheets API service object.

Usage:
    # First-time setup (opens browser for OAuth consent)
    python3 sheets_auth.py --setup

    # As a library
    from sheets_auth import get_sheets_service
    service = get_sheets_service()
"""

import argparse
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = SKILL_DIR / "credentials.json"
TOKEN_FILE = SKILL_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_credentials():
    """Load or refresh OAuth credentials. Runs interactive flow if needed."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
            return creds
        except Exception as e:
            print(f"Token refresh failed ({e}), re-authenticating...")

    # Need fresh auth
    if not CREDENTIALS_FILE.exists():
        print(f"ERROR: credentials.json not found at {CREDENTIALS_FILE}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        print("See SKILL.md Step 4 for details.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    # Save token for future use
    TOKEN_FILE.write_text(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")

    return creds


def get_sheets_service():
    """Return an authenticated Google Sheets API v4 service object."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)
    return service


def get_drive_service():
    """Return an authenticated Google Drive API v3 service object."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)
    return service


def main():
    parser = argparse.ArgumentParser(description="Google Sheets auth helper")
    parser.add_argument("--setup", action="store_true",
                        help="Run OAuth flow and save token")
    args = parser.parse_args()

    if args.setup:
        print("Starting OAuth flow...")
        creds = get_credentials()
        print("Authentication successful!")

        # Quick verification: list spreadsheet properties
        from googleapiclient.discovery import build
        service = build("sheets", "v4", credentials=creds)
        print("Sheets API service created. Ready to use.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
