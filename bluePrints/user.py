import datetime
import json
from datetime import timedelta
from robyn import SubRouter, jsonify
import requests
from sqlalchemy import or_, and_

from models import *
from utils.utils import *
from config import *

userRouter = SubRouter(__file__, prefix="/user")


@userRouter.post("/login")
async def login(request):
    data = request.json()
    nameOrPhone = data["nameOrPhone"]
    password = data["password"]
    agree = data["agree"]
    if not agree:
        return jsonify({
            "status": -1,
            "message": "请同意小程序的协议与隐私政策",
        })
    existUsers = session.query(User).filter(User.username == nameOrPhone).count()
    if existUsers > 1:
        return jsonify({
            "status": -4,
            "message": "存在同名用户，请用手机号登录"
        })
    user = session.query(User).filter(or_(
        User.username == nameOrPhone,
        User.phone == nameOrPhone,
        User.nickname == nameOrPhone)
    ).first()
    if not user:
        return jsonify({
            "status": -2,
            "message": "用户不存在",
        })
    if not user.checkPassword(password):
        return jsonify({
            "status": -3,
            "message": "密码错误",
        })
    signature = calcSignature(user.id)
    rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={signature}&algorithm=sha256"
    sessionid = encode(rawSessionid)
    log = Log(operatorId=user.id, operation="用户登录（密码登录）")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "登录成功",
        "sessionid": sessionid,
    })


"""
微信一键登录接口
登录流程：
1. 小程序端调用/getOpenidAndSessionKey接口获取openid和session_key，发送至服务器端
2. 服务器端调用微信API获取接口调用凭据access_token
3. 计算用户登录态签名signature：用session_key对空字符串签名，即signature = hmac_sha256(session_key, "")
4. 服务器端调用微信API检验登录态。若返回errcode==0，通过openid获取用户进行登录（流程同密码登录）；若返回errcode==87009，签名无效，中止登录
"""


@userRouter.post("/wxLogin")
async def wxLogin(request):
    data = request.json()
    openid = data["openid"]
    session_key = data["session_key"]
    if not openid or not session_key:
        return jsonify({
            "status": -1,
            "message": "openid或session_key不存在"
        })
    params1 = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": APPSECRET,
    }
    res1 = requests.get("https://api.weixin.qq.com/cgi-bin/token", params=params1)
    access_token = res1.json()["access_token"]
    if not access_token:
        return jsonify({
            "status": -2,
            "message": "access_token获取失败"
        })
    signature = hmac.new(session_key.encode("utf-8"), b"", hashlib.sha256).hexdigest()
    params2 = {
        "access_token": access_token,
        "openid": openid,
        "signature": signature,
        "sig_method": "hmac_sha256"
    }
    res2 = requests.get("https://api.weixin.qq.com/wxa/checksession", params=params2)
    errcode, errmsg = res2.json()["errcode"], res2.json()["errmsg"]
    if errcode != 0:
        return jsonify({
            "status": -3,
            "message": f"身份验证失败：{errmsg}"
        })
    # 可以进行登录
    user = session.query(User).filter(User.openid == openid).first()
    if not user:
        return jsonify({
            "status": -4,
            "message": "首次请通过密码登录，之后可进行微信一键登录"
        })
    signature = calcSignature(user.id)
    rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={signature}&algorithm=sha256"
    sessionid = encode(rawSessionid)
    log = Log(operatorId=user.id, operation="用户登录（微信一键登录）")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "登录成功",
        "sessionid": sessionid,
    })


@userRouter.post("/loginCheck")
async def loginCheck(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId, timestamp = res["userId"], res["timestamp"]
    if time.time() - float(timestamp) > 10800:  # 3小时
        return jsonify({
            "status": -2,
            "message": "登录已过期，请重新登录"
        })
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户已登录",
        "data": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "usertype": user.usertype,
        }
    })


@userRouter.post("/getUserInfo")
async def getUserInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户信息获取成功",
        "user": User.to_json(user)
    })


@userRouter.post("/getUsersInfoByIds")
async def getUsersInfoByIds(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userIds = data["userIds"]
    userIds = json.loads(userIds) if isinstance(userIds, str) else list(userIds)
    users = [session.query(User).get(userId) for userId in userIds]
    users = [User.to_json(user) for user in users]
    return jsonify({
        "status": 200,
        "message": "用户信息获取成功",
        "users": users
    })


@userRouter.post("/register")
async def register(request):
    data = request.json()
    username = data.get("username")
    nickname = data.get("nickname")
    gender = data.get("gender")
    phone = data.get("phone")
    password = data.get("password")
    # 唯一性校验
    existUser = session.query(User).filter(User.phone == phone).first()
    if existUser:
        return jsonify({
            "status": -3,
            "message": "该手机号已注册"
        })
    user = User(username=username, nickname=nickname, gender=gender, phone=phone,
                hashedPassword=User.hashPassword(password))
    session.add(user)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "注册成功"
    })


