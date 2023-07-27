from flask import Blueprint, request
from wechatpy import parse_message, create_reply, WeChatClient
from wechatpy.crypto import WeChatCrypto
from cacheout import LFUCache, Cache
from wechatpy.utils import check_signature
from dotenv import load_dotenv
import llm
import time
import threading
import os
import tts
import asyncio

load_dotenv(".env")

wxToken = os.environ.get('WX_TOKEN')
wxAesKey = os.environ.get('WX_AES_KEY')
wxAppSecret = os.environ.get('WX_APP_SECRET')
wxAppId = os.environ.get('WX_APP_ID')
gzhType = os.environ.get('GZH_TYPE')

wx_blue = Blueprint('wx', __name__)
client = WeChatClient(wxAppId, wxAppSecret)
cache = Cache(maxsize=100, ttl=120, timer=time.time, default=None)

switchVoiceRespKey = "{0}voice"

def async_call(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()

    return wrapper

@wx_blue.route("/callback", methods=['GET', 'POST'])
def callback():
    signature = request.args.get('signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    msg_signature = request.args.get("msg_signature")
    echostr = request.args.get('echostr', '')

    crypto = WeChatCrypto(wxToken, wxAesKey, wxAppId)
    if request.method == "GET":
        check_signature(wxToken, signature, timestamp, nonce)
        return echostr
    else:
        decrypted_xml = crypto.decrypt_message(
            request.data,
            msg_signature,
            timestamp,
            nonce
        )
        # 解析请求中的消息
        msg = parse_message(decrypted_xml)

        # 根据消息类型回复不同的内容
        if msg.type in ("text", "voice"):
            print(msg)
            if msg.type == "voice":
                content = msg.recognition
            else:
                content = msg.content

            # reply = switch_voice_resp(content, msg)
            # if reply == "":
            if gzhType == "0":
                #订阅号
                reply = create_reply(sync_resp_text(msg.source, content), msg).render()
            else:
                #服务号
                async_resp_text(msg.source, content)
                reply = create_reply("请稍等，思考中...", msg).render()
        else:
            reply = create_reply("请尝试输入文字或语音", msg).render()

        return crypto.encrypt_message(reply, nonce, timestamp)

def switch_voice_resp(content: str, msg) -> str:
    resp = None
    if content == "打开语音回复":
        cache.set(switchVoiceRespKey.format(msg.source), "")
        resp = "打开语音回复成功"
    elif content == "关闭语音回复":
        cache.delete(switchVoiceRespKey.format(msg.source))
        resp = "关闭语音回复成功"

    if resp is None:
        return ""
    else:
        return create_reply(resp, msg).render()


@async_call
def async_resp_text(openid: str, question: str) -> str:
    res = llm.completion(question).strip()
    if switchVoiceRespKey.format(openid) in cache:
        #回复语音
        output = asyncio.run(tts.communicate(res))
        print(output)
        with open(output, "rb") as file_object:
            temp = client.media.upload("voice", file_object.read())
            print(temp)
        client.message.send_voice(openid, temp.media_id)
    else:
        # 回复文本
        client.message.send_text(openid, res)

def sync_resp_text(content: str, msgid: str) -> str:
    # 判断是否相同请求,缓存请求
    if msgid in cache:
        if cache.get(msgid) == "" or cache.get(msgid) is None:
            # return "正在思考中，请在20秒后回复1获取结果"
            time.sleep(20)
            return ""
        else:
            return cache.get(msgid)
    else:
        cache.set(msgid, "")
        # 调用大模型，将结果存入缓存
        res = llm.completion(content).strip()
        cache.set(msgid, res)
        return res

def get_access_token():
    access_token = client.access_token
    if access_token and access_token.is_valid:
        return access_token.access_token
    else:
        access_token = client.fetch_access_token()
        return access_token['access_token']

@async_call
def refresh_access_token():
    print("开始刷新token.....")
    while True:
        time.sleep(7000)  # 每隔 7000 秒刷新一次
        client.fetch_access_token()

