# 🧠 Echo（エコー）– 自分の言葉で、自分を導くAI

「迷ったとき、答えをくれるのは、他人じゃない。過去の自分だ。」

---

## ✨ Echoとは？

Echoは、ChatGPTとLINEを連携させて構築する “自己対話AI” です。  
あなたが発した言葉や価値観を記録し、それをもとに「未来のあなたの悩みや問い」に、  
“過去のあなた自身の言葉”で返答してくれる、新しいタイプの応答エージェントです。

---

## 🚀 なぜEchoは特別なのか？

| 通常のAIチャット | Echo |
|------------------|------|
| 一般知識ベースで応答 | **自分の過去の言葉で応答** |
| 応答は都度リセットされる | **記憶が蓄積・進化する** |
| 一時的な助言 | **継続的に育つ“人格”として応答** |
| 他人の知識で寄り添う | **“自分が言っていたこと”で返す** |

---

## 💡 こんな人におすすめ

- **日々の選択に迷いがある人**
- 自分の価値観を言語化したい人
- 過去の気づきを活かせずに忘れてしまう人
- 自分だけの“思考補助AI”を育ててみたい人

---

## 🔁 Echoが動く2つのモード

| モード | 内容 |
|--------|------|
| Phase1（学習） | LINEで送信した発言を分類・記録。人格を形成するための“思考のログ”を蓄積します。 |
| Phase2（応答） | 新たな発言に対して、過去の自分の言葉をもとにChatGPTが“自分として”返答します。 |

---

## 📚 ブログ解説（導入背景・技術・思想）

このプロジェクトの詳しい背景・構造・実装意図については、以下の記事で完全解説しています。

👉 [Echoの作り方｜過去の自分が答えるAIを作る方法を完全公開](https://www.pmi-sfbac.org/category/product/ai-echo-system/)

---

## 💻 Echoの動作画面

以下は、実際にEchoをLINE上で実行した画面イメージです：

- 左：Phase1（記録モード）  
- 右：Phase2（応答モード）

<div align="center">
<img src="https://raw.githubusercontent.com/bepro-engineer/ai-echo/main/images/echo_screen.png" width="600">
</div>

---

## 📌 プロジェクト構成

```plaintext
ai_echo/
├── app.py                 # Flaskアプリ本体（LINE受信・処理ルーティング）
├── .env                   # APIキーなどの環境変数
├── requirements.txt       # 必要ライブラリ
├── logic/
│   ├── chatgpt_logic.py   # ChatGPT呼び出し・プロンプト生成・記憶抽出
│   ├── db_utils.py        # SQLite操作（記憶・対話ログ保存）
│   └── __init__.py
└── images/
    └── echo_screen.png    # 動作イメージ

## 🛠️ セットアップ手順（Ubuntu）
# 1. GitHubからクローン
git clone https://github.com/bepro-engineer/ai_echo.git
cd ai_echo

# 2. 仮想環境の構築と起動
python3 -m venv .venv
source .venv/bin/activate

# 3. ライブラリのインストール
pip install -r requirements.txt

# 4. .envファイルの作成
# 以下の内容を.envファイルに記載（各種キーは自分で取得）
OPENAI_API_KEY=sk-xxxxxxx
LINE_CHANNEL_SECRET=xxxxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxx

# 5. データベース初期化（必要な場合）
python logic/db_utils.py

# 6. テスト起動
python app.py

# 💬 利用モードについて
PHASE_MODE=learn → Phase1（記録モード）

PHASE_MODE=reply → Phase2（応答モード）

.env 内で環境変数 PHASE_MODE を切り替えて使用してください。

# 🛡️ 注意事項
本プロジェクトは自己実験・学習目的で設計されています。

OpenAI APIの利用料金が発生するため、月額上限に注意してください。

記録されたデータにはプライバシー上の配慮が必要です。商用運用時はご注意ください。

## 📜 ライセンス
MIT License
---
