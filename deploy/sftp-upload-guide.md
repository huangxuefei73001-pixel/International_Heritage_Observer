# SFTP 手动上传部署指南

这份说明适用于你现在的做法：

- 本地已经完成开发
- 通过 SFTP 手动上传文件到腾讯云轻量服务器
- 上传后再在服务器上执行安装、构建和启动

## 1. 本地需要上传什么

建议只上传精简后的项目文件，不要上传这些内容：

- `web/node_modules/`
- `web/.next/`
- `.pytest_cache/`
- `tests/tmp/`
- `data/library_backup_*`
- 本地临时文件

建议上传后的服务器目录仍然保持为：

```bash
/srv/guoji-yichan-guancha
```

## 2. 推荐上传内容

至少包括这些目录和文件：

- `backend/`
- `src/`
- `web/`
- `data/library/`
- `deploy/`
- `scripts/`
- `pyproject.toml`

如果你是用我准备的压缩包上传，解压后就会是这一套。

## 3. 上传后服务器上的操作顺序

### 3.1 进入项目目录

```bash
cd /srv/guoji-yichan-guancha
```

### 3.2 建立 Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### 3.3 配置 `.env`

把下面这个模板复制为项目根目录的 `.env`：

```bash
cp deploy/server.env.example .env
```

然后把里面这些值改成服务器真实配置：

- `database_url`
- `session_secret`
- `openrouter_api_key`
- `smtp_*`

### 3.4 准备前端

```bash
cd /srv/guoji-yichan-guancha/web
npm install
npm run typecheck
npm run build
```

### 3.5 初始化数据库表

```bash
cd /srv/guoji-yichan-guancha
source .venv/bin/activate
PYTHONPATH=backend:src python3 scripts/init_web_db.py
```

### 3.6 安装服务

```bash
sudo cp deploy/systemd/backend.service /etc/systemd/system/
sudo cp deploy/systemd/frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend.service frontend.service
sudo systemctl start backend.service frontend.service
```

### 3.7 配置 Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/guoji-yichan-guancha
sudo ln -sf /etc/nginx/sites-available/guoji-yichan-guancha /etc/nginx/sites-enabled/guoji-yichan-guancha
sudo nginx -t
sudo systemctl reload nginx
```

## 4. 部署后最小检查

### 后端健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 服务状态

```bash
sudo systemctl status backend.service
sudo systemctl status frontend.service
```

### 前端能否打开

```bash
curl -I http://127.0.0.1
```

## 5. 第一版已知限制

- 现在仍是第一版最小登录态，不是完整生产级鉴权
- 管理员仍通过最小机制访问后台
- 用户侧完整“历史会话恢复”还没有服务端列表接口
- 更新知识库仍然是手动触发
