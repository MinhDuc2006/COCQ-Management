from googleapiclient.discovery import build
from src.auth import authenticate_google_drive

_service_cache = None

def get_drive_service():
    """Returns an authorized Drive API service instance."""
    global _service_cache
    if _service_cache:
        return _service_cache
    creds = authenticate_google_drive()
    _service_cache = build('drive', 'v3', credentials=creds)
    return _service_cache

def _build_base_query(folder_id=None):
    """Builds the file search query string."""
    # Mime types to look for
    mime_types = [
        "application/pdf", 
        "image/jpeg", 
        "image/png"
    ]
    
    # Name contains 'CO', 'CQ' or 'cocq'
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
        
    return query

def _list_files_matching_criteria(folder_id):
    """Lists files in a specific folder matching the app's criteria."""
    service = get_drive_service()
    query = _build_base_query(folder_id)
    
    results = []
    page_token = None
    
    while True:
        try:
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
        except Exception as e:
            print(f"Error listing files in {folder_id}: {e}")
            break
    return results

def get_folder_name(folder_id):
    """Gets the name of a folder by ID."""
    try:
        service = get_drive_service()
        file = service.files().get(fileId=folder_id, fields='name').execute()
        return file.get('name', 'Unknown Folder')
    except:
        return 'Unknown Folder'

def walk_folder_structure(folder_id, recursive=False):
    """
    Generator that yields (folder_name, files_list) for the given folder
    and its subfolders (if recursive).
    """
    # 1. Yield current folder's files
    current_files = _list_files_matching_criteria(folder_id)
    folder_name = get_folder_name(folder_id)
    
    yield folder_name, current_files
    
    # 2. Recurse if needed
    if recursive:
        subfolders = get_subfolders(folder_id)
        for sub in subfolders:
            yield from walk_folder_structure(sub['id'], recursive=True)

def search_files(folder_id=None, recursive=False):
    """
    Legacy wrapper: Collects all results from walk_folder_structure into a single list.
    """
    all_files = []
    # If no folder_id is provided, we can't really "walk" efficiently from root without ID.
    # But filtering by parent needs an ID usually, unless we search whole drive.
    # For backward compat, if folder_id is None, we search whole drive flat (not using parent query).
    
    if folder_id is None:
        return _list_files_matching_criteria(None)
        
    for _, files in walk_folder_structure(folder_id, recursive):
        all_files.extend(files)
        
    return all_files

def get_subfolders(folder_id):
    """List all subfolders in a specific folder."""
    service = get_drive_service()
    
    query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    
    results = []
    page_token = None
    
    while True:
        try:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = response.get('files', [])
            results.extend(files)
            
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        except Exception as e:
            print(f"Error getting subfolders: {e}")
            break
            
    return results

def list_files_in_folder(folder_id):
    """List all files in a specific folder without name filtering."""
    service = get_drive_service()
    
    query = f"'{folder_id}' in parents and trashed = false"
    
    results = []
    page_token = None
    
    while True:
        try:
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
        except Exception as e:
            print(f"Error listing files: {e}")
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
        # dumb test
        pass
    except Exception as e:
        print(f"Error: {e}")
