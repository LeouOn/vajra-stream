"""Execute every observe-only tool and require it to be side-effect free.

This is a tripwire for an accidental write by the 22 audited read-only tools
through the normal Python APIs (``open``, ``pathlib``, ``os``, ``shutil``,
``sqlite3``). It is not a filesystem sandbox. The tools are our own audited
code, not an adversary.

The name-level allowlist test cannot see a read path that writes a file,
opens a database, or dials the network. This one calls each name in
``READ_ONLY_TOOL_NAMES`` inside a fresh interpreter whose working directory
is the scratch workspace under ``/tmp``. It fails when a tool call changes
that workspace, changes HOME, touches the network, pulls in audio or
hardware, connects to a live repo database, or writes outside the scratch
workspace.

The workspace check snapshots every relative path's size, mtime, and content
hash before and after each tool call. ``report.json`` at the workspace root
is the only ignored path: ``_run_child`` writes that harness report after the
loop. The snapshot sees a file that is still different when the call returns.
It does not see a write that is created and removed again inside that window,
and it does not see changes outside the workspace.

Reads of the repository (source and the knowledge corpora) are the read-only
work and are not writes. The only allowed write root is that scratch
workspace: HOME, TMPDIR, the XDG directories, the scratch database, and the
result report all live under it. The one path outside it that the interpreter
itself opens for write is ``/dev/null``: ``subprocess`` opens it read/write to
discard a child's standard streams, and importing ``sounddevice`` does that
while it looks up its library. Bytecode is off
(``PYTHONDONTWRITEBYTECODE=1`` and ``sys.dont_write_bytecode``) so the process
does not need a cache directory.

The audit hook watches in-process write ``open``s, ``os.mkdir``,
``os.rename``, ``os.replace``, ``os.remove``, ``os.rmdir``, ``os.link``,
``os.symlink``, ``os.truncate``, ``os.utime``, ``os.chmod``, ``os.chown``,
``shutil.*``, and ``sqlite3.connect``. For ``os.link`` and ``os.symlink``,
either operand outside the workspace is a violation. A ``dir_fd`` carried by
those ``os`` events is resolved through ``/proc/self/fd`` and must point
inside the workspace; relative operands are joined to that directory. Integer
``mode`` and ``flags`` values are not directory descriptors. Recursion state
is per thread, so one thread parked inside the hook does not hide another
thread's watched events.

The hook does not see a write through a file descriptor opened before the
hook was installed, because CPython emits no matching ``open`` event. It does
not see writes by subprocess descendants; the process guard only rejects
player commands. It does not see native-extension writes, database drivers
other than ``sqlite3``, or mount and alias tricks this file does not
exercise. The ``open`` event does not carry ``dir_fd``, so ``os.open``
relative to a directory descriptor is not attributed to that directory. A
short-lived thread that mutates nothing the watched events name can still
appear and disappear between the thread snapshots.

A read-only name with no entry in ``_TOOL_ARGS`` fails on purpose, so a newly
allowed tool cannot pass without being exercised.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

# The effects child re-executes this file. Disable bytecode before pytest or
# any later import can write a cache. The parent also exports
# PYTHONDONTWRITEBYTECODE=1, so the interpreter starts with caching off.
if os.environ.get("VAJRA_OBSERVE_EFFECTS_CHILD") == "1":
    sys.dont_write_bytecode = True

import pytest

_PROVIDER_KEY_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "ELEVENLABS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ZAI_API_KEY",
    "Z_AI_API_KEY",
    "MINIMAX_API_KEY",
    "AZURE_SPEECH_KEY",
)

# Explicit arguments for every tool this file is willing to execute.
# Names that are acting stay here so moving one back onto the allowlist
# runs it instead of skipping it. Keyword-only container args are omitted
# so the handler takes the global container, which is the production path.
_TOOL_ARGS: dict[str, dict[str, object]] = {
    "calculate_natal_chart": {
        "birth_date": "1990-01-01T00:00:00",
        "latitude": 37.7749,
        "longitude": -122.4194,
    },
    "cast_geomancy": {"question": "trend"},
    "cast_i_ching": {"question": "trend"},
    "cast_tarot_spread": {"count": 1, "question": "trend"},
    "check_auspicious_timing": {"genre": "healing"},
    "check_saka_dawa": {},
    "find_balancing_rates": {"subject": "water", "num_rates": 1},
    "generate_character": {},
    "get_88_buddhas_liturgy": {},
    "get_all_genre_windows": {},
    "get_auspicious_timing_details": {"latitude": 37.7749, "longitude": -122.4194},
    "get_automation_stats": {"session_id": "missing-session"},
    "get_automation_status": {"session_id": "missing-session"},
    "get_available_intentions": {},
    "get_blessing_traditions": {},
    "get_buddha_recitation_status": {},
    "get_celestial_night_sky": {"latitude": 37.7749, "longitude": -122.4194},
    "get_chakra_info": {},
    "get_current_conditions": {},
    "get_current_slide": {"session_id": "missing-session"},
    "get_dharani_text": {"dharani_id_or_name": "list"},
    "get_healing_modalities": {},
    "get_journey_status": {},
    "get_meridian_info": {},
    "get_narrative_loop_status": {},
    "get_planetary_hours_and_transits": {},
    "get_planetary_positions": {},
    "get_population_statistics": {},
    "get_ritual_schedule": {"hours": 1},
    "get_ritual_status": {},
    "get_rng_reading": {"session_id": "missing-session"},
    "get_rng_summary": {"session_id": "missing-session"},
    "get_sacred_frequencies": {},
    "get_system_status": {},
    "list_narrative_characters": {},
    "list_narrative_locations": {},
    "list_populations": {},
    "list_practices": {},
    "measure_general_vitality": {"subject": "water", "samples": 1},
    "search_grimoire_correspondences": {"query": "rose"},
    "search_knowledge": {"query": "water", "top_k": 1},
    "search_rate_database": {"query": "water"},
    "text_to_rate": {"text": "water", "num_dials": 1},
}

# The legacy adapter's sync-to-async bridge. Acceptable only when a tool
# calls it; the report names that tool. Any other new thread fails.
_LEGACY_ADAPTER_THREAD = "llm-legacy-adapter-bg-loop"

_AUDIO_MODULE_ROOTS = frozenset(
    {
        "alsaaudio",
        "evdev",
        "hid",
        "portaudio",
        "pulsectl",
        "pyaudio",
        "pygame",
        "serial",
        "sounddevice",
        "soundfile",
    }
)

_PLAYER_MARKERS = ("aplay", "afplay", "paplay", "ffplay", "speaker-test")

# The alarms name a stuck import or a stuck tool. They sit well above a cold
# import of this package on a loaded 2-core runner, and the parent bound is
# still finite: one stuck call fails at _TOOL_ALARM_S with that tool's name,
# and a child that never returns fails at _CHILD_TIMEOUT_S.
_CHILD_TIMEOUT_S = 150
_TOOL_ALARM_S = 30
_IMPORT_ALARM_S = 90

# Copied into the child only when the parent actually has them. Everything
# else the parent inherited (provider switches, VAJRA_*, XDG_*, TMPDIR,
# coverage, pytest) stays out. Provider keys are set to "" below so an
# absent variable cannot reload a real key from .env.
_LOCALE_VARS = (
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LC_MESSAGES",
    "LC_NUMERIC",
    "LC_TIME",
    "LANGUAGE",
)


# `_run_child` writes this at the workspace root after the tool loop. Tool
# snapshots ignore that relative path and no other path.
_HARNESS_REPORT_FILES = frozenset({"report.json"})

# Path index, then dir_fd index. None means that operand has no dir_fd.
# -1 in the event means the caller omitted the descriptor. Measured on
# CPython 3.13: mkdir/chmod carry dir_fd at index 2, remove/rmdir at 1,
# rename/link carry src_dir_fd and dst_dir_fd, symlink's dir_fd applies to
# the destination, utime's is index 3, chown's is index 3, truncate has none.
# os.replace is delivered as os.rename here and is listed in case it is not.
_MUTATION_OPERANDS: dict[str, tuple[tuple[int, int | None], ...]] = {
    "os.mkdir": ((0, 2),),
    "os.rmdir": ((0, 1),),
    "os.remove": ((0, 1),),
    "os.rename": ((0, 2), (1, 3)),
    "os.replace": ((0, 2), (1, 3)),
    "os.link": ((0, 2), (1, 3)),
    "os.symlink": ((0, None), (1, 2)),
    "os.truncate": ((0, None),),
    "os.utime": ((0, 3),),
    "os.chmod": ((0, 2),),
    "os.chown": ((0, 3),),
}


def _snapshot(
    root: pathlib.Path,
    ignore: frozenset[str] | None = None,
) -> dict[str, tuple[str, int | None, int | None, str | None]]:
    """Relative path to kind, size, mtime_ns, and content hash.

    Symlinks are recorded from ``lstat`` and are not followed. ``ignore``
    names harness files relative to ``root``.
    """
    found: dict[str, tuple[str, int | None, int | None, str | None]] = {}
    if not root.exists():
        return found
    skipped = ignore or frozenset()
    for dirpath, dirnames, filenames in os.walk(root):
        current = pathlib.Path(dirpath)
        for name in dirnames:
            path = current / name
            rel = path.relative_to(root).as_posix()
            if rel in skipped:
                continue
            file_stat = path.lstat()
            if stat.S_ISLNK(file_stat.st_mode):
                found[rel] = ("other", file_stat.st_size, file_stat.st_mtime_ns, None)
            else:
                found[rel] = ("dir", None, file_stat.st_mtime_ns, None)
        for name in filenames:
            path = current / name
            rel = path.relative_to(root).as_posix()
            if rel in skipped:
                continue
            file_stat = path.lstat()
            if stat.S_ISREG(file_stat.st_mode) and not stat.S_ISLNK(file_stat.st_mode):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                found[rel] = ("file", file_stat.st_size, file_stat.st_mtime_ns, digest)
            else:
                found[rel] = ("other", file_stat.st_size, file_stat.st_mtime_ns, None)
    return found


def _remember_delta(
    label: str,
    before: dict[str, tuple[str, int | None, int | None, str | None]],
    after: dict[str, tuple[str, int | None, int | None, str | None]],
    created: list[str],
    modified: list[str],
    deleted: list[str],
) -> None:
    for rel in sorted(set(after) - set(before)):
        created.append(f"{label}: {rel}")
    for rel in sorted(set(before) - set(after)):
        deleted.append(f"{label}: {rel}")
    for rel in sorted(set(before) & set(after)):
        if before[rel] != after[rel]:
            modified.append(f"{label}: {rel}")


class _CallBound(BaseException):
    """Raised by SIGALRM. A tool's ``except Exception`` cannot swallow it."""


