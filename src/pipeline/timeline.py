import os, subprocess, shlex, yaml
from rich import print

def _run(cmd, env=None, cwd=None):
    print(f"[cyan]$ {cmd}[/cyan]")
    p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=cwd)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {cmd}\n{p.stdout}")
    return p.stdout

def make_timeline(evidence_dir: str, outdir: str, profile_path: str):
    with open(profile_path, "r") as f:
        profile = yaml.safe_load(f) or {}

    plaso_file = os.path.join(outdir, "timeline.plaso")
    jsonl_file = os.path.join(outdir, "events.jsonl")
    plaso_log  = os.path.join(outdir, "plaso.log")

    parsers = None
    tcfg = profile.get("timeline", {})
    if isinstance(tcfg.get("parsers"), (str, list)):
        parsers = tcfg["parsers"] if isinstance(tcfg["parsers"], str) else ",".join(tcfg["parsers"])

    # 1) log2timeline: explicit --storage_file, single worker (stable under emulation)
    base = f"log2timeline.py --status_view=none --single_process --workers 1 --logfile {plaso_log} --storage_file {plaso_file}"
    if parsers:
        base += f" --parsers {parsers}"
    _run(f"{base} {evidence_dir}")

    # 2) psort to JSONL; guarantee the file exists even if there are 0 events
    try:
        _run(f"psort.py --status_view=none -o json_line -w {jsonl_file} {plaso_file}")
    except RuntimeError as e:
        print(f"[yellow]psort failed or produced no output; continuing[/yellow]\n{e}")
    finally:
        if not os.path.exists(jsonl_file):
            open(jsonl_file, "w").close()

    # small index note
    with open(os.path.join(outdir, "timeline.index"), "w") as f:
        f.write(plaso_file + "\n" + jsonl_file + "\n")

    return plaso_file, jsonl_file
