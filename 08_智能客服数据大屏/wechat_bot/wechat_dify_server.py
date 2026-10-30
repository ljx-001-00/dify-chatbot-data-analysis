# -*- coding: utf-8 -*-
"""
任务10：微信公众号接入智能聊天助手
链路：微信服务器 -> 本服务(Flask:80) -> Dify 工作流 API -> 返回 XML 文本

启动：  python wechat_dify_server.py
依赖：  pip install flask requests
"""

import os
import hashlib
import time
import logging
import xml.etree.ElementTree as ET

import requests
from flask import Flask, request, Response

# ============ 需要你改的三个值 ============
WECHAT_TOKEN = os.getenv("WECHAT_VERIFY_TOKEN", "<YOUR_VERIFY_TOKEN>")                       # 公众号后台「服务器配置」里自己填的 Token，两边必须一致
DIFY_API_KEY = "app-在这里填你的密钥"            # Dify 应用 -> 访问 API -> API 密钥
DIFY_URL = "http://192.168.1.10/v1/workflows/run"

DIFY_USER = "wechat-user"                       # 传给 Dify 的 user 标识，用 openid 更细
PORT = 80

# 微信硬超时 5 秒。留 1 秒给自己，Dify 最多等 3.8 秒
DIFY_TIMEOUT = (1.5, 3.8)

FALLBACK = "稍等，我这边正在查询，马上回复您～"

# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("wechat")

app = Flask(__name__)


def check_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """微信服务器校验：token/timestamp/nonce 字典序拼接后 sha1"""
    items = sorted([WECHAT_TOKEN, timestamp, nonce])
    calc = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    return calc == signature


def parse_xml(raw: bytes) -> dict:
    root = ET.fromstring(raw)
    return {child.tag: (child.text or "") for child in root}


def build_text_xml(to_user: str, from_user: str, content: str) -> str:
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def ask_dify(query: str, user: str) -> str:
    """调 Dify 工作流，blocking 模式，返回 answer 文本"""
    payload = {
        "inputs": {"query": query},
        "response_mode": "blocking",
        "user": user,
    }
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    started = time.time()
    resp = requests.post(
        DIFY_URL, json=payload, headers=headers, timeout=DIFY_TIMEOUT
    )
    elapsed = time.time() - started
    log.info("Dify 耗时 %.2fs, HTTP %s", elapsed, resp.status_code)

    resp.raise_for_status()
    data = resp.json()

    if data.get("data", {}).get("status") != "succeeded":
        log.warning("Dify 返回异常: %s", data)
        return FALLBACK

    outputs = data["data"].get("outputs", {}) or {}
    answer = outputs.get("answer") or ""
    return answer.strip() or FALLBACK


@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    if not check_signature(signature, timestamp, nonce):
        log.warning("签名校验失败")
        return Response("invalid signature", status=403)

    # 公众号后台点「提交」时的验证请求
    if request.method == "GET":
        echostr = request.args.get("echostr", "")
        log.info("接入验证通过，返回 echostr")
        return Response(echostr, mimetype="text/plain")

    # 收到用户消息
    msg = parse_xml(request.data)
    msg_type = msg.get("MsgType", "")
    from_user = msg.get("FromUserName", "")
    to_user = msg.get("ToUserName", "")

    log.info("收到消息 type=%s from=%s", msg_type, from_user)

    if msg_type == "text":
        query = (msg.get("Content") or "").strip()
    elif msg_type == "voice":
        query = (msg.get("Recognition") or "").strip()  # 语音转文字（需公众号开启）
    else:
        query = ""

    if not query:
        reply = "目前只支持文字消息哦，请把问题打字发给我～"
    else:
        try:
            reply = ask_dify(query, from_user or DIFY_USER)
        except requests.exceptions.Timeout:
            log.error("Dify 超时，返回兜底话术")
            reply = FALLBACK
        except Exception as exc:  # noqa: BLE001
            log.exception("调用 Dify 失败: %s", exc)
            reply = FALLBACK

    xml = build_text_xml(from_user, to_user, reply)
    return Response(xml, mimetype="application/xml")


@app.route("/health", methods=["GET"])
def health():
    return {"ok": True, "service": "wechat-dify"}


if __name__ == "__main__":
    log.info("微信回调服务启动，监听 0.0.0.0:%s，路径 /wechat", PORT)
    app.run(host="0.0.0.0", port=PORT, threaded=True)
