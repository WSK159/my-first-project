# API 文档

基础地址：`/api`（开发代理 `http://127.0.0.1:8000/api`）

## 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册（赠送体验余额），返回 access_token |
| POST | `/api/auth/login` | 登录，返回 access_token |

除注册/登录外，接口需请求头 `Authorization: Bearer <token>`。

## 项目

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/projects/estimate` | 成本预估 |
| POST | `/api/projects` | 创建项目并启动流水线 |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/{id}` | 项目详情（status/progress/stage） |
| DELETE | `/api/projects/{id}` | 删除项目与产物 |

创建请求体：

```json
{
  "idea": "一句话灵感（可空）",
  "random_mode": false,
  "genre": "",
  "episode_count": 1,
  "seconds_per_episode": 60,
  "video_tier": "mock"
}
```

## 交付

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/delivery/{id}/novel` | 完整小说 novel.md |
| GET | `/api/delivery/{id}/video` | 第 1 集成片 final.mp4 |
| GET | `/api/delivery/{id}/video/{ep}` | 指定集成片 |
| GET | `/api/delivery/{id}/archive` | 全量交付包 zip |

## 账单

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/billing/balance` | 余额（分） |
| GET | `/api/billing/transactions` | 账单流水 |

