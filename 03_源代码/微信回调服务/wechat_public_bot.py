# -*- coding: utf-8 -*-
"""
任务10：微信公众号接入智能聊天助手（对齐课件，支持安全模式/明文模式）

链路：微信服务器 -> 本服务(Flask:80) -> Dify 工作流 API -> 返回 XML

依赖：pip install flask requests wechatpy
启动：python wechat_public_bot.py
"""

import hashlib
import logging
import os
import random
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET

# pymysql 装在 ./libs（系统 Python 装不进 %APPDATA%，权限被拦）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))

import requests
from flask import Flask, Response, request, make_response

try:
    from wechatpy.crypto import WeChatCrypto
    HAS_WECHATPY = True
except ImportError:  # 明文模式下不需要
    HAS_WECHATPY = False
    WeChatCrypto = None

# 价格/排名/型号参数类问题走结构化查询，不经过模型，杜绝价格编造
try:
    from price_router import answer_price_question
    HAS_PRICE_ROUTER = True
except Exception as _e:                     # noqa: BLE001
    HAS_PRICE_ROUTER = False
    answer_price_question = None
    print(f"[WARN] 价格路由不可用，价格问题将回退到模型: {_e}")

app = Flask(__name__)

# ==================== 配置区：必须改 ====================
APP_ID = os.getenv("WECHAT_APP_ID", "<YOUR_APP_ID>")          # 公众号 AppID
APP_SECRET = "xxxxxxxxxxxxxxxxxxxx"     # 公众号 AppSecret（本程序暂未主动调接口，可留空）
TOKEN = os.getenv("WECHAT_VERIFY_TOKEN", "<YOUR_VERIFY_TOKEN>")                      # 必须与公众号后台「消息推送」里的 Token 完全一致
ENCODING_AES_KEY = os.getenv("WECHAT_AES_KEY", "")  # 安全模式必填；明文模式留空

# Dify 工作流
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "<YOUR_DIFY_APP_KEY>")
DIFY_WORKFLOW_URL = os.getenv("DIFY_WORKFLOW_URL", "http://192.168.1.10/v1/workflows/run")

# MCP 保活工作流（只有 开始 -> MCP list_tables -> 结束 三个节点，不写库）
# 作用：Dify 的 MCP 插件闲置约 15 秒会被卸载，下次调用要重新加载 4.5 秒，
#      定时打这个轻量工作流可以让插件一直热着，避免微信 5 秒超时。
KEEPALIVE_KEY = os.getenv("DIFY_KEEPALIVE_KEY", "")
KEEPALIVE_URL = os.getenv("DIFY_KEEPALIVE_URL", "http://192.168.1.10/v1/workflows/run")
KEEPALIVE_INTERVAL = 10                   # 秒

HOST = "0.0.0.0"
PORT = 80                                # 微信要求 80 或 443

# MySQL：问答落库（后台线程写，不占回复预算）
MYSQL_HOST = os.getenv("MYSQL_HOST", "192.168.1.10")
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "<MYSQL_PASSWORD>")
MYSQL_DB = "wechat"
MYSQL_TABLE = "chathistory"

# 微信硬超时 5 秒，留 0.5 秒给自己，Dify 最多等 4.5 秒
DIFY_TIMEOUT = (1.5, 4.8)
FALLBACK = "稍等，我这边正在查询，马上回复您～"
# ======================================================

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("wechat")


def check_signature(signature, timestamp, nonce):
    """校验消息是否来自微信服务器"""
    tmp = "".join(sorted([TOKEN, timestamp, nonce])).encode("utf-8")
    return hashlib.sha1(tmp).hexdigest() == signature


