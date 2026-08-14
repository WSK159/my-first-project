# 角色设定生成提示词模板

输入：`series.md`。

请以 JSON 输出并写入 `characters.md`：

```json
{
  "characters": [
    {
      "id": "linwan",
      "name": "林晚",
      "role": "主角",
      "age": 26,
      "gender": "女",
      "desire": "最想要的东西",
      "wound": "过去的创伤/矛盾",
      "leverage": "秘密/筹码",
      "personality": "性格与行为模式",
      "dialogue_style": "对白风格（短句/冷/毒舌等）",
      "visual_anchor": {
        "face": "脸型/五官/发型",
        "body": "身高体态",
        "wardrobe": "标志性服装与颜色",
        "props": "标志性道具",
        "palette": "角色专属色板",
        "invariants": ["不可更改项：如单侧耳钉、红色大衣"]
      }
    }
  ],
  "cast_rules": "角色出场/主配关系",
  "voice_notes": "每个角色的音色/语气备注（供 Seed Audio 选音色）"
}
```

写作要求：

- 每个核心角色必须有：欲望 + 创伤/矛盾 + 秘密/筹码。
- 视觉锚点要具体到能直接生成角色参考图，且多集不变。
- 对白风格差异化，避免所有角色一个腔调。

