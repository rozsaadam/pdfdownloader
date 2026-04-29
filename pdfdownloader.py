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
    
    # Flattened JS to prevent triple-quote copy-paste errors
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
                        
                        # Flattened JS to prevent triple-quote copy-paste errors
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
                            pdf_bytes = base64.b64decode(b64_data
