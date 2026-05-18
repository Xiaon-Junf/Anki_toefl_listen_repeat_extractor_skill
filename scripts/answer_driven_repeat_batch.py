#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import difflib
import html
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree


MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".mov"}
ANSWER_SUFFIXES = {".pdf", ".docx", ".txt"}


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=True)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def normalize_word(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def normalize_answer_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("e-mail", "email")
    text = re.sub(r"\bAPP\b", "app", text)
    text = text.replace("WiFi", "Wi-Fi")
    text = text.replace("℃", " degrees Celsius")
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    if text and text[-1] not in ".!?":
        text += "."
    return text


def exam_code_from_name(name: str) -> str:
    safe = []
    for ch in name:
        if ch.isascii() and ch.isalnum():
            safe.append(ch.lower())
        elif ch in ".-_":
            safe.append(ch)
    code = "".join(safe).replace(".", "_").strip("_")
    return code or "exam"


def candidate_priority(path: Path) -> tuple[int, int, int, str]:
    name = path.name.lower()
    part1 = 0 if re.search(r"part[\s_-]*1", name) else 1
    speaking = 0 if ("speaking" in name or "口语" in path.name) else 1
    listening = 1 if ("listening" in name or "听力" in path.name) else 0
    return (part1, speaking, listening, name)


def find_speaking_source(exam_dir: Path) -> tuple[Path | None, str]:
    direct = [
        p
        for p in exam_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in MEDIA_SUFFIXES
        and ("speaking" in p.name.lower() or "口语" in p.name)
    ]
    if direct:
        return sorted(direct, key=candidate_priority)[0], "direct"

    archives = [
        p
        for p in exam_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".zip"
        and ("speaking" in p.name.lower() or "口语" in p.name)
    ]
    if archives:
        return sorted(archives, key=candidate_priority)[0], "zip"
    return None, "missing"


def find_answer_source(exam_dir: Path) -> Path | None:
    files = [p for p in exam_dir.iterdir() if p.is_file() and p.suffix.lower() in ANSWER_SUFFIXES]
    preferred = [p for p in files if "答案" in p.name or "参考答案" in p.name or "answer" in p.name.lower()]
    candidates = preferred or files
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.suffix.lower() != ".txt", p.suffix.lower() != ".docx", p.name))[0]


def prepare_audio(source: Path, source_type: str, tmp_path: Path) -> Path:
    raw_media = source
    if source_type == "zip":
        with zipfile.ZipFile(source) as zf:
            media_names = [
                name
                for name in zf.namelist()
                if not name.startswith("__MACOSX/")
                and Path(name).suffix.lower() in MEDIA_SUFFIXES
            ]
            if not media_names:
                raise RuntimeError(f"zip archive has no supported media file: {source}")
            target_name = sorted(media_names, key=lambda name: candidate_priority(Path(name)))[0]
            raw_media = tmp_path / "raw_media" / Path(target_name).name
            raw_media.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(target_name) as src, raw_media.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    wav_path = tmp_path / "input.wav"
    run(["ffmpeg", "-y", "-i", str(raw_media), "-ac", "1", "-ar", "16000", str(wav_path)])
    return wav_path


def extract_docx_text(path: Path) -> str:
    if command_exists("pandoc"):
        with tempfile.TemporaryDirectory(prefix="answer_docx_") as td:
            out = Path(td) / "answer.txt"
            run(["pandoc", str(path), "-t", "plain", "-o", str(out)])
            return out.read_text(encoding="utf-8", errors="ignore")

    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    texts = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
        elif node.tag.endswith("}p"):
            texts.append("\n")
    return " ".join(texts)


def extract_answer_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        return extract_docx_text(path)
    if suffix == ".pdf":
        if not command_exists("pdftotext"):
            raise RuntimeError("pdftotext is required for PDF answers. Install poppler or provide a .txt answer file.")
        with tempfile.TemporaryDirectory(prefix="answer_pdf_") as td:
            out = Path(td) / "answer.txt"
            run(["pdftotext", str(path), str(out)])
            return out.read_text(encoding="utf-8", errors="ignore")
    raise RuntimeError(f"unsupported answer file type: {path}")


