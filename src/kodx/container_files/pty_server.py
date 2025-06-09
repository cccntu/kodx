"""PTY Server for CodexShell - runs inside container to provide PTY functionality"""

import asyncio
import logging
import os
import pty
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
PORT = 1384


class OpenRequest(BaseModel):
    """Request to open a new process."""

    cmd: list[str]
    env: dict[str, str]
    cwd: str | None = None


class RawResponse(Response):
    media_type = "application/octet-stream"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipes = {}
    try:
        yield
    finally:
        for pipe in app.state.pipes.values():
            try:
                os.close(pipe)
            except Exception:
                pass


app = FastAPI(lifespan=lifespan)


def get_env(request: OpenRequest) -> dict[str, str]:
    # Start with a copy of the current environment variables
    env = os.environ.copy()

    # Update with specific defaults and any variables from the request
    env.update(
        {
            "TERM": "xterm",
            "COLUMNS": "80",
            "LINES": "24",
            **request.env,
        }
    )

    return env


@app.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/open")
async def open(request: OpenRequest) -> int:
    """Start a new process and return the PID."""
    master, slave = pty.openpty()
    os.set_blocking(master, False)

    if request.cwd and not os.path.isabs(request.cwd):
        raise HTTPException(status_code=400, detail=f"CWD must be an absolute path. Received: '{request.cwd}'")

    env = get_env(request)

    try:
        # Start the process with PTY
        process = subprocess.Popen(
            request.cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
            text=False,
            env=env,
            cwd=request.cwd,
        )
        os.close(slave)
    except Exception as e:
        logger.exception("Failed to open process")
        try:
            os.close(master)
            os.close(slave)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"Failed to create process: {e}") from e

    app.state.pipes[process.pid] = master
    return process.pid


@app.post("/read/{pid}")
async def read(pid: int, request: Request) -> RawResponse:
    pipe = app.state.pipes.get(pid)
    if pipe is None:
        raise HTTPException(status_code=404, detail=f"Process not found: {pid}")

    try:
        size = int(await request.body())
        data = bytearray()

        # Read available data up to size
        deadline = asyncio.get_event_loop().time() + 1.0  # Max 1 second per read

        while size > 0 and asyncio.get_event_loop().time() < deadline:
            try:
                chunk = os.read(pipe, min(size, 4096))
                if chunk:
                    size -= len(chunk)
                    data.extend(chunk)
                else:
                    break
            except BlockingIOError:
                await asyncio.sleep(0.01)

        return RawResponse(content=bytes(data))
    except ValueError as e:
        logger.exception("Failed to parse size")
        raise HTTPException(status_code=400, detail=f"Failed to parse size: {e}") from e


@app.post("/write/{pid}")
async def write(pid: int, request: Request) -> int:
    pipe = app.state.pipes.get(pid)
    if pipe is None:
        raise HTTPException(status_code=404, detail=f"Process not found: {pid}")

    try:
        data = await request.body()
        size = os.write(pipe, data)
        return size
    except Exception as e:
        logger.exception("Failed to write to pipe")
        raise HTTPException(status_code=409, detail=f"Failed to write: {e}") from e


@app.post("/kill/{pid}")
async def kill(pid: int) -> None:
    pipe = app.state.pipes.pop(pid, None)
    if pipe is None:
        raise HTTPException(status_code=404, detail=f"Process not found: {pid}")

    try:
        os.close(pipe)
        # Also try to kill the process
        try:
            os.kill(pid, 15)  # SIGTERM
        except ProcessLookupError:
            pass
    except Exception as e:
        logger.exception("Failed to close pipe")
        raise HTTPException(status_code=409, detail=f"Failed to close: {e}") from e


@app.post("/write_file/{file_path:path}")
async def write_file(file_path: str, request: Request) -> dict:
    """Write content to a file."""
    try:
        content = await request.body()

        # Ensure parent directory exists
        import pathlib

        pathlib.Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, "wb") as f:
            f.write(content)

        return {"status": "success", "path": file_path, "size": len(content)}
    except Exception as e:
        logger.exception("Failed to write file")
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}") from e


@app.get("/read_file/{file_path:path}")
async def read_file(file_path: str) -> Response:
    """Read content from a file."""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            content = f.read()

        return Response(content=content, media_type="application/octet-stream")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to read file")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}") from e


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="error")


if __name__ == "__main__":
    main()
