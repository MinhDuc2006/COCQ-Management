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
                # 1. Fetch existing data for deduplication
                existing_links = set()
                if spreadsheet_id:
                    with st.spinner("Fetching existing data to check for duplicates..."):
                        existing_links = sheets.get_existing_drive_links(spreadsheet_id)

                # Initialize counters
                total_new_files = 0
                
                # Progress Bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Use the new generator to walk incrementally
                # We can't know total folders/files easily for progress bar 0-100%, 
                # so we'll just pulse or update text based on files found.
                
                # Helper to process a batch of files
                def process_batch(files_to_process, folder_name):
                    folder_new_data = []
                    count = len(files_to_process)
                    
                    for i, file in enumerate(files_to_process):
                        file_name = file['name']
                        web_link = file['webViewLink']
                        
                        status_msg = f"Reading {file_name} in '{folder_name}'..."
                        if force_ocr: status_msg = f"🔍 OCR on {file_name} in '{folder_name}'..."
                        
                        status_text.text(status_msg)
                        
                        # Download & Extract
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            temp_path = tmp.name
                            
                        try:
                            drive_scanner.download_file(file['id'], temp_path)
                            data, method = extractor.extract_data(temp_path, force_ocr=force_ocr)
                            
                            row = {
                                "File Name": file_name,
                                "Date": data.get("date"),
                                "Serial Number": data.get("serial_number"),
                                "Method": method,
                                "Drive Link": web_link,
                            }
                            folder_new_data.append(row)
                            st.write(f"✅ Processed {file_name}")
                            
                        except Exception as e:
                            st.warning(f"Failed to process {file_name}: {e}")
                        finally:
                            if os.path.exists(temp_path): os.remove(temp_path)
                            
                    return folder_new_data

                # Main Loop
                st.info("Scanning started... folders will be processed one by one.")
                
                for folder_name, files in drive_scanner.walk_folder_structure(drive_folder_id, recursive=recursive_search):
                    status_text.text(f"Scanning folder: {folder_name}...")
                    
                    # Filter duplicates for this batch
                    new_files = [f for f in files if f['webViewLink'] not in existing_links]
                    
                    if new_files:
                        st.info(f"📂 Found {len(new_files)} new files in '{folder_name}'. Processing...")
                        batch_data = process_batch(new_files, folder_name)
                        
                        if batch_data:
                            # Add to session state for preview
                            st.session_state['extracted_data'].extend(batch_data)
                            
                            # Auto-Sync Implementation for Manual Mode? 
                            # User only asked for "scanning one sub-folder at a time to ensure syncing". 
                            # Let's sync IMMEDIATELY to sheet if ID is present.
                            if spreadsheet_id:
                                try:
                                    rows_to_sync = [[
                                        item["File Name"],
                                        item["Date"],
                                        item["Serial Number"],
                                        item["Drive Link"]
                                    ] for item in batch_data]
                                    
                                    sheets.append_data_to_sheet(spreadsheet_id, rows_to_sync)
                                    st.success(f"💾 Synced {len(rows_to_sync)} rows from '{folder_name}' to Sheets.")
                                except Exception as e:
                                    st.error(f"Sync failed for batch: {e}")
                            
                            total_new_files += len(batch_data)
                    else:
                        # Optional: Indicate empty folder?
                        # st.text(f"No new files in '{folder_name}'.")
                        pass

                if total_new_files > 0:
                    st.success(f"🎉 Complete! Processed and synced {total_new_files} new files.")
                else:
                    st.warning("Scan complete. No new CO/CQ files found.")
                    
            except Exception as e:
                st.error(f"Error during processing: {e}")

    # Display Data (Accumulated)
    if st.session_state['extracted_data']:
        st.subheader("Session Data Preview")
        df = pd.DataFrame(st.session_state['extracted_data'])
        st.dataframe(df[["File Name", "Date", "Serial Number", "Method", "Drive Link"]])
        
        # We don't need a manual Sync button anymore if we auto-synced, or we keep it for safety?
        # Let's keep it but label it "Re-Sync Session Data"
        if st.button("💾 Re-Sync All Session Data"):
             # ... (existing sync logic) ...
             pass

# --- CONTINUOUS MONITOR MODE ---
elif mode == "Continuous Monitor":
    st.info(f"🔄 System will scan NEW files incrementally (folder by folder) every {scan_interval} minutes.")
    
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
                
                # 2. Walk Drive
                status_placeholder.info("Starting incremental scan...")
                
                files_found_in_loop = 0
                
                for folder_name, files in drive_scanner.walk_folder_structure(drive_folder_id, recursive=recursive_search):
                    status_placeholder.info(f"Scanning: {folder_name} ...")
                    
                    # Filter
                    new_files = [f for f in files if f['webViewLink'] not in existing_links]
                    
                    if new_files:
                        log(f"📂 {folder_name}: Found {len(new_files)} new files.")
                        
                        for file in new_files:
                            file_name = file['name']
                            web_link = file['webViewLink']
                            
                            status_placeholder.info(f"Processing: {file_name} ({folder_name})...")
                            
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
                                    log(f"✅ Synced: {file_name}")
                                    files_found_in_loop += 1
                                    
                                    # Add to local cache to prevent re-processing separate dups in same loop?
                                    existing_links.add(web_link) 
                                else:
                                    log(f"⚠️ Skipped Sync (No ID): {file_name}")
                                    
                            except Exception as e:
                                log(f"❌ Error {file_name}: {e}")
                            finally:
                                if os.path.exists(temp_path): os.remove(temp_path)
                    
                    # Yielding back to loop allows "breathing room" or UI updates if needed
                
                if files_found_in_loop == 0:
                     log("Scan complete. No new files.")
                else:
                     log(f"Loop complete. Synced {files_found_in_loop} files.")

                status_placeholder.success(f"Sleeping for {scan_interval} minutes...")
                time.sleep(scan_interval * 60)
                
            except Exception as e:
                log(f"Critical Error: {e}")
                time.sleep(60) # Retry after 1 min on error

st.sidebar.markdown("---")
st.sidebar.info("Admin Portal v2.0")
