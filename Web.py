import streamlit as st
import platform
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io
from flask import request  # Required for accessing headers

# Set up the page configuration
st.set_page_config(page_title="My App")

# Hide Streamlit style elements
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.markdown(
    """
    <h1 style="text-align: center; ">File preview</h1>
    """, 
    unsafe_allow_html=True
)

# Function to get the user's public IP using the X-Forwarded-For header or fallback
def get_user_ip():
    # Try to get the user's IP from the X-Forwarded-For header
    forwarded_ip = request.headers.get('X-Forwarded-For')
    
    # If the header exists, use the first IP address in the list
    if forwarded_ip:
        user_ip = forwarded_ip.split(',')[0]
    else:
        # If the header doesn't exist, fall back to the remote address
        user_ip = request.remote_addr
    return user_ip

# Use session state to store the user's IP
if 'user_ip' not in st.session_state:
    st.session_state['user_ip'] = get_user_ip()

# Show user's public IP on the page
st.markdown(f"User's Public IP Address: {st.session_state['user_ip']}")

# Google Drive functions
def authenticate():
    creds = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
    return creds

# Google Drive functions (same as before)
SCOPES = ['https://www.googleapis.com/auth/drive']
PARENT_ID = "1tPWd3s9pdhb_gC-9rTv31IzvXSEvuWCT"

# 🔹 Find a file in Google Drive by name
def find_file(service, file_name, parent_id):
    query = f"'{parent_id}' in parents and name = '{file_name}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    return files

# 🔹 Download an existing file from Google Drive
def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file_stream.seek(0)
    return file_stream

# 🔹 Append new data and upload the updated file
def append_and_upload(new_data, file_name="IP.xlsx"):
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)

    # Check if the file exists
    existing_files = find_file(service, file_name, PARENT_ID)

    if existing_files:
        # ✅ File exists: Download, update, and re-upload
        file_id = existing_files[0]["id"]
        file_stream = download_file(service, file_id)

        # Load existing data into DataFrame
        existing_data = pd.read_excel(file_stream)

        # Convert new_data dictionary into DataFrame and append
        new_df = pd.DataFrame([new_data])
        updated_data = pd.concat([existing_data, new_df], ignore_index=True)

        # Save updated data to a temporary file
        updated_data.to_excel("updated_file.xlsx", index=False)

        # Upload updated file (overwrite existing one)
        media = MediaFileUpload("updated_file.xlsx", resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
    
    else:
        # 🚀 File doesn't exist: Create new file and upload
        new_df = pd.DataFrame([new_data])
        new_df.to_excel("new_file.xlsx", index=False)

        file_metadata = {"name": file_name, "parents": [PARENT_ID]}
        media = MediaFileUpload("new_file.xlsx", resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

# 🔹 Example Usage: Button to upload IP data
if st.button("Upload IP Data"):
    new_data = {
        "IP": st.session_state['user_ip']
    }
    append_and_upload(new_data)

st.markdown("Here is the preview of the file:", unsafe_allow_html=True)