def call_dify_workflow(query, user_id):
    """调用 Dify 工作流 API，返回回复文本

    注意：inputs 的键名必须是 Dify 工作流「开始」节点的字段名，
    本项目里是 query（不是课件里的 input）。
    """
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "inputs": {"query": query},
        "user": user_id,
        "response_mode": "blocking",
    }

    try:
        started = time.time()
        resp = requests.post(DIFY_WORKFLOW_URL, json=data,
                             headers=headers, timeout=DIFY_TIMEOUT)
        log.info("Dify 耗时 %.2fs HTTP %s", time.time() - started, resp.status_code)
        resp.raise_for_status()
        result = resp.json()

        status = result.get("data", {}).get("status")
        if status != "succeeded":
            log.warning("Dify 返回非 succeeded: %s", result)
            return FALLBACK

        outputs = result.get("data", {}).get("outputs", {}) or {}
        # 本项目「结束」节点输出变量叫 answer；兼容课件里的 text
        ai_reply = outputs.get("answer") or outputs.get("text")
        if not ai_reply:
            log.warning("未取到回复文本，完整响应: %s", result)
            return FALLBACK

        ai_reply = strip_think(ai_reply)
        if not ai_reply:
            return FALLBACK

        return ai_reply[:2000]          # 微信文本消息长度限制

    except requests.exceptions.Timeout:
        log.error("Dify 超时（>%.1fs），返回兜底", DIFY_TIMEOUT[1])
        return FALLBACK
    except requests.exceptions.RequestException as e:
        log.error("调用 Dify 网络错误: %s", e)
        return "网络服务有点忙，请稍后再试。"
    except Exception as e:                       # noqa: BLE001
        log.exception("处理 Dify 响应时出错: %s", e)
        return "AI助手暂时开小差了，请稍后重试。"


def strip_think(text):
    """剥掉推理模型的思维链（DeepSeek-V4.1-Flash / R1 会输出 <think>...</think>）"""
    import re
    text = re.sub(r"<think\b[^>]*>.*?</think>", "", text, flags=re.S | re.I)
    text = re.sub(r"</?think\b[^>]*>", "", text, flags=re.I)
    return text.strip()


# ==================== 敏感消息拦截（辱骂 / 威胁）====================
# 为什么不用知识库：知识库靠「语义相似度」召回，辱骂语句与任何一条业务知识
# 相似度都极低，检索不到；即使硬塞一条进去，也只在用户刚好复述了那句话术时
# 才命中。所以必须在调用模型之前用规则拦一道。
#
# 为什么不「反击」：客服场景下对骂只会把冲突升级，并在聊天记录里留下把柄。
# 正确做法是「降温 + 划边界 + 转人工」，同时把这轮标记为高风险，供舆情预警用。
#
# L3 = 人身攻击/辱骂        -> 划边界，不接脏话，给出口
# L2 = 威胁投诉/曝光/监管   -> 郑重受理，引导提供凭证，准备转人工
# L1（垃圾/骗子/太差等）    -> 不拦截，交给模型按既有话术安抚，避免误伤真实投诉

_SENSITIVE_L3 = [
    r"傻[逼比屄bB]", r"煞笔", r"沙比", r"脑残", r"弱智", r"智障", r"废物",
    r"[去滚]你[妈马]", r"[操草艹]你", r"他妈的?", r"滚[开蛋]", r"神经病",
    r"狗[日东西]", r"贱[人货]", r"死全家", r"你妈", r"妈逼", r"tmd", r"nmsl",
    r"有病吧", r"闭嘴", r"去死", r"少废话",
]
_SENSITIVE_L2 = [
    r"曝光", r"12315", r"315投诉", r"消协", r"工商局", r"市场监督", r"起诉",
    r"律师函", r"报警", r"媒体", r"上热搜", r"举报",
]

_REPLY_L3 = [
    "您这句话我已经记录在案。\n"
    "我可以帮您解决问题，但不接受人身攻击——这是我的底线，不是商量。\n"
    "要处理售后退回复「人工」，继续谩骂，本次对话我直接结束。",
    "请注意措辞。\n"
    "我是来解决问题的，不是来挨骂的。有具体故障、订单号，说出来我照办；\n"
    "没有的话，这次对话就到这里。",
    "这条消息已存档，包含时间和原文。\n"
    "按平台规则，辱骂客服的会话我有权终止。\n"
    "想解决问题就正常说话，我一句不少地给您办。",
]
_REPLY_L2 = [
    "投诉、曝光、12315，都是您的权利，我拦不住，也没打算拦。\n"
    "但任何渠道受理都要订单号和事实：把单号发我，该退该赔我一项不少地办。\n"
    "您先看处理方案，再决定要不要投诉，这两件事不冲突。",
    "您要曝光，我不劝。\n"
    "但截图发出去之前，建议先看看我们给的处理结果——订单号发我，"
    "能当天解决的，不会拖到明天。",
]


