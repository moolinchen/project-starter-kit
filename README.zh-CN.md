# 中文独立项目启动包 1.1.0

[English](README.md) | 简体中文

从 [中文快速开始](docs/快速开始.md) 开始。

- **template/**：空白母版，复制后各项目完全独立。
- **example-星港窗户演示/**：可打开的虚构示例，有工作文件、审核、交付、结项和两种清理状态。
- **新建项目.command**：macOS 交互式新建工具；已有项目请按详细指南先检查映射。
- **tools/init_project.py**：跨平台初始化工具，只添加缺失文件。
- **tools/upgrade_project.py**（1.1.0）：把已建项目升级到当前母版；补缺少文件，代码差异先 diff，`--apply-code` 才备份后替换并迁移 project.json。
- **management/cli.py**（1.1.0，每个项目内）：AI 一行命令登记任务/版本/审核/交付和清理预览，自动处理 token/etag/项目锁。
- **skill/project-start-kit/**：可安装的初始化 Skill，未自动安装。
- **docs/**：使用、AI 接入、测试报告。
- **tests/**：标准库后端测试与 Node 界面逻辑测试（用户日常使用不需要 Node）。

日常运行仅需 Python 3.9+ 和浏览器，无第三方依赖，无账号、中央数据库或外网发布。Python 安装方式由用户自行选择，本包不安装软件或修改全局 AI 配置。

母版版本为 1.1.0（更新记录见 [CHANGELOG.md](CHANGELOG.md)）。已建项目不会自动跟随母版升级，需手动运行 tools/upgrade_project.py。1.1.0 还新增：审核页图片版本并排/叠图对比；清理预览按体积排序并汇总，可生成需输入 DELETE 确认、从不自动执行的删除脚本。请在自己选择的位置保留完整模板包；不要把实际项目建在母版内。

## 许可证

[MIT](LICENSE) © 2026 moolinchen
