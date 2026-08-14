# 分集完整剧本提示词模板

输入：`episode-card.md` + `series.md` + `characters.md`。

请以 JSON 输出并写入 `episodes/epXXX/script.md`：

```json
{
  "episode": 1,
  "scenes": [
    {
      "scene": 1,
      "location": "场景",
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
- 动作描写要可见、可拍摄。
- 对白稀疏化：短句优先，避免两人同时说话。
- 场景数参考短视频节奏：60 秒约 4-8 场。

