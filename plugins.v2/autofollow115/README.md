
# AutoFollow115 (MoviePilot v2 Plugin)

自动追剧/追片：发现(豆瓣 m 站 + RSSHub 榜单) → 订阅 → 多源搜索(PanSou/AiPan/NullBR) → 推送 115 链接到 MoviePilot 对话框（由 MP 自动转存）。

## 安装
- 将 `autofollow115` 添加到系统配置 `SystemConfigKey.UserInstalledPlugins`
- 重启或开启插件热更新

## 配置
- 启用插件、扫描 Cron（默认 */30 * * * *）
- 偏好：优先整季/全集、质量偏好（2160p/HEVC/HDR/...）
- 代理：`http_proxy` 可选（如 http://host:port）
- RSSHub：
  - `enable_rsshub` 开关（默认开）
  - `rsshub_base`（默认为你的自建 https://rss.hrtime.asia:4000）
  - `rsshub_movie_paths` / `rsshub_tv_paths`（一行一个路由）
- NullBR：
  - `enable_nullbr`（默认关）
  - `nullbr_base`（站点基址，需允许匿名检索）

## 接口
- GET /autofollow115/discover?type=tv|movie → 返回条目（包含 title/year/douban_id/source）
- POST /autofollow115/subscribe {"type":"tv","title":"...","year":2024}
- GET /autofollow115/list → 订阅清单
- POST /autofollow115/run → 手动扫描

## 行为
- 扫描周期内，按订阅逐个查询搜索源，抽取 115 链接（含 /s/ 与 /f/），评分去重后每次最多推送 1 条，避免骚扰
- 推送到 MP 对话框的文本：标题 + 115 链接（换行分隔）

## 注意
- 仅做公开信息抓取与链接聚合；请遵守各站点使用条款
- 如遇 Douban/RSSHub 或搜索源请求失败，插件会做简单重试与日志记录

### 0.2.4 新增
- 订阅支持 include / exclude 关键词过滤（任意匹配 / 任一命中排除）
- 订阅支持 max_daily 每日推送上限（默认 3）
- 可选 `validate_115`：推送前做 115 链接 HEAD 校验（降低失效链接的概率）

示例订阅 JSON：
{
  "type": "tv",
  "title": "示例剧集",
  "year": 2024,
  "include": ["中字", "2160p"],
  "exclude": ["预告", "花絮"],
  "max_daily": 2
}
