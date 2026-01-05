# CO/CQ Management System

The **CO/CQ Management System** is a robust automation tool designed to streamline the extraction, storage, and retrieval of metadata from **Certificate of Origin (CO)** and **Certificate of Quality (CQ)** documents stored in Google Drive.

By leveraging advanced PDF extraction techniques (Regex, Table Parsing, and OCR) and integrating directly with Google Sheets, this system eliminates manual data entry and provides a unified search interface for teams.

## 🚀 Key Features

*   **Automated Scanning**: Automatically discovers PDF files in a designated Google Drive folder.
*   **Intelligent Extraction**:
    *   **Digital PDFs**: Instant text extraction using `pdfplumber` and Regex.
    *   **Scanned PDFs**: Automatic fallback to **Tesseract OCR** for image-based documents.
    *   **Table Parsing**: Extracts data from structured tables within documents.
    *   **Smart Merging**: Combines data from multiple methods to ensure completeness.
*   **Advanced Parsing Logic**:
    *   **Dates**: Handles various formats (`12/05/2023`, `2023.05.12`, `July 12 2021`) and context-based detection (`Date: ...`).
    *   **Serial Numbers**: Captures single values, lists (`1234, 5678`), ranges (`1234 ~ 5678`), and column-based data. Includes robust noise filtering.
*   **Dual Interfaces**:
    *   **Admin Automator**: For processing files and syncing data to Google Sheets.
    *   **Client Search Portal**: For teams to quickly find documents by Serial Number or Date.
*   **Google Integration**: Direct links to open PDFs in Google Drive.

## 🛠️ Architecture

For a deep dive into the technical implementation of the scanning, extraction, and processing pipeline, please refer to the [Scanning Process Details](docs/scanning_process.md).

### Core Components
*   **`src/drive_scanner.py`**: Handles Google Drive API authentication, file discovery, and downloading.
*   **`src/extractor.py`**: The extraction engine containing Regex logic, Table parsing, and OCR orchestration.
*   **`src/utils.py`**: Utility functions for date normalization and cleanup.
*   **`src/sheets.py`**: Interface for reading/writing to Google Sheets.
*   **`src/app.py`**: The Admin Streamlit application.
*   **`src/user_app.py`**: The Client Search Streamlit application.

## 📦 Installation

### Prerequisites
*   Python 3.9+
*   **Tesseract OCR**: Required for scanned documents.
    *   macOS: `brew install tesseract`
    *   Linux: `sudo apt-get install tesseract-ocr`
*   **Poppler**: Required for PDF-to-Image conversion.
    *   macOS: `brew install poppler`
    *   Linux: `sudo apt-get install poppler-utils`

### Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/MinhDuc2006/COCQ-Management.git
    cd COCQ-Management
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    Create a `.env` file in the root directory with your Google Cloud credentials:
    ```env
    GOOGLE_SHEET_ID=your_spreadsheet_id
    GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
    GOOGLE_APPLICATION_CREDENTIALS=credentials.json
    ```
    *Note: Ensure `credentials.json` (Service Account Key) and `token.json` (OAuth Token) are present in the root if using that auth method.*

## 🖥️ Usage

### Admin Automator
Used to scan Google Drive, extract data, and sync it to the master Google Sheet.

```bash
streamlit run src/app.py
```
*   **Start Processing**: Downloads and extracts data from files.
*   **Force OCR**: Check this box to re-process files using OCR even if they have text.
*   **Clear Google Sheet**: Wipes the sheet (keeping headers) for a fresh sync.
*   **Sync to Google Sheets**: Appends extracted data to the sheet.

### Client Search Portal
Used by the team to find documents.

```bash
streamlit run src/user_app.py --server.port 8502
```
*   Users can search by **Serial Number** (partial match support).
*   Users can search by **Date**.
*   Results include a direct link to open the PDF in Google Drive.

## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

## 📄 License
[MIT License](LICENSE)
