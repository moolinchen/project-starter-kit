#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
 echo '需要 Python 3.9 或更新版本。安装后再次打开。'; read answer; exit 1
fi
python3 management/server.py
