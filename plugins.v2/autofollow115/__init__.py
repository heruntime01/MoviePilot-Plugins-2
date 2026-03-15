
# -*- coding: utf-8 -*-
import re
import json
import datetime
from typing import Any, Dict, List, Tuple
from app.plugins import Plugin, ServiceTask
from app.core.event import eventmanager
from app.log import logger
from apscheduler.triggers.cron import CronTrigger
from urllib import request as _req, error as _err

plugin_id = 'autofollow115'
plugin_name = 'AutoFollow115'
plugin_desc = '自动追剧/电影到 115：发现 → 订阅 → 搜索 → 推送 115 链接到对话框触发自动转存'
plugin_icon = 'autofollow115.png'
plugin_color = '#5E81AC'
plugin_version = '0.5.2'
plugin_author = 'heruntime01'
author_url = 'https://github.com/heruntime01'
plugin_config_prefix = 'autofollow115_'
auth_level = 1

# ===== Defaults (triple-quoted constants) =====
DEFAULT_RSSHUB_MOVIE_PATHS = """
/douban/movie/weekly/movie_real_time_hotest
/douban/movie/weekly/movie_showing
/douban/movie/weekly/movie_most_watched
/douban/movie/weekly/movie_high_score
/douban/movie/weekly/movie_trending
"""
DEFAULT_RSSHUB_TV_PATHS = """
/douban/tv/weekly/tv_real_time_hotest
/douban/tv/weekly/tv_showing
/douban/tv/weekly/tv_most_watched
/douban/tv/weekly/tv_high_score
/douban/tv/weekly/tv_trending
"""

RE_115 = re.compile(r'https?://115\.com/(?:s|f)/[A-Za-z0-9]+', re.I)
RE_115_SHORT = re.compile(r'https?://115\.com/l/[A-Za-z0-9]+', re.I)

