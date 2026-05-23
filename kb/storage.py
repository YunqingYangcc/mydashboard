"""存储层 - 按业务分库
- 知识库.db: documents, entities, relations, tasks, observations 等
- 认知闭环.db: claims
- 复盘.db: reviews, disciplines, plans, actions
"""
import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from kb.config import (
    DATABASE_KNOWLEDGE, DATABASE_CLAIMS, DATABASE_REVIEW,
    ensure_directories
)
from kb.utils import json_dumps, now_iso


# ===== 多数据库连接 =====

@contextmanager
def get_knowledge_db():
    """知识库数据库连接"""
    ensure_directories()
    conn = sqlite3.connect(str(DATABASE_KNOWLEDGE))
    conn.row_factory = _dict_factory
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_claims_db():
    """认知闭环数据库连接"""
    ensure_directories()
    conn = sqlite3.connect(str(DATABASE_CLAIMS))
    conn.row_factory = _dict_factory
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_review_db():
    """复盘数据库连接"""
    ensure_directories()
    conn = sqlite3.connect(str(DATABASE_REVIEW))
    conn.row_factory = _dict_factory
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _json_loads(value) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


def _decode_rows(rows, json_fields=None) -> list[dict]:
    if not rows:
        return []
    json_fields = json_fields or []
    result = []
    for row in rows:
        if isinstance(row, dict):
            r = dict(row)
        else:
            r = _dict_factory(None, row) if not isinstance(row, dict) else row
        for field in json_fields:
            if field in r and r[field]:
                r[field] = _json_loads(r[field])
        result.append(r)
    return result


