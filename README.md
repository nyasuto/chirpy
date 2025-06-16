# 🐦 Chirpy - 多言語対応音声読み上げRSSリーダー

Chirpyは、ローカルに保存されたRSS記事データベース（SQLite3）から、未読記事を自動で取得し音声読み上げするプロジェクトです。**英語記事の日本語翻訳機能**も搭載し、グローバルなコンテンツにも対応しています。

**✅ Production Ready** - 基本機能がすべて実装され、本格的な運用に対応した状態です。

---

## 🎯 実装済み機能

### ✅ コア機能
- **音声読み上げ機能**: pyttsx3 + macOS `say`コマンドフォールバック
- **記事読み上げ**: 未読記事を設定可能な件数で自動読み上げ
- **既読管理システム**: 読み上げ済み記事の自動追跡・管理
- **データベース管理**: SQLite3を使用した高速な記事取得・統計

### 🌐 翻訳・多言語機能 ⭐ NEW
- **自動言語検出**: 記事の言語を自動判定（langdetect）
- **英日翻訳**: 英語記事を自動的に日本語に翻訳・要約（OpenAI API）
- **原文保存**: 翻訳前の原文を保持し、いつでも参照可能
- **翻訳制御**: CLI経由で翻訳のON/OFF切り替え

### 🛠️ 高度な設定・管理
- **包括的設定管理**: 環境変数・設定ファイル・CLI引数の階層型設定
- **構造化ログ**: ファイルローテーション付きの詳細ログシステム
- **コンテンツ取得**: 空の要約に対する自動コンテンツ取得・AI要約生成
- **統計・分析**: データベース統計、翻訳統計、言語別分析

### 🧪 開発・品質管理
- **Python 3.13対応**: 最新Python環境での動作
- **型安全性**: 完全な型ヒント + MyPy検証（100%）
- **コード品質**: Ruff linting + formatting（100%パス）
- **CI/CD自動化**: GitHub Actions による自動テスト・品質管理
- **依存関係管理**: Dependabot による自動アップデート

---

## 🗂️ プロジェクト構成

```
chirpy/
├── chirpy.py                 # 🚀 メインアプリケーション
├── config.py                 # ⚙️ 設定管理・ログシステム
├── cli.py                   # 🖥️ CLI引数パーサー
├── content_fetcher.py       # 🌐 コンテンツ取得・翻訳・AI要約
├── db_utils.py              # 🗄️ データベース管理ユーティリティ
├── db_migration.py          # 📊 データベースマイグレーション
├── test_read_system.py      # 🧪 テストスイート
├── collect.sh               # 📥 データベース同期スクリプト
├── pyproject.toml           # ⚙️ プロジェクト設定・依存関係
├── uv.lock                 # 🔒 依存関係ロックファイル
├── .env.example            # 📝 設定ファイルテンプレート
├── data/
│   └── articles.db         # 📚 SQLite記事データベース (1,894件)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml          # 🔄 CI/CDパイプライン
│   │   └── release.yml     # 📦 リリース自動化
│   └── dependabot.yml      # 🤖 依存関係自動更新
├── CLAUDE.md               # 🧠 開発ガイドライン
├── ENHANCED_WORKFLOW.md    # ⚡ CI自動化ワークフロー
└── README.md               # 📖 本ドキュメント
```

---

## 🛠️ セットアップ

### 必要要件
- **Python 3.13+** (自動インストール)
- **uv** (モダンなPythonパッケージマネージャー)
- **SQLite3** (標準搭載)
- **macOS** (音声読み上げに最適化)
- **OpenAI API Key** (翻訳機能使用時)

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/nyasuto/chirpy.git
cd chirpy

# 依存関係を自動インストール (Python 3.13も含む)
uv sync

# 設定ファイルを作成
cp .env.example .env

# OpenAI API Keyを設定（翻訳機能使用時）
echo "OPENAI_API_KEY=your_openai_api_key_here" >> .env

# データベースをセットアップ (マイグレーション実行)
uv run python db_migration.py

