#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from pipeline import PipelineError, auto_cut, probe, render_video, transcribe_source, validate_source
from voice_clone import VoiceCloneError, audio_probe, clone_voice, engine_status, list_voice_profiles


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
RUNS = ROOT / "runs"
UPLOADS = ROOT / "uploads"
VOICE_UPLOADS = ROOT / "voice-uploads"
VOICES = ROOT / "voices"
RUNS.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)
VOICE_UPLOADS.mkdir(exist_ok=True)
VOICES.mkdir(exist_ok=True)
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
GITHUB_PAGES_ORIGIN = "https://yanruwill-dot.github.io"
API_KEY = os.environ.get("VIDEO_AGENT_API_KEY", "").strip()
ALLOWED_ORIGINS = {
    item.strip()
    for item in os.environ.get("VIDEO_AGENT_ALLOWED_ORIGINS", GITHUB_PAGES_ORIGIN).split(",")
    if item.strip()
}


def save_job(job_id: str) -> None:
    path = RUNS / job_id / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        path.write_text(json.dumps(JOBS[job_id], ensure_ascii=False, indent=2), encoding="utf-8")


def update_job(job_id: str, **values) -> None:
    with LOCK:
        JOBS[job_id].update(values)
    save_job(job_id)


def run_job(job_id: str, kind: str, payload: dict) -> None:
    out_dir = RUNS / job_id
    try:
        update_job(job_id, status="running", progress=8, message="正在检查输入")
        if kind == "clone":
            update_job(job_id, progress=22, message="正在上传声音样本")
            result = clone_voice(
                Path(payload["sample_path"]),
                str(payload.get("name", "我的克隆音色")),
                VOICES,
            )
            update_job(job_id, progress=88, message="正在保存克隆音色")
        else:
            source = validate_source(payload["source_path"])
        if kind == "analyze":
            update_job(job_id, progress=32, message="正在运行 AI 转写")
            transcript = transcribe_source(source, out_dir)
            media = probe(source)
            result = {"media": media, "transcript": transcript, "run_dir": str(out_dir)}
        elif kind == "autocut":
            update_job(job_id, progress=30, message="正在检测静音和有效口播")
            output, report = auto_cut(
                source, out_dir, int(payload.get("threshold_db", -35)), float(payload.get("min_silence", 0.65))
            )
            update_job(job_id, progress=82, message="正在验证剪辑结果")
            result = {"final": str(output), "report": report, "run_dir": str(out_dir)}
        elif kind == "generate":
            update_job(job_id, progress=20, message="正在生成 AI 配音")
            result = render_video(
                source=source,
                title=str(payload.get("title", "AI 视频工作台")).strip(),
                script=str(payload.get("script", "")).strip(),
                voice=str(payload.get("voice", "zh-CN-YunxiNeural")),
                out_dir=out_dir,
                use_auto_cut=bool(payload.get("auto_cut", True)),
                threshold_db=int(payload.get("threshold_db", -35)),
                min_silence=float(payload.get("min_silence", 0.65)),
                motion_preset=str(payload.get("motion_preset", "smart_push")),
                editing_style=str(payload.get("editing_style", "classic")),
                progress=lambda value, message: update_job(job_id, progress=value, message=message)
            )
        elif kind != "clone":
            raise PipelineError("未知任务类型")
        update_job(job_id, status="completed", progress=100, message="生成完成", result=result, finished_at=time.time())
    except Exception as error:
        update_job(job_id, status="failed", message=str(error), error=repr(error), finished_at=time.time())


def create_job(kind: str, payload: dict) -> dict:
    job_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    job = {
        "id": job_id,
        "kind": kind,
        "status": "queued",
        "progress": 0,
        "message": "已进入队列",
        "created_at": time.time()
    }
    with LOCK:
        JOBS[job_id] = job
    save_job(job_id)
    threading.Thread(target=run_job, args=(job_id, kind, payload), daemon=True).start()
    return job


