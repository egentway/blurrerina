#!/bin/bash

while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    time source scripts/entrypoint.sh
    code=$?
    if [ $code -ne 0 ]; then
        echo "[$timestamp] Program exited with code $code" >> /workspace/pipeline_run_errors.log
    fi
    # Optional: sleep between runs
    sleep 1
done