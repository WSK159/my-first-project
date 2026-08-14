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

## 域名与 HTTPS（上线）

1. 把域名 A 记录指向服务器 IP，等待生效。
2. 安装 certbot：`apt install -y certbot python3-certbot-nginx`
3. 签发证书：`certbot certonly --nginx -d your.domain.com`（需 80 端口可访问）
4. 把本目录 `nginx-https.conf` 复制到 `/etc/nginx/conf.d/`，并把其中的 `your.domain.com` 替换为真实域名。
5. 若 docker 前端已占用 80，改用 8080 端口映射（`docker-compose.yml` 中 `frontend: "8080:80"`）后 `nginx -s reload`。
6. 配置 `.env`：`CORS_ORIGINS=https://your.domain.com`
7. 重启容器：`docker compose up -d --force-recreate`

> 提示：证书每 90 天自动续期（certbot 自带 timer）。国内服务器需先完成 ICP 备案才能使用 80/443。
