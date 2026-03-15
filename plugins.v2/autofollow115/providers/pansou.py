
from typing import List, Dict, Optional
from .base import SearchProvider
from urllib.parse import quote

class PanSouProvider(SearchProvider):
    name = 'pansou'
    def search(self, query: str, media_type: str, year: Optional[int]=None) -> List[Dict]:
        url = f'https://www.pansou.com/?q={quote(query)}'
        try:
            html = self._get_html(url)
        except Exception:
            return []
        items = self.extract_items_with_titles(html)
        if items:
            return [{"title": t or query, "url": u, "provider": self.name, "score": 0} for (u,t) in items]
        links = self.extract_115(html)
        return [{"title": query, "url": u, "provider": self.name, "score": 0} for u in links]
