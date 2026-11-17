#!/bin/sh
# Наглядный прогон эксперимента: внутри тот же experiment.sh преподавателя,
# но во время прогона каждые 3 с видно, сколько запросов пользователей прошло.
#   ./demo.sh off   - без паттерна
#   ./demo.sh on    - с паттерном
# Полный вывод experiment.sh сохраняется в results/<off|on>.log (лог для репозитория).
MODE=${1:?usage: ./demo.sh off|on}
# отказ варианта 1 (в experiment.sh по умолчанию стоит задержка, поэтому задаем явно)
DEFAULT_FAULT='{"down": true}'
FAULT=${FAULT:-$DEFAULT_FAULT}
export FAULT
mkdir -p results
LOG=results/$MODE.log
rm -f "results/$MODE.csv"            # чтобы не остался старый результат

./experiment.sh "$MODE" > "$LOG" 2>&1 &
EXP=$!
echo "PATTERN=$MODE, отказ $FAULT"
echo "Перезапуск app и запуск нагрузки (~30 с), полный лог: $LOG"
until grep -q "нагрузка пошла" "$LOG" 2>/dev/null; do
  if ! kill -0 $EXP 2>/dev/null; then
    echo "ОШИБКА: experiment.sh остановился. Лог:"; cat "$LOG"; exit 1
  fi
  sleep 1
done
echo

# живой вывод: читаем ответы нагрузки по мере поступления
kubectl logs -f job/load 2>/dev/null | python3 live.py

wait $EXP
CODE=$?
echo
if [ $CODE -ne 0 ] || [ ! -s "results/$MODE.csv" ]; then
  echo "ОШИБКА: experiment.sh завершился с ошибкой (код $CODE). Лог:"
  cat "$LOG"
  exit 1
fi

echo "Итог (metrics.py):"
tail -1 "$LOG"

if [ "$MODE" = on ]; then
  # счетчики паттерна со всех 3 реплик app: куда ушли запросы за этот прогон
  for p in $(kubectl get pods -l app=app -o name); do
    kubectl exec "$p" -- wget -qO- -T 3 localhost:8080/metrics 2>/dev/null
  done | awk '
    /dep_calls_total\{target="a"\}/ {a += $2}
    /dep_calls_total\{target="b"\}/ {b += $2}
    /failover_total/                {f += $2}
    END {printf "Куда ушли запросы: в dep-a %d, в dep-b %d, переключений на dep-b: %d\n", a, b, f}'
fi

echo
if [ -s results/off.csv ] && [ -s results/on.csv ]; then
  python3 timeline.py results/off.csv results/on.csv
fi
