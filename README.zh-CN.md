# 项目启动包 1.1.0

[English](README.md) | 简体中文

## 交给 AI 就能用

这个包的说明和工具都是写给 AI 读的，可以直接交给 AI 全自动执行，不需要你手动点脚本：

- AI 读项目里的 `AGENTS.md` 和 `docs/AI接入.md`，就知道目录怎么放、状态怎么记。
- 建项目、升级旧项目、登记任务/版本/审核/交付、生成清理预览，AI 都可以自己用命令完成（`tools/init_project.py`、`tools/upgrade_project.py`、`management/cli.py`）。
- **网页工作台是给人用的**：看进度、审图、验收交付。
- **不可逆的操作要人确认**：升级时替换管理代码（`--apply-code`）、执行清理删除脚本。工具本身不会自动删除任何文件，删除脚本也必须由人手动运行并输入 `DELETE`。

可以复制给 AI 的示例指令：

> 项目启动包在「模板包路径」。请先读它的 README.zh-CN.md 和 docs/AI接入.md，在「目标目录」新建一个名为「项目名」的项目（先 --dry-run 给我看）。之后按项目里 AGENTS.md 的规则工作：文件放进对应目录，任务、版本、审核、交付用 `python3 management/cli.py` 登记，不要手写 JSON。每次收尾运行 `python3 management/core.py --preview` 报告校验结果和可清理文件。需要 `--apply-code` 升级或删除文件时，先停下问我。

AI 不一定每次都完全照做，关键结果请在工作台里核对。

## 为什么做这个

和 AI 一起做策划案、美术、3D 或代码时，常见这些问题：

- **文件到处放**：需求、工程、审核图、交付物、临时缓存混在一起，换个 AI 或过几周就找不到。
- **版本和审核记录散落**：哪一版通过了、谁说的、依据是什么，只存在聊天记录里；改了新版也说不清是否重新审过。
- **交付物难找**：最终交了哪个文件、是否验收，没有统一记录。
- **临时文件越堆越多**：渲染缓存、日志不敢删，删了又怕误删审核证据。

这个包的做法：

- 每个项目用同一套目录（00-brief 到 90-tmp），每类文件有固定位置，AI 和人都按同样规则放。
- 所有状态只记在一个 `management/project.json` 里；每次保存都会校验、写历史、备份旧数据。
- 版本登记后不可修改；新版本不会继承旧版的审核结论，通过审核必须写依据文件路径。
- 交付必须对应已通过审核的版本才能验收；项目可以封版，封版历史不能改写。
- 临时材料按批次登记，清理只出预览清单，仍被审核引用的不让清理；可生成需人工确认的删除脚本。
- 审图时可把同一任务的上一版和本版并排或叠图对比。
- 只需 Python 3.9+ 和浏览器，没有第三方依赖、账号、数据库，数据都在本机项目里。每个项目独立，互不影响。

## 快速上手

### 方式一：交给 AI

把上面的示例指令发给你的 AI（需要它能读写本机文件、运行命令）。它会用 `tools/init_project.py` 建项目，用 `management/cli.py` 记录工作。你需要看进度或审图时，打开工作台（见下）。

也可以把 `skill/project-start-kit/` 按你所用 AI 工具的方式安装成 Skill，之后直接说"新建一个独立项目"。

### 方式二：手动

1. 先看示例：进入 `example-星港窗户演示`，macOS 双击「启动面板.command」，Windows 双击「启动面板.bat」，或运行 `python3 management/server.py`。浏览器会打开 `http://127.0.0.1:端口`。
2. 在网页里编辑后，点「确认修改」，再点「保存到项目」才会写入。关闭服务：在启动窗口按 Ctrl+C。
3. 新建项目：把 `template` 整个文件夹复制到你想放的位置并改名；或双击根目录「新建项目.command」（macOS）；或运行：

```sh
python3 tools/init_project.py /项目位置/新项目 --name "项目名称" --dry-run
python3 tools/init_project.py /项目位置/新项目 --name "项目名称"
```

不要把实际项目建在模板包里面。更多见 [docs/快速开始.md](docs/快速开始.md)。

## 文件夹和文件说明

### 顶层

| 路径 | 作用 |
|---|---|
| `template/` | 空白项目母版，复制一份就是一个新项目 |
| `example-星港窗户演示/` | 虚构的完整示例，有工作文件、审核、交付和清理状态，可直接打开工作台看 |
| `tools/` | 建项目和升级项目的工具 |
| `skill/project-start-kit/` | 可选的 AI Skill，教 AI 如何用本包建项目；不会自动安装 |
| `docs/` | 使用说明 |
| `tests/` | 自动测试 |
| `新建项目.command` | macOS 交互式新建项目 |
| `CHANGELOG.md` | 版本更新记录 |
| `MANIFEST.sha256.json` | 全部文件的校验值，用来确认包是否完整、未被改动 |
| `LICENSE` | MIT 许可证 |