def _child_main() -> None:
    """Run in the fresh interpreter. Patches land before any project import.

    Every exit prints the JSON report and calls ``os._exit(0)``. A normal
    return would wait for non-daemon threads, and that wait is the hang.
    """
    sys.dont_write_bytecode = True
    import hashlib
    import inspect
    import json
    import pathlib
    import socket
    import sqlite3
    import subprocess
    import threading
    import time
    import traceback
    import urllib.parse
    import urllib.request

    child_started = time.monotonic()
    result_path = pathlib.Path(os.environ["VAJRA_OBSERVE_EFFECTS_RESULT"])

    def _emit_and_exit(payload: dict[str, object]) -> None:
        text = json.dumps(payload, sort_keys=True)
        try:
            result_path.write_text(text, encoding="utf-8")
        except OSError:
            pass
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        try:
            sys.stderr.flush()
        except Exception:  # noqa: BLE001 - flushing must not keep the child alive
            pass
        os._exit(0)

    def _raise_bound(_signum: int, _frame: object) -> None:
        raise _CallBound("bounded wait exceeded")

    home = pathlib.Path(os.environ["HOME"]).resolve()
    workspace_text = os.environ.get("VAJRA_OBSERVE_EFFECTS_WORK", "")
    workspace = pathlib.Path(workspace_text).resolve() if workspace_text else None
    hook_probe = os.environ.get("VAJRA_OBSERVE_EFFECTS_HOOK_PROBE", "")
    # The tool run stays under /tmp. A hook probe's fixtures live in pytest's
    # tmp_path, which follows TMPDIR and may be /var/tmp.
    if hook_probe:
        if workspace is None or not workspace.is_dir():
            _emit_and_exit({"import_error": "hook probe requires an existing scratch workspace"})
    elif not str(home).startswith("/tmp/") or workspace is None or not str(workspace).startswith("/tmp/"):
        _emit_and_exit({"import_error": "refusing to run the effects child outside /tmp"})
    assert workspace is not None
    if home != workspace and not str(home).startswith(str(workspace) + os.sep):
        _emit_and_exit({"import_error": "refusing to run the effects child when HOME is outside the scratch workspace"})
    db_path = pathlib.Path(os.environ["VAJRA_OBSERVE_EFFECTS_DB"]).resolve()
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    # The child is a script, so sys.path[0] is tests/unit. The app imports
    # `container` from the repo root, which pytest puts on the path and this
    # process otherwise would not.
    sys.path.insert(0, str(repo_root))
    if hook_probe:
        # The probe's protected database is the disposable fixture only.
        live_dbs = set()
        fixture_text = os.environ.get("VAJRA_OBSERVE_EFFECTS_LIVE_FIXTURE", "")
        if fixture_text:
            live_dbs.add(pathlib.Path(fixture_text).resolve())
    else:
        live_dbs = {
            (repo_root / "vajra_stream.db").resolve(),
            (repo_root / "backend" / "app" / "vajra_stream.db").resolve(),
        }

    for key in _PROVIDER_KEY_VARS:
        # Empty, not deleted: pydantic-settings reads the process environment
        # ahead of .env, so an absent variable would reload the real key.
        os.environ[key] = ""
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    os.environ.pop("VAJRA_TEST_AUDIO", None)

    def _patched_home(cls: type[pathlib.Path]) -> pathlib.Path:
        return home

    pathlib.Path.home = classmethod(_patched_home)  # type: ignore[method-assign]

    network: list[dict[str, str]] = []

    def _note(kind: str, detail: object) -> None:
        network.append({"kind": kind, "detail": repr(detail)[:300]})

    def _blocked_connect(self: socket.socket, address: object) -> None:
        _note("socket.connect", address)
        raise OSError("network blocked")

    def _blocked_connect_ex(self: socket.socket, address: object) -> int:
        _note("socket.connect_ex", address)
        return 101

    def _blocked_create_connection(*args: object, **kwargs: object) -> socket.socket:
        _note("socket.create_connection", args[0] if args else kwargs)
        raise OSError("network blocked")

    def _blocked_getaddrinfo(*args: object, **kwargs: object) -> list:
        _note("socket.getaddrinfo", args[0] if args else kwargs)
        raise OSError("network blocked")

    def _blocked_urlopen(*args: object, **kwargs: object) -> object:
        target = args[0] if args else kwargs.get("url")
        url = getattr(target, "full_url", None) or target
        _note("urllib.request.urlopen", url)
        raise OSError("network blocked")

    socket.socket.connect = _blocked_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked_connect_ex  # type: ignore[method-assign]
    socket.create_connection = _blocked_create_connection  # type: ignore[assignment]
    socket.getaddrinfo = _blocked_getaddrinfo  # type: ignore[assignment]
    urllib.request.urlopen = _blocked_urlopen  # type: ignore[assignment]

    # connect/urlopen above raise before any wait. This cap is the backstop
    # for a socket that bypasses those wrappers: None means block forever,
    # and a long timeout is the same hang when the peer never answers.
    # Restoring None, or any timeout above 50ms, is pinned back to 1ms.
    _real_settimeout = socket.socket.settimeout
    _real_setdefaulttimeout = socket.setdefaulttimeout

    def _immediate_timeout(timeout: object) -> float:
        if isinstance(timeout, int | float) and 0 <= timeout <= 0.05:
            return float(timeout)
        return 0.001

    def _capped_settimeout(self: socket.socket, timeout: object) -> None:
        _real_settimeout(self, _immediate_timeout(timeout))

    def _capped_setdefaulttimeout(timeout: object) -> None:
        _real_setdefaulttimeout(_immediate_timeout(timeout))

    _real_setdefaulttimeout(0.001)
    socket.socket.settimeout = _capped_settimeout  # type: ignore[method-assign]
    socket.setdefaulttimeout = _capped_setdefaulttimeout  # type: ignore[assignment]

    import_sleeps: list[dict[str, object]] = []
    call_sleeps: list[dict[str, object]] = []
    phase = {"name": "import"}
    real_sleep = time.sleep

    def _recording_sleep(seconds: float) -> None:
        bucket = import_sleeps if phase["name"] == "import" else call_sleeps
        bucket.append({"where": phase["name"], "seconds": seconds})
        real_sleep(seconds)

    time.sleep = _recording_sleep  # type: ignore[assignment]

    audio_calls: list[str] = []
    shell_calls: list[str] = []
    outside_writes: list[dict[str, str]] = []

    def _playerish(command: object) -> bool:
        text = command if isinstance(command, str) else " ".join(str(part) for part in command)
        lowered = text.lower()
        return any(marker in lowered for marker in _PLAYER_MARKERS)

    real_system = os.system

    def _guard_system(command: str) -> int:
        if _playerish(command):
            shell_calls.append(command)
            return 127
        return real_system(command)

    os.system = _guard_system  # type: ignore[assignment]

    real_popen = subprocess.Popen

    def _guard_popen(*args: object, **kwargs: object) -> subprocess.Popen:
        command = args[0] if args else kwargs.get("args", "")
        if _playerish(command):
            shell_calls.append(repr(command)[:300])
            raise OSError("audio player blocked")
        return real_popen(*args, **kwargs)  # type: ignore[arg-type]

    subprocess.Popen = _guard_popen  # type: ignore[assignment]

    # The only allowed write root is the scratch workspace. Reads of the repo
    # are not recorded. Bytecode is off, so no cache directory is allowlisted.
    # /dev/null is the interpreter's discard sink (subprocess stdio). Recursion
    # state is per thread. A subprocess descendant does not inherit this hook.
    workspace_real = os.path.normcase(os.path.realpath(workspace))
    interpreter_writes = frozenset({os.path.normcase(os.path.realpath(os.devnull))})
    _audit_local = threading.local()

    def _normalise_db_path(value: object) -> str | None:
        """Filesystem spelling of one path or SQLite URI.

        Returns None for a non-path, ``""``, and ``":memory:"``. ``file:``
        URIs are percent-decoded and lose their query. ``file:///abs`` and
        ``file://localhost/abs`` become absolute paths. ``file:rel`` stays
        relative. A non-local authority is returned unchanged so the caller
        treats it as outside the workspace rather than skipping it.
        """
        if value is None or isinstance(value, bool) or isinstance(value, int):
            return None
        if isinstance(value, bytes):
            value = os.fsdecode(value)
        elif isinstance(value, os.PathLike):
            value = os.fspath(value)
        if not isinstance(value, str):
            return None
        text = value
        if text.startswith("file:"):
            path_part = urllib.parse.unquote(text.split("?", 1)[0].split("#", 1)[0][len("file:") :])
            if path_part.startswith("//"):
                authority, separator, tail = path_part[2:].partition("/")
                if authority in ("", "localhost"):
                    text = "/" + tail if separator else "/"
                else:
                    text = path_part
            else:
                text = path_part
        if text in ("", ":memory:"):
            return None
        return text

    def _resolved_write_path(value: object) -> str | None:
        text = _normalise_db_path(value)
        if text is None:
            return None
        return os.path.normcase(os.path.realpath(text))

    def _is_live(candidate: object) -> bool:
        """True when the candidate is a protected database, including a hard link.

        Path spelling comes only from ``_normalise_db_path``. The comparison
        is the resolved path and, when both files exist, the device and inode.
        """
        text = _normalise_db_path(candidate)
        if text is None:
            return False
        real = os.path.normcase(os.path.realpath(text))
        live_real = {os.path.normcase(os.path.realpath(os.fspath(path))) for path in live_dbs}
        if real in live_real:
            return True
        try:
            found = os.stat(text)
        except OSError:
            return False
        for path in live_dbs:
            try:
                live_stat = os.stat(path)
            except OSError:
                continue
            if found.st_dev == live_stat.st_dev and found.st_ino == live_stat.st_ino:
                return True
        return False

    def _outside_workspace(value: object) -> str | None:
        resolved = _resolved_write_path(value)
        if resolved is None:
            return None
        if resolved in interpreter_writes:
            return None
        if resolved == workspace_real or resolved.startswith(workspace_real + os.sep):
            return None
        return resolved

    def _resolved_dir_fd(dir_fd: int) -> str | None:
        link = f"/proc/self/fd/{dir_fd}"
        try:
            os.readlink(link)
        except OSError:
            return None
        return os.path.normcase(os.path.realpath(link))

    def _operand_outside(value: object, dir_fd: object) -> str | None:
        """Check one mutation operand. A supplied dir_fd is not resolved via cwd."""
        supplied = isinstance(dir_fd, int) and not isinstance(dir_fd, bool) and dir_fd >= 0
        if not supplied:
            return _outside_workspace(value)
        resolved_fd = _resolved_dir_fd(dir_fd)
        inside_fd = resolved_fd is not None and (
            resolved_fd == workspace_real or resolved_fd.startswith(workspace_real + os.sep)
        )
        if not inside_fd:
            return resolved_fd or f"/proc/self/fd/{dir_fd}"
        text = _normalise_db_path(value)
        if text is None:
            return None
        candidate = text if os.path.isabs(text) else os.path.join(resolved_fd or "", text)
        return _outside_workspace(candidate)

    def _open_is_write(mode: object, flags: object) -> bool:
        if isinstance(mode, str) and any(char in mode for char in "wax+"):
            return True
        if isinstance(flags, int):
            access = flags & os.O_ACCMODE
            if access in (os.O_WRONLY, os.O_RDWR):
                return True
            if flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                return True
        return False

    def _record_outside(event: str, path: str) -> None:
        outside_writes.append({"tool": str(phase["name"]), "event": event, "path": path})
        raise RuntimeError(f"effects child write outside the scratch workspace: {phase['name']}: {event} {path}")

    def _audit_writes(event: str, args: tuple[object, ...]) -> None:
        if getattr(_audit_local, "depth", 0):
            return
        _audit_local.depth = 1
        try:
            if event == "open":
                # flags and the mode string are not directory descriptors.
                # This event does not carry dir_fd.
                mode = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 else None
                if args and _open_is_write(mode, flags):
                    outside = _outside_workspace(args[0])
                    if outside is not None:
                        _record_outside(event, outside)
            elif event == "sqlite3.connect":
                database = args[0] if args else None
                if _is_live(database):
                    _record_outside(event, _resolved_write_path(database) or repr(database))
                else:
                    outside = _outside_workspace(database)
                    if outside is not None:
                        _record_outside(event, outside)
            elif event in _MUTATION_OPERANDS:
                for path_index, fd_index in _MUTATION_OPERANDS[event]:
                    if path_index >= len(args):
                        continue
                    dir_fd = args[fd_index] if fd_index is not None and fd_index < len(args) else None
                    outside = _operand_outside(args[path_index], dir_fd)
                    if outside is not None:
                        _record_outside(event, outside)
            elif event.startswith("shutil."):
                for value in args:
                    outside = _outside_workspace(value)
                    if outside is not None:
                        _record_outside(event, outside)
        finally:
            _audit_local.depth = 0

    sys.addaudithook(_audit_writes)

    real_connect = sqlite3.connect

    def _guard_connect(database: object, *args: object, **kwargs: object) -> sqlite3.Connection:
        """Refuse a connect that resolves to a live database.

        Spelling and the inode check are ``_normalise_db_path`` and
        ``_is_live``, the same helpers the audit hook uses. ``:memory:``
        is not a file.
        """
        if _is_live(database):
            raise RuntimeError(f"effects child tried to open the live database {database!r}")
        return real_connect(database, *args, **kwargs)

    sqlite3.connect = _guard_connect  # type: ignore[assignment]
    sqlite3.dbapi2.connect = _guard_connect  # type: ignore[assignment]

    def _run_hook_probe_mode(mode: str) -> None:
        """Exercise one hostile action after the hook is installed. No project import."""
        target = pathlib.Path(os.environ["VAJRA_OBSERVE_EFFECTS_PROBE_TARGET"])
        out = pathlib.Path(os.environ["VAJRA_OBSERVE_EFFECTS_PROBE_OUT"])
        fixture = pathlib.Path(os.environ["VAJRA_OBSERVE_EFFECTS_PROBE_DB"])
        before_bytes = target.read_bytes()
        before_mtime = target.stat().st_mtime_ns
        before_size = target.stat().st_size
        os.chdir(workspace)
        phase["name"] = mode
        outcome: dict[str, str] = {"status": "ALLOWED", "detail": ""}
        held = False
        workspace_created: list[str] = []
        workspace_modified: list[str] = []
        workspace_deleted: list[str] = []
        try:
            if mode == "uri_encoded":
                uri = "file:" + urllib.parse.quote(str(fixture), safe="") + "?mode=ro"
                connection = sqlite3.connect(uri, uri=True)
                try:
                    row = connection.execute("select value from sentinel").fetchone()
                    outcome["detail"] = "" if row is None else str(row[0])
                finally:
                    connection.close()
            elif mode == "connection_hardlink":
                connection = sqlite3.Connection(workspace / "hardlink.sqlite")
                try:
                    row = connection.execute("select value from sentinel").fetchone()
                    outcome["detail"] = "" if row is None else str(row[0])
                finally:
                    connection.close()
            elif mode == "connection_direct":
                sqlite3.Connection(fixture)
            elif mode == "relative_write":
                before_tree = _snapshot(workspace, ignore=_HARNESS_REPORT_FILES)
                pathlib.Path("report.json").write_text("harness", encoding="utf-8")
                pathlib.Path("x").write_text("side effect happened", encoding="utf-8")
                after_tree = _snapshot(workspace, ignore=_HARNESS_REPORT_FILES)
                _remember_delta(
                    "probe", before_tree, after_tree, workspace_created, workspace_modified, workspace_deleted
                )
            elif mode == "link":
                os.link(target, out / "new-link")
            elif mode == "symlink":
                os.symlink(target, out / "new-symlink")
            elif mode == "truncate":
                os.truncate(target, 1)
            elif mode == "utime":
                os.utime(target, ns=(1_000_000_000, 1_000_000_000))
            elif mode == "touch":
                target.touch()
            elif mode == "dir_fd":
                descriptor = os.open(out, os.O_RDONLY)
                try:
                    os.mkdir("new-dir", dir_fd=descriptor)
                finally:
                    os.close(descriptor)
            elif mode == "open":
                target.write_text("changed", encoding="utf-8")
            elif mode == "copy":
                shutil.copy(target, out / "copied")
            elif mode == "thread_reentrancy":
                entered = threading.Event()
                release = threading.Event()
                realpath = os.path.realpath
                hold = str(workspace / "hold")

                def _held(path: object, *args: object, **kwargs: object) -> str:
                    if (
                        os.path.normcase(os.fspath(path)) == os.path.normcase(hold)
                        and threading.current_thread().name == "heldwriter"
                    ):
                        entered.set()
                        release.wait()
                    return realpath(path, *args, **kwargs)  # type: ignore[arg-type]

                os.path.realpath = _held  # type: ignore[assignment]

                def _writer() -> None:
                    (workspace / "hold").write_text("safe", encoding="utf-8")

                def _escaper() -> None:
                    if not entered.wait(5):
                        release.set()
                        return
                    try:
                        target.write_text("race write escaped", encoding="utf-8")
                    except Exception as exc:  # noqa: BLE001 - the probe records the refusal
                        outcome["status"] = type(exc).__name__
                        outcome["detail"] = str(exc)
                    finally:
                        release.set()

                writer = threading.Thread(name="heldwriter", target=_writer)
                escaper = threading.Thread(name="escapingwriter", target=_escaper)
                writer.start()
                escaper.start()
                writer.join(5)
                escaper.join(5)
                held = entered.is_set()
                if writer.is_alive() or escaper.is_alive():
                    release.set()
                    writer.join(5)
                    escaper.join(5)
                    raise RuntimeError("thread reentrancy probe did not finish")
            else:
                raise RuntimeError(f"unknown hook probe {mode}")
        except Exception as exc:  # noqa: BLE001 - the probe records the refusal
            outcome["status"] = type(exc).__name__
            outcome["detail"] = str(exc)
        now = target.stat()
        _emit_and_exit(
            {
                "mode": mode,
                "status": outcome["status"],
                "detail": outcome["detail"],
                "outside_writes": outside_writes,
                "content": target.read_text(encoding="utf-8"),
                "size": now.st_size,
                "mtime_ns": now.st_mtime_ns,
                "unchanged": target.read_bytes() == before_bytes
                and now.st_mtime_ns == before_mtime
                and now.st_size == before_size,
                "link": (out / "new-link").exists(),
                "symlink": (out / "new-symlink").exists(),
                "copied": (out / "copied").exists(),
                "dir_fd_created": (out / "new-dir").exists(),
                "cwd_dir_created": (workspace / "new-dir").exists(),
                "held": held,
                "workspace_created": workspace_created,
                "workspace_modified": workspace_modified,
                "workspace_deleted": workspace_deleted,
            }
        )

    if hook_probe:
        _run_hook_probe_mode(hook_probe)

    import_network_end = 0
    signal.signal(signal.SIGALRM, _raise_bound)
    signal.setitimer(signal.ITIMER_REAL, _IMPORT_ALARM_S)
    try:
        import backend.core.llm_agent.tools as tools
        from backend.core.llm_agent.autonomous_agent import READ_ONLY_TOOL_NAMES
    except _CallBound:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        _emit_and_exit(
            {
                "import_error": f"import exceeded {_IMPORT_ALARM_S}s and was interrupted",
                "import_network": network,
                "import_sleeps": import_sleeps,
                "outside_writes": outside_writes,
            }
        )
    except Exception:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        traceback.print_exc()
        _emit_and_exit(
            {
                "import_error": traceback.format_exc(),
                "import_network": network,
                "import_sleeps": import_sleeps,
                "outside_writes": outside_writes,
            }
        )
    signal.setitimer(signal.ITIMER_REAL, 0.0)
    import_network_end = len(network)
    phase["name"] = "ready"
    import_threads = [
        {"name": thread.name, "daemon": thread.daemon}
        for thread in threading.enumerate()
        if thread.name != "MainThread"
    ]

    def _audio_modules() -> set[str]:
        found = set()
        for name in sys.modules:
            root = name.split(".", 1)[0]
            if root in _AUDIO_MODULE_ROOTS:
                found.add(name)
        return found

    def _arm_audio() -> None:
        sounddevice = sys.modules.get("sounddevice")
        if sounddevice is None:
            return
        for method in ("play", "playrec", "wait", "stop"):
            original = getattr(sounddevice, method, None)
            if original is None:
                continue

            def _blocked(*_args: object, _method: str = method, **_kwargs: object) -> None:
                audio_calls.append(_method)
                raise RuntimeError("audio blocked")

            setattr(sounddevice, method, _blocked)

    _arm_audio()

    home_before = _snapshot(home)
    workspace_before = _snapshot(workspace, ignore=_HARNESS_REPORT_FILES)
    audio_before = _audio_modules()
    db_existed = db_path.exists()
    db_digest = hashlib.sha256(db_path.read_bytes()).hexdigest() if db_existed else None

    override = os.environ.get("VAJRA_OBSERVE_EFFECTS_NAMES", "").strip()
    if override:
        names = tuple(part for part in override.split(",") if part)
    else:
        names = tuple(sorted(READ_ONLY_TOOL_NAMES))

    missing_args = sorted(name for name in names if name not in _TOOL_ARGS)
    errors: dict[str, str] = {}
    home_created: list[str] = []
    home_modified: list[str] = []
    home_deleted: list[str] = []
    workspace_created: list[str] = []
    workspace_modified: list[str] = []
    workspace_deleted: list[str] = []
    call_network: list[dict[str, str]] = []
    threads_by_tool: dict[str, list[str]] = {}
    db_by_tool: list[str] = []
    tool_seconds: dict[str, float] = {}
    nondaemon_by_tool: dict[str, list[str]] = {}
    started = time.monotonic()

    for name in names:
        if name not in _TOOL_ARGS:
            continue
        function = getattr(tools, name, None)
        if function is None:
            errors[name] = "missing handler on backend.core.llm_agent.tools"
            continue
        net_at = len(network)
        home_at = _snapshot(home)
        work_at = _snapshot(workspace, ignore=_HARNESS_REPORT_FILES)
        db_existed_at = db_path.exists()
        db_digest_at = hashlib.sha256(db_path.read_bytes()).hexdigest() if db_existed_at else None
        thread_ids = {thread.ident for thread in threading.enumerate()}
        phase["name"] = name
        tool_started = time.monotonic()
        signal.signal(signal.SIGALRM, _raise_bound)
        signal.setitimer(signal.ITIMER_REAL, _TOOL_ALARM_S)
        try:
            try:
                result = function(**_TOOL_ARGS[name])
                if inspect.iscoroutine(result):
                    import asyncio

                    asyncio.run(result)
            except Exception as exc:  # noqa: BLE001 - the call must be attempted; the failure is reported
                errors[name] = f"{type(exc).__name__}: {exc}"
        except _CallBound:
            errors[name] = f"bounded: exceeded {_TOOL_ALARM_S}s and was interrupted"
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
        tool_seconds[name] = round(time.monotonic() - tool_started, 3)
        home_now = _snapshot(home)
        work_now = _snapshot(workspace, ignore=_HARNESS_REPORT_FILES)
        _remember_delta(name, home_at, home_now, home_created, home_modified, home_deleted)
        _remember_delta(name, work_at, work_now, workspace_created, workspace_modified, workspace_deleted)
        for attempt in network[net_at:]:
            call_network.append({"tool": name, **attempt})
        db_exists_now = db_path.exists()
        if db_exists_now and not db_existed_at:
            db_by_tool.append(f"{name}: created")
        elif db_exists_now and db_digest_at is not None:
            if hashlib.sha256(db_path.read_bytes()).hexdigest() != db_digest_at:
                db_by_tool.append(f"{name}: modified")
        new_threads = [thread for thread in threading.enumerate() if thread.ident not in thread_ids]
        if new_threads:
            threads_by_tool[name] = sorted(thread.name for thread in new_threads)
        nondaemon = sorted(thread.name for thread in new_threads if not thread.daemon and thread.name != "MainThread")
        if nondaemon:
            nondaemon_by_tool[name] = nondaemon

    unexpected_threads = {
        tool: [name for name in started_names if name != _LEGACY_ADAPTER_THREAD]
        for tool, started_names in threads_by_tool.items()
    }
    unexpected_threads = {tool: names_ for tool, names_ in unexpected_threads.items() if names_}
    legacy_thread_tools = sorted(
        tool for tool, started_names in threads_by_tool.items() if _LEGACY_ADAPTER_THREAD in started_names
    )
    audio_added = sorted(_audio_modules() - audio_before)
    db_created = (not db_existed) and db_path.exists()
    db_modified = False
    if db_path.exists():
        digest_now = hashlib.sha256(db_path.read_bytes()).hexdigest()
        db_modified = digest_now != db_digest

    report = {
        "seconds": round(time.monotonic() - started, 3),
        "names": list(names),
        "missing_args": missing_args,
        "errors": errors,
        "home_created": home_created,
        "home_modified": home_modified,
        "home_deleted": home_deleted,
        "workspace_created": workspace_created,
        "workspace_modified": workspace_modified,
        "workspace_deleted": workspace_deleted,
        "network": call_network,
        "import_network": network[:import_network_end],
        "audio_modules_added": audio_added,
        "audio_calls": audio_calls,
        "shell_calls": shell_calls,
        "threads_by_tool": threads_by_tool,
        "unexpected_threads": unexpected_threads,
        "legacy_thread_tools": legacy_thread_tools,
        "db_created": db_created,
        "db_modified": db_modified,
        "db_by_tool": db_by_tool,
        "home_unchanged_vs_post_import": _snapshot(home) == home_before,
        "workspace_unchanged_vs_post_import": _snapshot(workspace, ignore=_HARNESS_REPORT_FILES) == workspace_before,
        "tool_seconds": tool_seconds,
        "call_sleeps": call_sleeps,
        "import_sleeps": import_sleeps,
        "import_threads": import_threads,
        "nondaemon_by_tool": nondaemon_by_tool,
        "nondaemon_threads": [
            {"name": thread.name, "daemon": thread.daemon}
            for thread in threading.enumerate()
            if thread.name != "MainThread" and not thread.daemon
        ],
        "child_elapsed_s": round(time.monotonic() - child_started, 3),
        "outside_writes": outside_writes,
        "cwd": os.getcwd(),
        "dont_write_bytecode": sys.dont_write_bytecode,
        "python_dont_write_bytecode": os.environ.get("PYTHONDONTWRITEBYTECODE", ""),
        # Proof the parent environment was not copied. The parent test plants
        # these and asserts they did not arrive.
        "parent_leaks": {
            "VAJRA_SENTINEL_LEAK": os.environ.get("VAJRA_SENTINEL_LEAK", ""),
            "IMAGE_PROVIDER": os.environ.get("IMAGE_PROVIDER", ""),
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
            "VAJRA_AUTONOMOUS_AGENT": os.environ.get("VAJRA_AUTONOMOUS_AGENT", ""),
            "TMPDIR": os.environ.get("TMPDIR", ""),
        },
    }
    _emit_and_exit(report)


