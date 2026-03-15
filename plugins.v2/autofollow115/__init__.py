
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

class AutoFollow115(_PluginBase):
    plugin_name = "115 自动追剧"
    plugin_desc = "订阅豆瓣热门 + RSSHub 榜单，聚合网盘搜索源，命中后推送 115 链接到对话框自动转存"
    plugin_version = "0.2.3"
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
        return [{"cmd": "/af115", "event": None, "desc": "显示插件说明/快速命令", "category": "订阅"}]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/discover", "endpoint": self.api_discover, "methods": ["GET"], "auth": "apikey",
             "summary": "获取热门列表(豆瓣m站+RSSHub)", "description": "type=tv|movie"},
            {"path": "/subscribe", "endpoint": self.api_subscribe, "methods": ["POST"], "auth": "apikey",
             "summary": "新增订阅", "description": "提交订阅模型"},
            {"path": "/list", "endpoint": self.api_list, "methods": ["GET"], "auth": "apikey",
             "summary": "订阅清单", "description": ""},
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

    def get_page(self) -> Optional[List[dict]]:
        return [{"component": "v-alert", "props": {"type": "info", "text": "在“发现”页选择条目后订阅，命中将推送 115 链接至对话框"}}]

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
            if hasattr(self, 'info'):
                self.info(f"douban hot tv={len(tv)} movie={len(mv)}")
        except Exception as e:
            if hasattr(self, 'info'):
                self.info(f"douban hot error: {e}")
        if bool(self._conf.get('enable_rsshub', True)):
            base = (self._conf.get('rsshub_base') or '').strip() or 'https://rss.hrtime.asia:4000'
            proxy = self._conf.get('http_proxy')
            def _split_lines(s: str) -> List[str]:
                return [x.strip() for x in (s or '').splitlines() if x.strip()]
            movie_paths = _split_lines(self._conf.get('rsshub_movie_paths') or '')
            tv_paths = _split_lines(self._conf.get('rsshub_tv_paths') or '')
            try:
                m2 = fetch_rsshub(base, movie_paths, proxy=proxy)
                movie_list.extend(m2)
                if hasattr(self, 'info'):
                    self.info(f"rsshub movie items={len(m2)}")
            except Exception as e:
                if hasattr(self, 'info'):
                    self.info(f"rsshub movie error: {e}")
            try:
                t2 = fetch_rsshub(base, tv_paths, proxy=proxy)
                tv_list.extend(t2)
                if hasattr(self, 'info'):
                    self.info(f"rsshub tv items={len(t2)}")
            except Exception as e:
                if hasattr(self, 'info'):
                    self.info(f"rsshub tv error: {e}")
        self._discover_cache['tv'] = self._merge_discover(tv_list)
        self._discover_cache['movie'] = self._merge_discover(movie_list)
        if hasattr(self, 'info'):
            self.info(f"discover cached tv={len(self._discover_cache['tv'])} movie={len(self._discover_cache['movie'])}")

    def _push_115(self, title: str, url: str):
        text = f"{title}\n{url}"
        self.post_message(mtype=NotificationType.Text, title="[115自动追剧] 命中", text=text)

    def job_scan(self, **kwargs):
        subs = self.get_data("subs") or []
        if not subs:
            return
        pushed_map: Dict[str, List[str]] = self.get_data('pushed') or {}
        for sub in subs:
            q = sub.get('title')
            if not q:
                continue
            results: List[Dict] = []
            for p in self._providers:
                try:
                    rs = p.search(q, sub.get('type') or 'tv', sub.get('year'))
                except Exception as e:
                    if hasattr(self, 'info'):
                        self.info(f"provider {getattr(p,'name','?')} error: {e}")
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
            pushed_this_round: List[str] = []
            for r in uniq:
                u = r.get('url')
                if not u or u in pushed:
                    continue
                if not good_enough(r.get('title') or q, sub.get('year'), prefer_pack=bool(self._conf.get('prefer_pack', True))):
                    continue
                self._push_115(q, u)
                pushed_this_round.append(u)
                break
            if pushed_this_round:
                new_list = list(pushed.union(pushed_this_round))
                pushed_map[q] = new_list
        self.save_data('pushed', pushed_map)

    def api_discover(self, request=None):
        t = (request.query_params.get("type") if request else None) or "tv"
        return self._discover_cache.get(t, [])

    def api_subscribe(self, request=None):
        payload = request.json() if request else {}
        subs = self.get_data("subs") or []
        subs.append(payload)
        self.save_data("subs", subs)
        return {"ok": True}

    def api_list(self, request=None):
        return {"subs": self.get_data("subs") or []}

    def api_run(self, request=None):
        self.job_scan()
        return {"ok": True}

    def stop_service(self):
        pass
