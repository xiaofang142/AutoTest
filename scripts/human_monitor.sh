#!/bin/bash
# 真人操作模拟 — 基础导航 + 交互点击交替运行
while true; do
  C=$(cat /tmp/monitor_count 2>/dev/null || echo 0)
  C=$((C + 1))
  echo "$C" > /tmp/monitor_count
  TS=$(date '+%H:%M:%S')
  FAIL=0

  if (( C % 5 == 0 )); then
    # 每5轮运行一次深度交互模拟
    echo "[$TS] CYCLE $C — 真人交互模拟"
    OUTPUT=$(cd /Users/xiaofang/Documents/www/docker/AutoTest && .venv311/bin/python scripts/human_sim.py 2>&1)
    echo "$OUTPUT"
    FAIL=$(echo "$OUTPUT" | grep -c "❌")
  else
    # 基础导航检查
    for page in "/" "/tasks" "/projects" "/knowledge" "/settings"; do
      R=$(curl -s -X POST http://localhost:3100/agent/navigate \
        -H "Content-Type: application/json" \
        -d "{\"url\":\"http://localhost:3000$page\"}" 2>/dev/null)
      OK=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin).get('success',''))" 2>/dev/null)
      [ "$OK" != "True" ] && FAIL=$((FAIL+1))
    done
    if [ "$FAIL" -eq 0 ]; then echo "[$TS] CYCLE $C ✅ 5 pages OK"; else echo "[$TS] CYCLE $C ⚠️ $FAIL failures"; fi
  fi

  sleep 15
done
