#!/bin/bash
# Launch read-only inventory HTTP server in background (port 5000)
python inventory_server.py &
INVENTORY_PID=$!
echo "$(date '+%Y-%m-%d %H:%M:%S') 啟動 inventory_server.py (pid=$INVENTORY_PID)"

# Launch periodic GitHub backup (default every 30 min, first push after 10 min warm-up)
python git_sync_periodic.py &
SYNC_PID=$!
echo "$(date '+%Y-%m-%d %H:%M:%S') 啟動 git_sync_periodic.py (pid=$SYNC_PID)"

# run_pool launches RunAll inside a fresh process group via setsid so we can
# kill ONLY this pool's chromium/chromedriver children on iteration boundaries
# without touching the other pool's live browsers.
run_pool() {
    local pool=$1
    while true; do
        echo "$(date '+%Y-%m-%d %H:%M:%S') [Pool $pool] 啟動 RunAll..."
        setsid python RunAll_Scrapers.py --pool "$pool" --no-push &
        local runall_pid=$!
        wait "$runall_pid"
        local code=$?
        echo "$(date '+%Y-%m-%d %H:%M:%S') [Pool $pool] RunAll 退出 (code=$code)，清理本 pool 進程組..."
        # Kill the entire process group started by setsid (PGID == runall_pid).
        # This reaps any orphaned chromium/chromedriver that selenium failed to
        # quit, but leaves the OTHER pool's browsers untouched.
        kill -9 -- -"$runall_pid" 2>/dev/null
        sleep 10
        echo "$(date '+%Y-%m-%d %H:%M:%S') [Pool $pool] 重啟..."
    done
}

# Launch the two pools in parallel — Pool A grinds through ~3000 horses (~25h),
# Pool B finishes in ~20 min and keeps trial/entry/jockey/trainer data fresh.
run_pool A &
POOL_A_PID=$!
echo "$(date '+%Y-%m-%d %H:%M:%S') 啟動 Pool A (horse-heavy) pid=$POOL_A_PID"

run_pool B &
POOL_B_PID=$!
echo "$(date '+%Y-%m-%d %H:%M:%S') 啟動 Pool B (trial/entry/jockey/trainer) pid=$POOL_B_PID"

# GitHub push is owned by git_sync_periodic.py (every 30 min). The pool
# loops use --no-push so they don't fight each other over .git/index.lock.
wait
