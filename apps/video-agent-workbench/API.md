# API

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/api/health` | 引擎健康检查 |
| GET | `/api/latest` | 读取最近一次完成的生成任务 |
| GET | `/api/voices` | 读取个人与克隆音色 |
| POST | `/api/upload?name=video.mp4` | 上传原始视频字节 |
| POST | `/api/upload-audio?name=sample.wav` | 上传并验证声音样本 |
| POST | `/api/clone` | 创建声音克隆任务 |
| POST | `/api/analyze` | Whisper 转写与媒体分析 |
| POST | `/api/autocut` | 静音检测和自动剪辑 |
| POST | `/api/generate` | 配音、字幕、封面和 MP4 完整生成 |
| GET | `/api/jobs/<id>` | 查询任务状态 |
| GET | `/runs/<id>/<file>` | 获取任务产物 |

`/api/generate` 示例：

```json
{
  "source_path": "/absolute/source.mp4",
  "title": "老板真正需要的，不是一个AI工具",
  "script": "口播文案",
  "voice": "moss:<voice_id> 或 minimax:<voice_id>",
  "motion_preset": "smart_push",
  "auto_cut": true,
  "threshold_db": -35,
  "min_silence": 0.65
}
```

## 声音

```json
{
  "sample_path": "/absolute/path/sample.wav",
  "name": "我的专属音色",
  "consent": true
}
```

声音样本支持 MP3/M4A/WAV、10 秒到 5 分钟、不超过 20 MB。`consent=false` 会被拒绝。

动效可选值：`none`、`smart_push`、`breath_focus`、`beat_impact`。