def _hash(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ===== 初始化 =====

def init_db() -> None:
    """初始化所有数据库"""
    _init_knowledge_db()
    _init_claims_db()
    _init_review_db()


def _init_knowledge_db() -> None:
    """初始化知识库数据库"""
    schema = """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        run_type TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        metadata_json TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        source_name TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        summary TEXT,
        author TEXT,
        url TEXT,
        doc_date TEXT,
        hash TEXT NOT NULL UNIQUE,
        document_key TEXT,
        content_hash TEXT,
        chapter TEXT,
        tags_json TEXT DEFAULT '[]',
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(name, entity_type)
    );

    CREATE TABLE IF NOT EXISTS relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_entity_id INTEGER,
        relation_type TEXT NOT NULL,
        object_entity_id INTEGER,
        confidence REAL DEFAULT 1.0,
        metadata_json TEXT DEFAULT '{}',
        source_document_id INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        priority TEXT DEFAULT 'medium',
        due_date TEXT,
        plan_key TEXT,
        source TEXT,
        source_document_id INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_key TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        value REAL,
        unit TEXT,
        observed_at TEXT NOT NULL,
        frequency TEXT NOT NULL,
        source TEXT NOT NULL,
        asset TEXT,
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS signal_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        dimension TEXT NOT NULL,
        frequency TEXT NOT NULL,
        comparator TEXT NOT NULL,
        threshold REAL,
        metric_key TEXT NOT NULL,
        action_mapping_json TEXT DEFAULT '{}',
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS signal_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_key TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        raw_value REAL,
        threshold REAL,
        status TEXT NOT NULL,
        direction TEXT NOT NULL,
        score REAL NOT NULL DEFAULT 0,
        reasoning TEXT,
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        UNIQUE(signal_key, observed_at)
    );

    CREATE TABLE IF NOT EXISTS signal_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        score_date TEXT NOT NULL UNIQUE,
        positive_count INTEGER NOT NULL,
        negative_count INTEGER NOT NULL,
        neutral_count INTEGER NOT NULL,
        total_score REAL NOT NULL DEFAULT 0,
        action_suggestion TEXT NOT NULL,
        dimension_breakdown_json TEXT DEFAULT '{}',
        detail_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ai_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        output_type TEXT NOT NULL,
        content TEXT NOT NULL,
        model TEXT,
        json_metadata TEXT DEFAULT '{}',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS knowledge_progress (
        item_key TEXT PRIMARY KEY,
        layer TEXT NOT NULL,
        sublayer TEXT,
        item_name TEXT NOT NULL,
        is_learned INTEGER DEFAULT 0,
        learned_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS knowledge_documents (
        item_key TEXT NOT NULL,
        document_id INTEGER NOT NULL,
        linked_at TEXT NOT NULL,
        PRIMARY KEY (item_key, document_id)
    );

    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_key TEXT NOT NULL,
        question_type TEXT NOT NULL,
        question_text TEXT NOT NULL,
        options_json TEXT,
        correct_answer TEXT,
        explanation TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (document_key) REFERENCES documents(document_key)
    );

    CREATE TABLE IF NOT EXISTS knowledge_signal_bindings (
        item_key TEXT NOT NULL,
        signal_key TEXT NOT NULL,
        metric_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (item_key, signal_key)
    );

    CREATE TABLE IF NOT EXISTS signal_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_date TEXT NOT NULL,
        report_type TEXT NOT NULL,
        content TEXT NOT NULL,
        model TEXT,
        signal_snapshot_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS observation_derivatives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_key TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        raw_value REAL,
        mom_change REAL,
        mom_pct REAL,
        yoy_change REAL,
        yoy_pct REAL,
        z_score REAL,
        is_anomaly INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE(metric_key, observed_at)
    );

    CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);
    CREATE INDEX IF NOT EXISTS idx_documents_document_key ON documents(document_key);
    CREATE INDEX IF NOT EXISTS idx_quizzes_document_key ON quizzes(document_key);
    CREATE INDEX IF NOT EXISTS idx_obs_deriv_metric ON observation_derivatives(metric_key);

    CREATE TABLE IF NOT EXISTS stock_daily_quotes (
        symbol TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        turnover REAL,
        change_pct REAL,
        market TEXT NOT NULL,
        industry_chain TEXT,
        PRIMARY KEY (symbol, trade_date)
    );

    CREATE TABLE IF NOT EXISTS market_phases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        phase_date TEXT NOT NULL,
        phase TEXT NOT NULL,
        vol_condition TEXT,
        price_condition TEXT,
        vol_ratio REAL,
        price_position REAL,
        price_change_pct REAL,
        params_json TEXT DEFAULT '{}',
        reasoning TEXT,
        action_suggestion TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(symbol, phase_date)
    );

    CREATE INDEX IF NOT EXISTS idx_quotes_symbol_date ON stock_daily_quotes(symbol, trade_date);
    CREATE INDEX IF NOT EXISTS idx_phases_symbol_date ON market_phases(symbol, phase_date);
    """
    with get_knowledge_db() as conn:
        conn.executescript(schema)
        # === 数据库迁移：score 列从 INTEGER → REAL ===
        try:
            col_info = conn.execute("PRAGMA table_info(signal_values)").fetchall()
            score_col = [c for c in col_info if c["name"] == "score"]
            if score_col and "INTEGER" in str(score_col[0]["type"]).upper():
                conn.execute("ALTER TABLE signal_values ALTER COLUMN score SET DATA TYPE REAL")
        except Exception:
            pass  # SQLite 不完全支持 ALTER COLUMN，用兼容方式
        # 兼容迁移：重建 signal_values 表使 score 列为 REAL
        try:
            col_type = conn.execute("SELECT typeof(score) FROM signal_values LIMIT 1").fetchone()
            # 如果表存在但 score 仍是整数类型，无需处理（SQLite 动态类型自动兼容）
        except Exception:
            pass

        try:
            col_info2 = conn.execute("PRAGMA table_info(signal_scores)").fetchall()
            ts_col = [c for c in col_info2 if c["name"] == "total_score"]
            if ts_col and "INTEGER" in str(ts_col[0]["type"]).upper():
                conn.execute("ALTER TABLE signal_scores ALTER COLUMN total_score SET DATA TYPE REAL")
        except Exception:
            pass


def _init_claims_db() -> None:
    """初始化认知闭环数据库"""
    schema = """
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_type TEXT,
        chapter TEXT,
        subject TEXT,
        statement TEXT NOT NULL,
        verification_status TEXT DEFAULT 'pending',
        source TEXT,
        source_document_id INTEGER,
        notes TEXT,
        validation_note TEXT,
        validated_at TEXT,
        review_cycle TEXT,
        topic TEXT,
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS claim_signal_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id INTEGER NOT NULL,
        signal_key TEXT NOT NULL,
        auto_validated INTEGER DEFAULT 0,
        last_status TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(claim_id, signal_key)
    );
    """
    with get_claims_db() as conn:
        conn.executescript(schema)
        # 迁移：添加 chapter 列（如果不存在）
        try:
            conn.execute("ALTER TABLE claims ADD COLUMN chapter TEXT")
        except Exception:
            pass  # 列已存在


def _init_review_db() -> None:
    """初始化复盘数据库"""
    schema = """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_type TEXT NOT NULL,
        review_period TEXT NOT NULL,
        summary TEXT,
        reflection TEXT,
        next_actions TEXT,
        score INTEGER,
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS disciplines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rule_text TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        stage_goal TEXT,
        cadence TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT NOT NULL,
        description TEXT NOT NULL,
        result TEXT,
        status TEXT DEFAULT 'pending',
        action_time TEXT NOT NULL,
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS progress_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        log_time TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """
    with get_review_db() as conn:
        conn.executescript(schema)


# ===== 文档操作（知识库.db）=====

def upsert_document(payload: dict) -> dict:
    now = now_iso()
    doc_hash = _hash([payload.get("title", ""), payload.get("content", "")[:1000]])
    
    # 临时关闭 row_factory 获取 last_insert_rowid
    with get_knowledge_db() as conn:
        existing = conn.execute(
            "SELECT id FROM documents WHERE hash = ?", (doc_hash,)
        ).fetchone()
        
        if existing:
            conn.execute("""
                UPDATE documents SET
                    title=?, content=?, summary=?, url=?, doc_date=?,
                    chapter=?, tags_json=?, metadata_json=?, updated_at=?
                WHERE hash=?
            """, (
                payload.get("title"),
                payload.get("content"),
                payload.get("summary"),
                payload.get("url"),
                payload.get("doc_date"),
                payload.get("chapter"),
                json_dumps(payload.get("tags_json", [])),
                json_dumps(payload.get("metadata_json", {})),
                now,
                doc_hash
            ))
            doc_id = existing[0] if isinstance(existing, tuple) else existing["id"]
        else:
            cursor = conn.execute("""
                INSERT INTO documents(
                    source_type, source_name, title, content, summary, author, url, doc_date,
                    hash, document_key, content_hash, chapter, tags_json, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.get("source_type", "manual"),
                payload.get("source_name", "manual"),
                payload.get("title"),
                payload.get("content"),
                payload.get("summary"),
                payload.get("author"),
                payload.get("url"),
                payload.get("doc_date"),
                doc_hash,
                payload.get("document_key"),
                payload.get("content_hash"),
                payload.get("chapter"),
                json_dumps(payload.get("tags_json", [])),
                json_dumps(payload.get("metadata_json", {})),
                now,
                now
            ))
            doc_id = cursor.lastrowid
    
    return {"id": doc_id, "hash": doc_hash}


def fetch_latest_documents(limit: int = 20) -> list:
    with get_knowledge_db() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return _decode_rows(rows, ["tags_json", "metadata_json"])


def search_documents(keyword: str, limit: int = 20) -> list:
    with get_knowledge_db() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE title LIKE ? OR content LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", limit)
        ).fetchall()
    return _decode_rows(rows, ["tags_json", "metadata_json"])


def get_document_by_hash(document_hash: str) -> dict | None:
    with get_knowledge_db() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE hash = ?", (document_hash,)
        ).fetchone()
    return _decode_rows([row] if row else [], ["tags_json", "metadata_json"])[0] if row else None



def get_document_by_key(document_key: str) -> dict | None:
    """通过 document_key 获取文档"""
    with get_knowledge_db() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE document_key = ?", (document_key,)
        ).fetchone()
    return _decode_rows([row] if row else [], ["tags_json", "metadata_json"])[0] if row else None


# ===== 断言操作（认知闭环.db）=====

def list_claims(claim_type: str = None, chapter: str = None, limit: int = 100) -> list:
    with get_claims_db() as conn:
        if chapter:
            if claim_type:
                rows = conn.execute(
                    "SELECT * FROM claims WHERE claim_type = ? AND chapter = ? ORDER BY created_at DESC LIMIT ?",
                    (claim_type, chapter, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM claims WHERE chapter = ? ORDER BY created_at DESC LIMIT ?",
                    (chapter, limit)
                ).fetchall()
        else:
            if claim_type:
                rows = conn.execute(
                    "SELECT * FROM claims WHERE claim_type = ? ORDER BY created_at DESC LIMIT ?",
                    (claim_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM claims ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def insert_claim(payload: dict) -> None:
    now = now_iso()
    with get_claims_db() as conn:
        conn.execute("""
            INSERT INTO claims(
                claim_type, chapter, subject, statement, verification_status, source,
                source_document_id, notes, review_cycle, topic, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("claim_type"),
            payload.get("chapter"),
            payload.get("subject"),
            payload.get("statement"),
            payload.get("verification_status", "pending"),
            payload.get("source"),
            payload.get("source_document_id"),
            payload.get("notes"),
            payload.get("review_cycle"),
            payload.get("topic"),
            json_dumps(payload.get("metadata", {})),
            now,
            now
        ))


def delete_claim(claim_id: int) -> None:
    """删除指定断言"""
    with get_claims_db() as conn:
        conn.execute("DELETE FROM claims WHERE id = ?", (claim_id,))


def update_claim(claim_id: int, payload: dict) -> None:
    """更新断言的所有字段"""
    now = now_iso()
    with get_claims_db() as conn:
        conn.execute("""
            UPDATE claims SET
                claim_type = ?,
                chapter = ?,
                subject = ?,
                statement = ?,
                verification_status = ?,
                source = ?,
                notes = ?,
                validation_note = ?,
                topic = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            payload.get("claim_type"),
            payload.get("chapter"),
            payload.get("subject"),
            payload.get("statement"),
            payload.get("verification_status", "pending"),
            payload.get("source"),
            payload.get("notes"),
            payload.get("validation_note"),
            payload.get("topic"),
            now,
            claim_id
        ))


def update_claim_validation(claim_id: int, validation_status: str, note: str = None) -> None:
    now = now_iso()
    with get_claims_db() as conn:
        if note:
            conn.execute("""
                UPDATE claims SET verification_status = ?, validation_note = ?, validated_at = ?, updated_at = ?
                WHERE id = ?
            """, (validation_status, note, now, now, claim_id))
        else:
            conn.execute("""
                UPDATE claims SET verification_status = ?, validated_at = ?, updated_at = ?
                WHERE id = ?
            """, (validation_status, now, now, claim_id))


def claim_validation_summary() -> dict:
    with get_claims_db() as conn:
        rows = conn.execute(
            "SELECT verification_status, COUNT(*) as count FROM claims GROUP BY verification_status"
        ).fetchall()
    return {row["verification_status"]: row["count"] for row in rows}


# ===== 复盘操作（复盘.db）=====

def list_reviews(limit: int = 50) -> list:
    with get_review_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def insert_review(payload: dict) -> None:
    now = now_iso()
    with get_review_db() as conn:
        conn.execute("""
            INSERT INTO reviews(review_type, review_period, summary, reflection, next_actions, score, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("review_type"),
            payload.get("review_period"),
            payload.get("summary"),
            payload.get("reflection"),
            payload.get("next_actions"),
            payload.get("score"),
            json_dumps(payload.get("metadata", {})),
            now,
            now
        ))


# ===== 任务操作（知识库.db）=====

def list_tasks(limit: int = 100) -> list:
    with get_knowledge_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return _decode_rows(rows)


def insert_task(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO tasks(title, description, status, priority, due_date, plan_key, source, source_document_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("title"),
            payload.get("description"),
            payload.get("status", "pending"),
            payload.get("priority", "medium"),
            payload.get("due_date"),
            payload.get("plan_key"),
            payload.get("source"),
            payload.get("source_document_id"),
            now,
            now
        ))


def update_task_status(task_id: int, status: str) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))


