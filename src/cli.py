import argparse, json, os, sys, time
from rich import print
from src.pipeline import timeline, detections, report, provenance, memory, hayabusa

DEFAULT_PROFILE = os.environ.get("DFIRBOX_PROFILE", "/app/profiles/windows-triage.yml")


def cmd_run(args):
    evidence = os.path.abspath(args.evidence)
    outdir   = os.path.abspath(args.out)
    profile  = os.path.abspath(args.profile or DEFAULT_PROFILE)

    os.makedirs(outdir, exist_ok=True)
    meta = {
        "start_epoch": int(time.time()),
        "profile": profile,
        "evidence": evidence,
        "params": {"plaso": True, "sigma": True, "yara": True, "volatility": False}
    }

    # 1. timeline
    plaso_path, jsonl_path = timeline.make_timeline(evidence, outdir, profile)

    # 2. detections
    sigma_out = detections.run_sigma(jsonl_path, profile, outdir)
    yara_out  = detections.run_yara(evidence, profile, outdir)

    # 3. MemProcFS memory forensics (optional)
    memproc_out = memory.run_memprocfs(evidence, profile, outdir)
    if memproc_out:
        meta["memprocfs"] = memproc_out

    # 4. Hayabusa EVTX timeline (optional)
    hayabusa_out = hayabusa.run_hayabusa(evidence, profile, outdir)
    if hayabusa_out:
        meta["hayabusa"] = hayabusa_out

    # 5. provenance
    prov = provenance.generate(evidence, profile, outdir)

    # 6. report
    summary = report.build(
        outdir=outdir,
        jsonl_events=jsonl_path,
        sigma_path=sigma_out,
        yara_path=yara_out,
        provenance_path=prov,
        meta=meta,
    )

    print(f"[green]Done[/green]. Report: {summary}")
    return 0


def cmd_version(_):
    print(json.dumps(provenance.tool_versions(), indent=2))
    return 0


def cmd_selftest(args):
    # Very light smoke check
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "selftest.txt"), "w") as f:
        f.write("dfirbox selftest ok\n")
    print("selftest ok")
    return 0


def main():
    p = argparse.ArgumentParser(prog="dfirbox")
    sub = p.add_subparsers(dest="cmd", required=True)

    prun = sub.add_parser("run", help="Run triage pipeline")
    prun.add_argument("--profile", "-p", default=None, help="Profile YAML")
    prun.add_argument("--evidence", "-e", required=True, help="Path to evidence (dir)")
    prun.add_argument("--out", "-o", required=True, help="Output directory")
    prun.set_defaults(func=cmd_run)

    pver = sub.add_parser("version", help="Show tool versions discovered")
    pver.set_defaults(func=cmd_version)

    pst = sub.add_parser("selftest", help="Quick smoke test")
    pst.add_argument("--out", "-o", required=True)
    pst.set_defaults(func=cmd_selftest)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
