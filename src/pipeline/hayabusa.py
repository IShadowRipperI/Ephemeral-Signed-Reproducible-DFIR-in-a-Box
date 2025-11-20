import json
import os
import shlex
import subprocess
from typing import Dict, Optional

import yaml
from rich import print


def _run(cmd_list, *, cwd: Optional[str] = None) -> str:
    """Run a command list with logging, return combined stdout/stderr text."""
    cmd_str = " ".join(shlex.quote(c) for c in cmd_list)
    if cwd:
        print(f"[cyan]Hayabusa: running (cwd={cwd}) {cmd_str}[/cyan]")
    else:
        print(f"[cyan]Hayabusa: running {cmd_str}[/cyan]")

    proc = subprocess.run(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        cwd=cwd,
    )
    output = proc.stdout or ""

    if proc.returncode != 0:
        print(f"[yellow]Hayabusa: command exited with code {proc.returncode}[/yellow]")

    if output.strip():
        # Show only the first few lines so we don't spam the console
        lines = output.splitlines()
        preview = "\n".join(lines[:10])
        print("Hayabusa output (truncated):")
        print("  " + "\n  ".join(preview.splitlines()))

    return output


def run_hayabusa(evidence_dir: str, profile_path: str, outdir: str) -> Optional[Dict[str, str]]:
    """
    Run Hayabusa json-timeline.

    Prefers EVTX extracted from MemProcFS (memprocfs_eventlogs) if present,
    otherwise falls back to the EVTX directories configured in the profile
    or the evidence directory.
    """
    with open(profile_path, "r") as f:
        profile = yaml.safe_load(f) or {}

    tl_cfg = profile.get("timeline") or {}
    cfg = (tl_cfg.get("hayabusa") or {})
    if not cfg.get("enabled"):
        print("[yellow]Hayabusa: disabled in profile, skipping[/yellow]")
        return None

    # Prefer MemProcFS-extracted EVTX if MemProcFS ran.
    mem_cfg = (profile.get("memory") or {}).get("memprocfs") or {}
    mem_evtx_dir = mem_cfg.get("eventlog_dir") or os.path.join(outdir, "memprocfs_eventlogs")

    target_dir: Optional[str] = None

    if os.path.isdir(mem_evtx_dir):
        evtx_files = [
            name
            for name in os.listdir(mem_evtx_dir)
            if name.lower().endswith(".evtx")
        ]
        if evtx_files:
            print(f"[cyan]Hayabusa: using MemProcFS-extracted EVTX at {mem_evtx_dir}[/cyan]")
            target_dir = mem_evtx_dir

    # Fallback to configured EVTX dirs or evidence dir.
    if target_dir is None:
        evtx_dirs = cfg.get("evtx_dirs") or [evidence_dir]
        existing_dirs = [d for d in evtx_dirs if os.path.isdir(d)]
        if not existing_dirs:
            print("[yellow]Hayabusa: no EVTX directories found, skipping[/yellow]")
            return None
        target_dir = existing_dirs[0]
        print(f"[cyan]Hayabusa: using EVTX directory {target_dir}[/cyan]")

    hayabusa_outdir = os.path.join(outdir, "hayabusa_out")
    os.makedirs(hayabusa_outdir, exist_ok=True)
    timeline_path = os.path.join(hayabusa_outdir, "hayabusa_timeline.jsonl")

    cmd = ["hayabusa", "json-timeline", "-w", "-L", "-o", timeline_path, "-d", target_dir]
    min_level = cfg.get("min_level")
    if min_level:
        cmd += ["--min-level", str(min_level)]
    for extra in (cfg.get("extra_args") or []):
        cmd.append(str(extra))

    # IMPORTANT FIX:
    # Run Hayabusa from its own directory so it can find its rules/config
    # (encoded_rules.yml / rules_config_files.txt or rules/config/*).
    hayabusa_home = os.environ.get("HAYABUSA_HOME", "/opt/hayabusa")

    try:
        _run(cmd, cwd=hayabusa_home)
    except FileNotFoundError:
        print("[yellow]Hayabusa: 'hayabusa' binary not found in PATH, skipping[/yellow]")
        return None
    except Exception as e:
        print(f"[yellow]Hayabusa: failed to run, skipping. Error: {e}[/yellow]")
        return None

    # Summarize the JSONL timeline.
    total_events = 0
    levels: Dict[str, int] = {}
    try:
        with open(timeline_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total_events += 1
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                level = ev.get("level") or ev.get("lvl") or "unknown"
                levels[level] = levels.get(level, 0) + 1
    except FileNotFoundError:
        print(f"[yellow]Hayabusa: timeline file not found at {timeline_path}[/yellow]")
    except Exception as e:
        print(f"[yellow]Hayabusa: failed summarizing JSONL: {e}[/yellow]")

    summary_path = os.path.join(hayabusa_outdir, "hayabusa_summary.json")
    try:
        with open(summary_path, "w") as f:
            json.dump(
                {
                    "total_events": total_events,
                    "hits_by_level": levels,
                    "source_dir": target_dir,
                },
                f,
                indent=2,
            )
    except Exception as e:
        print(f"[yellow]Hayabusa: failed writing summary JSON: {e}[/yellow]")

    print(f"[green]Hayabusa: wrote[/green] {timeline_path} and {summary_path}")
    return {"timeline": timeline_path, "summary": summary_path, "source_dir": target_dir}
