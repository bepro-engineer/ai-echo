了解。以下が**Echoプロジェクト専用のREADME.md（マークダウン形式）完全版**です。GitHubのルートに**そのまま貼り付け可能**です。

---

```markdown
# Echo（自己応答AI）

「過去の自分が、未来の自分に答える。」

## 📌 プロジェクト概要

Echoは、ユーザー自身が送信した過去のメッセージを記録・蓄積し、  
新たな入力に対して**過去の類似発言を検索・抽出し、自分自身の応答を返す**自己応答型AIです。

ChatGPTと自然言語処理ロジックを組み合わせることで、  
「人間らしい記憶のような応答体験」を実現します。

## 💻 Echoの動作画面（LINE Bot）

以下は、実際にEchoがLINEで動作している画面例です。

- ユーザーが送った言葉を記録
- 類似発言があれば、過去の応答を引用して返す
- ChatGPTが補完を行うことで自然な会話が成立

<div align="center">
  <img src="https://github.com/bepro-engineer/echo/raw/main/images/echo_screen.png" width="300">
</div>

## 🧩 構成ファイル

```

echo/
├── app.py                       # Flaskアプリのエントリーポイント
├── config.py                    # 環境変数の設定
├── .env                         # APIキーなどの機密情報（ローカル）
├── requirements.txt             # 必要ライブラリ一覧
├── logic/
│   ├── chatgpt\_logic.py         # ChatGPT API処理ロジック
│   ├── similarity.py            # 発言類似度算出ロジック
│   ├── db\_utils.py              # SQLite操作（記録・検索）
│   └── line\_handler.py          # LINE Messaging API受信・応答処理
├── data/
│   └── message\_log.db           # 発言履歴DB（SQLite）

````

## 🚀 セットアップ手順（Ubuntu + VPS前提）

### 1. GitHubからクローン

```bash
cd ~/projects
git clone https://github.com/bepro-engineer/echo.git
cd echo
````

### 2. 仮想環境の作成と有効化

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 4. `.env` の作成（以下を記載）

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
LINE_CHANNEL_SECRET=xxxxxxxxxxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxx
```

### 5. DB初期化（未実行なら）

```bash
python logic/db_utils.py
```

### 6. 起動（Webhook用）

```bash
python app.py
```

## 🔁 応答ロジック概要

1. LINEでメッセージを受信
2. その発言をDBへ記録
3. 類似発言をSQLite全文検索で抽出
4. 類似スコア上位の応答を引用
5. ChatGPTで自然文に整形し、返信

## 💬 自己応答例（動作パターン）

| 入力例        | Echoの応答内容例                  |
| ---------- | --------------------------- |
| 最近、集中できない  | ※以前「集中できない」と言ったときの応答が再提示される |
| やる気が出ない    | 過去に似た話題の返答を自分の言葉で返す         |
| モチベーションがない | 「過去の自分はこう考えてた」といった補完文になる    |

## 🛡️ 注意事項

* 本プロジェクトは**研究・学習目的**です。商用利用の際は必ずライセンスを確認してください。
* OpenAIのAPIコストが発生します。使用量にはご注意ください。

## 📝 ライセンス

```
MIT License
```
