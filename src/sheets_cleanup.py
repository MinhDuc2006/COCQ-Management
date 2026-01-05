import os
from datetime import datetime
from dotenv import load_dotenv
from src import sheets
from src.utils import normalize_date

# Load environment variables
load_dotenv()

spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")


def cleanup_sheet():
    if not spreadsheet_id:
        print("Error: GOOGLE_SHEET_ID missing in .env")
        return

    print(f"Reading data from sheet: {spreadsheet_id}")
    service = sheets.get_sheets_service()
    
    # Get all values
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="A:Z"
    ).execute()
    
    values = result.get('values', [])
    if not values or len(values) < 2:
        print("No data found or sheet is empty.")
        return
        
    headers = [h.strip() for h in values[0]]
    if "Date" not in headers:
        print("Error: 'Date' column not found in headers.")
        return
        
    date_col_index = headers.index("Date")
    print(f"Date column found at index {date_col_index}")
    
    updated_count = 0
    # Process each row (skipping headers)
    for i, row in enumerate(values[1:], start=2):
        if len(row) > date_col_index:
            old_date = row[date_col_index]
            new_date = normalize_date(old_date)
            
            if old_date != new_date:
                print(f"Updating Row {i}: {old_date} -> {new_date}")
                
                # Update cell directly
                cell_range = f"{chr(65 + date_col_index)}{i}" # e.g. C2
                body = {'values': [[new_date]]}
                
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=cell_range,
                    valueInputOption="RAW",
                    body=body
                ).execute()
                updated_count += 1
                
    print(f"Done! Updated {updated_count} rows.")

if __name__ == "__main__":
    cleanup_sheet()
