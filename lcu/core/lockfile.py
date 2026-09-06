#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lockfile Detection and Parsing
Handles finding and parsing League Client lockfile
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import psutil

from utils.core.logging import get_logger

log = get_logger()

SWIFTPLAY_MODES = {"SWIFTPLAY", "BRAWL"}
SWIFTPLAY_QUEUE_ID = 480


@dataclass
class Lockfile:
    """Parsed lockfile data"""
    name: str
    pid: int
    port: int
    password: str
    protocol: str


def find_lockfile(explicit: Optional[str] = None) -> Optional[str]:
    """Find League Client lockfile using pathlib
    
    Args:
        explicit: Optional explicit path to lockfile
        
    Returns:
        Path to lockfile if found, None otherwise
    """
    # Check explicit path
    if explicit:
        explicit_path = Path(explicit)
        if explicit_path.is_file():
            return str(explicit_path)
    
    # Check environment variable
    env = os.environ.get("LCU_LOCKFILE")
    if env:
        env_path = Path(env)
        if env_path.is_file():
            return str(env_path)
    
    # Check common installation paths
    if os.name == "nt":
        common_paths = [
            Path("C:/Riot Games/League of Legends/lockfile"),
            Path("C:/Program Files/Riot Games/League of Legends/lockfile"),
            Path("C:/Program Files (x86)/Riot Games/League of Legends/lockfile"),
        ]
    else:
        common_paths = [
            Path("/Applications/League of Legends.app/Contents/LoL/lockfile"),
            Path.home() / ".local/share/League of Legends/lockfile",
        ]
    
    for p in common_paths:
        if p.is_file():
            return str(p)
    
    # Try to find via process scanning
    try:
        for proc in psutil.process_iter(attrs=["name", "exe"]):
            nm = (proc.info.get("name") or "").lower()
            if "leagueclient" in nm:
                exe = proc.info.get("exe") or ""
                if exe:
                    exe_path = Path(exe)
                    # Check in same directory and parent directory
                    for directory in [exe_path.parent, exe_path.parent.parent]:
                        lockfile = directory / "lockfile"
                        if lockfile.is_file():
                            return str(lockfile)
    except (psutil.Error, OSError, AttributeError) as e:
        log.debug(f"Failed to find lockfile via process iteration: {e}")
    
    return None


def find_lcu_credentials(processes: Optional[Iterable] = None) -> Optional[Lockfile]:
    """Build LCU credentials from a running League Client UX process.

    The WeGame client can leave its LeagueClient lockfile empty while still
    providing the standard LCU port and authentication token to
    LeagueClientUx.exe. psutil returns an already parsed command-line list,
    which avoids treating Windows argument quotes as part of the token.
    """
    if processes is None:
        try:
            processes = psutil.process_iter(attrs=["name", "pid", "cmdline"])
        except psutil.Error as e:
            log.debug(f"Failed to enumerate LCU processes: {e}")
            return None

    try:
        for proc in processes:
            info = proc.info
            if (info.get("name") or "").lower() != "leagueclientux.exe":
                continue

            arguments = info.get("cmdline") or []
            values = {}
            for argument in arguments:
                if not isinstance(argument, str) or "=" not in argument:
                    continue
                key, value = argument.split("=", 1)
                if key in {"--app-port", "--remoting-auth-token"} and value:
                    values[key] = value

            port = values.get("--app-port")
            password = values.get("--remoting-auth-token")
            if not port or not password:
                continue

            port_number = int(port)
            if not 1 <= port_number <= 65535:
                continue

            pid = info.get("pid", getattr(proc, "pid", 0))
            return Lockfile(
                name="LeagueClient",
                pid=int(pid),
                port=port_number,
                password=password,
                protocol="https",
            )
    except (psutil.Error, OSError, TypeError, ValueError, AttributeError) as e:
        log.debug(f"Failed to read LCU process credentials: {e}")

    return None


def parse_lockfile(
    lockfile_path: Optional[str], processes: Optional[Iterable] = None
) -> Optional[Lockfile]:
    """Parse lockfile and return Lockfile dataclass
    
    Args:
        lockfile_path: Path to lockfile, if available
        processes: Optional process iterable used to locate fallback credentials
        
    Returns:
        Parsed Lockfile or None if failed
    """
    if lockfile_path:
        path = Path(lockfile_path)
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                name, pid, port, pw, proto = content.split(":")[:5]
                return Lockfile(
                    name=name,
                    pid=int(pid),
                    port=int(port),
                    password=pw,
                    protocol=proto,
                )
            except (OSError, ValueError) as e:
                log.debug(f"Failed to parse lockfile: {e}")

    return find_lcu_credentials(processes)
