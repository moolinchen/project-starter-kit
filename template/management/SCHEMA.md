# project.json 数据结构 v1

UTF-8 JSON；schemaVersion=1，templateVersion="1.1.0"（仍接受 "1.0.0"，两者字段相同），revision 为服务管理的非负整数。其他模板版本须人工迁移；旧项目不会自动升级，可用模板包 tools/upgrade_project.py --apply-code 迁移（先备份、追加 history）。

project 为对象，name/kind/scope/acceptance/next 都是字符串。其余集合为数组，每条 id 唯一且只含中文、英文字母、数字、下划线、短横线，1–100 字符。使用面板新增可自动生成编号。

| 集合 | 必需字段（除特别说明外均为字符串） |
|---|---|
| tasks | id, title, status（待办/进行中/阻塞/完成）, blocker, batchId（可空） |
| versions | id, taskId, label, paths, note；登记后不可改写 |
| reviews | id, versionId, status（待审核/通过/退回）, issues, evidence；每版本一条 |
| deliveries | id, versionId, path, criteria, status（待验收/已验收） |
| settlements | id, summary, amount（非负有限数字文本或空）, currency, evidence, note |
| batches | id（T012_名称）, purpose, source, paths, retained, status（进行中/待确认/可清理）, blocker, unique（布尔）, running（布尔） |
| seals | 服务生成：id, createdAt（UTC ISO 时间）, snapshot（project/tasks/versions/reviews/deliveries/settlements/batches） |
| history | 服务追加：id, createdAt, action, fromRevision, toRevision |

paths/evidence/retained 是「每行一个路径」的字符串；path 是单一路径。禁止绝对路径、Windows 盘符、反斜杠、空路径段、.、.. 和符号链接。字段可空时用空字符串，不用 null。路径指向业务文件或目录，不上传附件、不复制附件。批次 paths 只允许 `40-review/同批次编号[/子路径]`、`90-tmp/同批次编号[/子路径]`；原有项目路径映射不会自动搬文件。

保存校验允许未来尚未生成的普通业务路径。封版会检查交付、版本工作路径、通过证据实际存在；清理会检查候选和保留成果实际存在。状态枚举、引用完整性、审核结论、金额和可清理条件由 core.py 及 API 执行。浏览器先做基础校验，服务器为最终校验。

可执行校验：`python3 management/core.py [项目绝对路径]`。可执行预览：`python3 management/core.py [项目绝对路径] --preview`（按体积排序，含 summary 汇总）；加 `--write-script` 生成需输入 DELETE 确认的删除脚本（不执行）。完整测试工具在母版包 tests/。
