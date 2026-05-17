"""存储层 - 按业务分库
- 知识库.db: documents, entities, relations, tasks, observations 等
- 认知闭环.db: claims
- 复盘.db: reviews, disciplines, plans, actions
"""
import hashlib
import json
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
        score INTEGER NOT NULL,
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
        total_score INTEGER NOT NULL,
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

    CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);
    CREATE INDEX IF NOT EXISTS idx_documents_document_key ON documents(document_key);
    """
    with get_knowledge_db() as conn:
        conn.executescript(schema)


def _init_claims_db() -> None:
    """初始化认知闭环数据库"""
    schema = """
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_type TEXT,
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
    """
    with get_claims_db() as conn:
        conn.executescript(schema)


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


# ===== 断言操作（认知闭环.db）=====

def list_claims(claim_type: str = None, limit: int = 100) -> list:
    with get_claims_db() as conn:
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
                claim_type, subject, statement, verification_status, source,
                source_document_id, notes, review_cycle, topic, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("claim_type"),
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
            ON CONFLICT(metric_key, observed_at, source) DO UPDATE SET
                value=excluded.value, unit=excluded.unit, metadata_json=excluded.metadata_json
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
    with get_claims_db() as conn:
        rows = conn.execute("""
            SELECT * FROM claims WHERE source_document_id IN (
                SELECT id FROM documents WHERE document_key = ?
            ) LIMIT ?
        """, (document_key, limit)).fetchall()
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
