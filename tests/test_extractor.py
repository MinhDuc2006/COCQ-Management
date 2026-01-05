import pytest
from unittest.mock import MagicMock, patch
from src.extractor import extract_date, extract_serial_number, extract_from_tables, extract_data

def test_extract_date():
    assert extract_date("Issued on 12/05/2023") == "12/05/2023"
    assert extract_date("Date: 2023-10-30") == "30/10/2023"
    assert extract_date("Created on January 15, 2024") == "15/01/2024"
    # New single digit date test
    assert extract_date("Short date: 1/1/2026") == "01/01/2026"
    assert extract_date("Mixed digits: 1/12/2026") == "01/12/2026"
    assert extract_date("No date here") is None

def test_extract_serial_number_new_keywords():
    # Generic labels now return ONLY the value (clean)
    assert extract_serial_number("Ref No: ABC-123") == ["ABC-123"]
    assert extract_serial_number("Certificate No. XYZ987") == ["XYZ987"]
    assert extract_serial_number("Serial: 123456789") == ["123456789"]
    assert extract_serial_number("S/N: SN-001") == ["SN-001"]
    assert extract_serial_number("No: 555-666") == ["555-666"]
    
    # New keywords (generic)
    assert extract_serial_number("Seri: 9999") == ["9999"]
    assert extract_serial_number("SN-6666") == ["6666"]
    
    # Context-aware labels (Requested by User)
    assert extract_serial_number("Serial No. X252K000949") == ["X252K000949"]
    assert extract_serial_number("Tube Head Serial No.: 8194") == ["8194 (Tube)"]
    assert extract_serial_number("Anode Serial No.: 3H88551") == ["3H88551 (Anode)"]
    
    # Compound keywords tests 
    assert extract_serial_number("Serial Number 2194907-PO") == ["2194907-PO"]
    
    # Multiple occurrences
    assert extract_serial_number("Tube Serial: 1234\nAnode Serial: 4567") == ["1234 (Tube)", "4567 (Anode)"]
    
    # Regression: Ensure NO newline jumping
    assert extract_serial_number("Seri Number\nMac") == [] 
    assert extract_serial_number("S/N:\n123") == []
    
    # User's new specific example
    assert extract_serial_number("Serial No.: 9876H12AJF") == ["9876H12AJF"]
    
    assert extract_serial_number("Random text") == []



def test_extract_from_tables():
    # Mock pdfplumber to return a specific table structure
    with patch("src.extractor.pdfplumber.open") as mock_open:
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf.pages = [mock_page]
        
        # Test Column Scannning
        # Row 1: "Serial No"
        # Row 2: "SN-1"
        # Row 3: "SN-2"
        # Row 4: "SN-3"
        # Row 5: Empty (stop)
        
        mock_table = [
            ["Item", "Description"],
            ["Serial No", ""], # Key "Serial No" matches. Next cell empty -> Trigger vertical scan.
            ["SN-1", ""],      # Value collected
            ["SN-2", ""],      # Value collected
            ["SN-3", ""],      # Value collected
            ["", ""]           # Stop
        ]
        
        mock_page.extract_tables.return_value = [mock_table]
        
        result = extract_from_tables("dummy_path.pdf")
        
        # Expect list of all 3 (generic serial header in mock)
        assert result["serial_number"] == ["SN-1", "SN-2", "SN-3"]

def test_extract_data_priority():
    # Test that table data overrides text data AND format is correct
    with patch("src.extractor.extract_text_from_pdf") as mock_text:
        with patch("src.extractor.extract_from_tables") as mock_tables:
            # Mock Text finding ["Wrong1", "Wrong2"]
            mock_text.return_value = "Serial Number: Wrong1\nSerial Number: Wrong2" 
            # (In reality extract_serial_number parses this text)
            
            # Mock Table finding ["Right1", "Right2"]
            mock_tables.return_value = {
                "serial_number": ["Right1 (Tube)", "Right2 (Tube)"],
                "date": "2025-01-01"
            }
            
            from src.extractor import extract_data
            result = extract_data("dummy.pdf")
            
            # Logic: Table overrides text. Result should be joined string of table values.
            assert result["serial_number"] == "Right1 (Tube)\nRight2 (Tube)"
            assert result["date"] == "01/01/2025"

@patch("src.extractor.extract_with_gemini")
@patch("src.extractor.extract_from_tables")
@patch("src.extractor.extract_text_from_pdf")
def test_extract_data_ai_fallback(mock_text, mock_tables, mock_ai):
    # Case: Text and Table extraction both return EMPTY data
    mock_text.return_value = "Random noisy text"
    mock_tables.return_value = {}
    
    # AI returns the actual data
    mock_ai.return_value = {
        "date": "25/12/2025",
        "serial_number": ["AI-SN-100 (Anode)"]
    }
    
    result = extract_data("missing_data.pdf")
    
    # Assertions
    assert result["date"] == "25/12/2025"
    assert result["serial_number"] == "AI-SN-100 (Anode)"
    mock_ai.assert_called_once()

def test_extract_from_tables_empty():
    with patch("src.extractor.pdfplumber.open") as mock_open:
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf.pages = [mock_page]
        mock_page.extract_tables.return_value = []
        
        result = extract_from_tables("dummy_path.pdf")
        assert result == {}
