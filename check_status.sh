#!/bin/bash
JOB_ID=$1
if [ -z "$JOB_ID" ]; then
    echo "Usage: ./check_status.sh <job_id>"
    exit 1
fi

echo "Checking status for job: $JOB_ID"
echo "================================"
curl -s "http://localhost:8000/api/v1/process/$JOB_ID/status" | python3 -m json.tool
