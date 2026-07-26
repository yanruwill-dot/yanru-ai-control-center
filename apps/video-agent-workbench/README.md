# 一键追爆 AI 视频工作台

这是一个真正在本机运行的视频生产工作台，不是静态展示页。

## 能做什么

- 上传或选择本地视频素材。
- 用 Whisper 生成机器转写。
- 用 FFmpeg 检测并删除长静音，保留自然呼吸边缘。
- 用 Edge Neural TTS 生成中文配音；网络不可用时自动降级 macOS 本地声音。
- 自动读取本机已验证的“颜汝 Moss”个人音色，并用它生成真实配音。
- 上传 10 秒到 5 分钟的 MP3/M4A/WAV 声音样本，通过 MiniMax 创建新的克隆音色。
- 选择“稳重原片、智能轻推镜、呼吸聚焦、节奏冲击”动效 Skill，逐帧写入最终 MP4。
- 选择“经典口播、剪映感大字弹跳、开拍感口播重点、卡点快切冲击字幕、知识口播关键词高亮”剪辑模板。
- 按配音时长生成字幕、标题层、1080×1920 竖屏 MP4、封面和联系表。
- 每个任务保留 `status.json`、`pipeline.log`、字幕、封面、成片和项目 JSON。

## 启动

双击 `start.command`，或在终端运行：

```bash
cd "apps/video-agent-workbench"
python3 app.py --host 127.0.0.1 --port 8788
```

打开 `http://127.0.0.1:8788`。

## 真实边界

- 声音克隆优先调用 `~/.codex/bin/minimax-voice-clone`；新机器需要配置自己的 MiniMax API Key。
- 克隆声音必须属于本人或已获授权。点击克隆会调用云端服务，可能产生费用；只上传到本机并未创建音色。
- 剪辑模板基于 GitHub 公开实现提炼，代码证据见 `EDITING_STYLE_RESEARCH.md`；不包含商业软件的私有模板或素材。
- 已有“颜汝 Moss”音色通过 AuraStd 兼容 TTS 生成；新克隆音色通过 MiniMax 官方 TTS 使用。
- “AI”能力还包括 Whisper 语音识别和 Edge Neural TTS；脚本文案允许人工编辑，避免模型胡编业务事实。
- 自动剪辑目前基于音频静音，不会擅自删除语义内容。
- 工作台会生成发布素材，不会在没有明确命令时自动发布到外部平台。
- 参考视频只迁移结构和节奏，最终脚本与素材应确认原创或已授权。

## 测试

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile app.py pipeline.py voice_clone.py
```

本仓库公开版不包含用户声音、视频素材、运行记录或密钥。下载后使用自己的授权素材完成验证。
