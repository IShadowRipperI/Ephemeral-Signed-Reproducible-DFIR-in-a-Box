import os
import json
import time
from pathlib import Path
from typing import Any, Dict

import yaml
from rich import print

try:
    import memprocfs  # type: ignore
except Exception:
    memprocfs = None  # type: ignore


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return default


def _serialize_module(module: Any) -> Dict[str, Any]:
    return {
        "name": _safe_getattr(module, "name"),
        "fullname": _safe_getattr(module, "fullname"),
        "is_wow64": _safe_getattr(module, "is_wow64"),
        "base": _safe_getattr(module, "base"),
        "file_size": _safe_getattr(module, "file_size"),
        "image_size": _safe_getattr(module, "image_size"),
        "count_section": _safe_getattr(module, "count_section"),
        "count_eat": _safe_getattr(module, "count_eat"),
        "count_iat": _safe_getattr(module, "count_iat"),
    }


def _serialize_process(
    process: Any,
    include_modules: bool = True,
    include_handles: bool = True,
    include_threads: bool = True,
    include_unloaded_modules: bool = True,
    max_handles: int = 2000,
    max_threads: int = 2000,
) -> Dict[str, Any]:
    """Convert a process object into a JSON-serializable dict."""
    info: Dict[str, Any] = {
        "pid": _safe_getattr(process, "pid"),
        "ppid": _safe_getattr(process, "ppid"),
        "name": _safe_getattr(process, "name"),
        "fullname": _safe_getattr(process, "fullname"),
        "pathuser": _safe_getattr(process, "pathuser"),
        "pathkernel": _safe_getattr(process, "pathkernel"),
        "is_wow64": _safe_getattr(process, "is_wow64"),
        "is_usermode": _safe_getattr(process, "is_usermode"),
        "session": _safe_getattr(process, "session"),
        "sid": _safe_getattr(process, "sid"),
        "integrity": _safe_getattr(process, "integrity"),
        "cmdline": _safe_getattr(process, "cmdline"),
        "exitcode": _safe_getattr(process, "exitcode"),
        "time_create": _safe_getattr(process, "time_create"),
        "time_exit": _safe_getattr(process, "time_exit"),
        "time_create_str": _safe_getattr(process, "time_create_str"),
        "time_exit_str": _safe_getattr(process, "time_exit_str"),
    }

    if include_modules:
        modules_serialized = []
        try:
            for m in process.module_list():
                modules_serialized.append(_serialize_module(m))
        except Exception as e:
            print(
                f"[yellow]MemProcFS: failed to enumerate modules for PID {info.get('pid')}: {e}[/yellow]"
            )
        info["modules"] = modules_serialized

    if include_handles:
        try:
            handles = process.maps.handle()
            if isinstance(handles, list) and len(handles) > max_handles:
                info["handles_truncated"] = True
                handles = handles[:max_handles]
            info["handles"] = handles
        except Exception as e:
            print(
                f"[yellow]MemProcFS: failed to enumerate handles for PID {info.get('pid')}: {e}[/yellow]"
            )

    if include_threads:
        try:
            threads = process.maps.thread()
            if isinstance(threads, list) and len(threads) > max_threads:
                info["threads_truncated"] = True
                threads = threads[:max_threads]
            info["threads"] = threads
        except Exception as e:
            print(
                f"[yellow]MemProcFS: failed to enumerate threads for PID {info.get('pid')}: {e}[/yellow]"
            )

    if include_unloaded_modules:
        try:
            info["unloaded_modules"] = process.maps.unloaded_module()
        except Exception as e:
            print(
                f"[yellow]MemProcFS: failed to enumerate unloaded modules for PID {info.get('pid')}: {e}[/yellow]"
            )

    return info


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _write_jsonl(path: Path, items) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")


