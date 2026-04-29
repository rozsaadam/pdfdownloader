import streamlit as st
import base64
import time
import io
import zipfile
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.print_page_options import PrintOptions

# --- 1. Core Logic for PDF Generation ---
def generate_bulk_pdfs(parsed_items):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # --- STEALTH SETTINGS ---
    # 1. Spoof a real Windows 11 / Chrome User-Agent so we don't look like "HeadlessChrome"
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    # 2. Disable the "navigator.webdriver" flag that websites use to detect bots
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 3. Remove the "Chrome is being controlled by automated test software" infobar/flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # 4. Final stealth step: Execute a script immediately to wipe the webdriver variable from the browser
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Timestamp format: dd.mm.yyyy hh.mm
    current_datetime = datetime.now().strftime("%d.%m.%Y %H.%M")
    zip_buffer = io.BytesIO()
    
    # JavaScript to hide common cookie banners, consent dialogs, and overlays
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
                
                driver.get(url)
                
                # Wait 6 seconds to allow anti-bot JS challenges and heavy assets to load
                time.sleep(6)  
                
                # Execute the JS to wipe away cookie popups
                try:
                    driver.execute_script(hide_cookies_js)
                    time.sleep(1)
                except Exception:
                    pass 
                
                print_options = PrintOptions()
                print_options.background = True
                
                pdf_base64 = driver.print_page(print_options)
                pdf_bytes = base64.b64decode(pdf_base64)
                
                # Sanitize name to prevent file path errors
                clean_name = re.sub(r'[\\/*?:"<>|]', "", name) if name else "Website"
                file_name = f"{index} {current_datetime} - {clean_name}.pdf"
                
                zip_file.writestr(file_name, pdf_bytes)
    finally:
        driver.quit()
        
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# --- 2. Streamlit User Interface ---
st.set_page_config(page_title="Bulk Website to PDF", page_icon="🗂️")

st.title("🗂️ Bulk Website to PDF Converter")

# Input Mode Toggle
input_mode = st.radio(
    "Select Input Format", 
    ["Markdown", "Plain Text (URL, Name)"], 
    horizontal=True
)

# Dynamically change the example text based on the selected mode
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
