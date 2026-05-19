# TOEFL 听力复述题提取器 (TOEFL Listen & Repeat Extractor)

如果你有托福口语考试的录音以及 PDF、DOCX 或 TXT 格式的答案，并且频繁切换文件和打开多个窗口让你难以保持长期能力练习复述问题，试试这个 SKILL！

只需告诉你的Agent：`托福口语考试的复述问题答案位于 xxx.pdf，音频是 xxx.mp3。帮我创建 Anki 输入答案的问答题闪卡` 你的Agent就会知道如何操作，支持批量模式。然后，只需将一个 CSV 文件导入 Anki，你就可以随时随地使用真实的考试问题，根据你的个人遗忘曲线练习听力和复述能力。这不是很简单吗？试试吧！

如果想要尝试自行使用下面的工具, 但不具备编程基础, 请你直接将 `Readme.md` 和 `SKILL.md` 丢给你的Agent看, 它会在跟你的对话中确认你的需求, 并生成CSV文件。

如果实在不会使用, 可以参考作者已经提取出的CSV和听力文件 (待更新, 将使用云盘), 直接导入至 Anki 即可。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

> 一个用于从 TOEFL 口语考试音频中提取「听力复述题」(Listen & Repeat) 并生成 Anki 记忆卡片的工具。在Linux DO上推广，等待审核通过后修改此处的链接

---

## 📖 目录

