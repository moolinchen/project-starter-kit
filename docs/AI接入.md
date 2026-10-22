# 给任意 AI 的显式接入提示

复制以下文字到当前项目的新 AI 会话：

> 请先读取本项目 PROJECT.md、AGENTS.md、management/PROTOCOL.md、management/SCHEMA.md，再读取 management/project.json。检查现有规范并遵守本项目内协议。JSON 是唯一动态状态来源；先核对 revision，写状态优先用 `python3 management/cli.py`（自动处理 token/etag/项目锁），其次才用本地服务 API 携带 etag 保存。新版本必须独立审核，禁止改写封版历史，不在 PROJECT.md 双写任务状态。业务路径只用项目内相对路径。材料按稳定任务批次登记，仅生成清理预览，不删除文件或触及全局缓存。完成后运行 management/core.py 校验，收尾时加 --preview，报告实际通过/失败/未运行。

这段提示不保证所有 AI 自动服从；必须核对其实际输出、保存结果和校验记录。

## AI 命令行（1.1.0）

每个项目的 `management/cli.py` 让 AI 一行命令完成常用操作，不需要自己取 token、带 etag 或拼 JSON：

| 命令 | 作用 |
|---|---|
| `status` | 项目、任务、版本审核状态、交付、待审核摘要 |
| `add-task --title 标题 [--status 进行中] [--batch T012_名称]` | 新增任务，编号自动生成 |
| `add-version --task T001 --path 相对路径 [--path …] [--label] [--note]` | 登记不可变版本；路径默认须已存在 |
| `submit-review --version V003 [--note]` | 提交为待审核（已通过的版本拒绝） |
| `review --version V003 --result pass/reject --issues 结论 [--evidence 路径 …]` | 审核；pass 必须有证据路径 |
| `add-deliverable --version V003 --path 交付路径 --criteria 标准 [--accepted]` | 新增交付；`--accepted` 需该版本已通过 |
| `preview-cleanup [--write-script]` | 按体积排序的清理预览；可生成需输入 DELETE 的删除脚本（不执行） |

全局参数：`--project 目录`（默认 cli.py 所在项目）、`--json`（JSON 输出）。退出码：0 成功、1 校验或其他错误、2 冲突/锁占用。

写入路径与面板一致：服务运行时 CLI 读 `management/.server.lock` 里的端口并调用 API；服务未运行时取得同一把项目锁，经 core.commit 校验后写入（history 动作带「CLI：」前缀，旧 JSON 进 management/recovery，原子替换）。锁存在但服务连不上时明确失败，需人工确认旧进程已退出再删除锁。

## 可选初始化 Skill

`skill/project-start-kit/SKILL.md` 是可安装的标准 Skill 文件，本次未安装。请在选定模板库固定位置后，将整个 `project-start-kit` 文件夹按你所用 AI 工具的 Skill 安装方式放置。Skill 首次执行须确认模板包位置，不能猜测或写死此临时任务目录。它调用本包初始化脚本，模板与示例仍在原包内。

## 可选的短全局入口建议

仅当你主动选择时，再手动加到相应 AI 的全局说明：

> 进入项目先检查根目录 AGENTS.md 和 PROJECT.md；若存在则按其中入口读取协议与状态。新项目需要独立启动模板时使用 project-start-kit；已有项目先检查映射，不覆盖原结构。

本交付没有写入任何全局配置，也没有声称全局入口能强制任意 AI 自动执行。

## 可执行验收

1. 读 JSON：确认项目名、schemaVersion=1、revision。
2. 运行 `python3 management/core.py`，必须显示校验通过。
3. 运行 `python3 management/cli.py status`；需要测试 API 时启动 server.py，用 GET /api/project 取得当前数据/etag/token，POST /api/save 保存测试修改，再读回核对。
4. 相同旧 etag 再保存应返回 409；新版本未独立审核时不能验收交付。
5. 运行 `python3 management/core.py --preview`，核对精确清单，不执行删除。

API 细节与限制在项目内 PROTOCOL.md，字段结构在 SCHEMA.md。离线直接改 JSON 只适合退出服务之后的单写入者流程，不能代替 API 冲突保护。
