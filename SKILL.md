---
name: toefl-listen-repeat-extractor
description: Use this skill to extract TOEFL Speaking Listen & Repeat questions from exam folders and build Anki import CSVs. Prefer the answer-driven workflow: read the official answer PDF/DOCX/TXT for the exact repeat sentences, align those sentences to Speaking audio with whisper.cpp word timestamps, cut one audio clip per sentence, and export Anki CSV rows using [sound:filename.mp3]. Trigger when the user wants only Listen & Repeat / listen and repeat / 复述题 cards from TOEFL Speaking audio.
---

# TOEFL Listen & Repeat Extractor

This skill extracts only TOEFL Speaking `Listen and repeat` questions. Use the answer-driven workflow as the default and most reliable path.

## Core Idea

Do not let ASR decide the question text. Use the answer file as ground truth:

1. Extract the standard `Listen and repeat` sentences from `PDF`, `DOCX`, or `TXT`.
2. Transcribe the Speaking audio with `whisper.cpp` word-level timestamps.
3. Align each answer sentence to the word timestamps in order.
4. Cut one audio clip per sentence.
5. Build Anki CSV rows that reference `[sound:filename.mp3]`.

This is more stable than segmenting by silence or by Whisper's sentence chunks, because Whisper may merge or split sentences unpredictably.

## Required Tools

The script is portable, but the machine must provide these command-line tools:

- `ffmpeg`: converts and cuts audio.
- `whisper.cpp` `whisper-cli`: performs English transcription with word timestamps.
- A compatible `ggml` Whisper model, usually `ggml-base.en.bin` or `ggml-base.bin`.
- `pdftotext` from Poppler for PDF answers.
- `pandoc` for DOCX answers. If unavailable, the script falls back to reading basic DOCX XML.

Before running, locate:

- `WHISPER_CLI`: path to `whisper-cli`.
- `WHISPER_MODEL`: path to the `.bin` model.
- Optional `COLLECTION_MEDIA`: Anki `collection.media` folder.

## Batch Command

From this skill directory or with an absolute script path:

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/ggml-base.en.bin" \
  --collection-media "/path/to/Anki2/Profile/collection.media" \
  --combined-csv "/path/to/output/ListenRepeat_All.csv"
```

If Anki import is not needed yet, omit `--collection-media`. The CSV will still contain `[sound:...]` fields, but Anki audio playback requires the referenced files to exist in `collection.media`.

## Expected Folder Shape

The input root should contain one folder per exam:

```text
exam-root/
  1.21 Test A/
    SpeakingModule1.mp3
    answer.pdf
  2.4 Test/
    speaking part1.zip
    answer.docx
```

The script searches each exam folder for:

- Speaking audio: filenames containing `speaking` or `口语`, including `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, or `.zip`.
- Answer files: filenames containing `answer`, `答案`, or `参考答案`, including `.pdf`, `.docx`, or `.txt`.
- If `part1` and `part2` both exist, `part1` is preferred because Listen & Repeat usually lives there.

## Outputs

For each exam:

- `clips/*.mp3`: one clip per repeat sentence.
- `clips/manifest.csv`: sentence text, time range, alignment score, clip filename.
- `*_ListenRepeat_Anki.csv`: per-exam Anki import CSV.

For the batch:

- `batch_report.csv`: `ok`, `skipped`, and `error` rows with reasons.
- Optional combined CSV from `--combined-csv`.

The Anki CSV uses:

- `#notetype:Basic (type in the answer)`
- `Front`: source label plus `[sound:filename.mp3]`
- `Back` / `Reference`: the answer sentence
- `Source`: full origin label, e.g. `Exam Name / ListenRepeat / Q01`
- `Tags`: simple TOEFL repeat tags

## Existing Anki Cards

If cards have already been imported and only the audio timing is wrong, keep the filenames unchanged and overwrite audio files in `collection.media`.

The script does this automatically when rerun with the same exam folder names and `--collection-media`: it regenerates `toefl_repeat_<exam_code>_qNN.mp3` and copies those same names into `collection.media`.

Useful timing options:

- `--lead-pad 0.45`: preserves audio before the first aligned word so the first 1-2 words are not clipped.
- `--tail-pad 0.08`: preserves a small tail after the last aligned word.
- Increase `--lead-pad` if the beginning is still clipped; try `0.65` before making manual edits.

## Manual Overrides

If an answer file does not match the audio, or OCR extraction fails, create a JSON override:

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

## Validation

After a run:

1. Open `batch_report.csv`; only import exams with `status=ok`.
2. Inspect `manifest.csv` for each problem exam.
3. Spot-check the first and last clip of several exams.
4. If the first words are clipped, rerun with a larger `--lead-pad`.
5. If the report says alignment failed, check whether the answer file belongs to the same audio; use `--manual-sentences-json` when needed.

## Boundary

This skill does not solve general TOEFL Speaking question extraction. It is intentionally scoped to `Listen and repeat` cards where an answer file provides the exact target sentences.

### Notice

你在切分完毕后, 必须询问用户是否存在开头1~2个单词的音频被截断, 末尾是否被截断 (空白过长)这一类边界问题.