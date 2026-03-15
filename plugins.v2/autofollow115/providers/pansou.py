
import re
from typing import List, Dict
from .base import SearchProvider

class PanSouProvider(SearchProvider):
    name = 'pansou'
    def search(self, query: str, media_type: str, year: int|None=None) -> List[Dict]:
        # pansou: simple GET
        opener = self._build_opener()
        url = f'https://www.pansou.com/?q={__import__("urllib.parse").parse.quote(query)}'
        try:
            req = __import__('urllib.request').request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with opener.open(req, timeout=self.timeout) as resp:
                html = resp.read().decode('utf-8','ignore')
        except Exception:
            return []
        links = self.extract_115(html)
        return [{"title": query, "url": u, "provider": self.name, "score": 0} for u in links]