def detect_sensitive(text):
    """返回 0（正常）/ 2（威胁投诉）/ 3（人身辱骂）"""
    t = re.sub(r"[\s\W_]+", "", str(text or "")).lower()
    for p in _SENSITIVE_L3:
        if re.search(p, t):
            return 3
    for p in _SENSITIVE_L2:
        if re.search(p, t):
            return 2
    return 0


def save_history(user_input, response):
    """把一轮问答写入 MySQL 的 chathistory（后台线程，不阻塞回复）。

    为什么不用 Dify 里的 MCP 节点写：实测 Dify 调 MCP 偶发 4.5 秒尖峰，
    而微信硬超时只有 5 秒，一撞上就丢回复。这里用本地 pymysql 直写，
    稳定在 20 毫秒内。MCP 服务与「MCP保活」工作流仍然保留，用于任务8
    的能力演示与验收，只是不再卡在微信的同步链路上。
    """
    try:
        import pymysql
    except ImportError:
        log.warning("未安装 pymysql，本次跳过落库（pip install pymysql）")
        return

    conn = None
    try:
        conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT,
                               user=MYSQL_USER, password=MYSQL_PASSWORD,
                               database=MYSQL_DB, charset="utf8mb4",
                               connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {MYSQL_TABLE} (user_input, response) VALUES (%s, %s)",
                (user_input[:2000], response[:2000]),
            )
        conn.commit()
    except Exception as e:                       # noqa: BLE001
        log.error("落库失败: %s", e)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def reply_text(to_user, from_user, content):
    """生成文本回复的 XML"""
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def xml_response(to_user, from_user, content, encrypt_type, nonce, timestamp):
    """按当前模式返回明文或加密的 XML 响应"""
    reply_xml = reply_text(to_user, from_user, content)

    if encrypt_type == "aes" and HAS_WECHATPY:
        crypto = WeChatCrypto(TOKEN, ENCODING_AES_KEY, APP_ID)
        reply_xml = crypto.encrypt_message(reply_xml, nonce, timestamp)

    resp = make_response(reply_xml)
    resp.content_type = "application/xml"
    return resp


# ==================== 多轮上下文（指代消解 + 短历史） ====================

HISTORY_TURNS = 2            # 每个用户最多记几轮
HISTORY_MAX_USERS = 500      # 内存里最多保留多少个用户
HISTORY_MAX_HEAD = 95        # 历史摘要最大字符数（控制 prompt 膨胀）

# 追问信号：短句、以「那/还/它」开头、或含指代词
_FOLLOWUP_RE = re.compile(r"^(那|还|它|这|再|然后)|它|这款|那款|这个|那个|该款")
# 型号：R40-A0 / X50-B2 / R60-D5 这一类
_MODEL_RE = re.compile(r"[A-Z]\d{1,2}-[A-Z]\d{1,2}")
# 价格类问题：不复用历史，避免把上一轮的数字带进这一轮
_PRICE_RE = re.compile(r"最贵|最便宜|多少钱|价格|报价|优惠|贵不贵")

_history = {}                # openid -> [(问, 答), ...]
_history_lock = threading.Lock()


def remember_turn(openid, question, answer):
    """记一对问答，供下一轮使用。只在内存里，进程重启即清空。"""
    if not openid or not answer:
        return
    with _history_lock:
        turns = _history.get(openid)
        if turns is None:
            if len(_history) >= HISTORY_MAX_USERS:      # 简单淘汰，防止无限增长
                _history.pop(next(iter(_history)), None)
            turns = []
            _history[openid] = turns
        turns.append((question.strip(), answer.strip()))
        del turns[:-HISTORY_TURNS]


