import pytest
from unittest.mock import MagicMock, patch
from src.drive_scanner import search_files

@patch('src.drive_scanner.get_drive_service')
def test_search_files(mock_get_service):
    # Mock the Drive API service and its chain of calls
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    
    mock_files = {
        'files': [
            {'id': '1', 'name': 'CO_doc.pdf', 'webViewLink': 'http://link1', 'mimeType': 'application/pdf'},
            {'id': '2', 'name': 'CQ_report.jpg', 'webViewLink': 'http://link2', 'mimeType': 'image/jpeg'}
        ],
        'nextPageToken': None
    }
    
    mock_service.files().list().execute.return_value = mock_files
    
    results = search_files()
    
    assert len(results) == 2
    assert results[0]['name'] == 'CO_doc.pdf'
    assert results[1]['name'] == 'CQ_report.jpg'
    
    # Verify the query was constructed with expected parts
    args, kwargs = mock_service.files().list.call_args
    query = kwargs.get('q', '')
    assert "name contains 'CO'" in query
    assert "name contains 'CQ'" in query
    assert "application/pdf" in query
    assert "trashed = false" in query

@patch('src.drive_scanner.get_drive_service')
def test_search_files_with_folder(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.files().list().execute.return_value = {'files': [], 'nextPageToken': None}
    
    folder_id = "test_folder_123"
    search_files(folder_id=folder_id)
    
    args, kwargs = mock_service.files().list.call_args
    query = kwargs.get('q', '')
    assert f"'{folder_id}' in parents" in query
