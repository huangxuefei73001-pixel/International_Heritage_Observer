# 国际遗产观察

一个基于“国际遗产观察”文章库的本地研究问答工具。

它现在有两种使用方式：

- `Codex skill`：适合已经在用 Codex 的人
- `网页问答 bot`：适合不熟悉代码、只想直接提问的人

## 项目包含什么

- `data/library/articles.jsonl`
  已整理好的本地文章库
- `scripts/query_library.py`
  本地命令行问答入口
- `scripts/sync_incremental.py`
  新文章增量补库入口
- `skills/guoji-yichan-guancha/SKILL.md`
  项目内的 skill 源文件
- `web/`
  网页前端
- `backend/`
  网页后端

## 给 Codex 用户使用

### 最省事的方式：clone 后一键安装

1. clone 整个仓库
2. 进入项目根目录
3. 运行：

```bash
python3 scripts/install_codex_skill.py
```

这条命令会自动把 skill 安装到：

`~/.codex/skills/guoji-yichan-guancha/SKILL.md`

而且会把当前电脑上的项目绝对路径自动写进去，所以不用再手改路径。

### 手动方式：拷贝整个项目目录

如果你不想跑安装脚本，也可以手动安装。

把整个项目目录复制给对方：

`/Users/pauline/Documents/国际遗产观察`

不要只发 `SKILL.md`，因为这个 skill 依赖项目里的脚本和文章库。

### 2. 安装 skill

对方需要把下面这个文件：

`skills/guoji-yichan-guancha/SKILL.md`

复制到他自己的：

`~/.codex/skills/guoji-yichan-guancha/SKILL.md`

如果目录不存在，就先创建：

```bash
mkdir -p ~/.codex/skills/guoji-yichan-guancha
```

然后复制：

```bash
cp /你的项目路径/skills/guoji-yichan-guancha/SKILL.md ~/.codex/skills/guoji-yichan-guancha/SKILL.md
```

### 3. 在项目根目录使用

进入项目根目录后，可以直接这样提问：

```bash
PYTHONPATH=src python3 scripts/query_library.py "最近韩国有什么世界遗产动态？" --library data/library/articles.jsonl --limit 5
```

## 给普通用户使用

如果对方不使用 Codex，最适合的方式不是发 skill，而是直接使用你部署好的网页问答 bot。

这样对方只需要打开网页即可提问，不需要安装 Codex，也不需要配置 skill。

当前网页版的最小使用机制是：

- 普通使用者不需要注册，首次打开会自动获得一个独立访客身份
- 每个访客只看到自己的对话与历史
- 管理员通过 `/admin/login` 登录
- 当前管理员账号固定为 `admin`
- 当前管理员密码固定为 `admin`

## 更新文章库

### 增量补库

默认新增目录：

`/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增`

把新下载的 `.docx` 放进去后，运行：

```bash
PYTHONPATH=src python3 scripts/sync_incremental.py
```

这条命令完成后会：

- 把新文章增量写入知识库
- 写入 `data/sync_logs/` 运行日志
- 将 `本次新增` 里的已处理 `.docx` 剪切到同级目录 `已同步归档/时间戳批次/`

这样 `本次新增` 文件夹会自动腾空，方便你下一次继续往里面补新文章。

### 全量重建库

```bash
PYTHONPATH=src python3 scripts/build_library.py --source-dir "<你的文章总目录>" --output-dir data/library
```

## 适合分享给别人时一起说明的两句话

### 如果对方也用 Codex

“最简单的是 clone 仓库后运行 `python3 scripts/install_codex_skill.py`。它会自动把 skill 安装到你的 Codex，并写好本机路径。”

### 如果对方不用 Codex

“直接打开网页提问，不需要安装 skill。”
