# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Tuple

class UIConfig:
    @staticmethod
    def get_form() -> Tuple[List[dict], Dict[str, Any]]:
        form = [{
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
                }
            ]
        }]
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
        }
        return form, defaults

    @staticmethod
    def get_page(subs: list, progress: dict) -> List[dict]:
        headers = [
            {'title': '标题', 'key': 'title', 'sortable': True},
            {'title': '类型', 'key': 'type'},
            {'title': '年份', 'key': 'year'},
            {'title': '总集数', 'key': 'total_episodes'},
            {'title': '已推送', 'key': 'pushed_count'},
            {'title': '最后更新', 'key': 'last_update'}
        ]
        rows = []
        for s in subs or []:
            sid = s.get('id') or s.get('title')
            pr = (progress or {}).get(sid, {})
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
                {'component': 'VDataTableVirtual', 'props': {'headers': headers, 'items': rows, 'height': '30rem', 'density': 'compact', 'fixed-header': True, 'items-per-page': 20}}
            ]
        }]
