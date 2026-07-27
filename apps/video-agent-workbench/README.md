# 一键追爆 AI 视频工作台

这是一个可通过 HTTPS 在线连接的视频生产工作台，不是静态展示页。

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

## 长期连接（推荐）

双击 `install-persistent.command`，或直接打开桌面的 `AI视频工作台.app`。系统会安装一个当前用户的 macOS LaunchAgent：

- 登录后自动启动。
- 进程异常退出后自动重启。
- 固定使用 `http://127.0.0.1:8788/`。
- GitHub 工作台没有 HTTPS 参数时也会自动回连这个长期引擎。

停止并移除登录项时双击 `uninstall-persistent.command`。已生成的视频和声音资料不会被删除。

## 临时 HTTPS 外网启动

双击 `start-online.command`。启动器会自动：

1. 在后台启动 Python 与 FFmpeg 生成引擎。
2. 生成本次专用的随机访问密钥。
3. 建立 Cloudflare HTTPS 隧道。
4. 打开已经连接到引擎的 GitHub 在线工作台。

停止时双击 `stop-online.command`。在线模式使用独立的 8789 端口，不会与长期 8788 引擎冲突。它不要求 Cloudflare 登录，但这台 Mac 必须保持开机。

## 仅本机启动

双击 `start.command`，或在终端运行：

```bash
cd "apps/video-agent-workbench"
python3 app.py --host 127.0.0.1 --port 8788
```

打开 `http://127.0.0.1:8788`。

## Docker 云服务器

容器内已包含 FFmpeg、中文字体和 Edge TTS：

```bash
docker build -t yanru-video-agent .
docker run --rm -p 8788:8788 \
  -e VIDEO_AGENT_API_KEY="请换成随机长密钥" \
  -e VIDEO_AGENT_ALLOWED_ORIGINS="https://yanruwill-dot.github.io" \
  yanru-video-agent
```

云服务器必须由 HTTPS 反向代理提供域名。打开工作台时通过 URL fragment 传入：

```text
https://yanruwill-dot.github.io/yanru-ai-control-center/video-agent-workbench/#api=https://你的后端域名&key=你的访问密钥
```

fragment 不会发送给 GitHub Pages，只由浏览器用于连接视频引擎。

## 真实边界

- 声音克隆优先调用 `~/.codex/bin/minimax-voice-clone`；新机器需要配置自己的 MiniMax API Key。
- 克隆声音必须属于本人或已获授权。点击克隆会调用云端服务，可能产生费用；只上传到本机并未创建音色。
- 剪辑模板基于 GitHub 公开实现提炼，代码证据见 `EDITING_STYLE_RESEARCH.md`；不包含商业软件的私有模板或素材。
- Quick Tunnel 的地址每次启动都会变化，适合个人使用和演示，不承诺云服务 SLA；永久在线需把同一 Docker 镜像部署到自己的容器服务器。
- HTTPS 模式使用随机访问密钥保护上传、生成、声音和产物接口；不要把带 `#key=` 的完整链接公开转发。
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
