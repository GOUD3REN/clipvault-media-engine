import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)


class FFmpegUnavailableError(RuntimeError):
    """Raised when ffmpeg/ffprobe cannot be executed on this machine."""


def _candidate(name: str) -> str:
    override = os.environ.get(f"CLIPVAULT_{name.upper()}")
    if override:
        return override
    found = shutil.which(name) or shutil.which(name + ".exe")
    return found or name


def ffmpeg_path() -> str:
    return _candidate("ffmpeg")


def ffprobe_path() -> str:
    return _candidate("ffprobe")


def _describe_problem(path: str):
    if os.path.isdir(path):
        return f"'{path}' is a DIRECTORY, not an executable. Fix your PATH or set CLIPVAULT_FFMPEG/CLIPVAULT_FFPROBE."
    if os.path.exists(path) and not os.access(path, os.X_OK):
        return (
            f"'{path}' exists but is NOT executable (permission denied). "
            "Linux/macOS: run 'chmod +x <path>'. Windows: unblock the file or reinstall FFmpeg, "
            "or set CLIPVAULT_FFMPEG / CLIPVAULT_FFPROBE to the full .exe path."
        )
    return None


def verify() -> dict:
    result = {"ok": True, "ffmpeg": None, "ffprobe": None, "version": None, "error": None}
    for key, getter in (("ffmpeg", ffmpeg_path), ("ffprobe", ffprobe_path)):
        path = getter()
        resolved = shutil.which(path) or path
        problem = _describe_problem(resolved)
        if problem:
            result.update(ok=False, error=problem)
            result[key] = resolved
            return result
        try:
            probe = subprocess.run(
                [resolved, "-version"],
                capture_output=True, text=True, timeout=15
            )
        except FileNotFoundError:
            result.update(
                ok=False,
                error=f"'{key}' not found on PATH. Install FFmpeg or set CLIPVAULT_{key.upper()} to the binary path."
            )
            result[key] = resolved
            return result
        except PermissionError as e:
            result.update(
                ok=False,
                error=(
                    f"Permission denied executing '{resolved}' ({e}). Linux/macOS: 'chmod +x' the binary. "
                    f"Windows: unblock/reinstall FFmpeg or set CLIPVAULT_{key.upper()}."
                )
            )
            result[key] = resolved
            return result
        except subprocess.TimeoutExpired:
            result.update(ok=False, error=f"'{resolved}' did not respond to -version.")
            return result
        result[key] = resolved
        if key == "ffmpeg" and probe.stdout:
            result["version"] = probe.stdout.splitlines()[0]
    return result


def require() -> None:
    check = verify()
    if not check["ok"]:
        raise FFmpegUnavailableError(check["error"])