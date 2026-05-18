#!/bin/bash
# AutoTest 永不停止的页面监控
while true; do
  TS=$(date '+%H:%M:%S')
  CYCLE=$(cat /tmp/monitor_count 2>/dev/null || echo 0)
  CYCLE=$((CYCLE + 1))
  echo "$CYCLE" > /tmp/monitor_count

  FAIL=0
  for page in "/" "/tasks" "/projects" "/knowledge" "/settings"; do
    R=$(curl -s -X POST http://localhost:3100/agent/navigate \
      -H "Content-Type: application/json" \
      -d "{\"url\":\"http://localhost:3000$page\"}" 2>/dev/null)
    S=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin).get('success',''))" 2>/dev/null)
    N=$(echo "$R" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ts=d.get('pageState',{}).get('visibleTexts',[])
print(len(ts))
" 2>/dev/null)
    if [ "$S" != "True" ] || [ -z "$N" ] || [ "$N" -le 0 ]; then
      echo "[$TS] CYCLE $CYCLE ❌ $page"
      FAIL=$((FAIL + 1))
    fi
  done

  if [ "$FAIL" -eq 0 ]; then
    echo "[$TS] CYCLE $CYCLE ✅ all 5 pages OK"
  else
    echo "[$TS] CYCLE $CYCLE ⚠️ $FAIL failures"
  fi

  sleep 15
done
