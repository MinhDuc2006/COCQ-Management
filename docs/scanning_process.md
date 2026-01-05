# File Scanning and Processing Architecture

This document details the exact technical process the application uses to scan, retrieve, and process files from Google Drive.

## 1. Discovery Phase (Google Drive Scanner)
**Source**: src/drive_scanner.py

The process begins when the user clicks "Start Processing". The application queries the Google Drive API to identify potential files.

### 1.1. Query Construction
The scanner builds a composite query to filter files server-side (on Google's end) before they reach the application.

- **Name Filters**: The file name must contain one of the following substrings (case-insensitive):
  - 'CO'
  - 'CQ'
  - 'cocq'
- **MIME Type Filters**: The file must be one of the following types:
  - application/pdf
  - image/jpeg
  - image/png
- **Trash Status**: trashed = false (Active files only).
- **Location**: If a specific Folder ID is provided, the query restricts results to that folder.

### 1.2. Shared Drive Support
To ensure visibility into Organization/Team Drives, the API request includes:
- supportsAllDrives=True: Tells Google we can handle Shared, Team, and Enterprise Drives.
- includeItemsFromAllDrives=True: Tells Google to actually verify items in those drives.

## 2. Acquisition Phase (Download)
**Source**: src/app.py & src/drive_scanner.py

Once the list of files is retrieved, the application processes them sequentially.

### 2.1. Temporary Storage
For each file found:
1. A secure temporary file is created using Python's tempfile.NamedTemporaryFile.
2. **Naming**: The file is given a .pdf suffix for the temp file.
3. **Path**: The file is stored in the system's temp directory (e.g., /tmp/ on Linux/Mac).

### 2.2. Stream Download
The file content is downloaded using MediaIoBaseDownload. This streams the file chunks into the temporary file buffer to avoid loading large files entirely into RAM before writing.

## 3. Extraction Phase (Hybrid Text-First + OCR)
**Source**: src/extractor.py

After downloading, the local temporary path is passed to the extraction engine.

### 3.1. Hybrid Extraction Strategy (4-Phase Process)

#### Phase 1: Digital Text Extraction (Priority - Fast)
**Source**: src/extractor.py → extract_text_from_pdf()

- **Method**: Uses pdfplumber to extract text from digital PDFs
- **Scope**: Scans **entire document**, all pages
- **Speed**: Near-instant for modern PDFs
- **Process**:
  1. Opens PDF with pdfplumber.open(file_path)
  2. Iterates through each page: for page in pdf.pages
  3. Extracts text: page.extract_text()
  4. Concatenates all pages into single text corpus

#### Phase 2: Completeness Check
**Source**: src/extractor.py → extract_data()

The system evaluates extraction quality:
- **Scanned Detection**: Document has < 10 characters of extractable text
- **Image Detection**: Uses pdfplumber.page.images to detect image-heavy documents
- **Data Completeness**: Verifies both Date AND Serial Number were found
- **Trigger Decision**: Determines if OCR is needed

#### Phase 3: OCR Fallback (Automatic Trigger)
**Source**: src/extractor.py → extract_text_with_ocr()

**Trigger Conditions** (ANY of the following):
1. Document is scanned (no extractable text)
2. Critical data is missing (Date OR Serial Number)
3. Document contains high-resolution images
4. User forces OCR via "Force OCR for Scanned Files" checkbox

**OCR Process Details**:
- **Library**: pytesseract (Python wrapper for Tesseract OCR engine)
- **Image Conversion**: pdf2image.convert_from_path()
  - **Resolution**: 300 DPI (default)
  - **Scope**: **ALL pages** converted to images
  - **Format**: Each page becomes a PIL Image object
- **Text Recognition**: pytesseract.image_to_string(image)
  - **Language**: English (eng) + Orientation/Script Detection (osd)
  - **Per-Page Processing**: Each page is OCR'd individually
  - **Output**: Text from all pages combined with page markers
- **System Requirements**:
  - Tesseract binary: brew install tesseract
  - Poppler utilities: brew install poppler

#### Phase 4: Intelligent Merging
**Source**: src/extractor.py → extract_data()

- **Strategy**: Combines results from digital and OCR extraction
- **Priority Rules**:
  - For scanned documents: OCR results override digital results
  - For hybrid documents: Missing fields are filled by OCR
  - Serial numbers are deduplicated across both sources
- **Method Tracking**:
  - "Regex" - Pure digital extraction (fast)
  - "Regex + OCR" - Hybrid (digital partial, OCR completed)
  - "OCR (Tesseract)" - Pure OCR (scanned document)
  - "OCR (Tesseract) (Failed)" - OCR attempted but no data found

### 3.2. Enhanced Pattern Matching

#### Date Extraction
**Source**: src/extractor.py → extract_date() + src/utils.py → normalize_date()

**Patterns Recognized**:
- DD/MM/YYYY (e.g., 12/05/2023)
- YYYY-MM-DD (e.g., 2023-05-12)
- Month DD, YYYY (e.g., May 12, 2023)

**Normalization Process**:
1. Regex captures date in any format
2. datetime.strptime() parses the string
3. Reformats to standard DD/MM/YYYY
4. Handles single-digit padding automatically

#### Serial Number Extraction (Enhanced)
**Source**: src/extractor.py → extract_serial_number()

**Keywords Recognized**:
- **Standard**: "Ref No.", "Ref No", "Certificate No.", "Serial Number", "Serial No.", "S/N", "SN"
- **CoC-Specific**: "Ser.Nos.", "Ser.Nos", "Ser.No.", "Ser. Nos."

**Extraction Methods**:

1. **Same-Line Capture**:
   - Pattern: Keyword followed by alphanumeric value
   - Captures value immediately following keyword
   - Splits by delimiters (comma, semicolon, multi-space)
   - Validates each segment individually

2. **Vertical/Columnar Scan**:
   - Triggered when keyword found without same-line value
   - Scans **next 5 lines** after keyword
   - Captures standalone alphanumeric sequences
   - Handles table-style layouts (e.g., Google Docs exports)

3. **Range Detection**:
   - Captures patterns like H733T021491-H733T021650
   - Supports comma-separated ranges
   - Example: SERIAL1-SERIAL2, SERIAL3-SERIAL4

**Noise Filtering**:
- **Address Keywords**: Excludes "Lane", "Street", "Ward", "District", "Hanoi", "Vietnam"
- **Quantity Labels**: Excludes "pcs", "pes", "EA", "Quantity"
- **Simple Fractions**: Excludes patterns like "1/3", "2/3"
- **Minimum Length**: Requires at least 4 characters

**Context Enhancement**:
- **Component Detection**: Identifies "Tube", "Anode", "Inverter", "Generator", "Tank", "Detector"
- **Format**: SERIAL123 (Tube) when context noun is detected
- **Scan Range**: 30 characters preceding the keyword

### 3.3. Table Extraction Strategy
**Source**: src/extractor.py → extract_from_tables()

In addition to text scanning, the application iterates through all tables in the PDF to find structured data.

- **Logic**: Cleans each row (removing empty cells) and scans for keywords in each cell
- **Heuristic**: 
    1. **Horizontal Check**: If a cell contains a keyword, check the **immediate next cell** in the same row
    2. **Vertical Check**: If horizontal fails, check the **same column in the next row**
    3. **Column Scan**: Continue scanning **downwards** to capture all consecutive values
- **Priority**: Table data supplements text-based extraction

### 3.4. Data Aggregation
**Source**: src/extractor.py → extract_data()

- Merges data from Text Scan, Table Scan, and OCR
- **Deduplication**: Serial numbers are deduplicated using set logic
- **Formatting**: Multiple serial numbers joined by newlines
- **Method Tracking**: Records extraction method used for debugging

## 4. Storage Phase (Google Sheets)
**Source**: src/sheets.py

Once processing is complete, the admin clicks "Sync to Google Sheets" to persist the data.

### 4.1. File Identification
- **File Name**: The original name of the PDF on Google Drive
- **Drive Link**: The webViewLink from Google Drive API, providing a direct URI to view the document

### 4.2. Data Layout
The application maintains a 1-to-1 relationship between files and rows.

- **Multi-Serial Storage**: If multiple serial numbers are found in a single file, they are stored in a **single cell** separated by newline characters. This ensures that the record for one document is never split across multiple rows, while remaining searchable.

## 5. Retrieval Phase (User Search Portal)
**Source**: src/user_app.py & src/sheets.py

Users can locate documents through a simplified search interface.

### 5.1. Data Retrieval
- The User App fetches the current state of the Google Sheet using sheets.get_sheet_data
- It converts the raw Sheet values into a structured format for filtering

### 5.2. Smart Search Logic
- **Serial Number Search**: Performs a case-insensitive partial match against the "Serial Number" column
- **Improved Date Search**:
    1. The app pre-calculates a normalized version of all dates in the current dataset using utils.normalize_date
    2. The user's query is also normalized
    3. A match is found if either the raw query OR the normalized query matches the normalized data

### 5.3. Direct Access
- Once a record is located, the User App provides a clickable **Open PDF** markdown link using the saved Drive Link

## 6. Performance & Optimization

### 6.1. Speed Hierarchy
1. **Regex on Digital Text**: < 1 second per file
2. **Table Extraction**: 1-2 seconds per file
3. **OCR Processing**: 10-30 seconds per file (depends on page count)

### 6.2. Resource Requirements
- **Memory**: ~50-100MB per file during OCR processing
- **CPU**: OCR is CPU-intensive, benefits from multi-core processors
- **Disk**: Temporary files cleaned up automatically after processing
