import time
import base64
import re
import os
import concurrent.futures
import requests
from hydrogram import Client, filters
from hydrogram.enums import ChatAction

test_server = os.getenv("TEST_SERVER")


def get_config(data):
    url = data
    if any(data.startswith(sche) for sche in ["vmess", "trojan", "vless", "ss:"]):
        url = requests.post(
            "https://paste.rs",
            data=data,
            timeout=20,
            headers={"Content-Type": "text/plain"},
        ).text
    elif any(data.startswith(sche) for sche in ["http", "https"]):
        req = requests.get(
            data,
            headers={"User-Agent": "v2rayNG/1"},
            proxies={
                "http": "http://127.0.0.1:6868",
                "https": "http://127.0.0.1:6868",
            },
            timeout=20,
        )
        data = req.text
        if not any(
            data.startswith(sche) for sche in ["vmess", "trojan", "vless", "ss:"]
        ):
            data = base64.b64decode(data).decode()
    else:
        data = base64.b64decode(data).decode()
    data = data.splitlines()
    count = len(data)
    return url, data, count


def start_test(config):
    r = requests.post(test_server, json={"q": config}, timeout=60)
    return r.text


@Client.on_message(filters.command("test"))
def litespeedtest(c, m):
    m.reply_chat_action(ChatAction.TYPING)
    url_pattern = re.compile(
        r"((http[s]?|vmess|trojan|vless|ss)://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)"
    )
    if m.reply_to_message:
        try:
            text = m.reply_to_message.text
        except Exception:
            try:
                text = m.reply_to_message.caption
            except Exception:
                m.reply("Không tìm thấy tin nhắn văn bản", quote=True)
                return
    else:
        try:
            text = m.text
        except Exception:
            try:
                text = m.caption
            except Exception:
                m.reply("Không tìm thấy tin nhắn văn bản", quote=True)
                return
    matches = re.findall(url_pattern, text)
    urls = [match[0] for match in matches]
    if not urls:
        m.reply("Không tìm thấy URL trong tin nhắn văn bản", quote=True)
        return

    def handler(url):
        m.reply_chat_action(ChatAction.TYPING)
        try:
            url, configs, count = get_config(url)
        except Exception:
            uvl = m.reply(f"Liên kết {url} không khả dụng", quote=True)
            time.sleep(10)
            uvl.delete()
            return
        if count is None:
            m.reply(f"Liên kết {url} bị lỗi", quote=True)
            return
        if url.startswith("http"):
            stt = m.reply(
                f"**{m.from_user.first_name}** thực hiện test liên kết {url} với **{count}** cấu hình",
                quote=True,
            )
        else:
            stt = m.reply(
                f"**{m.from_user.first_name}** thực hiện test 1 cấu hình\n{url}",
                quote=True,
            )
        s_msg = m
        first_msg = m
        result_gather = ""
        count = 0
        url = url.replace("--", "%2D%2D")
        for config in configs:
            result = start_test(config)
            result_gather = f"{result_gather}{result}\n"
            s_text = (
                f"{url}"
                + f"\n__Test bởi **[{m.from_user.first_name}](tg://user?id={m.from_user.id})**__"
                + "```\n"
                + result_gather
                + "```"
            )
            if count > 1:
                s_text = "**" + str(count) + "**" + "```\n" + result_gather + "```"
            try:
                s_msg.edit(s_text)
            except Exception as e:
                print(e)
                result_gather = result + "\n"
                s_msg = first_msg.reply(s_text, quote=True)
                count += 1
                if count == 1:
                    first_msg = s_msg
        result_gather = ""
        s_msg = None
        stt.delete()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(handler, urls)
