"""真实档 API 客户端单元测试：用请求捕获验证请求构造与错误处理（不调用真实服务）。

运行：python scripts/test_real_clients.py
覆盖：Seedance（创建/轮询）、Seedream（生成）、Seed Audio（配音）、LLM（对话补全）、BYOK 覆盖。
"""

import base64
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.services import audio as audio_svc  # noqa: E402
from app.services import images as images_svc  # noqa: E402
from app.services import videos as videos_svc  # noqa: E402
from app.services.llm import OpenAICompatLLM  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


class Captured:
    def __init__(self) -> None:
        self.requests: list[dict] = []


def install_post_capture(module, captured: Captured, responder):
    def fake_post(url, headers=None, json=None, content=None, timeout=None, **kw):
        captured.requests.append(
            {"url": str(url), "headers": headers or {}, "json": json, "content": content}
        )
        return responder(url, json, headers, httpx.Request("POST", str(url)))

    module.httpx.post = fake_post


def main() -> int:
    # 1) Seedance create_task 请求构造
    captured = Captured()
    install_post_capture(
        videos_svc,
        captured,
        lambda url, body, headers, request: httpx.Response(200, json={"id": "task-abc"}, request=request),
    )
    client = videos_svc.SeedanceClient(api_key="sk-seedance")
    client.base_url = "https://ark.example.com/api/v3"
    client.model = "doubao-seedance-2-0-fast-260128"
    task_id = client.create_task("一个连贯的推镜镜头", 10)
    check("Seedance：返回 task id", task_id == "task-abc")
    req = captured.requests[0]
    check("Seedance：URL 正确", req["url"].endswith("/contents/generations/tasks"), req["url"])
    body = req["json"]
    check("Seedance：鉴权头", req["headers"].get("Authorization") == "Bearer sk-seedance")
    check(
        "Seedance：请求体字段",
        body.get("model") == client.model
        and body.get("duration") == 10
        and body.get("resolution") == settings.seedance_resolution
        and body.get("ratio") == settings.seedance_ratio
        and body.get("return_last_frame") is True
        and body.get("watermark") is False,
        json.dumps(body, ensure_ascii=False)[:200],
    )

    # 2) Seedance poll_task 成功/失败
    def get_responder(url, **kw):
        if url.endswith("task-abc"):
            return httpx.Response(
                200,
                json={"status": "succeeded", "content": {"video_url": "https://cdn/v.mp4"}},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(200, json={"status": "failed", "error": "boom"}, request=httpx.Request("GET", url))

    videos_svc.httpx.get = lambda url, headers=None, timeout=None: get_responder(str(url))
    task = client.poll_task("task-abc", timeout_seconds=1)
    check("Seedance：轮询成功", task.get("status") == "succeeded")
    try:
        client.poll_task("task-bad", timeout_seconds=1)
        check("Seedance：失败任务抛错", False)
    except RuntimeError:
        check("Seedance：失败任务抛错", True)

    # 3) Seedream 生成请求构造
    captured2 = Captured()
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

    def seedream_responder(url, body, headers, request):
        return httpx.Response(
            200,
            json={"data": [{"url": "https://cdn/i.png"}]},
            request=httpx.Request("POST", str(url)),
        )

    install_post_capture(images_svc, captured2, seedream_responder)

    def fake_get_image(url, timeout=None):
        return httpx.Response(200, content=image_bytes, request=httpx.Request("GET", str(url)))

    images_svc.httpx.get = fake_get_image
    img_client = images_svc.SeedreamClient(api_key="sk-seedream")
    img_client.base_url = "https://ark.example.com/api/v3"
    content = img_client.generate("角色设定照", size="2K", ratio="3:4")
    check("Seedream：返回图片字节", content == image_bytes)
    req2 = captured2.requests[0]
    check("Seedream：URL 正确", req2["url"].endswith("/images/generations"), req2["url"])
    check(
        "Seedream：请求体",
        req2["json"].get("model") == settings.seedream_model
        and req2["json"].get("size") == "2K"
        and req2["json"].get("response_format") == "url"
        and req2["json"].get("watermark") is False,
        json.dumps(req2["json"], ensure_ascii=False)[:200],
    )

    # 4) Seed Audio 请求构造（X-Api-Key 头 + audio b64）
    captured3 = Captured()
    wav_b64 = base64.b64encode(b"RIFF-fake-wav").decode()

    def audio_responder(url, body, headers, request):
        return httpx.Response(
            200,
            json={"code": 200, "audio": wav_b64, "duration": 3.0},
            request=httpx.Request("POST", str(url)),
        )

    install_post_capture(audio_svc, captured3, audio_responder)
    audio_client = audio_svc.SeedAudioClient(api_key="sk-audio")
    audio_client.base_url = "https://voice.example.com"
    from pathlib import Path as P

    tmp = P("backend/data/_test_audio.mp3")
    result = audio_client.generate("测试对白", tmp)
    check("Seed Audio：返回时长", result["duration"] == 3.0)
    req3 = captured3.requests[0]
    check("Seed Audio：URL 正确", req3["url"].endswith("/api/v3/tts/create"), req3["url"])
    check("Seed Audio：X-Api-Key 头", req3["headers"].get("X-Api-Key") == "sk-audio")
    check("Seed Audio：请求体", "text_prompt" in req3["json"] and "audio_config" in req3["json"])
    check("Seed Audio：音频落盘", tmp.read_bytes() == b"RIFF-fake-wav")
    tmp.unlink(missing_ok=True)

    # 5) LLM 对话补全
    captured_llm = Captured()
    def llm_responder(url, body, headers, request):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{\"ok\": 1}"}}]},
            request=httpx.Request("POST", str(url)),
        )

    def fake_llm_post(url, headers=None, json=None, content=None, timeout=None, **kw):
        captured_llm.requests.append({"url": str(url), "headers": headers or {}, "json": json})
        return llm_responder(url, json, headers, httpx.Request("POST", str(url)))

    httpx.post = fake_llm_post
    llm = OpenAICompatLLM("sk-llm", "https://api.deepseek.com", "deepseek-chat")
    out = llm.complete([{"role": "user", "content": "你好"}])
    check("LLM：返回内容", out == '{"ok": 1}')
    req4 = captured_llm.requests[0]
    check("LLM：URL 正确", req4["url"].endswith("/chat/completions"), req4["url"])
    check("LLM：鉴权头", req4["headers"].get("Authorization") == "Bearer sk-llm")

    # 6) BYOK 覆盖：客户端优先使用用户传入的 Key
    check("BYOK：Seedance 覆盖", videos_svc.SeedanceClient(api_key="user-ak").api_key == "user-ak")
    check("BYOK：Seedream 覆盖", images_svc.SeedreamClient(api_key="user-img").api_key == "user-img")
    check("BYOK：Seed Audio 覆盖", audio_svc.SeedAudioClient(api_key="user-voice").api_key == "user-voice")

    print(f"\n真实档客户端单元测试：{PASS} 通过 / {FAIL} 失败")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