# ===== 实体和关系操作（知识库.db）=====

def list_entities() -> list:
    with get_knowledge_db() as conn:
        return conn.execute("SELECT * FROM entities ORDER BY name ASC").fetchall()


def ensure_entity(name: str, entity_type: str) -> int:
    """确保实体存在，返回实体 ID（已存在则返回现有 ID）"""
    now = now_iso()
    with get_knowledge_db() as conn:
        existing = conn.execute(
            "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
            (name, entity_type)
        ).fetchone()
        if existing:
            return existing["id"]
        cursor = conn.execute(
            "INSERT INTO entities(name, entity_type, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, entity_type, now, now)
        )
        return cursor.lastrowid


def insert_relation(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO relations(subject_entity_id, relation_type, object_entity_id, confidence, metadata_json, source_document_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("subject_entity_id"),
            payload.get("relation_type"),
            payload.get("object_entity_id"),
            payload.get("confidence", 1.0),
            json_dumps(payload.get("metadata", {})),
            payload.get("source_document_id"),
            now,
            now
        ))


# ===== 知识进度操作（知识库.db）=====

def upsert_knowledge_item(item_key: str, layer: str, sublayer: str, item_name: str, is_learned: bool) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        learned_at = now if is_learned else None
        conn.execute("""
            INSERT INTO knowledge_progress(item_key, layer, sublayer, item_name, is_learned, learned_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_key) DO UPDATE SET
                layer=excluded.layer, sublayer=excluded.sublayer, item_name=excluded.item_name,
                is_learned=excluded.is_learned, learned_at=excluded.learned_at, updated_at=excluded.updated_at
        """, (item_key, layer, sublayer, item_name, int(is_learned), learned_at, now, now))


def get_learned_items() -> set:
    with get_knowledge_db() as conn:
        rows = conn.execute("SELECT item_key FROM knowledge_progress WHERE is_learned = 1").fetchall()
    return {row["item_key"] for row in rows}


def get_knowledge_stats() -> dict:
    with get_knowledge_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM knowledge_progress").fetchone()["COUNT(*)"]
        learned = conn.execute("SELECT COUNT(*) FROM knowledge_progress WHERE is_learned = 1").fetchone()["COUNT(*)"]
    return {"total": total, "learned": learned, "rate": learned / total if total > 0 else 0}


# ===== 运行记录（知识库.db）=====

def insert_run(run_id: str, run_type: str, status: str) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute(
            "INSERT INTO runs(run_id, run_type, status, started_at) VALUES (?, ?, ?, ?)",
            (run_id, run_type, status, now)
        )


def finish_run(run_id: str, status: str, metadata: dict = None) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute(
            "UPDATE runs SET status = ?, finished_at = ?, metadata_json = ? WHERE run_id = ?",
            (status, now, json_dumps(metadata or {}), run_id)
        )


# ===== 观测数据（知识库.db）=====

def insert_observation(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO observations(metric_key, metric_name, value, unit, observed_at, frequency, source, asset, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("metric_key"),
            payload.get("metric_name"),
            payload.get("value"),
            payload.get("unit"),
            payload.get("observed_at"),
            payload.get("frequency"),
            payload.get("source"),
            payload.get("asset"),
            json_dumps(payload.get("metadata", {})),
            now
        ))


