# 调度示例

## cron

```cron
# 每天早上 7:30 拉取数据
30 7 * * * cd /Users/yangyunqing/Desktop/code/yyq/mydashboard && /usr/bin/env bash -lc 'source .venv/bin/activate && python -m kb.main ingest-all'

# 每周一早上 8:00 生成任务草案
0 8 * * 1 cd /Users/yangyunqing/Desktop/code/yyq/mydashboard && /usr/bin/env bash -lc 'source .venv/bin/activate && python -m kb.main weekly-plan'

# 每周五晚上 20:00 导出复盘模板
0 20 * * 5 cd /Users/yangyunqing/Desktop/code/yyq/mydashboard && /usr/bin/env bash -lc 'source .venv/bin/activate && python -m kb.main weekly-review-template'
```

## launchd

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yangyunqing.cognitiveos.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-lc</string>
        <string>cd /Users/yangyunqing/Desktop/code/yyq/mydashboard && source .venv/bin/activate && python -m kb.main ingest-all</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/yangyunqing/Desktop/code/yyq/mydashboard/logs/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/yangyunqing/Desktop/code/yyq/mydashboard/logs/launchd_stderr.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```
