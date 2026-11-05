"""Read-only monitor for repeated Linux authentication failures.

This utility tails an existing auth log and emits JSON alerts to stdout. It does
not block IPs, change firewall rules, modify encryption keys, or contact hosts.

Examples:
    python security/auth_failure_monitor.py
    python security/auth_failure_monitor.py --log-file /var/log/secure
    python security/auth_failure_monitor.py --from-start --threshold 8 --window 300

The account running the script needs read access to the selected log file.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

# Covers common OpenSSH and PAM failure formats found in auth.log / secure.
_PATTERNS = (
    re.compile(r"Failed password for (?:invalid user )?\S+ from ([0-9a-fA-F:.]+)(?: port \d+)?", re.I),
    re.compile(r"authentication failure;.*?rhost=([0-9a-fA-F:.]+)(?:\s|$)", re.I),
    re.compile(r"Invalid user \S+ from ([0-9a-fA-F:.]+)(?:\s|$)", re.I),
)


def default_log_path() -> Path:
    for candidate in (Path("/var/log/auth.log"), Path("/var/log/secure")):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No standard Linux auth log found. Specify one with --log-file."
    )


def source_ip(line: str) -> str | None:
    """Extract a valid source IP from a known authentication-failure pattern."""
    for pattern in _PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        candidate = match.group(1).strip("[]")
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


def emit_alert(ip: str, failures: int, threshold: int, window: int) -> None:
    record = {
        "event": "repeated_authentication_failures",
        "severity": "warning",
        "source_ip": ip,
        "failures_in_window": failures,
        "threshold": threshold,
        "window_seconds": window,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "response": "alert_only",
    }
    print(json.dumps(record, ensure_ascii=False), flush=True)


def monitor(log_path: Path, threshold: int, window: int, poll: float,
            from_start: bool) -> None:
    failures: dict[str, deque[float]] = defaultdict(deque)
    alerted: set[str] = set()

    with log_path.open("r", encoding="utf-8", errors="replace") as log:
        stat = log_path.stat()
        inode = getattr(stat, "st_ino", None)
        if not from_start:
            log.seek(0, 2)

        print(json.dumps({
            "event": "monitor_started",
            "log_file": str(log_path.resolve()),
            "threshold": threshold,
            "window_seconds": window,
            "response": "alert_only",
        }), flush=True)

        while True:
            try:
                current = log_path.stat()
                current_inode = getattr(current, "st_ino", None)
                # Handle rotation/replacement and truncation without shelling out.
                if current_inode != inode or current.st_size < log.tell():
                    log.close()
                    log = log_path.open("r", encoding="utf-8", errors="replace")
                    inode = current_inode

                line = log.readline()
                if not line:
                    now = time.monotonic()
                    for ip, timestamps in list(failures.items()):
                        while timestamps and now - timestamps[0] > window:
                            timestamps.popleft()
                        if len(timestamps) < threshold:
                            alerted.discard(ip)
                        if not timestamps:
                            failures.pop(ip, None)
                    time.sleep(poll)
                    continue

                ip = source_ip(line)
                if not ip:
                    continue
                now = time.monotonic()
                timestamps = failures[ip]
                while timestamps and now - timestamps[0] > window:
                    timestamps.popleft()
                timestamps.append(now)
                if len(timestamps) >= threshold and ip not in alerted:
                    emit_alert(ip, len(timestamps), threshold, window)
                    alerted.add(ip)
            except FileNotFoundError:
                print(f"Log file disappeared: {log_path}; waiting for it to return.",
                      file=sys.stderr, flush=True)
                time.sleep(poll)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", type=Path, help="Linux auth.log/secure file")
    parser.add_argument("--threshold", type=int, default=5,
                        help="failures from one IP before alerting (default: 5)")
    parser.add_argument("--window", type=int, default=300,
                        help="sliding time window in seconds (default: 300)")
    parser.add_argument("--poll", type=float, default=1.0,
                        help="seconds between file checks (default: 1)")
    parser.add_argument("--from-start", action="store_true",
                        help="process existing log contents at startup")
    args = parser.parse_args()

    if args.threshold < 1 or args.window < 1 or args.poll <= 0:
        parser.error("threshold/window must be positive and poll must be greater than zero")
    try:
        path = args.log_file or default_log_path()
        monitor(path, args.threshold, args.window, args.poll, args.from_start)
    except (OSError, KeyboardInterrupt) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print("Monitor stopped.", file=sys.stderr)
            return 0
        print(f"Cannot monitor authentication log: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