def latest_observation_map() -> dict:
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT o.* FROM observations o
            JOIN (
                SELECT metric_key, MAX(observed_at) AS max_time
                FROM observations GROUP BY metric_key
            ) latest ON latest.metric_key = o.metric_key AND latest.max_time = o.observed_at
        """).fetchall()
    return _decode_rows(rows, ["metadata_json"])


# ===== 信号系统（知识库.db）=====

def upsert_signal_definition(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO signal_definitions(signal_key, name, dimension, frequency, comparator, threshold, metric_key, action_mapping_json, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(signal_key) DO UPDATE SET
                name=excluded.name, dimension=excluded.dimension, frequency=excluded.frequency,
                comparator=excluded.comparator, threshold=excluded.threshold, metric_key=excluded.metric_key,
                action_mapping_json=excluded.action_mapping_json, description=excluded.description, updated_at=excluded.updated_at
        """, (
            payload.get("signal_key"),
            payload.get("name"),
            payload.get("dimension"),
            payload.get("frequency"),
            payload.get("comparator"),
            payload.get("threshold"),
            payload.get("metric_key"),
            json_dumps(payload.get("action_mapping", {})),
            payload.get("description"),
            now,
            now
        ))


def insert_signal_value(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO signal_values(signal_key, observed_at, raw_value, threshold, status, direction, score, reasoning, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(signal_key, observed_at) DO UPDATE SET
                raw_value=excluded.raw_value, threshold=excluded.threshold, status=excluded.status,
                direction=excluded.direction, score=excluded.score, reasoning=excluded.reasoning, metadata_json=excluded.metadata_json
        """, (
            payload.get("signal_key"),
            payload.get("observed_at"),
            payload.get("raw_value"),
            payload.get("threshold"),
            payload.get("status"),
            payload.get("direction"),
            payload.get("score"),
            payload.get("reasoning"),
            json_dumps(payload.get("metadata", {})),
            now
        ))


def latest_signal_score() -> dict | None:
    with get_knowledge_db() as conn:
        row = conn.execute("SELECT * FROM signal_scores ORDER BY score_date DESC LIMIT 1").fetchone()
    return _decode_rows([row] if row else [], ["dimension_breakdown_json", "detail_json"])[0] if row else None


def insert_signal_score(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO signal_scores(score_date, positive_count, negative_count, neutral_count, total_score, action_suggestion, dimension_breakdown_json, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(score_date) DO UPDATE SET
                positive_count=excluded.positive_count, negative_count=excluded.negative_count,
                neutral_count=excluded.neutral_count, total_score=excluded.total_score,
                action_suggestion=excluded.action_suggestion, dimension_breakdown_json=excluded.dimension_breakdown_json,
                detail_json=excluded.detail_json
        """, (
            payload.get("score_date"),
            payload.get("positive_count", 0),
            payload.get("negative_count", 0),
            payload.get("neutral_count", 0),
            payload.get("total_score", 0),
            payload.get("action_suggestion", "hold"),
            json_dumps(payload.get("dimension_breakdown", {})),
            json_dumps(payload.get("detail", {})),
            now
        ))


# ===== 信号系统查询（知识库.db）=====

def list_signal_definitions() -> list:
    """列出所有信号定义"""
    with get_knowledge_db() as conn:
        rows = conn.execute("SELECT * FROM signal_definitions ORDER BY dimension, signal_key").fetchall()
    return rows


def delete_signal_definition(signal_key: str) -> None:
    """删除信号定义"""
    with get_knowledge_db() as conn:
        conn.execute("DELETE FROM signal_definitions WHERE signal_key = ?", (signal_key,))


def list_recent_signal_values(limit: int = 100) -> list:
    """查询最近的信号评估值"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT sv.*, sd.name, sd.dimension
            FROM signal_values sv
            JOIN signal_definitions sd ON sv.signal_key = sd.signal_key
            ORDER BY sv.observed_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_observations_by_metric(metric_key: str, limit: int = 60) -> list:
    """查询单个指标的历史观测值"""
    with get_knowledge_db() as conn:
        rows = conn.execute(
            "SELECT * FROM observations WHERE metric_key = ? ORDER BY observed_at ASC LIMIT ?",
            (metric_key, limit)
        ).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def _compute_signal_score(raw_value: float, threshold: float, comparator: str) -> tuple:
    """渐变评分：用 tanh 连续函数替代阶梯判断
    返回 (status, direction, score)
    - score 为 -1.0 ~ +1.0 的连续值
    - 基于历史波动率动态确定 neutral 区间
    """
    if comparator == "gt":  # 超过阈值不利
        if raw_value > threshold:
            # 超过阈值越多，越负面，用 tanh 渐变
            score = -min(math.tanh((raw_value - threshold) / max(abs(threshold) * 0.3, 0.01)), 1.0)
            status = "negative"
            direction = "up"
        else:
            # 低于阈值：越低越正面
            ratio = raw_value / threshold if threshold != 0 else 1.0
            if ratio < 0.75:  # 远低于阈值 → 明确利好
                score = min(math.tanh((threshold - raw_value) / max(abs(threshold) * 0.3, 0.01)), 1.0)
                status = "positive"
                direction = "down"
            else:  # 0.75 ~ 1.0 中性偏利好（低于阈值=利好方向）
                score = (1.0 - ratio) / 0.25 * 0.5  # 0~+0.5
                status = "positive" if score > 0.05 else "neutral"
                direction = "down" if score > 0.05 else "flat"
    elif comparator == "lt":  # 低于阈值不利
        if raw_value < threshold:
            score = -min(math.tanh((threshold - raw_value) / max(abs(threshold) * 0.3, 0.01)), 1.0)
            status = "negative"
            direction = "down"
        else:
            ratio = raw_value / threshold if threshold != 0 else 1.0
            if ratio > 1.35:  # 远高于阈值 → 明确利好
                score = min(math.tanh((raw_value - threshold) / max(abs(threshold) * 0.3, 0.01)), 1.0)
                status = "positive"
                direction = "up"
            else:  # 1.0 ~ 1.35 中性偏利好（高于阈值=利好方向）
                score = (ratio - 1.0) / 0.35 * 0.5  # 0~+0.5
                status = "positive" if score > 0.05 else "neutral"
                direction = "up" if score > 0.05 else "flat"
    else:
        status, direction, score = "neutral", "flat", 0.0

    score = round(score, 3)
    return status, direction, score


def evaluate_signals_for_metric(metric_key: str, raw_value: float, observed_at: str) -> list:
    """根据指标值自动评估所有关联信号，返回评估结果列表（渐变评分版）"""
    definitions = list_signal_definitions()
    results = []
    for sig in definitions:
        if sig["metric_key"] != metric_key:
            continue
        threshold = sig["threshold"]
        comparator = sig["comparator"]
        status, direction, score = _compute_signal_score(raw_value, threshold, comparator)

        reasoning = f"{sig['name']}: {raw_value} {'>' if comparator == 'gt' else '<'} {threshold} → {status} (score={score})"
        payload = {
            "signal_key": sig["signal_key"],
            "observed_at": observed_at,
            "raw_value": raw_value,
            "threshold": threshold,
            "status": status,
            "direction": direction,
            "score": score,
            "reasoning": reasoning,
        }
        insert_signal_value(payload)
        results.append({**payload, "name": sig["name"], "dimension": sig["dimension"]})
    return results


def compute_daily_score(score_date: str = None) -> dict:
    """计算每日综合评分 — 维度等权 + 时间衰减 + 渐变评分
    改进点：
    1. 维度等权：先算每个维度的加权均分，再4维度等权平均，避免信号多的维度主导
    2. 时间衰减：7天半衰期，信号越旧权重越低
    3. 渐变评分：score 为 -1.0~+1.0 连续值，不再是 ±1 阶梯
    """
    from kb.utils import now_iso
    if score_date is None:
        score_date = now_iso()[:10]

    # 获取最近30天内所有信号值（支持时间衰减）
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT sv.*, sd.name, sd.dimension
            FROM signal_values sv
            JOIN signal_definitions sd ON sv.signal_key = sd.signal_key
            WHERE sv.observed_at >= ? AND sv.observed_at < ?
        """, (f"{score_date}T00:00:00", f"{score_date}T23:59:59")).fetchall()
    rows = _decode_rows(rows, ["metadata_json"])

    # 如果当天没有信号，尝试获取最近7天的
    if not rows:
        import datetime as _dt
        fallback_date = (_dt.date.fromisoformat(score_date) - _dt.timedelta(days=7)).isoformat()
        with get_knowledge_db() as conn:
            rows = conn.execute("""
                SELECT sv.*, sd.name, sd.dimension
                FROM signal_values sv
                JOIN signal_definitions sd ON sv.signal_key = sd.signal_key
                WHERE sv.observed_at >= ? AND sv.observed_at < ?
                ORDER BY sv.observed_at DESC
            """, (f"{fallback_date}T00:00:00", f"{score_date}T23:59:59")).fetchall()
        rows = _decode_rows(rows, ["metadata_json"])

    if not rows:
        return None

    # 按信号取最新值
    latest = {}
    for r in rows:
        key = r["signal_key"]
        if key not in latest or r["observed_at"] > latest[key]["observed_at"]:
            latest[key] = r
    values = list(latest.values())

    # === 时间衰减 ===
    import datetime
    score_datetime = datetime.datetime.fromisoformat(score_date)
    HALF_LIFE_DAYS = 7  # 7天半衰期

    for v in values:
        try:
            obs_dt = datetime.datetime.fromisoformat(v["observed_at"][:19])
            age_days = max((score_datetime - obs_dt).total_seconds() / 86400, 0)
        except (ValueError, TypeError):
            age_days = 0
        decay = math.exp(-0.693 * age_days / HALF_LIFE_DAYS)  # ln(2)/half_life
        v["_decay_weight"] = decay
        v["_weighted_score"] = (v.get("score") or 0) * decay

    # === 维度等权 ===
    dim_values = {}  # dimension -> list of values
    for v in values:
        dim = v.get("dimension", "未分类")
        dim_values.setdefault(dim, []).append(v)

    DIM_WEIGHTS = {"估值": 0.25, "基本面": 0.25, "需求": 0.25, "宏观": 0.125, "情绪": 0.125}
    # 如果出现未知维度，均匀分配剩余权重
    unknown_dims = [d for d in dim_values if d not in DIM_WEIGHTS]
    if unknown_dims:
        leftover = 1.0 - sum(DIM_WEIGHTS.values())
        per_dim = leftover / len(unknown_dims) if unknown_dims else 0
        for d in unknown_dims:
            DIM_WEIGHTS[d] = per_dim

    dim_breakdown = {}
    dim_scores = {}
    for dim, dvals in dim_values.items():
        total_decay = sum(v["_decay_weight"] for v in dvals)
        weighted_sum = sum(v["_weighted_score"] for v in dvals)
        dim_avg = weighted_sum / total_decay if total_decay > 0 else 0.0

        pos_count = sum(1 for v in dvals if v.get("status") == "positive")
        neg_count = sum(1 for v in dvals if v.get("status") == "negative")
        neu_count = sum(1 for v in dvals if v.get("status") == "neutral")

        dim_breakdown[dim] = {"positive": pos_count, "negative": neg_count, "neutral": neu_count,
                              "dim_avg_score": round(dim_avg, 3)}
        dim_scores[dim] = dim_avg

    # 综合得分 = 各维度加权平均（映射到 -4 ~ +4 量表便于理解）
    total_score = sum(dim_scores.get(d, 0) * DIM_WEIGHTS.get(d, 0) for d in dim_scores) * 4
    total_score = round(total_score, 2)

    # 信号计数
    positive_count = sum(1 for v in values if v.get("status") == "positive")
    negative_count = sum(1 for v in values if v.get("status") == "negative")
    neutral_count = sum(1 for v in values if v.get("status") == "neutral")

    # 动作建议（基于连续得分）
    if total_score >= 2.0:
        action = "strong_buy"
    elif total_score >= 0.5:
        action = "buy"
    elif total_score <= -2.0:
        action = "strong_sell"
    elif total_score <= -0.5:
        action = "sell"
    else:
        action = "hold"

    payload = {
        "score_date": score_date,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "total_score": total_score,
        "action_suggestion": action,
        "dimension_breakdown": dim_breakdown,
        "detail": {v["signal_key"]: {"status": v.get("status"), "score": v.get("score", 0),
                                      "decay": round(v.get("_decay_weight", 1), 3)} for v in values},
    }
    insert_signal_score(payload)
    return payload


