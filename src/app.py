import streamlit as st
import pandas as pd
import os
import tempfile
from dotenv import load_dotenv
from src import drive_scanner, extractor, sheets

import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="CO/CQ Automator", layout="wide")

st.title("📄 CO/CQ Automator")
st.markdown("Scan Google Drive for CO/CQ documents, extract metadata, and sync to Google Sheets.")

# Sidebar Configuration
st.sidebar.header("Configuration")
default_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
default_sheet_id = os.getenv("GOOGLE_SHEET_ID", "")

drive_folder_id = st.sidebar.text_input("Google Drive Folder ID", value=default_folder_id, help="The ID of the folder to scan. Leave empty to search entire Drive.")
spreadsheet_id = st.sidebar.text_input("Google Sheet ID", value=default_sheet_id, help="The ID of the destination Google Sheet.")
force_ocr = st.sidebar.checkbox("🔍 Force OCR for Scanned Files", value=False, help="Use Tesseract OCR for all files, ignoring direct text extraction. Recommended for scanned photos.")

# Session State for data persistence across reruns
if 'extracted_data' not in st.session_state:
    st.session_state['extracted_data'] = []

if 'processed_files' not in st.session_state:
    st.session_state['processed_files'] = set()

# Main Action Area
if st.sidebar.button("🚀 Start Processing", type="primary"):
    if not drive_folder_id:
        st.error("Please provide a Google Drive Folder ID.")
    else:
        try:
            with st.spinner("Scanning Google Drive..."):
                files = drive_scanner.search_files(drive_folder_id)
            
            if not files:
                st.warning("No CO/CQ files found in the specified folder.")
            else:
                st.info(f"Found {len(files)} potential documents. Starting extraction...")
                progress_bar = st.progress(0)
                new_data = []
                
                for i, file in enumerate(files):
                    file_id = file['id']
                    file_name = file['name']
                    web_link = file['webViewLink']
                    
                    # Update status based on force_ocr
                    status_msg = f"Reading {file_name}..."
                    if force_ocr:
                        status_msg = f"🔍 Running OCR on {file_name} (this may take a minute)..."
                    
                    with st.status(status_msg):
                        # Create temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            temp_path = tmp.name
                            
                        try:
                            # Download
                            drive_scanner.download_file(file_id, temp_path)
                            
                            # Extract
                            data, method = extractor.extract_data(temp_path, force_ocr=force_ocr)
                            
                            # Prepare Row
                            row = {
                                "File Name": file_name,
                                "Date": data.get("date"),
                                "Serial Number": data.get("serial_number"),
                                "Method": method,
                                "Drive Link": web_link,
                            }
                            new_data.append(row)
                            st.write(f"✅ Processed {file_name} via {method}")
                            
                        except Exception as e:
                            st.warning(f"Failed to process {file_name}: {e}")
                        finally:
                            # Cleanup temp file
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                    
                    progress_bar.progress((i + 1) / len(files))
                
                st.session_state['extracted_data'] = new_data
                st.success(f"Processing complete! {len(new_data)} files analyzed.")
                
        except Exception as e:
            st.error(f"Error during processing: {e}")
            # likely auth error
            st.info("Check your 'credentials.json' and 'token.json'. run 'python src/auth.py' locally to debug auth.")

# Display Data and Sync
if st.session_state['extracted_data']:
    st.subheader("Preview Extracted Data")
    df = pd.DataFrame(st.session_state['extracted_data'])
    
    # Display config for which columns to show
    st.dataframe(df[["File Name", "Date", "Serial Number", "Method", "Drive Link"]])
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Google Sheet"):
            if not spreadsheet_id:
                st.error("Spreadsheet ID is missing.")
            else:
                with st.spinner("Clearing sheet..."):
                    try:
                        cleared_rows = sheets.clear_sheet_data(spreadsheet_id)
                        st.success(f"Cleared {cleared_rows} rows from Google Sheet!")
                    except Exception as e:
                        st.error(f"Failed to clear sheet: {e}")
    
    with col2:
        if st.button("💾 Sync to Google Sheets"):
            if not spreadsheet_id:
                st.error("Spreadsheet ID is missing.")
            else:
                with st.spinner("Syncing to Sheets..."):
                    try:
                        # Prepare list of lists
                        rows_to_sync = []
                        for item in st.session_state['extracted_data']:
                            rows_to_sync.append([
                                item["File Name"],
                                # item["Extracted Name"], # REMOVED
                                item["Date"],
                                item["Serial Number"],
                                item["Drive Link"]
                            ])
                        
                        sheets.append_data_to_sheet(spreadsheet_id, rows_to_sync)
                        st.success(f"Successfully synced {len(rows_to_sync)} rows to Google Sheets!")
                    except Exception as e:
                        st.error(f"Sync failed: {e}")

st.sidebar.markdown("---")
st.sidebar.info("Make sure `credentials.json` is present in the root directory.")
