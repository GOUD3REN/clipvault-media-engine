from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
import uuid

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class VideoStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPOSITING = "COMPOSITING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VideoTask(BaseModel):
    id: str
    filename: str
    status: VideoStatus = VideoStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None
    output_filename: Optional[str] = None
    duration: Optional[float] = None

class BatchJob(BaseModel):
    id: str
    status: JobStatus = JobStatus.QUEUED
    total: int = 0
    completed: int = 0
    failed: int = 0
    template: str
    tasks: List[VideoTask] = []

class ProcessingConfig(BaseModel):
    input_dir: str
    image_path: str
    jumpscare_position_pct: float = 50.0
    jumpscare_duration: float = 0.5
    output_width: int = 1080
    output_height: int = 1920
    output_naming_prefix: str = "edit_final_"