import sqlite3
import os
import json

# 使用するSQLiteデータベースのファイル名
DB_NAME = "memory.db"

# データベースが存在しない場合、初期化処理を行う
def initDatabase():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        # テーブル存在チェック（memoriesがなければ全部再作成）
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
        if not c.fetchone():
            # 必要な全テーブルを作成（Phase1準拠、承諾済構造）
            c.execute("""
                -- ユーザーの記憶を保存するテーブル
                CREATE TABLE memories (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,       -- 記憶ID
                    content TEXT NOT NULL,                              -- 記憶の内容
                    category TEXT DEFAULT 'uncategorized',              -- 分類カテゴリ
                    weight INTEGER DEFAULT 1,                           -- 重み（初期値1）
                    target_user_id TEXT NOT NULL,                       -- 対象ユーザー
                    is_forgotten INTEGER DEFAULT 0,                     -- 忘却フラグ
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP           -- 作成日時
                )
            """)

            c.execute("""
                -- AIとユーザー間の対話ログを保存するテーブル
                CREATE TABLE dialogues (
                    dialogue_id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 対話ID
                    target_user_id TEXT NOT NULL,                       -- 対象ユーザー
                    sender_user_id TEXT NOT NULL,                       -- 発信者ユーザーID
                    message_type TEXT NOT NULL,                         -- メッセージ種別
                    is_ai_generated BOOLEAN NOT NULL,                   -- AI生成かどうか
                    text TEXT NOT NULL,                                 -- メッセージ本文
                    memory_refs TEXT,                                   -- 関連記憶ID群
                    prompt_version TEXT,                                -- プロンプトバージョン
                    temperature REAL,                                   -- 温度パラメータ
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP           -- 作成日時
                )
            """)

            c.execute("""
                -- 対象ユーザーと記憶間の関連性や操作ログを保存するテーブル
                CREATE TABLE weights (
                    weight_id INTEGER PRIMARY KEY AUTOINCREMENT,        -- 重みID
                    memory_id INTEGER NOT NULL,                         -- 対象記憶ID
                    target_user_id TEXT,                                -- 関連ユーザーID
                    interact TEXT,                                      -- 操作種別（例: reinforce, weaken）
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,          -- 作成日時
                    FOREIGN KEY (memory_id) REFERENCES memories(memory_id) -- 外部キー参照
                )
            """)

            conn.commit()
            print("Database schema initialized.")
        else:
            print("Database tables already exist.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ✅ 記憶と発話ログを1つのトランザクションで同時に保存（カテゴリ＋weight＝1）
def registerMemoryAndDialogue(
    user_id,
    message,
    content,
    category,
    memory_refs=None,
    is_ai_generated=False,
    sender_user_id="self",
    message_type="input"
):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # ✅ 記憶を保存（初期weight=1）
        c.execute(
            """
            INSERT INTO memories
              (content, category, weight, target_user_id)
            VALUES
              (?, ?, ?, ?)
            """,
            (content, category, 1, user_id)
        )
        memory_id = c.lastrowid

        # ✅ 発話ログ（dialogues）へ保存
        c.execute(
            """
            INSERT INTO dialogues (
                target_user_id, sender_user_id, message_type,
                is_ai_generated, text, memory_refs,
                prompt_version, temperature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                sender_user_id,
                message_type,
                is_ai_generated,
                message,
                json.dumps(memory_refs) if memory_refs else None,
                None,
                None
            )
        )

        # ✅ 重み初期ログ
        c.execute(
            "INSERT INTO weights (memory_id, interact) VALUES (?, ?)",
            (memory_id, "初期登録（weight=1）")
        )

        conn.commit()
        print("Memory and dialogue registered.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ✅ 全記憶（忘却フラグなし）
def getAllMemories():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT memory_id, content, category, weight FROM memories WHERE is_forgotten = 0")
    results = c.fetchall()
    conn.close()
    return results

# ✅ 重み履歴を追加
def insertWeightLog(memory_id, interact):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO weights (memory_id, interact) VALUES (?, ?)",
            (memory_id, interact)
        )
        conn.commit()
        print(f"Weight log inserted for memory_id={memory_id}")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ✅ 特定memory_idに紐づく重み履歴を取得
def getWeightLogsByMemoryId(memory_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT interact, created_at FROM weights WHERE memory_id = ? ORDER BY created_at DESC",
        (memory_id,)
    )
    logs = c.fetchall()
    conn.close()
    return logs

# ✅ 全weight履歴を取得（管理・表示用）
def getAllWeightLogs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT weight_id, memory_id, interact, created_at FROM weights ORDER BY created_at DESC")
    logs = c.fetchall()
    conn.close()
    return logs

# ✅ 単体実行でのテスト実行
if __name__ == "__main__":
    initDatabase()
    # 任意テスト用サンプル
    # registerMemoryAndDialogue("U123", "これはテスト発言です", "これは記憶です", "感情")
    # print(getAllMemories())
    # insertWeightLog(1, "再評価：強調対象としてweight変更候補")
    # print(getWeightLogsByMemoryId(1))
