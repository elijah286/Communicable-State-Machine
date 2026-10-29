#!/usr/bin/env bash
set -uo pipefail
ulimit -c 0

capture() {
    ps -eo pid,ppid,stat,rss,etime,args > /out/processes-after.txt
    find /tmp /root/.local/share/natinst /root/Documents -type f \
        \( -iname '*.log' -o -iname '*lvfailure*' \) -size -10240k -print \
        2>/dev/null | while IFS= read -r path; do
            mkdir -p "/out/native-logs$(dirname "$path")"
            cp "$path" "/out/native-logs${path}" 2>/dev/null || true
        done
}
trap capture EXIT

ps -eo pid,ppid,stat,rss,etime,args > /out/processes-before.txt
printf 'MODE=%s\nDISPLAY=%s\nLV_RTE_HEADLESS=%s\n' \
    "$MODE" "${DISPLAY:-}" "${LV_RTE_HEADLESS:-}"
free -m
LabVIEWCLI -Help || true

if [[ "$MODE" == xvfb-* ]]; then
    Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp > /out/xvfb.log 2>&1 &
    export DISPLAY=:99
    sleep 2
fi

if [ "$MODE" = recovery-full ]; then
    timeout 1800 bash /diagnostic/vidiff-candidate.sh \
        /workspace-base /workspace /out/report /ops
    exit $?
fi

mkdir -p /out/report
labview_exe=$(find /usr/local/natinst -name labviewprofull | head -1)
headless=(-Headless)
if [ "$MODE" = xvfb-gui ]; then
    unset LV_RTE_HEADLESS
    headless=()
fi
timeout 180 LabVIEWCLI -OperationName CreateComparisonReport \
    -LabVIEWPath "$labview_exe" -VI1 "/workspace-base/$CHANGED_FILES" \
    -VI2 "/workspace/$CHANGED_FILES" -ReportType html \
    -ReportPath /out/report/index.html -LogToConsole TRUE "${headless[@]}"
status=$?
printf 'CLI exit=%s; HTML bytes=' "$status"
wc -c /out/report/index.html || true
exit "$status"
