"""tools/runpod_api.py on canned answers: no network, no key from .env."""
from __future__ import annotations

import io
import json
import urllib.request

import pytest

from tools import runpod_api as rp

KEY = "rpa_TESTKEY0123456789"

STOCK = {"data": {
    "dataCenters": [
        {"id": "US-KS-2", "name": "KS", "storageSupport": True, "gpuAvailability": [
            {"gpuTypeId": "NVIDIA A100 80GB PCIe", "gpuTypeDisplayName": "A100 PCIe", "stockStatus": "Low", "available": True},
            {"gpuTypeId": "NVIDIA RTX 4090", "gpuTypeDisplayName": "RTX 4090", "stockStatus": "High", "available": True},
            {"gpuTypeId": "NVIDIA H100 80GB HBM3", "gpuTypeDisplayName": "H100 SXM", "stockStatus": None, "available": False}]},
        {"id": "US-MD-1", "name": "MD", "storageSupport": False, "gpuAvailability": [
            {"gpuTypeId": "NVIDIA A100-SXM4-80GB", "gpuTypeDisplayName": "A100 SXM", "stockStatus": "Low", "available": True}]},
    ],
    "gpuTypes": [
        {"id": "NVIDIA A100-SXM4-80GB", "displayName": "A100 SXM", "memoryInGb": 80,
         "lowestPrice": {"uninterruptablePrice": 1.79, "stockStatus": "Low"}},
        {"id": "NVIDIA H100 NVL", "displayName": "H100 NVL", "memoryInGb": 94,
         "lowestPrice": {"uninterruptablePrice": None, "stockStatus": None}},
    ]}}

POD = {"data": {"pod": {
    "id": "abc123", "name": "p", "desiredStatus": "RUNNING", "gpuCount": 1, "costPerHr": 1.79,
    "imageName": "img", "env": ["PUBLIC_KEY=ssh-ed25519 AAAA x", "JUPYTER_PASSWORD=supersecret", f"LEAK={KEY}"],
    "dockerArgs": "bash -c 'x'", "containerDiskInGb": 50, "volumeMountPath": "/workspace",
    "ports": "8888/http,22/tcp", "templateId": "t", "networkVolumeId": "v",
    "machine": {"gpuDisplayName": "A100 PCIe", "dataCenterId": "US-KS-2"}, "runtime": {"uptimeInSeconds": 60}}}}


class FakeOpener:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def __call__(self, req: urllib.request.Request, timeout: float) -> bytes:
        self.requests.append(req)
        return json.dumps(self.answer).encode()


def run(argv, answer):
    fake = FakeOpener(answer)
    buf = io.StringIO()
    rc = rp.main(argv, opener=fake, key=KEY, out=buf)
    return rc, buf.getvalue(), fake


def test_stock_filters_by_gpu_and_skips_out_of_stock():
    rc, text, fake = run(["stock"], STOCK)
    assert rc == 0
    assert "A100 PCIe" in text and "US-KS-2" in text
    assert "A100 SXM" in text and "US-MD-1" in text
    assert "RTX 4090" not in text            # filtered out by the default A100/H100/H200
    assert "H100 SXM" not in text            # no stockStatus: not in stock
    assert "H100 NVL" not in text            # not in stock anywhere: left out of the price table
    req = fake.requests[0]
    assert req.full_url == rp.API_URL and req.get_method() == "POST"
    assert req.headers["Authorization"] == f"Bearer {KEY}"


def test_stock_volumes_only_and_all_types():
    _, text, _ = run(["stock", "--volumes-only"], STOCK)
    assert "US-MD-1" not in text
    _, text, _ = run(["stock", "--gpu", ""], STOCK)
    assert "RTX 4090" in text


def test_pod_shows_env_names_only_and_never_the_key():
    _, text, _ = run(["pod", "abc123"], POD)
    assert "JUPYTER_PASSWORD" in text and "supersecret" not in text
    assert KEY not in text
    assert "bash -c 'x'" in text and "50 GB" in text
    _, text, _ = run(["--json", "pod", "abc123"], POD)
    assert "supersecret" not in text and KEY not in text
    assert "JUPYTER_PASSWORD=<hidden>" in text


def test_pod_id_is_validated():
    with pytest.raises(SystemExit):
        run(["pod", 'x"} mutation {'], POD)


