# -*- coding: utf-8 -*-
"""路由集合 —— 按「端」分包：

- web/   浏览器 SPA 的接口，前缀 /api/*（历史契约，路径不变）
- mini/  小程序端接口，前缀 /api/mini/*（轻量、分页、面向移动场景）

接口规范（新增端点前先读这段）：
1. 先确定服务的端，放进对应包 —— web 的东西不要塞进 mini，反之亦然；
   跨端共用的逻辑（取数、调度、鉴权）放 db / deps / schemas，两边都 import，
   不允许在两个包里各写一份。
2. 路径归属跟着包走：web 端沿用 /api/*；mini 端一律 /api/mini/*，
   不新增裸 /api/xxx 给小程序用 —— 看路径前缀就能判断调用方。
3. 两端共用同一套 token（security.make_token），账号体系不分裂；
   mini 包里的登录是对同一凭证逻辑的薄封装，不是第二套认证。
4. tags 用「小程序」或各 web 域名，Swagger 左侧栏按端/域分组。
5. 错误一律 {ok:false,msg}（main.py 的异常处理器已统一），状态码：
   凭据错 400、掉线 401、无权限 403、资源没有 404、冲突 409。
"""
from . import mini, web

# main.py 按这个顺序注册；web 在前（既有契约），mini 在后。
ALL = web.ALL + mini.ALL

__all__ = ['ALL', 'mini', 'web']
