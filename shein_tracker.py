from playwright.sync_api import sync_playwright
import json
import os
import requests
import time

# =========================================
# CONFIG
# =========================================

URL = "https://www.sheinindia.in/s/footwear-201712"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

DB_FILE = "seen_products.json"

# =========================================
# TELEGRAM
# =========================================

def send_telegram(message):

    telegram_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(
            telegram_url,
            data=data,
            timeout=30
        )

    except Exception as e:
        print("Telegram Error:", e)

# =========================================
# LOAD OLD PRODUCTS
# =========================================

def load_seen_products():

    if not os.path.exists(DB_FILE):
        return []

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return []

# =========================================
# SAVE PRODUCTS
# =========================================

def save_products(products):

    with open(DB_FILE, "w", encoding="utf-8") as f:

        json.dump(
            products,
            f,
            indent=2,
            ensure_ascii=False
        )

# =========================================
# SCRAPE PRODUCTS
# =========================================

def scrape_products():

    products = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        print("Opening SHEIN page...")

        page.goto(
            URL,
            timeout=120000,
            wait_until="domcontentloaded"
        )

        # wait for products
        page.wait_for_timeout(10000)

        # scroll slowly
        for i in range(5):

            print(f"Scrolling {i+1}/5")

            page.mouse.wheel(0, 4000)

            page.wait_for_timeout(2500)

        print("Collecting products...")

        imgs = page.locator("img").all()

        print("Total images found:", len(imgs))

        for img in imgs:

            try:

                src = img.get_attribute("src")

                if not src:
                    continue

                # detect product images
                if (
                    "medias" in src
                    or "root1" in src
                ):

                    parent = img.locator(
                        "xpath=ancestor::a[1]"
                    )

                    href = parent.get_attribute("href")

                    if not href:
                        continue

                    text = parent.inner_text().strip()

                    full_url = (
                        "https://www.sheinindia.in"
                        + href
                    )

                    product_id = href.split("/p/")[-1]

                    # clean text
                    lines = [
                        x.strip()
                        for x in text.splitlines()
                        if x.strip()
                    ]

                    clean_text = "\n".join(lines)

                    product = {
                        "id": product_id,
                        "url": full_url,
                        "text": clean_text,
                        "image": src
                    }

                    products.append(product)

            except Exception as e:

                print("ERROR:", e)

        browser.close()

    # remove duplicates
    unique = {}

    for p in products:
        unique[p["id"]] = p

    return list(unique.values())

# =========================================
# MAIN
# =========================================

def main():

    print("=" * 60)
    print("SHEIN PRODUCT TRACKER")
    print("=" * 60)

    old_products = load_seen_products()

    old_ids = set(
        p["id"] for p in old_products
    )

    print("Old products:", len(old_ids))

    products = scrape_products()

    print("\nProducts scraped:", len(products))

    new_products = []

    for p in products:

        if p["id"] not in old_ids:
            new_products.append(p)

    print("New products found:", len(new_products))

    # send notifications
    for p in new_products:

        message = (
            f"🆕 NEW SHEIN PRODUCT\n\n"
            f"{p['text']}\n\n"
            f"{p['url']}"
        )

        print("\nSENDING:")
        print(message)

        send_telegram(message)

        time.sleep(2)

    # save latest products
    save_products(products)

    print("\nDone")
    print("=" * 60)

# =========================================
# START
# =========================================

if __name__ == "__main__":
    main()