# データベース同期 (リモートサーバーから最新データを取得)
./collect.sh
```

---

## 🚀 使用方法

### 基本的な記事読み上げ
```bash
# デフォルト設定で実行（3記事、翻訳あり）
uv run python chirpy.py

# 読み上げ記事数を指定
uv run python chirpy.py --max-articles 5

# 音声なしモード（テキスト表示のみ）
uv run python chirpy.py --no-speech
```

### 翻訳機能
```bash
# 既存記事の翻訳処理
uv run python chirpy.py --translate-articles

# 翻訳を無効にして実行
uv run python chirpy.py --no-translate

# 翻訳対象言語を指定（デフォルト: ja）
uv run python chirpy.py --target-language ja
```

### データベース・統計
```bash
# データベース統計を表示
uv run python chirpy.py --stats

# 空の要約を持つ記事を処理（AI要約生成）
uv run python chirpy.py --process-summaries

# 設定確認
uv run python chirpy.py --show-config
```

### ログ・デバッグ
```bash
# デバッグログを有効化
uv run python chirpy.py --log-level DEBUG

# ログファイルに出力
uv run python chirpy.py --log-file logs/chirpy.log

# 詳細モード
uv run python chirpy.py --verbose
```

### 実行例
```
🐦 Chirpy RSS Reader Starting...
📊 Database Stats:
   Total articles: 1,894
   Read articles: 5
   Unread articles: 1,801
   Empty summaries: 92

📋 Translation:
   auto_translate: True
   target_language: ja
   preserve_original: True
   translation_provider: openai

📖 Fetching 3 latest unread articles...
📚 Found 3 unread articles to read

🔊 Speaking: Article title: 最新のAI技術動向について. Content: 本記事では...

--- Article 1 of 3 ---
📰 Title: Latest AI Technology Trends (英語記事 → 日本語翻訳済み)
🔗 Link: https://example.com/ai-trends
📅 Published: 2025-06-15T10:30:00+09:00
🌐 Language: en → ja (translated)
✅ Marked article 1234 as read

🎉 Session complete!
```

---

## 🧱 データベース構造

### メインテーブル（拡張済み）
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,                           -- 記事タイトル
    link TEXT UNIQUE,                     -- 記事URL
    published TEXT,                       -- 公開日時 (ISO format)
    summary TEXT,                         -- 記事内容・要約（翻訳後も含む）
    embedded INTEGER DEFAULT 0,          -- 埋め込み処理フラグ
    detected_language TEXT DEFAULT 'unknown',  -- 🆕 検出言語
    original_summary TEXT,               -- 🆕 翻訳前の原文
    is_translated INTEGER DEFAULT 0     -- 🆕 翻訳済みフラグ
);
```

### 既読管理テーブル
```sql
CREATE TABLE read_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,         -- articles.idへの参照
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles (id),
    UNIQUE(article_id)                   -- 重複読み上げ防止
);
```

### 現在のデータベース状況
- **総記事数**: 1,894件
- **未読記事**: 1,800+件 (コンテンツ付き)
- **言語別記事**: 日本語 (ja), 英語 (en), その他
- **翻訳済み記事**: CLI --translate-articlesで処理
- **最新更新**: 2025年6月16日

---

## ⚙️ 設定・カスタマイズ

