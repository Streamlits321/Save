import streamlit as st
import requests
import socket
import platform
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io

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



pdf_url = "https://drive.google.com/file/d/1sBPt9-h33f0u1QzyZ5bCt1O8cVqpxiYV/preview"

# JavaScript to block interactions and remove UI elements
hide_js = """
    <script>
        function hideDriveUI() {
            let iframe = document.querySelector("iframe");
            if (iframe) {
                let iframeWindow = iframe.contentWindow;
                if (iframeWindow) {
                    let iframeDoc = iframeWindow.document;
                    if (iframeDoc) {
                        let elements = iframeDoc.querySelectorAll('a, button, .ndfHFb-c4YZDc');
                        elements.forEach(el => el.style.display = 'none');  // Hide all links, buttons, UI elements
                    }
                }
            }
        }
        
        // Run every 1 second to continuously hide elements
        setInterval(hideDriveUI, 1000);
    </script>
"""

# Embed PDF inside an iframe with sandbox restrictions
pdf_display = f"""
    <iframe src="{pdf_url}" width="700" height="900" 
    style="border: none;" sandbox="allow-scripts allow-same-origin"></iframe>
    {hide_js}
"""
button=st.button("Preview")
if button:
    with st.spinner("In Progress..."):
        def get_device_name():
            try:
                return socket.gethostname() or platform.node()
            except Exception as e:
                return f"Unknown Device ({e})"

        device_name = get_device_name()
        local_ip = socket.gethostbyname(socket.gethostname())

        public_ip = requests.get("https://api64.ipify.org").text


        SCOPES = ['https://www.googleapis.com/auth/drive']
        PARENT_ID = "1tPWd3s9pdhb_gC-9rTv31IzvXSEvuWCT"

        def authenticate():
            creds = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
            return creds

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

                # Convert new_data dictionary into a DataFrame and append
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
        new_data = {
            "Device Name": device_name,
            "Local IP": local_ip,
            "Public IP": public_ip,
        }

        append_and_upload(new_data)

        st.markdown(pdf_display, unsafe_allow_html=True)
