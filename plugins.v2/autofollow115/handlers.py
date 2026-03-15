# -*- coding: utf-8 -*-
import re, datetime
from typing import List
from urllib import request as _req

RE_115 = re.compile(r'https?://115\.com/(?:s|f)/[A-Za-z0-9]+', re.I)
RE_115_SHORT = re.compile(r'https?://115\.com/l/[A-Za-z0-9]+', re.I)

UA={'User-Agent':'Mozilla/5.0'}

def http_get(url: str, timeout: int = 15) -> str:
    req = _req.Request(url, headers=UA)
    with _req.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8','ignore')

def parse_rsshub_titles(xml_text: str, limit: int = 20) -> List[str]:
    titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', xml_text, re.I)
    out=[]
    for t1,t2 in titles[:limit]:
        t=(t1 or t2 or '').strip()
        if t and (not t.lower().startswith('rsshub')):
            out.append(t)
    return out

def search_links_pansou(keyword: str) -> List[str]:
    try:
        from urllib import parse as _parse
        url = 'https://www.pansou.vip/s/' + _parse.quote(keyword or '')
        html = http_get(url)
        ls = list(set(re.findall(RE_115, html) + re.findall(RE_115_SHORT, html)))
        return ls[:20]
    except Exception:
        return []

def search_links_aipan(keyword: str) -> List[str]:
    try:
        from urllib import parse as _parse
        url = 'https://www.aipan.me/search?k=' + _parse.quote(keyword or '')
        html = http_get(url)
        ls = list(set(re.findall(RE_115, html) + re.findall(RE_115_SHORT, html)))
        return ls[:20]
    except Exception:
        return []
