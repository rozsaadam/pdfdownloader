import streamlit as st
import base64
import time
import io
import zipfile
import re
import pytz
from urllib.parse import urlparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.print_page_options import PrintOptions

def generate_bulk_pdfs(parsed_items, tz_string):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.page_load_strategy = 'eager'
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    
    # --- TIME ZONE LOGIC ---
    local_tz = pytz.timezone(tz_string)
    current_datetime = datetime.now(local_tz).strftime("%d.%m.%Y %H.%M")
    
    zip_buffer = io.BytesIO()
    
    hide_cookies_js = "const selectors = ['[id*=\"cookie\"]', '[class*=\"cookie\"]', '[id*=\"consent\"]', '[class*=\"consent\"]', '[id*=\"banner\"]', '[class*=\"banner\"]', '#onetrust-consent-sdk', '.osano-cm-window', '.trustarc-banner', '.optanon-alert-box-wrapper']; document.querySelectorAll(selectors.join(',')).forEach(el => { el.style.display = 'none'; }); document.body.style.overflow = 'auto';"
    
    fetch_js = "var pdf_url = arguments[0]; var done = arguments[1]; fetch(pdf_url).then(response => { if (!response.ok) throw new Error('HTTP ' + response.status); return response.blob(); }).then(blob => { var reader = new FileReader(); reader.onloadend = function() { done(reader.result); }; reader.readAsDataURL(blob); }).catch(err => done('ERROR: ' + err.message));"
    
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for index, (url, name) in enumerate(parsed_items, start=1):
                url = url.strip()
                name = name.strip()
                
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                
                parsed_url = urlparse(url)
                clean_name = re.sub(r'[\\/*?:"<>|]', "", name) if name else "Website"
                file_name = f"{index} {current_datetime} - {clean_name}.pdf"
                
                try:
                    if parsed_url.path.lower().endswith('.pdf'):
                        root_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
                        driver.get(root_url)
                        time.sleep(4)
                        
                        driver.set_script_timeout(30)
                        result = driver.execute_async_script(fetch_js, url)
                        
                        if isinstance(result, str) and 'base64,' in result:
                            b64_data = result.split('base64,')[1]
                            pdf_bytes = base64.b64decode(b64_data)
                            if not pdf_bytes.startswith(b'%PDF'):
                                raise Exception("Downloaded file is not a valid PDF.")
                        else:
                            raise Exception(f"Fetch failed: {result}")
                            
                    else:
                        driver.get(url)
                        time.sleep(5)  
                        
                        try:
                            driver.execute_script(hide_cookies_js)
                            time.sleep(1)
                        except Exception:
                            pass 
                        
                        print_options = PrintOptions()
                        print_options.background = True
                        pdf_base64 = driver.print_page(print_options)
                        pdf_bytes = base64.b64decode(pdf_base64)
                    
                    zip_file.writestr(file_name, pdf_bytes)
                
                except Exception as e:
                    error_msg = f"Failed to process {url}\nError: {str(e)}"
                    zip_file.writestr(file_name.replace('.pdf', '_ERROR.txt'), error_msg)
                
    finally:
        driver.quit()
        
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

st.set_page_config(page_title="Bulk Website to PDF", page_icon="🗂️")
st.title("🗂️ Bulk Website to PDF Converter")

# --- UI FOR TIME ZONE SELECTION ---
col1, col2 = st.columns(2)

with col1:
    input_mode = st.radio("Select Input Format", ["Markdown", "Plain Text (URL, Name)"])

with col2:
    tz_options = {
        "Budapest (CET/CEST)": "Europe/Budapest",
        "London (GMT/BST)": "Europe/London",
        "Tallinn (EET/EEST)": "Europe/Tallinn"
    }
    selected_tz_label = st.radio("Select Time Zone for File Names", list(tz_options.keys()))
    selected_tz_string = tz_options[selected_tz_label]

example_md = "1. [BT Taxe și comisioane (actualizate 01.04.2026)](https://www.bancatransilvania.ro/brosura-comisioane)\n2. [BT PDF Comisioane persoane fizice](https://www.bancatransilvania.ro/files/app/media/Taxe-si-comisioane/Persoane-fizice.pdf)\n3. [BT Abonamente cont curent](https://www.bancatransilvania.ro/conturi-si-operatiuni/conturi/abonament-cont-curent)"
example_plain = "https://www.bancatransilvania.ro/brosura-comisioane, BT Taxe și comisioane (actualizate 01.04.2026)\nhttps://www.bancatransilvania.ro/files/app/media/Taxe-si-comisioane/Persoane-fizice.pdf, BT PDF Comisioane persoane fizice\nhttps://www.bancatransilvania.ro/conturi-si-operatiuni/conturi/abonament-cont-curent, BT Abonamente cont curent"

if input_mode == "Markdown":
    user_input = st.text_area("Paste your links below:", value=example_md, height=200)
else:
    user_input = st.text_area("Paste your links below:", value=example_plain, height=200)

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
            else:
                if "," in line:
                    url, name = line.split(",", 1)
                    parsed_items.append((url.strip(), name.strip()))
                else:
                    parsed_items.append((line, "Unknown Name"))
        
        if parsed_items:
            with st.spinner(f"Processing {len(parsed_items)} links... This might take a minute or two."):
                try:
                    # Pass the timezone string into the generator function
                    zip_data = generate_bulk_pdfs(parsed_items, selected_tz_string)
                    st.success("Done! All webpages have been converted to PDF.")
                    
                    # Also use the correct timezone for the final ZIP file name
                    export_date = datetime.now(pytz.timezone(selected_tz_string)).strftime('%Y-%m-%d_%H-%M')
                    export_filename = f"PDF_Export_{export_date}.zip"
                    
                    st.download_button(label="📦 Download ZIP with all PDFs", data=zip_data, file_name=export_filename, mime="application/zip")
                except Exception as e:
                    st.error(f"A critical error occurred: {e}")
        else:
            st.warning("No valid links found.")
    else:
        st.warning("Please enter at least one link.")
