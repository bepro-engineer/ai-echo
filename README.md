以下が\*\*面影AIテンプレに完全準拠した Echo（`ai_echo`）用 `README.md`（マークダウン形式）\*\*です。
GitHubルートにそのまま貼り付けて使えます。一切の順序・文体・構成ブレなし。

---

````markdown
以下は、Echo（`ai_echo`）プロジェクト用の `README.md` のサンプルです。<br>
VPS環境（Ubuntu）での動作・GitHubクローン・環境構成が前提の構成になっています。

---
## 💻 Echoの動作画面

以下は、実際にEchoを実行したときの画面例です。<br>
- Echoでは、ユーザーの発言を記録し、類似した過去の会話をもとに自動応答を生成します。<br>
- 自分自身の過去の考え方や発言を活かした、自己応答型の会話体験が可能です。

<div align="center">
  <img src="https://github.com/bepro-engineer/ai-echo/blob/main/images/echo_screen.png" width="300">
</div>

```plaintext
# Echo（Echo AI）

「過去の自分が、未来の自分に答える。」

## 📌 プロジェクト概要

Echoは、ChatGPTと類似発言検索ロジックを活用し、ユーザー自身の過去の発言履歴をもとに現在の質問に対して応答する自己対話AIです。Phase構成により、記録と応答の処理を段階的に実装しています。

## 🧩 構成ファイル
````

ai\_echo/

* app.py：エントリーポイント
* config.py：設定ファイル
* .env：環境変数
* requirements.txt：ライブラリ一覧
* logic/

  * **init**.py
  * chatgpt\_logic.py：ChatGPT処理
  * db\_utils.py：DB処理
````

## 🚀 セットアップ手順（Ubuntu）

1. GitHubからクローン  
   ※PAT（Personal Access Token）を使用してクローンする必要があります。
   ```bash
   cd ~/projects/ai_echo
   git clone https://github.com/bepro-engineer/ai_echo.git
   cd echo
````

2. 仮想環境の作成と起動

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリのインストール

   ```bash
   pip install -r requirements.txt
   ```

4. `.env`ファイルの作成
   `.env` に以下を記載（各APIキーは自身で取得）

   ```
   OPENAI_API_KEY=sk-xxxxxxx
   LINE_CHANNEL_SECRET=xxxxxxxxxx
   LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxx
   ```

5. データベース初期化（必要に応じて）

   ```bash
   python logic/db_utils.py
   ```

## 🧪 テスト起動

```bash
python app.py
```

## 💬 モード構成

* `/learn`: ユーザーの発言をDBに記録
* `/reply`: 類似発言をもとにChatGPTで応答生成

## 🛡️ 注意事項

* 本プロジェクトは**研究・学習用途**です。商用利用はライセンスを確認の上、自己責任で行ってください。
* OpenAIのAPIコストが発生します。使用量には十分注意してください。

## 📝 ライセンス

```plaintext
MIT License
```