def _collect_process_data(vmm: Any, outdir: Path, cfg: Dict[str, Any]) -> Dict[str, str]:
    """Collect detailed per-process data (modules, handles, threads, etc.)."""
    include_modules = cfg.get("include_modules", True)
    include_handles = cfg.get("include_handles", True)
    include_threads = cfg.get("include_threads", True)
    include_unloaded = cfg.get("include_unloaded_modules", True)

    max_handles = int(cfg.get("max_handles_per_process", 2000))
    max_threads = int(cfg.get("max_threads_per_process", 2000))

    proc_jsonl = outdir / "memprocfs_processes.jsonl"
    summary_json = outdir / "memprocfs_summary.json"

    processes_serialized = []
    try:
        processes = vmm.process_list()
    except Exception as e:
        print(f"[red]MemProcFS: failed to enumerate process list: {e}[/red]")
        return {}

    for p in processes:
        proc_info = _serialize_process(
            p,
            include_modules=include_modules,
            include_handles=include_handles,
            include_threads=include_threads,
            include_unloaded_modules=include_unloaded,
            max_handles=max_handles,
            max_threads=max_threads,
        )
        processes_serialized.append(proc_info)

    _write_jsonl(proc_jsonl, processes_serialized)

    summary = {
        "process_count": len(processes_serialized),
        "pids": sorted(
            [p.get("pid") for p in processes_serialized if p.get("pid") is not None]
        ),
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _write_json(summary_json, summary)

    return {
        "processes_jsonl": str(proc_jsonl),
        "processes_summary": str(summary_json),
    }


def _collect_global_maps(vmm: Any, outdir: Path, cfg: Dict[str, Any]) -> Dict[str, str]:
    """Collect system-wide maps (net, drivers, services, users, etc.)."""
    maps_cfg = cfg.get("maps", {})
    collect_net = maps_cfg.get("net", True)
    collect_kdriver = maps_cfg.get("kdriver", True)
    collect_kdevice = maps_cfg.get("kdevice", False)
    collect_kobject = maps_cfg.get("kobject", False)
    collect_services = maps_cfg.get("services", True)
    collect_users = maps_cfg.get("users", True)

    paths: Dict[str, str] = {}

    if collect_net:
        try:
            net_info = vmm.maps.net()
            path = outdir / "memprocfs_net.json"
            _write_json(path, net_info)
            paths["net"] = str(path)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to collect net() info: {e}[/yellow]")

    if collect_kdriver:
        try:
            kdriver_info = vmm.maps.kdriver()
            path = outdir / "memprocfs_kdriver.json"
            _write_json(path, kdriver_info)
            paths["kdriver"] = str(path)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to collect kdriver() info: {e}[/yellow]")

    if collect_kdevice:
        try:
            kdevice_info = vmm.maps.kdevice()
            path = outdir / "memprocfs_kdevice.json"
            _write_json(path, kdevice_info)
            paths["kdevice"] = str(path)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to collect kdevice() info: {e}[/yellow]")

    if collect_kobject:
        try:
            kobject_info = vmm.maps.kobject()
            path = outdir / "memprocfs_kobject.json"
            _write_json(path, kobject_info)
            paths["kobject"] = str(path)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to collect kobject() info: {e}[/yellow]")

    if collect_services:
        try:
            services_info = vmm.maps.service()
            path = outdir / "memprocfs_services.json"
            _write_json(path, services_info)
            paths["services"] = str(path)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to collect service() info: {e}[/yellow]")

    if collect_users:
        try:
            users_info = vmm.maps.user()
            path = outdir / "memprocfs_users.json"
            _write_json(path, users_info)
            paths["users"] = str(path)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to collect user() info: {e}[/yellow]")

    return paths


def _copy_eventlogs(vmm: Any, dest_root: Path, max_bytes: int = 64 * 1024 * 1024) -> None:
    """
    Copy EVTX event logs from the MemProcFS VFS to dest_root.

    Uses the /misc/eventlog directory created by MemProcFS.
    """
    dest_root.mkdir(parents=True, exist_ok=True)
    try:
        entries = vmm.vfs.list("/misc/eventlog")
    except Exception as e:
        print(
            f"[yellow]MemProcFS: no /misc/eventlog tree or failed to list it: {e}[/yellow]"
        )
        return

    copied = 0
    for name, meta in entries.items():
        if meta.get("f_isdir"):
            continue
        size = int(meta.get("size", 0))
        if size <= 0:
            continue
        if size > max_bytes:
            print(
                f"[yellow]MemProcFS: skipping eventlog {name} (size {size} > {max_bytes})[/yellow]"
            )
            continue

        vpath = f"/misc/eventlog/{name}"
        try:
            data = vmm.vfs.read(vpath, size)
        except Exception as e:
            print(f"[yellow]MemProcFS: failed to read eventlog {vpath}: {e}[/yellow]")
            continue

        out_path = dest_root / name
        out_path.write_bytes(data)
        copied += 1

    if copied:
        print(
            f"[green]MemProcFS: copied {copied} EVTX files from /misc/eventlog to {dest_root}[/green]"
        )
    else:
        print("[yellow]MemProcFS: no EVTX files were copied from /misc/eventlog[/yellow]")


def _auto_discover_device(evidence_dir: str):
    """Find a likely memory image under evidence_dir by extension."""
    exts = {".raw", ".vmem", ".dmp", ".bin"}
    for root, _dirs, files in os.walk(evidence_dir):
        for name in files:
            if Path(name).suffix.lower() in exts:
                return os.path.join(root, name)
    return None


def run_memprocfs(evidence_dir: str, profile_path: str, outdir: str):
    """
    Run MemProcFS memory triage.

    Returns a metadata dict with paths to the generated JSONs and the eventlog
    directory, or None if MemProcFS is not enabled / not available.
    """
    outdir_path = Path(outdir)
    outdir_path.mkdir(parents=True, exist_ok=True)

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(
            f"[yellow]MemProcFS: profile {profile_path} not found; using defaults[/yellow]"
        )
        profile = {}
    except Exception as e:
        print(
            f"[yellow]MemProcFS: failed to load profile {profile_path}: {e}[/yellow]"
        )
        profile = {}

    mem_cfg = (profile.get("memory") or {}).get("memprocfs") or {}
    if not mem_cfg.get("enabled"):
        print("[yellow]MemProcFS: disabled in profile, skipping[/yellow]")
        return None

    if memprocfs is None:
        print("[yellow]MemProcFS: memprocfs Python package not available, skipping[/yellow]")
        return None

    device = mem_cfg.get("device") or _auto_discover_device(evidence_dir)
    if not device or not os.path.exists(device):
        print(f"MemProcFS: no memory image found (device={device!r}), skipping")
        return None

    args = ["-device", device]
    if mem_cfg.get("forensic", True):
        args += ["-forensic", "1"]

    extra_args = mem_cfg.get("extra_args", [])
    if isinstance(extra_args, list):
        args.extend(str(a) for a in extra_args)
    elif isinstance(extra_args, str) and extra_args.strip():
        args.extend(extra_args.split())

    print(f"[cyan]MemProcFS: analyzing memory image {device}[/cyan]")
    try:
        vmm = memprocfs.Vmm(args)
    except Exception as e:
        print(f"[yellow]MemProcFS: failed to initialize Vmm: {e}[/yellow]")
        return None

    meta: Dict[str, str] = {"device": device}

    # Per-process data
    try:
        proc_paths = _collect_process_data(vmm, outdir_path, mem_cfg.get("processes", {}))
        meta.update(proc_paths)
    except Exception as e:
        print(f"[yellow]MemProcFS: error while collecting per-process data: {e}[/yellow]")

    # Global maps (net, drivers, services, users, etc.)
    try:
        maps_paths = _collect_global_maps(vmm, outdir_path, mem_cfg)
        meta.update(maps_paths)
    except Exception as e:
        print(f"[yellow]MemProcFS: error while collecting global map data: {e}[/yellow]")

    # EVTX extraction to a directory Hayabusa can consume.
    try:
        max_bytes = int(mem_cfg.get("max_eventlog_bytes", 64 * 1024 * 1024))
        evtx_dir_cfg = mem_cfg.get(
            "eventlog_dir", str(outdir_path / "memprocfs_eventlogs")
        )
        evtx_dir = Path(evtx_dir_cfg)
        _copy_eventlogs(vmm, evtx_dir, max_bytes=max_bytes)
        meta["eventlogs_dir"] = str(evtx_dir)
    except Exception as e:
        print(f"[yellow]MemProcFS: error while copying EVTX files: {e}[/yellow]")

    return meta
