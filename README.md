# AI Subtitles

## 介绍

AI Subtitles 是一个从音频/视频转录字幕的工具，利用 OpenAI 的 Whisper 和 GPT。

特性：

* 通过 API 调用，无需本地显卡算力；
* 长音频自动切割在静音处，不会切割在说话的中间，原因是 Whisper在时间过长时效果变差，且 API 有 25 MB 文件大小限制；
* 调优的 GPT 字幕翻译 prompt；
* 支持多种音频、视频格式；
* 支持转录指定时间片段。

## Quickstart

### 安装

用 pipx 安装。

```sh
pipx install https://github.com/janzhen/ai-subtitles.git
```

或者用 pip 安装，建议安装在 virtualenv 里。

```
pip install https://github.com/janzhen/ai-subtitles.git
```

最后，在系统里安装 ffmpeg，详见“安装 ffmpeg”章节。

### 使用

设置 [OpenAI key](https://platform.openai.com/api-keys) 环境变量。

```sh
export OPENAI_API_KEY=sk-xxx
```

转录。

```sh
# 转录字幕，并翻译成中文
aisubs-transcribe -t zh-CN sample.mp4
# 查看转录结果
less sample.zh.srt

# 只转录不翻译
aisubs-transcribe sample.mp4

# 给定语言会更准确
aisubs-transcribe -l ja -t zh-CN sample.mp4

# 转录指定片段
aisubs-transcribe -t zh-CN --ss 1:00 --to 2:00 sample.mp4

# 多次执行会合并，合并前会创建备份
aisubs-transcribe -t zh-CN --ss 4:00 --to 5:00 -m sample.mp4
```

如果没有在转录的同时翻译，也可以单独执行翻译。

```sh
# 翻译字幕成中文，如果字幕已经存在，会创建备份
aisubs-translate sample.srt
less sample.zh.srt

# 翻译成指定语言
aisubs-translate -l en sample.srt

# 指定 GPT model，默认是 gpt-4-turbo
aisubs-translate -m gpt-3.5-turbo sample.srt
```

### 查看帮助

```sh
# 查看转录帮助
$ aisubs-transcribe -h

usage: aisubs-transcribe [-h] [--language LANGUAGE] [--ss SS] [--to TO]
                         [--jobs JOBS] [--silence-thresh SILENCE_THRESH]
                         [--translate-to TRANSLATE_TO]
                         [--translate-model TRANSLATE_MODEL] [--verbose]
                         audio_file

positional arguments:
  audio_file            Path to the audio file to transcribe

options:
  -h, --help            show this help message and exit
  --language LANGUAGE, -l LANGUAGE
                        Language code, e.g. zh, en, ja, ko
  --ss SS               Start time in seconds or timestamp, e.g. 10, 00:10
  --to TO               End time in seconds or timestamp, e.g. 20, 00:20
  --jobs JOBS, -j JOBS  Number of parallel jobs
  --silence-thresh SILENCE_THRESH
                        Silence threshold in dB
  --translate-to TRANSLATE_TO, -t TRANSLATE_TO
                        Language code, e.g. zh-CN, en, etc., default is zh-CN
  --translate-model TRANSLATE_MODEL, -m TRANSLATE_MODEL
                        GPT model, e.g. gpt-3.5-turbo, gpt-4-turbo, gpt-4,
                        etc., default is gpt-4-turbo
  --verbose, -v         Enable verbose logging
 
# 查看翻译帮助
$ aisubs-translate -h

usage: aisubs-translate [-h] [--language LANGUAGE] [--model MODEL] [--verbose]
                        input

Translate srt file

positional arguments:
  input                 Input srt file

options:
  -h, --help            show this help message and exit
  --language LANGUAGE, -l LANGUAGE
                        Language code, e.g. zh-CN, en, etc., default is zh-CN
  --model MODEL, -m MODEL
                        GPT model, e.g. gpt-3.5-turbo, gpt-4-turbo, gpt-4,
                        etc., default is gpt-4-turbo
  --verbose, -v         Verbose mode

```



## 安装 ffmpeg

MacOS ([homebrew](http://brew.sh)):

```bash
brew install ffmpeg
```

Linux (aptitude):

```bash
apt-get install ffmpeg
```

Windows:

1. 下载 ffmpeg [Windows binaries provided here](https://www.gyan.dev/ffmpeg/builds/)。
2. 把 `/bin` 加到 PATH 环境亦是。