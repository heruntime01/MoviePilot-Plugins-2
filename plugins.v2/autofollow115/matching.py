
import re

def normalize(t: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5]+", " ", t or '').strip().lower()

PREF_KEYWORDS = [
  ('pack', [r'全集', r'全季', r'全\s*集', r'合集', r'全\s*套', r'complete', r'all\s*episodes', r'S\d{1,2}\s*complete']),
  ('quality', [r'2160p', r'4k', r'uhd', r'dolby', r'dolby\s*vision', r'hdr10', r'hdr', r'dv', r'hevc', r'x265', r'h265', r'webrip', r'web-dl', r'bluray', r'remux', r'ddp', r'atmos', r'nf', r'amzn']),
  ('subs', [r'中字', r'中英', r'简英', r'双语', r'官中', r'官方中字', r'熟肉', r'内嵌', r'内封']),
  ('season', [r'S\d{1,2}', r'Season\s*\d+']),
  ('episode', [r'E\d{1,3}', r'EP?\d{1,3}'])
]

WEIGHTS = {
  'pack': 14,
  'quality': 6,
  'subs': 8,
  'season': 3,
  'episode': 2,
}

def score(title: str) -> int:
    t = (title or '').lower()
    s = 0
    for cat, kws in PREF_KEYWORDS:
        w = WEIGHTS.get(cat, 5)
        for k in kws:
            if re.search(k, t, re.IGNORECASE):
                s += w
    return s

def good_enough(title: str, year: int|None, prefer_pack: bool=True) -> bool:
    t = (title or '').lower()
    if prefer_pack and re.search(r'(全集|全季|全\s*集|合集|complete)', t):
        return True
    return True
