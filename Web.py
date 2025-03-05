import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import io

# Streamlit app configuration
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
    <h1 style="text-align: center; ">File Preview</h1>
    """, 
    unsafe_allow_html=True
)

# PDF URL for embedding
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

# JavaScript to fetch the user's public IP and pass it to Streamlit
get_user_ip_js = """
    <script>
        fetch('https://api64.ipify.org?format=json')
            .then(response => response.json())
            .then(data => {
                // Send the IP address to Streamlit via the URL
                window.location.href = window.location.origin + window.location.pathname + "?ip=" + data.ip;
            });
    </script>
"""

# Embed the JS code to get the user's IP address
st.components.v1.html(get_user_ip_js, height=0)

# Retrieve the IP address from the URL query parameters
query_params = st.experimental_get_query_params()
user_ip = query_params.get("ip", [None])[0]

# Display the user's IP address
if user_ip:
    st.write(f"User IP: {user_ip}")

    # Google Drive API functions
    SCOPES = ['https://www.googleapis.com/auth/drive']
    PARENT_ID = "1tPWd3s9pdhb_gC-9rTv31IzvXSEvuWCT"

    def authenticate():
        creds = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
        return creds

    def find_file(service, file_name, parent_id):
        query = f"'{parent_id}' in parents and name = '{file_name}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        return files

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

    # Append the user's IP to the Google Drive file
    new_data = {"IP": user_ip}
    append_and_upload(new_data)

    # Display the PDF
    st.markdown(pdf_display, unsafe_allow_html=True)
