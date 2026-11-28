#!/usr/bin/env bash
# Double-click this file in Finder to install. (First time only: right-click > Open.)
cd "$(dirname "$0")" || exit 1
bash installers/install.sh
status=$?
echo
read -r -p "Press Enter to close this window..." _
exit $status
