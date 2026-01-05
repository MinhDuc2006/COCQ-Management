from googleapiclient.discovery import build
from src.auth import authenticate_google_drive

def get_sheets_service():
    """Returns an authorized Sheets API service instance."""
    creds = authenticate_google_drive()
    return build('sheets', 'v4', credentials=creds)

def ensure_headers(service, spreadsheet_id):
    """
    Checks if the first row has the correct headers. 
    If not (or empty), writes them.
    """
    headers = ["File Name", "Date", "Serial Number", "Drive Link"]
    
    # Read first row
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="A1:E1"
    ).execute()
    
    values = result.get('values', [])
    
    if not values:
        # Sheet is empty or no headers, write them
        body = {
            'values': [headers]
        }
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range="A1",
            valueInputOption="RAW", body=body
        ).execute()
        return True
    
    # Optional: Validate headers match, but for now assuming if data exists headers are likely there
    return True

def append_data_to_sheet(spreadsheet_id, data_rows):
    """
    Appends a list of rows to the sheet.
    data_rows: List of lists, where each inner list corresponds to a row.
    """
    service = get_sheets_service()
    
    # Ensure headers exist
    ensure_headers(service, spreadsheet_id)
    
    body = {
        'values': data_rows
    }
    
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range="A1",
        valueInputOption="USER_ENTERED", body=body
    ).execute()
    
    return result.get('updates', {}).get('updatedCells')

def get_sheet_data(spreadsheet_id):
    """
    Reads data from the spreadsheet and returns a list of dictionaries.
    Assumes headers are: File Name, Date, Serial Number, Drive Link
    """
    service = get_sheets_service()
    
    # Read wider range to ensure we don't miss columns if the schema changed
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="A:Z"
    ).execute()
    
    values = result.get('values', [])
    if not values or len(values) < 2:
        return []
        
    headers = [h.strip() for h in values[0]]
    data = []
    
    for row in values[1:]:
        # Pad row if some cells are empty at the end
        row_padded = row + [""] * (len(headers) - len(row))
        item = {}
        for i, header in enumerate(headers):
            if header: # Only add if header is not empty
                item[header] = row_padded[i]
        data.append(item)
        
    return data

if __name__ == '__main__':
    # Test stub
    pass

def clear_sheet_data(spreadsheet_id):
    """
    Clears all data from the sheet except the header row.
    """
    service = get_sheets_service()
    
    # First, get the current range to know how many rows exist
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="A:Z"
    ).execute()
    
    values = result.get('values', [])
    if len(values) <= 1:
        # Only headers or empty, nothing to clear
        return 0
    
    # Clear from row 2 onwards
    num_rows = len(values)
    clear_range = f"A2:Z{num_rows}"
    
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=clear_range
    ).execute()
    
    return num_rows - 1  # Return number of data rows cleared

def get_existing_drive_links(spreadsheet_id):
    """
    Returns a set of Drive Links that are already present in the sheet.
    This is used to prevent re-scanning/re-adding the same file.
    """
    data = get_sheet_data(spreadsheet_id)
    # Return a set of links. Filter out empty ones.
    return {item.get("Drive Link") for item in data if item.get("Drive Link")}
