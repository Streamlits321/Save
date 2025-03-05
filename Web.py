import streamlit as st
import platform
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io
import requests

st.set_page_config(page_title="My App")

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

# JavaScript to fetch the user's public IP and pass it to Streamlit
get_user_ip_js = """
    <script>
        fetch('https://api64.ipify.org?format=json')
            .then(response => response.json())
            .then(data => {
                // Send the IP address to Streamlit via the window function
                window.parent.postMessage({type: 'user-ip', ip: data.ip}, '*');
            });
    </script>
"""

# Embed the JS code to get the user's IP address
st.markdown(get_user_ip_js, unsafe_allow_html=True)

# Define a placeholder for the user's IP
user_ip = st.empty()

# Function to listen for the user's IP address passed from JS
def set_user_ip(ip):
    user_ip.text(f"User's Public IP Address: {ip}")

# Listen for the 'user-ip' message from JavaScript
st.experimental_set_query_params()  # Ensure the Streamlit page runs in an interactive mode.
st.experimental_rerun()  # Triggering a rerun to call the JS code for the first time

# Function to interact with Google Drive
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

# 🔹 Example Usage
if user_ip:
    new_data = {
        "IP": user_ip
    }
    append_and_upload(new_data)

st.markdown("Here is the preview of the file:", unsafe_allow_html=True)
