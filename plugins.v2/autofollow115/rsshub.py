
from typing import List, Dict, Optional
import re
import xml.etree.ElementTree as ET

try:
    from urllib.parse import urljoin
    import urllib.request as ur
except Exception:
    urljoin = None
    ur = None

# Generic RSS/Atom fetcher for RSSHub

def _fetch(url: str, proxy: Optional[str]=None, timeout: int=12) -> str:
    if ur is None:
        import urllib.request as _ur
        opener = _ur.build_opener()
    else:
        opener = ur.build_opener()
    if proxy:
        if ur is None:
            import urllib.request as _ur
            opener = _ur.build_opener(_ur.ProxyHandler({'http':proxy,'https':proxy}))
        else:
            opener = ur.build_opener(ur.ProxyHandler({'http':proxy,'https':proxy}))
    req = (ur.Request if ur else __import__('urllib.request').Request)(url, headers={'User-Agent':'Mozilla/5.0'})
    with opener.open(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8','ignore')


def parse_feed(xml_text: str) -> List[Dict]:
    items: List[Dict] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items
    # RSS: channel/item/title/link
    # Atom: feed/entry/title/link(@href)
    if root.tag.endswith('rss') or root.find('.//channel') is not None:
        for it in root.findall('.//item'):
            title = (it.findtext('title') or '').strip()
            link = (it.findtext('link') or '').strip()
            items.append({'title': title, 'link': link})
    else:
        # Atom
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        for it in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title = (it.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
            link_el = it.find('{http://www.w3.org/2005/Atom}link')
            href = link_el.get('href') if link_el is not None else ''
            items.append({'title': title, 'link': href})
    # extract year and douban id when possible
    for it in items:
        t = it.get('title') or ''
        y = None
        m = re.search(r'(19|20)\d{2}', t)
        if m:
            try:
                y = int(m.group(0))
            except Exception:
                y = None
        it['year'] = y
        link = it.get('link') or ''
        m2 = re.search(r'/subject/(\d+)', link)
        if m2:
            it['douban_id'] = m2.group(1)
    return items


def fetch_rsshub(base: str, paths: List[str], proxy: Optional[str]=None, timeout: int=12) -> List[Dict]:
    outs: List[Dict] = []
    base = base.rstrip('/') + '/'
    for p in paths or []:
        p = p.lstrip('/')
        url = base + p
        try:
            xml_text = _fetch(url, proxy=proxy, timeout=timeout)
            outs.extend(parse_feed(xml_text))
        except Exception:
            continue
    # dedup by (title, year, douban_id)
    seen = set()
    uniq: List[Dict] = []
    for it in outs:
        k = (it.get('title'), it.get('year'), it.get('douban_id'))
        if k in seen:
            continue
        seen.add(k)
        uniq.append({'title': it.get('title'), 'year': it.get('year'), 'douban_id': it.get('douban_id')})
    return uniq
