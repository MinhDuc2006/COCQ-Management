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
