# 系统架构

```text
浏览器三栏工作台
       │ JSON / 原始视频流
       ▼
Python ThreadingHTTPServer
       │
       ├── Whisper：AI 转写
       ├── MiniMax Voice Clone：上传声音样本、创建专属音色
       ├── AuraStd / MiniMax TTS：颜汝 Moss 与新克隆音色配音
       ├── Edge TTS / macOS say：公共音色与本机降级
       ├── FFmpeg：静音检测、裁切、合成、编码、验证
       ├── FFmpeg zoompan：轻推镜、呼吸聚焦、节奏冲击
       └── Pillow：中文字幕层、封面、视觉资产
                    │
                    ▼
             runs/<任务ID>/
             final.mp4
             cover.jpg
             captions.srt
             project.json
             pipeline.log
```

## 数据流

1. 前端上传文件或提交本地素材路径。
2. 后端验证扩展名和文件存在性，创建独立任务目录。
3. 后台线程运行转写、自动剪辑或完整生成。
4. 前端轮询任务状态，完成后从 `/runs/` 读取视频、封面和字幕。

## 声音克隆数据流

1. `/api/upload-audio` 在本机验证格式、20 MB 上限和 10 秒到 5 分钟时长。
2. `/api/clone` 再检查授权确认，后台调用本机 MiniMax Voice Clone Skill。
3. 音色资料写入 `voices/<voice_id>/profile.json`，预览写入同目录。
4. `/api/voices` 把颜汝 Moss、已有克隆音色和公共神经音色返回工作台。
5. 生成视频时，`moss:` 走 AuraStd，`minimax:` 走 MiniMax 官方 TTS。

## 选型

- 标准库 HTTP 服务：减少安装和依赖故障。
- FFmpeg：可靠、可审计的媒体处理核心。
- Pillow：规避本机 FFmpeg 缺少 `drawtext`/`subtitles` 滤镜的问题。
- 文件式任务状态：单机工作台足够透明，可直接查看和恢复。
