import json
import os
import tempfile
import shutil
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.services.pipeline import run_pipeline
from app.services.column_detector import detect_columns

router = APIRouter()


@router.post("/detect-columns")
async def detect_columns_endpoint(
    file: Annotated[UploadFile, File()],
    site_type: Annotated[str, Form()] = "solar",
    worksheet: Annotated[str | None, Form()] = None,
):
    """Auto-detect column roles in an uploaded SCADA CSV."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or "")[1])
    try:
        tmp.write(await file.read())
        tmp.flush()
        result = detect_columns(tmp.name, file.filename or "", site_type, worksheet)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp.close()
        os.unlink(tmp.name)


@router.post("/analyse")
async def analyse_endpoint(
    files: Annotated[list[UploadFile], File()],
    site_config: Annotated[str, Form()],
    column_mappings: Annotated[str, Form()] = "{}",
    lang: Annotated[str, Form()] = "en",
):
    """Run the full analysis pipeline and return chart-ready JSON."""
    tmp_dir = tempfile.mkdtemp(prefix="reveal_analyse_")
    try:
        saved = []
        for f in files:
            dest = os.path.join(tmp_dir, f.filename or f"file_{len(saved)}.csv")
            with open(dest, "wb") as fh:
                fh.write(await f.read())
            saved.append(dest)

        config = json.loads(site_config)
        mappings = json.loads(column_mappings)

        result = run_pipeline(saved, config, mappings, lang)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
