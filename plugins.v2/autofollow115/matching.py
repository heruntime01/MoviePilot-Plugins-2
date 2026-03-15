
import re

def normalize(t: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-龥]+"," ", t or '').strip().lower()

PREF_KEYWORDS = [
  ('pack', ['全集','全季','全\s*集','S\d+ 全','合集','全\s*套']),
  ('quality', ['2160','4k','uhd','dolby','hdr10','hdr','dv','hevc','x265','h265','web-dl','remux']),
]

def score(title: str) -> int:
    t = title.lower()
    s = 0
    for _, kws in PREF_KEYWORDS:
        for k in kws:
            if re.search(k, t, re.IGNORECASE):
                s += 10
    return s

def good_enough(title: str, year: int|None, prefer_pack: bool=True) -> bool:
    t = title.lower()
    if prefer_pack and re.search(r"(全集|全季|全\s*集|合集)", t):
        return True
    return True
