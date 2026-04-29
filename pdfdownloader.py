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
    # 'eager' means Selenium won't wait for slow tracking scripts to finish loading
    chrome_options.page_load_strategy = 'eager' 
    
    # --- STEALTH SETTINGS ---
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Don't let a single broken page hang the entire app
    driver.set_page_load_timeout(30)
    
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
                
                # Sanitize name to prevent file path errors inside the ZIP
                clean_name = re.sub(r'[\\/*?:"<>|]', "", name) if name else "Website"
                file_name = f"{index} {current_datetime} - {clean_name}.pdf"
                
                try:
                    # --- LOGIC: Stealth JavaScript Fetch for direct PDF files ---
                    if parsed_url.path.lower().endswith('.pdf'):
                        root_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
                        driver.get(root_url)
                        time.sleep(4)
                        
                        fetch_js = """
                        var pdf_url = arguments[0];
                        var done = arguments[1];
                        fetch(pdf_url)
                            .then(response => {
                                if (!response.ok) throw new Error("HTTP " + response.status);
                                return response.blob();
                            })
                            .then(blob => {
                                var reader = new FileReader();
                                reader.onloadend = function() { done(reader.result); }
                                reader.readAsDataURL(blob);
                            })
                            .catch(err => done('ERROR: ' + err.
