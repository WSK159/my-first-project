# 部署说明

## 前置条件（服务器）

- 已安装 Docker 与 docker compose 插件
- 已安装 git
- 开放 80 端口（前端 + API 反向代理）

## 部署

```powershell
# 1. 在仓库根目录准备 .env（复制 .env.example 并填入火山方舟/语音/LLM 密钥）
# 2. 执行部署脚本
$env:SSH_PASS='服务器密码'
python scripts/deploy/deploy_remote.py --host 你的服务器IP --user root
```

服务器端脚本会：

1. 克隆/更新 `/opt/my-first-project`
2. `docker compose up -d --build` 构建并启动后端（含 ffmpeg）与前端（nginx）
3. 健康检查

## 本机一键启动（开发）

```powershell
cd backend
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm run dev   # http://localhost:5173
```

## 密钥

- 火山方舟（Seedream/Seedance）：https://ark.volcengine.com/region:cn-beijing/apiKey
- 火山语音（Seed Audio）：https://console.volcengine.com/speech/new/setting/apikeys
- LLM：DeepSeek / OpenAI 任选

密钥只放服务器 `.env`，不提交仓库。