def test_mutations_are_refused():
    with pytest.raises(ValueError):
        rp.query('mutation { podStop(input: {podId: "x"}) { id } }', KEY, opener=FakeOpener({}))
    with pytest.raises(ValueError):
        rp.query('  Mutation Stop { podStop(input: {podId: "x"}) { id } }', KEY, opener=FakeOpener({}))


def test_api_errors_are_raised_without_the_key():
    fake = FakeOpener({"errors": [{"message": f"bad token {KEY}"}]})
    with pytest.raises(rp.RunPodAPIError) as exc:
        rp.query("{ myself { id } }", KEY, opener=fake)
    assert KEY not in str(exc.value) and "<key>" in str(exc.value)


def test_missing_key_exits_with_a_message(monkeypatch, tmp_path):
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    empty_env = tmp_path / ".env"
    empty_env.write_text("")
    with pytest.raises(SystemExit) as exc:
        rp.load_key(empty_env)
    assert "RUNPOD_API_KEY" in str(exc.value)


def test_pods_and_volumes_tables():
    pods = {"data": {"myself": {"pods": [{"id": "a1", "name": "x", "desiredStatus": "EXITED", "gpuCount": 1,
                                          "costPerHr": 1.79, "imageName": "img",
                                          "machine": {"gpuDisplayName": "A100 SXM", "dataCenterId": "US-MD-1"}}]}}}
    _, text, _ = run(["pods"], pods)
    assert "EXITED" in text and "1x A100 SXM" in text
    vols = {"data": {"myself": {"networkVolumes": [{"id": "v1", "name": "Roger_AA_1", "size": 200, "dataCenterId": "US-KS-2"}]}}}
    _, text, _ = run(["volumes"], vols)
    assert "Roger_AA_1" in text and "200" in text


def test_record_appends_a_sample_with_all_types(tmp_path):
    log = tmp_path / "stock.jsonl"
    for t in ("2026-10-22T20:00:00+00:00", "2026-10-22T20:15:00+00:00"):
        rp.record_stock(log, KEY, opener=FakeOpener(STOCK), now=t)
    lines = [json.loads(x) for x in log.read_text().splitlines()]
    assert [s["t"] for s in lines] == ["2026-10-22T20:00:00+00:00", "2026-10-22T20:15:00+00:00"]
    ks = {dc["id"]: dc for dc in lines[0]["datacenters"]}
    assert {a["gpu"] for a in ks["US-KS-2"]["in_stock"]} == {"A100 PCIe", "RTX 4090"}   # unfiltered; H100 out of stock
    assert ks["US-MD-1"]["volumes"] is False
    assert lines[0]["secure_price_hr"]["A100 SXM"] == 1.79
    assert KEY not in log.read_text()


def _sample(t, ks_types):
    return {"t": t, "datacenters": [
        {"id": "US-KS-2", "volumes": True, "in_stock": [{"gpu": g, "stock": "Low"} for g in ks_types]},
        {"id": "US-MD-1", "volumes": False, "in_stock": [{"gpu": "A100 SXM", "stock": "Medium"}]}],
        "secure_price_hr": {}}


def test_history_shares_levels_and_gaps(tmp_path):
    samples = [_sample("t0", ["A100 SXM"]), _sample("t1", []), _sample("t2", []), _sample("t3", ["A100 SXM"])]
    rows = {(r["gpu"], r["datacenter"]): r for r in rp.stock_history(samples, ["A100"], False)}
    ks = rows[("A100 SXM", "US-KS-2")]
    assert ks["in_stock"] == "2/4" and ks["share"] == 0.5 and ks["longest_gap_samples"] == 2
    md = rows[("A100 SXM", "US-MD-1")]
    assert md["share"] == 1.0 and md["levels"] == "Medium 4" and md["volumes"] is False
    only_vol = rp.stock_history(samples, ["A100"], True)
    assert {r["datacenter"] for r in only_vol} == {"US-KS-2"}
    log = tmp_path / "log.jsonl"
    log.write_text("\n".join(json.dumps(s) for s in samples) + "\n")
    buf = io.StringIO()
    assert rp.main(["history", "--log", str(log), "--gpu", "A100"], key="unused", out=buf) == 0
    assert "4 samples" in buf.getvalue() and "2/4" in buf.getvalue()
    assert "By GPU count: no sample records it" in buf.getvalue()


