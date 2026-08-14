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

> 当前进度：阶段 0-11 已完成并通过验证（mock 全链路 + API E2E + 前端构建 + 样片检查）。
> 目标形态：30-60 集完整短剧，每集独立成片 90-180 秒（默认 120 秒），全剧总时长约 2 小时，前后人物与环境保持一致。
> 详细调研与补齐计划见 [docs/roadmap-60ep.md](docs/roadmap-60ep.md)。

### 阶段 0：项目基座

1. ✅ Git 仓库初始化、创建远程仓库并完成首次推送
2. ✅ Monorepo 骨架：`backend/`（平台）、`frontend/`（网站）、`pipeline/`（生成引擎）、`docs/`（文档）
3. ✅ 环境与密钥管理：`.env.example` 模板，密钥不入库（服务器环境变量注入）
4. ✅ 数据模型与数据库：用户、项目、任务、账单

### 阶段 1：LLM 内容引擎

5. ✅ LLM 适配层（mock / DeepSeek / OpenAI 一键切换）
6. ✅ 一句话 → 系列设定 `series.md`（题材、目标观众、可重复冲突引擎、季弧、视觉基调）
7. ✅ 角色设定 `characters.md`（欲望 / 矛盾 / 秘密 / 视觉锚点 / 对白风格）
8. ✅ 分集内容：episode-card → 完整剧本 `script.md`（场景、对白、动作、时长预算）
9. ✅ 分镜与连续视频提示词（`video-prompts.md` / `-en`，每段 8-20s）
10. ✅ 随机模式：完全随机题材 + 人设 + 冲突 + 画风

### 阶段 2：视觉资产

11. ✅ Seedream 角色形象图（正面/半身参考图，角色一致性锚点）
12. ✅ 场景 / 封面图（竖屏 9:16）
13. ⬜ 图片自动质检与重试（真实档建议开启）

### 阶段 3：视频生成

14. ✅ Seedance 任务提交、轮询、断点续传（任务恢复）
15. ✅ 连续片段生成：上一段尾帧 → 下一段首帧
16. ⬜ 片段质检与选择性重生成（真实档建议开启）
17. ⬜ 成本估算与火山资源包预检（接入 volcengine-resource-query）

### 阶段 4：音频

18. ✅ 角色音色与对白（Audio Director cue sheet）
19. ✅ 环境音 / 音乐（场景级 cue sheet）
20. ✅ 分轨生成（≤120s/请求，场景级并行）
21. ⬜ 真实档旁白严格模式与混音细化

### 阶段 5：后期合成

22. ✅ FFmpeg 拼接成片 + 音频混入
23. ✅ 字幕生成（剧本时间轴对齐）+ 烧录
24. ✅ 交付包：`final.mp4` + `novel.md` + 分集剧本 + 角色图 + 封面 + 元数据（zip）
25. ⬜ EDL 高级剪辑与 ASR 字幕校正（真实档细化）

### 阶段 6：网站平台

26. ✅ 用户注册 / 登录 / 余额
27. ✅ 一键生成页：一句话输入 + 随机按钮 + 参数（集数、单集时长、档位）
28. ✅ 任务队列与进度展示（9 阶段时间线）
29. ✅ 交付页：预览 / 下载 / 历史项目
30. ✅ 计费与成本展示（预估冻结，真实消耗记录）

### 阶段 7：部署与验收

31. ✅ Docker 化（后端含 ffmpeg、前端 nginx）+ 一键部署脚本
32. ⬜ 域名 / HTTPS（服务器配置）
33. ✅ mock 档端到端验收（真实档需配置密钥后验收）
34. ⬜ 上线与运营文档

### 阶段 8：60 集长剧架构

35. ✅ 大纲先行：全剧 30-60 集大纲表（钩子/冲突/反转/结尾悬念），逐集剧本忠实执行大纲行
36. ✅ 持久化任务表（Task：每集每步骤状态/尝试次数/错误）+ 服务重启自动恢复
37. ✅ 断点续跑：已完成产物自动跳过；失败/部分项目可一键"继续生成"
38. ✅ 失败自动重试（指数退避，最多 3 次）+ 单集失败不拖垮整剧（partial 状态）
39. ✅ 全剧一致性台账：角色形象注册表 / 场景注册表 / 全局风格锚点，图片与视频提示词统一引用
40. ✅ 分集交付规格：每集独立成片 90-180 秒（默认 120 秒），全剧约 2 小时，支持全剧合集
41. ✅ 按集预算冻结 + 实际消耗计费退款（真实档）

### 阶段 9：SSE 实时进度 + 小白前端

42. ✅ SSE 事件流（/api/projects/{id}/events）+ 前端自动断线重连
43. ✅ 题材模板库（10 个热门模板一键填充）+ 新手三步引导
44. ✅ 任务中心：项目卡片实时进度 + 失败/部分项目"继续生成"按钮
45. ✅ 分集状态网格（每集：完成/生成中/失败 + 时长 + 下载）
46. ✅ 成本预警（预估费用/出片时长/余额不足提示）+ 全剧合集下载 + 交付元数据接口

### 阶段 10：成本控制与 BYOK

47. ✅ 火山资源包预检（ListResourcePackages + Seedance fast 配额换算），估算/创建时预警与拦截
48. ✅ 实际消耗计费（按真实视频时长），冻结差额自动退款
49. ✅ 用户自带 Key（BYOK）加密管理：llm / seedream / seedance / seed_audio 四类

### 阶段 11：上线与运营

50. ✅ HTTPS 站点配置（nginx-https.conf + certbot 步骤）
51. ✅ AI 生成内容标识：字幕首行标注 + metadata.json compliance + 投稿合规说明
52. ✅ 投稿平台规格（抖音/快手/红果）自动生成 platforms.json + 静态文档 [docs/submission-spec.md](docs/submission-spec.md)
53. ✅ 运营手册 [docs/operations.md](docs/operations.md)：定价/教程/故障排查/合规红线/上线清单
54. ✅ nginx 性能与安全（gzip/长缓存/SSE 关闭缓冲/安全响应头）+ CORS 可配置收紧

## 目录结构

```text
AI短剧/
├── README.md                 # 本文件：总览 + 路线图
├── .env.example              # 环境变量模板（密钥不入库）
├── docs/
│   ├── architecture.md       # 架构与流水线设计
│   ├── api.md                # API 文档（随阶段补充）
│   ├── roadmap-60ep.md       # 60 集长剧路线图：同类项目调研 / 差距 / 成本 / 实施顺序
│   ├── submission-spec.md    # 投稿平台规格与合规（抖音/快手/红果）
│   └── operations.md         # 上线运营手册（定价/教程/排查/清单）
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

## Docker 部署

```powershell
# 复制 .env.example 为 .env 并填入密钥后：
docker compose up -d --build
# 前端 http://<服务器IP>/，API http://<服务器IP>/api/
```

一键远程部署：`python scripts/deploy/deploy_remote.py --host <ip> --user root`

## 关键约定

- 密钥（火山方舟 / 语音 / LLM）只通过 `.env` 或服务器环境变量注入，绝不提交到仓库。
- 生成的媒体文件属于运行期产物，统一放 `backend/data/`，由 `.gitignore` 排除，不入库。
- 所有代码、提示词模板、部署脚本都进 git 仓库；本地只保留工作副本。
