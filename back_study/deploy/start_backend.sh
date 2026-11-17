#!/bin/bash
# /www/wwwroot/python/start_backend.sh —— systemd ExecStart 的入口，服务器上在跑的这一份
# （注释只有仓库这份有，命令一致）。
# 它存在的唯一理由：**由 bash 来加载环境变量**。systemd 的 EnvironmentFile 不跑 shell
# （引号 / 行内注释 / 变量展开静默失效），宝塔面板填的「环境变量」更是不进进程。
# 所以密钥和普通配置都放在同级的 app.env 里，一份文件、一个来源。
set -a
. /www/wwwroot/python/app.env
set +a

cd /www/wwwroot/python/back_study || exit 1
# pyporject_evn 不是笔误：宝塔把 project_env 拼错了，路径只能照抄。
# 不带 --lan：run.py 默认只绑 127.0.0.1，公网入口只有 nginx 那一个。
exec /www/server/pyporject_evn/edupath/bin/python run.py 8081
