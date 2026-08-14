# 分集剧情卡提示词模板

输入：`series.md` + `characters.md` + 集号。

请以 JSON 输出并写入 `episodes/epXXX/episode-card.md`：

```json
{
  "episode": 1,
  "runtime_seconds": 120,
  "opening_hook": "第1-3秒可见的开场钩子（画面动作，不是旁白介绍）",
  "emotional_hook": "情绪钩子",
  "main_conflict": "本集核心冲突（必须能拍成动作/表情/道具/对白窗口）",
  "escalation": "升级：冲突如何加剧",
  "reversal": "反转/揭示",
  "ending_hook": "结尾钩子（交接下一集）",
  "characters": ["出场角色id"],
  "locations": ["scene01", "scene02"],
  "continuity": "与前集/系列设定的连续性约束"
}
```

写作要求：

- 开场 1-3 秒必须是可见钩子，拒绝纯铺垫。
- locations 必须引用系列设定/一致性台账中的场景编号（scene01 起），不得发明新场景。
- 出场角色必须来自角色设定，且遵守 cast_rules 的出场节奏。
- 冲突要能"演出来"，而不是心理描写。
- 反转与结尾钩子必须明确。
