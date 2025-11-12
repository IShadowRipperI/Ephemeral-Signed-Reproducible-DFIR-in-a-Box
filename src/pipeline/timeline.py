import os, subprocess, shlex, tempfile, yaml
from rich import print
from pathlib import Path

def _run(cmd, env=None, cwd=None):
    print(f"[cyan]$ {cmd}[/cyan]")
    p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=cwd)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {cmd}\n{p.stdout}")
    return p.stdout

def make_timeline(evidence_dir: str, outdir: str, profile_path: str):
    # We rely on plaso to walk files. Evidence should be mounted read-only by Docker.
    with open(profile_path, "r") as f:
        profile = yaml.safe_load(f)

    plaso_file = os.path.join(outdir, "timeline.plaso")
    jsonl_file = os.path.join(outdir, "events.jsonl")

    # log2timeline
    cmd_l2t = f"log2timeline.py --status_view=linear {plaso_file} {evidence_dir}"
    _run(cmd_l2t)

    # psort to JSONL
    cmd_ps = f"psort.py -o json_line -w {jsonl_file} {plaso_file}"
    _run(cmd_ps)

    # small index note
    with open(os.path.join(outdir, "timeline.index"), "w") as f:
        f.write(plaso_file + "\n" + jsonl_file + "\n")

    return plaso_file, jsonl_file
