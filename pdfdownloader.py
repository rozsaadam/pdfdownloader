import streamlit as st
import base64
import time
import io
import zipfile
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

    driver = webdriver.Chrome(options=chrome_options)

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
    // Re-enable scrolling just in case the cookie banner locked the page
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
                time.sleep(4)  # Wait for page layout and images to load

                # Execute the JS to wipe away cookie popups
                try:
                    driver.execute_script(hide_cookies_js)
                    time.sleep(1)  # Brief pause to let the DOM update
                except Exception:
                    pass  # If JS fails for some reason on a specific site, keep going

                print_options = PrintOptions()
                print_options.background = True

                pdf_base64 = driver.print_page(print_options)
                pdf_bytes = base64.b64decode(pdf_base64)

                clean_name = name if name else "Website"
                file_name = f"{index} {current_datetime} - {clean_name}.pdf"

                zip_file.writestr(file_name, pdf_bytes)
    finally:
        driver.quit()

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


# --- 2. Streamlit User Interface ---
st.set_page_config(page_title="Bulk Website to PDF", page_icon="🗂️")

st.title("🗂️ Bulk Website to PDF Converter")
st.write("Paste your links and the desired file names. **One format per row, separated by a comma.**")

example_text = """https://n26.com/en-eu/plans, Plans
https://n26.com/en-eu/mastercard, Mastercard
https://n26.com/en-eu/free-bank-account, Free Bank Account"""

user_input = st.text_area("Links and File Names", value=example_text, height=150)

if st.button("Generate PDF Archive", type="primary"):
    if user_input.strip():
        lines = user_input.strip().split('\n')
        parsed_items = []

        for line in lines:
            if "," in line:
                url, name = line.split(",", 1)
                parsed_items.append((url, name))
            else:
                parsed_items.append((line, "Unknown Name"))

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
        st.warning("Please enter at least one link.")
