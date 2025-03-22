import datetime
import json
from datetime import timedelta
from robyn import SubRouter, jsonify
import requests
from sqlalchemy import or_
from sqlalchemy.sql.functions import user

from models import *
from utils.utils import *
from config import *

extrasRouter = SubRouter(__file__, prefix="/extras")


@extrasRouter.post("/getAllNotice")
async def getAllNotice(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    notices = session.query(Notice).order_by(Notice.time.desc()).all()
    notices = [Notice.to_json(notice) for notice in notices]
    return jsonify({
        "status": 200,
        "message": "全部通知公告获取成功",
        "notices": notices
    })


@extrasRouter.post("/releaseNotice")
async def releaseNotice(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    title = data["title"]
    content = data["content"]
    notice = Notice(title=title, content=content, releaserId=userId)
    session.add(notice)
    log = Log(operatorId=userId, operation="发布通知公告")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "通知公告发布成功"
    })


@extrasRouter.post("/deleteNotice")
async def deleteNotice(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    noticeId = data["noticeId"]
    notice = session.query(Notice).get(noticeId)
    session.delete(notice)
    log = Log(operatorId=userId, operation="删除通知公告")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "通知公告删除成功"
    })


@extrasRouter.post("/getAllLogs")
async def getAllLogs(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    if user.usertype != 6:
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    logs = session.query(Log).order_by(Log.time.desc()).all()
    logs = [Log.to_json(log) for log in logs]
    return jsonify({
        "status": 200,
        "message": "全部日志获取成功",
        "logs": logs
    })
