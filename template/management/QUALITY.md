# 可选工程质量检查 / Optional quality gates

默认关闭，不增加启动包运行依赖。仅用于代码或游戏工程任务；纯策划、美术、3D、文档任务沿用原协议。启动包自身状态校验仍按原规则执行。

## 接入

1. 检查工程根目录（通常 30-work 下的子目录）、现有规范、工具版本和脚本，不改变原有工程结构。优先复用既有检查命令，不为已有工程重复安装工具。
2. 经用户确认后将 quality.example.json 复制为 management/quality.local.json，填写实际工程的检查步骤。该配置由用户维护；不要放密钥。未配置时检查明确返回 incomplete，而非通过。
3. 每个步骤使用 name、level（quick / verify / release）、cwd（项目内相对目录）、argv（命令及参数数组）、timeout（秒，1–3600）。例：
```json
{"schemaVersion":1,"steps":[
  {"name":"lint","level":"quick","cwd":"30-work/game","argv":["npm","run","lint"],"timeout":120},
  {"name":"typecheck","level":"verify","cwd":"30-work/game","argv":["npm","run","typecheck"],"timeout":180},
  {"name":"test","level":"verify","cwd":"30-work/game","argv":["npm","run","test"],"timeout":180},
  {"name":"build","level":"release","cwd":"30-work/game","argv":["npm","run","build"],"timeout":600}
]}
```
仅在实际 package.json 已定义对应脚本时使用此例。Windows 上优先使用实际可运行的可执行文件或显式 node/python 入口，勿为绕过问题改用 shell=True。命令必须由用户审核；脚本可执行任意本地代码，runner 并非沙箱。不要配置安装、部署、付款、删除或全工程格式化命令。未经授权不得新增依赖、修改全局环境、执行未知脚本。

## 分级与成本

- quick：代码任务收尾时运行轻量、只读检查；优先任务相关范围。格式化属于单独修改操作，仅允许本次任务中适用的源文件，不能整库自动重写。检查若只能全量运行，评估耗时后移到 verify。
- verify：重要功能完成时；包含 quick、类型/编译检查和相关测试。
- release：版本验收或发布前；包含前两级及完整回归/构建（不执行真实发布）。依然需要人工体验验收。

项目根目录运行：
```sh
python3 management/quality.py quick
python3 management/quality.py quick --run
python3 management/quality.py verify --run
python3 management/quality.py release --run
```
不加 --run 只显示计划；首次或命令变更后先审查计划。仅运行用户已批准的配置。成功只输出名称和退出码，失败输出最后 4096 字节，不自动读全量日志；首个失败停止，不自动重试。退出码 0=计划或已配置等级检查通过，1=命令失败/超时/不可运行，2=配置错误或未配置所需等级。等级通过不代表所有可能检查均有覆盖。必要时单独针对失败命令收集更多日志，归入既有任务批次。不自动写 project.json，不新增状态台账。

AI 默认最多两次自动修复并重跑；超限、环境缺失、涉及架构/依赖/大范围变更则报告阻碍。不能通过禁用规则、删测试、改验收标准来假装通过。交付只报检查等级、成功/失败/未运行及阻碍；人工需要的细节才展开。Git 检查只在现有 Git 工程执行，使用 diff --stat / diff --name-only 先看范围，随后读取相关 diff；不可自动提交、重置或删除用户改动。大型编译可能消耗 CPU、磁盘及 CI 分钟，但不直接调用大模型。

## 引擎接入预设（选择其一，实际命令依版本和工程配置确认）

| 工程 | quick | verify | release |
|---|---|---|---|
| Godot GDScript | gdformat --check / gdlint 指定文件 | Godot headless 解析/导入，已有 GUT 或 GdUnit 测试 | 完整测试、已有 export preset 构建 |
| Godot .NET / Unity | 已有 C# formatter / Roslyn 检查 | Godot .NET build；Unity batchmode EditMode/PlayMode 测试（按工程选择） | 目标平台构建及回归 |
| Unreal C++ | 项目 clang-format dry-run / clang-tidy（必要时移到 verify） | Unreal Build Tool / Automation Test | 项目既有 UAT 构建与回归 |
| Unreal TypeScript / WebGL / Three.js | 现有 Biome 或 Prettier + ESLint | TypeScript 类型检查、相关测试 | 项目既有全量测试和 build |

Unity/Unreal 的 CLI、授权、项目文件路径及目标平台须在本地验证。不要对 Unity 的 .meta、Godot .tscn/.tres、Unreal 资产、生成代码、第三方库执行通用格式化。引擎二进制及缓存排除在源文件范围外。工具配置和版本放在实际工程并随其版本管理。模板不自动安装这些工具，也不覆盖原有配置。

## 已有项目

使用母版升级工具的 dry-run 先查看新增模块；用户自行合并 AGENTS.md，既有质量配置不会被覆盖。本模块不改变 schemaVersion/templateVersion 或现有管理流程。已有项目可不启用。
