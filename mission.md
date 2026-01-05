Mission: CO/CQ Automator Web App
1. Project Overview
Goal: Build a web application that automates the extraction of metadata from Certificate of Origin (CO) and Certificate of Quality (CQ) documents stored in Google Drive and aggregates the data into a Google Sheet.

Core Workflow:

Scan: Authenticate with Google Drive and search for files matching specific naming conventions ("CO", "CQ", "cocq").

Extract: Open identified files (PDF/Images) and extract specific entities (Names, Dates, Serial Numbers).

Report: Append the extracted data along with the file's Google Drive link into a master Google Sheet.

2. Technical Stack & Requirements
Backend / Core Logic
Language: Python 3.9+

Framework: Streamlit (recommended for rapid UI creation) or Flask/FastAPI.

Google APIs:

google-auth / google-auth-oauthlib: For OAuth2 authentication.

google-api-python-client: To interact with Drive API (v3) and Sheets API (v4).

Data Extraction (OCR/Parsing):

pdfplumber or PyPDF2: For text-based PDFs.

pytesseract (Tesseract OCR): For scanned image-based PDFs/Images.

Optional: OpenAI API / LangChain (if regex is insufficient for unstructured document parsing).

Frontend
Interface: A simple dashboard to:

Authenticate via Google.

Select the source Drive Folder.

Select/Create the destination Google Sheet.

Trigger the "Sync" process and view a progress bar.

3. Implementation Plan (The Mission)
Phase 1: Authentication & Setup
[ ] Setup GCP Project: Create a credentials.json setup script or instructions for OAuth 2.0 Client IDs. Scopes required: drive.readonly, spreadsheets.

[ ] Auth Manager: Create a Python module (auth.py) to handle the login flow and store the user token locally or in session state.

Phase 2: Google Drive Scanner
[ ] Search Query Logic: Implement a function to list files in a specific folder.

Filter Condition: Name contains CO, CQ, cocq (case insensitive).

MIME Types: Include application/pdf, image/jpeg, image/png.

[ ] File Retrieval: Return a list of file objects containing ID, Name, and WebViewLink.

Phase 3: Intelligent Extraction Engine (Hybrid Text-First + OCR)
[✓] Text Extractor: Implemented in extractor.py with hybrid orchestration.

**Scanning Strategy (Text-First with OCR Override):**

1. **Digital Pass (Fast - Priority 1):**
   - Uses `pdfplumber` to extract text from digital PDFs
   - Scans entire document for text content
   - Extracts data from tables using `pdfplumber.extract_tables()`
   - **Speed:** Near-instant for modern PDFs

2. **Completeness Check:**
   - Verifies if both Date AND Serial Number were found
   - Checks if document is scanned (text length < 10 characters)
   - Detects image-heavy documents using `pdfplumber.page.images`

3. **OCR Pass (Fallback - Triggered Automatically):**
   - **Trigger Conditions:**
     - Document is detected as scanned (no extractable text)
     - OR critical data is missing (Date or Serial Number)
     - OR document contains high-resolution images
     - OR user forces OCR via UI checkbox
   
   - **OCR Process:**
     - Uses `pdf2image` to convert ALL pages to images (300 DPI)
     - Applies `pytesseract.image_to_string()` to each page
     - **Scan Range:** Full document, all pages
     - **Language:** English (eng) + Numbers (osd)
     - Combines OCR text from all pages into single corpus
   
   - **Post-OCR Processing:**
     - Re-runs regex extraction on OCR text
     - Merges results with digital extraction
     - Prioritizes OCR results for scanned documents

4. **Method Reporting:**
   - "Regex" - Pure digital extraction (fast)
   - "Regex + OCR" - Hybrid (digital found partial, OCR completed)
   - "OCR (Tesseract)" - Pure OCR (scanned document)
   - "OCR (Tesseract) (Failed)" - OCR attempted but no data found

[✓] Pattern Matching (Enhanced Regex):

**Date Extraction:**
- Patterns: DD/MM/YYYY, YYYY-MM-DD, Month DD, YYYY
- Normalizes all dates to DD/MM/YYYY format

**Serial Number Extraction:**
- **Keywords Recognized:** 
  - Standard: "Ref No.", "Certificate No.", "Serial Number", "Serial No.", "S/N", "SN"
  - CoC-specific: "Ser.Nos.", "Ser.No.", "Ser. Nos."
  
- **Extraction Methods:**
  - Same-line capture: Keyword followed by alphanumeric value
  - Vertical/Columnar scan: Scans next 5 lines after keyword for values
  - Range detection: Captures patterns like "SERIAL1-SERIAL2"
  
- **Noise Filtering:**
  - Excludes address keywords: "Lane", "Street", "Ward", "Hanoi", "Vietnam"
  - Excludes quantity labels: "pcs", "pes", "EA"
  - Excludes simple fractions: "1/3", "2/3"
  
- **Context Enhancement:**
  - Identifies component types: "Tube", "Anode", "Inverter", "Generator", "Tank", "Detector"
  - Formats as: "SERIAL123 (Tube)" when context is detected

[✓] Data Structuring: Returns dictionary with method tracking:
```python
{
    "date": str,           # Normalized date (DD/MM/YYYY)
    "serial_number": str,  # Newline-separated if multiple
    "method": str          # Extraction method used
}
```

Phase 4: Google Sheets Integration
[ ] Sheet Manager: Create sheets.py.

[ ] Header Check: Ensure the target sheet has headers: [File Name, Extracted Name, Date, Serial Number, Drive Link].

[ ] Batch Write: Append the processed data as a new row. Avoid duplicates based on the 'Drive Link' or 'File ID'.

Phase 5: UI Construction (Streamlit)
[ ] Sidebar: Configuration (Folder ID input, Spreadsheet ID input).

[ ] Main Area: "Start Processing" button.

[ ] Feedback: Display a dataframe preview of extracted data before committing to Google Sheets.

4. Extraction Logic Specifics
The extractor must handle "similar terms" for file filtering.

Strict Match: *CO*, *CQ*, *cocq*

Fuzzy logic: Check if filename parts match Certificate, Origin, Quality.

The parsing logic for Serial Numbers should prioritize:

Look for keywords: "Ref No", "Certificate No", "Serial", "S/N".

Capture the immediate alphanumeric string following the keyword.

5. Definition of Done
User can log in via Google.

App successfully finds a PDF named "Supplier_CO_2024.pdf".

App parses the date "2024-01-01" and Serial "A123" from inside that PDF.

App writes a row to the specified Google Sheet with the link to the file.

Code is modular and includes a requirements.txt.