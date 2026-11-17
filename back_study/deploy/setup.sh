#!/usr/bin/env bash
# 阿里云服务器（Debian/Ubuntu）一键部署。先把整个仓库放到目标目录
# （git clone 或 scp 都行），再跑：
#
#     bash back_study/deploy/setup.sh api.example.com
#
# 域名要已解析到本机公网 IP，且安全组放行 80/443（只放这两个）。
# 做的事：系统依赖 → venv → app.env 模板 → systemd（unit + start_backend.sh）
#        → nginx → certbot HTTPS。
# **密钥不经过脚本**：跑完手工编辑 <仓库根>/app.env 填 LLM_API_KEY 与
# CORS_ORIGINS，再 systemctl restart edupath。
set -euo pipefail
DOMAIN="${1:?用法: bash setup.sh <api域名>（DNS 已解析到本机）}"
HERE=$(cd "$(dirname "$0")" && pwd)          # back_study/deploy
BACK=$(dirname "$HERE")                     # back_study
APP=$(dirname "$BACK")                      # 仓库根

# data/ 在 .gitignore 里（卡片数据不进版本库）：git clone 来的仓库没有它，
# 必须先把本机 study/data/ 整个 scp 过来，否则服务起来是空库
if [ ! -d "$APP/data" ]; then
    echo "!! 缺 $APP/data —— 卡片数据不在 git 里，先 scp 本机 study/data/ 到服务器" >&2
    exit 1
fi

apt-get update
apt-get install -y python3-venv python3-pip nginx certbot python3-certbot-nginx

# 专用系统账号跑服务：不用 root，nologin 杜绝交互登录。
# 宝塔那台机器上服务本来就在 www 名下，用 `RUN_USER=www bash setup.sh ...` 跳过建账号。
RUN_USER="${RUN_USER:-edupath}"
PY_BIN="${PY_BIN:-$BACK/.venv/bin/python}"
PORT="${PORT:-8081}"
if [ "$RUN_USER" = edupath ]; then
    id -u edupath >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin edupath
fi

cd "$BACK"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f "$APP/app.env" ]; then
    cp deploy/env.example "$APP/app.env"
    echo "!! 已生成 $APP/app.env —— 填好 LLM_API_KEY 和 CORS_ORIGINS 再重启服务"
fi
chmod 600 "$APP/app.env"

# data/ 里有运行数据（store/），服务账号要能写
chown -R "$RUN_USER":"$RUN_USER" "$APP"

# systemd 装的是**两份**文件：unit + start_backend.sh。
# deploy/ 里那两个模板写的就是本仓库服务器上实际在跑的内容（/www/wwwroot/python
# + 宝塔 venv + 8081 + www 账号），别的布局按变量改写一遍即可。
# 为什么不让 unit 直接用 EnvironmentFile：见 start_backend.sh 开头那段。
sed -e "s|/www/wwwroot/python|$APP|g" \
    -e "s|/www/server/pyporject_evn/edupath/bin/python|$PY_BIN|g" \
    -e "s|run\.py 8081|run.py $PORT|g" \
    deploy/start_backend.sh > "$APP/start_backend.sh"
chmod 755 "$APP/start_backend.sh"

sed -e "s|/www/wwwroot/python|$APP|g" \
    -e "s|^User=www$|User=$RUN_USER|" \
    -e "s|^Group=www$|Group=$RUN_USER|" \
    deploy/edupath.service > /etc/systemd/system/edupath.service
systemctl daemon-reload
systemctl enable edupath

sed "s|api.example.com|$DOMAIN|g" deploy/nginx-edupath.conf > /etc/nginx/sites-available/edupath
ln -sf /etc/nginx/sites-available/edupath /etc/nginx/sites-enabled/edupath
# 发行版默认站点占着 default_server，会和我们的 80 段抢请求
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect

systemctl restart edupath
sleep 3
curl -fsS "https://$DOMAIN/api/health" && echo
echo
echo "完成。剩下两步手工："
echo "  1. 编辑 $APP/app.env 填 LLM_API_KEY / CORS_ORIGINS → systemctl restart edupath"
echo "  2. 预置管理员：$PY_BIN $BACK/scripts/make_admin.py <用户名> -"
echo "  看日志：journalctl -u edupath -f"