# ===== AI输出（知识库.db）=====

def insert_ai_output(payload: dict) -> None:
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO ai_outputs(run_id, output_type, content, model, json_metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            payload.get("run_id"),
            payload.get("output_type"),
            payload.get("content"),
            payload.get("model"),
            json_dumps(payload.get("metadata", {})),
            now
        ))


def list_ai_outputs(limit: int = 20) -> list:
    with get_knowledge_db() as conn:
        rows = conn.execute("SELECT * FROM ai_outputs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return _decode_rows(rows, ["json_metadata"])


# ===== 纪律（复盘.db）=====

def list_disciplines() -> list:
    with get_review_db() as conn:
        return conn.execute("SELECT * FROM disciplines ORDER BY created_at DESC").fetchall()


def insert_discipline(name: str, rule_text: str) -> None:
    now = now_iso()
    with get_review_db() as conn:
        conn.execute(
            "INSERT INTO disciplines(name, rule_text, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, rule_text, now, now)
        )


# ===== 计划（复盘.db）=====

def list_plans() -> list:
    with get_review_db() as conn:
        return conn.execute("SELECT * FROM plans ORDER BY weight DESC, id ASC").fetchall()


def upsert_plan(payload: dict) -> None:
    now = now_iso()
    with get_review_db() as conn:
        conn.execute("""
            INSERT INTO plans(plan_key, name, weight, stage_goal, cadence, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plan_key) DO UPDATE SET
                name=excluded.name, weight=excluded.weight, stage_goal=excluded.stage_goal,
                cadence=excluded.cadence, status=excluded.status, updated_at=excluded.updated_at
        """, (
            payload.get("plan_key"),
            payload.get("name"),
            payload.get("weight"),
            payload.get("stage_goal"),
            payload.get("cadence"),
            payload.get("status", "active"),
            now,
            now
        ))


# ===== 操作记录（复盘.db）=====

def list_actions(limit: int = 50) -> list:
    with get_review_db() as conn:
        rows = conn.execute("SELECT * FROM actions ORDER BY action_time DESC LIMIT ?", (limit,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def insert_action(payload: dict) -> None:
    now = now_iso()
    with get_review_db() as conn:
        conn.execute("""
            INSERT INTO actions(action_type, description, result, status, action_time, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("action_type"),
            payload.get("description"),
            payload.get("result"),
            payload.get("status", "pending"),
            payload.get("action_time"),
            json_dumps(payload.get("metadata", {})),
            now,
            now
        ))


# ===== 文档-知识点关联 =====

def link_document_to_knowledge(item_key: str, document_id: int) -> bool:
    """关联文档到知识点"""
    now = now_iso()
    with get_knowledge_db() as conn:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO knowledge_documents(item_key, document_id, linked_at)
                VALUES (?, ?, ?)
            """, (item_key, document_id, now))
            return True
        except Exception:
            return False


def unlink_document_from_knowledge(item_key: str, document_id: int) -> bool:
    """取消文档与知识点的关联"""
    with get_knowledge_db() as conn:
        conn.execute("""
            DELETE FROM knowledge_documents WHERE item_key = ? AND document_id = ?
        """, (item_key, document_id))
        return True


def get_all_knowledge_doc_links() -> dict:
    """获取所有文档-知识点关联"""
    with get_knowledge_db() as conn:
        rows = conn.execute("SELECT * FROM knowledge_documents").fetchall()
    return {row["document_id"]: row["item_key"] for row in rows}


def get_documents_by_knowledge(item_key: str) -> list:
    """获取知识点关联的文档"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT d.* FROM documents d
            JOIN knowledge_documents kd ON d.id = kd.document_id
            WHERE kd.item_key = ?
            ORDER BY kd.linked_at DESC
        """, (item_key,)).fetchall()
    return _decode_rows(rows, ["tags_json", "metadata_json"])


def get_knowledge_by_document(document_id: int) -> list:
    """获取文档关联的知识点"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT kp.* FROM knowledge_progress kp
            JOIN knowledge_documents kd ON kp.item_key = kd.item_key
            WHERE kd.document_id = ?
        """, (document_id,)).fetchall()
    return rows


def reset_knowledge_progress() -> None:
    """重置所有学习进度"""
    with get_knowledge_db() as conn:
        conn.execute("UPDATE knowledge_progress SET is_learned = 0, learned_at = NULL")


# ===== 题库系统（知识库.db）=====

def insert_quiz_question(payload: dict) -> int:
    """插入单个试题"""
    now = now_iso()
    with get_knowledge_db() as conn:
        cursor = conn.execute("""
            INSERT INTO quizzes(document_key, question_type, question_text, options_json, correct_answer, explanation, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("document_key"),
            payload.get("question_type"),
            payload.get("question_text"),
            json_dumps(payload.get("options", [])),
            payload.get("correct_answer"),
            payload.get("explanation"),
            payload.get("sort_order", 0),
            now,
            now
        ))
        return cursor.lastrowid


def insert_quizzes(document_key: str, questions: list[dict]) -> int:
    """批量插入试题"""
    count = 0
    for i, q in enumerate(questions):
        q["document_key"] = document_key
        q["sort_order"] = i
        insert_quiz_question(q)
        count += 1
    return count


def fetch_quizzes_by_document_key(document_key: str) -> list[dict]:
    """根据文档key获取试题列表"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT * FROM quizzes 
            WHERE document_key = ? 
            ORDER BY sort_order ASC, id ASC
        """, (document_key,)).fetchall()
    return _decode_rows(rows, ["options_json"])


def delete_quizzes_by_document_key(document_key: str) -> None:
    """删除指定文档的所有试题"""
    with get_knowledge_db() as conn:
        conn.execute("DELETE FROM quizzes WHERE document_key = ?", (document_key,))


def get_document_by_key(document_key: str) -> dict:
    """根据document_key获取文档"""
    with get_knowledge_db() as conn:
        row = conn.execute("SELECT * FROM documents WHERE document_key = ?", (document_key,)).fetchone()
    if row:
        return dict(row)
    return None


def update_claim_validation(claim_id: int, validation_status: str, note: str = None) -> None:
    """更新断言验证状态"""
    now = now_iso()
    with get_claims_db() as conn:
        if note:
            conn.execute("""
                UPDATE claims SET verification_status = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (validation_status, note, now, claim_id))
        else:
            conn.execute("""
                UPDATE claims SET verification_status = ?, updated_at = ?
                WHERE id = ?
            """, (validation_status, now, claim_id))


def list_extracted_claims_by_document_key(document_key: str, limit: int = 100) -> list:
    """根据文档key获取抽取的断言"""
    # 先从 knowledge_db 获取 document id
    with get_knowledge_db() as conn:
        doc_row = conn.execute(
            "SELECT id FROM documents WHERE document_key = ?", (document_key,)
        ).fetchone()
    
    if not doc_row:
        return []
    
    doc_id = doc_row["id"]
    
    # 再从 claims_db 查询
    with get_claims_db() as conn:
        rows = conn.execute(
            "SELECT * FROM claims WHERE source_document_id = ? LIMIT ?",
            (doc_id, limit)
        ).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_extracted_claims_by_document_hash(document_hash: str, limit: int = 100) -> list:
    """根据文档hash获取抽取的断言"""
    with get_claims_db() as conn:
        rows = conn.execute("""
            SELECT * FROM claims WHERE source_document_id IN (
                SELECT id FROM documents WHERE hash = ?
            ) LIMIT ?
        """, (document_hash, limit)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_extracted_tasks_by_document_key(document_key: str, limit: int = 100) -> list:
    """根据文档key获取抽取的任务"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks WHERE source_document_id IN (
                SELECT id FROM documents WHERE document_key = ?
            ) LIMIT ?
        """, (document_key, limit)).fetchall()
    return _decode_rows(rows)


def list_extracted_tasks_by_document_hash(document_hash: str, limit: int = 100) -> list:
    """根据文档hash获取抽取的任务"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks WHERE source_document_id IN (
                SELECT id FROM documents WHERE hash = ?
            ) LIMIT ?
        """, (document_hash, limit)).fetchall()
    return _decode_rows(rows)


