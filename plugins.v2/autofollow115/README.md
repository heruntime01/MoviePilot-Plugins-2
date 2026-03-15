
# AutoFollow115

自动追剧/电影到 115：发现 → 订阅 → 搜索 → 推送 115 链接到对话框触发自动转存。

## 功能
- 发现：基于 RSSHub（豆瓣榜单）拉取热门电影/剧集标题
- 订阅：按标题/类型（movie/tv）建立订阅项，持久化进度
- 搜索：在 PanSou/AiPan 抓取 115 链接（支持 /s /f /l 短链，去重）
- 推送：将命中 115 链接以文本推送到 MoviePilot 对话框，触发自动转存
- 定时：默认每 30 分钟扫描一次（可配置 crontab）
- 页面：
  - 设置页：Vuetify JSON（v-form/v-row/v-col/v-switch/v-text-field/v-textarea/v-select）
  - 详情页：订阅与进度 v-data-table
- 日志：内置 ring buffer + /logs API

## 安装
- 插件仓库：MoviePilot-Plugins-2（v2）
- 插件 ID：autofollow115
- `package.v2.json` 中已包含元信息；商店支持查看/更新。

## 配置
- enabled：是否启用（默认 true）
- cron_scan：扫描定时（默认 `*/30 * * * *`）
- prefer_pack：优先整季/全集包（默认 true）
- quality_prefs：质量偏好（默认 [2160p, HEVC, HDR]）
- validate_115：推送前校验 115 链接（HEAD，默认 false）
- enable_rsshub：启用 RSSHub（默认 true）
- rsshub_base：RSSHub 基址（默认 `https://rss.hrtime.asia:4000`）
- rsshub_movie_paths：电影路径（多行，一行一个）
- rsshub_tv_paths：剧集路径（多行，一行一个）
- enable_pansou：启用 PanSou 搜索（默认 true）
- enable_aipan：启用 AiPan 搜索（默认 true）
- http_proxy：HTTP 代理（形如 `http://host:port`，可选）

## API
- GET /autofollow115/discover：返回发现的条目（来自 RSSHub）
- POST /autofollow115/subscribe：{title, type, year?} → 订阅
- POST /autofollow115/unsubscribe：{id} → 取消订阅
- POST /autofollow115/reset_progress：{id} → 重置进度
- GET /autofollow115/list：订阅列表
- GET /autofollow115/progress：进度数据
- POST /autofollow115/run：立即执行一次扫描
- GET /autofollow115/logs：最近日志
- POST /autofollow115/logs/clear：清空日志

## 服务（定时任务）
- 名称：autofollow115_scan
- Cron：默认 `*/30 * * * *`（配置项 `cron_scan`）

## 使用说明
1) 在设置页启用插件，确认 RSSHub 基址可访问
2) 在“发现”接口或外部获取的标题基础上调用 /subscribe 建立订阅
3) 等待定时扫描或执行 /run，命中的 115 链接会被推送到 MoviePilot 对话框并自动转存
4) 在详情页查看订阅/进度，必要时 /unsubscribe 或 /reset_progress

## 日志
- /logs 返回最近 500 条日志；日志也写入后端日志文件（带前缀 [autofollow115]）

## 版本历史（摘）
- v0.5.1：文档补齐（官方模板 README）
- v0.5.0：重写为单文件；UI/设置/页面按 vuetify JSON；默认值常量化；清理目录；双命名资产
- v0.4.0：UI 对齐 dailysummary 风格；设置页与详情页可见
- v0.3.9：热修复字符串转义/引号导致的 SyntaxError

## 发布流程（开发者）
- 建议使用自动脚本（内部）创建 Release：
  - 更新 __init__.py 版本、package.v2.json（version/history/release）
  - 创建 Release（标签形如 AutoFollow115_vX.Y.Z）
  - 上传双命名资产（autofollow115-X.Y.Z.zip、autofollow115_vX.Y.Z.zip）
- 注：发布时可将 package.v2.json 的 release 设为 true 以在商店显示 NEW 高亮（建议保留一周）
