# 项目内 AI 工作规则

先读 PROJECT.md、management/PROTOCOL.md、management/SCHEMA.md，再读取 management/project.json。检查已有规范；若有冲突先报告，不搬迁旧项目。

- JSON 是动态状态唯一来源。不要在 PROJECT.md 双写任务状态，不另建 sources / records / scratch 或重复清理台账。
- 工程及完整依赖放 30-work；原始需求放 00-brief 默认保留；审核包放 40-review；恢复快照放 50-versions；确认交付放 80-deliver；计算中间件放 90-tmp。
- 每任务使用稳定批次编号，例如 T012_窗户玻璃调整。每批可关联多个路径，只在建批次、重要移交和收尾更新用途、来源/重建、保留成果、状态和阻碍。
- 版本登记后不可改写。新版本单独登记、单独审核；不能继承旧版通过。保留通过版本的实际工作文件或快照，不要原地覆盖所指文件。
- 结算记录只表示汇总和依据，不执行付款，不声称已付款。封版必须校验并锁定具体版本及交付清单，保留历史，不等于清理。
- 所有业务路径为项目内相对路径，禁止 ..、绝对路径、符号链接或越项目根。附件不复制到面板目录。
- 未知用途、可能唯一副本、有引用、运行中材料不得标记可清理。只生成确切清理预览，不执行删除，不触及全局共享缓存。
- 写状态优先使用 `python3 management/cli.py`（status / add-task / add-version / submit-review / review / add-deliverable / preview-cleanup），它自动处理 token、etag 和项目锁，并与面板走同一校验写入路径；不要手写 JSON。
- 无法使用 CLI 时，再使用已启动的本地 API（见协议），按 etag 乐观锁保存。不要在服务运行时直接覆盖 JSON；不要删改封版、版本和历史记录。
- 每次状态写入后运行 `python3 management/core.py`。收尾同时运行 `python3 management/core.py --preview`。如有校验错误须修复并重跑。

这些文件提供明确规则与校验，不保证任意 AI 会自动读取或遵守。用户须显式要求其他 AI 读取它们。
