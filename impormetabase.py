#!/usr/bin/env python3
"""
impormetabase.py

Fetches a Metabase card as CSV and uploads it to a Google Sheet.

Configuration via environment variables:
- METABASE_URL (e.g. https://mb-dynamic.rata.id) [required]
- METABASE_USER, METABASE_PASS [required]
- METABASE_CARD_ID (card id or question id) [required]
- GCP_SERVICE_ACCOUNT (JSON string of service account key) [required]
- GSHEET_ID (spreadsheet id) [required]
- GSHEET_SHEET_NAME (worksheet name, default: "order_payment")
"""
from typing import List, Optional
import os
import json
import io
import sys
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

def get_env(name: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name, default)
    if required and not val:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return val

def get_metabase_data(metabase_url: str, username: str, password: str, card_id: str, timeout: int = 60) -> Optional[List[List]]:
    """
    Log into Metabase and export the specified card as CSV.
    Returns data as list-of-lists (including header row) or None on failure.
    """
    session = requests.Session()
    login_url = f"{metabase_url.rstrip('/')}/api/session"
    try:
        resp = session.post(login_url, json={"username": username, "password": password}, timeout=15)
        resp.raise_for_status()
        session_id = resp.json().get("id")
        if not session_id:
            print("Metabase login succeeded but no session id returned.", file=sys.stderr)
            return None
        session.headers.update({"X-Metabase-Session": session_id})
    except Exception as e:
        print(f"[Metabase] Login failed: {e}", file=sys.stderr)
        return None

    csv_url = f"{metabase_url.rstrip('/')}/api/card/{card_id}/query/csv"
    try:
        resp = session.post(csv_url, timeout=timeout)
        resp.raise_for_status()
        # read into pandas for convenience and normalize NaNs
        df = pd.read_csv(io.StringIO(resp.text))
        df = df.fillna("")
        data = [df.columns.tolist()] + df.values.tolist()
        print(f"[Metabase] Pulled {len(data)-1} rows (+ header).")
        return data
    except Exception as e:
        print(f"[Metabase] Failed to export card {card_id} as CSV: {e}", file=sys.stderr)
        return None

def upload_to_gsheet(data: List[List], creds_info: dict, spreadsheet_id: str, sheet_name: str = "order_payment"):
    """
    Uploads a list-of-lists to a worksheet. Keeps row 1 as header (A1) and replaces rows below it.
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)

    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=100, cols=max(10, len(data[0]) if data else 10))

    # Ensure header row is set and clear everything below
    if not data:
        print("[GSheet] No data to upload.")
        return

    header = data[0]
    body = data[1:]

    # Set header in A1
    ws.update("A1", [header], value_input_option="USER_ENTERED")
    # Resize sheet to 1 row so old rows are removed, then append new rows (if any)
    if body:
        # resize to 1 row to remove old contents below header
        ws.resize(rows=1)
        # append_rows will add rows below header
        ws.append_rows(body, value_input_option="USER_ENTERED")
    else:
        # no body rows - just ensure sheet has single header row
        ws.resize(rows=1)

    print(f"[GSheet] Uploaded {len(body)} rows to '{sheet_name}' in spreadsheet {spreadsheet_id}.")

def main():
    try:
        METABASE_URL = get_env("METABASE_URL")
        METABASE_USER = get_env("METABASE_USER")
        METABASE_PASS = get_env("METABASE_PASS")
        METABASE_CARD_ID = get_env("METABASE_CARD_ID")

        GSHEET_ID = get_env("GSHEET_ID")
        GSHEET_SHEET_NAME = os.getenv("GSHEET_SHEET_NAME", "order_payment")

        creds_raw = get_env("GCP_SERVICE_ACCOUNT")
        creds_info = json.loads(creds_raw)

    except EnvironmentError as ee:
        print(f"[Config] {ee}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("[Config] GCP_SERVICE_ACCOUNT is not valid JSON", file=sys.stderr)
        sys.exit(1)

    data = get_metabase_data(METABASE_URL, METABASE_USER, METABASE_PASS, METABASE_CARD_ID)
    if not data:
        print("[Main] No data retrieved from Metabase.", file=sys.stderr)
        sys.exit(1)

    try:
        upload_to_gsheet(data, creds_info, GSHEET_ID, GSHEET_SHEET_NAME)
    except Exception as e:
        print(f"[Main] Failed to upload to Google Sheets: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
