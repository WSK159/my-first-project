# backend

FastAPI 平台：用户、项目、任务、账单、交付。

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

API 文档：`http://127.0.0.1:8000/docs`

目录：

- `app/main.py`：应用入口
- `app/config.py`：配置
- `app/db.py`：数据库引擎
- `app/models.py`：数据模型
- `app/routers/`：认证 / 项目 / 交付 / 账单
- `app/services/`：业务服务（LLM、图片、视频、音频、合成，逐阶段实现）
- `app/workers/`：流水线编排（逐阶段实现）

