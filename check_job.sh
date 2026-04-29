#!/bin/bash
# Check job status
JOB_ID=$1

if [ -z "$JOB_ID" ]; then
    echo "Usage: ./check_job.sh <job_id>"
    echo "Example: ./check_job.sh 14a621c6-d84a-4d49-a37f-5121a1afbcd1"
    exit 1
fi

echo "Checking job status for: $JOB_ID"
echo "================================"

curl -s "http://localhost:8000/api/v1/process/$JOB_ID/status" | python3 -m json.tool

echo ""
echo "To see real-time logs, watch the backend terminal output"