def build_query(question, openid):
    """把「它/这款」补成具体型号，必要时前置一句上一轮摘要。

    只做两件轻量的事，避免历史污染知识检索：
      1. 指代消解：上一轮出现过型号，就把代词换成型号（query 变短、检索更准）；
      2. 短历史：仅当本轮是追问式短句时前置一段 ≤95 字的上一轮摘要。
    普通独立问题原样发出，检索不会被历史带偏。
    """
    q = (question or "").strip()
    with _history_lock:
        turns = _history.get(openid)
        last = turns[-1] if turns else None

    if not last:
        return q

    last_q, last_a = last

    # 1) 指代消解
    if _MODEL_RE.search(q) is None:
        m = _MODEL_RE.search(last_q) or _MODEL_RE.search(last_a)
        if m:
            q = re.sub(r"它|这款|那款|该款|这个|那个", m.group(0), q, count=1)

    # 2) 短历史：只给追问式短句加；已经指代消解出型号、或问的是价格（怕数字串味）就不加
    has_model = _MODEL_RE.search(q) is not None
    is_price = _PRICE_RE.search(q) is not None
    is_followup = ((len(q) <= 14 or bool(_FOLLOWUP_RE.search(q)))
                   and not has_model and not is_price)
    if is_followup:
        head = "（上一轮 用户：%s｜助手：%s）" % (last_q[:40], last_a[:50])
        if len(head) <= HISTORY_MAX_HEAD:
            log.info("带上下文提问: %s | 上一轮=%s", q[:30], last_q[:20])
            return head + "\n" + q
    return q


# ==================== 路由 ====================

@app.route("/wechat", methods=["GET"])
def wechat_verify():
    """首次提交 URL 时的服务器验证"""
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    echostr = request.args.get("echostr", "")

    if check_signature(signature, timestamp, nonce):
        log.info("微信服务器验证成功")
        return echostr
    log.warning("微信服务器验证失败")
    return "Error: Invalid signature", 403


@app.route("/wechat", methods=["POST"])
def handle_wechat_message():
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    encrypt_type = request.args.get("encrypt_type", "")
    msg_signature = request.args.get("msg_signature", "")

    if not check_signature(signature, timestamp, nonce):
        return "Error: Invalid signature", 403

    raw = request.data

    # 安全模式先解密
    if encrypt_type == "aes":
        if not HAS_WECHATPY:
            log.error("安全模式需要 wechatpy，请 pip install wechatpy")
            return "success"
        crypto = WeChatCrypto(TOKEN, ENCODING_AES_KEY, APP_ID)
        try:
            raw = crypto.decrypt_message(raw, msg_signature, timestamp, nonce)
        except Exception as e:                   # noqa: BLE001
            log.error("解密失败: %s", e)
            return "success"                     # 返回 success 让微信停止重试

    root = ET.fromstring(raw)
    msg_type = root.findtext("MsgType", "")
    from_user = root.findtext("FromUserName", "")
    to_user = root.findtext("ToUserName", "")

    log.info("收到消息 type=%s from=%s", msg_type, from_user)

    if msg_type == "text":
        user_question = root.findtext("Content", "") or ""
        log.info("用户问题: %s", user_question)

        level = detect_sensitive(user_question)
        if level:
            ai_reply = random.choice(_REPLY_L3 if level == 3 else _REPLY_L2)
            log.warning("敏感消息 L%d，直接返回固定话术（不调模型）: %s",
                        level, user_question[:40])
            threading.Thread(target=save_history,
                             args=(user_question, ai_reply), daemon=True).start()
            return xml_response(from_user, to_user, ai_reply,
                                encrypt_type, nonce, timestamp)

        # 先看是不是价格/排名/型号类问题：命中就直接查库回答，不经过模型
        direct = None
        if HAS_PRICE_ROUTER:
            try:
                direct = answer_price_question(user_question)
            except Exception as e:              # noqa: BLE001
                log.warning("价格路由异常，回退模型: %s", e)
        if direct:
            log.info("价格路由直答（约 50ms）: %s", direct.replace("\n", " ")[:50])
            threading.Thread(target=save_history,
                             args=(user_question, direct), daemon=True).start()
            return xml_response(from_user, to_user, direct,
                                encrypt_type, nonce, timestamp)

        ask = build_query(user_question, from_user)
        ai_reply = call_dify_workflow(ask, from_user)
        log.info("AI回复: %s", ai_reply)
        if ai_reply and ai_reply != FALLBACK:
            remember_turn(from_user, user_question, ai_reply)
        # 落库放到后台线程：微信只等回复，不等 INSERT
        threading.Thread(target=save_history,
                         args=(user_question, ai_reply), daemon=True).start()
        return xml_response(from_user, to_user, ai_reply,
                            encrypt_type, nonce, timestamp)

    elif msg_type == "event":
        event = root.findtext("Event", "")
        if event == "subscribe":
            welcome = "感谢关注！我是您的AI智能助手，可以回答各种问题。请直接发送消息给我吧！"
            return xml_response(from_user, to_user, welcome,
                                encrypt_type, nonce, timestamp)
        return "success"

    else:
        return xml_response(from_user, to_user,
                            "暂不支持此类型消息，请发送文字内容。",
                            encrypt_type, nonce, timestamp)


