import streamlit as st
import asyncio
import sys
import pandas as pd
import time
import re
import io 

# --- WINDOWS COMPATIBILITY FIX ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.sync_api import sync_playwright

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="G-Maps Pro", page_icon="🚀", layout="wide")

# --- MAIN TITLE ---
st.title("🚀 G-Maps Pro: B2B Lead Engine")
st.markdown("Professional tool to extract verified business data. Exports directly to **Excel**.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("🔍 Search Parameters")
keyword = st.sidebar.text_input("Industry / Keyword", "Coffee Shop")
location = st.sidebar.text_input("Location", "London, UK")
limit = st.sidebar.number_input("Max Results", min_value=1, max_value=500, value=20)
headless_mode = st.sidebar.checkbox("Headless Mode (Fast)", value=False)

st.sidebar.divider()

# --- HELPER FUNCTION (RATING) ---
def extract_rating(text):
    if not text: return 0.0
    match = re.search(r"(\d+([.,]\d+)?)", text)
    if match:
        number_str = match.group(1)
        return float(number_str.replace(',', '.'))
    return 0.0

# --- CORE SCRAPER LOGIC ---
def scrape_google_maps(search_term, max_results, status_placeholder, progress_bar):
    data_list = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless_mode)
        page = browser.new_page()
        
        try:
            status_placeholder.info("🚀 Launching Engine...")
            page.goto("https://www.google.com/maps", timeout=60000)
            
            try:
                page.locator("button[aria-label='Accept all']").click(timeout=3000)
            except:
                pass

            status_placeholder.info(f"🔎 Analyzing Map for: **{search_term}**...")
            page.wait_for_selector("input#searchboxinput")
            page.fill("input#searchboxinput", search_term)
            page.keyboard.press("Enter")
            
            page.wait_for_selector('div[role="feed"]', timeout=15000)
            
            # --- SCROLLING ---
            status_placeholder.info("📜 Scanning Area & Scrolling...")
            page.hover('div[role="feed"]')
            
            last_count = 0
            loop_safety = 0
            
            while True:
                page.mouse.wheel(0, 5000)
                time.sleep(2)
                
                current_listings = page.locator('div[role="article"]').all()
                count = len(current_listings)
                
                status_placeholder.info(f"⚡ Leads Found: **{count}**...")
                
                if count >= max_results:
                    break
                
                if count == last_count:
                    loop_safety += 1
                    if loop_safety > 3: break
                else:
                    loop_safety = 0
                
                last_count = count
            
            # --- EXTRACTION ---
            status_placeholder.info("⚙️ Extracting Data Points...")
            progress_bar.progress(0)
            
            listings = page.locator('div[role="article"]').all()
            final_count = min(len(listings), max_results)
            
            for i, listing in enumerate(listings[:final_count]):
                item = {}
                try:
                    listing.click()
                    time.sleep(0.5)
                    
                    item['Business Name'] = listing.get_attribute("aria-label") or "N/A"
                    
                    try:
                        info_text = listing.locator('span[role="img"]').first.get_attribute("aria-label")
                        item['Rating'] = extract_rating(info_text)
                    except:
                        item['Rating'] = 0.0
                    
                    try:
                        item['Map Link'] = listing.locator("a").first.get_attribute("href")
                    except:
                        item['Map Link'] = ""
                        
                    data_list.append(item)
                    
                except:
                    continue
                
                percent = int((i + 1) / final_count * 100)
                progress_bar.progress(percent)
            
            browser.close()
            return data_list

        except Exception as e:
            status_placeholder.error(f"Error: {e}")
            browser.close()
            return []

# --- MAIN LAYOUT ---
status_area = st.empty()
progress_area = st.empty()

# --- START BUTTON ---
if st.sidebar.button("🚀 Start Engine", type="primary"):
    full_query = f"{keyword} in {location}"
    st.session_state['results'] = scrape_google_maps(full_query, limit, status_area, progress_area)
    status_area.success("Extraction Completed Successfully! ✅")
    time.sleep(1)
    progress_area.empty()

# --- RESULTS DISPLAY ---
if 'results' in st.session_state and st.session_state['results']:
    df = pd.DataFrame(st.session_state['results'])
    
    st.divider()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"✅ Generated Leads ({len(df)})")
    with col2:
        sort_by = st.selectbox("Sort By:", ["Default Order", "Highest Rating ⭐"])

    if sort_by == "Highest Rating ⭐":
        df = df.sort_values(by="Rating", ascending=False)
    
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Map Link": st.column_config.LinkColumn("Google Maps Link"),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐")
        },
        hide_index=True
    )
    
    # --- EXCEL DOWNLOAD 
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Leads')
    
    st.download_button(
        label="📥 Download Excel Report (.xlsx)",
        data=buffer.getvalue(),
        file_name='B2B_Leads.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

elif 'results' not in st.session_state:
    status_area.info("👈 Enter target details in the sidebar and click **Start Engine**.")