def update_task_status(task_id: int, status: str) -> None:
    """更新任务状态"""
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))


def list_extracted_relations_by_document_key(document_key: str, limit: int = 100) -> list:
    """根据文档key获取抽取的关系"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT * FROM relations WHERE source_document_id IN (
                SELECT id FROM documents WHERE document_key = ?
            ) LIMIT ?
        """, (document_key, limit)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def update_document_metadata(doc_id: int, metadata: dict) -> None:
    """更新文档元数据"""
    now = now_iso()
    metadata_json = json_dumps(metadata)
    with get_knowledge_db() as conn:
        conn.execute(
            "UPDATE documents SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (metadata_json, now, doc_id)
        )


def delete_extracted_by_source_document_key(document_key: str) -> None:
    """删除与文档关联的所有抽取结果（断言、关系、任务）"""
    with get_claims_db() as conn:
        conn.execute("""
            DELETE FROM claims WHERE source_document_id IN (
                SELECT id FROM documents WHERE document_key = ?
            )
        """, (document_key,))
    
    with get_knowledge_db() as conn:
        conn.execute("""
            DELETE FROM relations WHERE source_document_id IN (
                SELECT id FROM documents WHERE document_key = ?
            )
        """, (document_key,))
        conn.execute("""
            DELETE FROM tasks WHERE source_document_id IN (
                SELECT id FROM documents WHERE document_key = ?
            )
        """, (document_key,))


