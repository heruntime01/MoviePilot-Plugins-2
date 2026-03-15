
# AutoFollow115 (MoviePilot v2 Plugin)

…（前略）…

## 进度统计（0.3.0+）
- GET /autofollow115/list → 返回订阅的汇总信息：
  - title/type/year
  - episodes_count（已命中的集数）
  - last_episode（已命中最大集数）
  - pack（是否命中过“全集/全季/合集”）
  - last_update（最近命中时间）
- GET /autofollow115/progress → 返回每个订阅的完整剧集列表 episodes（升序）以及上述字段

注：剧集识别基于搜索结果标题/上下文的简单正则（EPxx / 第xx集等），以及“全集/全季/合集/complete”等整包关键字。若源站标注不规范，识别可能不完整。
