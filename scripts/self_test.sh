#!/bin/bash
# AutoTest 自我测试脚本
set -e

cd /Users/xiaofang/Documents/www/docker/AutoTest

# Kill old server
lsof -ti:8765 | xargs kill -9 2>/dev/null || true
sleep 1

# Clean database
rm -rf data/ 2>/dev/null || true

# Start server
nohup .venv311/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765 > /tmp/autotest-api.log 2>&1 &
sleep 4

# URL encode
CDIR=$(python3 -c "import urllib.parse; print(urllib.parse.quote('/Users/xiaofang/Documents/www/docker/AutoTest'))")
TURL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('http://localhost:3000'))")

echo "=== Step 1: 创建任务 ==="
RESP=$(curl -s -X POST "http://localhost:8765/api/v1/tasks?name=AutoTest-REAL&target_url=$TURL&code_dir=$CDIR&mode=quick")
TASK_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('task',{}).get('id',''))")
echo "任务ID: $TASK_ID"

echo ""
echo "=== Step 2: 启动 ==="
curl -s -X POST "http://localhost:8765/api/v1/tasks/$TASK_ID/start"
echo ""

echo ""
echo "=== Step 3: 等待执行 ==="
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 5
  DATA=$(curl -s "http://localhost:8765/api/v1/tasks/$TASK_ID" 2>/dev/null)
  LINE=$(echo "$DATA" | python3 -c "
import sys,json
d=json.load(sys.stdin)
t=d.get('data',{}).get('task',{})
if not t: print('no data'); exit()
s=t.get('status','?'); st=t.get('current_stage','?'); p=t.get('progress_percent',0)
e='Y' if t.get('environment_check') else 'N'
u='Y' if t.get('understanding') else 'N'
b='Y' if t.get('blueprint') else 'N'
dv='Y' if t.get('delivery') else 'N'
print(f'{s:20} stage={st:15} progress={p:3} pre={e} und={u} blu={b} del={dv}')
" 2>/dev/null)
  echo "  [$i] $LINE"
  if echo "$LINE" | grep -qE "completed|error|blocked"; then break; fi
done

echo ""
echo "=== Step 4: 结果 ==="
curl -s "http://localhost:8765/api/v1/tasks/$TASK_ID" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
t=d.get('data',{}).get('task',{})
if not t: print(str(d)[:300]); exit()
print(f'状态: {t[\"status\"]}')
print(f'自动化等级: {t[\"auto_level\"]}')
print(f'缺陷: {t[\"defect_count\"]}')
if t.get('blueprint'):
    for s in t['blueprint']['all_steps']:
        print(f'  {s[\"index\"]+1}. {s[\"action\"]} {s.get(\"target\",\"\")[:60]}')
if t.get('delivery'):
    print(f'交付: {t[\"delivery\"][\"tester_view\"][\"summary\"][:120]}')
" 2>/dev/null
