import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import pandas as pd
import io
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import time


# Function to get public IP using ipinfo.io API
def get_user_ip():
    ua = UserAgent()
    user_agent = ua.random
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()

    url = "https://router-network.com/tools/what-is-my-local-ip"
    driver.get(url)
    time.sleep(10)
    ip_element = driver.find_element("xpath", '//*[@id="ip-api-query"]')

    # Get the IP address text
    ip_address = ip_element.text
    print(f"My IP address is: {ip_address}")

    # Close the browser window
    driver.quit()
    return ip_address

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
        # Get the user's public IP from Streamlit (or fallback to ipinfo.io)
        user_ip = get_user_ip()
        if user_ip:
            st.write(f"Fetched Public IP: {user_ip}")

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

            # New data to append (public IP)
            new_data = {"Public IP": user_ip}
            append_and_upload(new_data)

            # Display the PDF
            st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.error("Failed to fetch the IP address.")
