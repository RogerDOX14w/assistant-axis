"""Stop a pod (the console's Stop Pod: the container disk is erased, the
network volume kept, billing stops) and print its status after.  Reuses
tools/runpod_api.py's key loading (the key is never printed) and query.
    uv run python pod_stop.py <pod id>        (from the repo root)"""
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
import runpod_api  # noqa: E402

pod_id = sys.argv[1]
key = runpod_api.load_key()
before = runpod_api.query('{ pod(input: {podId: "%s"}) { id name desiredStatus } }' % pod_id, key).get("pod") or {}
print("before:", before)
out = runpod_api.query('mutation { podStop(input: {podId: "%s"}) { id desiredStatus } }' % pod_id, key)
print("podStop:", out.get("podStop"))
after = runpod_api.query('{ pod(input: {podId: "%s"}) { id name desiredStatus runtime { uptimeInSeconds } } }' % pod_id, key).get("pod") or {}
print("after:", after)