- [功能简介](#功能简介)
- [安装指南](#安装指南)
  - [安装 whisper.cpp](#安装-whispercpp)
  - [安装本工具](#安装本工具)
- [使用方法](#使用方法)
- [工作流程](#工作流程)
- [输出文件](#输出文件)
- [手动覆盖](#手动覆盖)
- [验证与排错](#验证与排错)
- [常见问题](#常见问题)
- [多语言文档](#多语言文档)
- [许可证](#许可证)

---

## 功能简介

本工具采用**答案驱动**的工作流：

1. 从 PDF/DOCX/TXT 答案文件中提取标准复述句子
2. 使用 `whisper.cpp` 生成单词级时间戳
3. 将每个答案句子与音频时间戳对齐
4. 逐句切割音频
5. 生成包含 `[sound:filename.mp3]` 的 Anki CSV 导入文件

这种方法比基于静音检测或 Whisper 自动分句更稳定，因为 Whisper 可能会不可预测地合并或拆分句子。

---

## 安装指南

### 前置依赖

请你先使用以下命令安装这几个skills (from anthropics), 不然你的Agent大概率不知道如何读取docx或pdf中的内容:
```bash
npx add-skill https://github.com/anthropics/skills/tree/main/skills/pdf
npx add-skill https://github.com/anthropics/skills/tree/main/skills/docx
```

在运行本工具之前，请确保系统已安装以下命令行工具：

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| `ffmpeg` | 音频转换与切割 | `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux) |
| `whisper.cpp` | 英文语音识别（带单词时间戳） | 见下方 [安装 whisper.cpp](#安装-whispercpp) |
| `pdftotext` | PDF 答案文件提取 | `brew install poppler` (macOS) / `apt install poppler-utils` (Linux) |
| `pandoc` | DOCX 答案文件提取（可选） | `brew install pandoc` (macOS) / `apt install pandoc` (Linux) |

### 安装 whisper.cpp

`whisper.cpp` 是 OpenAI Whisper 模型的高性能 C/C++ 实现，支持 Apple Silicon、CUDA、Vulkan 等多种加速方式。

#### 1. 克隆仓库

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
```

#### 2. 下载模型

下载转换为 `ggml` 格式的模型（推荐 `base.en`）：

```bash
sh ./models/download-ggml-model.sh base.en
```

可选模型：

| 模型 | 磁盘大小 | 内存占用 |
|------|---------|---------|
| tiny | 75 MiB | ~273 MB |
| base | 142 MiB | ~388 MB |
| small | 466 MiB | ~852 MB |
| medium | 1.5 GiB | ~2.1 GB |
| large | 2.9 GiB | ~3.9 GB |

#### 3. 编译 whisper.cpp

**macOS (Apple Silicon / Intel):**

```bash
# 基础编译
cmake -B build
cmake --build build -j --config Release

# Apple Silicon 启用 Core ML 加速（推荐）
cmake -B build -DWHISPER_COREML=1
cmake --build build -j --config Release
```

**Linux:**

```bash
cmake -B build
cmake --build build -j --config Release
```

**NVIDIA GPU (CUDA 加速):**

```bash
cmake -B build -DGGML_CUDA=1
cmake --build build -j --config Release
```

**其他平台:** 详见 [whisper.cpp 官方文档](https://github.com/ggml-org/whisper.cpp)。

#### 4. 验证安装

```bash
./build/bin/whisper-cli -f samples/jfk.wav
```

### 安装本工具

```bash
npx add-skill https://github.com/Xiaon-Junf/Anki_toefl_listen_repeat_extractor_skill
```

或:

```bash
# 克隆本仓库
git clone https://github.com/Xiaon-Junf/Anki_toefl_listen_repeat_extractor_skill.git
cd Anki_toefl_listen_repeat_extractor_skill

# 安装 Python 依赖（如有需要）
# pip install -r requirements.txt
```

---

## 使用方法

### 基本命令

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/ggml-base.en.bin" \
  --collection-media "/path/to/Anki2/Profile/collection.media" \
  --combined-csv "/path/to/output/ListenRepeat_All.csv"
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `exam-root` | 考试文件夹根目录 | `"/Users/me/TOEFL/Exams"` |
| `--output-root` | 输出目录 | `"/Users/me/TOEFL/Output"` |
| `--whisper-cli` | whisper-cli 可执行文件路径 | `"/Users/me/whisper.cpp/build/bin/whisper-cli"` |
| `--model` | ggml 模型文件路径 | `"/Users/me/whisper.cpp/models/ggml-base.en.bin"` |
| `--collection-media` | Anki collection.media 文件夹路径（可选） | `"/Users/me/Library/Application Support/Anki2/User/collection.media"` |
| `--combined-csv` | 合并后的 CSV 输出路径（可选） | `"/Users/me/TOEFL/ListenRepeat_All.csv"` |

### 输入文件夹结构

```
exam-root/
  1.21 Test A/
    SpeakingModule1.mp3
    answer.pdf
  2.4 Test/
    speaking part1.zip
    answer.docx
```

脚本会自动搜索每个考试文件夹中的：
- **口语音频**: 文件名包含 `speaking` 或 `口语`，支持 `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, `.zip`
- **答案文件**: 文件名包含 `answer`, `答案`, 或 `参考答案`，支持 `.pdf`, `.docx`, `.txt`
- 如果同时存在 `part1` 和 `part2`，优先使用 `part1`（因为复述题通常在第一部分）

---

## 工作流程

```
┌─────────────────┐
│  读取答案文件    │
│ (PDF/DOCX/TXT) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 提取复述句子     │
│ (7句标准答案)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ whisper.cpp 转录 │
│ (单词级时间戳)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  句子对齐匹配    │
│ (答案↔时间戳)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   切割音频片段   │
│ (每句一个mp3)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  生成 Anki CSV  │
│ [sound:xxx.mp3] │
└─────────────────┘
```

---

## 输出文件

每个考试文件夹输出：

```
output/
  Exam Name/
    clips/
      toefl_repeat_examname_q01.mp3
      toefl_repeat_examname_q02.mp3
      ...
      manifest.csv          # 句子文本、时间范围、对齐分数、文件名
    ExamName_ListenRepeat_Anki.csv  # Anki 导入文件
```

批量输出：
- `batch_report.csv` — 包含 `ok`, `skipped`, `error` 状态及原因
- `ListenRepeat_All.csv` — 所有考试的合并 CSV（如指定 `--combined-csv`）

### Anki CSV 格式

```csv
#notetype:Basic (type in the answer)
Front,Back,Source,Tags
"[sound:toefl_repeat_examname_q01.mp3]","First repeat sentence.","Exam Name / ListenRepeat / Q01","TOEFL repeat"
```

---

## 手动覆盖

如果答案文件与音频不匹配，或 OCR 提取失败，可以创建 JSON 手动覆盖文件：

```json
{
  "Exam Folder Name": [
    "First repeat sentence.",
    "Second repeat sentence.",
    "Third repeat sentence.",
    "Fourth repeat sentence.",
    "Fifth repeat sentence.",
    "Sixth repeat sentence.",
    "Seventh repeat sentence."
  ]
}
```

运行命令：

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/model.bin" \
  --manual-sentences-json "/path/to/manual_sentences.json"
```

---

## 验证与排错

### 运行后检查清单

1. 打开 `batch_report.csv`，只导入 `status=ok` 的考试
2. 检查每个问题考试的 `manifest.csv`
3. 抽查几个考试的首尾音频片段
4. 如果开头单词被截断，增加 `--lead-pad` 参数重新运行
5. 如果报告提示对齐失败，检查答案文件是否属于同一套音频；必要时使用 `--manual-sentences-json`

### 常用参数调整

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `--lead-pad` | 0.45 | 首词前保留时间（秒），防止开头被截断 |
| `--tail-pad` | 0.08 | 尾词后保留时间（秒） |

如果开头仍被截断，尝试 `--lead-pad 0.65`。

---

## 常见问题

**Q: 为什么使用答案驱动而不是直接让 Whisper 分句？**
A: Whisper 可能会合并或拆分句子，导致时间戳不准确。使用标准答案作为基准可以确保每句话的边界精确。

**Q: 支持哪些音频格式？**
A: `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`，以及包含这些音频的 `.zip` 文件。

**Q: 需要什么样的硬件配置？**
A: 基础模型（base.en）在 Apple Silicon 上运行流畅，其他平台建议至少 4GB 内存。

**Q: 如何更新已导入 Anki 的卡片？**
A: 保持文件名不变，重新运行脚本并指定 `--collection-media`，新音频会自动覆盖 `collection.media` 中的旧文件。

---

## 多语言文档

- [English (英文)](./README_EN.md)
- [日本語 (日文)](./README_JA.md)
- [한국어 (韩文)](./README_KO.md)

---

## 许可证

本项目采用 [MIT 许可证](./LICENSE)。

---

## 致谢

- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) — OpenAI Whisper 的高性能 C/C++ 实现
- [Anki](https://apps.ankiweb.net/) — 强大的间隔重复记忆软件
