# AI短剧工坊（AI Short Drama Studio）

一个"一句话 / 完全随机 → 可直接投稿的完整短剧"的一键生成网站。

输入一句话（或点击随机），系统自动完成：完整小说 → 人物形象图 → 每集具体内容（剧本）→ 分镜视频 → 配音与音乐 → 后期合成 → 交付包（成片 + 小说 + 剧本 + 角色图 + 封面 + 元数据）。

## 技术栈

- 后端：Python / FastAPI / SQLAlchemy / SQLite（生产可换 PostgreSQL）
- 前端：Vue 3 + Vite（分阶段引入）
- 任务：后台队列（in-process worker → 后续可换 Celery/Redis）
- 内容引擎：DeepSeek / OpenAI 兼容 LLM（可插拔，含 mock）
- 视觉：火山方舟 Seedream（角色/场景/封面图）
- 视频：火山方舟 Seedance（分段生成 + 尾帧衔接）
- 音频：火山语音 Seed Audio（对白 TTS / 旁白 / 环境音 / 音乐）
- 后期：FFmpeg（拼接 / 混音 / 字幕烧录）

## 分步实施路线图

### 阶段 0：项目基座

1. Git 仓库初始化、创建远程仓库并完成首次推送
2. Monorepo 骨架：`backend/`（平台）、`frontend/`（网站）、`pipeline/`（生成引擎）、`docs/`（文档）
3. 环境与密钥管理：`.env.example` 模板，密钥不入库（服务器环境变量注入）
4. 数据模型与数据库：用户、项目、系列、角色、分集、任务、账单

### 阶段 1：LLM 内容引擎

5. LLM 适配层（mock / DeepSeek / OpenAI 一键切换）
6. 一句话 → 系列设定 `series.md`（题材、目标观众、可重复冲突引擎、季弧、视觉基调）
7. 角色设定 `characters.md`（欲望 / 矛盾 / 秘密 / 视觉锚点 / 对白风格）
8. 分集内容：episode-card → 完整剧本 `script.md`（场景、对白、动作、时长预算）
9. 分镜与连续视频提示词（`video-prompts.md` / `-en`，每段 8-20s）
10. 随机模式：完全随机题材 + 人设 + 冲突 + 画风

### 阶段 2：视觉资产

11. Seedream 角色形象图（正面/半身参考图，角色一致性锚点）
12. 场景 / 关键道具 / 封面图（竖屏 9:16）
13. 图片自动质检与重试

### 阶段 3：视频生成

14. Seedance 任务提交、轮询、断点续传（任务恢复）
15. 连续片段生成：上一段尾帧 → 下一段首帧
16. 片段质检与选择性重生成
17. 成本估算与火山资源包预检

### 阶段 4：音频

18. 角色音色库与对白 TTS
19. 旁白生成（`只朗读...读完立即停止` 严格模式）
20. 环境音 / 音效 / 音乐（Audio Director cue sheet）
21. 分轨生成与混音（≤120s/请求，长音频分段并行）

### 阶段 5：后期合成

22. FFmpeg 拼接与 EDL 剪辑（硬切 / 转场）
23. 音频混入成片
24. 字幕生成（脚本对齐 / ASR）+ 烧录
25. 交付包：`final.mp4` + `novel.md` + 分集剧本 + 角色图 + 封面 + 元数据（zip）

### 阶段 6：网站平台

26. 用户注册 / 登录 / 余额
27. 一键生成页：一句话输入 + 随机按钮 + 参数（集数、单集时长、题材、画风、档位）
28. 任务队列与进度展示（小说 → 人设 → 视频 → 音频 → 合成 → 交付）
29. 交付页：预览 / 下载 / 历史项目
30. 计费与成本展示（LLM token + 视频秒数，平台加价）

### 阶段 7：部署与验收

31. Docker 化与云服务器部署
32. 域名 / HTTPS（可选）
33. 端到端验收（mock 档 → 真实档）
34. 上线与运营文档（定价、内容规范、投稿说明）

## 目录结构

```text
AI短剧/
├── README.md                 # 本文件：总览 + 路线图
├── .env.example              # 环境变量模板（密钥不入库）
├── docs/
│   ├── architecture.md       # 架构与流水线设计
│   └── api.md                # API 文档（随阶段补充）
├── backend/                  # FastAPI 平台
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # 应用入口
│   │   ├── config.py         # 配置（pydantic-settings）
│   │   ├── db.py             # 数据库
│   │   ├── models.py         # 数据模型
│   │   ├── schemas.py        # 请求/响应模型
│   │   ├── routers/          # 路由（auth/projects/delivery/billing）
│   │   ├── services/         # 业务服务（llm/series/images/videos/audio...）
│   │   └── workers/          # 后台任务
│   └── data/                 # 运行时数据（不入库）
├── frontend/                 # Web 前端（Vue 3 + Vite，后续引入）
├── pipeline/                 # 生成引擎（可独立 CLI 运行）
│   ├── prompts/              # 各阶段提示词模板
│   ├── adapters/             # LLM/图像/视频/音频适配器
│   └── cli.py                # 一键流水线 CLI
└── scripts/
    ├── init_db.py            # 初始化数据库
    └── deploy/               # 部署脚本（阶段 7）
```

## 运行（开发）

```powershell
# 1. 初始化数据库
python scripts/init_db.py

# 2. 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 3. 打开前端
cd frontend
npm install && npm run dev
```

## 关键约定

- 密钥（火山方舟 / 语音 / LLM）只通过 `.env` 或服务器环境变量注入，绝不提交到仓库。
- 生成的媒体文件属于运行期产物，统一放 `backend/data/`，由 `.gitignore` 排除，不入库。
- 所有代码、提示词模板、部署脚本都进 git 仓库；本地只保留工作副本。

