🐦 Chirpy - MVP版 音声読み上げRSSリーダー

Chirpyは、ローカルに保存されたRSS記事データベース（SQLite3）を元に、
新着記事を自動で要約・音声読み上げするプロジェクトです。

このREADMEは、**MVP（最小実行可能プロトタイプ）**として、
DBから記事を読み出し、音声で読み上げる処理を実装するための手順をまとめたものです。

⸻

✅ MVPの目的
	•	SQLite3 DB（articlesテーブル）から未読記事を取得
	•	タイトルと要約（summary）を音声で読み上げる

⸻

🗂 ディレクトリ構成

chirpy/
├── chirpy.py          # メインスクリプト
├── data/articles.db    # SQLite3 DB（別マシンからコピー）
├── requirements.txt   # 必要ライブラリ
└── README.md          # 本ドキュメント


⸻

🛠 必要要件
	- Python 3.x
    - uv, ruff, tyを使ったモダンなアーキテクチャを採用
	- モジュール: sqlite3（標準）,  pyttsx3 または macOSのsayコマンド

⸻

🧱 DB構造（前提）

CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    link TEXT UNIQUE,
    published TEXT,
    summary TEXT,
    embedded INTEGER DEFAULT 0
);

	summary は全文が入っている。
    summaryが空の場合は原文が取得できていないので link から原文を取得する必要がある
    published は記事の更新日付でフィルタリングに使う

⸻

📥 セットアップ

# 任意の仮想環境
python3 -m venv venv
source venv/bin/activate

# ライブラリインストール
pip install -r requirements.txt

requirements.txt:

pyttsx3


⸻

🚀 実行方法

python chirpy.py

	•	未読の最新日付の記事３件を対象に読み上げ
	•	読み上げ済みの記事は、別のテーブルに既読テーブルを作って管理する
	•	音声出力は pyttsx3 または macOS の say コマンドを使用

⸻

📌 注意点
	•	articles.db は別マシンからコピーして chirpy/data 配下に配置しておく
	•	summary カラムが空欄の場合はlinkを辿って原文を要約する 要約にはOpen AI APIを使う
	•	音声はローカル再生され、mp3保存などは含まない

⸻

🔮 将来的な拡張案
	•	ChatGPT APIを用いたsummary自動生成
	•	毎朝決まった時刻に自動再生（cron or rumps）
	•	MP3保存機能
	•	AirPods接続検知で自動再生
	•	メニューバー常駐アプリ化（macOS）

⸻

📄 ライセンス

MIT License