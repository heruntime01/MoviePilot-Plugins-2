
from typing import List, Dict, Optional
from .base import SearchProvider
from urllib.parse import quote

class AiPanProvider(SearchProvider):
    name = 'aipan'
    def search(self, query: str, media_type: str, year: Optional[int]=None) -> List[Dict]:
        urls = [
            f'https://www.aipan.me/search?q={quote(query)}',
            f'https://aipan.me/search?q={quote(query)}',
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
        items = self.extract_items_with_titles(html)
        if items:
            return [{"title": t or query, "url": u, "provider": self.name, "score": 0} for (u,t) in items]
        links = self.extract_115(html)
        return [{"title": query, "url": u, "provider": self.name, "score": 0} for u in links]
