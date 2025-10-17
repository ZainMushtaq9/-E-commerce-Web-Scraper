import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import base64
import json

def scrape_data(url):
    """
    Scrapes product data from a given URL using a three-stage process:
    1. Intelligent Script Tag Parsing (for modern JS-heavy sites)
    2. Specific CSS Selectors (for traditional sites)
    3. Generic Fallback (as a last resort)
    """
    if not url:
        return None, "Please enter a URL to start scraping."

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching URL: {e}"

    page_soup = BeautifulSoup(response.text, "html.parser")
    scraped_data = []

    # Check for blocking pages
    if "captcha" in page_soup.title.string.lower() or "robot" in page_soup.title.string.lower():
        return None, "Scraping failed. The website is blocking the request with a CAPTCHA. Try again later or from a different network."

    # --- STRATEGY 1: Intelligent Script Tag Parsing ---
    st.info("Attempting scrape with intelligent script parsing...")
    scripts = page_soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if data.get('@type') == 'ItemList' and 'itemListElement' in data:
                for item in data['itemListElement']:
                    product = item.get('item', {})
                    name = product.get('name')
                    offers = product.get('offers', {})
                    price = offers.get('price')
                    rating_value = product.get('aggregateRating', {}).get('ratingValue')

                    if name and price:
                        scraped_data.append({
                            "Product_Name": name,
                            "Price (₹)": price,
                            "Rating": rating_value or "N/A"
                        })
        except (json.JSONDecodeError, KeyError):
            continue

    # --- STRATEGY 2: Use Specific, Known CSS Selectors ---
    if not scraped_data:
        st.warning("Intelligent parsing failed. Switching to specific CSS selectors...")
        potential_container_classes = ["_1AtVbE", "_2kHMtA", "_4ddWXP", "_1xHGtK _373qXS", "_13oc-S", "cPHDOP", "_1YokD2"]
        containers = []
        for class_name in potential_container_classes:
            found_containers = page_soup.findAll("div", class_=class_name)
            if found_containers:
                containers = found_containers
                break

        if containers:
            for container in containers:
                product_name_tag = container.find("div", {"class": "_4rR01T"}) or container.find("a", {"class": "s1Q9rs"}) or container.find("a", {"class": "IRpwTa"})
                price_tag = container.find("div", {"class": "_30jeq3 _1_WHN1"}) or container.find("div", {"class": "_30jeq3"})
                rating_tag = container.find("div", {"class": "_3LWZlK"})

                if product_name_tag and price_tag:
                    product_name = product_name_tag.text.strip()
                    price_match = re.search(r'[\d,]+', price_tag.text)
                    price = price_match.group(0) if price_match else "N/A"
                    rating = rating_tag.text.strip() if rating_tag else "N/A"
                    scraped_data.append({"Product_Name": product_name, "Price (₹)": price, "Rating": rating})

    # --- STRATEGY 3: Generic Fallback Method ---
    if not scraped_data:
        st.warning("Specific selectors failed. Switching to generic fallback strategy...")
        possible_products = page_soup.find_all('a')
        for product_link in possible_products:
            img_tag = product_link.find('img')
            price_text = product_link.find(string=re.compile(r'₹|\$|€'))

            if img_tag and price_text and img_tag.get('alt'):
                product_name = img_tag.get('alt', '').strip()
                price_match = re.search(r'[\d,]+', price_text)
                price = price_match.group(0) if price_match else "N/A"
                rating_tag = product_link.find(string=re.compile(r'\d\.\d'))
                rating = rating_tag.strip() if rating_tag else "N/A"

                if not any(d['Product_Name'] == product_name for d in scraped_data):
                     scraped_data.append({"Product_Name": product_name, "Price (₹)": price, "Rating": rating})


    if not scraped_data:
        return None, "All scraping methods failed. The website's structure is too complex or it's actively blocking script access."
    
    progress_bar = st.progress(0)
    df = pd.DataFrame(scraped_data)
    for i in range(100):
        progress_bar.progress(i + 1)

    return df, "Scraping successful!"


def get_table_download_link(df):
    """Generates a link allowing the data in a given pandas dataframe to be downloaded"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="scraped_products.csv" style="display: inline-block; padding: 8px 16px; background-color: #4CAF50; color: white; text-align: center; text-decoration: none; border-radius: 20px; font-weight: bold;">Download CSV File</a>'
    return href

# --- Streamlit App UI ---

st.set_page_config(page_title="Web Scraper", page_icon="🕸️", layout="wide")

# Custom CSS for a better look
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
    }
    .stButton > button {
        border-radius: 20px;
        border: 1px solid #4CAF50;
        color: #4CAF50;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #4CAF50;
        color: white;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


st.title("🛍️ E-commerce Web Scraper")
st.markdown("Enter a URL from an e-commerce site to scrape product names, prices, and ratings.")

# URL input
url = st.text_input("Enter URL", "https://www.flipkart.com/search?q=samsung+mobiles")

# Scrape button
if st.button("Scrape Data"):
    with st.spinner('Scraping in progress...'):
        df, message = scrape_data(url)

    st.info(message)
    
    if df is not None and not df.empty:
        st.success(f"Successfully scraped {len(df)} products!")
        st.dataframe(df)
        st.markdown(get_table_download_link(df), unsafe_allow_html=True)
    elif df is not None:
        st.warning("Scraping finished, but no data was extracted. Please check the URL and the website structure.")

