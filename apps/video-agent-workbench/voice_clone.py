from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path


MINIMAX_DIR = Path.home() / ".codex" / "minimax"
ENV_FILE = MINIMAX_DIR / ".env"
CLONE_BIN = Path.home() / ".codex" / "bin" / "minimax-voice-clone"
TTS_BIN = Path.home() / ".codex" / "bin" / "minimax-tts"
OFFICIAL_TTS_URL = "https://api.minimax.io/v1/t2a_v2"
AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav"}


class VoiceCloneError(RuntimeError):
    pass


def load_local_env() -> dict[str, str]:
    values = dict(os.environ)
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), value.strip().strip("\"'"))
    return values


def audio_probe(path: Path) -> dict:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise VoiceCloneError(f"声音样本不存在：{path}")
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        raise VoiceCloneError("声音样本仅支持 MP3、M4A、WAV")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise VoiceCloneError("声音样本不能超过 20 MB")
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise VoiceCloneError("无法读取声音样本，请换一个清晰的音频文件")
    duration = float(result.stdout.strip())
    if not 10 <= duration <= 300:
        raise VoiceCloneError(f"声音样本需 10 秒到 5 分钟，当前 {duration:.1f} 秒")
    return {
        "path": str(path),
        "duration": duration,
        "bytes": path.stat().st_size,
        "format": path.suffix.lower().lstrip("."),
    }


def voice_id_for(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_-").lower()
    if not slug or not slug[0].isalpha():
        slug = "voice"
    return f"{slug}_{time.strftime('%Y%m%d_%H%M%S')}"


def engine_status() -> dict:
    env = load_local_env()
    configured = bool(env.get("MINIMAX_API_KEY"))
    return {
        "provider": "MiniMax Voice Clone",
        "configured": configured,
        "clone_enabled": configured and CLONE_BIN.is_file() and TTS_BIN.is_file(),
        "sample_rule": "10 秒到 5 分钟，MP3/M4A/WAV，不超过 20 MB",
    }


def builtin_moss_profile() -> dict | None:
    env = load_local_env()
    voice_id = env.get("MINIMAX_VOICE_ID")
    if not voice_id or not TTS_BIN.is_file():
        return None
    return {
        "id": f"moss:{voice_id}",
        "voice_id": voice_id,
        "name": "颜汝 Moss · 已验证个人音色",
        "provider": "AuraStd",
        "ready": True,
        "builtin": True,
    }


def list_voice_profiles(voices_dir: Path) -> list[dict]:
    profiles: list[dict] = []
    moss = builtin_moss_profile()
    if moss:
        profiles.append(moss)
    for path in sorted(voices_dir.glob("*/profile.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        profile["id"] = f"minimax:{profile['voice_id']}"
        profile["ready"] = True
        profiles.append(profile)
    return profiles


def clone_voice(
    sample: Path,
    name: str,
    voices_dir: Path,
    preview_text: str = "这是我的 AI 克隆音色，现在可以直接用于视频配音。",
) -> dict:
    if not engine_status()["clone_enabled"]:
        raise VoiceCloneError("MiniMax 声音克隆引擎未配置")
    sample_info = audio_probe(sample)
    voice_id = voice_id_for(name)
    profile_dir = voices_dir / voice_id
    profile_dir.mkdir(parents=True, exist_ok=False)
    preview = profile_dir / "preview.mp3"
    command = [
        str(CLONE_BIN),
        "--audio", str(sample),
        "--voice-id", voice_id,
        "--preview-text", preview_text,
        "--preview-out", str(preview),
        "--noise-reduction",
        "--volume-normalization",
        "--no-save-default",
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise VoiceCloneError((result.stderr or result.stdout or "声音克隆失败")[-1200:])
    if not preview.exists():
        synthesize_minimax(preview_text, voice_id, preview, provider="minimax")
    profile = {
        "voice_id": voice_id,
        "name": name.strip() or "我的克隆音色",
        "provider": "MiniMax",
        "created_at": time.time(),
        "sample": sample_info,
        "preview": str(preview),
    }
    (profile_dir / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {**profile, "id": f"minimax:{voice_id}", "ready": True}


def synthesize_minimax(text: str, voice_id: str, output: Path, provider: str) -> Path:
    if not TTS_BIN.is_file():
        raise VoiceCloneError("未找到 MiniMax 配音工具")
    env = load_local_env()
    if provider == "minimax":
        env["MINIMAX_TTS_URL"] = OFFICIAL_TTS_URL
    command = [
        str(TTS_BIN), "--text", text, "--voice-id", voice_id,
        "--out", str(output), "--model", "speech-2.8-turbo",
    ]
    result = subprocess.run(command, text=True, capture_output=True, env=env)
    if result.returncode or not output.exists() or output.stat().st_size < 1024:
        raise VoiceCloneError((result.stderr or result.stdout or "克隆音色配音失败")[-1200:])
    return output