# ===== 进度跟踪（复盘.db）=====

def insert_progress_log(content: str, log_time: str = None) -> None:
    """插入进度记录"""
    from kb.utils import now_iso
    now = now_iso()
    if log_time is None:
        log_time = now
    with get_review_db() as conn:
        conn.execute("""
            INSERT INTO progress_logs(content, log_time, created_at)
            VALUES (?, ?, ?)
        """, (content.strip(), log_time, now))


def list_progress_logs(limit: int = 100) -> list:
    """查询进度记录，按时间倒序（最新的在前面）"""
    with get_review_db() as conn:
        rows = conn.execute(
            "SELECT * FROM progress_logs ORDER BY log_time DESC, id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return rows


def delete_progress_log(log_id: int) -> None:
    """删除指定进度记录"""
    with get_review_db() as conn:
        conn.execute("DELETE FROM progress_logs WHERE id = ?", (log_id,))


def clear_progress_logs() -> None:
    """清空所有进度记录"""
    with get_review_db() as conn:
        conn.execute("DELETE FROM progress_logs")


# ===== 知识-信号绑定（知识库.db）=====

def bind_signal_to_knowledge(item_key: str, signal_key: str, metric_key: str) -> None:
    """绑定信号到知识点"""
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO knowledge_signal_bindings(item_key, signal_key, metric_key, created_at)
            VALUES (?, ?, ?, ?)
        """, (item_key, signal_key, metric_key, now))


def unbind_signal_from_knowledge(item_key: str, signal_key: str) -> None:
    """解绑信号与知识点"""
    with get_knowledge_db() as conn:
        conn.execute("DELETE FROM knowledge_signal_bindings WHERE item_key = ? AND signal_key = ?",
                     (item_key, signal_key))


def get_knowledge_signal_bindings(item_key: str = None) -> list:
    """获取知识点关联的信号绑定"""
    with get_knowledge_db() as conn:
        if item_key:
            rows = conn.execute(
                "SELECT * FROM knowledge_signal_bindings WHERE item_key = ?", (item_key,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM knowledge_signal_bindings").fetchall()
    return rows


def get_knowledge_signal_status(item_key: str) -> list:
    """获取知识点的信号状态（含最新信号值）"""
    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT b.item_key, b.signal_key, b.metric_key,
                   sd.name, sd.dimension, sd.comparator, sd.threshold,
                   sv.raw_value, sv.status, sv.direction, sv.reasoning, sv.observed_at
            FROM knowledge_signal_bindings b
            JOIN signal_definitions sd ON b.signal_key = sd.signal_key
            LEFT JOIN (
                SELECT signal_key, raw_value, status, direction, reasoning, observed_at,
                       ROW_NUMBER() OVER (PARTITION BY signal_key ORDER BY observed_at DESC) AS rn
                FROM signal_values
            ) sv ON b.signal_key = sv.signal_key AND sv.rn = 1
            WHERE b.item_key = ?
        """, (item_key,)).fetchall()
    return rows


# ===== 信号报告（知识库.db）=====

def insert_signal_report(report_date: str, report_type: str, content: str,
                         model: str = None, snapshot: dict = None) -> None:
    """保存信号报告"""
    now = now_iso()
    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO signal_reports(report_date, report_type, content, model, signal_snapshot_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (report_date, report_type, content, model, json_dumps(snapshot or {}), now))