class Handler(BaseHTTPRequestHandler):
    server_version = "ViralVideoWorkbench/1.0"

    def send_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Video-Agent-Key")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Vary", "Origin")

    def is_authorized(self) -> bool:
        if not API_KEY:
            return True
        supplied = self.headers.get("X-Video-Agent-Key", "")
        if not supplied:
            supplied = parse_qs(urlparse(self.path).query).get("key", [""])[0]
        return hmac.compare_digest(supplied, API_KEY)

    def require_authorized(self) -> bool:
        if self.is_authorized():
            return True
        self.send_json({"ok": False, "error": "引擎访问密钥无效，请重新运行桌面启动器"}, 401)
        return False

    def send_json(self, value: dict, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2_000_000:
            raise PipelineError("JSON 请求过大")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8") or "{}")

    def serve_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith(("/api/", "/runs/", "/voices/")) and not self.require_authorized():
            return
        if path == "/api/health":
            self.send_json({
                "ok": True,
                "service": "一键追爆视频工作台",
                "version": "1.4.1",
                "voice_clone": engine_status(),
            })
            return
        if path == "/api/voices":
            self.send_json({"ok": True, "engine": engine_status(), "voices": list_voice_profiles(VOICES)})
            return
        if path == "/api/latest":
            candidates = []
            for status_file in RUNS.glob("*/status.json"):
                try:
                    job = json.loads(status_file.read_text(encoding="utf-8"))
                    if job.get("kind") == "generate" and job.get("status") == "completed":
                        candidates.append(job)
                except (OSError, json.JSONDecodeError):
                    continue
            latest = max(candidates, key=lambda item: item.get("finished_at", 0), default=None)
            self.send_json(latest or {"error": "暂无已完成任务"}, 200 if latest else 404)
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            if not re.fullmatch(r"[A-Za-z0-9-]{6,64}", job_id):
                self.send_json({"error": "任务 ID 无效"}, 400)
                return
            with LOCK:
                job = JOBS.get(job_id)
            if not job:
                status_file = RUNS / job_id / "status.json"
                if status_file.exists():
                    job = json.loads(status_file.read_text(encoding="utf-8"))
            self.send_json(job or {"error": "任务不存在"}, 200 if job else 404)
            return
        if path.startswith("/runs/"):
            relative = Path(path.removeprefix("/runs/"))
            target = (RUNS / relative).resolve()
            if RUNS.resolve() not in target.parents:
                self.send_error(403)
                return
            self.serve_file(target)
            return
        if path.startswith("/voices/"):
            relative = Path(path.removeprefix("/voices/"))
            target = (VOICES / relative).resolve()
            if VOICES.resolve() not in target.parents:
                self.send_error(403)
                return
            self.serve_file(target)
            return
        if path == "/":
            self.serve_file(STATIC / "index.html")
            return
        target = (STATIC / path.lstrip("/")).resolve()
        if STATIC.resolve() not in target.parents:
            self.send_error(403)
            return
        self.serve_file(target)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/") and not self.require_authorized():
                return
            if parsed.path == "/api/upload":
                query = parse_qs(parsed.query)
                original = Path(query.get("name", ["video.mp4"])[0]).name
                safe = re.sub(r"[^A-Za-z0-9._-]+", "-", original)
                suffix = Path(safe).suffix.lower()
                if suffix not in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
                    raise PipelineError("上传文件不是支持的视频格式")
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 2_000_000_000:
                    raise PipelineError("上传大小无效")
                target = UPLOADS / f"{uuid.uuid4().hex[:10]}-{safe}"
                with target.open("wb") as stream:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        stream.write(chunk)
                        remaining -= len(chunk)
                self.send_json({"ok": True, "path": str(target), "bytes": target.stat().st_size})
                return
            if parsed.path == "/api/upload-audio":
                query = parse_qs(parsed.query)
                original = Path(query.get("name", ["voice.wav"])[0]).name
                safe = re.sub(r"[^A-Za-z0-9._-]+", "-", original)
                if Path(safe).suffix.lower() not in {".mp3", ".m4a", ".wav"}:
                    raise PipelineError("声音样本仅支持 MP3、M4A、WAV")
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 20 * 1024 * 1024:
                    raise PipelineError("声音样本大小无效或超过 20 MB")
                target = VOICE_UPLOADS / f"{uuid.uuid4().hex[:10]}-{safe}"
                with target.open("wb") as stream:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        stream.write(chunk)
                        remaining -= len(chunk)
                info = audio_probe(target)
                self.send_json({"ok": True, **info})
                return
            if parsed.path in {"/api/analyze", "/api/autocut", "/api/generate", "/api/clone"}:
                kind = parsed.path.rsplit("/", 1)[-1]
                payload = self.read_json()
                if kind == "clone":
                    if not payload.get("consent"):
                        raise PipelineError("请确认声音属于本人或已获得授权")
                    audio_probe(Path(str(payload.get("sample_path", ""))))
                else:
                    validate_source(payload.get("source_path", ""))
                if kind == "generate":
                    if not str(payload.get("title", "")).strip():
                        raise PipelineError("标题不能为空")
                    if not str(payload.get("script", "")).strip():
                        raise PipelineError("口播文案不能为空")
                job = create_job(kind, payload)
                self.send_json({"ok": True, "job": job}, 202)
                return
            self.send_error(404)
        except (PipelineError, VoiceCloneError, ValueError, json.JSONDecodeError) as error:
            self.send_json({"ok": False, "error": str(error)}, 400)

    def log_message(self, format_text: str, *args) -> None:
        print(f"[workbench] {self.address_string()} - {format_text % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="一键追爆视频工作台")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"一键追爆视频工作台：http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
