# -*- coding: utf-8 -*-
import datetime, re
from typing import Any, Dict, List, Tuple
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.log import logger
from app.core.event import eventmanager
from apscheduler.triggers.cron import CronTrigger
from urllib import request as _req

from .ui import UIConfig
from .handlers import parse_rsshub_titles, search_links_pansou, search_links_aipan

class AutoFollow115(_PluginBase):
    plugin_name = 'AutoFollow115'
    plugin_desc = '自动追剧/电影到 115：发现 → 订阅 → 搜索 → 推送 115 链接到对话框触发自动转存'
    plugin_icon = 'autofollow115.png'
    plugin_color = '#5E81AC'
    plugin_version = '0.6.0'
    plugin_author = 'heruntime01'
    author_url = 'https://github.com/heruntime01'
    plugin_config_prefix = 'autofollow115_'
    plugin_order = 30
    auth_level = 1

    _enabled: bool = True
    _logs: List[Dict[str, Any]]

    def init_plugin(self, config: dict = None):
        cfg = config or {}
        self._enabled = bool(cfg.get('enabled', True))
        self._logs = self.get_data('logs') or []
        self.save_data('subs', self.get_data('subs') or [])
        self.save_data('progress', self.get_data('progress') or {})
        self._log('info', 'plugin initialized')

    def get_state(self) -> bool:
        return self._enabled

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return UIConfig.get_form()

    def get_page(self) -> List[dict]:
        subs = self.get_data('subs') or []
        prog = self.get_data('progress') or {}
        return UIConfig.get_page(subs, prog)

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {'path': '/discover', 'methods': ['GET'], 'endpoint': self.api_discover, 'summary': '发现候选'},
            {'path': '/subscribe', 'methods': ['POST'], 'endpoint': self.api_subscribe, 'summary': '订阅'},
            {'path': '/unsubscribe', 'methods': ['POST'], 'endpoint': self.api_unsubscribe, 'summary': '退订'},
            {'path': '/reset_progress', 'methods': ['POST'], 'endpoint': self.api_reset_progress, 'summary': '重置进度'},
            {'path': '/list', 'methods': ['GET'], 'endpoint': self.api_list, 'summary': '订阅列表'},
            {'path': '/progress', 'methods': ['GET'], 'endpoint': self.api_progress, 'summary': '进度'},
            {'path': '/run', 'methods': ['POST'], 'endpoint': self.api_run, 'summary': '立即扫描'},
            {'path': '/logs', 'methods': ['GET'], 'endpoint': self.api_logs, 'summary': '日志'},
            {'path': '/logs/clear', 'methods': ['POST'], 'endpoint': self.api_logs_clear, 'summary': '清空日志'},
        ]

    def get_service(self) -> List[dict]:
        if not self._enabled:
            return []
        cfg = self.get_config() or {}
        cron_scan = cfg.get('cron_scan') or '*/30 * * * *'
        try:
            trig = CronTrigger.from_crontab(cron_scan)
            return [{
                'id': 'AutoFollow115_scan',
                'name': 'AutoFollow115 扫描',
                'trigger': trig,
                'func': self.job_scan,
                'kwargs': {}
            }]
        except Exception as e:
            logger.warning('Cron 表达式无效：' + str(cron_scan) + '；回退 interval=30min；' + str(e))
            return [{
                'id': 'AutoFollow115_scan',
                'name': 'AutoFollow115 扫描',
                'trigger': 'interval',
                'func': self.job_scan,
                'kwargs': {'minutes': 30}
            }]

    def stop_service(self):
        pass

    # ===== APIs =====
    def api_discover(self, **kwargs):
        try:
            items = list(self._discover_from_rsshub())
            return self.success(data={'items': items})
        except Exception as e:
            self._log('error', 'discover failed: ' + str(e))
            return self.error(str(e))

    def api_subscribe(self, **kwargs):
        data = kwargs.get('data') or {}
        title = (data.get('title') or '').strip()
        tp = data.get('type') or 'tv'
        year = data.get('year')
        if not title:
            return self.error('title required')
        subs = self.get_data('subs') or []
        sid = (title + ':' + tp + ((':' + str(year)) if year else ''))
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
        cfg = self.get_config() or {}
        enable_pansou = bool(cfg.get('enable_pansou', True))
        enable_aipan = bool(cfg.get('enable_aipan', True))
        pushed_any = False
        for s in subs:
            links = []
            if enable_pansou:
                links += search_links_pansou(s.get('title'))
            if enable_aipan:
                links += search_links_aipan(s.get('title'))
            links = list({*links})
            if not links:
                continue
            link = links[0]
            msg = '[115自动追剧] 命中：' + str(s.get('title')) + chr(10) + str(link)
            self.post_message(mtype=NotificationType.Plugin, title='AutoFollow115', text=msg)
            prog = self.get_data('progress') or {}
            sid = s.get('id')
            pr = prog.get(sid, {'pushed': [], 'last_update': None, 'total_episodes': None})
            pr['pushed'] = list(set(pr.get('pushed') or []) | {link})
            pr['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            prog[sid] = pr
            self.save_data('progress', prog)
            pushed_any = True
        if pushed_any:
            self._log('info', 'push done for ' + str(len(subs)) + ' subs')

    # ===== Discover =====
    def _discover_from_rsshub(self):
        cfg = self.get_config() or {}
        if not cfg.get('enable_rsshub', True):
            return []
        base = (cfg.get('rsshub_base') or '').rstrip('/')
        paths = []
        mps = (cfg.get('rsshub_movie_paths') or '').strip().splitlines()
        tvps = (cfg.get('rsshub_tv_paths') or '').strip().splitlines()
        for p in list(mps) + list(tvps):
            p = (p or '').strip()
            if not p:
                continue
            url = base + (p if p.startswith('/') else '/' + p)
            try:
                req = _req.Request(url, headers={'User-Agent':'Mozilla/5.0'})
                with _req.urlopen(req, timeout=15) as resp:
                    txt = resp.read().decode('utf-8','ignore')
                titles = parse_rsshub_titles(txt, 20)
                for t in titles:
                    item = {'title': t, 'source': 'rsshub', 'path': p}
                    item['type'] = 'movie' if '/movie/' in p else 'tv'
                    item['year'] = None
                    item['score'] = None
                    item['hot'] = True
                    yield item
            except Exception as e:
                self._log('warn', 'rsshub fetch fail: ' + p + ' -> ' + str(e))
        return []

    # ===== Utils =====
    def _log(self, level: str, msg: str):
        rec = {'time': datetime.datetime.now().strftime('%H:%M:%S'), 'level': level, 'msg': msg}
        logs = self._logs or []
        logs.append(rec)
        self._logs = logs[-1000:]
        self.save_data('logs', self._logs)
        try:
            getattr(logger, level if hasattr(logger, level) else 'info')('[autofollow115] ' + msg)
        except Exception:
            logger.info('[autofollow115] ' + msg)