class AutoFollow115(Plugin):
    _enabled: bool = True
    _logs: List[Dict[str, Any]]

    @staticmethod
    def get_render_mode() -> str:
        return 'vuetify'

    def init_plugin(self, config: dict = None):
        cfg = config or {}
        self._enabled = bool(cfg.get('enabled', True))
        self._logs = self.get_data('logs') or []
        # ensure storage keys
        self.save_data('subs', self.get_data('subs') or [])
        self.save_data('progress', self.get_data('progress') or {})
        self._log('info', 'plugin initialized')

    def get_state(self) -> bool:
        return self._enabled

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {'path': '/discover', 'methods': ['GET'], 'func': self.api_discover},
            {'path': '/subscribe', 'methods': ['POST'], 'func': self.api_subscribe},
            {'path': '/unsubscribe', 'methods': ['POST'], 'func': self.api_unsubscribe},
            {'path': '/reset_progress', 'methods': ['POST'], 'func': self.api_reset_progress},
            {'path': '/list', 'methods': ['GET'], 'func': self.api_list},
            {'path': '/progress', 'methods': ['GET'], 'func': self.api_progress},
            {'path': '/run', 'methods': ['POST'], 'func': self.api_run},
            {'path': '/logs', 'methods': ['GET'], 'func': self.api_logs},
            {'path': '/logs/clear', 'methods': ['POST'], 'func': self.api_logs_clear},
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        page = [
            {"component": "v-form", "children": [
                {"component": "v-row", "children": [
                    {"component": "v-col", "props": {"cols": 12, "md": 4}, "children": [
                        {"component": "v-switch", "props": {"model": "enabled", "label": "启用插件"}}
                    ]},
                    {"component": "v-col", "props": {"cols": 12, "md": 4}, "children": [
                        {"component": "v-cron-field", "props": {"model": "cron_scan", "label": "扫描 Cron"}}
                    ]},
                    {"component": "v-col", "props": {"cols": 12, "md": 4}, "children": [
                        {"component": "v-switch", "props": {"model": "prefer_pack", "label": "优先整季/全集包"}}
                    ]}
                ]},
                {"component": "v-row", "children": [
                    {"component": "v-col", "props": {"cols": 12, "md": 6}, "children": [
                        {"component": "v-select", "props": {"model": "quality_prefs", "label": "质量偏好", "items": ["2160p", "1080p", "HEVC", "HDR", "WEB-DL"], "multiple": True, "chips": True}}
                    ]},
                    {"component": "v-col", "props": {"cols": 12, "md": 6}, "children": [
                        {"component": "v-switch", "props": {"model": "validate_115", "label": "推送前校验 115 链接(HEAD)"}}
                    ]}
                ]},
                {"component": "v-divider"},
                {"component": "v-subheader", "props": {"text": "RSSHub (豆瓣榜单)"}},
                {"component": "v-row", "children": [
                    {"component": "v-col", "props": {"cols": 12, "md": 3}, "children": [
                        {"component": "v-switch", "props": {"model": "enable_rsshub", "label": "启用 RSSHub"}}
                    ]},
                    {"component": "v-col", "props": {"cols": 12, "md": 9}, "children": [
                        {"component": "v-text-field", "props": {"model": "rsshub_base", "label": "RSSHub 基址"}}
                    ]}
                ]},
                {"component": "v-row", "children": [
                    {"component": "v-col", "props": {"cols": 12, "md": 6}, "children": [
                        {"component": "v-textarea", "props": {"model": "rsshub_movie_paths", "label": "电影路径(一行一个)", "rows": 6}}
                    ]},
                    {"component": "v-col", "props": {"cols": 12, "md": 6}, "children": [
                        {"component": "v-textarea", "props": {"model": "rsshub_tv_paths", "label": "剧集路径(一行一个)", "rows": 6}}
                    ]}
                ]},
                {"component": "v-divider"},
                {"component": "v-subheader", "props": {"text": "可选：搜索源"}},
                {"component": "v-row", "children": [
                    {"component": "v-col", "props": {"cols": 12, "md": 6}, "children": [
                        {"component": "v-switch", "props": {"model": "enable_pansou", "label": "启用 PanSou"}}
                    ]},
                    {"component": "v-col", "props": {"cols": 12, "md": 6}, "children": [
                        {"component": "v-switch", "props": {"model": "enable_aipan", "label": "启用 AiPan"}}
                    ]}
                ]},
                {"component": "v-row", "children": [
                    {"component": "v-col", "props": {"cols": 12, "md": 12}, "children": [
                        {"component": "v-text-field", "props": {"model": "http_proxy", "label": "HTTP 代理 (http://host:port)"}}
                    ]}
                ]}
            ]}]
        defaults = {
            'enabled': True,
            'cron_scan': '*/30 * * * *',
            'prefer_pack': True,
            'quality_prefs': ['2160p','HEVC','HDR'],
            'validate_115': False,
            'enable_rsshub': True,
            'rsshub_base': 'https://rss.hrtime.asia:4000',
            'rsshub_movie_paths': DEFAULT_RSSHUB_MOVIE_PATHS,
            'rsshub_tv_paths': DEFAULT_RSSHUB_TV_PATHS,
            'enable_pansou': True,
            'enable_aipan': True,
            'http_proxy': None,
        }
        return page, defaults

    def get_page(self) -> List[dict]:
        subs = self.get_data('subs') or []
        prog = self.get_data('progress') or {}
        headers = [
            {'title': '标题', 'key': 'title', 'sortable': True},
            {'title': '类型', 'key': 'type'},
            {'title': '年份', 'key': 'year'},
            {'title': '总集数', 'key': 'total_episodes'},
            {'title': '已推送', 'key': 'pushed_count'},
            {'title': '最后更新', 'key': 'last_update'}
        ]
        rows = []
        for s in subs:
            sid = s.get('id') or s.get('title')
            pr = prog.get(sid, {})
            rows.append({
                'title': s.get('title'),
                'type': s.get('type'),
                'year': s.get('year'),
                'total_episodes': pr.get('total_episodes'),
                'pushed_count': len(pr.get('pushed') or []),
                'last_update': pr.get('last_update')
            })
        return [
            {"component": "v-card", "props": {"title": "AutoFollow115 订阅与进度"}, "children": [
                {"component": "v-data-table", "props": {"headers": headers, "items": rows, "items-per-page": 10}}
            ]}
        ]

    def get_service(self) -> List[ServiceTask]:
        cfg = self.get_config() or {}
        cron_scan = cfg.get('cron_scan') or '*/30 * * * *'
        return [
            ServiceTask(name='autofollow115_scan', trigger=CronTrigger.from_crontab(cron_scan), func=self.job_scan)
        ]

    def stop_service(self):
        pass

    # ===== APIs =====
    def api_discover(self, **kwargs):
        try:
            items = self._discover_from_rsshub()
            return self.success(data={'items': items})
        except Exception as e:
            self._log('error', f'discover failed: {e}')
            return self.error(str(e))

    def api_subscribe(self, **kwargs):
        data = kwargs.get('data') or {}
        title = (data.get('title') or '').strip()
        tp = data.get('type') or 'tv'
        year = data.get('year')
        if not title:
            return self.error('title required')
        subs = self.get_data('subs') or []
        sid = f"{title}:{tp}:{year}" if year else f"{title}:{tp}"
        if any((s.get('id')==sid) for s in subs):
            return self.success(msg='already subscribed')
        subs.append({'id': sid, 'title': title, 'type': tp, 'year': year})
        self.save_data('subs', subs)
        prog = self.get_data('progress') or {}
        prog.setdefault(sid, {'pushed': [], 'last_update': None, 'total_episodes': None})
        self.save_data('progress', prog)
        return self.success(msg='subscribed', data={'id': sid})

    def api_unsubscribe(self, **kwargs):
        data = kwargs.get('data') or {}
        sid = data.get('id')
        subs = [s for s in (self.get_data('subs') or []) if s.get('id')!=sid]
        self.save_data('subs', subs)
        prog = self.get_data('progress') or {}
        if sid in prog:
            prog.pop(sid, None)
            self.save_data('progress', prog)
        return self.success(msg='unsubscribed')

    def api_reset_progress(self, **kwargs):
        data = kwargs.get('data') or {}
        sid = data.get('id')
        prog = self.get_data('progress') or {}
        if sid in prog:
            prog[sid] = {'pushed': [], 'last_update': None, 'total_episodes': prog[sid].get('total_episodes')}
            self.save_data('progress', prog)
        return self.success(msg='progress reset')

    def api_list(self, **kwargs):
        return self.success(data={'subs': self.get_data('subs') or []})

    def api_progress(self, **kwargs):
        return self.success(data={'progress': self.get_data('progress') or {}})

    def api_run(self, **kwargs):
        try:
            self.job_scan()
            return self.success(msg='scan started')
        except Exception as e:
            return self.error(str(e))

    def api_logs(self, **kwargs):
        return self.success(data={'logs': self._logs[-500:]})

    def api_logs_clear(self, **kwargs):
        self._logs = []
        self.save_data('logs', self._logs)
        return self.success(msg='cleared')

    # ===== Jobs =====
    def job_scan(self):
        if not self._enabled:
            return
        subs = self.get_data('subs') or []
        if not subs:
            return
        # 简化：按标题关键字去 Pansou/AiPan 抓 115 链接（如启用），并推送到对话框
        cfg = self.get_config() or {}
        enable_pansou = bool(cfg.get('enable_pansou', True))
        enable_aipan = bool(cfg.get('enable_aipan', True))
        pushed_any = False
        for s in subs:
            links = []
            if enable_pansou:
                links += self._search_links_pansou(s.get('title'))
            if enable_aipan:
                links += self._search_links_aipan(s.get('title'))
            links = list({*links})
            if not links:
                continue
            # 只推送一个，避免刷屏
            link = links[0]
            msg = "[115自动追剧] 命中：" + str(s.get("title")) + chr(10) + str(link)
            self.post_message('Text', msg)