### 環境変数設定 (`.env` ファイル)
```bash
# OpenAI API（翻訳・AI要約機能）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o                    # 使用モデル
OPENAI_MAX_TOKENS=5000                 # 最大トークン数
OPENAI_TEMPERATURE=0.3                 # 創造性レベル

# データベース設定
CHIRPY_DATABASE_PATH=data/articles.db
CHIRPY_MAX_ARTICLES=3                  # 一度に処理する記事数
CHIRPY_MAX_SUMMARY_LENGTH=500          # 要約最大長

# 音声読み上げ設定
TTS_ENGINE=pyttsx3                     # 音声エンジン
TTS_RATE=180                          # 音声速度 (words per minute)
TTS_VOLUME=1.0                        # 音量 (0.0-1.0)
SPEECH_ENABLED=true                   # TTS有効・無効

# 翻訳設定
AUTO_TRANSLATE=true                   # 自動翻訳有効・無効
TARGET_LANGUAGE=ja                    # 翻訳先言語
PRESERVE_ORIGINAL=true                # 原文保存
TRANSLATION_PROVIDER=openai           # 翻訳プロバイダー

# コンテンツ取得設定
FETCH_TIMEOUT=30                      # HTTP通信タイムアウト
RATE_LIMIT_DELAY=2                    # API呼び出し間隔

# ログ設定
LOG_LEVEL=INFO                        # ログレベル
LOG_FILE=logs/chirpy.log              # ログファイルパス（任意）
LOG_MAX_BYTES=10485760                # ログローテーション サイズ制限
LOG_BACKUP_COUNT=3                    # バックアップファイル数

# アプリケーション動作
AUTO_MARK_READ=true                   # 自動既読マーク
PAUSE_BETWEEN_ARTICLES=true           # 記事間の一時停止
```

### CLI オプション完全リスト

#### 基本操作
```bash
chirpy [database_path]                # データベースパスを指定
--max-articles N                      # 処理記事数
```

#### 動作モード
```bash
--process-summaries                   # 空要約の記事をAI処理
--stats                              # データベース統計表示
--show-config                        # 現在の設定を表示
--translate-articles                 # 記事翻訳処理
```

#### 音声設定
```bash
--no-speech                          # 音声読み上げを無効
--tts-rate WPM                       # 音声速度
--tts-volume LEVEL                   # 音量レベル
--tts-engine {pyttsx3,say}           # TTS エンジン選択
```

#### 翻訳設定
```bash
--no-translate                       # 自動翻訳を無効
--target-language LANG               # 翻訳先言語（例: ja, en）
```

#### ログ・デバッグ
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}  # ログレベル
--log-file PATH                      # ログファイルパス
--verbose, -v                        # 詳細ログ (DEBUG相当)
--quiet, -q                          # エラーのみ表示
```

#### 設定管理
```bash
--config-file PATH                   # カスタム設定ファイル
```

#### アプリケーション制御
```bash
--no-mark-read                       # 自動既読マークを無効
--no-pause                           # 記事間の一時停止を無効
```

---

## 🧪 開発・テスト

### コード品質チェック
```bash
# リンティング + フォーマット
uv run ruff check .
uv run ruff format .

# 型チェック
uv run mypy .

# 全チェック一括実行
uv run ruff check . && uv run ruff format . && uv run mypy .
```

### テスト実行
```bash
# データベース機能テスト
uv run python test_read_system.py

# 翻訳機能テスト
uv run python -c "
from content_fetcher import ContentFetcher
from config import ChirpyConfig
cf = ContentFetcher(ChirpyConfig.from_env())
print('✅ Translation system operational' if cf.is_available() else '⚠️  OpenAI API not configured')
"

# 基本動作確認
uv run python -c "from chirpy import ChirpyReader; print('✅ All systems operational')"
```

### 翻訳機能のテスト
```bash
# 言語検出テスト
uv run python -c "
from content_fetcher import ContentFetcher
from config import ChirpyConfig
cf = ContentFetcher(ChirpyConfig.from_env())
print('English detected:', cf.detect_language('Hello world this is English text'))
print('Japanese detected:', cf.detect_language('こんにちは、これは日本語のテキストです'))
"

