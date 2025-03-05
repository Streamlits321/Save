import streamlit as st
import requests
from flask import Flask, request
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io

# Flask app to fetch IP
app = Flask(__name__)

real_ip = None  # Global variable to store IP

@app.route('/')
def get_ip():
    global real_ip
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in user_ip:
        user_ip = user_ip.split(',')[0]
    real_ip = user_ip  # Store the IP for Streamlit to use
    # Shutdown the Flask server after IP is fetched
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    return real_ip


def run_flask():
    app.run(port=5002)  # Change the port to 5001 (or any other unused port)


# Run Flask in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Streamlit app to display PDF and collect IP
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
        
        setInterval(hideDriveUI, 1000);
    </script>
"""

pdf_display = f"""
    <iframe src="{pdf_url}" width="700" height="900" 
    style="border: none;" sandbox="allow-scripts allow-same-origin"></iframe>
    {hide_js}
"""

button = st.button("Preview")
if button:
    with st.spinner("In Progress..."):
        # Get the user's public IP from the Flask server
        if real_ip is None:
            st.error("IP not fetched yet.")
        else:
            st.write(f"Fetched IP: {real_ip}")

            # Set up Google Drive API integration
            SCOPES = ['https://www.googleapis.com/auth/drive']
            PARENT_ID = "1tPWd3s9pdhb_gC-9rTv31IzvXSEvuWCT"

            def authenticate():
                creds = service_account.Credentials.from_service_account_info(
                    st.secrets["google_service_account"], scopes=SCOPES)
                return creds

            def find_file(service, file_name, parent_id):
                query = f"'{parent_id}' in parents and name = '{file_name}' and trashed = false"
                results = service.files().list(q=query, fields="files(id, name)").execute()
                return results.get('files', [])

            def download_file(service, file_id):
                request = service.files().get_media(fileId=file_id)
                file_stream = io.BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                file_stream.seek(0)
                return file_stream

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

            new_data = {"IP": real_ip}
            append_and_upload(new_data)
            st.markdown(pdf_display, unsafe_allow_html=True)
