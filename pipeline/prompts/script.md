# 分集完整剧本提示词模板

输入：`episode-card.md` + `series.md` + `characters.md`。

请以 JSON 输出并写入 `episodes/epXXX/script.md`：

```json
{
  "episode": 1,
  "scenes": [
    {
      "scene": 1,
      "scene_id": "scene01",
      "location": "场景名（与场景注册表一致）",
      "time": "日/夜",
      "beat": "节拍：这段要达成什么叙事目标",
      "duration_seconds": 12,
      "actions": ["连续可见动作（供视频提示词复用）"],
      "dialogue": [
        {"speaker": "林晚", "line": "台词", "emotion": "情绪/语气"}
      ],
      "camera": "本场景主导运镜（推/拉/跟/固定）"
    }
  ],
  "narration": "可选的画外旁白（如需要）",
  "total_seconds": 60
}
```

写作要求：

- 每场戏时长可加总为整集时长。
- 每场戏的 scene_id 必须引用一致性台账中的场景编号；location 名称必须与场景注册表完全一致。
- 场景内的道具、光线、陈设必须与场景注册表一致，不得自由发挥。
- 动作描写要可见、可拍摄。
- 对白稀疏化：短句优先，避免两人同时说话。
- 场景数参考短视频节奏：90 秒约 6-9 场，120 秒约 8-12 场，180 秒约 10-15 场；每场 10-15 秒。
- 每场至少一个可拍的动作节拍（供分镜直接复用）。
