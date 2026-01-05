import pdfplumber
import pytesseract
import pandas as pd
import re
import logging
from pdf2image import convert_from_path
from src.utils import normalize_date

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def has_images(file_path):
    """Checks if a PDF contains images on the first page."""
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages: return False
            first_page = pdf.pages[0]
            return bool(first_page.images)
    except Exception:
        return False

def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file using pdfplumber."""
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
    except Exception as e:
        logging.error(f"Error extracting PDF text: {e}")
        return None

def extract_text_with_ocr(file_path):
    """
    Converts PDF to images and uses Tesseract OCR to extract text.
    Requires 'poppler' (for pdf2image) and 'tesseract' installed.
    """
    logging.info(f"Running Tesseract OCR on {file_path}...")
    try:
        # Convert PDF pages to images
        images = convert_from_path(file_path)
        full_text = ""
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            full_text += f"\n--- Page {i+1} ---\n{text}"
        return full_text
    except Exception as e:
        logging.error(f"Tesseract OCR failed: {e}. Ensure 'tesseract' and 'poppler' are installed on your system.")
        return None

def extract_date(text):
    """Extracts and normalizes dates from text."""
    if not text: return None
    patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{4}\b', 
        r'\b\d{4}-\d{2}-\d{2}\b', 
        # Support dots and spaces: 12.05.2023, 2023.05.12, 12 05 2023
        r'\b\d{1,2}[. ]\d{1,2}[. ]\d{4}\b',
        r'\b\d{4}[. ]\d{1,2}[. ]\d{1,2}\b',
        # Month formats - strictly relax spacing around comma
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},?\s*\d{4}\b',
        r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b'
    ]
    
    # 1. Try stand-alone date patterns
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(0)
            # Fix missing space after comma (July 12,2021 -> July 12, 2021)
            date_str = re.sub(r',(\d)', r', \1', date_str)
            return normalize_date(date_str)
            
    # 2. Try context-based extraction (Date: ...)
    # Captures "Date: 12 Oct 2023" or "Date: 12/10/2023" even if slightly malformed
    context_pattern = r'(?:Date|Dated|Issue Date)[:\.\s]*([A-Za-z0-9\/\.\-, ]{8,20})'
    match = re.search(context_pattern, text, re.IGNORECASE)
    if match:
        potential_date = match.group(1).strip()
        # Clean up potential trail characters
        potential_date = re.sub(r'[^\w\/\.\-, ]', '', potential_date)
        # Try to normalize this string
        normalized = normalize_date(potential_date)
        # Verify it looks like a date (roughly)
        if re.search(r'\d', normalized): 
            return normalized

    return None

def extract_serial_number(text):
    """Extracts serial numbers based on keywords, handling multi-line/columnar data."""
    if not text: return []
    
    # Stricter keywords to avoid noise like No. 28A (addresses)
    keywords = [
        "Ref No.", "Ref No", "Certificate No.", "Certificate No", 
        "Serial Number", "Seri Number", "Serial No.", "Serial N0", "Serial No", "Serial", 
        "Ser.Nos.", "Ser.Nos", "Ser.No.", "Ser.No", "Ser. Nos.", "Ser. Nos", "Ser Nos",
        "S/N", "S.N", "SN", "No:", "No."
    ]
    keywords.sort(key=len, reverse=True)
    
    # 1. Direct same-line match
    keyword_pat = r'\b(?P<label>' + '|'.join(map(re.escape, keywords)) + r')(?![A-Za-z0-9])'
    # Updated pattern: allow comma, tilde, slash, underscore, dot and spaces around them
    sameline_pattern = keyword_pat + r'[:\.\t \-]*([A-Za-z0-9]+(?:\s*[-~/._,]\s*[A-Za-z0-9]+)*)'
    
    results = []
    seen = set()
    context_nouns = ["Tube", "Anode", "Inverter", "Generator", "Tank", "Detector"]
    noise_keywords = [
        # Address terms
        "Lane", "Street", "Ward", "District", "Hanoi", "Vietnam",
        # Quantity/measurement terms
        "pcs", "pes", "Quantity", "Invoice", "EA",
        # Common company/manufacturer names
        "MORITA", "Morita", "MFG", "CORP", "Corporation", "Company", "Ltd", "Limited",
        "Inc", "Incorporated", "Japan", "JAPAN", "USA", "China",
        # Common document terms
        "Model", "Production", "Year", "Kyoto", "Osaka", "Tokyo",
        # Common extracted noise words
        "and", "the", "with", "made", "in", "dated", "kind", "type", "ref", "certificate", "city", "date"
    ]

    def is_noise(val):
        # Exclude common noise
        if any(nk.lower() in val.lower() for nk in noise_keywords):
            return True
        # Exclude simple fractions like 1/3
        if re.match(r'^\d+/\d+ - \d+/\d+$', val) or re.match(r'^\d+/\d+$', val):
            return True
        # Exclude short reference codes like ANH25, CO25, CQ25 (likely document IDs)
        if re.match(r'^[A-Z]{2,4}\d{1,3}$', val):
            return True
        # Exclude all-caps single words (likely company names/logos)
        if re.match(r'^[A-Z]{3,}$', val):
            return True
        # Exclude phone numbers and fax patterns
        if re.match(r'^\+?\d{1,3}[\s\-\.]?\(?\d{1,4}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}$', val):
            return True
        # Exclude website patterns
        if 'www.' in val.lower() or '.com' in val.lower() or '.co.jp' in val.lower():
            return True
        return False

    # First pass: Same line matches
    for match in re.finditer(sameline_pattern, text, re.IGNORECASE):
        raw_val = match.group(2).strip()
        if raw_val.lower() == "number": continue
        
        # Remove website suffixes that might be attached (e.g., "SERIAL123 www")
        raw_val = re.sub(r'\s+www\b.*$', '', raw_val, flags=re.IGNORECASE)
        raw_val = re.sub(r'\s+http.*$', '', raw_val, flags=re.IGNORECASE)
        
        # Split by typical delimiters (comma, semicolon, newline, or multi-space)
        parts = re.split(r'[,;\n]|\s{2,}', raw_val)
        
        for val in parts:
            val = val.strip()
            if not val or len(val) < 4:
                continue
            
            # Additional cleanup: remove trailing punctuations and www
            val = re.sub(r'[.\s]+$', '', val)
            val = re.sub(r'\s+www$', '', val, flags=re.IGNORECASE)
            
            # Check if it's noise AFTER cleanup
            if is_noise(val):
                continue
            
            # Check context
            start_pos = match.start()
            preceding_text = text[max(0, start_pos-30):start_pos]
            line_start = preceding_text.rfind('\n')
            if line_start != -1: preceding_text = preceding_text[line_start+1:]
            
            found_noun = None
            for noun in context_nouns:
                if re.search(r'\b' + re.escape(noun) + r'\b', preceding_text, re.IGNORECASE):
                    found_noun = noun
                    break
            
            formatted_val = f"{val} ({found_noun})" if found_noun else val
            if formatted_val not in seen:
                results.append(formatted_val)
                seen.add(formatted_val)

    # Second pass: Vertical/Columnar scan
    label_only_pat = r'\b(' + '|'.join(map(re.escape, keywords)) + r')\b'
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if re.search(label_only_pat, line, re.IGNORECASE):
            start_scan = i + 1
            end_scan = min(len(lines), i + 10)  # Increased to capture more serial numbers
            for j in range(start_scan, end_scan):
                # Pattern: Alphanumeric, length 5+, often with delimiters. 
                # Note: Do not include comma here to allow comma-separated values to be distinct if on one line
                # But allow spaces around separators
                sn_pattern = r'\b([A-Z0-9]{5,}(?:\s*[-~/._]\s*[A-Za-z0-9]+)*)\b'
                line_matches = re.finditer(sn_pattern, lines[j])
                for sn_match in line_matches:
                    val = sn_match.group(1).strip()
                    # Remove www suffix if attached
                    val = re.sub(r'\s+www$', '', val, flags=re.IGNORECASE)
                    if val not in seen and not is_noise(val):
                        results.append(val)
                        seen.add(val)

    return results

def extract_from_tables(file_path):
    """Extracts key-value pairs from tables in the PDF."""
    extracted_data = {}
    target_keywords = {
        "date": ["Date", "Issue Date", "Dated"],
        "serial_number": ["Serial Number", "Serial No.", "Seri Number", "Seri"] # Added Seri
    }
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for i, row in enumerate(table):
                        # Clean row data
                        row_text = [str(cell).strip() if cell else "" for cell in row]
                        
                        for col_idx, cell_text in enumerate(row_text):
                            cell_lower = cell_text.lower()
                            
                            # Check for Serial Number Header
                            if any(k.lower() in cell_lower for k in target_keywords["serial_number"]):
                                # Found SN header. Scan this column downwards.
                                found_sns = []
                                # Scan up to 15 rows down
                                for r_idx in range(i + 1, min(len(table), i + 15)):
                                    if len(table[r_idx]) > col_idx:
                                        val = str(table[r_idx][col_idx]).strip()
                                        val_lower = val.lower()
                                        if val and len(val) > 4:
                                            # Skip obvious non-serial headers/noise in the column
                                            noise_col_vals = ['product type', 'type', 'product', 'power', 'mac', 'window']
                                            if any(n in val_lower for n in noise_col_vals):
                                                continue
                                            found_sns.append(val)
                                
                                if found_sns:
                                    if "serial_number" not in extracted_data:
                                        extracted_data["serial_number"] = []
                                    extracted_data["serial_number"].extend(found_sns)

                            # Check for Date Header
                            if any(k.lower() in cell_lower for k in target_keywords["date"]):
                                # Horizontal finding first
                                if col_idx + 1 < len(row_text):
                                    val = row_text[col_idx + 1]
                                    if val: extracted_data["date"] = val
                                # If empty, check next row same col
                                if not extracted_data.get("date") and i + 1 < len(table):
                                    val = str(table[i+1][col_idx]).strip()
                                    if val: extracted_data["date"] = val

    except Exception as e:
        logging.error(f"Table extraction failed: {e}")
        
    return extracted_data

def extract_data(file_path, force_ocr=False):
    """Orchestrates the extraction process: Digital -> Table -> OCR."""
    method = "Regex"
    
    # 1. Digital Analysis
    text = extract_text_from_pdf(file_path)
    is_scanned = not text or len(text.strip()) < 10
    has_img = has_images(file_path)
    
    # Digital Extraction
    data = {
        "date": extract_date(text),
        "serial_number": extract_serial_number(text),
    }
    
    # Table Supplement
    table_data = extract_from_tables(file_path)
    if table_data.get("date") and not data["date"]:
        data["date"] = extract_date(table_data["date"])
    if table_data.get("serial_number"):
        # Smart merge: avoid adding partial matches
        for sn in table_data["serial_number"]:
            # Check if this SN is already in the list or is a substring of an existing one
            is_duplicate = False
            for i, existing_sn in enumerate(data["serial_number"]):
                # If new SN is substring of existing, or vice versa
                if sn in existing_sn or existing_sn in sn:
                    is_duplicate = True
                    # If existing is shorter (partial), replace it with the longer one
                    if len(sn) > len(existing_sn):
                        data["serial_number"][i] = sn
                    break
            if not is_duplicate:
                data["serial_number"].append(sn)

    # Check for meaningful extracted data
    is_digital_complete = bool(data["date"] and data["serial_number"])
    
    # 2. OCR Orchestration
    # Trigger OCR if forced, if scanned, or if digital pass was incomplete/image-heavy
    should_ocr = force_ocr or is_scanned or (not is_digital_complete and has_img) or not is_digital_complete
    
    if should_ocr:
        logging.info(f"Triggering OCR fallback for {file_path}. Reason: Scanned={is_scanned}, Image-Heavy={has_img}, Incomplete={not is_digital_complete}")
        ocr_text = extract_text_with_ocr(file_path)
        
        if ocr_text:
            # If we already had some digital data, it's a Hybrid process
            if data["date"] or data["serial_number"]:
                method = "Regex + OCR"
            else:
                method = "OCR (Tesseract)"
            
            # Supplement/Override
            ocr_date = extract_date(ocr_text)
            if ocr_date and (not data["date"] or is_scanned):
                data["date"] = ocr_date
            
            ocr_sns = extract_serial_number(ocr_text)
            for sn in ocr_sns:
                if sn not in data["serial_number"]:
                    data["serial_number"].append(sn)
        else:
            if is_scanned or force_ocr:
                method = "OCR (Tesseract) (Failed)"

    # 3. Final Formatting
    if isinstance(data.get("serial_number"), list):
        if data["serial_number"]:
            data["serial_number"] = "\n".join(list(dict.fromkeys(data["serial_number"])))
        else:
            data["serial_number"] = None
            
    return data, method
