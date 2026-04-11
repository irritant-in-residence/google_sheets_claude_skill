#!/usr/bin/env python3
"""
sheets_mcp.py — Google Sheets MCP server.

Exposes Google Sheets CRUD operations as MCP tools over stdio.
Keeps the auth token and API service object warm in memory.
"""

import json
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Ensure we can import sheets_auth from the same directory
SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR))
from sheets_auth import get_sheets_service, get_drive_service

# Lazy-init services (warm after first call)
_sheets_service = None
_drive_service = None


def _get_service():
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = get_sheets_service()
    return _sheets_service


def _get_drive():
    global _drive_service
    if _drive_service is None:
        _drive_service = get_drive_service()
    return _drive_service


def _resolve_spreadsheet_id(spreadsheet_id: str | None = None) -> str:
    if spreadsheet_id:
        return spreadsheet_id
    env_id = os.environ.get("GOOGLE_SHEET_ID")
    if env_id:
        return env_id
    raise ValueError("No spreadsheet_id provided. Pass spreadsheet_id or set GOOGLE_SHEET_ID env var.")


def _get_sheet_id_by_name(service, spreadsheet_id: str, sheet_name: str) -> int:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == sheet_name:
            return props.get("sheetId")
    available = [s["properties"]["title"] for s in meta["sheets"]]
    raise ValueError(f"Sheet '{sheet_name}' not found. Available: {available}")


mcp = FastMCP("google-sheets")


@mcp.tool()
def read(range: str = "A:ZZ", spreadsheet_id: str | None = None, output_json: bool = False) -> str:
    """Read data from a Google Sheet. Range uses A1 notation (e.g., 'Sheet1!A1:D10')."""
    service = _get_service()
    sid = _resolve_spreadsheet_id(spreadsheet_id)

    result = service.spreadsheets().values().get(
        spreadsheetId=sid, range=range
    ).execute()
    rows = result.get("values", [])

    if not rows:
        return "(empty — no data in range)"

    if output_json:
        return json.dumps(rows, indent=2)

    return "\n".join("\t".join(str(cell) for cell in row) for row in rows)


@mcp.tool()
def write(range: str, values: list[list[str]], spreadsheet_id: str | None = None) -> str:
    """Write data to specific cells (overwrite). Values is an array of arrays (rows)."""
    service = _get_service()
    sid = _resolve_spreadsheet_id(spreadsheet_id)

    result = service.spreadsheets().values().update(
        spreadsheetId=sid,
        range=range,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    updated = result.get("updatedCells", 0)
    return f"Updated {updated} cell(s) in {result.get('updatedRange', range)}"


@mcp.tool()
def append(values: list[list[str]], range: str = "A:ZZ", spreadsheet_id: str | None = None) -> str:
    """Append rows after existing data. Values is an array of arrays (rows)."""
    service = _get_service()
    sid = _resolve_spreadsheet_id(spreadsheet_id)

    result = service.spreadsheets().values().append(
        spreadsheetId=sid,
        range=range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()

    updates = result.get("updates", {})
    return f"Appended {updates.get('updatedRows', 0)} row(s) at {updates.get('updatedRange', '?')}"


@mcp.tool()
def delete_rows(start: int, end: int, sheet_name: str | None = None, spreadsheet_id: str | None = None) -> str:
    """Delete rows by 1-indexed row numbers (inclusive). Optionally specify sheet by name."""
    service = _get_service()
    sid = _resolve_spreadsheet_id(spreadsheet_id)

    if sheet_name:
        sheet_id = _get_sheet_id_by_name(service, sid, sheet_name)
    else:
        sheet_id = 0

    # Convert 1-indexed to 0-indexed
    start_idx = start - 1
    end_idx = end  # exclusive in API

    service.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_idx,
                    "endIndex": end_idx,
                }
            }
        }]},
    ).execute()

    return f"Deleted {end_idx - start_idx} row(s) ({start}-{end})"


@mcp.tool()
def delete_cols(start: int, end: int, sheet_name: str | None = None, spreadsheet_id: str | None = None) -> str:
    """Delete columns by 1-indexed column numbers (inclusive). Optionally specify sheet by name."""
    service = _get_service()
    sid = _resolve_spreadsheet_id(spreadsheet_id)

    if sheet_name:
        sheet_id = _get_sheet_id_by_name(service, sid, sheet_name)
    else:
        sheet_id = 0

    start_idx = start - 1
    end_idx = end

    service.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_idx,
                    "endIndex": end_idx,
                }
            }
        }]},
    ).execute()

    return f"Deleted {end_idx - start_idx} column(s) ({start}-{end})"


@mcp.tool()
def info(spreadsheet_id: str | None = None) -> str:
    """Show spreadsheet metadata: title, URL, and all sheets with their dimensions."""
    service = _get_service()
    sid = _resolve_spreadsheet_id(spreadsheet_id)

    meta = service.spreadsheets().get(spreadsheetId=sid).execute()

    lines = [
        f"Title: {meta.get('properties', {}).get('title', '?')}",
        f"URL: https://docs.google.com/spreadsheets/d/{sid}/edit",
        "",
    ]

    sheets = meta.get("sheets", [])
    lines.append(f"Sheets ({len(sheets)}):")
    for sheet in sheets:
        props = sheet.get("properties", {})
        grid = props.get("gridProperties", {})
        title = props.get("title", "?")
        s_id = props.get("sheetId", "?")
        rows = grid.get("rowCount", "?")
        cols = grid.get("columnCount", "?")
        lines.append(f"  {title}  (id={s_id}, {rows} rows x {cols} cols)")

    return "\n".join(lines)


@mcp.tool()
def list_spreadsheets(query: str | None = None, max_results: int = 20) -> str:
    """List Google Sheets accessible to this account. Optionally filter by name with a search query."""
    drive = _get_drive()

    q = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    if query:
        q += f" and name contains '{query}'"

    result = drive.files().list(
        q=q,
        pageSize=max_results,
        fields="files(id, name, modifiedTime, owners)",
        orderBy="modifiedTime desc",
    ).execute()

    files = result.get("files", [])
    if not files:
        return "(no spreadsheets found)"

    lines = []
    for f in files:
        owners = ", ".join(o.get("displayName", "?") for o in f.get("owners", []))
        lines.append(f"{f['name']}")
        lines.append(f"  id: {f['id']}")
        lines.append(f"  modified: {f.get('modifiedTime', '?')}  owner: {owners}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
