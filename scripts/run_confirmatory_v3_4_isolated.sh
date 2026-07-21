#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

gpu_uuid=GPU-474505f8-4b3d-0ba7-65de-8014425baee0
cuda_visible_device=1
port=8101
model_name=qwen2.5-14b
model_path=/home/kec23008/Models/Qwen2.5-14B-Instruct
output_root="$repo_root/outputs/confirmatory_v3.4.1"
runtime_root="$repo_root/outputs/confirmatory_v3.4.1_runtime"
lock_file=/tmp/handoffbench-v3.4-gpu-474505f8.lock
server_log="$runtime_root/qwen-vllm.log"
monitor_log="$runtime_root/gpu-monitor.tsv"
violation_file="$runtime_root/INFRASTRUCTURE_VIOLATION"

mkdir -p "$runtime_root"
exec 9>"$lock_file"
flock -n 9 || { echo "exclusive GPU lock is held: $lock_file" >&2; exit 2; }

if [[ -e "$output_root" ]]; then
  echo "sealed fresh output root already exists; v3.4 attempt cannot resume" >&2
  exit 2
fi
if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${port}$"; then
  echo "sealed port $port is already in use" >&2
  exit 2
fi
if nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader,nounits \
    | awk -F, -v uuid="$gpu_uuid" '{gsub(/ /,"",$1); if ($1==uuid) print $2}' \
    | grep -q '[0-9]'; then
  echo "sealed GPU $gpu_uuid is not idle" >&2
  exit 2
fi

: >"$server_log"
: >"$monitor_log"
rm -f "$violation_file"

CUDA_VISIBLE_DEVICES="$cuda_visible_device" setsid vllm serve "$model_path" \
  --served-model-name "$model_name" \
  --host 127.0.0.1 \
  --port "$port" \
  --gpu-memory-utilization 0.72 \
  --max-model-len 8192 \
  --max-num-seqs 8 \
  --enforce-eager \
  --generation-config vllm >"$server_log" 2>&1 &
server_pid=$!
runner_pid=
monitor_pid=

cleanup() {
  [[ -n "${monitor_pid:-}" ]] && kill "$monitor_pid" 2>/dev/null || true
  if kill -0 "$server_pid" 2>/dev/null; then
    kill -- "-$server_pid" 2>/dev/null || kill "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

healthy=0
for _ in $(seq 1 240); do
  kill -0 "$server_pid" 2>/dev/null || {
    echo "vLLM exited during startup; inspect $server_log" >&2
    exit 3
  }
  if payload=$(curl -fsS --max-time 3 "http://127.0.0.1:${port}/v1/models" 2>/dev/null) \
      && jq -e --arg model "$model_name" \
        '([.data[]?.id] | index($model)) != null' <<<"$payload" >/dev/null; then
    healthy=1
    break
  fi
  sleep 2
done
[[ "$healthy" -eq 1 ]] || { echo "vLLM did not become healthy" >&2; exit 3; }

mapfile -t allowed_gpu_pids < <(
  nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader,nounits \
    | awk -F, -v uuid="$gpu_uuid" '{gsub(/ /,"",$1); gsub(/ /,"",$2); if ($1==uuid) print $2}' \
    | sort -n -u
)
[[ "${#allowed_gpu_pids[@]}" -gt 0 ]] || {
  echo "healthy endpoint has no process on sealed GPU" >&2
  exit 3
}
allowed_csv=$(IFS=,; echo "${allowed_gpu_pids[*]}")

PYTHONPATH=src python scripts/run_confirmatory.py \
  --config configs/confirmatory_v3.4.1.yaml \
  --execute \
  --model "$model_name" \
  --base-url "$model_name=http://127.0.0.1:${port}/v1" \
  --output-dir "$output_root" \
  --workers 6 >"$runtime_root/runner.stdout.log" \
  2>"$runtime_root/runner.stderr.log" &
runner_pid=$!

monitor() {
  while kill -0 "$runner_pid" 2>/dev/null; do
    now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    mapfile -t current_gpu_pids < <(
      nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader,nounits \
        | awk -F, -v uuid="$gpu_uuid" '{gsub(/ /,"",$1); gsub(/ /,"",$2); if ($1==uuid) print $2}' \
        | sort -n -u
    )
    current_csv=$(IFS=,; echo "${current_gpu_pids[*]:-}")
    endpoint=down
    if payload=$(curl -fsS --max-time 3 "http://127.0.0.1:${port}/v1/models" 2>/dev/null) \
        && jq -e --arg model "$model_name" \
          '([.data[]?.id] | index($model)) != null' <<<"$payload" >/dev/null; then
      endpoint=ok
    fi
    printf '%s\t%s\t%s\n' "$now" "$current_csv" "$endpoint" >>"$monitor_log"
    if [[ "$endpoint" != ok || "$current_csv" != "$allowed_csv" ]]; then
      printf '%s\tallowed=%s\tobserved=%s\tendpoint=%s\n' \
        "$now" "$allowed_csv" "$current_csv" "$endpoint" >"$violation_file"
      kill "$runner_pid" 2>/dev/null || true
      return
    fi
    sleep 5
  done
}
monitor &
monitor_pid=$!

set +e
wait "$runner_pid"
runner_status=$?
set -e
wait "$monitor_pid" 2>/dev/null || true
monitor_pid=

if [[ -e "$violation_file" ]]; then
  echo "v3.4.1 infrastructure isolation violated; entire attempt is invalid" >&2
  exit 4
fi
if [[ "$runner_status" -ne 0 ]]; then
  echo "v3.4.1 runner failed; entire attempt is closed and cannot resume" >&2
  exit "$runner_status"
fi

echo "v3.4.1 Qwen full-arm execution completed; run the post-execution audit before analysis"