# ---------------------------------------------------------------------------
# Pods of 1, 2 and 4 GPUs (2026-10-28)
# ---------------------------------------------------------------------------

import re  # noqa: E402

LISTING = {"data": {
    "dataCenters": [{"id": "US-KS-2", "name": "KS", "storageSupport": True, "gpuAvailability": []},
                    {"id": "EU-RO-1", "name": "RO", "storageSupport": False, "gpuAvailability": []}],
    "gpuTypes": [
        {"id": "NVIDIA A100-SXM4-80GB", "displayName": "A100 SXM", "memoryInGb": 80,
         "lowestPrice": {"uninterruptablePrice": 1.79, "stockStatus": "Low"}},
        {"id": "NVIDIA H100 80GB HBM3", "displayName": "H100 SXM", "memoryInGb": 80,
         "lowestPrice": {"uninterruptablePrice": 2.99, "stockStatus": "High"}},
        {"id": "NVIDIA GeForce RTX 4090", "displayName": "RTX 4090", "memoryInGb": 24,
         "lowestPrice": {"uninterruptablePrice": 0.69, "stockStatus": "High"}}]}}

# (type id, datacenter, count) -> stockStatus; anything absent answers null.
BY_COUNT = {("NVIDIA A100-SXM4-80GB", "US-KS-2", 1): "Low",
            ("NVIDIA A100-SXM4-80GB", "US-KS-2", 2): "Low",
            ("NVIDIA H100 80GB HBM3", "US-KS-2", 1): "High",
            ("NVIDIA H100 80GB HBM3", "US-KS-2", 2): "Medium",
            ("NVIDIA H100 80GB HBM3", "US-KS-2", 4): "Low",
            ("NVIDIA H100 80GB HBM3", "EU-RO-1", 4): "Low"}

_ALIAS = re.compile(r'(a\d+): lowestPrice\(input: \{gpuCount: (\d+), secureCloud: true, '
                    r'dataCenterId: "([^"]+)"\}\) \{ stockStatus uninterruptablePrice \}')


class RoutingOpener:
    """The listing for the stock query; for a per-type query, each alias
    answered from ``stock`` (or an error for the types in ``fail``)."""

    def __init__(self, stock=BY_COUNT, fail=()):
        self.stock, self.fail, self.queries = stock, set(fail), []

    def __call__(self, req, timeout):
        q = json.loads(req.data)["query"]
        self.queries.append(q)
        m = re.search(r"gpuTypes\(input: \{id: (\"[^\"]*\")\}\)", q)
        if not m:
            return json.dumps(LISTING).encode()
        gid = json.loads(m.group(1))
        if gid in self.fail:
            return json.dumps({"errors": [{"message": f"boom {KEY}"}]}).encode()
        got = {"id": gid}
        for a, n, dc in _ALIAS.findall(q):
            st = self.stock.get((gid, dc, int(n)))
            got[a] = {"stockStatus": st, "uninterruptablePrice": 1.0 if st else None}
        return json.dumps({"data": {"gpuTypes": [got]}}).encode()


def test_count_query_aliases_every_datacenter_and_count():
    q, aliases = rp.count_query('A100 "SXM"', ["US-KS-2", 'bad"}id', "EU-RO-1"])
    assert q.startswith('{ gpuTypes(input: {id: "A100 \\"SXM\\""})')
    assert sorted(aliases.values()) == sorted((dc, n) for dc in ("US-KS-2", "EU-RO-1")
                                              for n in (1, 2, 4))
    assert len(_ALIAS.findall(q)) == 6 and "bad" not in q     # an odd id is left out


