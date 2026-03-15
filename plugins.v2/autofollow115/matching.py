
import re

def normalize(t: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-龥]+", " ", t or '').strip().lower()

PREF_KEYWORDS = [
  ('pack', [r'全集', r'全季', r'全\s*集', r'S\d+\s*全', r'合集', r'全\s*套']),
  ('quality', [r'2160', r'4k', r'uhd', r'dolby', r'hdr10', r'hdr', r'dv', r'hevc', r'x265', r'h265', r'web-dl', r'remux'])
]

WEIGHTS = {
  'pack': 12,
  'quality': 5
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
    if prefer_pack and re.search(r'(全集|全季|全\s*集|合集)', t):
        return True
    return True