### 项目目录（template 内，每个项目都一样）

| 目录 | 放什么 |
|---|---|
| `00-brief/` | 原始需求、合同、参考资料，默认一直保留 |
| `10-plan/` | 计划、决策记录、接入已有项目时的目录映射 |
| `30-work/` | 可编辑的工程文件和完整依赖（不只是预览图） |
| `40-review/` | 按任务批次存放审核对比包；`accepted/` 放通过后精选的确认依据 |
| `50-versions/` | 重要阶段的快照和回退包，不需要每次修改都存 |
| `80-deliver/` | 已确认的交付文件 |
| `90-tmp/` | 按批次存放计算中间件、缓存、日志，是清理的主要对象 |
| `AGENTS.md` | 给 AI 的项目规则：先读什么、文件放哪、怎么写状态 |
| `PROJECT.md` | 项目入口说明：怎么启动工作台、各目录用途 |
| `启动面板.command` / `启动面板.bat` | 双击启动工作台（macOS / Windows） |

### management/（每个项目内的工作台）

| 文件 | 作用 |
|---|---|
| `project.json` | 项目唯一的状态记录：概况、任务、版本、审核、交付、批次、结项、封版、历史 |
| `server.py` | 本机网页服务，提供工作台页面和保存接口 |
| `index.html` / `app.js` / `style.css` | 工作台网页 |
| `core.py` | 校验、保存、历史与备份、清理预览的核心逻辑；也可直接运行做校验 |
| `cli.py` | 给 AI 和脚本用的命令行 |
| `PROTOCOL.md` | 读写规则和接口说明 |
| `SCHEMA.md` | `project.json` 字段结构 |
| `recovery/`（运行后生成） | 每次保存前的旧数据备份和升级备份 |

### tools/

| 文件 | 作用 |
|---|---|
| `init_project.py` | 新建项目，或给已有目录补上模板文件；只添加缺少的文件，不覆盖 |
| `upgrade_project.py` | 把已建项目升级到当前母版版本 |

### tests/

`test_project.py`、`test_v110.py`（Python 标准库）和 `test_ui_logic.js`（Node）。日常使用不需要 Node。`test_v110.py` 中的升级测试需设置环境变量 `PROJECT_KIT_V100` 指向 1.0.0 包，否则跳过。

### docs/

| 文件 | 内容 |
|---|---|
| `快速开始.md` | 五分钟上手 |
| `详细指南.md` | 保存与恢复、材料归档、清理、审核对比、升级、封版等 |
| `AI接入.md` | 给 AI 的接入提示词、CLI 命令表、验收步骤 |
| `测试报告.md` | 已验证和未验证的内容 |

## 升级已建项目

已建项目不会自动跟随母版升级。先关闭该项目的工作台，再运行：

```sh
python3 tools/upgrade_project.py 项目目录 --dry-run      # 只看差异，不写入
python3 tools/upgrade_project.py 项目目录                # 只补缺少的文件
python3 tools/upgrade_project.py 项目目录 --apply-code   # 备份后替换管理代码，并迁移 project.json（需人确认）
```

旧代码备份在 `management/recovery/upgrade-时间-from-旧版本/`。`AGENTS.md`、`PROJECT.md` 等可编辑文件只报告差异，工作文件不会被动。

## CLI

在项目目录运行 `python3 management/cli.py <命令>`：

| 命令 | 作用 |
|---|---|
| `status` | 查看项目、任务、审核、交付摘要 |
| `add-task` | 新增任务 |
| `add-version` | 登记版本（不可修改） |
| `submit-review` | 提交审核 |
| `review` | 审核通过或退回（通过须带依据路径） |
| `add-deliverable` | 登记交付 |
| `preview-cleanup [--write-script]` | 清理预览；可生成需输入 DELETE 的删除脚本，不会执行 |

参数详见 [docs/AI接入.md](docs/AI接入.md)。CLI 没有删除命令。

## 安全说明

- 工作台只监听本机回环地址 `127.0.0.1`，外部设备访问不到；拒绝跨来源写入。
- 写入需要每次启动时临时生成的会话 token，只在内存中，不写入任何文件。
- 图片接口只读，只提供项目内的普通图片文件。
- 不自动删除文件，不修改全局配置或缓存，不涉及付款。

## 引用与商用

本项目使用 [MIT 许可证](LICENSE)：可以自由使用、修改、分发和商用，只需在副本中保留版权署名 `Copyright (c) 2026 moolinchen` 和许可证全文。

建议引用写法：

> 本项目基于 [Project Starter Kit](https://github.com/moolinchen/project-starter-kit)（© 2026 moolinchen，MIT 许可证）。
