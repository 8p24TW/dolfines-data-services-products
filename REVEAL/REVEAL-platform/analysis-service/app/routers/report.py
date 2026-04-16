import json
import os
import shutil
import tempfile
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.services.report_builder import generate_report_file

router = APIRouter()


@router.post("/report/generate")
async def generate_report(
    files: Annotated[list[UploadFile], File()],
    site_config: Annotated[str, Form()],
    column_mappings: Annotated[str, Form()] = "{}",
    report_type: Annotated[str, Form()] = "comprehensive",
    lang: Annotated[str, Form()] = "en",
    report_date: Annotated[str | None, Form()] = None,
    logo_variant: Annotated[str, Form()] = "dolfines",
    output_format: Annotated[str, Form()] = "pdf",
):
    """Generate a report file and stream it back to the caller."""
    tmp_dir = tempfile.mkdtemp(prefix="reveal_report_")
    try:
        saved = []
        for f in files:
            dest = os.path.join(tmp_dir, f.filename or f"file_{len(saved)}.csv")
            with open(dest, "wb") as fh:
                fh.write(await f.read())
            saved.append(dest)

        config = json.loads(site_config)
        mappings = json.loads(column_mappings)

        report_path, media_type = await generate_report_file(
            data_files=saved,
            site_config=config,
            column_mappings=mappings,
            report_type=report_type,
            lang=lang,
            report_date=report_date,
            logo_variant=logo_variant,
            output_dir=tmp_dir,
            output_format=output_format,
        )

        def iterfile():
            with open(report_path, "rb") as fh:
                yield from fh
            shutil.rmtree(tmp_dir, ignore_errors=True)

        site_name = config.get("site_name", "site").replace(" ", "_")
        suffix = ".html" if media_type.startswith("text/html") else ".pdf"
        filename = f"REVEAL_{report_type}_{site_name}{suffix}"

        return StreamingResponse(
            iterfile(),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
