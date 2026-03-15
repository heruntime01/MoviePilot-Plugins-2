
import time
import re
from typing import List, Dict, Optional, Tuple
import html as _html

class SearchProvider:
    name = 'base'
    def __init__(self, proxy: Optional[str]=None, timeout: int=12, retries: int=2, backoff: float=0.8):
        self.proxy = proxy
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def _build_opener(self):
        import urllib.request as ur
        handlers = []
        if self.proxy:
            handlers.append(ur.ProxyHandler({'http': self.proxy, 'https': self.proxy}))
        return ur.build_opener(*handlers)

    def _get_html(self, url: str, headers: Optional[Dict[str,str]]=None) -> str:
        import urllib.request as ur
        opener = self._build_opener()
        hdrs = {'User-Agent':'Mozilla/5.0'}
        if headers:
            hdrs.update(headers)
        last_exc = None
        for i in range(self.retries+1):
            try:
                req = ur.Request(url, headers=hdrs)
                with opener.open(req, timeout=self.timeout) as resp:
                    return resp.read().decode('utf-8','ignore')
            except Exception as e:
                last_exc = e
                if i < self.retries:
                    time.sleep(self.backoff * (2**i))
        raise last_exc

    @staticmethod
    def extract_115(text: str) -> List[str]:
        pat = r"https?://115\\.com/(?:s|f)/[A-Za-z0-9]+"
        return list({m.group(0) for m in re.finditer(pat, text)})

    @staticmethod
    def extract_items_with_titles(html: str) -> List[Tuple[str,str]]:
        items: List[Tuple[str,str]] = []
        # Try capture <a href="115...">anchor text</a>
        for m in re.finditer(r'<a[^>]+href=[\"\'](https?://115\\.com/(?:s|f)/[A-Za-z0-9]+)[\"\'][^>]*>(.*?)</a>', html, re.IGNORECASE|re.DOTALL):
            url = m.group(1)
            text = _html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2))).strip()
            if text:
                items.append((url, text))
        # Fallback: around raw links, take preceding 80 chars as context
        if not items:
            for m in re.finditer(r"(.{0,80})(https?://115\\.com/(?:s|f)/[A-Za-z0-9]+)", html, re.IGNORECASE|re.DOTALL):
                url = m.group(2)
                ctx = _html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip()
                title = ctx[-60:].strip()
                if title:
                    items.append((url, title))
        # Dedup by url, keep first non-empty title
        seen = set(); out: List[Tuple[str,str]] = []
        for url, t in items:
            if url in seen:
                continue
            seen.add(url)
            out.append((url, t))
        return out

    def search(self, query: str, media_type: str, year: Optional[int]=None) -> List[Dict]:
        return []
