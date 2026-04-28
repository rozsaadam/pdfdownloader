# 🗂️ Bulk Website to PDF Converter

A Streamlit web application that allows you to bulk-convert web pages into nicely formatted PDF documents. It uses Selenium to properly render JavaScript-heavy websites and automatically hides annoying cookie banners before generating the PDFs.

Access the application here: https://pdfdownloader.streamlit.app/

## ✨ Features
- **Bulk Processing**: Paste a list of URLs and let the app process them all at once.
- **Custom File Names**: Define the exact output name for each PDF.
- **Smart Rendering**: Waits for images and layouts to load before printing.
- **Cookie Banner Removal**: Automatically detects and hides common cookie consent banners so they don't block your PDF content.
- **ZIP Export**: Packages all generated PDFs into a single, easy-to-download `.zip` archive.

## 🛠️ Prerequisites
- Python 3.8 or higher
- Google Chrome installed on your machine (Selenium requires it to run in the background)

## 🚀 Installation & Setup

1. Clone this repository or place the `pdfdownloader.py` file in your project folder.
2. Open your terminal (or PyCharm terminal) and install the required Python libraries:
   ```bash
   pip install streamlit selenium
