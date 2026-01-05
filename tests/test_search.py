import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

def test_search_filtering_logic():
    # Mock data as returned by sheets.get_sheet_data
    mock_data = [
        {"File Name": "CO_123.pdf", "Date": "12/05/2023", "Serial Number": "SN-001\nSN-002", "Drive Link": "link1"},
        {"File Name": "CQ_456.pdf", "Date": "01/01/2024", "Serial Number": "SN-999", "Drive Link": "link2"},
        {"File Name": "CO_789.pdf", "Date": "12/05/2023", "Serial Number": "SN-003", "Drive Link": "link3"},
    ]
    
    df = pd.DataFrame(mock_data)
    
    # 1. Search by serial number (partial match, multi-line)
    query_sn = "SN-002"
    filtered_sn = df[df["Serial Number"].str.contains(query_sn, case=False, na=False)]
    assert len(filtered_sn) == 1
    assert filtered_sn.iloc[0]["File Name"] == "CO_123.pdf"
    
    # 2. Search by date
    query_date = "12/05/2023"
    filtered_date = df[df["Date"].str.contains(query_date, case=False, na=False)]
    assert len(filtered_date) == 2
    
    # 3. Combined search logic check
    filtered_both = df[
        (df["Serial Number"].str.contains("SN-001", case=False, na=False)) & 
        (df["Date"].str.contains("12/05/2023", case=False, na=False))
    ]
    assert len(filtered_both) == 1

    # 4. Normalized date search (User types 1/1/2026, matches 01/01/2026)
    from src.utils import normalize_date
    mock_data_normalization = [
        {"File Name": "CO_001.pdf", "Date": "01/01/2026", "Serial Number": "SN-001", "Drive Link": "link1"},
    ]
    df_norm = pd.DataFrame(mock_data_normalization)
    
    query_date_raw = "1/1/2026"
    normalized_query = normalize_date(query_date_raw)
    
    assert normalized_query == "01/01/2026"
    filtered_norm = df_norm[
        (df_norm["Date"].str.contains(query_date_raw, case=False, na=False)) |
        (df_norm["Date"].str.contains(normalized_query, case=False, na=False))
    ]
    assert len(filtered_norm) == 1

@patch("src.sheets.get_sheets_service")
def test_get_sheet_data(mock_get_service):
    # Mock Sheets API response
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    
    mock_values = {
        'values': [
            ["File Name", "Date", "Serial Number", "Drive Link"],
            ["file1.pdf", "2023-01-01", "123", "link1"],
            ["file2.pdf", "2023-01-02", "456"] # Padded check
        ]
    }
    
    mock_service.spreadsheets().values().get().execute.return_value = mock_values
    
    from src.sheets import get_sheet_data
    result = get_sheet_data("dummy_id")
    
    assert len(result) == 2
    assert result[0]["File Name"] == "file1.pdf"
    assert result[1]["Drive Link"] == "" # Padded check
