# -*- coding: utf-8 -*-
import datetime, re
from typing import Any, Dict, List, Tuple
from urllib import request as _req
from urllib import parse as _parse

from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.log import logger
from apscheduler.triggers.cron import CronTrigger

UA={'User-Agent':'Mozilla/5.0'}

class AutoFollow115(_PluginBase):
    # 元数据
    plugin_name = 'AutoFollow115'
    plugin_desc = '自动追剧/电影到 115：发现 → 订阅 → 搜索 → 推送 115 链接到对话框触发自动转存'
    plugin_icon = 'autofollow115.png'
    plugin_color = '#5E81AC'
    plugin_version = '0.6.2'
    plugin_author = 'heruntime01'
    author_url = 'https://github.com/heruntime01'
    plugin_config_prefix = 'autofollow115_'
    plugin_order = 30
    auth_level = 1

    # 运行字段
    _enabled: bool = True
    _logs: List[Dict[str, Any]] = []

    # 初始化
    def init_plugin(self, config: dict = None):
        cfg = config or {}
        self._enabled = bool(cfg.get('enabled', True))
        self._logs = self.get_data('logs') or []
        # 保证数据键存在
        self.save_data('subs', self.get_data('subs') or [])
        self.save_data('progress', self.get_data('progress') or {})
        # 手动订阅：保存设置即生效
        sub_title = (cfg.get('subscribe_title') or '').strip()
        sub_type = (cfg.get('subscribe_type') or 'tv')
        sub_year = (cfg.get('subscribe_year') or '').strip()
        if sub_title:
            subs = self.get_data('subs') or []
            sid = sub_title + ':' + sub_type + ((':' + sub_year) if sub_year else '')
            if not any((s.get('id')==sid) for s in subs):
                subs.append({'id': sid, 'title': sub_title, 'type': sub_type, 'year': (sub_year or None)})
                self.save_data('subs', subs)
                prog = self.get_data('progress') or {}
                prog.setdefault(sid, {'pushed': [], 'last_update': None, 'total_episodes': None})
                self.save_data('progress', prog)
                self._log('info', 'subscribed via settings: ' + sid)
            # 清空标题/年份，保留类型
            try:
                self.update_config({'subscribe_title': '', 'subscribe_year': ''})
            except Exception:
                pass
        self._log('info', 'plugin initialized')

    # 状态
    def get_state(self) -> bool:
        return self._enabled

    # 配置表单（大写 V 组件 + content/props）
    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        form = [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件'}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [
                                {'component': 'VCronField', 'props': {'model': 'cron_scan', 'label': '扫描 Cron'}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'prefer_pack', 'label': '优先整季/全集包'}}
                            ]},
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VSelect', 'props': {
                                    'model': 'quality_prefs', 'label': '质量偏好',
                                    'items': ['2160p','1080p','HEVC','HDR','WEB-DL'], 'multiple': True, 'chips': True
                                }}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'validate_115', 'label': '推送前校验 115 链接(HEAD)'}}
                            ]}
                        ]
                    },
                    {'component': 'VDivider'},
                    {'component': 'VSubheader', 'props': {'text': 'RSSHub (豆瓣榜单)'}},
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'enable_rsshub', 'label': '启用 RSSHub'}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 9}, 'content': [
                                {'component': 'VTextField', 'props': {'model': 'rsshub_base', 'label': 'RSSHub 基址'}}
                            ]}
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VTextarea', 'props': {'model': 'rsshub_movie_paths', 'label': '电影路径(一行一个)', 'rows': 6}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VTextarea', 'props': {'model': 'rsshub_tv_paths', 'label': '剧集路径(一行一个)', 'rows': 6}}
                            ]}
                        ]
                    },
                    {'component': 'VDivider'},
                    {'component': 'VSubheader', 'props': {'text': '可选：搜索源'}},
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'enable_pansou', 'label': '启用 PanSou'}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'enable_aipan', 'label': '启用 AiPan'}}
                            ]}
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 12}, 'content': [
                                {'component': 'VTextField', 'props': {'model': 'http_proxy', 'label': 'HTTP 代理 (http://host:port)'}}
                            ]}
                        ]
                    },
                    {'component': 'VDivider'},
                    {'component': 'VSubheader', 'props': {'text': '手动订阅（保存设置后立即添加）'}},
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                {'component': 'VTextField', 'props': {'model': 'subscribe_title', 'label': '标题'}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 6, 'md': 3}, 'content': [
                                {'component': 'VSelect', 'props': {'model': 'subscribe_type', 'label': '类型', 'items': [
                                    {'title':'电视剧','value':'tv'}, {'title':'电影','value':'movie'}
                                ]}}
                            ]},
                            {'component': 'VCol', 'props': {'cols': 6, 'md': 3}, 'content': [
                                {'component': 'VTextField', 'props': {'model': 'subscribe_year', 'label': '年份(可选)'}}
                            ]}
                        ]
                    }
                ]
            }
        ]
        defaults = {
            'enabled': True,
            'cron_scan': '*/30 * * * *',
            'prefer_pack': True,
            'quality_prefs': ['2160p','HEVC','HDR'],
            'validate_115': False,
            'enable_rsshub': True,
            'rsshub_base': 'https://rss.hrtime.asia:4000',
            'rsshub_movie_paths': """
/douban/movie/weekly/movie_real_time_hotest
/douban/movie/weekly/movie_showing
/douban/movie/weekly/movie_most_watched
/douban/movie/weekly/movie_high_score
/douban/movie/weekly/movie_trending
""",
            'rsshub_tv_paths': """
/douban/tv/weekly/tv_real_time_hotest
/douban/tv/weekly/tv_showing
/douban/tv/weekly/tv_most_watched
/douban/tv/weekly/tv_high_score
/douban/tv/weekly/tv_trending
""",
            'enable_pansou': True,
            'enable_aipan': True,
            'http_proxy': None,
            'subscribe_title': '',
            'subscribe_type': 'tv',
            'subscribe_year': ''
        }
        return form, defaults

    # 详情页（表格视图）
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
        return [{
            'component': 'VCard',
            'props': {'title': 'AutoFollow115 订阅与进度'},
            'content': [
                {'component': 'VDataTableVirtual', 'props': {
                    'headers': headers,
                    'items': rows,
                    'height': '30rem',
                    'density': 'compact',
                    'fixed-header': True,
                    'items-per-page': 20
                }}
            ]
        }]

    # API 注册（使用 endpoint）
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

    # 服务注册（Cron 失败回退 interval）
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

    # ===== API 实现 =====
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
        sid = title + ':' + tp + ((':' + str(year)) if year else '')
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

    # ===== 扫描作业 =====
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
                links += self._search_links_pansou(s.get('title'))
            if enable_aipan:
                links += self._search_links_aipan(s.get('title'))
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

    # ===== RSS 发现 =====
    def _discover_from_rsshub(self):
        cfg = self.get_config() or {}
        if not cfg.get('enable_rsshub', True):
            return []
        base = (cfg.get('rsshub_base') or '').rstrip('/')
        mps = (cfg.get('rsshub_movie_paths') or '').strip().splitlines()
        tvps = (cfg.get('rsshub_tv_paths') or '').strip().splitlines()
        for p in list(mps) + list(tvps):
            p = (p or '').strip()
            if not p:
                continue
            url = base + (p if p.startswith('/') else '/' + p)
            try:
                txt = self._http_get(url)
                titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', txt, re.I)
                n=0
                for t1,t2 in titles:
                    if n>=20:
                        break
                    t=(t1 or t2 or '').strip()
                    if (not t) or t.lower().startswith('rsshub'):
                        continue
                    item={'title': t, 'source': 'rsshub', 'path': p}
                    item['type']='movie' if '/movie/' in p else 'tv'
                    item['year']=None
                    item['score']=None
                    item['hot']=True
                    n+=1
                    yield item
            except Exception as e:
                self._log('warn', 'rsshub fetch fail: ' + p + ' -> ' + str(e))
        return []

    # ===== 工具函数 =====
    def _http_get(self, url: str, timeout: int = 15) -> str:
        req = _req.Request(url, headers=UA)
        with _req.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8','ignore')

    def _search_links_pansou(self, kw: str) -> List[str]:
        try:
            url = 'https://www.pansou.vip/s/' + _parse.quote(kw or '')
            html = self._http_get(url)
            ls = list(set(re.findall(r'https?://115\.com/(?:s|f)/[A-Za-z0-9]+', html, re.I) + re.findall(r'https?://115\.com/l/[A-Za-z0-9]+', html, re.I)))
            return ls[:20]
        except Exception:
            return []

    def _search_links_aipan(self, kw: str) -> List[str]:
        try:
            url = 'https://www.aipan.me/search?k=' + _parse.quote(kw or '')
            html = self._http_get(url)
            ls = list(set(re.findall(r'https?://115\.com/(?:s|f)/[A-Za-z0-9]+', html, re.I) + re.findall(r'https?://115\.com/l/[A-Za-z0-9]+', html, re.I)))
            return ls[:20]
        except Exception:
            return []

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
