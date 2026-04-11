#!/usr/bin/env python3
"""
sheets_ops.py — Google Sheets CRUD operations.

CLI tool for reading, writing, appending, and deleting data in Google Sheets.

Usage:
    python3 sheets_ops.py read [--range RANGE] [--json]
    python3 sheets_ops.py write --range RANGE --values V1 V2 ... | --json JSON
    python3 sheets_ops.py append [--range RANGE] --values V1 V2 ... | --json JSON
    python3 sheets_ops.py delete-rows --start N --end N [--sheet NAME]
    python3 sheets_ops.py delete-cols --start N --end N [--sheet NAME]
    python3 sheets_ops.py info

All commands accept --spreadsheet-id ID or use GOOGLE_SHEET_ID env var.
Default spreadsheet: 1ohdygd0jj9dT4tqfyo7-bI3HdXonk0SBxjISVOlQA-s
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure we can import sheets_auth from the same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_auth import get_sheets_service

DEFAULT_SPREADSHEET_ID = "1ohdygd0jj9dT4tqfyo7-bI3HdXonk0SBxjISVOlQA-s"


def get_spreadsheet_id(args):
    """Resolve spreadsheet ID from args, env, or default."""
    if hasattr(args, "spreadsheet_id") and args.spreadsheet_id:
        return args.spreadsheet_id
    return os.environ.get("GOOGLE_SHEET_ID", DEFAULT_SPREADSHEET_ID)


def get_sheet_id_by_name(service, spreadsheet_id, sheet_name):
    """Look up numeric sheet ID from sheet name."""
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == sheet_name:
            return props.get("sheetId")
    raise ValueError(f"Sheet '{sheet_name}' not found. "
                     f"Available: {[s['properties']['title'] for s in meta['sheets']]}")


def cmd_read(args):
    """Read data from the spreadsheet."""
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id(args)
    range_str = args.range or "A:ZZ"

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_str,
    ).execute()

    rows = result.get("values", [])

    if not rows:
        print("(empty — no data in range)")
        return

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        # TSV output
        for row in rows:
            print("\t".join(str(cell) for cell in row))


def cmd_write(args):
    """Write data to specific cells (overwrite)."""
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id(args)

    if not args.range:
        print("ERROR: --range is required for write", file=sys.stderr)
        sys.exit(1)

    if args.json:
        values = json.loads(args.json)
        if not isinstance(values[0], list):
            values = [values]
    elif args.values:
        values = [args.values]
    else:
        print("ERROR: provide --values or --json", file=sys.stderr)
        sys.exit(1)

    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=args.range,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    updated = result.get("updatedCells", 0)
    print(f"Updated {updated} cell(s) in {result.get('updatedRange', args.range)}")


def cmd_append(args):
    """Append rows after existing data."""
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id(args)
    range_str = args.range or "A:ZZ"

    if args.json:
        values = json.loads(args.json)
        if not isinstance(values[0], list):
            values = [values]
    elif args.values:
        values = [args.values]
    else:
        print("ERROR: provide --values or --json", file=sys.stderr)
        sys.exit(1)

    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_str,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()

    updates = result.get("updates", {})
    print(f"Appended {updates.get('updatedRows', 0)} row(s) at {updates.get('updatedRange', '?')}")


def cmd_delete_rows(args):
    """Delete rows by 1-indexed row numbers."""
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id(args)

    if args.sheet:
        sheet_id = get_sheet_id_by_name(service, spreadsheet_id, args.sheet)
    else:
        sheet_id = 0  # first sheet

    # Convert 1-indexed to 0-indexed
    start_idx = args.start - 1
    end_idx = args.end  # exclusive in API, so 1-indexed end == 0-indexed exclusive

    request = {
        "deleteDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": start_idx,
                "endIndex": end_idx,
            }
        }
    }

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [request]},
    ).execute()

    count = end_idx - start_idx
    print(f"Deleted {count} row(s) ({args.start}-{args.end})")


def cmd_delete_cols(args):
    """Delete columns by 1-indexed column numbers."""
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id(args)

    if args.sheet:
        sheet_id = get_sheet_id_by_name(service, spreadsheet_id, args.sheet)
    else:
        sheet_id = 0

    start_idx = args.start - 1
    end_idx = args.end

    request = {
        "deleteDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": start_idx,
                "endIndex": end_idx,
            }
        }
    }

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [request]},
    ).execute()

    count = end_idx - start_idx
    print(f"Deleted {count} column(s) ({args.start}-{args.end})")


def cmd_info(args):
    """Show spreadsheet metadata (sheets/tabs, row counts)."""
    service = get_sheets_service()
    spreadsheet_id = get_spreadsheet_id(args)

    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    print(f"Title: {meta.get('properties', {}).get('title', '?')}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    print()

    sheets = meta.get("sheets", [])
    print(f"Sheets ({len(sheets)}):")
    for sheet in sheets:
        props = sheet.get("properties", {})
        grid = props.get("gridProperties", {})
        title = props.get("title", "?")
        sid = props.get("sheetId", "?")
        rows = grid.get("rowCount", "?")
        cols = grid.get("columnCount", "?")
        print(f"  {title}  (id={sid}, {rows} rows x {cols} cols)")


def main():
    parser = argparse.ArgumentParser(description="Google Sheets operations")
    parser.add_argument("--spreadsheet-id", help="Override spreadsheet ID")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # read
    p_read = subparsers.add_parser("read", help="Read data from the sheet")
    p_read.add_argument("--range", help="Range in A1 notation (e.g., Sheet1!A1:D10)")
    p_read.add_argument("--json", action="store_true", help="Output as JSON")

    # write
    p_write = subparsers.add_parser("write", help="Write data to specific cells")
    p_write.add_argument("--range", help="Target range (e.g., A1:C1)", required=True)
    p_write.add_argument("--values", nargs="+", help="Values to write")
    p_write.add_argument("--json", help="JSON array of arrays")

    # append
    p_append = subparsers.add_parser("append", help="Append rows after existing data")
    p_append.add_argument("--range", help="Target range (default: A:ZZ)")
    p_append.add_argument("--values", nargs="+", help="Values for one row")
    p_append.add_argument("--json", help="JSON array of arrays for multiple rows")

    # delete-rows
    p_delr = subparsers.add_parser("delete-rows", help="Delete rows")
    p_delr.add_argument("--start", type=int, required=True, help="Start row (1-indexed)")
    p_delr.add_argument("--end", type=int, required=True, help="End row (1-indexed, inclusive)")
    p_delr.add_argument("--sheet", help="Sheet name (default: first sheet)")

    # delete-cols
    p_delc = subparsers.add_parser("delete-cols", help="Delete columns")
    p_delc.add_argument("--start", type=int, required=True, help="Start column (1-indexed)")
    p_delc.add_argument("--end", type=int, required=True, help="End column (1-indexed, inclusive)")
    p_delc.add_argument("--sheet", help="Sheet name (default: first sheet)")

    # info
    subparsers.add_parser("info", help="Show spreadsheet metadata")

    args = parser.parse_args()

    commands = {
        "read": cmd_read,
        "write": cmd_write,
        "append": cmd_append,
        "delete-rows": cmd_delete_rows,
        "delete-cols": cmd_delete_cols,
        "info": cmd_info,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
