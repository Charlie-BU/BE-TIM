from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, Boolean, Column, Integer, String, Text, JSON, DateTime, Date, Float
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.ext.mutable import MutableList
from bcrypt import hashpw, gensalt, checkpw

from config import DATABASE_URI

engine = create_engine(DATABASE_URI, echo=True)
# 数据库表基类
Base = declarative_base()
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
Base.metadata.naming_convention = naming_convention
# 会话，用于通过ORM操作数据库
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = Session()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(60), nullable=False)
    nickname = Column(String(60), nullable=True)
    hashedPassword = Column(Text, nullable=False)
    # 性别：男1/女2
    gender = Column(Integer, nullable=False)
    phone = Column(String(60), nullable=True)
    # 用户权限级：普通用户1/普通管理员2/超级管理员6
    usertype = Column(Integer, nullable=False, default=1)
    avatarUrl = Column(Text, nullable=True)
    openid = Column(Text, nullable=True)

    @staticmethod  # 静态方法归属于类的命名空间，同时能够在不依赖类的实例的情况下调用
    def hashPassword(password):
        hashedPwd = hashpw(password.encode("utf-8"), gensalt())
        return hashedPwd.decode("utf-8")

    def checkPassword(self, password):
        return checkpw(password.encode("utf-8"), self.hashedPassword.encode("utf-8"))

    def to_json(self):
        data = {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "gender": self.gender,
            "phone": self.phone,
            "usertype": self.usertype,
            "avatarUrl": self.avatarUrl,
        }
        return data


class Log(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    operatorId = Column(Integer, ForeignKey("user.id"), nullable=False)
    operator = relationship("User", backref="logs")
    operation = Column(Text, nullable=True)
    time = Column(DateTime, default=datetime.now)

    def to_json(self):
        data = {
            "id": self.id,
            "operatorId": self.operatorId,
            "operatorName": self.operator.username,
            "operation": self.operation,
            "time": self.time,
        }
        return data


class EmailCaptcha(Base):
    __tablename__ = "email_captcha"
    id = Column(Integer, primary_key=True, autoincrement=True)
    captcha = Column(Text, nullable=False)
    createdTime = Column(DateTime, nullable=False, default=datetime.now)
    userId = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", backref="emailCaptchas")

    def to_json(self):
        data = {
            "id": self.id,
            "captcha": self.captcha,
            "createdTime": self.createdTime,
            "userId": self.userId,
        }
        return data


class Notice(Base):
    __tablename__ = "notice"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    time = Column(DateTime, default=datetime.now, nullable=True)
    releaserId = Column(Integer, ForeignKey("user.id"), nullable=False)
    releaser = relationship("User", backref="notices")

    def to_json(self):
        data = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "time": self.time,
            "releaserId": self.releaserId,
        }
        return data

# 创建所有表（被alembic替代）
# if __name__ == "__main__":
#     Base.metadata.create_all(bind=engine)
