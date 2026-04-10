# 国际遗产观察 Web 恢复检查点

更新时间：2026-04-09

## 当前完成状态

- 后端 Task 1 已完成：`backend/app/main.py`、`config.py`、`database.py`、`models.py`、`schemas.py` 骨架已建好
- 后端 Task 2 已完成：邮箱验证码登录、最小角色区分已完成
- 后端 Task 3 已完成：`/chat/ask` 已接入现有知识库查询逻辑，前端不再传 `library_path`
- 后端 Task 4 已完成：会话与消息持久化已打通
  - `X-Debug-User` 作为当前阶段的最小用户识别方式
  - 新会话创建 / 旧会话复用 / 跨用户会话拒绝 / 回答失败时保留用户提问 都已覆盖
- 管理员后端已完成：
  - `GET /admin/conversations`
  - `POST /admin/refresh-library`
  - 已恢复为沿用你既有的“本次新增”规则，不再擅自改成别的来源目录
- 用户侧前端已完成：
  - `web/` 已建成可构建的 Next.js 应用
  - `/` 为邮箱验证码登录页
  - `/chat` 已接真实后端问答接口
  - 管理员访问 `/chat` 会被带回 `/admin`
- 管理员前端已完成：
  - `/admin` 已有“全部对话 + 更新知识库”两块
  - 登录成功后 `admin` 会跳转 `/admin`，普通用户跳转 `/chat`
- 部署文件已完成：
  - `deploy/nginx.conf`
  - `deploy/systemd/backend.service`
  - `deploy/systemd/frontend.service`
  - `deploy/setup-server.md`
  - `scripts/init_web_db.py`

当前主要剩余项：

- 还没有真正 SSH 到腾讯云服务器执行部署
- 登录态仍是第一版最小实现，还没有生产级会话机制
- `datetime.utcnow()` 仍有弃用 warning，后续可顺手换成时区感知时间

## 已验证命令

- `PYTHONPATH=backend python3 -m pytest backend/tests/test_auth.py -v`
- `PYTHONPATH=backend:src python3 -m pytest backend/tests/test_chat.py -v`
- `PYTHONPATH=backend python3 -m pytest backend/tests/test_admin.py -v`
- `PYTHONPATH=backend:src python3 -m pytest backend/tests -v`
- `PYTHONPATH=backend:src python3 -m pytest backend/tests/test_backend_smoke.py -v`
- `PYTHONPATH=backend:src python3 -m pytest tests/test_query.py -v`
- `cd web && npm run typecheck`
- `cd web && npm run build`
- `python3 -m py_compile scripts/init_web_db.py`

## 当前停留节点

现在正停留在：

`本地开发与部署文件已完成，下一步如继续，应开始实际腾讯云部署 / 服务器联调。`

## 下一步该做什么

1. 如果要正式部署，先提供腾讯云服务器的登录方式或 SSH 信息
2. 在服务器上：
   - 放置代码到 `/srv/guoji-yichan-guancha`
   - 创建 `.venv`
   - `pip install -e .`
   - `cd web && npm install && npm run build`
   - 配置 `.env`
   - 执行 `PYTHONPATH=backend:src python3 scripts/init_web_db.py`
   - 启动 `systemd` 服务与 `nginx`
3. 部署后做联调：
   - 登录页发验证码
   - 用户问答
   - 管理员查看全部对话
   - 管理员手动更新知识库

## 恢复提示词

下次回来时，直接说：

`继续，从恢复检查点接着做`

或引用本文件：

`请按 docs/superpowers/plans/2026-04-09-guoji-yichan-guancha-web-resume-checkpoint.md 继续`
