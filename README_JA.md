# TOEFL リスニング復唱問題抽出ツール

TOEFL スピーキング試験の音声と PDF、DOCX、または TXT 形式の答えを持っていて、ファイルの頻繁な切り替えや複数のウィンドウを開くことで長期にわたる復唱問題の練習が難しいと感じているなら、このテクニックを試してみてください！

あなたの Agent にこう伝えるだけです：`TOEFL スピーキングの復唱問題の答えは xxx.pdf にあり、音声は xxx.mp3 です。答えを入力する Anki フラッシュカードを作成してください。` あなたの Agent は操作方法を理解しており、バッチモードもサポートしています。その後、CSV ファイル 1 つを Anki にインポートするだけで、個人の忘却曲線に合わせていつでもどこでも本番の試験問題でリスニングと復唱の練習ができます。シンプルでしょう？試してみてください！

もし以下のツールを使いたいけどプログラミングの基礎がない場合は、`Readme.md` と `SKILL.md` をあなたの Agent に見せてください。対話の中でニーズを確認し、CSV ファイルを生成します。

それでも使い方がわからない場合は、著者がすでに抽出した CSV ファイルと音声クリップ（更新予定、クラウドストレージを使用）を参照し、Anki に直接インポートしてください。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

> TOEFL スピーキング試験の音声から「リスニング復唱問題」を抽出し、Anki フラッシュカードを生成するツール。

---

## 📖 目次

