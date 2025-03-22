import re
from robyn import SubRouter, WebSocket

from utils.imageTools import *

socketRouter = SubRouter(__file__, prefix="/socket")

websocket = WebSocket(socketRouter, "/ws")

ws_ids = []


@websocket.on("message")
async def message(ws, msg):
    # 判断心跳检测
    if msg == "ping":
        await ws.async_send_to(ws.id, "pong")
        return ""
    # 判断断开信号
    if msg == "close":
        ws.close()
        if ws.id in ws_ids:
            ws_ids.remove(ws.id)
        return ""

    if "图片" in msg:
        match = re.search(r"(\d+)\s*张", msg)
        num = int(match.group(1)) if match else 1  # 如果没匹配到，默认1张
        await sendPlantyOfData(ws, num)
        return ""

    if len(ws_ids) != 2:
        print("有人离线")
        return "对方暂时不在线，请稍后再试"
    from_id = ws.id
    to_id = ws_ids[0] if ws_ids[1] == from_id else ws_ids[1]
    await ws.async_send_to(to_id, msg)
    return ""  # 若为异步函数，这个是必须的


@websocket.on("connect")
def connect(ws):
    global ws_ids
    if len(ws_ids) >= 2:
        ws_ids.remove(ws_ids[0])
    ws_ids.append(ws.id)
    ws_ids = list(set(ws_ids))  # 去重
    print("WebSocket已连接：", ws.id)


@websocket.on("close")
def close(ws):
    global ws_ids
    if ws.id in ws_ids:
        ws_ids.remove(ws.id)
    print("WebSocket已关闭")
