#!/bin/sh
cd "$(dirname "$0")" || exit 1
printf '请输入新项目完整目录（可拖入目录，不要放在模板包内部）：\n'
IFS= read -r target
printf '请输入项目名称：\n'
IFS= read -r name
python3 tools/init_project.py "$target" --name "$name"
printf '\n完成后可打开项目内的“启动面板.command”。按回车关闭。\n'
read answer
