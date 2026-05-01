"""Shared utilities for all HKJC scrapers (Traditional Chinese pages)."""
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

CHROMIUM_PATH = os.environ.get(
    "CHROMIUM_PATH",
    "/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium",
)
CHROMEDRIVER_PATH = os.environ.get(
    "CHROMEDRIVER_PATH",
    "/nix/store/8zj50jw4w0hby47167kqqsaqw4mm5bkd-chromedriver-unwrapped-138.0.7204.100/bin/chromedriver",
)

MAX_RETRIES = 3
PAGE_TIMEOUT = 30

# UA spoof — HKJC serves a JS-shell (0 data rows) when it sees `HeadlessChrome/`
# in the UA. Stripping that substring and presenting a vanilla desktop Chrome UA
# gets us the full server-rendered page. Verified 2026-05-01:
#   curl -A "Mozilla/5.0 HeadlessChrome/147.0.0.0" -L <trackwork_url>  → ~4 日期 matches (shell only)
#   curl -A "Mozilla/5.0"                          -L <trackwork_url>  → 1086 data rows
# This restored ~1000 empty trackwork CSVs that had been stuck at 65B header-only.
SPOOF_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)


def make_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    # Anti-bot avoidance: override default UA (hides HeadlessChrome signal) +
    # disable the `AutomationControlled` blink feature which sets
    # navigator.webdriver=true. Both are standard detection signals.
    opts.add_argument(f"--user-agent={SPOOF_UA}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.binary_location = CHROMIUM_PATH
    from selenium.webdriver.chrome.service import Service as ChromeService
    driver = webdriver.Chrome(
        service=ChromeService(executable_path=CHROMEDRIVER_PATH),
        options=opts
    )
    # Post-init: clobber navigator.webdriver via CDP for extra safety against
    # JS-side detection. Covers servers that check `navigator.webdriver` after
    # page load rather than just the UA string.
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
        )
    except Exception:
        pass
    return driver


def load_page(driver, url, timeout=PAGE_TIMEOUT, retries=MAX_RETRIES):
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return True
        except Exception as e:
            print(f"  Load failed attempt {attempt}/{retries} for {url}: {type(e).__name__}: {e}")
            if attempt < retries:
                time.sleep(3)
    return False


def safe_cell(cells, index, default=""):
    try:
        return cells[index].text.strip()
    except (IndexError, Exception):
        return default


def log_failed(logfile, entity_id, reason=""):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(logfile, "a") as f:
        f.write(f"{entity_id}  # {reason}  [{ts}]\n")


def parse_zh_location(raw):
    """
    Parse a Traditional Chinese location string into (racecourse, track, course).

    Examples:
      '沙田草地"A"'        -> ('沙田', '草地', 'A')
      '跑馬地草地"A"'      -> ('跑馬地', '草地', 'A')
      '沙田全天候跑道'      -> ('沙田', '全天候跑道', '')
      '草地"C"'            -> ('', '草地', 'C')
      '沙地跑道'           -> ('', '沙地跑道', '')
    """
    raw = raw.strip()
    m = re.match(
        r'^(沙田|跑馬地)?(草地|全天候跑道|沙地跑道|沙地|泥地)"?([^"]*)"?$',
        raw
    )
    if m:
        racecourse = m.group(1) or ""
        track = m.group(2) or ""
        course = m.group(3).strip('"').strip() if m.group(3) else ""
        return racecourse, track, course
    return raw, "", ""
