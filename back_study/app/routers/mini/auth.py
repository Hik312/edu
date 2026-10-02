# -*- coding: utf-8 -*-
"""小程序端认证。

与 web 端 /api/auth 同一凭证体系（同一个 token 签发与校验），路径归在
/api/mini 下：小程序不 import web 包的路由，两端策略以后分岔互不影响，
账号数据（db.verify_login）仍是同一份，不会出现两套账号。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
import security
from ...deps import current_user

router = APIRouter(prefix='/api/mini/auth', tags=['小程序'])


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str
    password: str
    displayName: str = ''


def _issue(user):
    return {
        'ok': True,
        'token': security.make_token(user['id'], security.get_secret()),
        'user': user,
    }


@router.post('/login', summary='小程序登录')
def login(body: LoginIn):
    user, err = db.verify_login(body.username, body.password)
    if err:
        # 凭据错用 400（和 web 端同一约定）；401 只留给「token 失效」
        raise HTTPException(400, err)
    return _issue(user)


@router.post('/register', summary='小程序注册')
def register(body: RegisterIn):
    user, err = db.create_user(body.username, body.password, body.displayName)
    if err:
        raise HTTPException(400, err)
    return _issue(user)


@router.get('/me', summary='当前用户')
def me(user=Depends(current_user)):
    return {'ok': True, 'user': user}
