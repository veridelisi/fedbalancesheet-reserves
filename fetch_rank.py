"""
fetch_rank.py  —  Run by GitHub Actions every hour.
Fetches Amazon BSR for Money & Monetary Policy and appends to CSV.
"""

import csv
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

ASIN       = "B0G584KJ73"
URL        = f"https://www.amazon.com/dp/{ASIN}"
OUTPUT_CSV = Path("ranks_{}.csv".format(ASIN))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_rank() -> dict:
    result = {
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "rank": None,
        "status": "ok",
    }
    try:
        r = requests.get(URL, headers=HEADERS, timeout=15)
    except Exception as e:
        result["status"] = f"error: {e}"
        return result

    if r.status_code != 200:
        result["status"] = f"http_{r.status_code}"
        return result

    if "captcha" in r.text.lower():
        result["status"] = "captcha"
        return result

    soup = BeautifulSoup(r.text, "html.parser")
    bsr_text = ""

    for li in soup.select("#detailBulletsWrapper_feature_div li"):
        text = li.get_text(" ", strip=True)
        if "Best Sellers Rank" in text:
            bsr_text = text
            break

    if not bsr_text:
        for row in soup.select("#productDetails_db_sections tr, #prodDetails tr"):
            th, td = row.find("th"), row.find("td")
            if th and td and "Best Sellers Rank" in th.get_text():
                bsr_text = td.get_text(" ", strip=True)
                break

    if not bsr_text:
        result["status"] = "rank_not_found"
        return result

    m = re.search(r"#([\d,]+)\s+in Money & Monetary Policy", bsr_text)
    if m:
        result["rank"] = int(m.group(1).replace(",", ""))
    else:
        result["status"] = "rank_not_found"

    return result


def append_csv(row: dict):
    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fetched_at", "rank", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    result = fetch_rank()
    append_csv(result)
    print(f"[{result['fetched_at']}] rank={result['rank']}  status={result['status']}")