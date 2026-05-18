# TOEFL Listen & Repeat Extractor

If you have TOEFL Speaking exam audio recordings along with answer files in PDF, DOCX, or TXT format, and you find it difficult to maintain long-term practice of Listen & Repeat questions due to frequently switching files and opening multiple windows, try this technique!

Simply tell your Agent: `The answers for TOEFL Speaking Listen & Repeat questions are in xxx.pdf, and the audio is xxx.mp3. Help me create Anki flashcards for inputting answers.` Your Agent will know how to operate, with batch mode support. Then, just import a single CSV file into Anki, and you can practice listening and repeating with real exam questions anytime, anywhere, following your personal forgetting curve. Isn't that simple? Give it a try!

If you want to use the tool below but have no programming background, simply show `Readme.md` and `SKILL.md` to your Agent. It will confirm your needs during the conversation and generate the CSV file for you.

If you still can't figure it out, refer to the CSV files and audio clips already extracted by the author (to be updated, will use cloud storage), and import them directly into Anki.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

> A tool for extracting TOEFL Speaking "Listen & Repeat" questions from exam audio and generating Anki flashcards.

---

## 📖 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [Install whisper.cpp](#install-whispercpp)
  - [Install This Tool](#install-this-tool)
- [Usage](#usage)
- [Workflow](#workflow)
- [Output Files](#output-files)
- [Manual Override](#manual-override)
- [Validation & Troubleshooting](#validation--troubleshooting)
- [FAQ](#faq)
- [Multilingual Docs](#multilingual-docs)
- [License](#license)

---

## Overview

This tool uses an **answer-driven workflow**:

1. Extract standard repeat sentences from PDF/DOCX/TXT answer files
2. Generate word-level timestamps using `whisper.cpp`
3. Align each answer sentence to audio timestamps
4. Cut one audio clip per sentence
5. Generate Anki CSV import files with `[sound:filename.mp3]`

This approach is more stable than silence-based segmentation or Whisper's automatic sentence chunking, as Whisper may unpredictably merge or split sentences.

---

## Installation

### Prerequisites

Before running this tool, ensure the following command-line tools are installed:

| Tool | Purpose | Installation |
|------|---------|--------------|
| `ffmpeg` | Audio conversion and cutting | `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux) |
| `whisper.cpp` | English speech recognition (with word timestamps) | See [Install whisper.cpp](#install-whispercpp) below |
| `pdftotext` | PDF answer file extraction | `brew install poppler` (macOS) / `apt install poppler-utils` (Linux) |
| `pandoc` | DOCX answer file extraction (optional) | `brew install pandoc` (macOS) / `apt install pandoc` (Linux) |

### Install whisper.cpp

`whisper.cpp` is a high-performance C/C++ implementation of OpenAI's Whisper model, supporting Apple Silicon, CUDA, Vulkan, and more.

#### 1. Clone the repository

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
```

#### 2. Download a model

Download a model converted to `ggml` format (recommended: `base.en`):

```bash
sh ./models/download-ggml-model.sh base.en
```

Available models:

| Model | Disk Size | Memory Usage |
|------|-----------|--------------|
| tiny | 75 MiB | ~273 MB |
| base | 142 MiB | ~388 MB |
| small | 466 MiB | ~852 MB |
| medium | 1.5 GiB | ~2.1 GB |
| large | 2.9 GiB | ~3.9 GB |

#### 3. Build whisper.cpp

**macOS (Apple Silicon / Intel):**

```bash
# Basic build
cmake -B build
cmake --build build -j --config Release

# Apple Silicon with Core ML acceleration (recommended)
cmake -B build -DWHISPER_COREML=1
cmake --build build -j --config Release
```

**Linux:**

```bash
cmake -B build
cmake --build build -j --config Release
```

**NVIDIA GPU (CUDA acceleration):**

```bash
cmake -B build -DGGML_CUDA=1
cmake --build build -j --config Release
```

**Other platforms:** See [whisper.cpp official docs](https://github.com/ggml-org/whisper.cpp).

#### 4. Verify installation

```bash
./build/bin/whisper-cli -f samples/jfk.wav
```

### Install This Tool

```bash
# Clone this repository
git clone https://github.com/Xiaon-Junf/Anki_toefl_listen_repeat_extractor_skill.git
cd Anki_toefl_listen_repeat_extractor_skill

# Install Python dependencies (if needed)
# pip install -r requirements.txt
```

---

## Usage

### Basic Command

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/ggml-base.en.bin" \
  --collection-media "/path/to/Anki2/Profile/collection.media" \
  --combined-csv "/path/to/output/ListenRepeat_All.csv"
```

### Parameter Reference

| Parameter | Description | Example |
|-----------|-------------|---------|
| `exam-root` | Root directory of exam folders | `"/Users/me/TOEFL/Exams"` |
| `--output-root` | Output directory | `"/Users/me/TOEFL/Output"` |
| `--whisper-cli` | Path to whisper-cli executable | `"/Users/me/whisper.cpp/build/bin/whisper-cli"` |
| `--model` | Path to ggml model file | `"/Users/me/whisper.cpp/models/ggml-base.en.bin"` |
| `--collection-media` | Anki collection.media folder path (optional) | `"/Users/me/Library/Application Support/Anki2/User/collection.media"` |
| `--combined-csv` | Combined CSV output path (optional) | `"/Users/me/TOEFL/ListenRepeat_All.csv"` |

### Input Folder Structure

```
exam-root/
  1.21 Test A/
    SpeakingModule1.mp3
    answer.pdf
  2.4 Test/
    speaking part1.zip
    answer.docx
```

The script automatically searches each exam folder for:
- **Speaking audio**: filenames containing `speaking` or `口语`, supporting `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, `.zip`
- **Answer files**: filenames containing `answer`, `答案`, or `参考答案`, supporting `.pdf`, `.docx`, `.txt`
- If both `part1` and `part2` exist, `part1` is preferred (as Listen & Repeat questions are usually in the first part)

---

## Workflow

```
┌─────────────────┐
│ Read Answer    │
│ File           │
│ (PDF/DOCX/TXT) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extract Repeat  │
│ Sentences       │
│ (7 standard     │
│  answers)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ whisper.cpp     │
│ Transcription   │
│ (word-level     │
│  timestamps)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Sentence        │
│ Alignment       │
│ (Answer ↔       │
│  Timestamps)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cut Audio       │
│ Clips           │
│ (one mp3 per    │
│  sentence)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Anki   │
│ CSV             │
│ [sound:xxx.mp3] │
└─────────────────┘
```

---

## Output Files

Each exam folder produces:

```
output/
  Exam Name/
    clips/
      toefl_repeat_examname_q01.mp3
      toefl_repeat_examname_q02.mp3
      ...
      manifest.csv          # sentence text, time range, alignment score, filename
    ExamName_ListenRepeat_Anki.csv  # Anki import file
```

Batch outputs:
- `batch_report.csv` — contains `ok`, `skipped`, `error` statuses with reasons
- `ListenRepeat_All.csv` — combined CSV for all exams (if `--combined-csv` is specified)

### Anki CSV Format

```csv
#notetype:Basic (type in the answer)
Front,Back,Source,Tags
"[sound:toefl_repeat_examname_q01.mp3]","First repeat sentence.","Exam Name / ListenRepeat / Q01","TOEFL repeat"
```

---

## Manual Override

If the answer file doesn't match the audio, or OCR extraction fails, create a JSON manual override file:

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

Run with:

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/model.bin" \
  --manual-sentences-json "/path/to/manual_sentences.json"
```

---

## Validation & Troubleshooting

### Post-Run Checklist

1. Open `batch_report.csv` and only import exams with `status=ok`
2. Inspect `manifest.csv` for each problematic exam
3. Spot-check the first and last clips of several exams
4. If the first words are clipped, increase `--lead-pad` and re-run
5. If the report shows alignment failure, check if the answer file belongs to the same audio; use `--manual-sentences-json` when needed

### Common Parameter Adjustments

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--lead-pad` | 0.45 | Time to preserve before the first aligned word (seconds), prevents clipping |
| `--tail-pad` | 0.08 | Time to preserve after the last aligned word (seconds) |

If the beginning is still clipped, try `--lead-pad 0.65`.

---

## FAQ

**Q: Why use an answer-driven approach instead of letting Whisper segment automatically?**
A: Whisper may merge or split sentences unpredictably, resulting in inaccurate timestamps. Using standard answers as the baseline ensures precise boundaries for each sentence.

**Q: What audio formats are supported?**
A: `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, and `.zip` files containing these audio formats.

**Q: What hardware configuration is needed?**
A: The base model (base.en) runs smoothly on Apple Silicon. For other platforms, at least 4GB of RAM is recommended.

**Q: How do I update already-imported Anki cards?**
A: Keep the filenames unchanged, re-run the script with `--collection-media`, and the new audio will automatically overwrite the old files in `collection.media`.

---

## Multilingual Docs

- [中文 (Chinese)](./Readme.md)
- [日本語 (Japanese)](./README_JA.md)
- [한국어 (Korean)](./README_KO.md)

---

## License

This project is licensed under the [MIT License](./LICENSE).

---

## Acknowledgments

- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) — High-performance C/C++ implementation of OpenAI Whisper
- [Anki](https://apps.ankiweb.net/) — Powerful spaced repetition software
