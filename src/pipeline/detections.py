import os, re, json, fnmatch, hashlib, yaml
from pathlib import Path
from tqdm import tqdm
from rich import print
import subprocess, shlex

def run_yara(evidence_dir: str, profile_path: str, outdir: str):
    with open(profile_path, "r") as f:
        profile = yaml.safe_load(f)
    rules_dir = profile.get("detections", {}).get("yara", {}).get("rules_dir", "/app/rules/yara")
    paths = profile.get("detections", {}).get("yara", {}).get("paths", [evidence_dir])

    out_json = os.path.join(outdir, "yara_hits.json")
    results = []

    # Compile all .yar files in rules_dir
    # Using yara CLI for simplicity
    rule_files = [str(p) for p in Path(rules_dir).rglob("*.yar")]
    if not rule_files:
        print("[yellow]No YARA rules found[/yellow]")
        with open(out_json,"w") as f: json.dump(results, f, indent=2)
        return out_json

    # Walk paths recursively, scan with yara
    for root_path in paths:
        for p in tqdm(list(Path(root_path).rglob("*")), desc="yara-scan"):
            if p.is_file():
                try:
                    cmd = f'yara -r {" ".join(rule_files)} "{p}"'
                    pr = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if pr.stdout.strip():
                        for line in pr.stdout.strip().splitlines():
                            # Format: RULE_NAME [TAG?] FILEPATH:OFFSET?  -> keep simple
                            results.append({"match": line, "file": str(p)})
                except Exception as e:
                    continue

    with open(out_json,"w") as f:
        json.dump(results, f, indent=2)
    return out_json

# Minimal Sigma engine for common equals/contains cases over JSONL events.
def _load_sigma_rules(rules_dir: str):
    files = [p for p in Path(rules_dir).rglob("*.yml")]
    rules = []
    for f in files:
        try:
            data = yaml.safe_load(open(f,"r"))
            # allow single-rule files only
            if not isinstance(data, dict): continue
            title = data.get("title", Path(f).name)
            detection = data.get("detection", {})
            condition = detection.get("condition","")
            # collect simple selections
            selections = []
            for k,v in detection.items():
                if k == "condition": continue
                if isinstance(v, dict):
                    selections.append((k, v))
            rules.append({"title": title, "file": str(f), "detection": detection, "condition": condition, "selections": selections})
        except Exception:
            continue
    return rules

def _match_selection(event: dict, kv: dict) -> bool:
    # support exact or wildcard '*' and case-insensitive contains via |contains
    for field, expected in kv.items():
        ev = _dig(event, field)
        if ev is None:
            return False
        if isinstance(expected, str):
            if expected.startswith("|contains "):
                needle = expected.split(" ",1)[1].lower()
                if needle not in str(ev).lower(): return False
            elif "*" in expected or "?" in expected:
                if not fnmatch.fnmatch(str(ev), expected): return False
            else:
                if str(ev) != str(expected): return False
        elif isinstance(expected, list):
            ok=False
            for item in expected:
                if "*" in str(item) or "?" in str(item):
                    if fnmatch.fnmatch(str(ev), str(item)): ok=True; break
                elif str(ev)==str(item):
                    ok=True; break
            if not ok: return False
        else:
            if str(ev) != str(expected): return False
    return True

def _dig(d, dotted):
    cur = d
    for part in dotted.split('|')[0].split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur

def run_sigma(jsonl_events: str, profile_path: str, outdir: str):
    with open(profile_path, "r") as f:
        profile = yaml.safe_load(f)
    rules_dir = profile.get("detections", {}).get("sigma", {}).get("rules_dir", "/app/rules/sigma")
    pipelines = profile.get("detections", {}).get("sigma", {}).get("pipelines", [])

    rules = _load_sigma_rules(rules_dir)
    out_json = os.path.join(outdir, "sigma_findings.json")
    matches = []

    if not rules:
        with open(out_json,"w") as f: json.dump(matches, f, indent=2)
        print("[yellow]No Sigma rules found[/yellow]")
        return out_json

    # Iterate JSONL
    with open(jsonl_events, "r") as f:
        for line in f:
            try:
                ev = json.loads(line)
            except Exception:
                continue
            for r in rules:
                # simple "all of selection*" semantics
                if "1 of " in r["condition"]:
                    ok=False
                    for _,sel in r["selections"]:
                        if _match_selection(ev, sel):
                            ok=True; break
                else:
                    # all selections must match
                    ok=True
                    for _,sel in r["selections"]:
                        if not _match_selection(ev, sel):
                            ok=False; break
                if ok:
                    matches.append({"rule": r["title"], "rule_path": r["file"], "event": ev})

    with open(out_json,"w") as f:
        json.dump(matches, f, indent=2)
    return out_json
