import os, re, json, fnmatch, yaml
from pathlib import Path
from tqdm import tqdm
from rich import print
import subprocess, shlex

def run_yara(evidence_dir: str, profile_path: str, outdir: str):
    with open(profile_path, "r") as f:
        profile = yaml.safe_load(f) or {}
    rules_dir = profile.get("detections", {}).get("yara", {}).get("rules_dir", "/app/rules/yara")
    paths = profile.get("detections", {}).get("yara", {}).get("paths", [evidence_dir])

    out_json = os.path.join(outdir, "yara_hits.json")
    results = []

    rule_files = [str(p) for p in Path(rules_dir).rglob("*.yar")]
    if not rule_files:
        print("[yellow]No YARA rules found[/yellow]")
        with open(out_json,"w") as f: json.dump(results, f, indent=2)
        return out_json

    for root_path in paths:
        for p in tqdm(list(Path(root_path).rglob("*")), desc="yara-scan"):
            if p.is_file():
                cmd = f'yara -r {" ".join(rule_files)} "{p}"'
                pr = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if pr.stdout.strip():
                    for line in pr.stdout.strip().splitlines():
                        results.append({"match": line, "file": str(p)})

    with open(out_json,"w") as f:
        json.dump(results, f, indent=2)
    return out_json

def _load_sigma_rules(rules_dir: str):
    files = [p for p in Path(rules_dir).rglob("*.yml")]
    rules = []
    for f in files:
        try:
            data = yaml.safe_load(open(f,"r")) or {}
            if not isinstance(data, dict): continue
            title = data.get("title", f.name)
            detection = data.get("detection", {})
            condition = detection.get("condition","")
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
    for field, expected in kv.items():
        ev = _dig(event, field)
        if ev is None: return False
        if isinstance(expected, str):
            if expected.startswith("|contains "):
                needle = expected.split(" ",1)[1].lower()
                return needle in str(ev).lower()
            if "*" in expected or "?" in expected:
                return fnmatch.fnmatch(str(ev), expected)
            return str(ev) == str(expected)
        if isinstance(expected, list):
            return any(fnmatch.fnmatch(str(ev), str(item)) if ("*" in str(item) or "?" in str(item)) else str(ev)==str(item) for item in expected)
        return str(ev) == str(expected)
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
        profile = yaml.safe_load(f) or {}
    rules_dir = profile.get("detections", {}).get("sigma", {}).get("rules_dir", "/app/rules/sigma")

    out_json = os.path.join(outdir, "sigma_findings.json")
    matches = []

    rules = _load_sigma_rules(rules_dir)
    if not rules:
        with open(out_json,"w") as f: json.dump(matches, f, indent=2)
        print("[yellow]No Sigma rules found[/yellow]")
        return out_json

    if not os.path.exists(jsonl_events):
        print("[yellow]events.jsonl missing; skipping Sigma[/yellow]")
        with open(out_json,"w") as f: json.dump(matches, f, indent=2)
        return out_json

    with open(jsonl_events, "r") as f:
        for line in f:
            try:
                ev = json.loads(line)
            except Exception:
                continue
            for r in rules:
                ok = True
                for _,sel in r["selections"]:
                    if not _match_selection(ev, sel):
                        ok=False; break
                if ok:
                    matches.append({"rule": r["title"], "rule_path": r["file"], "event": ev})

    with open(out_json,"w") as f:
        json.dump(matches, f, indent=2)
    return out_json
