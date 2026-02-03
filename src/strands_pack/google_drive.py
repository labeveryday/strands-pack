"""
Google Drive Tool

Interact with the Google Drive API (v3) to list/search files and manage file content.

Installation:
    pip install "strands-pack[drive]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
- list_files: List files using an optional Drive query
- get_file: Get file metadata
- download_file: Download file content to disk
- upload_file: Upload a local file to Drive
- create_folder: Create a Drive folder
- delete_file: Permanently delete a file
- delete_spreadsheet: Alias for delete_file (deletes the Drive file by id)

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import google_drive

    agent = Agent(tools=[google_drive])
    agent("List my recent files")
    agent("Search for PDFs in my Drive")
    agent("Download file with ID abc123")
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/drive",
]

try:
    from googleapiclient.discovery import build as _google_build
    from googleapiclient.http import MediaFileUpload as _MediaFileUpload
    from googleapiclient.http import MediaIoBaseDownload as _MediaIoBaseDownload

    HAS_GOOGLE_DRIVE = True
except ImportError:  # pragma: no cover
    _google_build = None
    _MediaFileUpload = None
    _MediaIoBaseDownload = None
    HAS_GOOGLE_DRIVE = False


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Google Drive service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("drive", "v3", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


DEFAULT_LIST_FIELDS = "nextPageToken, files(id,name,mimeType,modifiedTime,size,webViewLink,parents,trashed)"


@tool
def google_drive(
    action: str,
    # list_files params
    q: Optional[str] = None,
    page_size: int = 25,
    page_token: Optional[str] = None,
    fields: Optional[str] = None,
    # get_file, download_file, delete_file params
    file_id: Optional[str] = None,
    # download_file params
    output_path: Optional[str] = None,
    # export_file params
    export_mime_type: Optional[str] = None,
    # rename_file params
    new_name: Optional[str] = None,
    # copy_file/move_file params
    destination_folder_id: Optional[str] = None,
    # delete_file params
    confirm: bool = False,
    # upload_file params
    file_path: Optional[str] = None,
    # upload_file, create_folder params
    name: Optional[str] = None,
    parent_id: Optional[str] = None,
    # upload_file params
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Google Drive API tool for managing files and folders.

    Args:
        action: The operation to perform. One of:
            - "list_files": List files using an optional Drive query
            - "get_file": Get file metadata
            - "download_file": Download file content to disk
            - "upload_file": Upload a local file to Drive
            - "create_folder": Create a Drive folder
            - "rename_file": Rename a file
            - "copy_file": Copy/duplicate a file
            - "move_file": Move a file to a different folder
            - "trash_file": Move a file to trash (recoverable)
            - "restore_file": Restore a file from trash
            - "delete_file": Permanently delete a file (requires confirm=True)
            - "delete_spreadsheet": Alias for delete_file
            - "export_file": Export a Google-native file (Docs/Sheets/Slides) to another format and save to disk
            - "get_quota": Get Drive storage quota usage
        q: Drive query string for list_files (e.g., "name contains 'report' and trashed=false")
        page_size: Number of files to return per page (default 25, for list_files)
        page_token: Token for pagination (for list_files)
        fields: Override default fields to return
        file_id: ID of the file (required for get_file, download_file, delete_file)
        output_path: Path to save downloaded file (required for download_file)
        export_mime_type: MIME type to export to (required for export_file), e.g. "application/pdf"
        new_name: New file name (required for rename_file)
        destination_folder_id: Destination folder ID (required for move_file; optional for copy_file)
        confirm: Set True to perform destructive actions like delete_file (default False)
        file_path: Path to file to upload (required for upload_file)
        name: Name for uploaded file or folder (optional for upload_file, required for create_folder)
        parent_id: Parent folder ID (optional for upload_file, create_folder)
        mime_type: MIME type for uploaded file (optional for upload_file)

    Returns:
        dict with success status and relevant data

    Examples:
        # List files
        google_drive(action="list_files", page_size=10)

        # Search for PDFs
        google_drive(action="list_files", q="mimeType='application/pdf' and trashed=false")

        # Get file metadata
        google_drive(action="get_file", file_id="FILE_ID")

        # Download a file
        google_drive(action="download_file", file_id="FILE_ID", output_path="downloads/file.bin")

        # Export a Google Doc to PDF
        google_drive(action="export_file", file_id="FILE_ID", export_mime_type="application/pdf", output_path="downloads/doc.pdf")

        # Rename a file
        google_drive(action="rename_file", file_id="FILE_ID", new_name="Renamed.txt")

        # Copy a file
        google_drive(action="copy_file", file_id="FILE_ID", new_name="Copy of file", destination_folder_id="FOLDER_ID")

        # Move a file
        google_drive(action="move_file", file_id="FILE_ID", destination_folder_id="FOLDER_ID")

        # Trash / restore
        google_drive(action="trash_file", file_id="FILE_ID")
        google_drive(action="restore_file", file_id="FILE_ID")

        # Get quota
        google_drive(action="get_quota")

        # Upload a file
        google_drive(action="upload_file", file_path="report.pdf", parent_id="FOLDER_ID")

        # Create a folder
        google_drive(action="create_folder", name="My Folder")

        # Delete a file
        google_drive(action="delete_file", file_id="FILE_ID")
    """
    if not HAS_GOOGLE_DRIVE:
        return _err(
            "Missing Google Drive dependencies. Install with: pip install strands-pack[drive]"
        )

    valid_actions = [
        "list_files",
        "get_file",
        "download_file",
        "export_file",
        "upload_file",
        "create_folder",
        "rename_file",
        "copy_file",
        "move_file",
        "trash_file",
        "restore_file",
        "delete_file",
        "delete_spreadsheet",
        "get_quota",
    ]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", error_type="InvalidAction", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("drive")

    try:
        # list_files
        if action == "list_files":
            req: Dict[str, Any] = {
                "pageSize": int(page_size),
                "fields": fields or DEFAULT_LIST_FIELDS,
            }
            if q:
                req["q"] = q
            if page_token:
                req["pageToken"] = page_token

            resp = service.files().list(**req).execute()
            files = resp.get("files", []) or []
            return _ok(files=files, count=len(files), next_page_token=resp.get("nextPageToken"), query=req)

        # get_file
        if action == "get_file":
            if not file_id:
                return _err("file_id is required for get_file")
            req = {"fileId": file_id, "fields": fields or "*"}
            meta = service.files().get(**req).execute()
            return _ok(file=meta, file_id=file_id)

        # download_file
        if action == "download_file":
            if not file_id:
                return _err("file_id is required for download_file")
            if not output_path:
                return _err("output_path is required for download_file")

            out_path = Path(output_path).expanduser()
            out_path.parent.mkdir(parents=True, exist_ok=True)

            request = service.files().get_media(fileId=file_id)

            fh = io.FileIO(str(out_path), "wb")
            downloader = _MediaIoBaseDownload(fh, request)
            done = False
            chunks = 0
            while not done:
                _status, done = downloader.next_chunk()
                chunks += 1

            return _ok(file_id=file_id, output_path=str(out_path), chunks=chunks)

        # export_file (Google native -> chosen mime)
        if action == "export_file":
            if not file_id:
                return _err("file_id is required for export_file")
            if not export_mime_type:
                return _err("export_mime_type is required for export_file")
            if not output_path:
                return _err("output_path is required for export_file")

            out_path = Path(output_path).expanduser()
            out_path.parent.mkdir(parents=True, exist_ok=True)

            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            fh = io.FileIO(str(out_path), "wb")
            downloader = _MediaIoBaseDownload(fh, request)
            done = False
            chunks = 0
            while not done:
                _status, done = downloader.next_chunk()
                chunks += 1

            return _ok(file_id=file_id, export_mime_type=export_mime_type, output_path=str(out_path), chunks=chunks)

        # rename_file
        if action == "rename_file":
            if not file_id:
                return _err("file_id is required for rename_file")
            if not new_name:
                return _err("new_name is required for rename_file")
            updated = service.files().update(
                fileId=file_id,
                body={"name": str(new_name)},
                fields="id,name,mimeType,parents,webViewLink,trashed",
            ).execute()
            return _ok(file_id=file_id, file=updated)

        # copy_file
        if action == "copy_file":
            if not file_id:
                return _err("file_id is required for copy_file")
            body: Dict[str, Any] = {}
            if new_name:
                body["name"] = str(new_name)
            if destination_folder_id:
                body["parents"] = [destination_folder_id]
            created = service.files().copy(
                fileId=file_id,
                body=body,
                fields="id,name,mimeType,parents,webViewLink,trashed",
            ).execute()
            return _ok(source_file_id=file_id, file=created)

        # move_file
        if action == "move_file":
            if not file_id:
                return _err("file_id is required for move_file")
            if not destination_folder_id:
                return _err("destination_folder_id is required for move_file")
            meta = service.files().get(fileId=file_id, fields="parents").execute()
            parents = meta.get("parents", []) or []
            remove_parents = ",".join(parents) if parents else None
            kwargs: Dict[str, Any] = {
                "fileId": file_id,
                "addParents": destination_folder_id,
                "fields": "id,name,parents,webViewLink,trashed",
            }
            if remove_parents:
                kwargs["removeParents"] = remove_parents
            moved = service.files().update(**kwargs).execute()
            return _ok(file_id=file_id, file=moved, removed_parents=parents, added_parent=destination_folder_id)

        # trash_file / restore_file
        if action in ("trash_file", "restore_file"):
            if not file_id:
                return _err(f"file_id is required for {action}")
            trashed = action == "trash_file"
            updated = service.files().update(
                fileId=file_id,
                body={"trashed": trashed},
                fields="id,name,trashed,parents,webViewLink",
            ).execute()
            return _ok(file_id=file_id, file=updated, trashed=trashed, action=action)

        # get_quota
        if action == "get_quota":
            about = service.about().get(fields="storageQuota,user").execute()
            return _ok(about=about)

        # upload_file
        if action == "upload_file":
            if not file_path:
                return _err("file_path is required for upload_file")
            p = Path(file_path).expanduser()
            if not p.exists():
                return _err(f"file_path not found: {file_path}", error_type="FileNotFoundError")
            if not p.is_file():
                return _err(f"file_path is not a file: {file_path}")

            metadata: Dict[str, Any] = {"name": name or p.name}
            if parent_id:
                metadata["parents"] = [parent_id]

            media = _MediaFileUpload(str(p), mimetype=mime_type, resumable=True)
            created = service.files().create(body=metadata, media_body=media, fields="id,name,mimeType,parents,webViewLink").execute()
            return _ok(file=created, source_path=str(p))

        # create_folder
        if action == "create_folder":
            if not name:
                return _err("name is required for create_folder")
            metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
            if parent_id:
                metadata["parents"] = [parent_id]
            created = service.files().create(body=metadata, fields="id,name,mimeType,parents").execute()
            return _ok(folder=created)

        # delete_file / delete_spreadsheet
        if action in ("delete_file", "delete_spreadsheet"):
            if not file_id:
                return _err(f"file_id is required for {action}")
            if action == "delete_file" and not confirm:
                return _err(
                    "Refusing to permanently delete without confirm=True",
                    action=action,
                    file_id=file_id,
                    hint="Use trash_file for a safer delete, or pass confirm=True to delete_file to permanently delete.",
                )
            service.files().delete(fileId=file_id).execute()
            return _ok(file_id=file_id, deleted=True, action=action)

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    return _err(f"Unhandled action: {action}")
