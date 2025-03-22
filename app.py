from robyn import Robyn, ALLOW_CORS, jsonify

from bluePrints.extras import extrasRouter
from bluePrints.user import userRouter
from bluePrints.socketRouter import socketRouter
from models import User, session

app = Robyn(__file__)
ALLOW_CORS(app, origins=["*"])

# 注册蓝图
app.include_router(userRouter)
app.include_router(extrasRouter)
app.include_router(socketRouter)


@app.get("/")
async def index():
    return "Welcome to TIM"


@app.get("/aaa")
async def aaa():
    user = User(username="admin", phone="11111111111", hashedPassword=User.hashPassword("tjhh666"), gender=1)
    session.add(user)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "success",
    })


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8081)