prog = self.get_data('progress') or {}
            sid = s.get('id')
            pr = prog.get(sid, {'pushed': [], 'last_update': None, 'total_episodes': None})
            pr['pushed'] = list(set(pr.get('pushed') or []) | {link})
            pr['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            prog[sid] = pr
            self.save_data('progress', prog)
            pushed_any = True
        if pushed_any:
            self._log('info', f'push done for {len(subs)} subs')

    # ===== Internals =====
    def _discover_from_rsshub(self) -> List[Dict[str, Any]]:
        cfg = self.get_config() or {}
        if not cfg.get('enable_rsshub', True):
            return []
        base = (cfg.get('rsshub_base') or '').rstrip('/')
        paths = []
        mps = (cfg.get('rsshub_movie_paths') or '').strip().splitlines()
        tvps = (cfg.get('rsshub_tv_paths') or '').strip().splitlines()
        for p in [*mps, *tvps]:
            p = p.strip()
            if not p:
                continue
            url = f"{base}{p if p.startswith('/') else '/' + p}"
            try:
                req = _req.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with _req.urlopen(req, timeout=15) as resp:
                    txt = resp.read().decode('utf-8', 'ignore')
                # 粗提取：从 <item><title>…</title> 抓标题
                titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', txt, re.I)
                for t1, t2 in titles[:20]:
                    t = (t1 or t2 or '').strip()
                    if not t or t.lower().startswith('rsshub'):
                        continue
                    yield_item = {'title': t, 'source': 'rsshub', 'path': p}
                    # 类型粗判
                    yield_item['type'] = 'movie' if '/movie/' in p else 'tv'
                    yield_item['year'] = None
                    yield_item['score'] = None
                    yield_item['hot'] = True
                    # 为列表返回
                    yield yield_item
            except Exception as e:
                self._log('warn', f'rsshub fetch fail: {p} -> {e}')
        return []

    def _search_links_pansou(self, kw: str) -> List[str]:
        try:
            url = f"https://www.pansou.vip/s/{parse.quote(kw)}"
            req = _req.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with _req.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', 'ignore')
            ls = list(set(re.findall(RE_115, html) + re.findall(RE_115_SHORT, html)))
            return ls[:20]
        except Exception as e:
            self._log('warn', f'pansou error: {e}')
            return []

    def _search_links_aipan(self, kw: str) -> List[str]:
        try:
            url = f"https://www.aipan.me/search?k={parse.quote(kw)}"
            req = _req.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with _req.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', 'ignore')
            ls = list(set(re.findall(RE_115, html) + re.findall(RE_115_SHORT, html)))
            return ls[:20]
        except Exception as e:
            self._log('warn', f'aipan error: {e}')
            return []

    # ===== Utils =====
    def _log(self, level: str, msg: str):
        rec = {'time': datetime.datetime.now().strftime('%H:%M:%S'), 'level': level, 'msg': msg}
        self._logs.append(rec)
        self._logs = self._logs[-1000:]
        self.save_data('logs', self._logs)
        try:
            getattr(logger, level if hasattr(logger, level) else 'info')(f'[autofollow115] {msg}')
        except Exception:
            logger.info(f'[autofollow115] {msg}')