@userRouter.post("/modifyUserInfo")
async def modifyUserInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    modified = False
    userData = data["userData"]
    userData = json.loads(userData)
    for field in userData:
        if userData[field] and getattr(user, field) != userData[field]:
            setattr(user, field, userData[field])
            modified = True
    if not modified:
        return jsonify({
            "status": -2,
            "message": "没有修改的信息"
        })
    log = Log(operatorId=userId, operation=f"修改用户信息")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "用户信息修改成功"
    })


@userRouter.post("/getOpenidAndSessionKey")
async def getOpenidAndSessionKey(request):
    tempCode = request.json().get("tempCode")
    params = {
        "appid": APPID,
        "secret": APPSECRET,
        "js_code": tempCode,
        "grant_type": "authorization_code",
    }
    response = requests.get("https://api.weixin.qq.com/sns/jscode2session", params=params)
    openid = response.json().get("openid")
    session_key = response.json().get("session_key")
    if not openid or not session_key:
        return jsonify({
            "status": -1,
            "message": response.json().get("errmsg")
        })
    return jsonify({
        "status": 200,
        "message": "openid及session_key获取成功",
        "openid": openid,
        "session_key": session_key,
    })


@userRouter.post("/storeOpenid")
async def storeOpenid(request):
    data = request.json()
    sessionid = data["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    openid = data["openid"]
    if not user.openid:
        user.openid = openid
        existUsers = session.query(User).filter(User.openid == openid).all()
        for exiUser in existUsers:
            exiUser.openid = None
        session.commit()
        return jsonify({
            "status": 200,
            "message": "openid保存成功"
        })
    return jsonify({
        "status": -1,
        "message": "openid已存在"
    })


@userRouter.post("/sendEmailCaptcha")
async def sendEmailCaptcha(request):
    data = request.json()
    username = data["username"]
    phone = data["phone"]
    user = session.query(User).filter(User.username == username, User.phone == phone).first()
    if not user:
        return jsonify({
            "status": -1,
            "message": "用户不存在或信息错误"
        })
    if not user.email:
        return jsonify({
            "status": -2,
            "message": "您未登记邮箱，请联系管理员重置密码"
        })
    captcha = generateCaptcha()
    emailCaptcha = EmailCaptcha(captcha=captcha, userId=user.id)
    session.add(emailCaptcha)
    session.commit()
    sendEmail(
        to=user.email,
        subject="忘记密码",
        content=f"【同济-合合信息俱乐部】您好，您正在执行密码重置操作，您的验证码为『{captcha}』，有效期5分钟。若非本人操作请忽略。",
    )
    return jsonify({
        "status": 200,
        "message": "邮箱验证码发送成功"
    })


@userRouter.post("/resetPassword")
async def resetPassword(request):
    data = request.json()
    username = data["username"]
    phone = data["phone"]
    captcha = data["captcha"]
    user = session.query(User).filter(User.username == username, User.phone == phone).first()
    if not user:
        return jsonify({
            "status": -1,
            "message": "用户不存在"
        })
    allCaptchas = user.emailCaptchas
    if datetime.now() - allCaptchas[-1].createdTime > timedelta(minutes=5):
        return jsonify({
            "status": -2,
            "message": "验证码已过期"
        })
    hisCaptchas = [this.captcha for this in allCaptchas]
    for capt in allCaptchas:
        session.delete(capt)
    if captcha not in hisCaptchas:
        return jsonify({
            "status": -3,
            "message": "验证码错误"
        })
    elif captcha in hisCaptchas and captcha != hisCaptchas[-1]:
        return jsonify({
            "status": -2,
            "message": "验证码已过期"
        })
    user.hashedPassword = User.hashPassword("12345")
    log = Log(operatorId=user.id, operation=f"用户重置密码")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "密码已重置为『12345』，请尽快修改密码"
    })


@userRouter.post("/modifyPassword")
async def modifyPassword(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    oldPassword = data["oldPassword"]
    newPassword = data["newPassword"]
    if not user.checkPassword(oldPassword):
        return jsonify({
            "status": -2,
            "message": "原密码输入错误"
        })
    user.hashedPassword = User.hashPassword(newPassword)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "密码修改成功"
    })


@userRouter.post("/getAllUsers")
async def getAllUsers(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    users = session.query(User).order_by(User.username).all()
    users = [{
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "gender": user.gender,
        "phone": user.phone,
        "avatarUrl": user.avatarUrl,
    } for user in users]
    return jsonify({
        "status": 200,
        "message": "全部用户信息获取成功",
        "users": users
    })


@userRouter.post("/searchUser")
async def searchUser(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    searchContent = data["searchContent"]
    try:
        int(searchContent)
        users = session.query(User).filter(User.phone.contains(searchContent)).order_by(User.username).all()
    except ValueError:
        users = session.query(User).filter(User.username.contains(searchContent)).order_by(User.username).all()
    users = [{
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "gender": user.gender,
        "phone": user.phone,
        "avatarUrl": user.avatarUrl,
    } for user in users]
    return jsonify({
        "status": 200,
        "message": "查找用户信息获取成功",
        "users": users
    })