if os.environ.get("VAJRA_OBSERVE_EFFECTS_CHILD") == "1":
    try:
        _child_main()
    except BaseException as exc:  # noqa: BLE001 - the child must not fall through to a joining exit
        sys.stdout.write(json.dumps({"import_error": f"{type(exc).__name__}: {exc}"}) + "\n")
        sys.stdout.flush()
    os._exit(0)


def _child_environ(
    home: pathlib.Path,
    db_path: pathlib.Path,
    result_path: pathlib.Path,
    names: str | None,
    workspace: pathlib.Path,
) -> dict[str, str]:
    """Environment for the effects child. Built from an allowlist, not inherited.

    ``os.environ.copy()`` let a suite that had exported ``TMPDIR``, ``XDG_*``,
    ``IMAGE_PROVIDER`` or ``VAJRA_*`` change the scratch location and the tool
    behaviour. ``TMPDIR`` outside ``/tmp`` made the child refuse to run, so the
    same test passed alone and failed inside that suite.
    """
    path = os.environ.get("PATH", "")
    if not path:
        raise AssertionError("PATH is required to spawn the effects child")
    env: dict[str, str] = {"PATH": path}
    for key in _LOCALE_VARS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    if "LANG" not in env and "LC_ALL" not in env:
        env["LANG"] = "C.UTF-8"
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        env["VIRTUAL_ENV"] = virtual_env
    env["HOME"] = str(home)
    env["TMPDIR"] = str(home / "tmp")
    env["XDG_CACHE_HOME"] = str(home / "cache")
    env["XDG_CONFIG_HOME"] = str(home / "config")
    env["XDG_DATA_HOME"] = str(home / "data")
    env["XDG_STATE_HOME"] = str(home / "state")
    env["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["VAJRA_OBSERVE_EFFECTS_WORK"] = str(workspace)
    env["VAJRA_OBSERVE_EFFECTS_CHILD"] = "1"
    env["VAJRA_OBSERVE_EFFECTS_DB"] = str(db_path)
    env["VAJRA_OBSERVE_EFFECTS_RESULT"] = str(result_path)
    for key in _PROVIDER_KEY_VARS:
        env[key] = ""
    if names is not None:
        env["VAJRA_OBSERVE_EFFECTS_NAMES"] = names
    return env


def _run_child(names: str | None = None) -> dict[str, object]:
    """One fresh interpreter. ``names`` forces a comma-separated list."""
    # dir= ignores the parent TMPDIR, which a suite (or a harness) may point
    # outside /tmp. The child refuses to run unless HOME is under /tmp.
    work = pathlib.Path(tempfile.mkdtemp(prefix="ag1-observe-", dir="/tmp"))
    home = work / "home"
    home.mkdir()
    for sub in ("tmp", "cache", "config", "data", "state"):
        (home / sub).mkdir()
    db_path = work / "app.db"
    result_path = work / "report.json"
    env = _child_environ(home, db_path, result_path, names, work)

    started = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, str(pathlib.Path(__file__).resolve())],
        cwd=work,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        return _collect_child(proc, result_path, started)
    finally:
        if proc.poll() is None:
            _kill_child(proc)
        shutil.rmtree(work, ignore_errors=True)


