"""Local-only, stateless API. Run with uvicorn api:app --host 127.0.0.1."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, FileResponse
from starlette.datastructures import UploadFile
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.concurrency import run_in_threadpool

from importer import MAX_BYTES, read_table, normalize, export_csv

app = FastAPI(title="Local tabular importer", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
MAX_REQUEST = MAX_BYTES + 256 * 1024
ROOT = Path(__file__).parent


@app.middleware("http")
async def local_boundary(request, call_next):
    origin = request.headers.get("origin")
    if origin and (urlsplit(origin).scheme != "http" or urlsplit(origin).netloc != request.headers.get("host")):
        return JSONResponse({"detail": "Cross-origin access is disabled"}, status_code=403)
    if request.method == "POST" and request.headers.get("x-importer-client") != "local-ui":
        return JSONResponse({"detail": "Missing local client header"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response


def strict_json(value):
    if not isinstance(value, str) or len(value) > 65536:
        raise ValueError("Schema/mapping must be JSON text of at most 64 KiB")
    def invalid_constant(value):
        raise ValueError("Non-finite JSON constants are not allowed")
    return json.loads(value, parse_constant=invalid_constant)


async def decode_upload(request):
    # Bound the actual stream BEFORE multipart parsing or temporary file spooling.
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > MAX_REQUEST:
            raise HTTPException(413, "Upload request exceeds 10 MiB plus metadata allowance")
        payload.extend(chunk)
    used = False
    async def receive():
        nonlocal used
        if used:
            return {"type": "http.request", "body": b"", "more_body": False}
        used = True
        return {"type": "http.request", "body": bytes(payload), "more_body": False}
    bounded = StarletteRequest(request.scope, receive)
    async with bounded.form(max_files=1, max_fields=7, max_part_size=65536) as form:
        allowed = {"file", "schema", "mapping", "sheet", "encoding", "delimiter", "output"}
        if set(form) - allowed or len(form.multi_items()) != len(form):
            raise HTTPException(422, "Unknown or duplicate form fields")
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise HTTPException(422, "One file is required")
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "File exceeds 10 MiB")
        try:
            schema = strict_json(form.get("schema"))
            mapping = strict_json(form["mapping"]) if form.get("mapping") else None
        except (ValueError, TypeError) as error:
            raise HTTPException(422, str(error)) from None
        options = {}
        for name in ["sheet", "encoding", "delimiter", "output"]:
            value = form.get(name)
            if value is not None and (not isinstance(value, str) or len(value) > 200):
                raise HTTPException(422, "Invalid import option")
            options[name] = value or None
        if options["encoding"] not in {None, "utf-8-sig", "utf-8", "cp1252", "utf-16"}:
            raise HTTPException(422, "Unsupported encoding")
        if options["output"] not in {None, "json", "csv"}:
            raise HTTPException(422, "Output must be json or csv")
        return data, file.filename or "", schema, mapping, options


def perform_import(data, filename, schema, mapping, options):
    table = read_table(data, filename, sheet=options["sheet"],
                       encoding=options["encoding"] or "utf-8-sig", delimiter=options["delimiter"])
    result = normalize(table, schema, mapping)
    result["headers"] = table.headers
    return result


@app.post("/api/import")
async def import_file(request: Request):
    args = await decode_upload(request)
    try:
        result = await run_in_threadpool(perform_import, *args)
    except (ValueError, TypeError, KeyError, LookupError) as error:
        raise HTTPException(422, str(error)) from None
    except Exception:
        # Parser exceptions must not expose file internals or server traces.
        raise HTTPException(422, "Workbook could not be read; check format, encryption and integrity") from None
    if args[-1]["output"] == "csv":
        return Response(export_csv(result), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="normalized.csv"'})
    return JSONResponse(result)


@app.get("/health")
def health():
    return {"status": "ok", "storage": "stateless", "max_file_bytes": MAX_BYTES}


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/app.js")
def javascript():
    return FileResponse(ROOT / "web" / "app.js", media_type="application/javascript")


@app.get("/style.css")
def stylesheet():
    return FileResponse(ROOT / "web" / "style.css", media_type="text/css")


@app.get("/example/{kind}")
def example(kind: str):
    if kind not in {"schema.json", "synthetic.csv"}:
        raise HTTPException(404)
    return FileResponse(ROOT / "examples" / kind)
