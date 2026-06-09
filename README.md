# 国际遗产观察

一个基于“国际遗产观察”文章库的本地研究问答 skill。

## 项目包含什么

- `data/library/articles.jsonl`
  已整理好的本地文章库
- `scripts/query_library.py`
  本地命令行问答入口
- `scripts/sync_incremental.py`
  新文章增量补库入口
- `skills/guoji-yichan-guancha/SKILL.md`
  项目内的 skill 源文件

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

而且会自动写入当前电脑上的项目路径，所以不用再手改路径。

### 在项目根目录使用

进入项目根目录后，可以直接这样提问：

```bash
PYTHONPATH=src python3 scripts/query_library.py "最近韩国有什么世界遗产动态？" --library data/library/articles.jsonl --limit 5
```

### 全量重建库

```bash
PYTHONPATH=src python3 scripts/build_library.py --source-dir "<你的文章总目录>" --output-dir data/library
```

## 适合分享给别人时一起说明的两句话

### 如果对方也用 Codex

“最简单的是 clone 仓库后运行 `python3 scripts/install_codex_skill.py`。它会自动把 skill 安装到你的 Codex。”
