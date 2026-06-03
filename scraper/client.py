import requests

API_URL = "https://xivpf.com/api/listings"
HEADERS = {"User-Agent": "xivpf-scraper/1.0 (github study project)"}


class XivpfClient:
    def fetch_listings(self) -> list[dict]:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