- [概要](#概要)
- [インストール](#インストール)
  - [whisper.cpp のインストール](#whispercpp-のインストール)
  - [本ツールのインストール](#本ツールのインストール)
- [使い方](#使い方)
- [ワークフロー](#ワークフロー)
- [出力ファイル](#出力ファイル)
- [手動オーバーライド](#手動オーバーライド)
- [検証とトラブルシューティング](#検証とトラブルシューティング)
- [よくある質問](#よくある質問)
- [多言語ドキュメント](#多言語ドキュメント)
- [ライセンス](#ライセンス)

---

## 概要

本ツールは**答案駆動型ワークフロー**を採用しています：

1. PDF/DOCX/TXT の答案ファイルから標準復唱文を抽出
2. `whisper.cpp` を使用して単語レベルのタイムスタンプを生成
3. 各答案文を音声タイムスタンプに照合
4. 文ごとに音声をカット
5. `[sound:filename.mp3]` を含む Anki CSV インポートファイルを生成

この方法は、静音検出や Whisper の自動文分割よりも安定しており、Whisper が予期せず文を結合または分割する問題を回避できます。

---

## インストール

### 前提条件

本ツールを実行する前に、以下のコマンドラインツールがインストールされていることを確認してください：

| ツール | 用途 | インストール方法 |
|--------|------|----------------|
| `ffmpeg` | 音声変換とカット | `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux) |
| `whisper.cpp` | 英語音声認識（単語タイムスタンプ付き） | [whisper.cpp のインストール](#whispercpp-のインストール) を参照 |
| `pdftotext` | PDF 答案ファイルの抽出 | `brew install poppler` (macOS) / `apt install poppler-utils` (Linux) |
| `pandoc` | DOCX 答案ファイルの抽出（オプション） | `brew install pandoc` (macOS) / `apt install pandoc` (Linux) |

### whisper.cpp のインストール

`whisper.cpp` は OpenAI の Whisper モデルの高性能 C/C++ 実装で、Apple Silicon、CUDA、Vulkan などをサポートしています。

#### 1. リポジトリのクローン

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
```

#### 2. モデルのダウンロード

`ggml` 形式に変換されたモデルをダウンロード（推奨: `base.en`）：

```bash
sh ./models/download-ggml-model.sh base.en
```

利用可能なモデル：

| モデル | ディスクサイズ | メモリ使用量 |
|--------|--------------|------------|
| tiny | 75 MiB | ~273 MB |
| base | 142 MiB | ~388 MB |
| small | 466 MiB | ~852 MB |
| medium | 1.5 GiB | ~2.1 GB |
| large | 2.9 GiB | ~3.9 GB |

#### 3. whisper.cpp のビルド

**macOS (Apple Silicon / Intel):**

```bash
# 基本ビルド
cmake -B build
cmake --build build -j --config Release

# Apple Silicon で Core ML 加速を有効化（推奨）
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

**その他のプラットフォーム:** [whisper.cpp 公式ドキュメント](https://github.com/ggml-org/whisper.cpp) を参照。

#### 4. インストールの確認

```bash
./build/bin/whisper-cli -f samples/jfk.wav
```

### 本ツールのインストール

```bash
npx add-skill https://github.com/Xiaon-Junf/Anki_toefl_listen_repeat_extractor_skill
```

または:

```bash
# 本リポジトリをクローン
git clone https://github.com/Xiaon-Junf/Anki_toefl_listen_repeat_extractor_skill.git
cd Anki_toefl_listen_repeat_extractor_skill

# Python 依存関係のインストール（必要に応じて）
# pip install -r requirements.txt
```

---

## 使い方

### 基本コマンド

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/ggml-base.en.bin" \
  --collection-media "/path/to/Anki2/Profile/collection.media" \
  --combined-csv "/path/to/output/ListenRepeat_All.csv"
```

### パラメータ一覧

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `exam-root` | 試験フォルダのルートディレクトリ | `"/Users/me/TOEFL/Exams"` |
| `--output-root` | 出力ディレクトリ | `"/Users/me/TOEFL/Output"` |
| `--whisper-cli` | whisper-cli 実行ファイルのパス | `"/Users/me/whisper.cpp/build/bin/whisper-cli"` |
| `--model` | ggml モデルファイルのパス | `"/Users/me/whisper.cpp/models/ggml-base.en.bin"` |
| `--collection-media` | Anki collection.media フォルダのパス（オプション） | `"/Users/me/Library/Application Support/Anki2/User/collection.media"` |
| `--combined-csv` | 結合 CSV の出力パス（オプション） | `"/Users/me/TOEFL/ListenRepeat_All.csv"` |

### 入力フォルダ構造

```
exam-root/
  1.21 Test A/
    SpeakingModule1.mp3
    answer.pdf
  2.4 Test/
    speaking part1.zip
    answer.docx
```

スクリプトは各試験フォルダ内で以下を自動検索します：
- **口语音声**: ファイル名に `speaking` または `口语` を含む、`.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, `.zip` に対応
- **答案ファイル**: ファイル名に `answer`, `答案`, または `参考答案` を含む、`.pdf`, `.docx`, `.txt` に対応
- `part1` と `part2` の両方が存在する場合、`part1` を優先（復唱問題は通常第1部に含まれるため）

---

## ワークフロー

```
┌─────────────────┐
│ 答案ファイルの  │
│ 読み込み        │
│ (PDF/DOCX/TXT) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 復唱文の抽出    │
│ (7つの標準答案) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ whisper.cpp     │
│ 音声認識        │
│ (単語レベル     │
│  タイムスタンプ)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 文の照合        │
│ (答案 ↔         │
│  タイムスタンプ)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 音声クリップの  │
│ カット          │
│ (文ごとに       │
│  mp3)           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Anki CSV の    │
│ 生成            │
│ [sound:xxx.mp3] │
└─────────────────┘
```

---

## 出力ファイル

各試験フォルダの出力：

```
output/
  Exam Name/
    clips/
      toefl_repeat_examname_q01.mp3
      toefl_repeat_examname_q02.mp3
      ...
      manifest.csv          # 文テキスト、時間範囲、照合スコア、ファイル名
    ExamName_ListenRepeat_Anki.csv  # Anki インポートファイル
```

バッチ出力：
- `batch_report.csv` — `ok`, `skipped`, `error` の状態と理由を含む
- `ListenRepeat_All.csv` — 全試験の結合 CSV（`--combined-csv` 指定時）

### Anki CSV フォーマット

```csv
#notetype:Basic (type in the answer)
Front,Back,Source,Tags
"[sound:toefl_repeat_examname_q01.mp3]","First repeat sentence.","Exam Name / ListenRepeat / Q01","TOEFL repeat"
```

---

## 手動オーバーライド

答案ファイルが音声と一致しない場合、または OCR 抽出が失敗した場合、JSON 手動オーバーライドファイルを作成します：

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

実行コマンド：

```bash
python3 scripts/answer_driven_repeat_batch.py \
  "/path/to/exam-root" \
  --output-root "/path/to/output" \
  --whisper-cli "/path/to/whisper-cli" \
  --model "/path/to/model.bin" \
  --manual-sentences-json "/path/to/manual_sentences.json"
```

---

## 検証とトラブルシューティング

### 実行後のチェックリスト

1. `batch_report.csv` を開き、`status=ok` の試験のみをインポート
2. 問題のある試験の `manifest.csv` を確認
3. 数試験の最初と最後のクリップをスポットチェック
4. 最初の単語が切れている場合、`--lead-pad` を増やして再実行
5. 照合失敗の報告がある場合、答案ファイルが同じ音声に属しているか確認；必要に応じて `--manual-sentences-json` を使用

### よく使うパラメータ調整

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `--lead-pad` | 0.45 | 最初の照合単語前に保持する時間（秒）、切れ防止 |
| `--tail-pad` | 0.08 | 最後の照合単語後に保持する時間（秒） |

先頭がまだ切れている場合、`--lead-pad 0.65` を試行。

---

## よくある質問

**Q: なぜ答案駆動型を採用するのですか？**
A: Whisper は予期せず文を結合または分割する可能性があり、タイムスタンプが不正確になることがあります。標準答案を基準にすることで、各文の境界を正確に保証できます。

**Q: 対応している音声フォーマットは？**
A: `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`、およびこれらの音声を含む `.zip` ファイル。

**Q: 必要なハードウェア構成は？**
A: base モデル（base.en）は Apple Silicon でスムーズに動作します。他のプラットフォームでは最低 4GB の RAM を推奨。

**Q: 既にインポートした Anki カードを更新するには？**
A: ファイル名を変更せず、スクリプトを `--collection-media` 付きで再実行すると、`collection.media` の旧ファイルが自動的に上書きされます。

---

## 多言語ドキュメント

- [中文 (中国語)](./Readme.md)
- [English (英語)](./README_EN.md)
- [한국어 (韓国語)](./README_KO.md)

---

## ライセンス

本プロジェクトは [MIT ライセンス](./LICENSE) の下で提供されています。

---

## 謝辞

- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) — OpenAI Whisper の高性能 C/C++ 実装
- [Anki](https://apps.ankiweb.net/) — 強力な間隔反復学習ソフトウェア
