import os
import uuid
import threading
import logging
import glob
from typing import Optional

from ..models.job import (
    BatchJob, JobStatus, VideoTask, VideoStatus, ProcessingConfig
)
from .renderer import render_video
from . import ffmpeg_tools

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self):
        self.current_job: Optional[BatchJob] = None
        self._lock = threading.Lock()

    def get_status(self) -> Optional[dict]:
        with self._lock:
            return self.current_job.model_dump() if self.current_job else None

    def create_job(self, config: ProcessingConfig, template_name: str) -> BatchJob:
        with self._lock:
            if self.current_job and self.current_job.status == JobStatus.PROCESSING:
                raise RuntimeError("A job is already processing.")

            input_files = []
            if os.path.exists(config.input_dir):
                for ext in ("*.mp4", "*.mov", "*.mkv", "*.avi"):
                    input_files.extend(glob.glob(os.path.join(config.input_dir, ext)))
                    input_files.extend(
                        glob.glob(os.path.join(config.input_dir, ext.upper()))
                    )
            else:
                raise FileNotFoundError(
                    f"Input directory not found: {config.input_dir}"
                )

            # Dedupe: no Windows o glob é case-insensitive, então "*.mp4" e "*.MP4"
            # retornam os mesmos arquivos, duplicando a lista.
            deduped = []
            seen = set()
            for f in input_files:
                key = os.path.normcase(os.path.abspath(f))
                if key not in seen:
                    seen.add(key)
                    deduped.append(f)
            input_files = deduped

            if not input_files:
                raise ValueError("No video files found in input directory.")

            input_files.sort()

            # Pré-flight: garante que ffmpeg/ffprobe estão executáveis
            # ANTES de criar o job, para não estourar erro dentro do batch.
            ffmpeg_tools.require()

            job = BatchJob(
                id=str(uuid.uuid4()),
                total=len(input_files),
                template=template_name,
                tasks=[
                    VideoTask(id=str(uuid.uuid4()), filename=os.path.basename(f))
                    for f in input_files
                ]
            )
            self.current_job = job
            return job

    def start_job(self, config: ProcessingConfig):
        threading.Thread(
            target=self._run_batch, args=(config,), daemon=True
        ).start()

    def _run_batch(self, config: ProcessingConfig):
        with self._lock:
            if not self.current_job:
                return
            self.current_job.status = JobStatus.PROCESSING

        job = self.current_job
        os.makedirs("output", exist_ok=True)
        temp_dir = os.path.join("logs", f"temp_{job.id}")
        os.makedirs(temp_dir, exist_ok=True)

        for idx, task in enumerate(job.tasks):
            try:
                with self._lock:
                    task.status = VideoStatus.ANALYZING

                input_path = os.path.join(config.input_dir, task.filename)
                output_filename = f"{config.output_naming_prefix}{idx + 1:03d}.mp4"

                with self._lock:
                    task.output_filename = output_filename
                    task.status = VideoStatus.RENDERING

                render_video(
                    input_path,
                    os.path.join("output", output_filename),
                    config.image_path,
                    config.jumpscare_duration,
                    config.jumpscare_position_pct,
                    config.output_width,
                    config.output_height,
                    temp_dir
                )

                with self._lock:
                    task.status = VideoStatus.COMPLETED
                    job.completed += 1

            except Exception as e:
                logger.error(f"Failed to process {task.filename}: {str(e)}")
                with self._lock:
                    task.status = VideoStatus.FAILED
                    task.error = str(e)
                    job.failed += 1

        with self._lock:
            if job.failed == job.total:
                job.status = JobStatus.FAILED
            else:
                job.status = JobStatus.COMPLETED

        try:
            os.rmdir(temp_dir)
        except OSError:
            pass