
from typing import Optional
import re

# Best-effort fetch of total episodes from Douban subject HTML (if id known)

def _get(url: str, proxy: Optional[str]=None, timeout: int=8) -> str:
    import urllib.request as ur
    opener = ur.build_opener()
    if proxy:
        opener = ur.build_opener(ur.ProxyHandler({'http':proxy,'https':proxy}))
    req = ur.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with opener.open(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8','ignore')


def total_episodes_from_douban(douban_id: str, proxy: Optional[str]=None) -> Optional[int]:
    if not douban_id:
        return None
    # Use desktop subject page for richer info
    url = f'https://movie.douban.com/subject/{douban_id}/'
    try:
        html = _get(url, proxy=proxy)
    except Exception:
        return None
    # Common patterns: 集数: 16 / 总集数：16 / 共16集
    for pat in [r'集数\s*[:：]\s*(\d{1,3})', r'总?集数\s*[:：]\s*(\d{1,3})', r'共\s*(\d{1,3})\s*集']:
        m = re.search(pat, html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None
