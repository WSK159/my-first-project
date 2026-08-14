# 连续视频提示词生成模板

输入：`script.md` + 角色参考图。

请为每集生成 `video-prompts.md`（中文）与 `video-prompts-en.md`（模型需要时），每个 clip 对应一段 8-20s 的连续叙事镜头：

```json
{
  "episode": 1,
  "clips": [
    {
      "clip": "clip-01",
      "source_beat": "对应剧本场景/节拍",
      "duration_hint": 10,
      "references": {"images": ["角色参考图路径"], "purpose": "保持角色身份/服装一致"},
      "timeline_beats": ["起：", "中：", "转：", "合："],
      "continuity_rules": ["保持脸型/发型/服装不变", "从上一段尾帧状态开始"],
      "camera": "单一主导运镜",
      "dialogue_audio": "对白窗口或音频需求（如无则空）",
      "negative": ["多人同框", "文字水印", "穿帮动作"],
      "ending_frame": "结尾画面/交接点",
      "rerun_notes": "失败重跑的调整方向"
    }
  ]
}
```

写作要求（Seedance/即梦风格）：

- 一段提示词 = 一个连贯 8-20s 电影瞬间，不是机械分镜表。
- 用可见动作代替抽象情绪。
- 参考角色网格：脸、年龄、服装、体态、风格、标志道具。
- 每段一个主导运镜，不混冲突机位。
- 关键揭示不要放在头尾 0.5 秒。

