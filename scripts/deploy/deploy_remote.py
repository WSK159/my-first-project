"""远程部署：SSH 连接云服务器，拉取仓库并 docker compose 启动。

用法：
  $env:SSH_PASS='<服务器密码>'  # 或使用 SSH 密钥（--key）
  python scripts/deploy/deploy_remote.py --host <ip> --user root [--branch main]
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import paramiko  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="部署 AI短剧工坊到远程服务器")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--repo", default="https://github.com/WSK159/my-first-project.git")
    parser.add_argument("--key", default="", help="SSH 私钥路径（优先于密码）")
    args = parser.parse_args()

    password = os.environ.get("SSH_PASS", "")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if args.key:
        client.connect(args.host, username=args.user, key_filename=args.key, timeout=30)
    else:
        if not password:
            print("未提供密码：请设置环境变量 SSH_PASS 或使用 --key")
            return 2
        client.connect(args.host, username=args.user, password=password, timeout=30)

    commands = [
        "which git docker || true",
        "(docker compose version >/dev/null 2>&1 && echo COMPOSE_V2) || (docker-compose version >/dev/null 2>&1 && echo COMPOSE_V1) || echo NO_COMPOSE",
        f"cd /opt && (test -d my-first-project && cd my-first-project && git pull --ff-only || git clone {args.repo})",
        f"cd /opt/my-first-project && git checkout {args.branch} && git pull --ff-only",
        "cd /opt/my-first-project && (test -f .env || (cp .env.example .env && echo 'WARN: 已从 .env.example 创建 .env，请编辑填入真实密钥'))",
        "cd /opt/my-first-project && (docker compose version >/dev/null 2>&1 && docker compose up -d --build || docker-compose up -d --build)",
        "cd /opt/my-first-project && for i in $(seq 1 12); do curl -sf http://127.0.0.1/api/health && break || sleep 5; done",
        "curl -sf http://127.0.0.1/api/health && echo 'DEPLOY OK' || echo 'check manually: docker compose logs backend'",
    ]
    for cmd in commands:
        print(f"$ {cmd}")
        _stdin, stdout, stderr = client.exec_command(cmd, timeout=1200)
        out = stdout.read().decode("utf-8", "ignore")
        err = stderr.read().decode("utf-8", "ignore")
        print(out)
        if err.strip():
            print("stderr:", err[:500])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
