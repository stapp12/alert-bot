#!/bin/bash
# מפעיל את כל הבוטים במקביל
set -e

echo "[start] מפעיל planner_bot..."
python3 planner_bot.py &
PID_PLANNER=$!

echo "[start] מפעיל growth_bot..."
python3 growth_bot.py &
PID_GROWTH=$!

echo "[start] מפעיל bot_manager..."
python3 bot_manager.py &
PID_MANAGER=$!

echo "[start] מפעיל apify_bot..."
python3 apify_bot.py &
PID_APIFY=$!

echo "[start] כל הבוטים רצים (PIDs: $PID_PLANNER $PID_GROWTH $PID_MANAGER $PID_APIFY)"

# מחכה לאחד מהם — אם מת, מפעיל מחדש
wait -n 2>/dev/null || wait
echo "[start] אחד הבוטים נכבה — Railway יפעיל מחדש"
