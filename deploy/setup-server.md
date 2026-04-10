# 腾讯云轻量服务器部署说明

以下步骤按“单台腾讯云轻量服务器”设计，适合当前第一版。

## 1. 服务器准备

建议系统：

- Ubuntu 22.04 LTS

建议先安装基础依赖：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib nodejs npm
```

说明：

- 当前项目已兼容 `Python 3.10+`
- 如果系统自带的 Node 版本过低，请改用 Node 18 或更高版本

## 2. 放置项目目录

建议部署路径：

```bash
/srv/guoji-yichan-guancha
```

把项目代码放进去后，目录结构应至少包含：

- `backend/`
- `src/`
- `web/`
- `data/`
- `deploy/`
- `pyproject.toml`

## 3. 创建 Python 虚拟环境

```bash
cd /srv/guoji-yichan-guancha
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

这一步会安装 FastAPI、SQLAlchemy、`uvicorn`、`psycopg` 等后端依赖。

## 4. 准备数据库

第一版推荐直接使用 `SQLite`，这样不需要额外安装和初始化 PostgreSQL。

在项目目录准备一个本地数据库文件即可，例如：

```bash
mkdir -p /srv/guoji-yichan-guancha/data/runtime
```

项目里已经提供了最小初始化脚本。配置好 `.env` 后运行：

```bash
cd /srv/guoji-yichan-guancha
source .venv/bin/activate
PYTHONPATH=backend:src python3 scripts/init_web_db.py
```

## 5. 配置后端环境变量

在项目根目录创建：

```bash
/srv/guoji-yichan-guancha/.env
```

建议内容：

```bash
database_url=sqlite:////srv/guoji-yichan-guancha/data/runtime/app.db
session_secret=replace-with-a-long-random-string
openrouter_api_key=your-openrouter-key
openrouter_model=openai/gpt-4.1-mini
smtp_host=smtp.example.com
smtp_port=587
smtp_username=your-smtp-user
smtp_password=your-smtp-password
smtp_sender=bot@example.com
library_path=/srv/guoji-yichan-guancha/data/library/articles.jsonl
incoming_source_dir=/srv/guoji-yichan-guancha/data/incoming
sync_log_dir=/srv/guoji-yichan-guancha/data/sync_logs
```

注意：

- 如果你想继续沿用当前本地“本次新增”目录逻辑，服务器上需要准备等效目录并把 `incoming_source_dir` 指向它
- 前端通过 `NEXT_PUBLIC_API_BASE_URL=/api` 访问后端，所以 Nginx 要保留 `/api/` 转发

## 6. 构建前端

```bash
cd /srv/guoji-yichan-guancha/web
npm install
npm run build
```

## 7. 安装 systemd 服务

复制服务文件：

```bash
sudo cp /srv/guoji-yichan-guancha/deploy/systemd/guoji-yichan-backend.service /etc/systemd/system/
sudo cp /srv/guoji-yichan-guancha/deploy/systemd/guoji-yichan-frontend.service /etc/systemd/system/
```

加载并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable guoji-yichan-backend.service guoji-yichan-frontend.service
sudo systemctl start guoji-yichan-backend.service guoji-yichan-frontend.service
```

检查状态：

```bash
sudo systemctl status guoji-yichan-backend.service
sudo systemctl status guoji-yichan-frontend.service
```

## 8. 配置 Nginx

复制站点配置：

```bash
sudo cp /srv/guoji-yichan-guancha/deploy/nginx.conf /etc/nginx/sites-available/guoji-yichan-guancha
sudo ln -sf /etc/nginx/sites-available/guoji-yichan-guancha /etc/nginx/sites-enabled/guoji-yichan-guancha
sudo nginx -t
sudo systemctl reload nginx
```

## 9. 最小验证

后端健康检查：

```bash
curl http://127.0.0.1:8000/health
```

前端本地代理：

```bash
curl -I http://127.0.0.1
```

前端类型与构建：

```bash
cd /srv/guoji-yichan-guancha/web
npm run typecheck
npm run build
```

后端测试：

```bash
cd /srv/guoji-yichan-guancha
PYTHONPATH=backend:src python3 -m pytest backend/tests -v
```

数据库初始化：

```bash
cd /srv/guoji-yichan-guancha
source .venv/bin/activate
PYTHONPATH=backend:src python3 scripts/init_web_db.py
```

## 10. 当前版本的已知限制

- 现在的登录态和管理员校验仍是第一版最小实现，还没有完整生产级认证
- 管理员更新知识库仍是“手动触发”
- 用户侧会话列表仍未做完整的服务端恢复接口
- 当前还没有数据库迁移系统，仍以初始化脚本为主
- 第一版默认使用 SQLite，适合当前轻量用户规模；后续用户变多后可再切 PostgreSQL
