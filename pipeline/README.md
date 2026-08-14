# pipeline

独立可运行的"一键短剧"生成引擎（后续阶段逐步实现）。

```powershell
python pipeline/cli.py --idea "一句话灵感" --episodes 3 --tier mock
python pipeline/cli.py --random --episodes 3 --tier mock
```

`prompts/` 下的模板是内容引擎的核心提示词，与平台 `backend/app/services/` 各阶段一一对应。