def _collect_child(
    proc: subprocess.Popen[str],
    result_path: pathlib.Path,
    started: float,
) -> dict[str, object]:
    try:
        stdout, stderr = proc.communicate(timeout=_CHILD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        _kill_child(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        wall = round(time.monotonic() - started, 3)
        raise AssertionError(
            "effects child exceeded "
            f"{_CHILD_TIMEOUT_S}s (wall={wall}s) and was killed. "
            "A blocked socket or a non-daemon thread kept the child alive "
            "past the parent bound. The import and per-tool alarms name the "
            "stuck phase before this bound is reached.\n"
            f"stdout:\n{(stdout or '')[:4000]}\n"
            f"stderr:\n{(stderr or '')[:4000]}"
        )
    wall = round(time.monotonic() - started, 3)
    if not result_path.exists():
        raise AssertionError(
            "effects child wrote no report\n"
            f"exit={proc.returncode} wall={wall}s\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    report = json.loads(result_path.read_text(encoding="utf-8"))
    report["_stderr"] = stderr
    report["_exit"] = proc.returncode
    report["_child_wall_s"] = wall
    return report


def _kill_child(proc: subprocess.Popen[str]) -> None:
    """SIGKILL the child's process group. ``communicate`` does not do this."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _problems(report: dict[str, object]) -> list[str]:
    if "import_error" in report:
        return [f"import failed:\n{report['import_error']}"]
    problems: list[str] = []
    for key in (
        "missing_args",
        "home_created",
        "home_modified",
        "home_deleted",
        "workspace_created",
        "workspace_modified",
        "workspace_deleted",
        "network",
        "audio_modules_added",
        "audio_calls",
        "shell_calls",
    ):
        value = report.get(key) or []
        if value:
            problems.append(f"{key}: {value}")
    errors = report.get("errors") or {}
    if errors:
        problems.append(f"errors: {errors}")
    unexpected = report.get("unexpected_threads") or {}
    if unexpected:
        problems.append(f"unexpected_threads: {unexpected}")
    if report.get("db_created") or report.get("db_modified"):
        problems.append(
            "scratch DATABASE_URL changed: "
            f"created={report.get('db_created')} modified={report.get('db_modified')} "
            f"by={report.get('db_by_tool')}"
        )
    nondaemon = report.get("nondaemon_threads") or []
    if nondaemon:
        problems.append(f"nondaemon_threads: {nondaemon} by_tool={report.get('nondaemon_by_tool')}")
    sleeps = report.get("call_sleeps") or []
    if sleeps:
        problems.append(f"call_sleeps: {sleeps}")
    outside = report.get("outside_writes") or []
    if outside:
        problems.append(f"outside_writes: {outside}")
    if report.get("workspace_unchanged_vs_post_import") is False:
        problems.append("workspace changed relative to the post-import snapshot")
    return problems


def test_observe_only_tools_have_no_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each allowlisted tool runs, and none of them touch home, network, audio, or the scratch DB.

    The planted parent variables are the ones a suite has actually exported.
    They must not reach the child, and a parent ``TMPDIR`` outside ``/tmp``
    must not move the scratch. The child works in the scratch directory, with
    bytecode disabled, and reports a write that leaves that directory.
    """
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    monkeypatch.setenv("VAJRA_SENTINEL_LEAK", "leak")
    monkeypatch.setenv("TMPDIR", "/var/tmp")
    before = {thread.ident for thread in threading.enumerate()}
    report = _run_child()
    leaks = report.get("parent_leaks")
    if "import_error" not in report:
        assert isinstance(leaks, dict), report
        assert leaks.get("VAJRA_SENTINEL_LEAK") == "", leaks
        assert leaks.get("IMAGE_PROVIDER") == "", leaks
        assert leaks.get("OPENAI_API_KEY") == "", leaks
        assert leaks.get("VAJRA_AUTONOMOUS_AGENT") == "", leaks
        assert str(leaks.get("TMPDIR", "")).startswith("/tmp/"), leaks
        assert report.get("dont_write_bytecode") is True, report
        assert report.get("python_dont_write_bytecode") == "1", report
        child_cwd = pathlib.Path(str(report.get("cwd", ""))).resolve()
        assert str(child_cwd).startswith("/tmp/"), report
        assert child_cwd != pathlib.Path(__file__).resolve().parents[2], report
    gained = [thread.name for thread in threading.enumerate() if thread.ident not in before and not thread.daemon]
    tool_seconds = report.get("tool_seconds") or {}
    slowest_name = ""
    slowest_s = 0.0
    if isinstance(tool_seconds, dict) and tool_seconds:
        slowest_name = max(tool_seconds, key=lambda name: float(tool_seconds[name]))
        slowest_s = float(tool_seconds[slowest_name])
    print(
        "OBSERVE_EFFECTS"
        f" child_wall_s={report.get('_child_wall_s')}"
        f" child_elapsed_s={report.get('child_elapsed_s')}"
        f" tool_loop_s={report.get('seconds')}"
        f" slowest={slowest_name}:{slowest_s}"
        f" import_sleeps={report.get('import_sleeps')}"
        f" import_threads={report.get('import_threads')}"
        f" nondaemon_child={report.get('nondaemon_threads')}"
        f" nondaemon_pytest={gained}",
        flush=True,
    )
    problems = _problems(report)
    if gained:
        problems.append(f"pytest process gained non-daemon threads: {gained}")
    legacy = report.get("legacy_thread_tools") or []
    detail = (
        f"child_wall_s={report.get('_child_wall_s')} seconds={report.get('seconds')} "
        f"names={len(report.get('names') or [])} legacy_thread_tools={legacy}\n" + "\n".join(problems)
    )
    assert not problems, detail


def test_observe_effects_child_rejects_an_unlisted_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """A read-only name with no argument entry is a failure, not a skip."""
    monkeypatch.setenv("VAJRA_OBSERVE_EFFECTS_CHILD", "")
    report = _run_child(names="not_a_real_observe_tool")
    missing = report.get("missing_args")
    assert missing == ["not_a_real_observe_tool"], report


def _run_hook_probe(mode: str, root: pathlib.Path) -> dict[str, object]:
    """Spawn the hook probe. The hard link exists before the child installs the hook.

    ``root`` is a pytest ``tmp_path`` (or a subdirectory). The fixture database
    lives beside the workspace, never at the repo database.
    """
    workspace = root / "workspace"
    out = root / "outside"
    workspace.mkdir()
    out.mkdir()
    target = out / "target"
    target.write_text("original data", encoding="utf-8")
    fixture = out / "owned-fixture.sqlite"
    connection = sqlite3.connect(fixture)
    connection.execute("create table sentinel(value)")
    connection.execute("insert into sentinel values ('owned fixture only')")
    connection.commit()
    connection.close()
    (workspace / "hardlink.sqlite").hardlink_to(fixture)
    before_fixture = fixture.read_bytes()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": os.environ.get("LANG") or "C.UTF-8",
        "HOME": str(workspace),
        "TMPDIR": str(workspace),
        "PYTHONDONTWRITEBYTECODE": "1",
        "VAJRA_OBSERVE_EFFECTS_CHILD": "1",
        "VAJRA_OBSERVE_EFFECTS_HOOK_PROBE": mode,
        "VAJRA_OBSERVE_EFFECTS_WORK": str(workspace),
        "VAJRA_OBSERVE_EFFECTS_DB": str(workspace / "app.db"),
        "VAJRA_OBSERVE_EFFECTS_RESULT": str(workspace / "report.json"),
        "VAJRA_OBSERVE_EFFECTS_PROBE_TARGET": str(target),
        "VAJRA_OBSERVE_EFFECTS_PROBE_OUT": str(out),
        "VAJRA_OBSERVE_EFFECTS_PROBE_DB": str(fixture),
        "VAJRA_OBSERVE_EFFECTS_LIVE_FIXTURE": str(fixture),
    }
    proc = subprocess.run(
        [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        start_new_session=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise AssertionError(
            f"hook probe {mode} failed exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    report["fixture_unchanged"] = fixture.read_bytes() == before_fixture
    return report


def _assert_hook_refused(report: dict[str, object]) -> None:
    assert report["status"] == "RuntimeError", report
    assert report["outside_writes"], report
    assert report["unchanged"] is True, report
    assert report["fixture_unchanged"] is True, report


def test_encoded_sqlite_uri_to_fixture_db_is_refused(tmp_path: pathlib.Path) -> None:
    """A percent-encoded file: URI must not open a database outside the workspace.

    ``sqlite3.connect`` hits the wrapper, which raises before the C audit
    event, so this refusal is the guard message rather than ``outside_writes``.
    """
    report = _run_hook_probe("uri_encoded", tmp_path)
    assert report["status"] == "RuntimeError", report
    assert "live database" in str(report["detail"]), report
    assert "owned fixture only" not in str(report["detail"])
    assert report["unchanged"] is True, report
    assert report["fixture_unchanged"] is True, report


def test_direct_connection_to_fixture_hardlink_is_refused(tmp_path: pathlib.Path) -> None:
    """sqlite3.Connection on a hard link of a protected database is the same file."""
    report = _run_hook_probe("connection_hardlink", tmp_path)
    _assert_hook_refused(report)
    assert "owned fixture only" not in str(report["detail"])


def test_relative_write_inside_scratch_fails_the_workspace_snapshot(tmp_path: pathlib.Path) -> None:
    """A relative write under the scratch workspace fails the effects check.

    The hook allows the workspace, so this is not an audit-hook exception.
    The before/after snapshot is what refuses a clean pass. The harness report
    name is the only ignored path, and nothing is written outside the scratch.
    """
    report = _run_hook_probe("relative_write", tmp_path)
    assert report["outside_writes"] == [], report
    assert report["status"] == "ALLOWED", report
    created = report["workspace_created"]
    assert created == ["probe: x"], report
    problems = _problems(report)
    assert any("workspace_created" in problem for problem in problems), problems
    assert (tmp_path / "workspace" / "x").read_text(encoding="utf-8") == "side effect happened"
    assert not (tmp_path / "outside" / "x").exists()


def test_os_link_outside_is_refused(tmp_path: pathlib.Path) -> None:
    report = _run_hook_probe("link", tmp_path)
    _assert_hook_refused(report)
    assert report["link"] is False, report


def test_os_symlink_outside_is_refused(tmp_path: pathlib.Path) -> None:
    report = _run_hook_probe("symlink", tmp_path)
    _assert_hook_refused(report)
    assert report["symlink"] is False, report


def test_os_truncate_outside_is_refused(tmp_path: pathlib.Path) -> None:
    report = _run_hook_probe("truncate", tmp_path)
    _assert_hook_refused(report)
    assert report["content"] == "original data", report
    assert report["size"] == 13, report


def test_os_utime_and_path_touch_outside_are_refused(tmp_path: pathlib.Path) -> None:
    for mode in ("utime", "touch"):
        root = tmp_path / mode
        root.mkdir()
        report = _run_hook_probe(mode, root)
        _assert_hook_refused(report)
        assert report["content"] == "original data", report


def test_os_mkdir_with_dir_fd_outside_is_refused(tmp_path: pathlib.Path) -> None:
    report = _run_hook_probe("dir_fd", tmp_path)
    _assert_hook_refused(report)
    assert report["dir_fd_created"] is False, report
    assert report["cwd_dir_created"] is False, report


def test_audit_depth_is_per_thread(tmp_path: pathlib.Path) -> None:
    """One thread parked inside realpath must not blind another thread's write."""
    report = _run_hook_probe("thread_reentrancy", tmp_path)
    assert report["held"] is True, report
    _assert_hook_refused(report)
    assert report["content"] == "original data", report


def test_ordinary_outside_open_copy_and_direct_connection_stay_refused(tmp_path: pathlib.Path) -> None:
    for mode in ("open", "copy", "connection_direct"):
        root = tmp_path / mode
        root.mkdir()
        report = _run_hook_probe(mode, root)
        _assert_hook_refused(report)
        assert report["copied"] is False, report


def test_extracted_guard_refuses_live_db_spellings_without_connecting() -> None:
    """Live-database spellings reach a recording fake only for "" and :memory:.

    The real path is stat'd by the guard and is never passed to sqlite3.connect.
    """
    import ast

    repo = pathlib.Path(__file__).resolve().parents[2]
    live = repo / "vajra_stream.db"
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    wanted = ("_normalise_db_path", "_is_live", "_guard_connect")
    nodes = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name in wanted]
    nodes.sort(key=lambda node: node.lineno)
    assert [node.name for node in nodes] == list(wanted), [node.name for node in nodes]
    forwarded: list[str] = []

    def _fake(*args: object, **_kwargs: object) -> str:
        forwarded.append(repr(args))
        return "fake"

    env: dict[str, object] = {
        "os": os,
        "urllib": urllib,
        "sqlite3": sqlite3,
        "live_dbs": {live, repo / "backend" / "app" / "vajra_stream.db"},
        "real_connect": _fake,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "ag1e-guard", "exec"), env)  # noqa: S102
    guard = env["_guard_connect"]
    assert callable(guard)
    previous = os.getcwd()
    os.chdir(repo)
    try:
        blocked = [
            str(live),
            "vajra_stream.db",
            "backend/app/vajra_stream.db",
            bytes(live),
            live,
            "file:" + str(live) + "?mode=ro",
            "file:" + urllib.parse.quote(str(live), safe="") + "?mode=ro",
            "file://localhost" + str(live) + "?mode=ro",
            str(repo / "core/../vajra_stream.db"),
        ]
        for form in blocked:
            try:
                guard(form, uri=True)
            except RuntimeError:
                continue
            raise AssertionError(f"live spelling was forwarded: {form!r}")
        for form in (":memory:", ""):
            guard(form, uri=True)
    finally:
        os.chdir(previous)
    assert forwarded == ["(':memory:',)", "('',)"], forwarded