@app.route("/health")
def health():
    return {"ok": True, "mode": "aes-support" if HAS_WECHATPY else "plaintext-only"}


def _warmup():
    """启动后预热一次工作流，把冷启动成本（约 2.5 秒）提前吃掉。

    实测：进程刚起来后的第一条真实消息会慢 2~3 秒（TLS 握手 + Dify worker
    冷启动 + LLM 连接池为空），容易顶到 5 秒硬超时。预热一次即可消除。
    预热记录用 user=__warmup__ 标记，方便事后从 chathistory 里清掉。
    """
    time.sleep(3)
    try:
        t0 = time.time()
        reply = call_dify_workflow("预热", "__warmup__")
        log.info("预热完成 %.2fs -> %s", time.time() - t0, str(reply)[:30])
    except Exception as e:                       # noqa: BLE001
        log.warning("预热失败（不影响使用）: %s", e)


def _keepalive():
    """每 10 秒打一次「MCP保活」工作流，让 Dify 的 MCP 插件不进入休眠。

    实测 Dify 的 MCP 工具闲置约 15 秒后会被 plugin_daemon 卸载，下次调用
    重新加载要 4.5 秒（MCP 服务器本身只耗时 7 毫秒，可排除网络与代码）。
    微信 5 秒硬超时下，这 4.5 秒是致命的，所以用轻量心跳把它按住。
    这个工作流只调 list_tables，不写数据库，不污染 chathistory。
    """
    if not KEEPALIVE_KEY or KEEPALIVE_KEY.startswith("app-XXXX"):
        log.info("未配置 KEEPALIVE_KEY，跳过 MCP 保活")
        return

    headers = {"Authorization": f"Bearer {KEEPALIVE_KEY}",
               "Content-Type": "application/json"}
    payload = {"inputs": {}, "response_mode": "blocking", "user": "__keepalive__"}
    fails = 0
    while True:
        try:
            requests.post(KEEPALIVE_URL, json=payload, headers=headers, timeout=6)
            if fails:
                log.info("MCP 保活已恢复（此前失败 %d 次）", fails)
                fails = 0
        except Exception as e:                   # noqa: BLE001
            fails += 1
            if fails in (1, 10, 100):            # 不刷屏，只在关键次数提醒
                log.warning("MCP 保活失败 %d 次: %s", fails, e)
        time.sleep(KEEPALIVE_INTERVAL)


if __name__ == "__main__":
    log.info("微信公众号智能客服服务启动中...")
    log.info("服务地址: http://%s:%s/wechat", HOST, PORT)
    log.info("请把公网地址配置到公众号后台「消息推送」的 URL 中")
    log.info("=" * 50)
    threading.Thread(target=_warmup, daemon=True).start()
    # MCP 已不在微信主链路上（落库改由 Flask 直写），保活线程默认关闭，
    # 否则每 10 秒往 Dify 写一条 workflow_run 日志，一天近 9000 条。
    # 若日后又要让 Dify 工作流带 MCP 节点，把下面这行取消注释即可。
    # threading.Thread(target=_keepalive, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
