# -*- coding: utf-8 -*-
import datetime, re
from typing import Any, Dict, List, Tuple
from urllib import request as _req
from urllib import parse as _parse

from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.log import logger
from app.core.config import settings
from apscheduler.triggers.cron import CronTrigger

UA={'User-Agent':'Mozilla/5.0'}

REGION_OPTS=['大陆','欧美','日韩']
GENRE_OPTS=['剧情','喜剧','悬疑','动作','爱情','科幻','犯罪','动画','纪录片','战争','古装','武侠','奇幻','家庭','恐怖','历史','音乐']

class AutoFollow115(_PluginBase):
    plugin_name = 'AutoFollow115'
    plugin_desc = '自动追剧/电影到 115：发现→筛选→订阅→搜索→推送→进度（独立于系统订阅）'
    plugin_icon = 'autofollow115.png'
    plugin_color = '#5E81AC'
    plugin_version = '0.6.5'
    plugin_author = 'heruntime01'
    author_url = 'https://github.com/heruntime01'
    plugin_config_prefix = 'autofollow115_'
    plugin_order = 30
    auth_level = 1

    _enabled: bool = True
    _logs: List[Dict[str, Any]] = []

    def init_plugin(self, config: dict = None):
        cfg = config or {}
        self._enabled = bool(cfg.get('enabled', True))
        self._logs = self.get_data('logs') or []
        self.save_data('subs', self.get_data('subs') or [])
        self.save_data('progress', self.get_data('progress') or {})
        self.save_data('candidates', self.get_data('candidates') or [])
        sub_title = (cfg.get('subscribe_title') or '').strip()
        sub_type = (cfg.get('subscribe_type') or 'tv')
        sub_year = (cfg.get('subscribe_year') or '').strip()
        if sub_title:
            self._add_subscription(sub_title, sub_type, (sub_year or None), source='settings')
            try:
                self.update_config({'subscribe_title': '', 'subscribe_year': ''})
            except Exception:
                pass
        try:
            self._refresh_candidates()
        except Exception as e:
            self._log_step('discover', 'init refresh candidates failed', {'error': str(e)})
        self._log_step('init', 'plugin initialized')

    def get_state(self) -> bool:
        return self._enabled

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        form = [
            {'component': 'VForm','content': [
                {'component': 'VRow','content': [
                    {'component': 'VCol','props': {'cols':12,'md':3},'content':[{'component':'VSwitch','props':{'model':'enabled','label':'启用插件'}}]},
                    {'component': 'VCol','props': {'cols':12,'md':3},'content':[{'component':'VCronField','props':{'model':'cron_scan','label':'扫描 Cron'}}]},
                    {'component': 'VCol','props': {'cols':12,'md':3},'content':[{'component':'VCronField','props':{'model':'cron_discover','label':'候选刷新 Cron'}}]},
                    {'component': 'VCol','props': {'cols':12,'md':3},'content':[{'component':'VSwitch','props':{'model':'prefer_pack','label':'优先整季/全集包'}}]},
                ]},
                {'component': 'VRow','content': [
                    {'component': 'VCol','props': {'cols':12,'md':6},'content':[{'component':'VSelect','props':{'model':'quality_prefs','label':'质量偏好','items':['2160p','1080p','HEVC','HDR','WEB-DL'],'multiple':True,'chips':True}}]},
                    {'component': 'VCol','props': {'cols':12,'md':6},'content':[{'component':'VSwitch','props':{'model':'validate_115','label':'推送前校验 115 链接(HEAD)'}}]},
                ]},
                {'component':'VDivider'},
                {'component':'VSubheader','props':{'text':'RSSHub 来源与筛选'}},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12,'md':4},'content':[{'component':'VSwitch','props':{'model':'enable_rsshub','label':'启用 RSSHub'}}]},
                    {'component':'VCol','props':{'cols':12,'md':8},'content':[{'component':'VTextField','props':{'model':'rsshub_base','label':'RSSHub 基址'}}]},
                ]},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VTextarea','props':{'model':'rsshub_movie_paths','label':'电影路径(一行一个)','rows':6}}]},
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VTextarea','props':{'model':'rsshub_tv_paths','label':'剧集路径(一行一个)','rows':6}}]},
                ]},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12,'md':4},'content':[{'component':'VSelect','props':{'model':'filter_regions','label':'地区筛选','items':REGION_OPTS,'multiple':True,'chips':True}}]},
                    {'component':'VCol','props':{'cols':12,'md':4},'content':[{'component':'VSelect','props':{'model':'filter_genres','label':'类型筛选','items':GENRE_OPTS,'multiple':True,'chips':True}}]},
                    {'component':'VCol','props':{'cols':12,'md':4},'content':[{'component':'VTextField','props':{'model':'max_candidates','label':'候选数量(15~20 推荐)'}}]},
                ]},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VTextarea','props':{'model':'include_keywords','label':'包含关键词(一行一个)','rows':4}}]},
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VTextarea','props':{'model':'exclude_keywords','label':'排除关键词(一行一个)','rows':4}}]},
                ]},
                {'component':'VDivider'},
                {'component':'VSubheader','props':{'text':'可选：搜索源与代理'}},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VSwitch','props':{'model':'enable_pansou','label':'启用 PanSou'}}]},
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VSwitch','props':{'model':'enable_aipan','label':'启用 AiPan'}}]},
                ]},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12},'content':[{'component':'VTextField','props':{'model':'http_proxy','label':'HTTP 代理 (http://host:port)'}}]},
                ]},
                {'component':'VDivider'},
                {'component':'VSubheader','props':{'text':'手动订阅（保存设置后立即添加）'}},
                {'component':'VRow','content':[
                    {'component':'VCol','props':{'cols':12,'md':6},'content':[{'component':'VTextField','props':{'model':'subscribe_title','label':'标题'}}]},
                    {'component':'VCol','props':{'cols':6,'md':3},'content':[{'component':'VSelect','props':{'model':'subscribe_type','label':'类型','items':[{'title':'电视剧','value':'tv'},{'title':'电影','value':'movie'}]}}]},
                    {'component':'VCol','props':{'cols':6,'md':3},'content':[{'component':'VTextField','props':{'model':'subscribe_year','label':'年份(可选)'}}]},
                ]},
            ]}
        ]
        defaults = {
            'enabled': True,
            'cron_scan': '*/30 * * * *',
            'cron_discover': '0 8 * * *',
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
/douban/movie/weekly/tv_hot
""",
            'filter_regions': [],
            'filter_genres': [],
            'max_candidates': '20',
            'include_keywords': '',
            'exclude_keywords': '',
            'enable_pansou': True,
            'enable_aipan': True,
            'http_proxy': None,
            'subscribe_title': '',
            'subscribe_type': 'tv',
            'subscribe_year': ''
        }
        return form, defaults

    def get_page(self) -> List[dict]:
        items = self.get_data('candidates') or []
        cards = []
        for it in items[:20]:
            title = it.get('title'); poster = it.get('poster'); mtype = it.get('type'); year = it.get('year'); douban = it.get('douban'); region = it.get('region'); genres = it.get('genres') or []
            cards.append({'component':'VCard','props':{'class':'w-56'},'content':[
                {'component':'VImg','props':{'src': poster, 'height':180, 'cover':True}},
                {'component':'VCardTitle','props':{'class':'text-truncate','title':title},'text':title},
                {'component':'VCardText','text': (region or '') + ' ' + ('/'.join(genres) if genres else '')},
                {'component':'VCardActions','content':[
                    {'component':'VBtn','props':{'size':'small','color':'primary'},'text':'订阅','events':{'click':{'api':'plugin/AutoFollow115/subscribe','method':'post','params':{'title':title,'type':mtype,'year':year,'apikey': settings.API_TOKEN}}}},
                    {'component':'VBtn','props':{'size':'small','variant':'text'},'text':'豆瓣','events':{'click':{'api':'open','method':'get','params':{'url':'https://movie.douban.com/subject/'+str(douban) if douban else 'https://movie.douban.com/'}}}},
                ]}
            ]})
        grid={'component':'div','props':{'class':'grid gap-3 grid-info-card'},'content':cards}
        subs = self.get_data('subs') or []
        prog = self.get_data('progress') or {}
        headers=[{'title':'标题','key':'title','sortable':True},{'title':'类型','key':'type'},{'title':'年份','key':'year'},{'title':'已推送','key':'pushed_count'},{'title':'最后更新','key':'last_update'}]
        rows=[]
        for s in subs:
            sid = s.get('id') or s.get('title')
            pr = prog.get(sid, {})
            rows.append({'title': s.get('title'), 'type': s.get('type'), 'year': s.get('year'), 'pushed_count': len(pr.get('pushed') or []), 'last_update': pr.get('last_update')})
        table={'component':'VDataTableVirtual','props':{'headers':headers,'items':rows,'height':'26rem','density':'compact','fixed-header':True,'items-per-page':20}}
        return [
            {'component':'VCard','props':{'title':'今日候选（按筛选）'},'content':[grid]},
            {'component':'VCard','props':{'title':'我的订阅与进度'},'content':[table]},
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {'path':'/discover','methods':['GET'],'endpoint': self.api_discover, 'summary':'发现候选（返回并刷新）'},
            {'path':'/subscribe','methods':['POST'],'endpoint': self.api_subscribe, 'summary':'订阅'},
            {'path':'/unsubscribe','methods':['POST'],'endpoint': self.api_unsubscribe, 'summary':'退订'},
            {'path':'/reset_progress','methods':['POST'],'endpoint': self.api_reset_progress, 'summary':'重置进度'},
            {'path':'/list','methods':['GET'],'endpoint': self.api_list, 'summary':'订阅列表'},
            {'path':'/progress','methods':['GET'],'endpoint': self.api_progress, 'summary':'进度'},
            {'path':'/run','methods':['POST'],'endpoint': self.api_run, 'summary':'立即扫描'},
            {'path':'/logs','methods':['GET'],'endpoint': self.api_logs, 'summary':'日志'},
            {'path':'/logs/clear','methods':['POST'],'endpoint': self.api_logs_clear, 'summary':'清空日志'},
        ]

    def get_service(self) -> List[dict]:
        if not self._enabled:
            return []
        cfg = self.get_config() or {}
        cron_scan = cfg.get('cron_scan') or '*/30 * * * *'
        cron_disc = cfg.get('cron_discover') or '0 8 * * *'
        svcs=[]
        try:
            svcs.append({'id':'AutoFollow115_scan','name':'AutoFollow115 扫描','trigger':CronTrigger.from_crontab(cron_scan),'func':self.job_scan,'kwargs':{}})
        except Exception as e:
            logger.warning('scan Cron 无效：' + str(cron_scan) + '；回退 interval=30min；' + str(e))
            svcs.append({'id':'AutoFollow115_scan','name':'AutoFollow115 扫描','trigger':'interval','func':self.job_scan,'kwargs':{'minutes':30}})
        try:
            svcs.append({'id':'AutoFollow115_discover','name':'AutoFollow115 候选刷新','trigger':CronTrigger.from_crontab(cron_disc),'func':self.job_refresh_candidates,'kwargs':{}})
        except Exception as e:
            logger.warning('discover Cron 无效：' + str(cron_disc) + '；回退 interval=24h；' + str(e))
            svcs.append({'id':'AutoFollow115_discover','name':'AutoFollow115 候选刷新','trigger':'interval','func':self.job_refresh_candidates,'kwargs':{'hours':24}})
        return svcs

    def stop_service(self):
        pass

    def api_discover(self, **kwargs):
        try:
            cnt = self._refresh_candidates()
            return self.success(data={'count': cnt, 'items': self.get_data('candidates') or []})
        except Exception as e:
            self._log_step('discover', 'api discover failed', {'error': str(e)})
            return self.error(str(e))

    def api_subscribe(self, **kwargs):
        data = kwargs.get('data') or {}
        title = (data.get('title') or '').strip()
        tp = data.get('type') or 'tv'
        year = data.get('year')
        if not title:
            return self.error('title required')
        ok, sid = self._add_subscription(title, tp, year, source='api')
        if ok:
            return self.success(msg='subscribed', data={'id': sid})
        return self.success(msg='already subscribed', data={'id': sid})

    def api_unsubscribe(self, **kwargs):
        data = kwargs.get('data') or {}
        sid = data.get('id')
        subs = [s for s in (self.get_data('subs') or []) if s.get('id')!=sid]
        self.save_data('subs', subs)
        prog = self.get_data('progress') or {}
        if sid in prog:
            prog.pop(sid, None)
            self.save_data('progress', prog)
        self._log_step('subscribe', 'unsubscribed', {'sid': sid})
        return self.success(msg='unsubscribed')

    def api_reset_progress(self, **kwargs):
        data = kwargs.get('data') or {}
        sid = data.get('id')
        prog = self.get_data('progress') or {}
        if sid in prog:
            prog[sid] = {'pushed': [], 'last_update': None, 'total_episodes': prog[sid].get('total_episodes')}
            self.save_data('progress', prog)
        self._log_step('progress', 'reset', {'sid': sid})
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
            self._log_step('scan', 'api run failed', {'error': str(e)})
            return self.error(str(e))

    def api_logs(self, **kwargs):
        return self.success(data={'logs': self._logs[-1000:]})

    def api_logs_clear(self, **kwargs):
        self._logs = []
        self.save_data('logs', self._logs)
        return self.success(msg='cleared')

    def job_scan(self):
        if not self._enabled:
            return
        subs = self.get_data('subs') or []
        if not subs:
            return
        cfg = self.get_config() or {}
        enable_pansou = bool(cfg.get('enable_pansou', True))
        enable_aipan = bool(cfg.get('enable_aipan', True))
        self._log_step('scan', 'start', {'subs': len(subs), 'pansou': enable_pansou, 'aipan': enable_aipan})
        pushed = 0
        for s in subs:
            title = s.get('title'); tp = s.get('type'); sid = s.get('id')
            self._log_step('scan', 'search begin', {'sid': sid, 'title': title, 'type': tp})
            links = []
            if enable_pansou:
                ls = self._search_links_pansou(title)
                self._log_step('scan', 'pansou results', {'count': len(ls)})
                links += ls
            if enable_aipan:
                la = self._search_links_aipan(title)
                self._log_step('scan', 'aipan results', {'count': len(la)})
                links += la
            links = list({*links})
            self._log_step('scan', 'merge results', {'total': len(links)})
            if not links:
                continue
            link = links[0]
            msg = '[115自动追剧] 命中：' + str(title) + chr(10) + str(link)
            self.post_message(mtype=NotificationType.Plugin, title='AutoFollow115', text=msg)
            prog = self.get_data('progress') or {}
            pr = prog.get(sid, {'pushed': [], 'last_update': None, 'total_episodes': None})
            pr['pushed'] = list(set(pr.get('pushed') or []) | {link})
            pr['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            prog[sid] = pr
            self.save_data('progress', prog)
            pushed += 1
            self._log_step('scan', 'pushed', {'sid': sid, 'link': link})
        self._log_step('scan', 'done', {'pushed': pushed})

    def job_refresh_candidates(self):
        try:
            cnt = self._refresh_candidates()
            self._log_step('discover', 'refresh scheduled done', {'count': cnt})
        except Exception as e:
            self._log_step('discover', 'refresh scheduled failed', {'error': str(e)})

    def _refresh_candidates(self) -> int:
        raw = list(self._discover_from_rsshub())
        cfg = self.get_config() or {}
        maxn = int(str(cfg.get('max_candidates') or '20') or '20')
        items=[]
        for it in raw:
            if self._candidate_pass(it, cfg):
                items.append(it)
            if len(items) >= maxn:
                break
        self.save_data('candidates', items)
        return len(items)

    def _candidate_pass(self, it: Dict[str,Any], cfg: Dict[str,Any]) -> bool:
        regs = set(cfg.get('filter_regions') or [])
        gens = set(cfg.get('filter_genres') or [])
        incs = [x.strip().lower() for x in (cfg.get('include_keywords') or '').splitlines() if x.strip()]
        excs = [x.strip().lower() for x in (cfg.get('exclude_keywords') or '').splitlines() if x.strip()]
        title = (it.get('title') or '').lower()
        if incs and not any(k in title for k in incs):
            return False
        if any(k in title for k in excs):
            return False
        if regs:
            r = (it.get('region') or '').strip()
            if r and r not in regs:
                return False
        if gens:
            gs = set(it.get('genres') or [])
            if gs and gs.isdisjoint(gens):
                return False
        return True

    def _discover_from_rsshub(self):
        cfg = self.get_config() or {}
        if not cfg.get('enable_rsshub', True):
            return []
        base = (cfg.get('rsshub_base') or '').rstrip('/')
        mps = (cfg.get('rsshub_movie_paths') or '').strip().splitlines()
        tvps = (cfg.get('rsshub_tv_paths') or '').strip().splitlines()
        paths = [p.strip() for p in (list(mps)+list(tvps)) if (p and p.strip())]
        for p in paths:
            url = base + (p if p.startswith('/') else '/' + p)
            total=0; empty_link=0; yielded=0
            try:
                xml = self._http_get(url)
                for item_xml in re.split(r'</item>', xml, flags=re.I):
                    title = self._xml_tag(item_xml, 'title')
                    link = self._xml_tag(item_xml, 'link')
                    desc = self._xml_tag(item_xml, 'description')
                    if not (title or link):
                        continue
                    total += 1
                    if not (link and link.strip()):
                        empty_link += 1
                    poster = self._first_img(desc)
                    doubanid = self._first_douban_id(link)
                    region = self._extract_region(desc)
                    genres = self._extract_genres(desc)
                    item={'title': title, 'poster': poster, 'link': link, 'douban': doubanid, 'region': region, 'genres': genres}
                    item['type']='movie' if '/movie/' in p else 'tv'
                    item['year']=self._extract_year(desc)
                    yielded += 1
                    yield item
                self._log_step('discover', 'rsshub parsed', {'path': p, 'total': total, 'empty_link': empty_link, 'yielded': yielded})
            except Exception as e:
                self._log_step('discover', 'rsshub fetch fail', {'path': p, 'error': str(e)})
        return []

    def _http_get(self, url: str, timeout: int = 15) -> str:
        req = _req.Request(url, headers=UA)
        with _req.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8','ignore')

    def _xml_tag(self, xml: str, tag: str) -> str:
        if not xml:
            return ''
        m = re.search(r'<'+tag+r'>\s*(?:<!\[CDATA\[(.*?)\]\]>|(.*?))\s*</'+tag+r'>', xml, re.I|re.S)
        if not m:
            return ''
        return (m.group(1) or m.group(2) or '').strip()

    def _first_img(self, html: str) -> str:
        if not html:
            return ''
        m = re.search(r"<img[^>]+src=["']([^"']+)["']", html, re.I)
        return (m.group(1).strip() if m else '')

    def _first_douban_id(self, link: str) -> str:
        if not link:
            return ''
        m = re.search(r'/subject/(\d+)', link)
        if not m:
            m = re.search(r'/(\d{5,})(?:$|[/?#])', link)
        return (m.group(1) if m else '')

    def _extract_year(self, text: str) -> str:
        if not text:
            return None
        m = re.search(r'(19\d{2}|20\d{2})', text)
        return (m.group(1) if m else None)

    def _extract_region(self, text: str) -> str:
        if not text:
            return ''
        m = re.search(r'(?:地区|制片国家/地区)[：: ]([^<
]+)', text)
        if m:
            val=(m.group(1) or '').strip()
            for key in REGION_OPTS:
                if key in val:
                    return key
            if '中国' in val or '内地' in val or '香港' in val or '台湾' in val:
                return '大陆'
            if any(x in val for x in ['日本','韩国']):
                return '日韩'
            return '欧美'
        return ''

    def _extract_genres(self, text: str) -> List[str]:
        if not text:
            return []
        m = re.search(r'(?:类型)[：: ]([^<
]+)', text)
        if not m:
            return []
        raw=(m.group(1) or '').strip()
        parts=re.split(r'[ /、，,]', raw)
        ret=[]
        for p in parts:
            p=p.strip()
            if not p:
                continue
            for g in GENRE_OPTS:
                if p.startswith(g) or g in p:
                    if g not in ret:
                        ret.append(g)
        return ret

    def _add_subscription(self, title: str, tp: str, year: Any, source: str='api'):
        subs = self.get_data('subs') or []
        sid = title + ':' + tp + ((':' + str(year)) if year else '')
        if any((s.get('id')==sid) for s in subs):
            self._log_step('subscribe', 'exists', {'sid': sid, 'title': title, 'type': tp, 'year': year, 'source': source})
            return False, sid
        subs.append({'id': sid, 'title': title, 'type': tp, 'year': year})
        self.save_data('subs', subs)
        prog = self.get_data('progress') or {}
        prog.setdefault(sid, {'pushed': [], 'last_update': None, 'total_episodes': None})
        self.save_data('progress', prog)
        self._log_step('subscribe', 'added', {'sid': sid, 'title': title, 'type': tp, 'year': year, 'source': source})
        return True, sid

    def _log_step(self, phase: str, msg: str, ctx: Dict[str,Any]=None):
        rec = {'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'phase': phase,'msg': msg,'ctx': (ctx or {})}
        logs = self._logs or []
        logs.append(rec)
        self._logs = logs[-2000:]
        self.save_data('logs', self._logs)
        try:
            logger.info('[autofollow115][' + phase + '] ' + msg + ' ' + str(ctx or {}))
        except Exception:
            pass
