import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io
import requests

# Streamlit app settings
st.set_page_config(page_title="My App")

# Hide Streamlit UI elements
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>File Preview</h1>", unsafe_allow_html=True)

# Function to get the real client IP
def get_client_ip():
    try:
        # Get IP from Streamlit headers
        ip = st.experimental_get_query_params().get("ip", [None])[0]

        # Fallback method (sometimes Streamlit does not pass headers)
        if not ip:
            response = requests.get("https://api64.ipify.org?format=json")
            ip = response.json().get("ip")

        return ip
    except:
        return "Unknown"

# Display IP fetching status
user_ip = get_client_ip()
st.write(f"Client's Public IP: {user_ip}")

# Google Drive API settings
SCOPES = ['https://www.googleapis.com/auth/drive']
PARENT_ID = "1tPWd3s9pdhb_gC-9rTv31IzvXSEvuWCT"

# Authenticate Google Drive API
def authenticate():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"], scopes=SCOPES)
    return creds

# Find a file in Google Drive
def find_file(service, file_name, parent_id):
    query = f"'{parent_id}' in parents and name = '{file_name}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

# Download a file from Google Drive
def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file_stream.seek(0)
    return file_stream

# Append and upload new IP data to Google Drive
def append_and_upload(new_data, file_name="IP.xlsx"):
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)
    existing_files = find_file(service, file_name, PARENT_ID)

    if existing_files:
        file_id = existing_files[0]["id"]
        file_stream = download_file(service, file_id)
        existing_data = pd.read_excel(file_stream)
        new_df = pd.DataFrame([new_data])
        updated_data = pd.concat([existing_data, new_df], ignore_index=True)
        updated_data.to_excel("updated_file.xlsx", index=False)
        media = MediaFileUpload("updated_file.xlsx", resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        new_df = pd.DataFrame([new_data])
        new_df.to_excel("new_file.xlsx", index=False)
        file_metadata = {"name": file_name, "parents": [PARENT_ID]}
        media = MediaFileUpload("new_file.xlsx", resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

# Save the collected IP
if user_ip and user_ip != "Unknown":
    new_data = {"Public IP": user_ip}
    append_and_upload(new_data)

# PDF Preview
pdf_url = "https://drive.google.com/file/d/1sBPt9-h33f0u1QzyZ5bCt1O8cVqpxiYV/preview"
pdf_display = f"""
    <iframe src="{pdf_url}" width="700" height="900" style="border: none;"></iframe>
"""
st.markdown(pdf_display, unsafe_allow_html=True)
