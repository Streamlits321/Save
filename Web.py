import streamlit as st
import requests
import socket
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io

# Function to get local IP of the server (machine where Streamlit app is running)
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'  # Default to localhost
    finally:
        s.close()
    return local_ip

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
        # Get the user's real IP from ipify API
        ip_response = requests.get("https://api.ipify.org?format=json")
        if ip_response.status_code == 200:
            real_ip = ip_response.json().get("ip")
            st.write(f"Fetched Public IP: {real_ip}")

            # Get the local IP of the server (machine where the app is hosted)
            local_ip = get_local_ip()
            st.write(f"Local IP of Server: {local_ip}")

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

            new_data = {"Public IP": real_ip, "Server Local IP": local_ip}
            append_and_upload(new_data)
            st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.error("Failed to fetch IP address")
