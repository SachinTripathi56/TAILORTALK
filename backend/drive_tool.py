import os
import json
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from langchain.tools import tool

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

MIME_TYPE_MAP = {
    "pdf": "application/pdf",
    "doc": "application/vnd.google-apps.document",
    "docs": "application/vnd.google-apps.document",
    "google doc": "application/vnd.google-apps.document",
    "sheet": "application/vnd.google-apps.spreadsheet",
    "sheets": "application/vnd.google-apps.spreadsheet",
    "google sheet": "application/vnd.google-apps.spreadsheet",
    "spreadsheet": "application/vnd.google-apps.spreadsheet",
    "slide": "application/vnd.google-apps.presentation",
    "slides": "application/vnd.google-apps.presentation",
    "presentation": "application/vnd.google-apps.presentation",
    "image": "image/",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "txt": "text/plain",
    "text": "text/plain",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "folder": "application/vnd.google-apps.folder",
    "video": "video/",
    "audio": "audio/",
}

def get_drive_service():
    """Build and return an authenticated Google Drive service."""
    service_account_info = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_account_info:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set.")
    
    info = json.loads(service_account_info)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials)


def search_drive_files(
    query_string: str,
    folder_id: Optional[str] = None,
    max_results: int = 10
) -> list:
    """
    Execute a Google Drive files.list query.
    Returns a list of file dicts with id, name, mimeType, webViewLink, modifiedTime.
    """
    service = get_drive_service()
    
    
    if folder_id:
        folder_clause = f"'{folder_id}' in parents"
        if query_string:
            query_string = f"({query_string}) and {folder_clause}"
        else:
            query_string = folder_clause
    
    
    query_string += " and trashed = false"
    
    results = service.files().list(
        q=query_string,
        pageSize=max_results,
        fields="files(id, name, mimeType, webViewLink, modifiedTime, size, parents)",
        orderBy="modifiedTime desc"
    ).execute()
    
    return results.get("files", [])


@tool
def drive_search_tool(query: str) -> str:
    """
    Search Google Drive using a native Drive API query string.
    
    The query must be a valid Drive API 'q' parameter string. Examples:
    - name contains 'report'
    - name = 'Budget 2024'
    - mimeType = 'application/pdf'
    - fullText contains 'quarterly revenue'
    - modifiedTime > '2024-01-01T00:00:00'
    - name contains 'invoice' and mimeType = 'application/pdf'
    
    Always returns a JSON string with found files or an empty list.
    """
    folder_id = os.environ.get("DRIVE_FOLDER_ID")
    
    try:
        files = search_drive_files(query, folder_id=folder_id, max_results=15)
        if not files:
            return json.dumps({"files": [], "message": "No files found matching your query."})
        
        simplified = []
        for f in files:
            simplified.append({
                "name": f.get("name"),
                "type": _friendly_mime(f.get("mimeType", "")),
                "mimeType": f.get("mimeType"),
                "link": f.get("webViewLink", ""),
                "modified": f.get("modifiedTime", "")[:10] if f.get("modifiedTime") else "",
                "id": f.get("id"),
            })
        
        return json.dumps({"files": simplified, "count": len(simplified)})
    except Exception as e:
        return json.dumps({"error": str(e), "files": []})


def _friendly_mime(mime: str) -> str:
    """Convert MIME type to human-readable label."""
    mapping = {
        "application/pdf": "PDF",
        "application/vnd.google-apps.document": "Google Doc",
        "application/vnd.google-apps.spreadsheet": "Google Sheet",
        "application/vnd.google-apps.presentation": "Google Slides",
        "application/vnd.google-apps.folder": "Folder",
        "image/jpeg": "Image (JPEG)",
        "image/png": "Image (PNG)",
        "image/gif": "Image (GIF)",
        "text/plain": "Text File",
        "text/csv": "CSV",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel Sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
    }
    return mapping.get(mime, mime.split("/")[-1].replace("vnd.", "").replace(".", " ").title())
