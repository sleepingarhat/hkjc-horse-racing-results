#!/bin/bash
while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') 啟動 scraper..."
    python RacingData_Scraper.py
    EXIT_CODE=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') Scraper 退出 (code=$EXIT_CODE)，5秒後重啟..."
    pkill -f chromium 2>/dev/null
    pkill -f chromedriver 2>/dev/null
    sleep 5
done