def test_stock_shows_pods_of_1_2_and_4_gpus():
    fake = RoutingOpener()
    buf = io.StringIO()
    assert rp.main(["stock"], opener=fake, key=KEY, out=buf) == 0
    text = buf.getvalue()
    # one listing request, then one per kept type (A100 SXM, H100 SXM; not the RTX)
    per_type = [q for q in fake.queries if "gpuTypes(input:" in q]
    assert len(fake.queries) == 3 and len(per_type) == 2
    assert not any("RTX" in q for q in per_type)
    assert all(len(_ALIAS.findall(q)) == 6 for q in per_type)
    assert "pods of 1x, 2x, 4x GPUs" in text and "2 GPU types asked" in text
    by_dc = {tuple(line.split()[:3]): line.split()[3:] for line in text.splitlines()
             if line.startswith(("A100 SXM", "H100 SXM")) and "-" in line}
    assert by_dc[("H100", "SXM", "US-KS-2")] == ["True", "High", "Medium", "Low"]
    assert by_dc[("A100", "SXM", "US-KS-2")] == ["True", "Low", "Low"]      # no 4x: blank
    assert by_dc[("H100", "SXM", "EU-RO-1")] == ["False", "Low"]           # 4x only
    assert KEY not in text
    _, text2, _ = run(["stock", "--volumes-only"], LISTING)
    assert "EU-RO-1" not in text2


def test_record_and_history_by_count(tmp_path):
    log = tmp_path / "stock.jsonl"
    old = _sample("2026-10-22T20:00:00+00:00", ["A100 SXM"])           # the 1x-only form
    log.write_text(json.dumps(old) + "\n")
    rp.record_stock(log, KEY, opener=RoutingOpener(), now="2026-10-28T20:00:00+00:00")
    gone = dict(BY_COUNT)
    del gone[("NVIDIA H100 80GB HBM3", "US-KS-2", 4)]
    rp.record_stock(log, KEY, opener=RoutingOpener(gone), now="2026-10-28T20:15:00+00:00")
    rp.record_stock(log, KEY, opener=RoutingOpener(fail={"NVIDIA H100 80GB HBM3"}),
                    now="2026-10-28T20:30:00+00:00")
    samples = [json.loads(x) for x in log.read_text().splitlines()]
    bc = samples[1]["by_count"]
    assert bc["counts"] == [1, 2, 4] and bc["gpus"] == ["A100 SXM", "H100 SXM"]
    assert bc["datacenters"] == ["US-KS-2", "EU-RO-1"] and bc["errors"] == []
    assert {(e["gpu"], e["datacenter"], e["count"]) for e in bc["in_stock"]} == {
        ("A100 SXM", "US-KS-2", 1), ("A100 SXM", "US-KS-2", 2), ("H100 SXM", "US-KS-2", 1),
        ("H100 SXM", "US-KS-2", 2), ("H100 SXM", "US-KS-2", 4), ("H100 SXM", "EU-RO-1", 4)}
    # a type whose request failed: under errors, not asked, and never the key
    failed = samples[3]["by_count"]
    assert failed["gpus"] == ["A100 SXM"] and failed["errors"][0]["gpu"] == "H100 SXM"
    assert KEY not in log.read_text()

    rows = {(r["gpu"], r["datacenter"], r["count"]): r
            for r in rp.stock_history_by_count(samples, ["H100", "A100"], False)}
    h4 = rows[("H100 SXM", "US-KS-2", "4x")]
    assert h4["in_stock"] == "1/2" and h4["share"] == 0.5 and h4["longest_gap_samples"] == 1
    assert rows[("H100 SXM", "EU-RO-1", "4x")]["in_stock"] == "2/2"
    assert rows[("A100 SXM", "US-KS-2", "2x")]["in_stock"] == "3/3"
    assert ("A100 SXM", "US-KS-2", "4x") not in rows                 # never in stock
    vol = rp.stock_history_by_count(samples, ["H100"], True)
    assert {r["datacenter"] for r in vol} == {"US-KS-2"}

    buf = io.StringIO()
    assert rp.main(["history", "--log", str(log), "--gpu", "H100"], key="unused", out=buf) == 0
    text = buf.getvalue()
    assert "4 samples" in text and "3 of 4 samples record it" in text and "1/2" in text


def test_record_cli_reports_the_counts(tmp_path):
    buf = io.StringIO()
    log = tmp_path / "s.jsonl"
    assert rp.main(["record", "--log", str(log), "--gpu", "H100"], opener=RoutingOpener(),
                   key=KEY, out=buf) == 0
    assert "4 (datacenter, type, count) of 1 types asked at 1x/2x/4x" in buf.getvalue()
    assert json.loads(log.read_text())["by_count"]["gpus"] == ["H100 SXM"]
