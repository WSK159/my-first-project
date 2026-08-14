# API 文档

基础地址：`/api`（开发代理 `http://127.0.0.1:8000/api`）

除注册/登录外，接口需请求头 `Authorization: Bearer <token>`；SSE 端点额外支持 `?token=` 查询参数（EventSource 无法自定义请求头）。

## 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册（赠送体验余额），返回 access_token |
| POST | `/api/auth/login` | 登录，返回 access_token |

## 项目与任务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/projects/templates` | 题材模板库（10 个热门模板） |
| POST | `/api/projects/estimate` | 成本预估（含火山资源包预检 quota） |
| POST | `/api/projects` | 创建项目并启动流水线 |
| GET | `/api/projects` | 项目列表（任务中心） |
| GET | `/api/projects/{id}` | 项目详情（status/progress/stage） |
| POST | `/api/projects/{id}/resume` | 继续生成（断点续跑，失败/部分项目） |
| GET | `/api/projects/{id}/episodes` | 分集状态（每集步骤/失败/时长/是否有成片） |
| GET | `/api/projects/{id}/events` | SSE 事件流（实时进度，断线重连） |
| DELETE | `/api/projects/{id}` | 删除项目与产物 |

创建请求体：

```json
{
  "idea": "一句话灵感（可空）",
  "random_mode": false,
  "genre": "",
  "episode_count": 60,
  "seconds_per_episode": 120,
  "video_tier": "mock | fast | quality"
}
```

`episode_count` 范围 1-60，`seconds_per_episode` 范围 90-180。

估算响应示例：

```json
{
  "frozen_cents": 7200,
  "balance_cents": 1000,
  "sufficient": false,
  "detail": {"llm_cents": 10, "video_cents": 7190},
  "quota": {"available": true, "ok": false, "remaining_tokens": 1000000, "deficit_tokens": 500000}
}
```

`quota.available` 为 `null` 表示未配置火山 AK/SK（跳过预检）。

## 交付

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/delivery/{id}/novel` | 完整小说 novel.md |
| GET | `/api/delivery/{id}/video/{ep}` | 单集成片 final.mp4（默认第 1 集） |
| GET | `/api/delivery/{id}/collection` | 全剧合集 collection.mp4（≥2 集，按需构建缓存） |
| GET | `/api/delivery/{id}/archive` | 全量交付包 zip（视频+小说+剧本+图+投稿规范） |
| GET | `/api/delivery/{id}/metadata` | 交付元数据（集数/总时长/按集清单/AI 标识/平台规格） |

## 计费

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/billing/balance` | 余额（分） |
| GET | `/api/billing/transactions` | 流水（充值/赠送/扣费/退款） |

计费规则：创建时按预估冻结；生成结束按实际消耗结算，差额自动退还（`kind=refund`）。

## BYOK（用户自带 Key）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/keys` | 各 provider 配置状态（密文掩码） |
| POST | `/api/keys` | 保存 Key（`{"provider": "llm|seedream|seedance|seed_audio", "api_key": "..."}`，加密存储） |
| DELETE | `/api/keys/{provider}` | 清除指定 Key |

## 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` / `/api/health` | 服务健康状态 |
