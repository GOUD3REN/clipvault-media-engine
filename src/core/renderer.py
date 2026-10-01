import os
import logging
from .compositor import (
    build_segment_cmd, build_jumpscare_cmd,
    build_concat_cmd, run_ffmpeg
)
from .analyzer import analyze_video

logger = logging.getLogger(__name__)


def render_video(
    input_path: str,
    output_path: str,
    image_path: str,
    jump_duration: float,
    jump_position_pct: float,
    target_width: int,
    target_height: int,
    temp_dir: str
):
    meta = analyze_video(input_path)
    duration = meta["duration"]
    fps = meta["fps"] if 10 <= meta["fps"] <= 120 else 30.0
    has_audio = meta["has_audio"]

    if not (0 <= jump_position_pct <= 100):
        raise ValueError("Invalid jumpscare position")
    if jump_duration <= 0:
        raise ValueError("Invalid jumpscare duration")

    midpoint = duration * (jump_position_pct / 100.0)

    vf = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
        f"setsar=1,fps={fps}"
    )

    part1 = os.path.join(temp_dir, "part1.mp4")
    part2 = os.path.join(temp_dir, "part2.mp4")
    jump = os.path.join(temp_dir, "jump.mp4")
    concat_file = os.path.join(temp_dir, "concat.txt")

    logger.info(
        f"Processing {os.path.basename(input_path)}: "
        f"duration={duration:.2f}s, midpoint={midpoint:.2f}s"
    )

    def concat_entry(p: str) -> str:
        # FFmpeg concat demuxer precisa de barras '/' mesmo no Windows,
        # e aspas internas devem ser escapadas.
        safe = os.path.abspath(p).replace("\\", "/")
        return "file '" + safe.replace("'", "'\\''") + "'"

    try:
        run_ffmpeg(build_segment_cmd(input_path, part1, 0, midpoint, vf, has_audio))
        run_ffmpeg(build_segment_cmd(input_path, part2, midpoint, 0, vf, has_audio))
        run_ffmpeg(build_jumpscare_cmd(image_path, jump, jump_duration, vf))

        with open(concat_file, "w", encoding="utf-8") as f:
            f.write(concat_entry(part1) + "\n")
            f.write(concat_entry(jump) + "\n")
            f.write(concat_entry(part2) + "\n")

        run_ffmpeg(build_concat_cmd(concat_file, output_path))
    finally:
        for f in [part1, part2, jump, concat_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass