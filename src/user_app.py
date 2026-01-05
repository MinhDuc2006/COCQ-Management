import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
from src import sheets
from src.utils import normalize_date, is_serial_in_range

# Load environment variables
load_dotenv()

st.set_page_config(page_title="CO/CQ Search", layout="wide")

st.title("🔍 CO/CQ Document Search")
st.markdown("Search for CO/CQ documents by Serial Number or Date.")

# Configuration (pulled from env for end-user simplicity)
spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")

if not spreadsheet_id:
    st.error("Application is not configured: GOOGLE_SHEET_ID missing in .env")
    st.stop()

# Search UI
col1, col2 = st.columns(2)

with col1:
    serial_query = st.text_input("Serial Number", placeholder="e.g. 2194907").strip()

with col2:
    date_query = st.text_input("Date", placeholder="e.g. 12/05/2023").strip()

if st.button("Search"):
    with st.spinner("Searching records..."):
        try:
            # Fetch data from Google Sheets
            all_data = sheets.get_sheet_data(spreadsheet_id)
            
            if not all_data:
                st.info("No records found in the database.")
            else:
                # Convert to DataFrame for easier filtering
                df = pd.DataFrame(all_data)
                
                # Pre-calculate normalized date column once per fetch for faster searching
                if "Date" in df.columns:
                    df["Normalized_Date"] = df["Date"].apply(normalize_date)
                else:
                    df["Normalized_Date"] = ""

                # Filtering logic
                filtered_df = df.copy()
                
                if serial_query:
                    # Match case-insensitive and handle multi-line serial cells, also check ranges
                    # Use 'apply' to check each cell against specialized logic
                    # We pass the serial_query to the lambda
                    filtered_df = filtered_df[filtered_df["Serial Number"].apply(
                        lambda cell: is_serial_in_range(serial_query, str(cell))
                    )]
                
                if date_query:
                    # Normalize user's query
                    normalized_user_query = normalize_date(date_query)
                    
                    # Search by either raw query or normalized query against our pre-calculated normalized column
                    filtered_df = filtered_df[
                        (filtered_df["Normalized_Date"].str.contains(date_query, case=False, na=False)) |
                        (filtered_df["Normalized_Date"].str.contains(normalized_user_query, case=False, na=False))
                    ]

                
                if filtered_df.empty:
                    st.warning("No matches found for your search.")
                else:
                    st.success(f"Found {len(filtered_df)} match({'es' if len(filtered_df) > 1 else ''}).")
                    
                    # Columns to show
                    available_cols = filtered_df.columns.tolist()
                    target_cols = ["File Name", "Date", "Serial Number", "Drive Link"]
                    cols_to_display = [c for c in target_cols if c in available_cols]
                    
                    # Display using st.dataframe with LinkColumn configuration
                    st.dataframe(
                        filtered_df[cols_to_display],
                        column_config={
                            "Drive Link": st.column_config.LinkColumn(
                                "File Link",
                                help="Click to open the PDF in Google Drive",
                                validate=r"^https://.*",
                                display_text="Open PDF"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
        except Exception as e:
            st.error(f"Search failed: {e}")
            st.info("This might be an authentication issue. Please contact the administrator.")

st.sidebar.markdown("---")
st.sidebar.info("This is the User Search Portal. For administrative tasks, use the Backend App.")
