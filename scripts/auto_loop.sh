#!/bin/bash
# AutoTest 永不停止的自我优化循环
set -e

cd /Users/xiaofang/Documents/www/docker/AutoTest

# 确保服务在运行
if ! curl -sf http://localhost:8765/health > /dev/null 2>&1; then
    echo "Starting API server..."
    rm -rf data/ 2>/dev/null || true
    nohup .venv311/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765 > /tmp/autotest-api.log 2>&1 &
    sleep 4
fi

CDIR=$(python3 -c "import urllib.parse; print(urllib.parse.quote('/Users/xiaofang/Documents/www/docker/AutoTest'))")
TURL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('http://localhost:3000'))")
CYCLE=0

while true; do
    CYCLE=$((CYCLE + 1))
    echo ""
    echo "=============================================="
    echo "  CYCLE $CYCLE - $(date '+%H:%M:%S')"
    echo "=============================================="

    # Step 1: 审核代码 → 修复问题
    # (Sisypus continua analyzing and fixing in the background)

    # Step 2: 自我测试
    echo "--- Creating self-test task ---"
    RESP=$(curl -s -X POST "http://localhost:8765/api/v1/tasks?name=cycle$CYCLE&target_url=$TURL&code_dir=$CDIR&mode=quick")
    TID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('task',{}).get('id',''))" 2>/dev/null)

    if [ -z "$TID" ] || [ "$TID" = "None" ]; then
        echo "Failed to create task, restarting server..."
        lsof -ti:8765 | xargs kill -9 2>/dev/null || true
        sleep 1
        rm -rf data/ 2>/dev/null || true
        nohup .venv311/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765 > /tmp/autotest-api.log 2>&1 &
        sleep 4
        continue
    fi

    echo "Task: $TID"
    curl -s -X POST "http://localhost:8765/api/v1/tasks/$TID/start" > /dev/null

    # Step 3: 等待完成 (最长2分钟)
    RESULT=""
    for i in $(seq 1 12); do
        sleep 10
        DATA=$(curl -s "http://localhost:8765/api/v1/tasks/$TID" 2>/dev/null)
        STATUS=$(echo "$DATA" | python3 -c "
import sys,json
d=json.load(sys.stdin)
t=d.get('data',{}).get('task',{})
if t: print(t.get('status','?'), t.get('progress_percent',0), t.get('defect_count',0))
else: print('no_data',0,0)
" 2>/dev/null)
        S=$(echo "$STATUS" | awk '{print $1}')
        if [ "$S" = "completed" ] || [ "$S" = "error" ] || [ "$S" = "blocked" ]; then
            RESULT="$STATUS"
            break
        fi
    done

    # Step 4: 输出结果
    if [ -n "$RESULT" ]; then
        STATUS=$(echo "$RESULT" | awk '{print $1}')
        PROGRESS=$(echo "$RESULT" | awk '{print $2}')
        DEFECTS=$(echo "$RESULT" | awk '{print $3}')
        echo "Result: $STATUS progress=$PROGRESS% defects=$DEFECTS"
    else
        echo "Result: timeout"
    fi

    # 获取详细报告
    if [ -n "$TID" ]; then
        curl -s "http://localhost:8765/api/v1/tasks/$TID/delivery" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'data' in d:
    print('Report: ' + d['data'].get('tester_view',{}).get('summary','')[:100])
" 2>/dev/null || true
    fi

    echo "--- Cycle $CYCLE complete, starting next cycle in 3s ---"
    sleep 3
done
