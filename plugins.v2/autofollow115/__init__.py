from typing import Any, Dict, List, Optional, Tuple
from apscheduler.triggers.cron import CronTrigger
from app.plugins import _PluginBase
from app.schemas import NotificationType

class _DummyProvider:
    name = "dummy"
    def search(self, **kwargs):
        return []

class AutoFollow115(_PluginBase):
    plugin_name = "115 自动追剧"
    plugin_desc = "订阅豆瓣热门，聚合网盘搜索源，命中后推送 115 链接到对话框自动转存"
    plugin_version = "0.1.0"
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
        self._providers = [_DummyProvider()]

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [{"cmd": "/af115", "event": None, "desc": "显示插件说明/快速命令", "category": "订阅"}]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/discover", "endpoint": self.api_discover, "methods": ["GET"], "auth": "apikey",
             "summary": "获取热门列表", "description": "type=tv|movie"},
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
        ]
        defaults = {
            "enabled": True,
            "cron_scan": "*/30 * * * *",
            "prefer_pack": True,
            "quality_prefs": ["2160p", "HEVC", "HDR"]
        }
        return form, defaults

    def get_page(self) -> Optional[List[dict]]:
        return [{"component": "v-alert", "props": {"type": "info", "text": "在“发现”页选择条目后订阅，命中将推送 115 链接至对话框"}}]

    def get_service(self) -> List[Dict[str, Any]]:
        cron_scan = self._conf.get("cron_scan") or "*/30 * * * *"
        return [
            {"id": "af115-scan", "name": "订阅扫描", "trigger": CronTrigger.from_crontab(cron_scan), "func": self.job_scan, "kwargs": {}},
            {"id": "af115-discover", "name": "热门刷新", "trigger": CronTrigger.from_crontab("0 */6 * * *"), "func": self.job_discover, "kwargs": {}},
        ]

    def job_discover(self, **kwargs):
        self._discover_cache["tv"] = [
            {"title": "示例剧集 A", "year": 2024, "douban_id": "tv001"},
            {"title": "示例剧集 B", "year": 2023, "douban_id": "tv002"},
        ]
        self._discover_cache["movie"] = [
            {"title": "示例电影 X", "year": 2024, "douban_id": "m001"},
            {"title": "示例电影 Y", "year": 2022, "douban_id": "m002"},
        ]

    def job_scan(self, **kwargs):
        subs = self.get_data("subs") or []
        for _s in subs:
            pass

    def _push_115(self, title: str, url: str):
        text = f"{title}
{url}"
        self.post_message(mtype=NotificationType.Text, title="[115自动追剧] 命中", text=text)

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