def extract_repeat_sentences(answer_text: str, expected_count: int) -> list[str]:
    lines = [line.rstrip() for line in answer_text.replace("\f", "\n").splitlines()]
    section_idx = next((i for i, line in enumerate(lines) if "Speaking" in line or "口语" in line), None)
    if section_idx is None:
        section_idx = next((i for i, line in enumerate(lines) if "Listen and repeat" in line), None)
    if section_idx is None:
        raise RuntimeError("answer text has no Speaking/listen-and-repeat section")

    collected: list[tuple[int, str]] = []
    current_no: int | None = None
    current_parts: list[str] = []

    for raw_line in lines[section_idx + 1 :]:
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r"\b(Writing|Listening|Reading)\b", line, re.I) or any(token in line for token in ["写作", "听力", "阅读"]):
            break
        if "小红书" in line:
            continue

        match = re.match(r"^([1-9]\d*)[.)、]\s*(.*)$", line)
        if match:
            number = int(match.group(1))
            if current_no is not None:
                collected.append((current_no, " ".join(current_parts).strip()))
            if number > expected_count:
                break
            current_no = number
            current_parts = [match.group(2).strip()]
            continue

        if current_no is not None:
            current_parts.append(line)

    if current_no is not None:
        collected.append((current_no, " ".join(current_parts).strip()))

    collected = [(no, normalize_answer_text(text)) for no, text in collected if text.strip()]
    collected = [(no, text) for no, text in collected if 1 <= no <= expected_count]
    collected.sort(key=lambda item: item[0])
    sentences = [text for _, text in collected[:expected_count]]
    if len(sentences) != expected_count:
        raise RuntimeError(f"expected {expected_count} repeat sentences, extracted {len(sentences)}")
    return sentences


def load_manual_sentences(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for exam_name, sentences in data.items():
        if not isinstance(sentences, list):
            raise RuntimeError(f"manual sentence entry must be a list: {exam_name}")
        result[exam_name] = [normalize_answer_text(str(item)) for item in sentences]
    return result


def transcribe_words(audio_path: Path, whisper_cli: Path, model: Path, output_prefix: Path, threads: int) -> Path:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(whisper_cli),
            "-m",
            str(model),
            "-f",
            str(audio_path),
            "-l",
            "en",
            "-t",
            str(threads),
            "-oj",
            "-of",
            str(output_prefix),
            "-np",
            "-ml",
            "1",
        ]
    )
    return Path(f"{output_prefix}.json")


