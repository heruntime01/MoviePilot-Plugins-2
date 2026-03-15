
import re, time
from typing import List, Dict

class SearchProvider:
    name = 'base'
    def __init__(self, proxy: str|None=None, timeout: int=12):
        self.proxy = proxy
        self.timeout = timeout

    def _build_opener(self):
        handlers = []
        if self.proxy:
            handlers.append(__import__('urllib.request').request.ProxyHandler({'http': self.proxy, 'https': self.proxy}))
        return __import__('urllib.request').request.build_opener(*handlers)

    def search(self, query: str, media_type: str, year: int|None=None) -> List[Dict]:
        return []

    @staticmethod
    def extract_115(text: str) -> List[str]:
        return list({m.group(0) for m in re.finditer(r"https?://115\.com/s/[A-Za-z0-9]+", text)})
