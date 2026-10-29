# 纯白看台 · 皇马女足（GitHub 免费更新版）

## 👉 [打开皇马女足网站](https://yanzh23324-star.github.io/madrid-femenino/)

日常看新闻、赛程与赛果，请直接打开上面的链接；无需登录 GitHub。

[查看保留的静态版](https://yanzh23324-star.github.io/madrid-femenino/static.html) · [查看自动更新运行记录](https://github.com/yanzh23324-star/madrid-femenino/actions)

这里是网站的源码仓库，成品网站地址为 [yanzh23324-star.github.io/madrid-femenino](https://yanzh23324-star.github.io/madrid-femenino/)。建议收藏成品网址。


中文球迷专题，基于 GitHub Pages + GitHub Actions。无需服务器租用、数据库、付费 API或 AI API key。

## 当前状态

代码与工作流已完成，并加入标题中文粗译与有来源的常用译名表，通过解析、缓存、译名与失败保护测试。部署和自动更新记录请查看本仓库 Actions；以最近一次成功运行与网页核验时间为准。

- `site/index.html`：自动更新版。浏览器从相对路径 `data/feed.json` 读取数据，适合仓库子路径部署。
- `site/static.html`：保留的原静态网页；不会被更新脚本修改。
- `site/data/feed.json`：最近成功核验的数据及失败状态。
- `scripts/update.py`：仅用 Python 标准库，读取公开官网页面中的结构化状态数据；不执行来源 JavaScript。
- `.github/workflows/update-and-deploy.yml`：自动更新、保存快照并发布 GitHub Pages。
- `src/template.html`：自动更新版页面模板；构建时嵌入一份快照以供本地预览和故障回退。

## 免费条件

使用**公开仓库**、标准 `ubuntu-latest` GitHub-hosted runner、默认 `github.io` 地址。不要改用 larger runner、付费比分接口或购买域名。

GitHub Free 支持公开仓库的 Pages；标准 runner 在公开仓库免费。本项目使用短期（1 天）小型 Pages 构建产物，符合个人非商业球迷站用途。GitHub 仍有带宽、体积、使用政策和调度限制；这里不承诺超出官方额度的流量或永久不变的政策。

当前官方依据：
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

## 自动更新频率与范围

- 新闻：每小时第 17 分钟检查皇马女足官网首页的精选新闻，与旧新闻合并，保留最多 30 条；不是官网完整新闻档案，也不是全网新闻检索。
- 赛程/赛果：每天北京时间 **08:37**，读取女足主页与官方日历，按女足官方球队 ID 过滤，合并并保留最近 45 天、未来 120 天范围内可取得的记录。
- GitHub 的 cron 使用 UTC，已配置为 `17 * * * *` 及 `37 0 * * *`。
- GitHub 任务可能延迟或漏跑；不是严格整点，也不是比赛中实时比分。若长时间不活动，GitHub 可能停用定时任务，应检查 Actions。脚本每日/每小时提交最近核验时间，但不能保证平台永远不会停用任务。
- 新新闻自动生成简体中文标题，保留西语原题和官方报道链接；不翻译或转载新闻全文。已有人工 `titleZh` / `summaryZh` 保留。
- 标题翻译在 Actions 内离线执行：常见足球标题使用已核对的表达规则，其余使用 Meta 的 NLLB-200 distilled 600M，西语直接译成中文，不经英语中转。模型固定版本，不使用远程推理 API，不需要密钥。
- 只有新增标题、原题改动或词表/翻译引擎版本改变时才重新翻译。无新标题时不安装模型依赖、不运行模型；命中足球表达规则时也无需下载模型。
- 中文标题按原题绑定。官网更改标题时移除旧机器译文，等待重新翻译，避免用旧中文搭配新原文。数字、比分或姓名标记校验失败时保留原题并在下一次运行重试。
- `data/translation-glossary.json` 保存可维护的常用译名表，包括别名、译写、类别、依据与官方参考网址；网页快报底部可展开查看。球员译写参考皇马官方中文商店；球队、赛事用语单独标注为本站统一用语，不冒称官方翻译。
- 比赛队名采用中文映射；未知队名保留官方原名，避免猜测。
- 官方已确认 UTC 开球时间直接转换为北京时间/马德里时间；待定时间不会从午夜占位值推算。
- 比分仅在官网标记已结束且最终比分有效时写入。
- 失败保留旧数据和原来的成功时间，在页面展示错误状态。新闻或赛事可以分别成功，不互相清空。
- 每次成功检查即使没有新内容，也会更新核验时间。网页打开期间每 5 分钟读取已发布快照，关闭网页后 Actions 仍可运行。
- 官网访问受限或数据结构变化时任务会报错；不绕过反爬，不把失败页面当成“无新消息”。

## 上传与启用（一次性）

需要一个有管理权限的公开 GitHub 仓库。无需发送 GitHub 密码或令牌到聊天中；通过 GitHub 连接授权或自己本地登录。

1. 将**本目录中的全部内容**上传到仓库根目录，必须包含隐藏的 `.github` 目录，而不是把 ZIP 文件本身上传作为网站源码。
2. 在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
3. 打开 **Actions**；如果有运行许可提示，启用仓库工作流。工作流在仓库默认分支上运行。
4. 选择“更新皇马女足资讯并发布网页”→ **Run workflow**，mode 选 `both`。
5. 等待部署成功，打开运行中的 `github-pages` 环境链接；通常形如 `https://用户名.github.io/仓库名/`（用户站点仓库地址规则不同，以 GitHub 返回值为准）。
6. 验证页面最近核验时间、新闻和赛果。自动更新日志位于 Actions；失败时可按 GitHub 通知设置收到提醒。

工作流权限为仓库内容写入、Pages 发布和 OIDC；仅使用 GitHub 自动提供的 `GITHUB_TOKEN`，不需要自己新建 PAT。若组织策略或分支保护禁止机器人提交，需由仓库管理员允许该流程或调整部署策略；不要为了运行本项目打开付费 runner。

工作流只部署公开仓库的默认分支，避免误在私人仓库消耗计费额度。新默认分支也不需要修改 workflow 中的分支名称。

## 本地运行与修改

Python 3.9+（推荐 3.12）；抓取、构建与单元测试只需标准库：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update.py --mode both
# 可选：只有要运行模型翻译时才安装以下依赖（较大，请在虚拟环境中安装）
# python3 -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
# python3 -m pip install -r requirements-translation.txt
# python3 scripts/translate.py
python3 scripts/build.py
python3 -m http.server 8000 --directory site
```

打开 `http://localhost:8000/`。直接用文件方式打开 `site/index.html` 也可看嵌入快照，但需要 HTTP/Pages 才会读取最新 JSON。

更新样式/交互请编辑 `src/template.html`，然后运行 `scripts/build.py`；不要只修改生成的 `site/index.html`，否则下次自动构建会覆盖。原静态版 `site/static.html` 不属于生成文件。

## 内容与来源

非皇家马德里官方站点。图片、队名、商标归各自权利人。此项目仅聚合官方标题、时间、链接和比赛事实，不转载新闻全文。原静态页的阵容/历史为资料快照，不随小时任务自动更新。

- 官方女足主页：https://www.realmadrid.com/es-ES/futbol/primer-equipo-femenino
- 官方日历：https://www.realmadrid.com/es-ES/calendario?filter-football=primer-equipo-femenino

## 中文粗译维护

- `scripts/translate.py --check` 检查是否有待翻译标题；`--check-model` 检查其中是否有必须运行神经模型的标题；这两个命令都不导入模型、也不联网。
- 执行 `python3 scripts/translate.py` 保存中文标题和 `translation` 来源记录；模型异常不会清空新闻、赛程或人工中文内容。部分失败仍保存成功译文，网页显示剩余待翻译数量，工作流在发布可用快照后报告失败。
- 人工改写机器译文时，应删除该条的 `translation` 和 `translationError`，留下 `titleZh`。没有机器元数据的中文标题视为人工整理，后续更新不覆盖。
- 更改词表后，下次更新自动重译机器标题；改用其他模型或更改表达规则时同时提升 `ENGINE` 版本。
- 模型只下载到 Actions 的 Hugging Face 缓存，约 2.5 GB，不提交到仓库或网站。缓存仅使用一个固定模型版本的 key；不缓存 pip 包。保留标准公开仓库 runner，避免使用付费推理、larger runner 或额外付费缓存额度。
- 模型来源：[Meta / facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M)，固定 revision `f8d333a098d19b4fd9a8b18f94170487ad3f821d`。模型许可 CC BY-NC 4.0，本站为非商业球迷阅读辅助；模型并非足球专用，输出可能有误，不能当成官方中文报道。
- 球员译名依据：[皇马官方中文商店女队导航](https://shop.realmadrid.com/zh-cn/index.html)，核对日期 2026-10-29。同一官方商店的不同页面存在译写差异，词表固定所采用的版本，未确认译写的姓名保留官方拉丁字母。
