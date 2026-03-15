
# AutoFollow115 (MoviePilot v2 Plugin)

一个用于 MoviePilot v2 的自动追剧/追片插件：发现热门条目，聚合网盘搜索源，命中后将 115 分享链接推送到 MoviePilot 对话框，触发 115 自动转存。

## 功能概览
- 发现源（可并行聚合）
  - 豆瓣 m 站热门（电影/剧集）
  - RSSHub 路由（可配置自建地址与路由；预置常用的电影/剧集周榜与热度榜）
- 搜索源（聚合 + 去重 + 打分）
  - PanSou、AiPan（默认启用）
  - NullBR（可选，需站点允许匿名检索）
- 打分/过滤
  - 质量与整包偏好：2160p/1080p/HEVC/HDR/WEB-DL、整季/全集/Complete 优先
  - 集数/季集识别：SxxExx、EPxx、中文“第xx集/话”等
  - 字幕偏好加权：中字/中英/官中/熟肉/内嵌/内封等
  - include/exclude 订阅级关键词过滤
- 推送与限流
  - 命中后以文本消息推送到 MoviePilot 对话框（标题 + 115 链接），由 MP 自动转存
  - 同订阅同链接去重；每次扫描最多推送 1 条；支持每订阅每日上限 max_daily（默认 3）
  - 可选 validate_115：推送前对 115 链接做 HEAD 校验（降低失效概率）
- 进度统计（剧集）
  - 命中时记录 episodes 列表、是否整包 pack、最近一次 last_update/last_url/last_provider
  - 尝试从豆瓣条目页解析总集数 total_episodes（尽力而为，失败则为 null）

## 安装
1) 在系统配置 SystemConfigKey.UserInstalledPlugins 中加入 `autofollow115`
2) 重载/重启 MoviePilot 插件服务
3) 插件路径：`plugins.v2/autofollow115/`

## 配置（表单）
- 启用插件 enabled（默认开）
- 扫描 Cron（默认 `*/30 * * * *`）
- 优先整季/全集包 prefer_pack（默认开）
- 质量偏好 quality_prefs（2160p/1080p/HEVC/HDR/WEB-DL）
- 推送前校验 115 链接 validate_115（默认关）
- RSSHub：enable_rsshub、rsshub_base、rsshub_movie_paths、rsshub_tv_paths（多行文本，一行一个）
- NullBR：enable_nullbr、nullbr_base（可选）
- HTTP 代理 http_proxy（可选）

## API（均会被框架自动加上前缀 /autofollow115）
- GET /discover
  - 参数：type=tv|movie（默认 tv）
  - 返回：热门条目列表（包含 source 字段：douban/rsshub）
- POST /subscribe
  - 请求体：{type, title, year, include?, exclude?, max_daily?}
  - 动作：新增订阅并持久化
- POST /unsubscribe
  - 请求体：{title}
  - 动作：取消订阅
- POST /reset_progress
  - 请求体：{title}
  - 动作：清空该订阅的进度记录
- GET /list
  - 返回：订阅汇总（title/type/year、episodes_count、last_episode、pack、total_episodes、last_update）
- GET /progress
  - 返回：订阅详情（episodes 列表、pack、total_episodes、last_url、last_provider、last_update）
- POST /run
  - 动作：立即触发一次扫描

## 定时任务（服务）
- 订阅扫描：默认 `*/30 * * * *`（可在配置中修改）
- 热门刷新：`0 */6 * * *`（豆瓣 m 站 + RSSHub 合并并去重）

## 工作原理（简述）
1) Discover：合并豆瓣 m 站与 RSSHub 的热门条目，去重缓存
2) Subscribe：按 title/type/year 建立订阅规则，可配置 include/exclude 与每日推送上限
3) Scan：并行调用各 Provider 搜索 115 链接，抽取链接与标题，统一打分排序与去重
4) Filter：按订阅 include/exclude/质量/整包等策略过滤
5) Push：将 115 链接逐条推送到 MoviePilot 对话框，由 MP 自动转存；记入进度/去重

## 已知限制
- 某些站点会触发反爬或限频；已内置重试/退避与代理支持，但并不保证 100% 命中
- 集数/整包识别依赖页面文本，源站标题不规范时可能识别不完整
- total_episodes 依赖豆瓣条目页解析，失败时返回 null

## 路线图（Roadmap）
- 提升 Provider 选择器鲁棒性与备用入口
- 更多 115 链接归一化与短链展开（限频、礼貌）
- 更细粒度日志开关与调试面板
- 前端页面展示订阅/进度表格与一键操作

## 版本记录（要点）
- 0.3.1：总集数（豆瓣抓取，尽力而为）、取消订阅/重置进度 API、进度新增 last_url/last_provider
- 0.3.0：进度统计与 API（/list、/progress），Provider 捕获标题用于集数识别
- 0.2.4：订阅 include/exclude、每日推送上限 max_daily、validate_115（HEAD 校验）
- 0.2.3：评分增强（字幕/季集/质量），发现项标注来源（douban/rsshub），日志增强
- 0.2.x：集成 RSSHub 路由；NullBR 可选 Provider；整包与质量偏好；代理支持

## 0.3.2 更新
- 插件页新增表格：直接展示订阅与进度摘要（标题/类型/年份/已集数/最新集/整包/总集数/最近更新时间）。如需更丰富操作，将在后续版本加入交互按钮。
