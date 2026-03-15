
from typing import Any, Dict, List, Optional, Tuple
from apscheduler.triggers.cron import CronTrigger
from app.plugins import _PluginBase
from app.schemas import NotificationType

from .douban import hot as douban_hot
from .rsshub import fetch_rsshub
from .matching import score as score_title, good_enough
from .providers.pansou import PanSouProvider
from .providers.aipan import AiPanProvider
from .providers.nullbr import NullBRProvider
from .metadata import total_episodes_from_douban

import re
import datetime

class AutoFollow115(_PluginBase):
    plugin_name = "115 自动追剧"
    plugin_desc = "订阅豆瓣热门 + RSSHub 榜单，聚合网盘搜索源，命中后推送 115 链接到对话框自动转存"
    plugin_version = "0.3.2"
    plugin_author = "Herun"
    plugin_order = 20
    plugin_icon = "https://movie-pilot.org/favicon.ico"

    def __init__(self):
        super().__init__()
        self._enabled = True
        self._conf: Dict[str, Any] = {}
        self._providers = []
        self._discover_cache = {"tv": [], "movie": []}

    def init_plugin(self, config: dict = None):
        self._conf = config or {}
        self._enabled = bool(self._conf.get("enabled", True))
        proxy = self._conf.get('http_proxy')
        provs = [PanSouProvider(proxy=proxy), AiPanProvider(proxy=proxy)]
        if bool(self._conf.get('enable_nullbr')):
            base = (self._conf.get('nullbr_base') or '').strip()
            provs.append(NullBRProvider(base=base, proxy=proxy))
        self._providers = provs

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [
            {"cmd": "/af115", "event": None, "desc": "显示插件说明/快速命令", "category": "订阅"}
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/discover", "endpoint": self.api_discover, "methods": ["GET"], "auth": "apikey",
             "summary": "获取热门列表(豆瓣m站+RSSHub)", "description": "type=tv|movie"},
            {"path": "/subscribe", "endpoint": self.api_subscribe, "methods": ["POST"], "auth": "apikey",
             "summary": "新增订阅", "description": "字段: type/title/year，可选 include/exclude/max_daily"},
            {"path": "/unsubscribe", "endpoint": self.api_unsubscribe, "methods": ["POST"], "auth": "apikey",
             "summary": "取消订阅", "description": "{title}"},
            {"path": "/reset_progress", "endpoint": self.api_reset_progress, "methods": ["POST"], "auth": "apikey",
             "summary": "重置进度", "description": "{title}"},
            {"path": "/list", "endpoint": self.api_list, "methods": ["GET"], "auth": "apikey",
             "summary": "订阅清单", "description": "返回订阅+进度概览(含总集数)"},
            {"path": "/progress", "endpoint": self.api_progress, "methods": ["GET"], "auth": "apikey",
             "summary": "订阅进度", "description": "返回每个订阅的剧集进度/总数"},
            {"path": "/run", "endpoint": self.api_run, "methods": ["POST"], "auth": "apikey",
             "summary": "手动触发扫描", "description": ""},
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        form = [
            {"type": "switch", "key": "enabled", "props": {"label": "启用插件"}},
            {"type": "subheader", "text": "策略"},
            {"type": "text", "key": "cron_scan", "props": {"label": "扫描 Cron", "placeholder": "*/30 * * * *"}},
            {"type": "switch", "key": "prefer_pack", "props": {"label": "优先整季/全集包"}},
            {"type": "chips", "key": "quality_prefs", "props": {"label": "质量偏好", "multiple": True},
             "items": [{"text":"2160p"},{"text":"1080p"},{"text":"HEVC"},{"text":"HDR"},{"text":"WEB-DL"}]},
            {"type": "switch", "key": "validate_115", "props": {"label": "推送前校验 115 链接可达(HEAD)", "inset": True}},
            {"type": "subheader", "text": "RSSHub (豆瓣榜单)"},
            {"type": "switch", "key": "enable_rsshub", "props": {"label": "启用 RSSHub 榜单聚合"}},
            {"type": "text", "key": "rsshub_base", "props": {"label": "RSSHub 基址", "placeholder": "https://rss.hrtime.asia:4000"}},
            {"type": "textarea", "key": "rsshub_movie_paths", "props": {"label": "电影路径(一行一个)", "rows": 6}},
            {"type": "textarea", "key": "rsshub_tv_paths", "props": {"label": "剧集路径(一行一个)", "rows": 6}},
            {"type": "subheader", "text": "NullBR (可选)"},
            {"type": "switch", "key": "enable_nullbr", "props": {"label": "启用 NullBR 聚合"}},
            {"type": "text", "key": "nullbr_base", "props": {"label": "NullBR 基址", "placeholder": "https://example.com"}},
            {"type": "text", "key": "http_proxy", "props": {"label": "HTTP 代理(可选)", "placeholder": "http://host:port"}},
        ]
        defaults = {
            "enabled": True,
            "cron_scan": "*/30 * * * *",
            "prefer_pack": True,
            "quality_prefs": ["2160p", "HEVC", "HDR"],
            "validate_115": False,
            "enable_rsshub": True,
            "rsshub_base": "https://rss.hrtime.asia:4000",
            "rsshub_movie_paths": "\n".join([
                "/douban/movie/weekly/movie_real_time_hotest",
                "/douban/movie/weekly/movie_showing",
                "/douban/movie/weekly/movie_most_watched",
                "/douban/movie/weekly/movie_high_score",
                "/douban/movie/weekly/movie_trending",
            ]),
            "rsshub_tv_paths": "\n".join([
                "/douban/tv/weekly/tv_real_time_hotest",
                "/douban/tv/weekly/tv_showing",
                "/douban/tv/weekly/tv_most_watched",
                "/douban/tv/weekly/tv_high_score",
                "/douban/tv/weekly/tv_trending",
            ]),
            "enable_nullbr": False,
            "nullbr_base": "",
            "http_proxy": None
        }
        return form, defaults

    def _table_items(self) -> List[Dict[str, Any]]:
        subs = self.get_data("subs") or []
        prog = self.get_data('progress') or {}
        items = []
        for s in subs:
            key = s.get('title')
            p = prog.get(key) or {}
            eps = sorted((p.get('episodes') or []))
            items.append({
                'title': key,
                'type': s.get('type'),
                'year': s.get('year'),
                'episodes_count': len(eps),
                'last_episode': (eps[-1] if eps else None),
                'pack': '是' if (p.get('pack') or False) else '否',
                'total_episodes': p.get('total'),
                'last_update': p.get('last_update'),
            })
        return items

    def get_page(self) -> Optional[List[dict]]:
        headers = [
            {"title": "标题", "key": "title"},
            {"title": "类型", "key": "type"},
            {"title": "年份", "key": "year", "align": "end", "width": 80},
            {"title": "已集数", "key": "episodes_count", "align": "end", "width": 80},
            {"title": "最新集", "key": "last_episode", "align": "end", "width": 80},
            {"title": "整包", "key": "pack", "width": 80},
            {"title": "总集数", "key": "total_episodes", "align": "end", "width": 90},
            {"title": "最近更新时间", "key": "last_update", "width": 180},
        ]
        return [
            {"component": "v-card", "props": {"class": "pa-3"}, "children": [
                {"component": "v-alert", "props": {"type": "info", "text": f"AutoFollow115 v{self.plugin_version}：在下方表格查看订阅与进度；更多细节见 README。"}},
                {"component": "v-data-table", "props": {"items": self._table_items(), "headers": headers, "items-per-page": 50}}
            ]}
        ]

    def _merge_discover(self, arr: List[Dict]) -> List[Dict]:
        seen = set(); out: List[Dict] = []
        for it in arr:
            k = (it.get('title'), it.get('year'), it.get('douban_id'))
            if k in seen:
                continue
            seen.add(k); out.append(it)
        return out

    def get_service(self) -> List[Dict[str, Any]]:
        cron_scan = self._conf.get("cron_scan") or "*/30 * * * *"
        return [
            {"id": "af115-scan", "name": "订阅扫描", "trigger": CronTrigger.from_crontab(cron_scan), "func": self.job_scan, "kwargs": {}},
            {"id": "af115-discover", "name": "热门刷新", "trigger": CronTrigger.from_crontab("0 */6 * * *"), "func": self.job_discover, "kwargs": {}},
        ]

    def job_discover(self, **kwargs):
        tv_list: List[Dict] = []
        movie_list: List[Dict] = []
        try:
            tv = douban_hot('tv', 0, 20) or []
            mv = douban_hot('movie', 0, 20) or []
            tv_list.extend(tv)
            movie_list.extend(mv)
        except Exception:
            pass
        if bool(self._conf.get('enable_rsshub', True)):
            base = (self._conf.get('rsshub_base') or '').strip() or 'https://rss.hrtime.asia:4000'
            proxy = self._conf.get('http_proxy')
            def _split_lines(s: str) -> List[str]:
                return [x.strip() for x in (s or '').splitlines() if x.strip()]
            movie_paths = _split_lines(self._conf.get('rsshub_movie_paths') or '')
            tv_paths = _split_lines(self._conf.get('rsshub_tv_paths') or '')
            try:
                movie_list.extend(fetch_rsshub(base, movie_paths, proxy=proxy))
            except Exception:
                pass
            try:
                tv_list.extend(fetch_rsshub(base, tv_paths, proxy=proxy))
            except Exception:
                pass
        self._discover_cache['tv'] = self._merge_discover(tv_list)
        self._discover_cache['movie'] = self._merge_discover(movie_list)

    def _push_115(self, title: str, url: str):
        text = f"{title}\n{url}"
        self.post_message(mtype=NotificationType.Text, title="[115自动追剧] 命中", text=text)

    @staticmethod
    def _extract_episode_num(text: str) -> Optional[int]:
        t = text or ''
        for pat in [r'[Ee]P?(\d{1,3})', r'第(\d{1,3})[集话]']:
            m = re.search(pat, t)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
        return None

    @staticmethod
    def _is_pack(text: str) -> bool:
        t = (text or '').lower()
        return bool(re.search(r'(全集|全季|合集|complete)', t))

    def _record_progress(self, sub: Dict[str, Any], item: Dict[str, Any]):
        prog: Dict[str, Any] = self.get_data('progress') or {}
        key = sub.get('title')
        if not key:
            return
        entry = prog.get(key) or {"episodes": [], "pack": False, "last_update": None, "total": None, "last_url": None, "last_provider": None}
        title = item.get('title') or key
        if self._is_pack(title):
            entry['pack'] = True
        ep = self._extract_episode_num(title) or self._extract_episode_num(item.get('url') or '')
        if ep:
            if ep not in entry['episodes']:
                entry['episodes'].append(ep)
        entry['last_url'] = item.get('url')
        entry['last_provider'] = item.get('provider')
        entry['last_update'] = datetime.datetime.now().isoformat(timespec='seconds')
        if entry.get('total') is None and sub.get('type') == 'tv':
            douban_id = None
            year = sub.get('year')
            cand = None
            for it in self._discover_cache.get('tv', []):
                if it.get('title') == key and (not year or it.get('year') == year):
                    cand = it; break
            if cand:
                douban_id = cand.get('douban_id')
            total = None
            try:
                total = total_episodes_from_douban(douban_id, proxy=self._conf.get('http_proxy')) if douban_id else None
            except Exception:
                total = None
            if total:
                entry['total'] = int(total)
        prog[key] = entry
        self.save_data('progress', prog)

    def job_scan(self, **kwargs):
        subs = self.get_data("subs") or []
        if not subs:
            return
        pushed_map: Dict[str, List[str]] = self.get_data('pushed') or {}
        push_count: Dict[str, Dict[str,int]] = self.get_data('push_count') or {}
        today = datetime.date.today().isoformat()
        validate = bool(self._conf.get('validate_115', False))
        for sub in subs:
            q = sub.get('title')
            if not q:
                continue
            results: List[Dict] = []
            for p in self._providers:
                try:
                    rs = p.search(q, sub.get('type') or 'tv', sub.get('year'))
                except Exception:
                    rs = []
                for r in rs:
                    r['score'] = r.get('score',0) + score_title(r.get('title') or q)
                results.extend(rs)
            seen = set(); uniq=[]
            for r in sorted(results, key=lambda x: x.get('score',0), reverse=True):
                u = r.get('url');
                if not u or u in seen:
                    continue
                seen.add(u); uniq.append(r)
            pushed = set(pushed_map.get(q, []) or [])
            sub_limit = 3
            try:
                sub_limit = int(sub.get('max_daily', 3))
            except Exception:
                sub_limit = 3
            sub_count_map = push_count.get(q, {})
            today_count = int(sub_count_map.get(today, 0))
            if today_count >= sub_limit:
                continue
            include = sub.get('include')
            exclude = sub.get('exclude')
            pushed_this_round: List[str] = []
            for r in uniq:
                u = r.get('url')
                if not u or u in pushed:
                    continue
                title = r.get('title') or q
                t_low = title.lower()
                def _lst(x):
                    if x is None:
                        return []
                    if isinstance(x, list):
                        return [str(i).strip().lower() for i in x if str(i).strip()]
                    parts = [p.strip() for p in str(x).replace('，', ',').split(',')]
                    return [p.lower() for p in parts if p]
                inc = _lst(include); exc = _lst(exclude)
                if inc and not any(k in t_low for k in inc):
                    continue
                if exc and any(k in t_low for k in exc):
                    continue
                if not good_enough(title, sub.get('year'), prefer_pack=bool(self._conf.get('prefer_pack', True))):
                    continue
                if validate and not self._check_url_head(u):
                    continue
                self._record_progress(sub, r)
                self._push_115(q, u)
                pushed_this_round.append(u)
                today_count += 1
                break
            if pushed_this_round:
                new_list = list(pushed.union(pushed_this_round))
                pushed_map[q] = new_list
                sub_count_map[today] = today_count
                push_count[q] = sub_count_map
        self.save_data('pushed', pushed_map)
        self.save_data('push_count', push_count)

    def _check_url_head(self, url: str, timeout: int=3) -> bool:
        try:
            import urllib.request as ur
            req = ur.Request(url, method='HEAD', headers={'User-Agent':'Mozilla/5.0'})
            opener = ur.build_opener()
            with opener.open(req, timeout=timeout) as resp:
                return 200 <= getattr(resp, 'status', resp.getcode()) < 400
        except Exception:
            return False

    def api_discover(self, request=None):
        t = (request.query_params.get("type") if request else None) or "tv"
        return self._discover_cache.get(t, [])

    def api_subscribe(self, request=None):
        payload = request.json() if request else {}
        subs = self.get_data("subs") or []
        subs.append(payload)
        self.save_data("subs", subs)
        return {"ok": True}

    def api_unsubscribe(self, request=None):
        payload = request.json() if request else {}
        title = (payload or {}).get('title')
        subs = self.get_data('subs') or []
        subs = [s for s in subs if s.get('title') != title]
        self.save_data('subs', subs)
        return {"ok": True, "removed": title}

    def api_reset_progress(self, request=None):
        payload = request.json() if request else {}
        title = (payload or {}).get('title')
        prog = self.get_data('progress') or {}
        if title in prog:
            del prog[title]
        self.save_data('progress', prog)
        return {"ok": True, "reset": title}

    def api_list(self, request=None):
        items = self._table_items()
        return {'subs': items}

    def api_progress(self, request=None):
        subs = self.get_data("subs") or []
        prog = self.get_data('progress') or {}
        out = []
        for s in subs:
            key = s.get('title')
            p = prog.get(key) or {}
            eps = sorted((p.get('episodes') or []))
            out.append({
                'title': key,
                'type': s.get('type'),
                'year': s.get('year'),
                'episodes': eps,
                'episodes_count': len(eps),
                'pack': p.get('pack') or False,
                'total_episodes': p.get('total'),
                'last_url': p.get('last_url'),
                'last_provider': p.get('last_provider'),
                'last_update': p.get('last_update'),
            })
        return {'progress': out}

    def api_run(self, request=None):
        self.job_scan()
        return {"ok": True}

    def stop_service(self):
        pass
