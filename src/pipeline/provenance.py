import os, json, subprocess, shlex, hashlib, time
from pathlib import Path
from rich import print
import yaml

def _run(cmd):
    p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        return None
    return p.stdout.strip()

def _hash_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _hash_tree(root):
    root=Path(root)
    digests=[]
    for p in root.rglob("*"):
        if p.is_file():
            try:
                digests.append(_hash_file(p))
            except Exception:
                continue
    m=hashlib.sha256()
    for d in sorted(digests):
        m.update(d.encode())
    return m.hexdigest(), len(digests)

def tool_versions():
    vers = {
        "plaso": _run("log2timeline.py --version"),
        "psort": _run("psort.py --version"),
        "yara": _run("yara --version"),
        "python": _run("python3 --version"),
        "syft": _run("syft version") if shutil_which("syft") else None,
    }
    try:
        import yara as _y
        vers["yara_python"] = getattr(_y, "__version__", "unknown")
    except Exception:
        vers["yara_python"] = None
    return vers

def shutil_which(cmd):
    from shutil import which
    return which(cmd) is not None

def generate(evidence, profile, outdir):
    ev_hash, ev_files = _hash_tree(evidence)
    # hash rules and profile
    prof_hash = _hash_file(profile) if os.path.isfile(profile) else None
    rules_dir = "/app/rules"
    rules_hash, rules_files = _hash_tree(rules_dir)

    prov = {
        "schema": "dfirbox-provenance-0.1",
        "timestamp": int(time.time()),
        "host": {"container": True},
        "inputs": {"evidence_path": evidence, "evidence_tree_sha256": ev_hash, "file_count": ev_files, "profile": profile, "profile_sha256": prof_hash},
        "environment": {"user": os.getenv("USER","runner")},
        "tool_versions": tool_versions(),
        "rules": {"dir": rules_dir, "sha256_tree": rules_hash, "file_count": rules_files},
        "outputs": {
            "plaso": "timeline.plaso",
            "events_jsonl": "events.jsonl",
            "sigma_findings": "sigma_findings.json",
            "yara_hits": "yara_hits.json",
        }
    }

    out_json = os.path.join(outdir, "provenance.json")
    with open(out_json,"w") as f:
        json.dump(prov, f, indent=2)

    # Optional SBOM of runtime filesystem, if syft exists
    if shutil_which("syft"):
        sbom_path = os.path.join(outdir, "sbom.syft.json")
        # Use filesystem mode for container root
        cmd = f"syft dir:/ -o json --exclude /evidence --exclude /out --exclude /proc --exclude /sys --exclude /dev"
        out = _run(cmd)
        if out:
            with open(sbom_path,"w") as f: f.write(out)

    return out_json
