# 项目入口

这是一个独立项目，模板版本 **1.1.0**。先打开根目录的「启动面板.command」（macOS），或「启动面板.bat」（Windows）。也可在本目录运行 `python3 management/server.py`。需要 Python 3.9+，没有第三方依赖。

项目名称、范围、验收标准、任务、版本、审核、交付、结项和封版状态，统一阅读 **management/project.json** 或本地面板。此文档不重复维护动态状态。

| 目录 | 用途 |
|---|---|
| 00-brief | 原始需求、合同、参考，默认保留 |
| 10-plan | 计划、决策、已有目录映射 |
| 30-work | 可编辑工程和完整依赖 |
| 40-review | 按任务批次的审核、对比、试渲染；accepted 存精选确认依据 |
| 50-versions | 按需阶段快照、回退包 |
| 80-deliver | 确认交付件 |
| 90-tmp | 按批次的计算中间件、缓存、日志 |
| management | 面板、唯一动态状态、规则与恢复备份 |

AI 接手先读 [AGENTS.md](AGENTS.md)、[工作协议](management/PROTOCOL.md)、[数据说明](management/SCHEMA.md)。完整指南在原始模板包 docs/；项目内协议可独立使用。

不要直接双击 HTML 后期待自动落盘。静态模式只支持手动导入/导出；完整模式由本地服务写入本项目 JSON。
