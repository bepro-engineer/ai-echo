from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3
from openai import OpenAI
import json

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAIクライアント初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ 指定カテゴリの記憶を取得（忘却されていないもの）
def getMemoriesByCategory(category, target_user_id, limit=10):
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("""
        SELECT memory_id, content
        FROM memories
        WHERE is_forgotten = 0
          AND category = ?
          AND target_user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (category, target_user_id, limit))
    results = c.fetchall()
    conn.close()
    return results

# ✅ ChatGPTに与えるプロンプトを構築する（記憶と発話を組み合わせる）
def buildPrompt(memories, user_message, role_label):
    memory_section = "\n".join(f"- {m}" for m in memories)
    print(f"🔍 役割: {role_label}")

    # ✅ 安全性確保のための制限命令を追加
    restriction = """
あなたは記憶再現AIです。
性的な内容、疑似恋人としての振る舞い、または性的なロールプレイは一切行ってはいけません。
そのような話題が含まれる場合は「この話題には応答できません」と返答してください。
"""

    prompt = f"""
{restriction}

あなたは過去の記憶をもとに、人間らしく返答するAIです。
今からあなたは「{role_label}」として返答してください。

以下は過去に記録された重要な記憶です：

{memory_section}

この記憶をもとに、以下の発言に自然に返答してください：
「{user_message}」
"""
    return prompt.strip()

# ✅ ChatGPTで自然な応答を得る（カテゴリごとに記憶を絞る）
def getChatGptReply(user_message, target_user_id):
    # ① カテゴリ判定
    category = getCategoryByGpt(user_message)
    print(f"🔍 判定カテゴリ: {category}")

    # ② 指定カテゴリ × ユーザーIDの記憶を取得
    memory_items = getMemoriesByCategory(category, target_user_id)
    memory_ids = [m[0] for m in memory_items]
    memory_texts = [m[1] for m in memory_items]

    # ③ プロンプト生成
    role_label = os.getenv("TARGET_ROLE")
    prompt = buildPrompt(memory_texts, user_message, role_label)

    # ④ ChatGPT API呼び出し
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは過去の記憶を踏まえて人間らしく返答するAIです。"},
            {"role": "user", "content": prompt}
        ]
    )

    reply_text = response.choices[0].message.content.strip()

    return {
        "reply_text": reply_text,
        "used_memory_ids": memory_ids
    }

# ✅ ユーザー発言をカテゴリに分類（Phase1と共通）
def getCategoryByGpt(message):
    system_prompt = (
        "以下のユーザー発言に対して、最も適切なカテゴリを1単語で返してください。\n"
        "候補カテゴリには「家族」「仕事」「感情」「趣味」「健康」「その他」があります。\n"
        "出力はカテゴリ名のみで、他の説明を含めないでください。"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        category = response.choices[0].message.content.strip()
        return category if category else "uncategorized"
    except Exception as e:
        print("[ChatGPT Error]", e)
        return "uncategorized"

# ChatGPTを使ってカテゴリを判定する（自己ミッション付き）
def getCategoryByGptWithMission(user_message, mission_text):
    # OpenAIクライアントの初期化
    client = OpenAI()

    # プロンプト構築
    messages = [
        { "role": "system", "content": f"あなたの自己ミッションは以下の通りです：{mission_text}" },
        { "role": "user", "content": f"次の発言をカテゴリに分類してください：{user_message}" }
    ]

    # GPTに問い合わせ
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
    )

    # 結果を抽出
    category = response.choices[0].message.content.strip()
    return category


# 自己ミッションファイルを読み込む関数
def loadSelfMissionData() -> str:
    file_path = "./self_mission.txt"
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()
    
# ✅ 指定カテゴリの記憶を取得（Phase2専用）
def getMemoryForReply(category, target_user_id, limit=10):
    """
    対象ユーザーとカテゴリに一致する記憶をDBから取得します。
    忘却フラグが立っていない最新データを上位から取得します。
    """
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("""
        SELECT memory_id, content
        FROM memories
        WHERE is_forgotten = 0
          AND category = ?
          AND target_user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (category, target_user_id, limit))
    results = c.fetchall()
    conn.close()
    return results

