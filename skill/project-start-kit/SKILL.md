---
name: project-start-kit
description: 为游戏策划、美术、3D 或代码任务初始化独立项目目录和本地管理面板；接入已有项目时先检查并映射结构，不覆盖原文件。
---

# 独立项目启动

模板包由用户保存到自行选择的位置。先确认该位置包含 template/ 和 tools/init_project.py，缺失时报告，不猜测全局路径，不修改全局配置。

用户要求新建独立项目时：检查目标目录及已有规范；空目录用 `python3 "模板包/tools/init_project.py" "目标目录" --name "项目名"`。先用 `--dry-run` 查看将新增的文件。

已有目录先检查 PROJECT.md、AGENTS.md 和业务目录。写一份临时映射 JSON：`{"reviewedExistingRules":true,"directories":{"原有相对目录":"用途和对应模板目录角色"}}`。用 `--mapping "映射文件" --dry-run` 预览后执行。不移动原有文件，不覆盖已有规范或旧版管理代码；如有冲突报告需人工接入的文件，不自动升级旧项目（升级用 upgrade_project.py）。

初始化后读取项目 PROJECT.md、AGENTS.md、management/PROTOCOL.md 和 management/SCHEMA.md；读取并验证 management/project.json。运行 `python3 "目标目录/management/core.py"`。告知用户项目绝对路径和启动方式；需要打开面板时运行项目 management/server.py。

后续状态修改遵守项目协议，优先用 `python3 management/cli.py`（status/add-task/add-version/submit-review/review/add-deliverable/preview-cleanup），其次使用本地 API 的 etag 保存与冲突处理。已建项目需要跟上母版时，先关闭服务，用 `python3 "模板包/tools/upgrade_project.py" "项目目录" --dry-run` 查看，再按用户确认决定是否加 `--apply-code`。新版本不能继承旧版审核。批次只在建批次、重要移交、收尾更新。不要搭中央数据库，不执行真实付款或自动删除，不触及项目外缓存，不声称所有 AI 都会自动遵守。

一次性小任务可减少记录数量，但不绕过验证。完整流程和字段以项目内文档为准。若目标结构或权限不允许，报告确切路径及已完成步骤，继续可独立执行的检查。
