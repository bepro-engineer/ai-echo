from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3
from openai import OpenAI
import json

# .envファイルから環境変数を読み込む
load_dotenv()

# 🔁 カテゴリの定義とマッピングを一元管理
CATEGORY_CONFIG = {
    "感情": "心・精神",
    "健康": "健康",
    "趣味": "家庭・プライベート",
    "仕事": "社会・仕事",
    "お金": "経済・お金",
    "教養": "教養・知識"
}

# 📦 カテゴリ分類に使う候補カテゴリ一覧（GTPプロンプト用に）
CATEGORY_LABELS = list(CATEGORY_CONFIG.keys())
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
# 性的または恋愛的な内容、または人格的な恋人ロールプレイに限定しては禁止します。
# そのような話題が含まれる場合は「この話題には応答できません」と返答してください。
返答は**必ず50文字以内**で簡潔にしてください。
句読点を含めても100文字を超えないようにしてください。
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

# ✅ ユーザー発言をカテゴリに分類（Phase1と共通）
def getCategoryByGpt(message):
    categories = "」「".join(CATEGORY_LABELS)
    system_prompt = (
        f"以下のユーザー発言に対して、最も適切なカテゴリを1単語で返してください。\n"
        f"候補カテゴリには「{categories}」があります。\n"
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

# ✅ 自己ミッションを使ってユーザー発言をカテゴリに分類する（Phase1用）
def getCategoryByGptWithMission(user_message, mission_text):
    # 🧩 カテゴリ一覧を動的に生成
    categories = list(CATEGORY_CONFIG.keys())
    categories_str = "、".join(categories)

    # 💬 ChatGPTへのプロンプト文（動的カテゴリ）
    prompt_text = (
        f"以下の発言を、次のカテゴリの中から1語だけで分類してください。\n"
        f"出力はカテゴリ名の1単語のみとし、説明や装飾語は一切含めないでください。\n"
        f"候補カテゴリ: {categories_str}\n\n"
        f"発言: {user_message}"
    )

    # 🔧 メッセージ構築
    messages = [
        { "role": "system", "content": f"あなたの自己ミッションは以下の通りです：{mission_text}" },
        { "role": "user", "content": prompt_text }
    ]

    # 🔁 API呼び出し
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.3
    )

    # 📌 カテゴリ抽出と変換
    category_raw = response.choices[0].message.content.strip()

    # 🔍 CATEGORY_CONFIG にあれば変換、なければそのまま返す
    if category_raw in CATEGORY_CONFIG:
        return CATEGORY_CONFIG[category_raw]
    else:
        return category_raw

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

# Phase1専用（記憶蓄積用・自己ミッションを含まない）
# ==============================
# Phase1専用：学習目的の記憶生成
# ユーザーの発言内容に対して、
# カテゴリ分類→記憶参照→単純応答を行う。
# 自己ミッション等は使用しない。
# ==============================
def getChatGptReplyForLearning(user_message, category, target_user_id):
    # ① カテゴリ判定
 #   category = getCategoryByGpt(user_message)
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
        ],
        max_tokens=50,  # ✅ 約50文字以内になるようトークン制限
        temperature=0.7
    )

    reply_text = response.choices[0].message.content.strip()

    # ① 応答のトリム処理を先に実行
    reply_text = reply_text[:100]

    # ② その後に辞書で返却
    return {
        "reply_text": reply_text,
        "used_memory_ids": memory_ids
    }

# Phase2専用（人格模倣・self_mission参照あり）
# ==============================
# Phase2専用：人格模倣応答生成
# ユーザー発言をもとにカテゴリ判定し、
# 自己ミッション、記憶ログを活用して
# 応答を生成する人格模倣フェーズ。
# ==============================
def getChatGptReplyForReplying(user_message, target_user_id):
    """
    ユーザー発言をもとに、自己ミッションと記憶を活用して応答を生成。
    """

    # ① カテゴリ分類（GPT出力）
    raw_category = getCategoryByGpt(user_message)
    print(f"🔍 判定カテゴリ: {raw_category}")

    # ② カテゴリ名マッピング（self_mission.json のキーに合わせる）
    # マッピングはグローバル CATEGORY_CONFIG を参照
    mapped_category = CATEGORY_CONFIG.get(raw_category)
    if not mapped_category:
        print(f"[ERROR] 未対応カテゴリ: {raw_category}")
        mapped_category = raw_category  # fallback

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
    