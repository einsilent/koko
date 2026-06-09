#!/usr/bin/env python3
"""
電商商品上架監控 - 女神異聞錄4R 豪華版
GitHub Actions 版（單次執行，由 Actions 排程呼叫）
"""

import os
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

# ===== 從環境變數讀取（GitHub Secrets）=====
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

KEYWORD = "女神異聞錄4R 豪華版"
KEYWORD_SHORT = "女神異聞錄4R"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.json().get("ok", False)
    except Exception as e:
        print(f"[Telegram] 發送失敗: {e}")
        return False


def is_target(text: str) -> bool:
    text = text.lower()
    has_game = "女神異聞錄" in text or "persona 4" in text or "p4r" in text
    has_deluxe = "豪華" in text or "deluxe" in text
    return has_game and has_deluxe


def check_books():
    kw = requests.utils.quote(KEYWORD)
    url = f"https://search.books.com.tw/search/query/key/{kw}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.select("li.item, .searchbook li, ul.searchbook > li"):
            el = item.find(class_=re.compile("msg|title|name", re.I)) or item.find("h4") or item.find("h3")
            if el and is_target(el.get_text()):
                a = item.find("a", href=True)
                return True, a["href"] if a else url
        return False, None
    except Exception as e:
        print(f"[博客來] 錯誤: {e}")
        return None, None


def check_momo():
    kw = requests.utils.quote(KEYWORD)
    url = f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={kw}&searchType=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.select("li.goodsItemLi, [class*='goodsItem']"):
            el = item.find(class_=re.compile("goodsName|name|title", re.I)) or item.find("h3")
            if el and is_target(el.get_text()):
                a = item.find("a", href=True)
                href = a["href"] if a else url
                if href.startswith("/"):
                    href = "https://www.momoshop.com.tw" + href
                return True, href
        return False, None
    except Exception as e:
        print(f"[momo] 錯誤: {e}")
        return None, None


def check_bahamut():
    kw = requests.utils.quote(KEYWORD)
    url = f"https://mall.gamer.com.tw/search?q={kw}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.select(".product-item, [class*='product'], .item-block"):
            el = item.find(class_=re.compile("title|name", re.I)) or item.find("h3")
            if el and is_target(el.get_text()):
                a = item.find("a", href=True)
                href = a["href"] if a else url
                if href.startswith("/"):
                    href = "https://mall.gamer.com.tw" + href
                return True, href
        return False, None
    except Exception as e:
        print(f"[巴哈] 錯誤: {e}")
        return None, None


def check_pchome():
    kw = requests.utils.quote(KEYWORD_SHORT)
    api_url = (
        f"https://ecapi.pchome.com.tw/cdn/ecshop/cate_prod/v8/search?"
        f"q={kw}&fields=Id,Nick,Price&offset=0&limit=20&sort=sale/dc"
    )
    fallback = f"https://24h.pchome.com.tw/search/#/q={kw}"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        data = r.json()
        prods = data if isinstance(data, list) else data.get("Prods", [])
        for prod in prods:
            if is_target(prod.get("Nick", "")):
                pid = prod.get("Id", "")
                return True, f"https://24h.pchome.com.tw/prod/{pid}"
        return False, None
    except Exception as e:
        print(f"[PChome] 錯誤: {e}")
        return None, None


def check_yahoo():
    kw = requests.utils.quote(KEYWORD)
    url = f"https://tw.buy.yahoo.com/search/product?p={kw}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.select("[class*='product'], [class*='item'], li[data-pid]"):
            el = item.find(class_=re.compile("title|name", re.I)) or item.find("h3")
            if el and is_target(el.get_text()):
                a = item.find("a", href=True)
                return True, a["href"] if a else url
        return False, None
    except Exception as e:
        print(f"[Yahoo] 錯誤: {e}")
        return None, None


STORES = [
    ("博客來",       check_books,    f"https://search.books.com.tw/search/query/key/{requests.utils.quote(KEYWORD)}/"),
    ("momo 購物",   check_momo,     f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={requests.utils.quote(KEYWORD)}"),
    ("巴哈姆特商城", check_bahamut, f"https://mall.gamer.com.tw/search?q={requests.utils.quote(KEYWORD)}"),
    ("PChome 24h",  check_pchome,  f"https://24h.pchome.com.tw/search/#/q={requests.utils.quote(KEYWORD_SHORT)}"),
    ("Yahoo 商城",  check_yahoo,   f"https://tw.buy.yahoo.com/search/product?p={requests.utils.quote(KEYWORD)}"),
]


def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC+8")
    print(f"[{now}] 開始檢查：{KEYWORD}")

    found_stores = []

    for name, fn, search_url in STORES:
        found, link = fn()
        if found is True:
            print(f"  ✅ {name}: 找到！{link}")
            found_stores.append((name, link or search_url))
        elif found is False:
            print(f"  ❌ {name}: 未上架")
        else:
            print(f"  ⚠️  {name}: 抓取失敗")

    if found_stores:
        lines = "\n".join(f"🏪 {n}\n🔗 {l}" for n, l in found_stores)
        msg = (
            f"🎮 <b>女神異聞錄4R 豪華版 上架通知！</b>\n\n"
            f"{lines}\n\n"
            f"⏰ {now}\n\n"
            f"確認後請至 GitHub Actions 停用監控 ✋"
        )
        send_telegram(msg)
        print("Telegram 通知已發送！")
    else:
        print("本次未發現商品上架。")


if __name__ == "__main__":
    main()
