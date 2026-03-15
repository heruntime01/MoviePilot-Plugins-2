
from typing import List, Dict, Optional
from urllib.parse import quote
from .base import SearchProvider

class NullBRProvider(SearchProvider):
    name = 'nullbr'
    def __init__(self, base: Optional[str]=None, **kwargs):
        super().__init__(**kwargs)
        self.base = (base or '').rstrip('/')

    def search(self, query: str, media_type: str, year: Optional[int]=None) -> List[Dict]:
        # base must be provided by config, e.g. https://nullbr.example
        if not self.base:
            return []
        urls = [
            f"{self.base}/search?q={quote(query)}",
            f"{self.base}/?s={quote(query)}",
        ]
        html = ''
        for url in urls:
            try:
                html = self._get_html(url)
                if html:
                    break
            except Exception:
                continue
        if not html:
            return []
        links = self.extract_115(html)
        return [{"title": query, "url": u, "provider": self.name, "score": 0} for u in links]