# ✅ ユーザー発言と記憶ログを元にプロンプトを構築（Phase2）
def buildReplyPrompt(memories, user_message, role_label, self_mission, category):
    """
    記憶ログ・発言・自己ミッション情報からプロンプトを構築する。
    自己ミッションの各要素（mission, values, roles, prohibitions, categories）を
    明示的に参照させ、ChatGPTがそれらを必ず考慮するように指示を含めます。
    応答は必ず「常体（タメ口）」で行うよう明記します。
    """
    memory_section = "\n".join(f"- {m}" for m in memories)

    # 自己ミッション構造の各要素を抽出
    mission = self_mission.get("mission", "")
    values = "\n".join(f"- {v}" for v in self_mission.get("values", []))
    roles = "\n".join(f"- {r}" for r in self_mission.get("roles", []))
    prohibitions = "\n".join(f"- {p}" for p in self_mission.get("prohibitions", []))
    category_tips = "\n".join(f"- {c}" for c in self_mission.get("categories", {}).get(category, []))

    # 安全対策：システムレベルで制限する応答ルール
    restriction = """
あなたは記憶再現AIです。
以下のような応答は禁止されています：

- 性的な話題やロールプレイ
- 恋愛的・擬似恋人としての振る舞い
- 過度に依存的な会話誘導
- 励ましや慰めを目的とした感情的な対応

これらに該当する場合は「この話題には応答できません」と返答してください。
ただし、疲労・迷い・不安などの発言には、事実と判断支援を中心とした実用的返答を行ってください。
"""

    # ChatGPTへのプロンプト構築（常体指定を明記）
    prompt = f"""
{restriction}

あなたは、以下の情報を厳密に踏まえて自然な日本語で返答を行う、人格模倣型のAIです。
次の制約に必ず従ってください：

【自己ミッション（行動原理・判断基準）】
{mission}

【価値観（判断軸として常に考慮すること）】
{values}

【担っている人格的役割（この立場で発言すること）】
{roles}

【禁止されている応答スタイル（絶対に違反しないこと）】
{prohibitions}

【該当カテゴリ「{category}」における具体方針】
{category_tips}

【過去に蓄積された記憶（参考情報）】
{memory_section}

今からあなたは「{role_label}」という人格を再現し、以下の発言に返答してください。
返答文は【自分自身との内面的な対話】であるため、文体は必ず「常体（タメ口）」にしてください。
一人称・語尾・表現はすべて自分に話しかけるような口調にしてください。

「{user_message}」

この返答は、あくまで記憶とミッションに基づいた一貫性のある人格的返答でなければなりません。
また、返答はできるだけ簡潔にしてください。最大でも全角で200文字以内とします。
"""

    return prompt.strip()


# ✅ プロンプトをChatGPTに送信し、返答を取得
def callChatGptWithPrompt(prompt):
    """
    指定されたプロンプトをOpenAIへ送信し、返答を取得します。
    使用モデルはgpt-4oで固定。
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは過去の記憶を踏まえて人間らしく返答するAIです。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# ✅ Phase2用 ChatGPT応答生成の統合関数
def getChatGptReply(user_message, target_user_id):
    """
    ユーザー発言をもとに、自己ミッションと記憶を活用して応答を生成。
    """

    # ① カテゴリ分類（GPT出力）
    raw_category = getCategoryByGpt(user_message)
    print(f"🔍 判定カテゴリ: {raw_category}")

    # ② カテゴリ名マッピング（self_mission.json のキーに合わせる）
    CATEGORY_MAPPING = {
        "感情": "心・精神",
        "健康": "健康",
        "趣味": "家庭・プライベート",
        "仕事": "社会・仕事",
        "お金": "経済・お金",
        "教養": "教養・知識"
    }

    mapped_category = CATEGORY_MAPPING.get(raw_category)
    if not mapped_category:
        print(f"[ERROR] 未対応カテゴリ: {raw_category}")
        mapped_category = raw_category  # fallback

    # ③ 記憶ログ取得
    memory_items = getMemoryForReply(mapped_category, target_user_id)
    memory_ids = [m[0] for m in memory_items]
    memory_texts = [m[1] for m in memory_items]

    # ④ 自己ミッション・ロール取得
    self_mission = loadSelfMissionDataJson()
    role_label = os.getenv("TARGET_ROLE")

    # ⑤ プロンプト構築
    prompt = buildReplyPrompt(memory_texts, user_message, role_label, self_mission, mapped_category)

    print("[PROMPT DEBUG] =====")
    print(prompt)
    print("[PROMPT DEBUG] =====")

    # ⑥ ChatGPT呼び出し
    reply_text = callChatGptWithPrompt(prompt)

    return {
        "reply_text": reply_text,
        "used_memory_ids": memory_ids
    }


# ✅ 自己ミッションファイル（JSON構造）を読み込む関数
def loadSelfMissionDataJson() -> dict:
    file_path = "./self_mission.json"
    if not os.path.exists(file_path):
        print("[DEBUG] self_mission.json が存在しません")
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print("[DEBUG] self_mission.json の読み込みに成功しました")
            return data
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSONデコードエラー: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] self_mission.json の読み込みに失敗しました: {e}")
        return {}