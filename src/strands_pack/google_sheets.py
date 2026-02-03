"""
Google Sheets Tool

Interact with the Google Sheets API (v4) to read/write spreadsheet values.

Installation:
    pip install "strands-pack[sheets]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
- create_spreadsheet: Create a new spreadsheet (optional title)
- get_spreadsheet: Get spreadsheet metadata (including sheet/tab IDs)
- add_sheet: Add a new sheet/tab to an existing spreadsheet (requires spreadsheet_id; optional sheet_name)
- delete_sheet: Delete a sheet/tab inside a spreadsheet (requires spreadsheet_id and sheet_id or sheet_name)
- get_values: Read a range (requires spreadsheet_id, range)
- update_values: Overwrite a range with values (requires spreadsheet_id, range, values)
- append_values: Append rows to a range/table (requires spreadsheet_id, range, values)
- clear_values: Clear a range (requires spreadsheet_id, range)

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import google_sheets

    agent = Agent(tools=[google_sheets])
    agent("Read data from my spreadsheet")
    agent("Append a row to Sheet1")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/spreadsheets",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_GOOGLE_SHEETS = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_GOOGLE_SHEETS = False


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Google Sheets service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


@tool
def google_sheets(
    action: str,
    title: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
    sheet_id: Optional[int] = None,
    sheet_name: Optional[str] = None,
    range: Optional[str] = None,
    values: Optional[List[List[Any]]] = None,
    value_render_option: Optional[str] = None,
    value_input_option: str = "USER_ENTERED",
    insert_data_option: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Google Sheets API tool for managing spreadsheet data.

    Args:
        action: The operation to perform. One of:
            - "create_spreadsheet": Create a new spreadsheet
            - "get_spreadsheet": Get spreadsheet metadata (including sheet/tab IDs)
            - "add_sheet": Add a new sheet/tab inside a spreadsheet
            - "delete_sheet": Delete a sheet/tab inside a spreadsheet
            - "get_values": Read a range of values
            - "update_values": Overwrite a range with new values
            - "append_values": Append rows to a range/table
            - "clear_values": Clear a range
        title: Spreadsheet title (optional, for create_spreadsheet)
        spreadsheet_id: ID of the spreadsheet (required for all actions)
        sheet_id: Sheet/tab ID (int) inside the spreadsheet (for delete_sheet). You can get this from get_spreadsheet.
        sheet_name: Sheet/tab title inside the spreadsheet (for add_sheet; or alternative to sheet_id for delete_sheet)
        range: A1 notation range like "Sheet1!A1:C10" (required for all actions)
        values: List of rows to write, e.g. [["a", "b"], ["c", "d"]] (required for update_values, append_values)
        value_render_option: How to render values (optional, for get_values). Options: FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA
        value_input_option: How to interpret input (default "USER_ENTERED", for update_values/append_values). Options: RAW, USER_ENTERED
        insert_data_option: How to insert data (optional, for append_values). Options: OVERWRITE, INSERT_ROWS

    Returns:
        dict with success status and relevant data

    Examples:
        # Create a spreadsheet
        google_sheets(action="create_spreadsheet", title="My Sample Sheet")

        # Get spreadsheet metadata (including sheet IDs)
        google_sheets(action="get_spreadsheet", spreadsheet_id="SHEET_ID")

        # Add a new tab
        google_sheets(action="add_sheet", spreadsheet_id="SHEET_ID", sheet_name="Summary")

        # Delete a tab by name
        google_sheets(action="delete_sheet", spreadsheet_id="SHEET_ID", sheet_name="Sheet2")

        # Delete a tab by sheetId
        google_sheets(action="delete_sheet", spreadsheet_id="SHEET_ID", sheet_id=123456)

        # Read values
        google_sheets(action="get_values", spreadsheet_id="SHEET_ID", range="Sheet1!A1:C10")

        # Update values
        google_sheets(action="update_values", spreadsheet_id="SHEET_ID", range="Sheet1!A1", values=[["Hello", "World"]])

        # Append rows
        google_sheets(action="append_values", spreadsheet_id="SHEET_ID", range="Sheet1!A:C", values=[["new", "row", "data"]])

        # Clear values
        google_sheets(action="clear_values", spreadsheet_id="SHEET_ID", range="Sheet1!A1:C10")
    """
    if not HAS_GOOGLE_SHEETS:
        return _err(
            "Missing Google Sheets dependencies. Install with: pip install strands-pack[sheets]"
        )

    valid_actions = ["create_spreadsheet", "get_spreadsheet", "add_sheet", "delete_sheet", "get_values", "update_values", "append_values", "clear_values"]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("sheets")

    try:
        # create_spreadsheet
        if action == "create_spreadsheet":
            body: Dict[str, Any] = {}
            if title:
                body = {"properties": {"title": str(title)}}
            resp = service.spreadsheets().create(body=body).execute()
            return _ok(spreadsheet=resp, spreadsheet_id=resp.get("spreadsheetId"), spreadsheet_url=resp.get("spreadsheetUrl"))

        # get_spreadsheet
        if action == "get_spreadsheet":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for get_spreadsheet")
            resp = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields="spreadsheetId,properties.title,spreadsheetUrl,sheets(properties(sheetId,title,index))",
            ).execute()
            sheets = resp.get("sheets", []) or []
            sheet_summaries = [
                {
                    "sheet_id": s.get("properties", {}).get("sheetId"),
                    "title": s.get("properties", {}).get("title"),
                    "index": s.get("properties", {}).get("index"),
                }
                for s in sheets
            ]
            return _ok(spreadsheet_id=spreadsheet_id, spreadsheet=resp, sheets=sheet_summaries, count=len(sheet_summaries))

        # add_sheet (tab)
        if action == "add_sheet":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for add_sheet")
            props: Dict[str, Any] = {}
            if sheet_name:
                props["title"] = str(sheet_name)
            body = {"requests": [{"addSheet": {"properties": props}}]}
            resp = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            # Try to surface created sheetId if present
            created_sheet_id = None
            try:
                replies = resp.get("replies", []) or []
                if replies and "addSheet" in replies[0]:
                    created_sheet_id = replies[0]["addSheet"].get("properties", {}).get("sheetId")
            except Exception:
                created_sheet_id = None
            return _ok(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                created_sheet_id=created_sheet_id,
                updated=resp,
            )

        # delete_sheet (tab)
        if action == "delete_sheet":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for delete_sheet")

            resolved_sheet_id = sheet_id
            if resolved_sheet_id is None and sheet_name:
                meta = service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id,
                    fields="sheets(properties(sheetId,title))",
                ).execute()
                for s in meta.get("sheets", []) or []:
                    props = s.get("properties", {}) or {}
                    if props.get("title") == sheet_name:
                        resolved_sheet_id = props.get("sheetId")
                        break

            if resolved_sheet_id is None:
                return _err("sheet_id or sheet_name is required for delete_sheet")

            body = {"requests": [{"deleteSheet": {"sheetId": int(resolved_sheet_id)}}]}
            resp = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            return _ok(spreadsheet_id=spreadsheet_id, deleted_sheet_id=int(resolved_sheet_id), deleted_sheet_name=sheet_name, updated=resp)

        # get_values
        if action == "get_values":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for get_values")
            if not range:
                return _err("range is required for get_values")
            req: Dict[str, Any] = {"spreadsheetId": spreadsheet_id, "range": range}
            if value_render_option:
                req["valueRenderOption"] = value_render_option
            resp = service.spreadsheets().values().get(**req).execute()
            return _ok(spreadsheet_id=spreadsheet_id, range=range, values=resp.get("values", []), raw=resp)

        # update_values
        if action == "update_values":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for update_values")
            if not range:
                return _err("range is required for update_values")
            if values is None:
                return _err("values is required for update_values (list[list])")
            body = {"values": values}
            resp = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range,
                valueInputOption=value_input_option,
                body=body,
            ).execute()
            return _ok(spreadsheet_id=spreadsheet_id, range=range, updated=resp)

        # append_values
        if action == "append_values":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for append_values")
            if not range:
                return _err("range is required for append_values")
            if values is None:
                return _err("values is required for append_values (list[list])")
            req = {
                "spreadsheetId": spreadsheet_id,
                "range": range,
                "valueInputOption": value_input_option,
                "body": {"values": values},
            }
            if insert_data_option:
                req["insertDataOption"] = insert_data_option
            resp = service.spreadsheets().values().append(**req).execute()
            return _ok(spreadsheet_id=spreadsheet_id, range=range, appended=resp)

        # clear_values
        if action == "clear_values":
            if not spreadsheet_id:
                return _err("spreadsheet_id is required for clear_values")
            if not range:
                return _err("range is required for clear_values")
            resp = service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=range, body={}
            ).execute()
            return _ok(spreadsheet_id=spreadsheet_id, range=range, cleared=resp)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
