"""Check Naver keyword search volume via Search Ad API."""
import sys
import json
import time
import hashlib
import hmac
import base64
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, quote

sys.stdout.reconfigure(encoding="utf-8")

CUSTOMER_ID = "2009398"
API_KEY = "010000000063d7e87fde8ef8404610aa14fe366fa92cfbdbbccd14320a3645d982d984d502"
SECRET_KEY = "AQAAAABj1+h/3o74QEYQqhT+Nm+pyw8+oV5UvBohD/Qnoxqw3g=="
BASE_URL = "https://api.searchad.naver.com"


def get_signature(timestamp, method, uri):
    sign = f"{timestamp}.{method}.{uri}"
    return base64.b64encode(
        hmac.new(SECRET_KEY.encode("utf-8"), sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")


def main():
    keywords = [
        "뷰티샵 마케팅", "네일샵 홍보", "헤드스파 마케팅",
        "1인 카페 마케팅", "소상공인 마케팅", "블로그 대행",
        "인스타 대행", "SNS 마케팅 대행", "자영업 마케팅", "매장 홍보",
    ]

    uri = "/keywordstool"
    print(f"Querying {len(keywords)} keywords...")
    print()

    # Query one keyword at a time to avoid API limits
    all_items = []
    for kw in keywords:
        timestamp = str(int(time.time() * 1000))
        url = f"{BASE_URL}{uri}?hintKeywords={quote(kw)}&showDetail=1"
        headers = {
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-API-KEY": API_KEY,
            "X-Customer": CUSTOMER_ID,
            "X-Signature": get_signature(timestamp, "GET", uri),
        }
        req = Request(url, headers=headers)
        try:
            resp = urlopen(req)
            data = json.loads(resp.read().decode())
            all_items.extend(data.get("keywordList", []))
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"  [{kw}] Error {e.code}: {body[:100]}")
        time.sleep(0.3)

    data = {"keywordList": all_items}

    target = set(keywords)
    results = [item for item in data.get("keywordList", []) if item.get("relKeyword") in target]

    print(f"{'키워드':<20} {'월검색(PC)':>10} {'월검색(모바일)':>12} {'경쟁도':>8} {'PC클릭단가':>10}")
    print("-" * 66)

    for item in sorted(results, key=lambda x: x.get("monthlyMobileQcCnt", 0) if isinstance(x.get("monthlyMobileQcCnt"), int) else 0, reverse=True):
        kw = item["relKeyword"]
        pc = item.get("monthlyPcQcCnt", "< 10")
        mob = item.get("monthlyMobileQcCnt", "< 10")
        comp = item.get("compIdx", "-")
        cpc = item.get("monthlyAvePcCpc", "-")
        print(f"{kw:<20} {str(pc):>10} {str(mob):>12} {str(comp):>8} {str(cpc):>10}")

    # Related keywords
    related = [i for i in data.get("keywordList", []) if i["relKeyword"] not in target]
    related_sorted = sorted(related, key=lambda x: (x.get("monthlyMobileQcCnt", 0) if isinstance(x.get("monthlyMobileQcCnt"), int) else 0), reverse=True)

    print(f"\n\n=== 관련 추천 키워드 (검색량 높은 순 Top 20) ===")
    print(f"{'키워드':<24} {'월검색(PC)':>10} {'월검색(모바일)':>12} {'경쟁도':>8}")
    print("-" * 58)
    for item in related_sorted[:20]:
        kw = item["relKeyword"]
        pc = item.get("monthlyPcQcCnt", "< 10")
        mob = item.get("monthlyMobileQcCnt", "< 10")
        comp = item.get("compIdx", "-")
        print(f"{kw:<24} {str(pc):>10} {str(mob):>12} {str(comp):>8}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
