
import re
from typing import List, Dict
from .base import SearchProvider

class AiPanProvider(SearchProvider):
    name = 'aipan'
    def search(self, query: str, media_type: str, year: int|None=None) -> List[Dict]:
        opener = self._build_opener()
        # aipan search endpoints vary; try common pattern
        urls = [
            f'https://www.aipan.me/search?q={__import__("urllib.parse").parse.quote(query)}',
            f'https://aipan.me/search?q={__import__("urllib.parse").parse.quote(query)}',
        ]
        html = ''
        for url in urls:
            try:
                req = __import__('urllib.request').request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
                with opener.open(req, timeout=self.timeout) as resp:
                    html = resp.read().decode('utf-8','ignore')
                    if html:
                        break
            except Exception:
                continue
        if not html:
            return []
        links = self.extract_115(html)
        return [{"title": query, "url": u, "provider": self.name, "score": 0} for u in links]
