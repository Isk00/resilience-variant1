#!/bin/sh
# Наглядный прогон эксперимента: то же самое, что experiment.sh,
# но во время прогона каждые ~3 с видно, что происходит.
#   ./demo.sh off   - без паттерна
#   ./demo.sh on    - с паттерном
# Полный вывод experiment.sh сохраняется в results/<off|on>.log (это и есть лог для репозитория).
MODE=${1:?usage: ./demo.sh off|on}
# отказ варианта 1 (в experiment.sh по умолчанию стоит задержка, поэтому задаем явно)
DEFAULT_FAULT='{"down": true}'
FAULT=${FAULT:-$DEFAULT_FAULT}
export FAULT
mkdir -p results
LOG=results/$MODE.log

./experiment.sh "$MODE" > "$LOG" 2>&1 &
EXP=$!
echo "PATTERN=$MODE: перезапуск app и подготовка нагрузки (~30 с), лог: $LOG"
until grep -q "нагрузка пошла" "$LOG" 2>/dev/null; do
  kill -0 $EXP 2>/dev/null || { cat "$LOG"; exit 1; }
  sleep 1
done
T0=$(date +%s)

# снимок счетчиков всех реплик app + проверка dep-a, одной командой внутри первого пода
snapshot() {
  IPS=$(kubectl get pods -l app=app --field-selector=status.phase=Running -o jsonpath='{.items[*].status.podIP}')
  POD=$(kubectl get pods -l app=app --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
  kubectl exec "$POD" -- sh -c "for ip in $IPS; do wget -qO- -T 1 http://\$ip:8080/metrics; done; \
    wget -qO- -T 1 http://dep-a/work >/dev/null 2>&1 && echo DEPA up || echo DEPA down" 2>/dev/null
}
sum() { echo "$SNAP" | awk -v k="$1" 'index($1, k) == 1 {s += $2} END {print s + 0}'; }
bar() {  # bar ok all
  awk -v ok="$1" -v n="$2" 'BEGIN {
    if (n == 0) { printf "%-20s %7s", "", "-"; exit }
    f = int(20 * ok / n + 0.5); s = ""
    for (i = 0; i < 20; i++) s = s (i < f ? "█" : "░")
    printf "%s %3d/%-3d", s, ok, n }'
}

echo
echo " время | dep-a    | ответы пользователям         | куда ушли запросы  | переключений на dep-b"
echo "-------+----------+------------------------------+--------------------+----------------------"
P_OK=0; P_ERR=0; P_A=0; P_B=0; P_F=0; FIRST=1
while kill -0 $EXP 2>/dev/null; do
  SNAP=$(snapshot)
  T=$(( $(date +%s) - T0 ))
  OK=$(sum 'requests_total{code="200"}')
  ALL=$(sum 'requests_total')
  A=$(sum 'dep_calls_total{target="a"}')
  B=$(sum 'dep_calls_total{target="b"}')
  F=$(sum 'failover_total')
  case "$SNAP" in *"DEPA up"*) DEPA="работает" ;; *"DEPA down"*) DEPA="ОТКАЗ   " ;; *) DEPA="?       " ;; esac
  if [ $FIRST = 0 ]; then
    dOK=$((OK - P_OK)); dALL=$((ALL - P_ALL)); dA=$((A - P_A)); dB=$((B - P_B)); dF=$((F - P_F))
    if [ "$MODE" = on ]; then WHERE=$(printf "%-18s" "dep-a $dA, dep-b $dB"); else WHERE="только dep-a      "; fi
    [ "$MODE" = on ] && FO="+$dF" || FO="-"
    printf "%4d с | %s | %s | %s | %s\n" "$T" "$DEPA" "$(bar $dOK $dALL)" "$WHERE" "$FO"
  fi
  P_OK=$OK; P_ALL=$ALL; P_A=$A; P_B=$B; P_F=$F; FIRST=0
  sleep 2
done

echo
tail -1 "$LOG"
echo
if [ -f results/off.csv ] && [ -f results/on.csv ]; then
  python3 timeline.py results/off.csv results/on.csv
else
  python3 timeline.py "results/$MODE.csv"
fi
