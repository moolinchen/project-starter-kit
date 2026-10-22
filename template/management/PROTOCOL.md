# 工具无关工作协议 1.1.0

## 启动与接入

1. 检查项目现有 PROJECT.md、AGENTS.md、工具规范及目录，不修改全局 AI 配置。
2. 空项目复制模板。已有项目先检查并写目录映射；使用初始化工具的 `--dry-run` 查看仅新增哪些文件，绝不覆盖现有文件。映射用于解释原目录，不强行迁移。模板新增目录用于后续材料。
3. 读取 management/project.json；确认 schemaVersion、templateVersion 和相对路径。运行 `python3 management/core.py`。
4. 启动 `python3 management/server.py`，使用打印的本机地址。各项目启动各自端口、各自 JSON，不共享数据库。

## AI 一行命令（推荐，1.1.0）

AI 与脚本写状态时优先用 `python3 management/cli.py`，不必手动取 token 或 etag：

```sh
python3 management/cli.py status
python3 management/cli.py add-task --title "窗户玻璃调整" --status 进行中
python3 management/cli.py add-version --task T001 --path 30-work/a-v003.png --label "第三版" --note "降低反射"
python3 management/cli.py submit-review --version V003
python3 management/cli.py review --version V003 --result pass --issues "符合验收" --evidence 40-review/accepted/V003.md
python3 management/cli.py review --version V003 --result reject --issues "反射仍过亮"
python3 management/cli.py add-deliverable --version V003 --path 80-deliver/a-final.png --criteria "低反射、可编辑"
python3 management/cli.py preview-cleanup [--write-script]
```

- 服务运行中：CLI 从 `management/.server.lock` 读取端口，调用本机 API（自动取 token/etag）保存。
- 服务未运行：CLI 取得同一把项目锁，通过 core.commit 写入：完整校验、版本不可变检查、revision+1、追加 history（动作带「CLI：」前缀）、旧 JSON 存入 management/recovery、临时文件 + fsync + 原子替换。
- 锁存在但连不上服务（崩溃残留或 1.0.0 旧服务）时 CLI 明确失败，不会绕过锁。冲突退出码 2，其他错误 1。加 `--json` 输出 JSON。
- `add-version`、`add-deliverable`、`review --evidence` 默认要求路径已存在；`--allow-missing` 仅用于登记尚未生成的路径。CLI 没有删除命令。

## 写入与冲突

推荐所有 AI 和面板都通过同一个本地服务保存：GET `/api/project` 返回 `{data, etag, token}`；POST `/api/save` 发送 `{data, etag}`，请求头 `X-Project-Token` 使用此次会话 token。URL 使用启动时打印的回环地址。不要记录 token 到项目文件。

服务器检查所有字段、路径与引用、版本不可变、封版历史不可改写，随后增加 revision，追加 history，在 management/recovery 保存旧 JSON，再用临时文件 + fsync + 原子替换写入 project.json。重复提交相同数据不会增加历史。重复旧请求返回 409，不重复操作。保存返回新的 data 和 etag，客户端以返回值为准。

409 表示磁盘已变化：保留并导出自己的草稿，重新读取最新数据，人工或 AI 合并，再保存；不得盲目覆盖。页面保留未保存草稿且不会自动重试。恢复目录仅作备份，不作状态输入，不自动删除。

若必须离线编辑：先退出本项目所有服务和面板，复制 JSON 备份，保留 revision/history/seals 及已登记版本，编辑后用 core.py 校验，再重启服务核对。外部编辑器不遵守锁时无法保证并发安全。离线校验只检查结构/当前引用，不能证明历史没有被恶意改写。服务使用项目锁拒绝第二个实例；崩溃后需确认 PID 已结束，再手动移除 management/.server.lock。

## 版本、审核与封版

