# TOEFL 청취 따라말하기 문제 추출기

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

> TOEFL 스피킹 시험 오디오에서 "청취 따라말하기" 문제를 추출하고 Anki 플래시카드를 생성하는 도구입니다.

---

## 📖 목차

- [개요](#개요)
- [설치](#설치)
  - [whisper.cpp 설치](#whispercpp-설치)
  - [본 도구 설치](#본-도구-설치)
- [사용 방법](#사용-방법)
- [작업 흐름](#작업-흐름)
- [출력 파일](#출력-파일)
- [수동 오버라이드](#수동-오버라이드)
- [증 및 문제 해결](#검증-및-문제-해결)
- [자주 묻는 질문](#자주-묻는-질문)
- [다국어 문서](#다국어-문서)
- [라이선스](#라이선스)

---

## 개요

본 도구는 **정답 기반 워크플로우**를 사용합니다：

1. PDF/DOCX/TXT 정답 파일에서 표준 따라말하기 문장 추출
2. `whisper.cpp`를 사용하여 단어 수준 타임스탬프 생성
3. 각 정답 문장을 오디오 타임스탬프와 정렬
4. 문장별로 오디오 자르기
5. `[sound:filename.mp3]`가 포함된 Anki CSV 가져오기 파일 생성

이 방법은 무음 감지나 Whisper의 자동 문장 분할보다 안정적이며, Whisper가 예측할 수 없게 문장을 병합하거나 분할하는 문제를 피할 수 있습니다.

---

## 설치

### 전제 조건

본 도구를 실행하기 전에 다음 명령줄 도구가 설치되어 있는지 확인하세요：

| 도구 | 용도 | 설치 방법 |
|------|------|----------|
| `ffmpeg` | 오디오 변환 및 자르기 | `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux) |
| `whisper.cpp` | 영어 음성 인식 (단어 타임스탬프 포함) | [whisper.cpp 설치](#whispercpp-설치) 참조 |
| `pdftotext` | PDF 정답 파일 추출 | `brew install poppler` (macOS) / `apt install poppler-utils` (Linux) |
| `pandoc` | DOCX 정답 파일 추출 (선택) | `brew install pandoc` (macOS) / `apt install pandoc` (Linux) |

### whisper.cpp 설치

`whisper.cpp`는 OpenAI의 Whisper 모델의 고성능 C/C++ 구현으로, Apple Silicon, CUDA, Vulkan 등을 지원합니다.

#### 1. 리포지토리 복제

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
```

#### 2. 모델 다운로드

`ggml` 형식으로 변환된 모델 다운로드 (권장: `base.en`):

```bash
sh ./models/download-ggml-model.sh base.en
```

사용 가능한 모델:

| 모델 | 디스크 크기 | 메모리 사용량 |
|------|-----------|-------------|
| tiny | 75 MiB | ~273 MB |
| base | 142 MiB | ~388 MB |
| small | 466 MiB | ~852 MB |
| medium | 1.5 GiB | ~2.1 GB |
| large | 2.9 GiB | ~3.9 GB |

#### 3. whisper.cpp 빌드

**macOS (Apple Silicon / Intel):**

```bash
# 기본 빌드
cmake -B build
cmake --build build -j --config Release

# Apple Silicon에서 Core ML 가속 활성화 (권장)
cmake -B build -DWHISPER_COREML=1
cmake --build build -j --config Release
```

**Linux:**

```bash
cmake -B build
cmake --build build -j --config Release
```

**NVIDIA GPU (CUDA 가속):**

```bash
cmake -B build -DGGML_CUDA=1
cmake --build build -j --config Release
```

**기타 플랫폼:** [whisper.cpp 공식 문서](https://github.com/ggml-org/whisper.cpp) 참조.

#### 4. 설치 확인

```bash
./build/bin/whisper-cli -f samples/jfk.wav
```

### 본 도구 설치

```bash
# 본 리포지토리 복제
git clone https://github.com/Xiaon-Junf/Anki_toefl_listen_repeat_extractor_skill.git
cd Anki_toefl_listen_repeat_extractor_skill

# Python 의존성 설치 (필요한 경우)
# pip install -r requirements.txt
```

---

## 사용 방법

### 기본 명령

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/ggml-base.en.bin" \
  --collection-media "/path/to/Anki2/Profile/collection.media" \
  --combined-csv "/path/to/output/ListenRepeat_All.csv"
```

### 매개변수 안내

| 매개변수 | 설명 | 예시 |
|-----------|------|------|
| `exam-root` | 시험 폴더 루트 디렉토리 | `"/Users/me/TOEFL/Exams"` |
| `--output-root` | 출력 디렉토리 | `"/Users/me/TOEFL/Output"` |
| `--whisper-cli` | whisper-cli 실행 파일 경로 | `"/Users/me/whisper.cpp/build/bin/whisper-cli"` |
| `--model` | ggml 모델 파일 경로 | `"/Users/me/whisper.cpp/models/ggml-base.en.bin"` |
| `--collection-media` | Anki collection.media 폴더 경로 (선택) | `"/Users/me/Library/Application Support/Anki2/User/collection.media"` |
| `--combined-csv` | 통합 CSV 출력 경로 (선택) | `"/Users/me/TOEFL/ListenRepeat_All.csv"` |

### 입력 폴더 구조

```
exam-root/
  1.21 Test A/
    SpeakingModule1.mp3
    answer.pdf
  2.4 Test/
    speaking part1.zip
    answer.docx
```

스크립트는 각 시험 폴더에서 다음을 자동 검색합니다：
- **스피킹 오디오**: 파일명에 `speaking` 또는 `口语` 포함, `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, `.zip` 지원
- **정답 파일**: 파일명에 `answer`, `答案`, 또는 `参考答案` 포함, `.pdf`, `.docx`, `.txt` 지원
- `part1`과 `part2`가 모두 존재하는 경우, `part1` 우선 (따라말하기 문제는 보통 제1부에 있음)

---

## 작업 흐름

```
┌─────────────────┐
│ 정답 파일       │
│ 읽기            │
│ (PDF/DOCX/TXT) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 따라말하기 문장 │
│ 추출            │
│ (7개 표준      │
│  정답)          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ whisper.cpp     │
│ 음성 인식       │
│ (단어 수준     │
│  타임스탬프)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 문장 정렬       │
│ (정답 ↔        │
│  타임스탬프)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 오디오 클립     │
│ 자르기          │
│ (문장별        │
│  mp3)           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Anki CSV        │
│ 생성            │
│ [sound:xxx.mp3] │
└─────────────────┘
```

---

## 출력 파일

각 시험 폴더의 출력：

```
output/
  Exam Name/
    clips/
      toefl_repeat_examname_q01.mp3
      toefl_repeat_examname_q02.mp3
      ...
      manifest.csv          # 문장 텍스트, 시간 범위, 정렬 점수, 파일명
    ExamName_ListenRepeat_Anki.csv  # Anki 가져오기 파일
```

배치 출력：
- `batch_report.csv` — `ok`, `skipped`, `error` 상태 및 이유 포함
- `ListenRepeat_All.csv` — 모든 시험의 통합 CSV (`--combined-csv` 지정 시)

### Anki CSV 형식

```csv
#notetype:Basic (type in the answer)
Front,Back,Source,Tags
"[sound:toefl_repeat_examname_q01.mp3]","First repeat sentence.","Exam Name / ListenRepeat / Q01","TOEFL repeat"
```

---

## 수동 오버라이드

정답 파일이 오디오와 일치하지 않거나 OCR 추출이 실패한 경우 JSON 수동 오버라이드 파일을 생성합니다：

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

실행 명령：

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/model.bin" \
  --manual-sentences-json "/path/to/manual_sentences.json"
```

---

## 검증 및 문제 해결

### 실행 후 체크리스트

1. `batch_report.csv`를 열어 `status=ok`인 시험만 가져오기
2. 문제가 있는 시험의 `manifest.csv` 검사
3. 여러 시험의 첫 번째와 마지막 클립을 샘플 점검
4. 첫 단어가 잘린 경우 `--lead-pad`를 늘려 재실행
5. 정렬 실패 보고가 있는 경우, 정답 파일이 같은 오디오에 속하는지 확인；필요시 `--manual-sentences-json` 사용

### 자주 사용하는 매개변수 조정

| 매개변수 | 기본값 | 설명 |
|-----------|-------|------|
| `--lead-pad` | 0.45 | 첫 정렬 단어 전에 보존할 시간(초), 잘림 방지 |
| `--tail-pad` | 0.08 | 마지막 정렬 단어 후에 보존할 시간(초) |

시작 부분이 여전히 잘리는 경우, `--lead-pad 0.65`를 시도하세요.

---

## 자주 묻는 질문

**Q: 왜 정답 기반 방식을 사용하나요?**
A: Whisper는 예측할 수 없게 문장을 병합하거나 분할할 수 있어 타임스탬프가 부정확해질 수 있습니다. 표준 정답을 기준으로 하면 각 문장의 경계를 정확히 보장할 수 있습니다.

**Q: 지원하는 오디오 형식은?**
A: `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov` 및 이러한 오디오를 포함한 `.zip` 파일.

**Q: 필요한 하드웨어 구성은?**
A: base 모델(base.en)은 Apple Silicon에서 원활하게 실행됩니다. 다른 플랫폼에서는 최소 4GB RAM을 권장합니다.

**Q: 이미 가져온 Anki 카드를 업데이트하려면?**
A: 파일명을 변경하지 않고 `--collection-media`와 함께 스크립트를 재실행하면 `collection.media`의 기존 파일이 자동으로 덮어쓰기됩니다.

---

## 다국어 문서

- [中文 (중국어)](./Readme.md)
- [English (영어)](./README_EN.md)
- [日本語 (일본어)](./README_JA.md)

---

## 라이선스

본 프로젝트는 [MIT 라이선스](./LICENSE) 하에 제공됩니다.

---

## 감사의 말

- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) — OpenAI Whisper의 고성능 C/C++ 구현
- [Anki](https://apps.ankiweb.net/) — 강력한 간격 반복 학습 소프트웨어
