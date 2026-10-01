import subprocess
import json
import os
import logging
from .ffmpeg_tools import ffprobe_path

logger = logging.getLogger(__name__)


def analyze_video(filepath: str) -> dict:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video not found: {filepath}")

    cmd = [
        ffprobe_path(), "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", filepath
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        if "format" not in data or "duration" not in data["format"]:
            raise ValueError("Could not determine video duration.")

        duration = float(data["format"]["duration"])
        video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), None)
        audio_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "audio"), None)

        fps = 30.0
        if video_stream:
            fr = video_stream.get("avg_frame_rate", "30/1")
            if '/' in str(fr):
                num, den = str(fr).split('/')
                if float(den) != 0:
                    fps = float(num) / float(den)
            else:
                fps = float(fr)

        return {
            "duration": duration,
            "fps": fps,
            "has_video": video_stream is not None,
            "has_audio": audio_stream is not None
        }
    except FileNotFoundError:
        raise ValueError("ffprobe not found on PATH. Install FFmpeg or set CLIPVAULT_FFPROBE.")
    except PermissionError as e:
        raise ValueError(
            f"Permission denied executing ffprobe ({e}). "
            "Fix binary permissions or set CLIPVAULT_FFPROBE."
        )
    except subprocess.CalledProcessError:
        raise ValueError("Unsupported or corrupted video file.")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {filepath}: {e}")
        raise ValueError(f"Analysis error: {str(e)}")