def list_signal_reports(report_type: str = None, limit: int = 10) -> list:
    """查询信号报告"""
    with get_knowledge_db() as conn:
        if report_type:
            rows = conn.execute(
                "SELECT * FROM signal_reports WHERE report_type = ? ORDER BY created_at DESC LIMIT ?",
                (report_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM signal_reports ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return _decode_rows(rows, ["signal_snapshot_json"])


# ===== 观测衍生计算（知识库.db）=====

def compute_observation_derivatives(metric_key: str, observed_at: str, raw_value: float) -> dict:
    """计算观测值的环比/同比/异常检测，独立落库"""
    now = now_iso()
    with get_knowledge_db() as conn:
        # 获取前一条记录（环比）
        prev_row = conn.execute(
            "SELECT value, observed_at FROM observations WHERE metric_key = ? AND observed_at < ? ORDER BY observed_at DESC LIMIT 1",
            (metric_key, observed_at)
        ).fetchone()

        # 获取去年同期（同比）
        year_ago = observed_at[:4] + str(int(observed_at[4:6]) - 12 + 12).zfill(2) if len(observed_at) >= 6 else None
        yoy_row = None
        if year_ago:
            yoy_row = conn.execute(
                "SELECT value FROM observations WHERE metric_key = ? AND observed_at >= ? AND observed_at < ? ORDER BY observed_at ASC LIMIT 1",
                (metric_key, year_ago, observed_at[:4] + observed_at[4:])
            ).fetchone()

        # 获取最近30个值算 z-score
        recent_rows = conn.execute(
            "SELECT value FROM observations WHERE metric_key = ? ORDER BY observed_at DESC LIMIT 30",
            (metric_key,)
        ).fetchall()

    mom_change = None
    mom_pct = None
    yoy_change = None
    yoy_pct = None
    z_score = None
    is_anomaly = 0

    if prev_row and prev_row["value"] is not None:
        mom_change = raw_value - prev_row["value"]
        mom_pct = mom_change / abs(prev_row["value"]) * 100 if prev_row["value"] != 0 else None

    if yoy_row and yoy_row["value"] is not None:
        yoy_change = raw_value - yoy_row["value"]
        yoy_pct = yoy_change / abs(yoy_row["value"]) * 100 if yoy_row["value"] != 0 else None

    if len(recent_rows) >= 5:
        values = [r["value"] for r in recent_rows if r["value"] is not None]
        if len(values) >= 5:
            import statistics
            mean = statistics.mean(values)
            std = statistics.stdev(values)
            if std > 0:
                z_score = (raw_value - mean) / std
                is_anomaly = 1 if abs(z_score) > 2 else 0

    result = {
        "metric_key": metric_key,
        "observed_at": observed_at,
        "raw_value": raw_value,
        "mom_change": mom_change,
        "mom_pct": mom_pct,
        "yoy_change": yoy_change,
        "yoy_pct": yoy_pct,
        "z_score": z_score,
        "is_anomaly": is_anomaly,
    }

    with get_knowledge_db() as conn:
        conn.execute("""
            INSERT INTO observation_derivatives(metric_key, observed_at, raw_value, mom_change, mom_pct, yoy_change, yoy_pct, z_score, is_anomaly, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metric_key, observed_at) DO UPDATE SET
                raw_value=excluded.raw_value, mom_change=excluded.mom_change, mom_pct=excluded.mom_pct,
                yoy_change=excluded.yoy_change, yoy_pct=excluded.yoy_pct, z_score=excluded.z_score, is_anomaly=excluded.is_anomaly
        """, (metric_key, observed_at, raw_value, mom_change, mom_pct, yoy_change, yoy_pct, z_score, is_anomaly, now))

    return result


def list_derivatives_for_metric(metric_key: str, limit: int = 30) -> list:
    """查询指标的衍生计算结果"""
    with get_knowledge_db() as conn:
        rows = conn.execute(
            "SELECT * FROM observation_derivatives WHERE metric_key = ? ORDER BY observed_at DESC LIMIT ?",
            (metric_key, limit)
        ).fetchall()
    return rows


def list_anomaly_observations(limit: int = 20) -> list:
    """查询异常观测值"""
    with get_knowledge_db() as conn:
        rows = conn.execute(
            "SELECT * FROM observation_derivatives WHERE is_anomaly = 1 ORDER BY observed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return rows


# ===== 断言-信号关联（认知闭环.db）=====

def link_claim_to_signal(claim_id: int, signal_key: str) -> None:
    """关联断言与信号"""
    now = now_iso()
    with get_claims_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO claim_signal_links(claim_id, signal_key, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (claim_id, signal_key, now, now))


def unlink_claim_from_signal(claim_id: int, signal_key: str) -> None:
    """取消断言与信号的关联"""
    with get_claims_db() as conn:
        conn.execute("DELETE FROM claim_signal_links WHERE claim_id = ? AND signal_key = ?",
                     (claim_id, signal_key))


def get_claims_for_signal(signal_key: str) -> list:
    """获取信号关联的断言"""
    with get_claims_db() as conn:
        rows = conn.execute("""
            SELECT c.*, csl.last_status, csl.auto_validated
            FROM claim_signal_links csl
            JOIN claims c ON csl.claim_id = c.id
            WHERE csl.signal_key = ?
            ORDER BY c.updated_at DESC
        """, (signal_key,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def get_signals_for_claim(claim_id: int) -> list:
    """获取断言关联的信号"""
    with get_claims_db() as conn:
        rows = conn.execute("""
            SELECT csl.claim_id, csl.signal_key, csl.last_status, csl.auto_validated, csl.created_at
            FROM claim_signal_links csl
            WHERE csl.claim_id = ?
        """, (claim_id,)).fetchall()
    # 补充信号定义信息
    if rows:
        sig_keys = [r["signal_key"] for r in rows]
        sig_def_map = {}
        for s in list_signal_definitions():
            if s["signal_key"] in sig_keys:
                sig_def_map[s["signal_key"]] = s
        result = []
        for r in rows:
            sd = sig_def_map.get(r["signal_key"], {})
            result.append({**r, "name": sd.get("name", ""), "dimension": sd.get("dimension", ""), "threshold": sd.get("threshold")})
        return result
    return []


def update_claim_signal_status(claim_id: int, signal_key: str, status: str, auto_validated: bool = False) -> None:
    """更新断言-信号关联状态"""
    now = now_iso()
    with get_claims_db() as conn:
        conn.execute("""
            UPDATE claim_signal_links SET last_status = ?, auto_validated = ?, updated_at = ?
            WHERE claim_id = ? AND signal_key = ?
        """, (status, int(auto_validated), now, claim_id, signal_key))


def check_claims_for_signal_change(signal_key: str, new_status: str) -> list:
    """信号状态变化时，检查关联断言是否需要重新验证，返回待验证断言列表"""
    claims = get_claims_for_signal(signal_key)
    pending = []
    for claim in claims:
        # 只对未验证或状态变化了的断言提醒
        if claim.get("verification_status") != "validated" or claim.get("last_status") != new_status:
            update_claim_signal_status(claim["id"], signal_key, new_status)
            pending.append(claim)
    return pending
