# 🐦 Chirpy - 音声読み上げRSSリーダー

Chirpyは、ローカルに保存されたRSS記事データベース（SQLite3）から、未読記事を自動で取得し音声読み上げするプロジェクトです。

**✅ MVP版完成済み** - 基本機能がすべて実装され、実用可能な状態です。

---

## 🎯 実装済み機能

### ✅ 完全実装済み
- **音声読み上げ機能**: pyttsx3 + macOS `say`コマンドフォールバック
- **記事読み上げ**: 未読記事3件を新しい順に自動読み上げ
- **既読管理システム**: 読み上げ済み記事の自動追跡・管理
- **データベース管理**: SQLite3を使用した高速な記事取得
- **エラーハンドリング**: 包括的なエラー処理と詳細なフィードバック
- **設定可能TTS**: 音声速度・音声選択のカスタマイズ対応

### 🛠️ 開発・品質管理
- **Python 3.13対応**: 最新Python環境での動作
- **型安全性**: 完全な型ヒント + MyPy検証
- **コード品質**: Ruff linting + formatting (100%パス)
- **CI/CD自動化**: GitHub Actions による自動テスト・品質管理
- **依存関係管理**: Dependabot による自動アップデート

---

## 🗂️ プロジェクト構成

```
chirpy/
├── chirpy.py              # 🚀 メインアプリケーション
├── db_utils.py            # 🗄️ データベース管理ユーティリティ
├── db_migration.py        # 📊 データベースマイグレーション
├── test_read_system.py    # 🧪 テストスイート
├── collect.sh             # 📥 データベース同期スクリプト
├── pyproject.toml         # ⚙️ プロジェクト設定・依存関係
├── uv.lock               # 🔒 依存関係ロックファイル
├── data/
│   └── articles.db       # 📚 SQLite記事データベース (1,894件)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml        # 🔄 CI/CDパイプライン
│   │   └── release.yml   # 📦 リリース自動化
│   └── dependabot.yml    # 🤖 依存関係自動更新
├── CLAUDE.md             # 🧠 開発ガイドライン
├── ENHANCED_WORKFLOW.md  # ⚡ CI自動化ワークフロー
└── README.md             # 📖 本ドキュメント
```

---

## 🛠️ セットアップ

### 必要要件
- **Python 3.13+** (自動インストール)
- **uv** (モダンなPythonパッケージマネージャー)
- **SQLite3** (標準搭載)
- **macOS** (音声読み上げに最適化)

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/nyasuto/chirpy.git
cd chirpy

# 依存関係を自動インストール (Python 3.13も含む)
uv sync

# データベースをセットアップ (マイグレーション実行)
uv run python db_migration.py

# データベース同期 (リモートサーバーから最新データを取得)
./collect.sh
```

---

## 🚀 使用方法

### 基本実行
```bash
# デフォルトデータベースで実行
uv run python chirpy.py

# カスタムデータベースパスを指定
uv run python chirpy.py /path/to/custom/articles.db
```

### 実行例
```
🐦 Chirpy RSS Reader Starting...
📊 Database Stats:
   Total articles: 1,894
   Read articles: 5
   Unread articles: 1,801

📖 Fetching 3 latest unread articles...
📚 Found 3 unread articles to read

🔊 Speaking: Article title: 最新のAI技術動向について. Content: 本記事では...

--- Article 1 of 3 ---
📰 Title: 最新のAI技術動向について
🔗 Link: https://example.com/ai-trends
📅 Published: 2025-06-15T10:30:00+09:00
✅ Marked article 1234 as read

🎉 Session complete!
```

---

## 🧱 データベース構造

### メインテーブル
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,                    -- 記事タイトル
    link TEXT UNIQUE,             -- 記事URL
    published TEXT,               -- 公開日時 (ISO format)
    summary TEXT,                 -- 記事内容・要約
    embedded INTEGER DEFAULT 0    -- 埋め込み処理フラグ
);
```

### 既読管理テーブル
```sql
CREATE TABLE read_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,  -- articles.idへの参照
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles (id),
    UNIQUE(article_id)           -- 重複読み上げ防止
);
```

### 現在のデータベース状況
- **総記事数**: 1,894件
- **未読記事**: 1,800+件 (コンテンツ付き)
- **最新更新**: 2025年6月15日

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

# 基本動作確認
uv run python -c "from chirpy import ChirpyReader; print('✅ All systems operational')"
```

### CI/CD
- **自動テスト**: プルリクエスト・mainブランチプッシュ時
- **品質チェック**: コード品質・型安全性・テスト実行
- **依存関係更新**: Dependabotによる週次自動更新

---

## ⚙️ 設定・カスタマイズ

### 環境変数 (`.env` ファイル)
```bash
# OpenAI API (将来の要約機能用)
OPENAI_API_KEY=your_api_key_here

# 読み上げ設定
MAX_ARTICLES=3        # 一度に処理する記事数
TTS_ENGINE=pyttsx3    # 音声エンジン (pyttsx3 | macos_say)
TTS_RATE=180         # 音声速度 (words per minute)
TTS_VOLUME=0.8       # 音量 (0.0-1.0)
```

### 音声設定のカスタマイズ
ChirpyReaderクラスの`_initialize_tts()`メソッドで音声設定を調整可能:
- 音声速度 (現在: 180 wpm)
- 音声選択 (利用可能な音声から自動選択)
- フォールバック機能 (pyttsx3 → macOS say)

---

## 🔮 将来的な拡張予定

### 🚧 設定済み・未実装
- **OpenAI API統合**: 空のsummaryの自動要約生成
- **コンテンツ取得**: linkからの原文自動取得
- **環境変数設定**: .envベースの動的設定

### 💡 将来の機能アイデア
- **スケジューリング**: 毎朝決まった時刻に自動実行 (cron/rumps)
- **音声ファイル保存**: MP3エクスポート機能
- **デバイス連携**: AirPods接続検知で自動再生
- **GUI化**: macOSメニューバー常駐アプリ
- **多言語対応**: 英語記事の読み上げ対応
- **カテゴリー分類**: RSS記事の自動分類・フィルタリング

---

## 🤝 開発に参加

### 品質基準
- **型安全性**: 完全な型ヒント必須
- **コード品質**: Ruff 100%パス
- **テスト**: 新機能には対応テスト必須
- **コミット**: Conventional Commit形式

### 開発ワークフロー
1. **ブランチ作成**: `feat/issue-X-description`
2. **実装**: 型安全・テスト付きで実装
3. **品質チェック**: `uv run ruff check . && uv run mypy .`
4. **プルリクエスト**: CI通過後マージ

詳細は [`CLAUDE.md`](CLAUDE.md) と [`ENHANCED_WORKFLOW.md`](ENHANCED_WORKFLOW.md) を参照。

---

## 📊 技術スタック

### ランタイム
- **Python 3.13** - 最新Python環境
- **SQLite3** - 高速ローカルデータベース
- **pyttsx3** - クロスプラットフォーム音声合成
- **requests + BeautifulSoup4** - Webスクレイピング (将来使用)

### 開発ツール
- **uv** - 高速パッケージマネージャー
- **Ruff** - 高速リンター・フォーマッター
- **MyPy** - 静的型チェッカー
- **GitHub Actions** - CI/CDパイプライン

---

## 📄 ライセンス

MIT License

---

## 🏆 ステータス

**✅ MVP完成・本格運用可能**

- すべてのコア機能実装済み
- 包括的なテストカバレッジ
- CI/CD自動化完備
- コード品質100%準拠
- 本格的な開発プロセス確立

**現在のマイルストーン**: 安定運用 + 機能拡張検討中