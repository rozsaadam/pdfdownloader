import streamlit as st
import base64
import time
import io
import zipfile
import re
import os
import tempfile
import shutil
from urllib.parse import urlparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.print_page_options import PrintOptions

# --- 1. Core Logic for PDF Generation ---
def generate_bulk_pdfs(parsed_items):
    # Create a temporary directory for Selenium to download actual PDF files into
    temp_download_dir = tempfile.mkdtemp()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # --- STEALTH SETTINGS ---
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Force Chrome to download PDFs to our temp folder instead of opening them
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    current_datetime = datetime.now().strftime("%d.%m.%Y %H.%M")
    zip_buffer = io.BytesIO()
    
    hide_cookies_js = """
    const selectors = [
        '[id*="cookie"]', '[class*="cookie"]',
        '[id*="consent"]', '[class*="consent"]',
        '[id*="banner"]', '[class*="banner"]',
        '#onetrust-consent-sdk', '.osano-cm-window',
        '.trustarc-banner', '.optanon-alert-box-wrapper'
    ];
    document.querySelectorAll(selectors.join(',')).forEach(el => {
        el.style.display = 'none';
    });
    document.body.style.overflow = 'auto';
    """
    
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for index, (url, name) in enumerate(parsed_items, start=1):
                url = url.strip()
                name = name.strip()
                
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                
                parsed_url = urlparse(url)
                
                # --- NEW LOGIC: Use Selenium to securely download direct PDFs ---
                if parsed_url.path.lower().endswith('.pdf'):
                    # Empty the temp folder before starting so we don't grab old files
                    for filename in os.listdir(temp_download_dir):
                        file_path = os.path.join(temp_download_dir, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            
                    driver.get(url)
                    
                    # Wait for Chrome to finish downloading the file (max 15 seconds)
                    pdf_bytes = None
                    for _ in range(15):
                        files = os.listdir(temp_download_dir)
                        # Chrome uses .crdownload extension while a file is still downloading
                        valid_files = [f for f in files if not f.endswith('.crdownload')]
                        
                        if valid_files:
                            downloaded_file_path = os.path.join(temp_download_dir, valid_files[0])
                            with open(downloaded_file_path, 'rb') as f:
                                pdf_bytes = f.read()
                            break
                        time.sleep(1)
                        
                    if not pdf_bytes:
                        raise Exception(f"Failed to securely download PDF from {url}. The request timed out or was blocked.")
                        
                # --- STANDARD LOGIC: Render standard webpages to PDF ---
                else:
                    driver.get(url)
                    time.sleep(6)  
                    
                    try:
                        driver.execute_script(hide_cookies_js)
                        time.sleep(1)
                    except Exception:
                        pass 
                    
                    print_options = PrintOptions()
                    print_options.background = True
                    
                    pdf_base64 = driver.print_page(print_options)
                    pdf_bytes = base64.b64decode(pdf_base64)
                
                # Sanitize name to prevent file path errors inside the ZIP
                clean_name = re.sub(r'[\\/*?:"<>|]', "", name) if name else "Website"
                file_name = f"{index} {current_datetime} - {clean_name}.pdf"
                
                zip_file.writestr(file_name, pdf_bytes)
                
    finally:
        driver.quit()
        # Clean up the temporary download folder from your hard drive
        shutil.rmtree(temp_download_dir, ignore_errors=True)
        
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# --- 2. Streamlit User Interface ---
st.set_page_config(page_title="Bulk Website to PDF", page_icon="🗂️")

st.title("🗂️ Bulk Website to PDF Converter")

input_mode = st.radio(
    "Select Input Format", 
    ["Markdown", "Plain Text (URL, Name)"], 
    horizontal=True
)

if input_mode == "Markdown":
    example_text = """1. [BT Taxe și comisioane (actualizate 01.04.2026)](https://www.bancatransilvania.ro/brosura-comisioane)
2. [BT PDF Comisioane persoane fizice](https://www.bancatransilvania.ro/files/app/media/Taxe-si-comisioane/Persoane-fizice.pdf)
* [N26 Mastercard](https://n26.com/en-eu/mastercard)"""
else:
    example_text = """https://www.bancatransilvania.ro/brosura-comisioane, BT Taxe și comisioane
https://www.bancatransilvania.ro/files/app/media/Taxe-si-comisioane/Persoane-fizice.pdf, BT PDF Comisioane persoane fizice
https://n26.com/en-eu/mastercard, N26 Mastercard"""

user_input = st.text_area("Paste your links below:", value=example_text, height=200)

if st.button("Generate PDF Archive", type="primary"):
    if user_input.strip():
        lines = user_input.strip().split('\n')
        parsed_items = []
        md_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if input_mode == "Markdown":
                md_match = md_pattern.search(line)
                if md_match:
                    name = md_match.group(1).strip()
                    url = md_match.group(2).strip()
                    parsed_items.append((url, name))
                else:
                    parsed_items.append((line, "Unknown Name"))
                    
            elif input_mode == "Plain Text (URL, Name)":
                if "," in line:
                    url, name = line.split(",", 1)
                    parsed_items.append((url.strip(), name.strip()))
                else:
                    parsed_items.append((line, "Unknown Name"))
        
        if parsed_items:
            with st.spinner(f"Processing {len(parsed_items)} links... This might take a minute or two."):
                try:
                    zip_data = generate_bulk_pdfs(parsed_items)
                    st.success("Done! All webpages have been converted to PDF.")
                    
                    export_date = datetime.now().strftime('%Y-%m-%d_%H-%M')
                    export_filename = f"PDF_Export_{export_date}.zip"
                    
                    st.download_button(
                        label="📦 Download ZIP with all PDFs",
                        data=zip_data,
                        file_name=export_filename,
                        mime="application/zip"
                    )
                except Exception as e:
                    st.error(f"An error occurred during conversion: {e}")
        else:
            st.warning("No valid links found.")
    else:
        st.warning("Please enter at least one link.")