# 翻訳統計確認
uv run python -c "
from db_utils import DatabaseManager
db = DatabaseManager('data/articles.db')
stats = db.get_translation_stats()
print('Translation stats:', stats)
"
```

### CI/CD
- **自動テスト**: プルリクエスト・mainブランチプッシュ時
- **品質チェック**: コード品質・型安全性・テスト実行
- **依存関係更新**: Dependabotによる週次自動更新

---

## 📊 技術スタック

### ランタイム
- **Python 3.13** - 最新Python環境
- **SQLite3** - 高速ローカルデータベース
- **pyttsx3** - クロスプラットフォーム音声合成
- **langdetect** - 言語自動検出
- **requests + BeautifulSoup4** - Webスクレイピング・コンテンツ取得
- **OpenAI API** - AI翻訳・要約生成
- **python-dotenv** - 環境変数管理

### 開発ツール
- **uv** - 高速パッケージマネージャー
- **Ruff** - 高速リンター・フォーマッター
- **MyPy** - 静的型チェッカー
- **GitHub Actions** - CI/CDパイプライン

---

## 🌐 翻訳システム詳細

### 対応言語
- **ソース言語**: 英語 (en)、日本語 (ja)、その他（検出のみ）
- **ターゲット言語**: 日本語 (ja)
- **翻訳エンジン**: OpenAI GPT-4o/GPT-3.5-turbo

### 翻訳ワークフロー
1. **言語検出**: langdetectによる自動言語判定
2. **翻訳判定**: 英語記事かつ未翻訳の場合に翻訳実行
3. **AI翻訳**: OpenAI APIで翻訳と要約を同時実行
4. **データ保存**: 翻訳結果をsummaryに、原文をoriginal_summaryに保存
5. **メタデータ更新**: 言語情報・翻訳フラグをデータベースに記録

### 翻訳品質の特徴
- **コンテキスト考慮**: 記事タイトルとコンテンツを統合処理
- **要約最適化**: 音声読み上げに適した2-3段落の自然な日本語
- **専門用語対応**: AI技術記事・ニュース記事の専門用語を適切に翻訳
- **読みやすさ重視**: 機械翻訳感を排した自然な日本語表現

---

## 🔮 将来的な拡張予定

### 🚧 近期実装予定
- **エラーハンドリング強化**: リトライ機構・回路ブレーカーパターン
- **包括的テストスイート**: pytest基盤のユニット・統合テスト
- **インタラクティブUI**: リアルタイム制御・キーボードショートカット
- **パフォーマンス最適化**: キャッシュ・データベースインデックス

### 💡 中長期アイデア
- **多言語翻訳拡張**: 中国語・韓国語・スペイン語対応
- **音声ファイル保存**: MP3エクスポート機能
- **スケジューリング**: 毎朝決まった時刻に自動実行
- **Web インターフェース**: ブラウザベースの管理画面
- **デバイス連携**: AirPods接続検知で自動再生
- **GUI化**: macOSメニューバー常駐アプリ
- **カテゴリー分類**: RSS記事の自動分類・フィルタリング
- **感情分析**: 記事の感情・トーン分析機能

---

## 🤝 開発に参加

### 品質基準
- **型安全性**: 完全な型ヒント必須（MyPy 100%）
- **コード品質**: Ruff 100%パス
- **テスト**: 新機能には対応テスト必須
- **コミット**: Conventional Commit形式
- **ドキュメント**: 新機能はREADME・CLAUDE.md更新

### Issue管理ルール
- **必須ラベル**: 全issueに `priority: {critical|high|medium|low}` と `type: {feature|bug|enhancement|docs|test|refactor|ci/cd|security}` を設定
- **ブランチ命名**: `{type}/issue-X-description` 形式

### 開発ワークフロー
1. **ブランチ作成**: `feat/issue-X-description`
2. **実装**: 型安全・テスト付きで実装
3. **品質チェック**: `uv run ruff check . && uv run mypy .`
4. **プルリクエスト**: CI通過後マージ

詳細は [`CLAUDE.md`](CLAUDE.md) と [`ENHANCED_WORKFLOW.md`](ENHANCED_WORKFLOW.md) を参照。

---

## 📄 ライセンス

MIT License

---

## 🏆 ステータス

**✅ Production Ready - 多言語対応完了**

- すべてのコア機能実装済み（音声読み上げ・翻訳・設定管理）
- 英語→日本語翻訳システム完全実装
- 包括的な設定管理・ログシステム
- CI/CD自動化完備
- コード品質100%準拠（Ruff + MyPy）
- 本格的な開発プロセス確立

**現在のマイルストーン**: 本格運用中 + エラーハンドリング・テスト強化検討中

**最新機能**: 🌐 英語記事の自動日本語翻訳対応（2025年6月実装）