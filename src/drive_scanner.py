from googleapiclient.discovery import build
from src.auth import authenticate_google_drive

def get_drive_service():
    """Returns an authorized Drive API service instance."""
    creds = authenticate_google_drive()
    return build('drive', 'v3', credentials=creds)

def search_files(folder_id=None):
    """
    Search for files matching specific naming conventions (CO, CQ, cocq)
    and mime types (PDF, Images).
    """
    service = get_drive_service()

    # Mime types to look for
    mime_types = [
        "application/pdf", 
        "image/jpeg", 
        "image/png"
    ]
    
    # Construct query
    # Name contains 'CO', 'CQ' or 'cocq' (case insensitive not directly supported by 'name contains', 
    # but we can filter later or use multiple contains)
    # Drive API 'contains' is case-insensitive.
    
    name_queries = [
        "name contains 'CO'",
        "name contains 'CQ'",
        "name contains 'cocq'"
    ]
    name_query = f"({' or '.join(name_queries)})"
    
    mime_query_parts = [f"mimeType = '{m}'" for m in mime_types]
    mime_query = f"({' or '.join(mime_query_parts)})"
    
    query = f"{name_query} and {mime_query} and trashed = false"
    
    if folder_id:
        query += f" and '{folder_id}' in parents"

    results = []
    page_token = None
    
    while True:
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, webViewLink, mimeType)',
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = response.get('files', [])
        results.extend(files)
        
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
            
    return results

def list_files_in_folder(folder_id):
    """List all files in a specific folder without name filtering."""
    service = get_drive_service()
    
    query = f"'{folder_id}' in parents and trashed = false"
    
    results = []
    page_token = None
    
    while True:
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, webViewLink, mimeType)',
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = response.get('files', [])
        results.extend(files)
        
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
            
    return results

def download_file(file_id, destination_path):
    """Downloads a file from Google Drive to the specified path."""
    from googleapiclient.http import MediaIoBaseDownload
    import io

    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    # Write to file
    with open(destination_path, 'wb') as f:
        f.write(fh.getvalue())
    
    return destination_path

if __name__ == '__main__':
    try:
        print("Searching for files...")
        # Note: This will fail if credentials.json is not present and auth flow cannot start
        files = search_files()
        print(f"Found {len(files)} files.")
        for file in files[:5]:
            print(f"Found file: {file['name']} ({file['id']})")
    except Exception as e:
        print(f"Error: {e}")
