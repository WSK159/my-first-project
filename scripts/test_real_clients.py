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

    # 7) MiniMax 生图
    captured_mm_img = Captured()
    mm_img_bytes = b"\x89PNG-mock-minimax"

    def mm_img_responder(url, body, headers, request):
        return httpx.Response(
            200,
            json={"data": {"image_urls": ["https://cdn/mm.png"]}, "base_resp": {"status_code": 0}},
            request=request,
        )

    install_post_capture(images_svc, captured_mm_img, mm_img_responder)
    images_svc.httpx.get = lambda url, timeout=None: httpx.Response(
        200, content=mm_img_bytes, request=httpx.Request("GET", str(url))
    )
    mm_img = images_svc.MiniMaxImageClient(api_key="sk-mm")
    mm_img.base_url = "https://api.minimaxi.com"
    content = mm_img.generate("角色设定照", ratio="3:4")
    check("MiniMax图：返回图片字节", content == mm_img_bytes)
    req = captured_mm_img.requests[0]
    check(
        "MiniMax图：请求体",
        req["url"].endswith("/v1/image_generation")
        and req["json"].get("model") == settings.minimax_image_model
        and req["json"].get("aspect_ratio") == "3:4"
        and req["json"].get("response_format") == "url",
        json.dumps(req["json"], ensure_ascii=False)[:200],
    )

    # 7.1) MiniMax 余额不足错误处理
    def mm_img_err_responder(url, body, headers, request):
        return httpx.Response(
            200,
            json={"data": None, "base_resp": {"status_code": 1008, "status_msg": "insufficient balance"}},
            request=request,
        )

    install_post_capture(images_svc, Captured(), mm_img_err_responder)
    try:
        mm_img.generate("测试", ratio="1:1")
        check("MiniMax图：余额不足抛错", False)
    except RuntimeError as exc:
        check("MiniMax图：余额不足抛错", "insufficient balance" in str(exc))

    # 8) MiniMax 生视频（任务创建 + 轮询直链）
    captured_mm_vid = Captured()

    def mm_vid_responder(url, body, headers, request):
        return httpx.Response(200, json={"task_id": "mm-task-1"}, request=request)

    install_post_capture(videos_svc, captured_mm_vid, mm_vid_responder)
    mm_vid = videos_svc.MiniMaxVideoClient(api_key="sk-mm")
    mm_vid.base_url = "https://api.minimaxi.com"
    task_id = mm_vid.create_task("推镜镜头", 10)
    check("MiniMax视频：返回 task id", task_id == "mm-task-1")
    req = captured_mm_vid.requests[0]
    check(
        "MiniMax视频：请求体",
        req["url"].endswith("/v2/video_generation")
        and req["json"].get("model") == settings.minimax_video_model
        and req["json"].get("duration") == 10
        and req["json"].get("resolution") == settings.minimax_video_resolution
        and req["json"].get("ratio") == settings.seedance_ratio,
        json.dumps(req["json"], ensure_ascii=False)[:200],
    )

    # 8.1) MiniMax 视频参考图（角色一致性）
    tmp_ref = P("backend/data/_mm_ref.png")
    tmp_ref.write_bytes(b"\x89PNG-ref")
    captured_mm_vid2 = Captured()

    def mm_vid_responder2(url, body, headers, request):
        return httpx.Response(200, json={"task_id": "mm-task-2"}, request=request)

    install_post_capture(videos_svc, captured_mm_vid2, mm_vid_responder2)
    mm_vid.create_task("角色镜头", 5, reference_images=[tmp_ref])
    req_ref = captured_mm_vid2.requests[0]
    ref_items = [i for i in req_ref["json"]["content"] if i.get("role") == "reference_image"]
    check(
        "MiniMax视频：参考图加入 content",
        len(ref_items) == 1 and ref_items[0]["image_url"]["url"].startswith("data:image/png;base64,"),
        str(ref_items)[:200],
    )
    tmp_ref.unlink(missing_ok=True)

    def mm_vid_get(url, headers=None, timeout=None):
        return httpx.Response(
            200,
            json={"task": {"status": "succeeded", "content": {"url": "https://cdn/mm.mp4"}}},
            request=httpx.Request("GET", str(url)),
        )

    videos_svc.httpx.get = mm_vid_get
    url = mm_vid.poll_task("mm-task-1", timeout_seconds=1)
    check("MiniMax视频：轮询返回直链", url == "https://cdn/mm.mp4")

    # 9) MiniMax TTS
    captured_mm_tts = Captured()
    wav_b64_tts = base64.b64encode(b"MM-TTS-AUDIO").decode()

    def mm_tts_responder(url, body, headers, request):
        return httpx.Response(
            200,
            json={"data": {"audio": wav_b64_tts, "extra_info": {"audio_length": 2.5}}},
            request=request,
        )

    install_post_capture(audio_svc, captured_mm_tts, mm_tts_responder)
    mm_tts = audio_svc.MiniMaxTTSClient(api_key="sk-mm")
    mm_tts.base_url = "https://api.minimaxi.com"
    tmp2 = P("backend/data/_test_mm_tts.mp3")
    result = mm_tts.generate("你好，世界", tmp2, "female-shaonv")
    check("MiniMaxTTS：返回时长", result["duration"] == 2.5)
    check("MiniMaxTTS：音频落盘", tmp2.read_bytes() == b"MM-TTS-AUDIO")
    tmp2.unlink(missing_ok=True)
    req = captured_mm_tts.requests[0]
    check(
        "MiniMaxTTS：请求体",
        req["url"].endswith("/v1/t2a_v2")
        and req["json"].get("model") == settings.minimax_tts_model
        and req["json"].get("voice_setting", {}).get("voice_id") == "female-shaonv",
        json.dumps(req["json"], ensure_ascii=False)[:200],
    )

    print(f"\n真实档客户端单元测试：{PASS} 通过 / {FAIL} 失败")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
