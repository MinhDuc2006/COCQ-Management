from datetime import datetime
import re

def normalize_date(d_str):
    """
    Standardizes date strings to DD/MM/YYYY.
    Handles various formats including DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, and D/M/YYYY.
    """
    if not d_str or not isinstance(d_str, str):
        return d_str
    
    # Clean string
    d_str = d_str.strip()
    
    # Potential formats to try
    formats = [
        '%d/%m/%Y', # Preferred
        '%m/%d/%Y', 
        '%Y-%m-%d', 
        '%d-%m-%Y',
        '%B %d, %Y', # January 01, 2026
        '%b %d, %Y', # Jan 01, 2026
        '%d/%m/%y',  # 01/01/26
        '%Y/%m/%d',  # 2026/01/01 (common after dot normalization)
        '%d-%b-%Y',  # 01-Jan-2026
        '%B %d %Y',  # January 01 2026 (no comma)
        '%b %d %Y',  # Jan 01 2026 (no comma)
        '%d %B %Y',  # 01 January 2026
        '%d %b %Y',  # 01 Jan 2026
        '%d-%B-%Y',  # 01-January-2026
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(d_str, fmt).strftime('%d/%m/%Y')
        except ValueError:
            continue
            
    # Try one more: loose separator check if everything above fails
    # e.g. "1.1.2026" or "01 01 2026"
    cleaned = re.sub(r'[.\s\-]', '/', d_str)
    if cleaned != d_str:
        return normalize_date(cleaned) # Recursively try cleaned version
        
    return d_str

def expand_serial_ranges(serial_list):
    """
    Expands serial numbers containing ranges (marked by '~' or '-').
    
    Rules:
    1. '~' is always treated as a range separator.
    2. '-' is treated as a range separator IF AND ONLY IF the parts are "similar".
       Otherwise, it's treated as a delimiter between two distinct serials.
    
    Example: 
    'A100~A105' -> Expand
    'A100-A105' -> Expand (Similar)
    'A100 - B200' -> ['A100', 'B200'] (Dissimilar, split)
    'Model-X' -> ['Model-X'] (Not a range, looks like single entity)
    """
    expanded = []
    if not serial_list:
        return []
        
    for item in serial_list:
        if not item or not isinstance(item, str):
            continue
            
        # Pre-process: Split by clear delimiters first
        # We split by comma or semicolon
        sub_items = re.split(r'[,;]\s*', item)
        
        for sub in sub_items:
            sub = sub.strip()
            if not sub: continue
            
            # Decide on separator
            separator = None
            if '~' in sub:
                separator = '~'
            elif '-' in sub:
                # Only consider hyphen if it looks like a separator (spaces around or distinct parts)
                # But simple 'A-B' could be range or distinct. We'll parsing it.
                separator = '-'
            
            if not separator:
                expanded.append(sub)
                continue
                
            # Split into potential parts
            # We use maxsplit=1 to handle the first range indicator. 
            # (Complex chains like A-B-C are rare and ambiguous, we assume A-B)
            if separator == '~':
                parts = sub.split('~', 1)
            else:
                # For hyphen, we need to be careful not to split "Model-X" immediately
                # If there are spaces " - ", it's likely a separator
                if ' - ' in sub:
                    parts = sub.split(' - ', 1)
                elif sub.count('-') == 1:
                    parts = sub.split('-', 1)
                else:
                    # Multiple hyphens or ambiguous? Treat as single unless clear
                    expanded.append(sub)
                    continue

            if len(parts) != 2:
                expanded.append(sub)
                continue
                
            start_str = parts[0].strip()
            end_str = parts[1].strip()
            
            # --- Range Expansion Logic ---
            
            # 1. Extract potential numbers
            match_start = re.search(r'^(.*?)(\d+)$', start_str)
            match_end = re.search(r'^(.*?)(\d+)$', end_str)
            
            is_range = False
            
            if match_start:
                prefix = match_start.group(1)
                start_num_str = match_start.group(2)
                start_num = int(start_num_str)
                
                # Handling the End Part
                if match_end:
                    end_prefix = match_end.group(1)
                    end_num_str = match_end.group(2)
                    end_num = int(end_num_str)
                    
                    # SIMILARITY CHECKS
                    
                    # Case A: Exact Prefix Match (e.g. A100 - A105)
                    if end_prefix == prefix:
                        is_range = True
                    # Case B: Mixed OCR (0 vs O) Match (e.g. A100 - Al05) - simplified
                    elif end_prefix.replace('0', 'O') == prefix.replace('0', 'O'):
                        is_range = True
                    # Case C: Suffix only extraction (e.g. A100-105)
                    # This happens if end_str was purely digits, match_end would have empty prefix
                    elif end_prefix == "" and separator == '~': 
                        # ~ implies range strongly
                        is_range = True
                    elif end_prefix == "" and separator == '-':
                         # For hyphen, A100-105 is range. A100-2 is likely version/submodel?
                         # Let's assume it IS a range if the number is greater.
                         is_range = True
                    
                    # LOGICAL VALIDATION
                    if is_range:
                        # Must be ascending and reasonable size
                        if end_num < start_num or (end_num - start_num) > 200:
                            is_range = False
                            
                elif end_str.isdigit():
                     # Case where End is just digits (A100~105)
                     end_num = int(end_str)
                     if end_num > start_num and (end_num - start_num) <= 200:
                         is_range = True
                         end_num_str = str(end_num) # for fill logic below (imprecise but works)
            
            if is_range and separator == '-':
                # Extra strictness for Hyphens:
                # If prefix is empty (just numbers 100-200), it's a range.
                # If prefix exists, we already checked equality.
                pass

            # EXECUTE EXPANSION OR SPLIT
            if is_range:
                # Expand
                for i in range(start_num, end_num + 1):
                    # Use START's formatting
                    # We try to preserve padding length of start
                    fmt_num = str(i).zfill(len(start_num_str))
                    expanded.append(f"{prefix}{fmt_num}")
            else:
                # NOT a range.
                if separator == '~':
                    # Tilde usually means range, if failed, keep as whole string?
                    expanded.append(sub)
                else: 
                    # Hyphen: If not a range, treat as SEPARATE items if they look like separate entities
                    # e.g. "SerialA - SerialB"
                    # But "Model-X" should stay "Model-X"
                    
                    # Heuristic: If both parts look like valid serials (alphanumeric length > 3), separate them
                    if len(start_str) > 3 and len(end_str) > 3:
                         expanded.append(start_str)
                         expanded.append(end_str)
                    else:
                         # Likely a single code (e.g. "AB-1")
                         expanded.append(sub)

    return expanded

def clean_serial_number(serial):
    """
    Normalizes a serial number string.
    Fixes OCR issues:
    - 'KO' -> 'K0'
    - 'O' -> '0' if mixed with digits (e.g. 'A5O87' -> 'A5087')
    """
    if not serial: return serial
    
    # 1. Standard KO fix
    if re.match(r'^KO\d+', serial):
        serial = 'K0' + serial[2:]
        
    # 2. Global O -> 0 Fix Check
    # We only apply this if the string contains at least SOME digits (so we don't break "MODEL")
    # AND if the 'O' is adjacent to digits or is inside a clearly numeric-heavy string.
    
    # Simple Heuristic: If it has digits, swap all 'O's to '0's? 
    # Risk: "ISO9001" -> "IS09001". Accepted risk? Perhaps. 
    # Safer: Swap O if it is surrounded by digits or creates a digit pattern.
    
    if any(char.isdigit() for char in serial):
        # Allow O to become 0
        # Check against "all letters" again just in case
        clean = serial.replace('O', '0')
        # But wait, what about "Model No 01"? "No" -> "N0". Bad.
        
        # Regex approach: Replace O only if followed/preceded by digit?
        # Let's try aggressive for now as per user request ("acceptable OCR scan error")
        # User accepted 0/O ambiguity.
        # But let's try to be smart: O sandwiched by digits?
        
        # Replace O with 0 if it is followed by a digit
        serial = re.sub(r'O(?=\d)', '0', serial)
        # Replace O with 0 if it is preceded by a digit
        serial = re.sub(r'(?<=\d)O', '0', serial)
        
    return serial


def is_serial_in_range(target_serial, db_serial_string):
    """
    Checks if 'target_serial' exists within 'db_serial_string', 
    handling potential ranges (~) in the DB string.
    """
    if not db_serial_string or not isinstance(db_serial_string, str):
        return False
        
    # Quick text match first (optimization)
    if target_serial in db_serial_string and '~' not in db_serial_string:
        return True
    
    # If range exists or we want to be strict about boundaries, expand.
    # Split DB string into list (it might be newline separated)
    raw_list = re.split(r'[\n,;]', db_serial_string)
    expanded_list = expand_serial_ranges(raw_list)
    
    # Clean target for comparison
    clean_target = clean_serial_number(target_serial)
    
    # Normalize for fuzzy comparison (O vs 0)
    # If explicit target is KO... we might want to match K0... 
    # But usually user types K0... and DB has K0 or KO.
    target_fuzzy = clean_target.replace('O', '0')
    
    for item in expanded_list:
        # Clean item from DB
        clean_item = clean_serial_number(item)
        item_fuzzy = clean_item.replace('O', '0')
        
        # Check standard substring
        if clean_target in clean_item:
            return True
            
        # Check fuzzy match
        if target_fuzzy in item_fuzzy:
            return True
            
    return False
