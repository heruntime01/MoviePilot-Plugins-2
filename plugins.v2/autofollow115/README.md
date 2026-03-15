
# AutoFollow115 (MoviePilot v2 Plugin)

…（前略）…

## 0.3.1 更新
- TV 订阅增加总集数(尝试从豆瓣条目页解析)，在 /list 与 /progress 中返回 total_episodes
- 新增 API：
  - POST /autofollow115/unsubscribe {"title":"..."}
  - POST /autofollow115/reset_progress {"title":"..."}
- providers 捕获到的链接标题用于识别集数，进度记录新增 last_url / last_provider

注：总集数为尽力获取，可能因条目页面结构变更读取失败，届时返回 null。
