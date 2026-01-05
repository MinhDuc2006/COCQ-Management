import streamlit as st
import time
from datetime import datetime
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
# Sidebar Configuration
st.sidebar.header("Configuration")
mode = st.sidebar.radio("Operation Mode", ["Manual Scan", "Continuous Monitor"], help="Choose 'Manual' for one-time scan or 'Continuous' to run in background.")

default_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
default_sheet_id = os.getenv("GOOGLE_SHEET_ID", "")

drive_folder_id = st.sidebar.text_input("Google Drive Folder ID", value=default_folder_id, help="The ID of the folder to scan.")
spreadsheet_id = st.sidebar.text_input("Google Sheet ID", value=default_sheet_id, help="The ID of the destination Google Sheet.")
force_ocr = st.sidebar.checkbox("🔍 Force OCR for Scanned Files", value=False)
recursive_search = st.sidebar.checkbox("📂 Recursive Search", value=False)

if mode == "Continuous Monitor":
    scan_interval = st.sidebar.number_input("Scan Interval (minutes)", min_value=1, value=10, step=1)

# Session State
if 'extracted_data' not in st.session_state:
    st.session_state['extracted_data'] = []

# --- MANUAL MODE ---
if mode == "Manual Scan":
    if st.sidebar.button("🚀 Start Scan", type="primary"):
        if not drive_folder_id:
            st.error("Please provide a Google Drive Folder ID.")
        else:
            try:
                # 1. Fetch existing data for deduplication (Optional but good for manual too)
                existing_links = set()
                if spreadsheet_id:
                    with st.spinner("Fetching existing data to check for duplicates..."):
                        existing_links = sheets.get_existing_drive_links(spreadsheet_id)

                with st.spinner("Scanning Google Drive..."):
                    files = drive_scanner.search_files(drive_folder_id, recursive=recursive_search)
                
                # Filter duplicates
                new_files = [f for f in files if f['webViewLink'] not in existing_links]
                
                if not new_files:
                    if len(files) > 0:
                        st.info(f"Scanned {len(files)} files, but all are already in the database! ✅")
                    else:
                        st.warning("No CO/CQ files found in the specified folder.")
                else:
                    st.info(f"Found {len(new_files)} NEW documents (out of {len(files)} total). Starting extraction...")
                    progress_bar = st.progress(0)
                    new_data = []
                    
                    for i, file in enumerate(new_files):
                        file_id = file['id']
                        file_name = file['name']
                        web_link = file['webViewLink']
                        
                        status_msg = f"Reading {file_name}..."
                        if force_ocr: status_msg = f"🔍 Running OCR on {file_name}..."
                        
                        with st.status(status_msg):
                            # Create temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                temp_path = tmp.name
                                
                            try:
                                drive_scanner.download_file(file_id, temp_path)
                                data, method = extractor.extract_data(temp_path, force_ocr=force_ocr)
                                
                                row = {
                                    "File Name": file_name,
                                    "Date": data.get("date"),
                                    "Serial Number": data.get("serial_number"),
                                    "Method": method,
                                    "Drive Link": web_link,
                                }
                                new_data.append(row)
                                st.write(f"✅ Processed {file_name}")
                                
                            except Exception as e:
                                st.warning(f"Failed to process {file_name}: {e}")
                            finally:
                                if os.path.exists(temp_path): os.remove(temp_path)
                        
                        progress_bar.progress((i + 1) / len(new_files))
                    
                    st.session_state['extracted_data'] = new_data
                    st.success(f"Processing complete! {len(new_data)} new files analyzed.")
                    
            except Exception as e:
                st.error(f"Error during processing: {e}")

    # Display Data and Sync (Manual)
    if st.session_state['extracted_data']:
        st.subheader("Preview Extracted Data")
        df = pd.DataFrame(st.session_state['extracted_data'])
        st.dataframe(df[["File Name", "Date", "Serial Number", "Method", "Drive Link"]])
        
        if st.button("💾 Sync to Google Sheets"):
            if not spreadsheet_id:
                st.error("Spreadsheet ID is missing.")
            else:
                with st.spinner("Syncing to Sheets..."):
                    try:
                        rows_to_sync = []
                        for item in st.session_state['extracted_data']:
                            rows_to_sync.append([
                                item["File Name"],
                                item["Date"],
                                item["Serial Number"],
                                item["Drive Link"]
                            ])
                        
                        sheets.append_data_to_sheet(spreadsheet_id, rows_to_sync)
                        st.success(f"Successfully synced {len(rows_to_sync)} rows to Google Sheets!")
                        # Clear session state after sync to prevent double sync
                        st.session_state['extracted_data'] = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sync failed: {e}")

# --- CONTINUOUS MONITOR MODE ---
elif mode == "Continuous Monitor":
    st.info(f"🔄 System will scan every {scan_interval} minutes for NEW files and sync them automatically.")
    
    if st.button("🔴 Start Monitoring Loop"):
        status_placeholder = st.empty()
        log_placeholder = st.empty()
        logs = []

        def log(msg):
            timestamp = datetime.now().strftime("%H:%M:%S")
            logs.insert(0, f"[{timestamp}] {msg}")
            # Keep last 50 logs
            if len(logs) > 50: logs.pop()
            log_placeholder.code("\n".join(logs), language="text")

        while True:
            try:
                # 1. Check for duplicates
                existing_links = set()
                if spreadsheet_id:
                    status_placeholder.info("Fetching existing records...")
                    existing_links = sheets.get_existing_drive_links(spreadsheet_id)
                
                # 2. Scan Drive
                status_placeholder.info("Scanning Google Drive...")
                files = drive_scanner.search_files(drive_folder_id, recursive=recursive_search)
                
                # 3. Filter
                new_files = [f for f in files if f['webViewLink'] not in existing_links]
                
                if new_files:
                    log(f"Found {len(new_files)} new files. Processing...")
                    
                    for file in new_files:
                        file_name = file['name']
                        web_link = file['webViewLink']
                        
                        status_placeholder.info(f"Processing: {file_name}...")
                        
                        # Download & Extract
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            temp_path = tmp.name
                        
                        try:
                            drive_scanner.download_file(file['id'], temp_path)
                            data, method = extractor.extract_data(temp_path, force_ocr=force_ocr)
                            
                            # Immediate Sync
                            row_data = [[
                                file_name,
                                data.get("date"),
                                data.get("serial_number"),
                                web_link
                            ]]
                            
                            if spreadsheet_id:
                                sheets.append_data_to_sheet(spreadsheet_id, row_data)
                                log(f"✅ Synced: {file_name} ({method})")
                            else:
                                log(f"⚠️ Skipped Sync (No ID): {file_name}")
                                
                        except Exception as e:
                            log(f"❌ Error {file_name}: {e}")
                        finally:
                            if os.path.exists(temp_path): os.remove(temp_path)
                            
                else:
                    log("No new files found.")

                status_placeholder.success(f"Sleeping for {scan_interval} minutes...")
                time.sleep(scan_interval * 60)
                
            except Exception as e:
                log(f"Critical Error: {e}")
                time.sleep(60) # Retry after 1 min on error

st.sidebar.markdown("---")
st.sidebar.info("Admin Portal v2.0")
