# -*- coding: utf-8 -*-
"""认证：注册 / 登录 / 取当前用户。

**为什么登录失败返回 400 而不是 401**
401 会被前端 `api/client.js` 的拦截器接管，触发「清 token + 跳登录页」。
在登录页上这会产生一个很怪的现象：密码输错，页面刷新一下、提示变成
「登录已过期」。所以「凭据不对」用 400，「token 失效」才用 401 ——
让拦截器只在真正掉线时出手。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import db
import security
from ..deps import current_user

router = APIRouter(prefix='/api/auth', tags=['认证'])


class RegisterIn(BaseModel):
    username: str = Field(..., description='3-20 位字母、数字或下划线')
    password: str = Field(..., description='至少 6 位')
    displayName: str = Field('', description='昵称，可不填，默认用用户名')


class LoginIn(BaseModel):
    username: str
    password: str


def _issue(user):
    """签发 token 并把用户一起返回。

    注册后直接发 token，前端就不用「注册成功 → 再登一次」——
    学习类产品多这一步会掉一批人。
    """
    return {
        'ok': True,
        'token': security.make_token(user['id'], security.get_secret()),
        'user': user,
    }


@router.post('/register', summary='注册')
def register(body: RegisterIn):
    user, err = db.create_user(body.username, body.password, body.displayName)
    if err:
        raise HTTPException(400, err)
    return _issue(user)


@router.post('/login', summary='登录')
def login(body: LoginIn):
    user, err = db.verify_login(body.username, body.password)
    if err:
        # 400 不是 401，理由见模块开头
        raise HTTPException(400, err)
    return _issue(user)


@router.get('/me', summary='当前用户')
def me(user=Depends(current_user)):
    """前端刷新页面时用它确认 token 还有效，顺便拿到用户信息。"""
    return {'ok': True, 'user': user}


@router.get('/users', summary='用户列表（仅管理员）')
def users(user=Depends(current_user)):
    if user.get('role') != 'admin':
        raise HTTPException(403, '只有管理员能看用户列表')
    return {'ok': True, 'users': db.user_all()}