登记版本要绑定任务及实际文件/快照；登记后内容不可修改，新的工作结果使用新的版本编号和新路径。通过需要明确结论和证据；旧版审核不会赋予新版通过。退回已验收版本前，先将依赖交付改为待验收。

面板「版本审核」页对图片版本（png/jpg/jpeg/webp/svg/gif，取版本 paths 中第一张图）显示同任务上一张图片版本与本版的并排对比，或叠图（洋葱皮）滑块。图片由服务 GET `/files/<项目内相对路径>` 只读提供：只限项目目录内的普通图片文件；拒绝 ..、绝对路径、符号链接、隐藏文件（如 .server.lock）和非图片类型；SVG 以沙箱 CSP 返回，不能执行脚本。一个版本一条当前审核；编辑前状态保留在 recovery，操作记入 history。

封版调用 POST `/api/seal`，同样携带 data、etag 和会话请求头；必须先保存草稿。服务校验范围/标准、完成任务、已验收交付、结项记录、无运行中批次、实际文件存在和审核通过，然后保存版本、审核、任务、交付、批次和结算快照。重复同一快照被拒绝。文件本身不会被复制、写保护或哈希锁定；需在 50-versions 保存必要的不可变阶段包并把路径登记到版本。封版锁定的是登记信息。

## 清理

POST `/api/preview` 携带 `{data}` 和会话请求头，基于当前草稿扫描；建议先保存。也可运行 `python3 management/core.py --preview`。每条预览给出批次、确切目录、完整文件列表、普通文件数、字节数、用途/来源、保留成果和阻止原因。不跟随符号链接；范围重叠、缺少保留成果、引用、运行中或唯一副本均阻止。业务记录和历次封版的版本/审核/交付/结算引用都会保留。不会执行删除，没有删除 API。

1.1.0 起预览按体积从大到小排序，每条附 `human` 可读体积和按大小排列的 `fileDetails`；`summary` 给出按分类（40-review / 90-tmp）汇总与总计（全部 / 可人工复核）。重叠范围已被阻止，总计可能重复计算重叠部分。

**删除脚本（可选）**：面板「生成删除脚本」、POST `/api/cleanup-script`（会话请求头，可带 etag）、`python3 management/core.py --write-script` 或 `cli.py preview-cleanup --write-script`，都基于已保存的磁盘状态生成 `90-tmp/cleanup-YYYYMMDD.sh` 与 `.bat`（同名已存在时加 -2、-3，不覆盖）。脚本只列出「可人工复核」项的确切普通文件，被阻止项不写入；运行时先列出清单，必须手动输入 `DELETE` 才继续，逐个确认仍是普通文件再删除，不删除目录。工具从不执行脚本，文件也不设可执行权限；运行方式：`sh 90-tmp/cleanup-日期.sh`。含 `% ! ^ & | < > "` 的路径不写入 .bat，需人工处理。生成后到运行前如有变化，请重新预览并重新生成。

人工清理前重新生成预览，关闭相关程序，核对保留文件能打开，取得项目负责人对确切清单的确认，再按系统文件管理器操作。不要只凭文件夹名称删除。预览是瞬时扫描，不能检测其他程序是否在写入，running 必须如实登记。大目录扫描耗时与文件数相关。

## 模板升级

已建项目不会自动升级。在模板包里运行 `python3 tools/upgrade_project.py <项目目录> --dry-run` 查看差异；去掉 `--dry-run` 只补缺少的文件；加 `--apply-code` 才会把管理代码和协议替换为母版版本（旧文件先备份到 management/recovery/upgrade-时间-from-旧版本/），并迁移 project.json 的 templateVersion（先备份、追加 history）。AGENTS.md、PROJECT.md、目录 README 等用户可编辑文件只报告差异，不替换；工作目录中的文件从不触碰。升级前须关闭本项目服务。

## 一次性小任务

可只填范围、验收、一个任务、一个版本、审核、交付和结项汇总；没有临时材料就不建批次。完整功能仍可使用，封版校验不绕过。
