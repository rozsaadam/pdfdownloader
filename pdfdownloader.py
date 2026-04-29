import streamlit as st
import base64
import time
import io
import zipfile
import re
from urllib.parse import urlparse
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
    
    # --- CRASH PREVENTION SETTINGS ---
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.page_load_strategy = 'eager' 
    
    # --- STEALTH SETTINGS ---
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    
    current_datetime = datetime.now().strftime("%d.%m.%Y %H.%M")
    zip_buffer = io.BytesIO()
    
    hide_cookies_js = (
        "const selectors = ['[id*=\"cookie\"]', '[class*=\"cookie\"]', '[id*=\"consent\"]', '[class*=\"consent\"]', "
        "'[id*=\"banner\"]', '[class*=\"banner\"]', '#onetrust-consent-sdk', '.osano-cm-window', '.trustarc-banner', '.optanon-alert-box-wrapper']; "
        "document.querySelectorAll(selectors.join(',')).forEach(el => { el.style.display = 'none'; }); "
        "document.body.style.overflow = 'auto';"
    )
    
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
                        
                        fetch_js = (
                            "var pdf_url = arguments[0]; var done = arguments[1]; "
                            "fetch(pdf_url).then(response => { if (!response.ok) throw new Error('HTTP ' + response.status); return response.blob(); }) "
                            ".then(blob => { var reader = new FileReader(); reader.onloadend = function() { done(reader.result); }; reader.readAsDataURL(blob); }) "
                            ".catch(err => done('ERROR: ' + err.message));"
                        )
                        
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

# --- 2. Streamlit User Interface ---
st.set_page_config(page_title="Bulk Website to PDF", page_icon="🗂️")

st.title("🗂️ Bulk Website to PDF Converter")

input_mode = st.radio(
    "Select Input Format", 
    ["Markdown", "Plain Text (URL, Name)"], 
    horizontal=True
)

if input_mode == "Markdown":
    example_text = (
        "1. [BT Taxe și comisioane (actualizate 01.04.2026)](https://www.bancatransilvania.ro/brosura-comisioane)\n"
        "2. [BT PDF Comisioane persoane fizice](https://www.bancatransilvania.ro/files/app/media/Taxe-si-comisioane/Persoane-fizice.pdf)\n"
        "3. [BT Abonamente cont curent](https://www.bancatransilvania.ro/conturi-si-operatiuni/conturi/abonament-cont-curent)"
    )
else:
    example_text = (
        "