def parse_word_items(json_path: Path) -> list[dict[str, float | str]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    items: list[dict[str, float | str]] = []
    for item in data.get("transcription", []):
        text = (item.get("text") or "").strip()
        offsets = item.get("offsets", {})
        start = offsets.get("from")
        end = offsets.get("to")
        norm = normalize_word(text)
        if start is None or end is None or not norm:
            continue
        items.append({"text": text, "norm": norm, "start": float(start) / 1000.0, "end": float(end) / 1000.0})
    return items


def align_sentence(
    word_items: list[dict[str, float | str]],
    sentence: str,
    min_word_index: int,
    min_score: float,
) -> tuple[float, float, int, float]:
    tokens = [normalize_word(part) for part in sentence.split()]
    tokens = [token for token in tokens if token]
    if not tokens:
        raise RuntimeError(f"cannot align empty sentence: {sentence}")

    search_items = word_items[min_word_index:]
    norms = [str(item["norm"]) for item in search_items]
    target = " ".join(tokens)
    ideal_len = len(tokens)

    best_score = 0.0
    best_span: tuple[float, float, int, float] | None = None
    for start_idx in range(len(norms)):
        min_end = min(len(norms), start_idx + max(1, ideal_len - 3))
        max_end = min(len(norms), start_idx + ideal_len + 12)
        for end_idx in range(min_end, max_end + 1):
            candidate = " ".join(norms[start_idx:end_idx])
            score = difflib.SequenceMatcher(None, target, candidate).ratio()
            if score > best_score:
                best_score = score
                best_span = (
                    float(search_items[start_idx]["start"]),
                    float(search_items[end_idx - 1]["end"]),
                    min_word_index + end_idx,
                    score,
                )

    if best_span is None or best_score < min_score:
        raise RuntimeError(f"sentence alignment failed: {sentence} (score={best_score:.2f})")
    return best_span


def export_clips(
    audio_path: Path,
    sentences: list[str],
    word_items: list[dict[str, float | str]],
    clips_dir: Path,
    lead_pad: float,
    tail_pad: float,
    min_score: float,
) -> Path:
    clips_dir.mkdir(parents=True, exist_ok=True)
    manifest = clips_dir / "manifest.csv"
    min_word_index = 0
    rows: list[dict[str, str]] = []

    for idx, sentence in enumerate(sentences, start=1):
        start, end, min_word_index, score = align_sentence(word_items, sentence, min_word_index, min_score)
        clip_start = max(0.0, start - lead_pad)
        clip_end = end + tail_pad
        audio_name = f"{audio_path.stem}_q{idx:02d}.mp3"
        run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{clip_start:.3f}",
                "-to",
                f"{clip_end:.3f}",
                "-i",
                str(audio_path),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-q:a",
                "2",
                str(clips_dir / audio_name),
            ]
        )
        rows.append(
            {
                "question_no": str(idx),
                "audio_file": audio_name,
                "start": f"{clip_start:.3f}",
                "end": f"{clip_end:.3f}",
                "align_score": f"{score:.3f}",
                "source": "listen-repeat",
                "text": sentence,
            }
        )

    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["question_no", "audio_file", "start", "end", "align_score", "source", "text"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def safe_audio_name(exam_code: str, question_no: int) -> str:
    return f"toefl_repeat_{exam_code}_q{question_no:02d}.mp3"


def build_anki_csv(
    manifest: Path,
    clips_dir: Path,
    output_csv: Path,
    exam_label: str,
    exam_code: str,
    collection_media: Path | None,
) -> None:
    with manifest.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out_rows = []
    for row in rows:
        question_no = int(row["question_no"])
        media_name = safe_audio_name(exam_code, question_no)
        if collection_media is not None:
            collection_media.mkdir(parents=True, exist_ok=True)
            shutil.copy2(clips_dir / row["audio_file"], collection_media / media_name)

        source = f"{exam_label} / ListenRepeat / Q{question_no:02d}"
        back = row["text"]
        out_rows.append(
            {
                "Front": f"{html.escape(source)}<br>[sound:{media_name}]",
                "Back": back,
                "Source": source,
                "Audio": f"[sound:{media_name}]",
                "Reference": back,
                "Tags": f"toefl repeat {exam_code} q{question_no:02d}",
            }
        )

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        handle.write("#separator:Comma\n")
        handle.write("#html:true\n")
        handle.write("#notetype:Basic (type in the answer)\n")
        handle.write("#tags column:6\n")
        handle.write("#columns:Front,Back,Source,Audio,Reference,Tags\n")
        writer = csv.DictWriter(handle, fieldnames=["Front", "Back", "Source", "Audio", "Reference", "Tags"])
        writer.writeheader()
        writer.writerows(out_rows)


def combine_csvs(csv_paths: list[Path], output_csv: Path) -> None:
    if not csv_paths:
        return
    lines_out: list[str] = []
    for idx, path in enumerate(csv_paths):
        lines = path.read_text(encoding="utf-8").splitlines()
        if idx == 0:
            lines_out.extend(lines)
        else:
            lines_out.extend(lines[6:])
    output_csv.write_text("\n".join(lines_out) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Answer-driven TOEFL Listen & Repeat audio splitter and Anki CSV builder.")
    parser.add_argument("root", type=Path, help="Folder containing one subfolder per test/exam.")
    parser.add_argument("--output-root", type=Path, required=True, help="Where per-exam clips, manifests, and CSVs are written.")
    parser.add_argument("--whisper-cli", type=Path, required=True, help="Path to whisper.cpp whisper-cli.")
    parser.add_argument("--model", type=Path, required=True, help="Path to a whisper.cpp ggml model, usually an English model.")
    parser.add_argument("--collection-media", type=Path, help="Optional Anki collection.media folder. If set, audio is copied there.")
    parser.add_argument("--combined-csv", type=Path, help="Optional path for one combined Anki CSV.")
    parser.add_argument("--manual-sentences-json", type=Path, help="Optional JSON map: exam folder name -> list of repeat sentences.")
    parser.add_argument("--expected-count", type=int, default=7, help="Expected Listen & Repeat sentence count per exam.")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--lead-pad", type=float, default=0.45, help="Seconds to keep before each aligned sentence.")
    parser.add_argument("--tail-pad", type=float, default=0.08, help="Seconds to keep after each aligned sentence.")
    parser.add_argument("--min-score", type=float, default=0.56, help="Minimum fuzzy alignment score.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    manual_sentences = load_manual_sentences(args.manual_sentences_json)

    report_rows: list[dict[str, str]] = []
    csv_paths: list[Path] = []
    exam_dirs = sorted([p for p in args.root.iterdir() if p.is_dir()], key=lambda p: p.name)

    for exam_dir in exam_dirs:
        source, source_type = find_speaking_source(exam_dir)
        answer_source = find_answer_source(exam_dir)
        exam_out = args.output_root / exam_dir.name
        exam_out.mkdir(parents=True, exist_ok=True)

        if source is None or answer_source is None:
            report_rows.append(
                {
                    "exam": exam_dir.name,
                    "status": "skipped",
                    "reason": "missing speaking audio or answer file",
                    "csv": "",
                    "answer_source": str(answer_source) if answer_source else "",
                }
            )
            continue

        try:
            with tempfile.TemporaryDirectory(prefix="toefl_repeat_") as td:
                audio_path = prepare_audio(source, source_type, Path(td))
                if exam_dir.name in manual_sentences:
                    sentences = manual_sentences[exam_dir.name]
                else:
                    sentences = extract_repeat_sentences(extract_answer_text(answer_source), args.expected_count)

                word_json = transcribe_words(
                    audio_path,
                    args.whisper_cli,
                    args.model,
                    exam_out / "transcription" / "full_words",
                    args.threads,
                )
                word_items = parse_word_items(word_json)
                manifest = export_clips(
                    audio_path,
                    sentences,
                    word_items,
                    exam_out / "clips",
                    args.lead_pad,
                    args.tail_pad,
                    args.min_score,
                )

            csv_path = exam_out / f"{exam_dir.name}_ListenRepeat_Anki.csv"
            build_anki_csv(
                manifest,
                exam_out / "clips",
                csv_path,
                exam_dir.name,
                exam_code_from_name(exam_dir.name),
                args.collection_media,
            )
            csv_paths.append(csv_path)
            report_rows.append(
                {
                    "exam": exam_dir.name,
                    "status": "ok",
                    "reason": source_type,
                    "csv": str(csv_path),
                    "answer_source": str(answer_source),
                }
            )
        except Exception as exc:  # noqa: BLE001
            report_rows.append(
                {
                    "exam": exam_dir.name,
                    "status": "error",
                    "reason": re.sub(r"\s+", " ", str(exc)).strip(),
                    "csv": "",
                    "answer_source": str(answer_source) if answer_source else "",
                }
            )

    report_csv = args.output_root / "batch_report.csv"
    with report_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["exam", "status", "reason", "csv", "answer_source"])
        writer.writeheader()
        writer.writerows(report_rows)

    if args.combined_csv is not None:
        args.combined_csv.parent.mkdir(parents=True, exist_ok=True)
        combine_csvs(csv_paths, args.combined_csv)


if __name__ == "__main__":
    main()
