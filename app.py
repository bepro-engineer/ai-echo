from flask import Flask, request, abort
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage
from logic.chatgpt_logic import loadSelfMissionData, getCategoryByGptWithMission
import openai

from dotenv import load_dotenv
import os
import json

from logic.db_utils import initDatabase, registerMemoryAndDialogue
from logic.chatgpt_logic import getChatGptReplyForLearning, getChatGptReplyForReplying, getCategoryByGpt
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# 環境変数の読み込み
load_dotenv()

# 各種設定値を取得
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")
memory_target_user_id = os.getenv("MEMORY_TARGET_USER_ID")
phase_mode = os.getenv("PHASE_MODE")  # learn または reply

# 致命的な設定ミスの検出
if not memory_target_user_id:
    raise ValueError("MEMORY_TARGET_USER_ID is not set. Startup aborted.")
if phase_mode not in ["learn", "reply"]:
    raise ValueError("PHASE_MODE must be 'learn' or 'reply'. Startup aborted.")

# FlaskとLINE初期化
app = Flask(__name__)
handler = WebhookHandler(channel_secret)
messaging_api = MessagingApi(ApiClient(Configuration(access_token=access_token)))

# DB初期化
initDatabase()

@app.route("/ai_echo_webhook", methods=["POST"])
def ai_echo_webhook():
    signature = request.headers["X-Line-Signature"]
    body_text = request.get_data(as_text=True)
    body_json = request.get_json(force=True)

    events = body_json.get("events", [])
    if not events:
        print("⚠️ Warning: No events in body.")
        return "NO EVENT", 200

    user_id = events[0]["source"]["userId"]
    print("user_id:", user_id)

    try:
        handler.handle(body_text, signature)
    except Exception as e:
        print(f"[{phase_mode.upper()}] Webhook Error: {e}")
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handleMessage(event):
    try:
        user_id = event.source.user_id
        message = event.message.text

        NG_WORDS = ["セフレ", "エロ", "性欲", "キスして", "付き合って", "いやらしい"]
        if any(ng in message.lower() for ng in NG_WORDS):
            reply_text = "この話題には応答できません。"
            reply = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
            messaging_api.reply_message(reply)
            return

        print(f"[{phase_mode.upper()}] Received message from user_id: {user_id}")
        print(f"[{phase_mode.upper()}] MEMORY_TARGET_USER_ID: {memory_target_user_id}")

        if phase_mode == "learn":
            if user_id == memory_target_user_id:
                # ① 自己ミッションファイルを読み込み
                self_mission_data = loadSelfMissionData()

                # ② カテゴリを判定（自己ミッション込み）
                category = getCategoryByGptWithMission(message, self_mission_data)

                # ③ ChatGPTから応答を得る（記憶はまだ少ないが、空でも動作可能）
                gpt_result = getChatGptReplyForLearning(message, category, memory_target_user_id)
                reply_text = gpt_result["reply_text"]
                memory_refs = json.dumps(gpt_result["used_memory_ids"])

                # ④ ユーザー入力を記録（input）
                registerMemoryAndDialogue(
                    user_id=user_id,
                    message=message,
                    content=message,
                    category=category,
                    memory_refs=None,
                    is_ai_generated=False,
                    sender_user_id="self",
                    message_type="input"
                )

                # ⑤ ChatGPT応答を記録（reply）
                registerMemoryAndDialogue(
                    user_id=user_id,
                    message=reply_text,
                    content=reply_text,
                    category="応答",
                    memory_refs=memory_refs,
                    is_ai_generated=True,
                    sender_user_id="self",
                    message_type="reply"
                )

                # ⑥ 応答をLINEに返す
                reply = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
                messaging_api.reply_message(reply)
                print("Learn mode: Input and GPT reply recorded")

            else:
                print("Ignored: Not memory target (LEARN mode)")

        elif phase_mode == "reply":
#            if user_id == memory_target_user_id:
#                print("Ignored: memory_target_user_id should not speak in REPLY mode")
#                return
            try:
                # ChatGPT応答を生成（指定ユーザー人格で応答）
                gpt_result = getChatGptReplyForReplying(message, memory_target_user_id)
                reply_text = gpt_result["reply_text"]
                memory_refs = json.dumps(gpt_result["used_memory_ids"])

                # 応答ログを記録（Phase2では user_id は発話者、memory_target_user_id は人格保持者）
                registerMemoryAndDialogue(
                    user_id=memory_target_user_id,       # 応答人格のユーザーID
                    message=message,                     # 入力された発言（記録上の文脈として残す）
                    content=reply_text,                  # 実際のAI応答
                    category="応答",                      # 一律で応答カテゴリ
                    memory_refs=memory_refs,             # 使用された記憶IDリスト
                    is_ai_generated=True,
                    sender_user_id=user_id,              # 発話者のID（記憶者とは別）
                    message_type="reply"
                )

                # LINEへ返信を返す
                reply = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
                messaging_api.reply_message(reply)
                print("Reply sent and recorded (REPLY mode)")

            except Exception as e:
                print(f"[REPLY] Handler Error: {e}")


    except Exception as e:
        print(f"[{phase_mode.upper()}] Handler Error: {e}")

if __name__ == '__main__':
    print("✅ initDatabase() を実行開始")
    initDatabase()
    print("✅ initDatabase() を完了")
    print(f"🌐 DEBUG: phase_mode is {phase_mode}")
    app.run(debug=False, host='0.0.0.0', port=5002)
