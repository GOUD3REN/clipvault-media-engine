import os
import logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .models.job import ProcessingConfig
from .core.job_manager import JobManager
from .core import ffmpeg_tools

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("logs/clipvault.log"), logging.StreamHandler()]
)

app = FastAPI(title="CLIPVAULT MEDIA ENGINE")
job_manager = JobManager()

for d in ["input", "assets", "output", "templates"]:
    os.makedirs(d, exist_ok=True)


class ProcessRequest(BaseModel):
    input_dir: str
    image_path: str
    jumpscare_position_pct: float
    jumpscare_duration: float
    output_width: int = 1080
    output_height: int = 1920
    output_naming_prefix: str = "edit_final_"
    template_name: str = "streamer_jumpscare_v1"


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return ffmpeg_tools.verify()


@app.get("/api/status")
async def get_status():
    return job_manager.get_status() or {"status": "READY"}


@app.get("/api/templates")
async def get_templates():
    templates = []
    if os.path.isdir("templates"):
        for f in os.listdir("templates"):
            if f.endswith(".json"):
                try:
                    with open(os.path.join("templates", f), "r", encoding="utf-8") as fp:
                        templates.append(json.load(fp))
                except Exception:
                    pass
    return templates


@app.post("/api/process")
async def process_videos(req: ProcessRequest):
    if not os.path.exists(req.image_path):
        raise HTTPException(status_code=400, detail="Jumpscare image not found.")
    try:
        config = ProcessingConfig(
            input_dir=req.input_dir,
            image_path=req.image_path,
            jumpscare_position_pct=req.jumpscare_position_pct,
            jumpscare_duration=req.jumpscare_duration,
            output_width=req.output_width,
            output_height=req.output_height,
            output_naming_prefix=req.output_naming_prefix
        )
        job_manager.create_job(config, req.template_name)
        job_manager.start_job(config)
        return {"message": "Batch job started."}
    except ffmpeg_tools.FFmpegUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


app.mount("/static", StaticFiles(directory="static"), name="static")

_startup = ffmpeg_tools.verify()
if _startup["ok"]:
    logging.info(f"FFmpeg OK: {_startup['ffmpeg']} | {_startup['version']}")
else:
    logging.warning(f"FFMPEG PROBLEM: {_startup['error']}")