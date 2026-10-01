import subprocess
import logging

logger = logging.getLogger(__name__)


def build_segment_cmd(
    input_path: str, output_path: str,
    start_time: float, duration: float,
    vf: str, has_audio: bool
) -> list:
    cmd = ["ffmpeg", "-y", "-i", input_path]

    if not has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    if start_time > 0:
        cmd += ["-ss", str(start_time)]
    if duration > 0:
        cmd += ["-t", str(duration)]

    cmd += [
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p"
    ]

    if has_audio:
        cmd += [
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k"
        ]
    else:
        cmd += [
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k"
        ]

    cmd.append(output_path)
    return cmd


def build_jumpscare_cmd(
    image_path: str, output_path: str,
    duration: float, vf: str
) -> list:
    return [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
        "-shortest",
        output_path
    ]


def build_concat_cmd(concat_file: str, output_path: str) -> list:
    return [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy",
        output_path
    ]


def run_ffmpeg(cmd: list):
    from .ffmpeg_tools import ffmpeg_path

    # cmd vem como ["ffmpeg", "-y", "-i", ...] — substituímos o literal "ffmpeg"
    # pelo caminho resolvido (que pode ser um .exe ou um caminho absoluto).
    full_cmd = [ffmpeg_path()] + cmd[1:]

    logger.debug(f"Running FFmpeg: {' '.join(full_cmd)}")

    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg or set CLIPVAULT_FFMPEG."
        )
    except PermissionError as e:
        raise RuntimeError(
            f"Permission denied executing ffmpeg ({e}). "
            "Fix binary permissions or set CLIPVAULT_FFMPEG."
        )

    if result.returncode != 0:
        logger.error(f"FFmpeg failed: {result.stderr}")
        raise RuntimeError(f"FFmpeg error: {result.stderr[:200]}...")