
from typing import List, Dict
import json

def _fetch(url: str) -> dict|None:
    try:
        import urllib.request as ur
        opener = ur.build_opener()
        req = ur.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://m.douban.com/'})
        with opener.open(req, timeout=12) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

COLL = {
  'movie': 'movie_hot_gaia',
  'tv': 'tv_hot',
}

def hot(kind: str='tv', start: int=0, count: int=20) -> List[Dict]:
    coll = COLL.get(kind, 'tv_hot')
    url = f'https://m.douban.com/rexxar/api/v2/subject_collection/{coll}/items?start={start}&count={count}'
    data = _fetch(url)
    out: List[Dict] = []
    for it in (data or {}).get('subject_collection_items', []):
        title = it.get('title') or it.get('name')
        year = None
        ysrc = (it.get('year') or '')
        try:
            year = int(str(ysrc)[:4]) if ysrc else None
        except Exception:
            year = None
        out.append({'title': title, 'year': year, 'douban_id': it.get('id') or it.get('id_str'), 'source': 'douban'})
    return out
