"""Print a pod's runtime port mapping (public ip and port for each exposed
port), which tools/runpod_api.py's `pod` view does not fetch.  Reuses its
key loading (the key is never printed) and its query function.
    uv run python pod_ports.py <pod id>        (from the repo root)"""
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
import runpod_api  # noqa: E402

Q = """{ pod(input: {podId: "%s"}) { id name desiredStatus
  runtime { uptimeInSeconds ports { ip isIpPublic privatePort publicPort type } } } }"""

pod_id = sys.argv[1]
key = runpod_api.load_key()
data = runpod_api.query(Q % pod_id, key)
p = data.get("pod") or {}
rt = p.get("runtime") or {}
print(f"{p.get('id')} ({p.get('name')}) {p.get('desiredStatus')} uptime {rt.get('uptimeInSeconds')} s")
for port in rt.get("ports") or []:
    print(f"  {port.get('type')}: {port.get('ip')}:{port.get('publicPort')} -> {port.get('privatePort')}"
          f" ({'public' if port.get('isIpPublic') else 'private'} ip)")
