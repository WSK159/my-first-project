"""火山引擎资源包预检：查询 Seedance/Seedream 套餐余额，防止生成中欠费。

实现移植自 volcengine-resource-query 技能的 V4 签名方案，改用 httpx。
未配置 AK/SK 时返回 available=None（跳过预检，不阻塞 mock/开发流程）。
"""

import datetime as dt
import hashlib
import hmac
import json
import logging
import urllib.parse

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

SERVICE = "billing"
HOST = "open.volcengineapi.com"
VERSION = "2022-01-01"


def _hmac(key, msg: str) -> bytes:
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sign_key(secret_key: str, date: str, region: str, service: str) -> bytes:
    k_date = _hmac(secret_key, date)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    return _hmac(k_service, "request")


def _call_openapi(action: str, body: dict) -> dict:
    ak = settings.volc_access_key
    sk = settings.volc_secret_key
    if not ak or not sk:
        raise RuntimeError("未配置 VOLC_ACCESS_KEY / VOLC_SECRET_KEY，无法查询资源包")
    region = settings.volc_region
    now = dt.datetime.now(dt.UTC)
    date = now.strftime("%Y%m%d")
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_hash = hashlib.sha256(payload).hexdigest()
    query = {"Action": action, "Version": VERSION}
    canonical_query = urllib.parse.urlencode(sorted(query.items()))
    signed_headers = "content-type;host;x-content-sha256;x-date"
    content_type = "application/json; charset=utf-8"
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    canonical_request = "\n".join(
        ["POST", "/", canonical_query, canonical_headers, signed_headers, payload_hash]
    )
    credential_scope = f"{date}/{region}/{SERVICE}/request"
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            x_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        _sign_key(sk, date, region, SERVICE),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    resp = httpx.post(
        f"https://{HOST}/?{canonical_query}",
        content=payload,
        headers={
            "Content-Type": content_type,
            "Host": HOST,
            "X-Date": x_date,
            "X-Content-Sha256": payload_hash,
            "Authorization": authorization,
        },
        timeout=35,
    )
    resp.raise_for_status()
    return resp.json()


def _amount_to_tokens(item: dict) -> float:
    amount = float(item.get("AvailableAmount") or 0)
    unit = (item.get("Unit") or "").lower()
    return amount * 1000 if "千" in unit else amount


def check_seedance_quota(required_tokens: float, max_pages: int = 2) -> dict:
    """查询 Seedance 2.0 fast 套餐余量。返回 {ok, remaining_tokens, ...}。"""
    if not (settings.volc_access_key and settings.volc_secret_key):
        return {
            "available": None,
            "ok": None,
            "message": "未配置 VOLC_ACCESS_KEY / VOLC_SECRET_KEY，跳过资源包预检（建议生产环境配置）",
        }
    items = []
    next_token = ""
    for _ in range(max_pages):
        data = _call_openapi(
            "ListResourcePackages",
            {"ResourceType": "Package", "MaxResults": "20", "NextToken": next_token, "Status": "Effective"},
        )
        meta = data.get("ResponseMetadata", {})
        if "Error" in meta:
            return {"available": None, "ok": None, "error": json.dumps(data, ensure_ascii=False)}
        result = data.get("Result", {})
        items.extend(result.get("List", []))
        next_token = result.get("NextToken") or ""
        if not next_token:
            break
    matches = [
        item
        for item in items
        if "Doubao_Seedance_2.0_fast" in (item.get("ConfigurationCode") or "")
        or "Seedance-2.0-fast" in (item.get("ConfigurationName") or "")
    ]
    remaining = sum(_amount_to_tokens(item) for item in matches)
    return {
        "available": True,
        "ok": remaining >= required_tokens,
        "required_tokens": round(required_tokens, 1),
        "remaining_tokens": round(remaining, 1),
        "deficit_tokens": round(max(0.0, required_tokens - remaining), 1),
        "matched_packages": [
            {
                "ConfigurationName": item.get("ConfigurationName"),
                "ConfigurationCode": item.get("ConfigurationCode"),
                "AvailableAmount": item.get("AvailableAmount"),
                "Unit": item.get("Unit"),
                "available_tokens": round(_amount_to_tokens(item), 1),
                "ExpiryTime": item.get("ExpiryTime"),
            }
            for item in matches
        ],
    }


def estimate_video_tokens(total_seconds: int) -> float:
    """按秒估算 Seedance fast 720p 所需 token（粗略，可配置校准）。"""
    return max(0, total_seconds) * settings.seedance_tokens_per_second
