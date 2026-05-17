import hashlib
import json
import os
from contextlib import contextmanager
from typing import Any

import psycopg2
import sqlite3

from kb.config import DATABASE_PATH, ensure_directories
from kb.document_utils import build_document_key
from kb.utils import json_dumps, now_iso


# 检测使用哪种数据库（强制使用 SQLite，避免 Supabase 连接问题）
USE_POSTGRES = False

# PostgreSQL Schema（无 FTS5）
PG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
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
    tags_json TEXT DEFAULT '[]',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    metric_key TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value REAL,
    unit TEXT,
    observed_at TEXT NOT NULL,
    frequency TEXT NOT NULL,
    source TEXT NOT NULL,
    asset TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(metric_key, observed_at, source)
);

CREATE TABLE IF NOT EXISTS signal_definitions (
    id SERIAL PRIMARY KEY,
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
    id SERIAL PRIMARY KEY,
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
    id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS actions (
    id SERIAL PRIMARY KEY,
    action_time TEXT NOT NULL,
    asset TEXT NOT NULL,
    action_type TEXT NOT NULL,
    size REAL,
    reason_signal_ids TEXT,
    risk_control TEXT,
    result_followup TEXT,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS disciplines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id SERIAL PRIMARY KEY,
    plan_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    weight REAL NOT NULL,
    stage_goal TEXT NOT NULL,
    cadence TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    plan_key TEXT,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    cadence TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    source TEXT NOT NULL DEFAULT 'manual',
    source_document_key TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(name, entity_type)
);

CREATE TABLE IF NOT EXISTS relations (
    id SERIAL PRIMARY KEY,
    subject_entity_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    object_entity_id INTEGER NOT NULL,
    evidence_document_id INTEGER,
    confidence REAL DEFAULT 0.5,
    note TEXT,
    source_document_key TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    claim_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    statement TEXT NOT NULL,
    stance TEXT NOT NULL DEFAULT 'neutral',
    evidence_document_id INTEGER,
    review_cycle TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    validation_status TEXT DEFAULT 'pending',
    validation_note TEXT,
    validated_at TEXT,
    source_document_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ai_outputs (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    role TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    json_metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_progress (
    id SERIAL PRIMARY KEY,
    item_key TEXT NOT NULL UNIQUE,
    layer TEXT NOT NULL,
    sublayer TEXT,
    item_name TEXT NOT NULL,
    is_learned INTEGER NOT NULL DEFAULT 0,
    learned_at TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id SERIAL PRIMARY KEY,
    item_key TEXT NOT NULL,
    document_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(item_key, document_id),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
"""

# SQLite Schema
SQLITE_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

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
    tags_json TEXT DEFAULT '[]',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title, content, summary, content='documents', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, content, summary)
    VALUES (new.id, new.title, new.content, COALESCE(new.summary, ''));
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, content, summary)
    VALUES ('delete', old.id, old.title, old.content, COALESCE(old.summary, ''));
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, content, summary)
    VALUES ('delete', old.id, old.title, old.content, COALESCE(old.summary, ''));
    INSERT INTO documents_fts(rowid, title, content, summary)
    VALUES (new.id, new.title, new.content, COALESCE(new.summary, ''));
END;

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
    created_at TEXT NOT NULL,
    UNIQUE(metric_key, observed_at, source)
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

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_time TEXT NOT NULL,
    asset TEXT NOT NULL,
    action_type TEXT NOT NULL,
    size REAL,
    reason_signal_ids TEXT,
    risk_control TEXT,
    result_followup TEXT,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS disciplines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    weight REAL NOT NULL,
    stage_goal TEXT NOT NULL,
    cadence TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_key TEXT,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    cadence TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    source TEXT NOT NULL DEFAULT 'manual',
    source_document_key TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

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

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(name, entity_type)
);

CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_entity_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    object_entity_id INTEGER NOT NULL,
    evidence_document_id INTEGER,
    confidence REAL DEFAULT 0.5,
    note TEXT,
    source_document_key TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    statement TEXT NOT NULL,
    stance TEXT NOT NULL DEFAULT 'neutral',
    evidence_document_id INTEGER,
    review_cycle TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    validation_status TEXT DEFAULT 'pending',
    validation_note TEXT,
    validated_at TEXT,
    source_document_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ai_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    role TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    json_metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_key TEXT NOT NULL UNIQUE,
    layer TEXT NOT NULL,
    sublayer TEXT,
    item_name TEXT NOT NULL,
    is_learned INTEGER NOT NULL DEFAULT 0,
    learned_at TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_key TEXT NOT NULL,
    document_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(item_key, document_id),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
"""

if not USE_POSTGRES:
    ensure_directories()


# ===== 连接管理 =====

@contextmanager
def get_connection():
    """统一连接接口"""
    if USE_POSTGRES:
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            raise RuntimeError("DATABASE_URL 环境变量未设置，请检查 Streamlit Cloud Secrets 配置")
        
        # 使用 Supavisor 连接池（支持 IPv4）
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="Yyq@2147483648",
            host="pool.kvmvaodlznttvtfsjqpl.supabase.com",
            port="5432",
            sslmode="require"
        )
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = _sqlite_row_factory
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _sqlite_row_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# ===== 参数占位符 =====
def _p(n: int) -> str:
    """返回第 n 个参数的占位符"""
    return "%s" if USE_POSTGRES else "?"


# ===== 初始化 =====
def init_db() -> None:
    schema = PG_SCHEMA_SQL if USE_POSTGRES else SQLITE_SCHEMA_SQL
    with get_connection() as conn:
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(schema)
            cur.close()
        else:
            conn.executescript(schema)
        _run_migrations(conn)


def _run_migrations(conn) -> None:
    if USE_POSTGRES:
        # PostgreSQL 迁移
        conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='documents' AND column_name='document_key') 
                THEN ALTER TABLE documents ADD COLUMN document_key TEXT; END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='documents' AND column_name='content_hash') 
                THEN ALTER TABLE documents ADD COLUMN content_hash TEXT; END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='claims' AND column_name='validation_status') 
                THEN ALTER TABLE claims ADD COLUMN validation_status TEXT DEFAULT 'pending'; END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='claims' AND column_name='validation_note') 
                THEN ALTER TABLE claims ADD COLUMN validation_note TEXT; END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='claims' AND column_name='validated_at') 
                THEN ALTER TABLE claims ADD COLUMN validated_at TEXT; END IF;
            END $$;
        """)
        # 创建索引
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_document_key ON documents(document_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_validation_status ON claims(validation_status)")
    else:
        # SQLite 迁移
        def _table_columns(table_name: str) -> set[str]:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            # PRAGMA 返回: cid, name, type, notnull, dflt_value, pk
            if rows and isinstance(rows[0], dict):
                return {row['name'] for row in rows}
            return {row[1] for row in rows}
        
        def _add_column(table_name: str, col: str, defn: str):
            if col not in _table_columns(table_name):
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {defn}")
        
        _add_column("documents", "document_key", "TEXT")
        _add_column("documents", "content_hash", "TEXT")
        _add_column("claims", "validation_status", "TEXT DEFAULT 'pending'")
        _add_column("claims", "validation_note", "TEXT")
        _add_column("claims", "validated_at", "TEXT")
        
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_document_key ON documents(document_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_validation_status ON claims(validation_status)")


def _json_loads(value) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        loaded = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _decode_rows(rows, json_fields: list[str]) -> list[dict]:
    parsed = []
    for row in rows:
        item = dict(row) if not isinstance(row, dict) else row
        for field in json_fields:
            if item.get(field):
                item[field] = _json_loads(item[field])
        parsed.append(item)
    return parsed


def _hash(parts: list[str]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update((part or "").encode("utf-8"))
        digest.update(b"||")
    return digest.hexdigest()


# ===== 文档操作 =====
def upsert_document(payload: dict) -> dict:
    payload = dict(payload)
    payload["document_key"] = payload.get("document_key") or build_document_key(payload)
    payload["content_hash"] = payload.get("content_hash") or _hash([payload.get("content", "")])
    payload["hash"] = payload.get("hash") or _hash([payload["document_key"], payload.get("content", "")])
    now = now_iso()
    
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO documents(
                    source_type, source_name, title, content, summary, author, url, doc_date,
                    document_key, content_hash, hash, tags_json, metadata_json, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(hash) DO UPDATE SET
                    title=EXCLUDED.title,
                    content=EXCLUDED.content,
                    summary=EXCLUDED.summary,
                    author=EXCLUDED.author,
                    url=EXCLUDED.url,
                    doc_date=EXCLUDED.doc_date,
                    content_hash=EXCLUDED.content_hash,
                    tags_json=EXCLUDED.tags_json,
                    metadata_json=EXCLUDED.metadata_json,
                    updated_at=EXCLUDED.updated_at
            """, (
                payload["source_type"], payload["source_name"], payload["title"], payload["content"],
                payload.get("summary"), payload.get("author"), payload.get("url"), payload.get("doc_date"),
                payload["document_key"], payload["content_hash"], payload["hash"],
                json_dumps(payload.get("tags", [])), json_dumps(payload.get("metadata", {})),
                now, now
            ))
            row = conn.execute(
                "SELECT id, document_key, content_hash, hash FROM documents WHERE document_key = %s",
                (payload["document_key"],)
            ).fetchone()
        else:
            conn.execute("""
                INSERT INTO documents(
                    source_type, source_name, title, content, summary, author, url, doc_date,
                    document_key, content_hash, hash, tags_json, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hash) DO UPDATE SET
                    title=excluded.title,
                    content=excluded.content,
                    summary=excluded.summary,
                    author=excluded.author,
                    url=excluded.url,
                    doc_date=excluded.doc_date,
                    content_hash=excluded.content_hash,
                    tags_json=excluded.tags_json,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
            """, (
                payload["source_type"], payload["source_name"], payload["title"], payload["content"],
                payload.get("summary"), payload.get("author"), payload.get("url"), payload.get("doc_date"),
                payload["document_key"], payload["content_hash"], payload["hash"],
                json_dumps(payload.get("tags", [])), json_dumps(payload.get("metadata", {})),
                now, now
            ))
            row = conn.execute(
                "SELECT id, document_key, content_hash, hash FROM documents WHERE document_key = ?",
                (payload["document_key"],)
            ).fetchone()
    return row


def fetch_latest_documents(limit: int = 20) -> list:
    with get_connection() as conn:
        if USE_POSTGRES:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY COALESCE(doc_date, created_at) DESC, id DESC LIMIT %s",
                (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY COALESCE(doc_date, created_at) DESC, id DESC LIMIT ?",
                (limit,)
            ).fetchall()
    return _decode_rows(rows, ["tags_json", "metadata_json"])


def search_documents(keyword: str, limit: int = 20) -> list:
    keyword = keyword.strip()
    if not keyword:
        return fetch_latest_documents(limit)
    
    with get_connection() as conn:
        if USE_POSTGRES:
            # PostgreSQL 用 ILIKE 搜索
            pattern = f"%{keyword}%"
            rows = conn.execute("""
                SELECT * FROM documents 
                WHERE title ILIKE %s OR content ILIKE %s OR summary ILIKE %s
                ORDER BY COALESCE(doc_date, created_at) DESC, id DESC LIMIT %s
            """, (pattern, pattern, pattern, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT d.* FROM documents_fts f
                JOIN documents d ON d.id = f.rowid
                WHERE documents_fts MATCH ?
                ORDER BY COALESCE(d.doc_date, d.created_at) DESC, d.id DESC LIMIT ?
            """, (keyword, limit)).fetchall()
    return _decode_rows(rows, ["tags_json", "metadata_json"])


def get_document_by_hash(document_hash: str) -> dict | None:
    with get_connection() as conn:
        p = _p(1)
        row = conn.execute(f"SELECT * FROM documents WHERE hash = {p}", (document_hash,)).fetchone()
    if not row:
        return None
    return _decode_rows([row], ["tags_json", "metadata_json"])[0]


def get_document_by_key(document_key: str) -> dict | None:
    with get_connection() as conn:
        p = _p(1)
        row = conn.execute(f"SELECT * FROM documents WHERE document_key = {p}", (document_key,)).fetchone()
    if not row:
        return None
    return _decode_rows([row], ["tags_json", "metadata_json"])[0]


def update_document_metadata(document_id: int, metadata: dict) -> None:
    with get_connection() as conn:
        p = _p(1)
        conn.execute(
            f"UPDATE documents SET metadata_json = {p}, updated_at = {p} WHERE id = {p}",
            (json_dumps(metadata), now_iso(), document_id)
        )


# ===== Claims =====
def list_claims(claim_type: str = None, limit: int = 100) -> list:
    sql = "SELECT * FROM claims WHERE 1=1"
    params = []
    if claim_type:
        sql += f" AND claim_type = {_p(len(params)+1)}"
        params.append(claim_type)
    sql += f" ORDER BY updated_at DESC LIMIT {_p(len(params)+1)}"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_extracted_claims_by_document_key(document_key: str, limit: int = 100) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"""
            SELECT * FROM claims WHERE source_document_key = {p}
            ORDER BY updated_at DESC LIMIT {p}
        """, (document_key, limit)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_extracted_claims_by_document_hash(document_hash: str, limit: int = 100) -> list:
    return list_extracted_claims_by_document_key(document_hash, limit)


def update_claim_validation(claim_id: int, validation_status: str, note: str = None) -> None:
    now = now_iso()
    with get_connection() as conn:
        p = _p(1)
        conn.execute(f"""
            UPDATE claims SET validation_status = {p}, validation_note = {p},
            validated_at = {p}, updated_at = {p} WHERE id = {p}
        """, (validation_status, note, now, now, claim_id))


# ===== 其他函数（简化版，保持兼容）=====
def insert_claim(payload: dict) -> None:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO claims(
                    claim_type, subject, statement, stance, evidence_document_id, review_cycle,
                    status, validation_status, validation_note, validated_at,
                    source_document_key, created_at, updated_at, metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload["claim_type"], payload["subject"], payload["statement"],
                payload.get("stance", "neutral"), payload.get("evidence_document_id"),
                payload.get("review_cycle"), payload.get("status", "active"),
                payload.get("validation_status", "pending"), payload.get("validation_note"),
                payload.get("validated_at"), payload.get("source_document_key"),
                now, now, json_dumps(payload.get("metadata", {}))
            ))
        else:
            conn.execute("""
                INSERT INTO claims(
                    claim_type, subject, statement, stance, evidence_document_id, review_cycle,
                    status, validation_status, validation_note, validated_at,
                    source_document_key, created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["claim_type"], payload["subject"], payload["statement"],
                payload.get("stance", "neutral"), payload.get("evidence_document_id"),
                payload.get("review_cycle"), payload.get("status", "active"),
                payload.get("validation_status", "pending"), payload.get("validation_note"),
                payload.get("validated_at"), payload.get("source_document_key"),
                now, now, json_dumps(payload.get("metadata", {}))
            ))


# ===== 任务 =====
def list_tasks(limit: int = 100) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(
            f"SELECT * FROM tasks ORDER BY priority DESC, due_date ASC, id DESC LIMIT {p}",
            (limit,)
        ).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def insert_task(payload: dict) -> None:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO tasks(
                    plan_key, title, description, due_date, cadence, status, priority,
                    source, source_document_key, metadata_json, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload.get("plan_key"), payload["title"], payload.get("description"),
                payload.get("due_date"), payload.get("cadence"), payload.get("status", "todo"),
                payload.get("priority", "medium"), payload.get("source", "manual"),
                payload.get("source_document_key"), json_dumps(payload.get("metadata", {})),
                now, now
            ))
        else:
            conn.execute("""
                INSERT INTO tasks(
                    plan_key, title, description, due_date, cadence, status, priority,
                    source, source_document_key, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.get("plan_key"), payload["title"], payload.get("description"),
                payload.get("due_date"), payload.get("cadence"), payload.get("status", "todo"),
                payload.get("priority", "medium"), payload.get("source", "manual"),
                payload.get("source_document_key"), json_dumps(payload.get("metadata", {})),
                now, now
            ))


def update_task_status(task_id: int, status: str) -> None:
    with get_connection() as conn:
        p = _p(1)
        conn.execute(
            f"UPDATE tasks SET status = {p}, updated_at = {p} WHERE id = {p}",
            (status, now_iso(), task_id)
        )


def list_extracted_tasks_by_document_key(document_key: str, limit: int = 100) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"""
            SELECT * FROM tasks WHERE source_document_key = {p}
            ORDER BY created_at DESC LIMIT {p}
        """, (document_key, limit)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_extracted_tasks_by_document_hash(document_hash: str, limit: int = 100) -> list:
    return list_extracted_tasks_by_document_key(document_hash, limit)


# ===== 知识进度 =====
def upsert_knowledge_item(item_key: str, layer: str, sublayer: str, item_name: str, is_learned: bool) -> None:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO knowledge_progress(
                    item_key, layer, sublayer, item_name, is_learned, learned_at, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(item_key) DO UPDATE SET
                    is_learned = EXCLUDED.is_learned,
                    learned_at = CASE WHEN EXCLUDED.is_learned = 1 THEN COALESCE(knowledge_progress.learned_at, EXCLUDED.learned_at) ELSE NULL END,
                    updated_at = EXCLUDED.updated_at
            """, (item_key, layer, sublayer, item_name, 1 if is_learned else 0, now if is_learned else None, now, now))
        else:
            conn.execute("""
                INSERT INTO knowledge_progress(
                    item_key, layer, sublayer, item_name, is_learned, learned_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_key) DO UPDATE SET
                    is_learned = excluded.is_learned,
                    learned_at = CASE WHEN excluded.is_learned = 1 THEN COALESCE(knowledge_progress.learned_at, excluded.learned_at) ELSE NULL END,
                    updated_at = excluded.updated_at
            """, (item_key, layer, sublayer, item_name, 1 if is_learned else 0, now if is_learned else None, now, now))


def get_learned_items() -> set:
    with get_connection() as conn:
        rows = conn.execute("SELECT item_key FROM knowledge_progress WHERE is_learned = 1").fetchall()
    return {row["item_key"] if isinstance(row, dict) else row[0] for row in rows}


def reset_knowledge_progress() -> None:
    with get_connection() as conn:
        conn.execute("UPDATE knowledge_progress SET is_learned = 0, learned_at = NULL")


def get_knowledge_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as cnt FROM knowledge_progress").fetchone()
        learned = conn.execute("SELECT COUNT(*) as cnt FROM knowledge_progress WHERE is_learned = 1").fetchone()
        total_cnt = total["cnt"] if isinstance(total, dict) else total[0]
        learned_cnt = learned["cnt"] if isinstance(learned, dict) else learned[0]
    return {"total": total_cnt, "learned": learned_cnt}


# ===== 知识点-文档关联 =====
def link_document_to_knowledge(item_key: str, document_id: int) -> bool:
    now = now_iso()
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                conn.execute("""
                    INSERT INTO knowledge_documents (item_key, document_id, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(item_key, document_id) DO NOTHING
                """, (item_key, document_id, now))
            else:
                conn.execute("""
                    INSERT OR IGNORE INTO knowledge_documents (item_key, document_id, created_at)
                    VALUES (?, ?, ?)
                """, (item_key, document_id, now))
        return True
    except Exception:
        return False


def unlink_document_from_knowledge(item_key: str, document_id: int) -> bool:
    try:
        with get_connection() as conn:
            p = _p(1)
            conn.execute(f"""
                DELETE FROM knowledge_documents WHERE item_key = {p} AND document_id = {p}
            """, (item_key, document_id))
        return True
    except Exception:
        return False


def get_documents_by_knowledge(item_key: str) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"""
            SELECT d.* FROM documents d
            INNER JOIN knowledge_documents kd ON d.id = kd.document_id
            WHERE kd.item_key = {p}
            ORDER BY kd.created_at DESC
        """, (item_key,)).fetchall()
    return rows


def get_knowledge_by_document(document_id: int) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"""
            SELECT item_key FROM knowledge_documents WHERE document_id = {p}
        """, (document_id,)).fetchall()
    return [row["item_key"] if isinstance(row, dict) else row[0] for row in rows]


def get_all_knowledge_doc_links() -> dict:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT kd.item_key, d.id, d.title, d.source_name
            FROM knowledge_documents kd
            INNER JOIN documents d ON d.id = kd.document_id
            ORDER BY kd.item_key, kd.created_at DESC
        """).fetchall()
        
        result = {}
        for row in rows:
            key = row["item_key"] if isinstance(row, dict) else row[0]
            if key not in result:
                result[key] = []
            result[key].append({
                "id": row["id"] if isinstance(row, dict) else row[1],
                "title": row["title"] if isinstance(row, dict) else row[2],
                "source_name": row["source_name"] if isinstance(row, dict) else row[3]
            })
        return result


# ===== 关系 =====
def list_extracted_relations_by_document_key(document_key: str) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"""
            SELECT r.*, s.name AS subject_name, o.name AS object_name
            FROM relations r
            JOIN entities s ON s.id = r.subject_entity_id
            JOIN entities o ON o.id = r.object_entity_id
            WHERE r.source_document_key = {p}
            ORDER BY r.created_at DESC
        """, (document_key,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_extracted_relations_by_document_hash(document_hash: str) -> list:
    return list_extracted_relations_by_document_key(document_hash)


# ===== 其他查询函数（保持兼容）=====
def latest_observation_map() -> dict:
    with get_connection() as conn:
        if USE_POSTGRES:
            rows = conn.execute("""
                SELECT o.* FROM observations o
                JOIN (
                    SELECT metric_key, MAX(observed_at) AS max_time
                    FROM observations GROUP BY metric_key
                ) latest ON latest.metric_key = o.metric_key AND latest.max_time = o.observed_at
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT o.* FROM observations o
                JOIN (
                    SELECT metric_key, MAX(observed_at) AS max_time
                    FROM observations GROUP BY metric_key
                ) latest ON latest.metric_key = o.metric_key AND latest.max_time = o.observed_at
            """).fetchall()
    return {row["metric_key"]: _decode_rows([row], ["metadata_json"])[0] for row in rows}


def latest_signal_score() -> dict | None:
    with get_connection() as conn:
        p = _p(1)
        row = conn.execute(f"SELECT * FROM signal_scores ORDER BY score_date DESC LIMIT {p}", (1,)).fetchone()
    if not row:
        return None
    return _decode_rows([row], ["dimension_breakdown_json", "detail_json"])[0]


def list_reviews(limit: int = 50) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"SELECT * FROM reviews ORDER BY created_at DESC LIMIT {p}", (limit,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_actions(limit: int = 50) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"SELECT * FROM actions ORDER BY action_time DESC LIMIT {p}", (limit,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_disciplines() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM disciplines ORDER BY created_at DESC").fetchall()


def list_entities() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM entities ORDER BY name ASC").fetchall()


def list_plans() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM plans ORDER BY weight DESC, id ASC").fetchall()


def list_signal_values(limit: int = 50) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"""
            SELECT sv.*, sd.name, sd.dimension
            FROM signal_values sv
            JOIN signal_definitions sd ON sd.signal_key = sv.signal_key
            ORDER BY sv.observed_at DESC, sv.signal_key ASC LIMIT {p}
        """, (limit,)).fetchall()
    return _decode_rows(rows, ["metadata_json"])


def list_ai_outputs(limit: int = 20) -> list:
    with get_connection() as conn:
        p = _p(1)
        rows = conn.execute(f"SELECT * FROM ai_outputs ORDER BY created_at DESC LIMIT {p}", (limit,)).fetchall()
    return _decode_rows(rows, ["json_metadata"])


def insert_run(run_id: str, run_type: str, status: str) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute(
                "INSERT INTO runs(run_id, run_type, status, started_at) VALUES (%s, %s, %s, %s)",
                (run_id, run_type, status, now_iso())
            )
        else:
            conn.execute(
                "INSERT INTO runs(run_id, run_type, status, started_at) VALUES (?, ?, ?, ?)",
                (run_id, run_type, status, now_iso())
            )


def finish_run(run_id: str, status: str, metadata: dict = None) -> None:
    with get_connection() as conn:
        p = _p(1)
        if USE_POSTGRES:
            conn.execute(
                f"UPDATE runs SET status = {p}, finished_at = {p}, metadata_json = {p} WHERE run_id = {p}",
                (status, now_iso(), json_dumps(metadata or {}), run_id)
            )
        else:
            conn.execute(
                f"UPDATE runs SET status = {p}, finished_at = {p}, metadata_json = {p} WHERE run_id = {p}",
                (status, now_iso(), json_dumps(metadata or {}), run_id)
            )


def insert_discipline(name: str, rule_text: str) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute(
                "INSERT INTO disciplines(name, rule_text, created_at) VALUES (%s, %s, %s)",
                (name, rule_text, now_iso())
            )
        else:
            conn.execute(
                "INSERT INTO disciplines(name, rule_text, created_at) VALUES (?, ?, ?)",
                (name, rule_text, now_iso())
            )


def upsert_plan(payload: dict) -> None:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO plans(plan_key, name, weight, stage_goal, cadence, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(plan_key) DO UPDATE SET
                    name=EXCLUDED.name, weight=EXCLUDED.weight, stage_goal=EXCLUDED.stage_goal,
                    cadence=EXCLUDED.cadence, status=EXCLUDED.status, updated_at=EXCLUDED.updated_at
            """, (payload["plan_key"], payload["name"], payload["weight"], payload["stage_goal"],
                  payload["cadence"], payload.get("status", "active"), now, now))
        else:
            conn.execute("""
                INSERT INTO plans(plan_key, name, weight, stage_goal, cadence, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_key) DO UPDATE SET
                    name=excluded.name, weight=excluded.weight, stage_goal=excluded.stage_goal,
                    cadence=excluded.cadence, status=excluded.status, updated_at=excluded.updated_at
            """, (payload["plan_key"], payload["name"], payload["weight"], payload["stage_goal"],
                  payload["cadence"], payload.get("status", "active"), now, now))


def insert_review(payload: dict) -> None:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO reviews(review_type, review_period, summary, reflection, next_actions, score, metadata_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (payload["review_type"], payload["review_period"], payload.get("summary"),
                  payload.get("reflection"), payload.get("next_actions"), payload.get("score"),
                  json_dumps(payload.get("metadata", {})), now, now))
        else:
            conn.execute("""
                INSERT INTO reviews(review_type, review_period, summary, reflection, next_actions, score, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (payload["review_type"], payload["review_period"], payload.get("summary"),
                  payload.get("reflection"), payload.get("next_actions"), payload.get("score"),
                  json_dumps(payload.get("metadata", {})), now, now))


def ensure_entity(name: str, entity_type: str, description: str = None) -> int:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO entities(name, entity_type, description, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(name, entity_type) DO UPDATE SET
                    description=COALESCE(EXCLUDED.description, entities.description),
                    updated_at=EXCLUDED.updated_at
            """, (name, entity_type, description, now, now))
            row = conn.execute(
                "SELECT id FROM entities WHERE name = %s AND entity_type = %s",
                (name, entity_type)
            ).fetchone()
        else:
            conn.execute("""
                INSERT INTO entities(name, entity_type, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name, entity_type) DO UPDATE SET
                    description=COALESCE(excluded.description, entities.description),
                    updated_at=excluded.updated_at
            """, (name, entity_type, description, now, now))
            row = conn.execute(
                "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
                (name, entity_type)
            ).fetchone()
    return row["id"] if isinstance(row, dict) else row[0]


def insert_relation(payload: dict) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO relations(
                    subject_entity_id, relation_type, object_entity_id, evidence_document_id,
                    confidence, note, source_document_key, created_at, metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload["subject_entity_id"], payload["relation_type"], payload["object_entity_id"],
                payload.get("evidence_document_id"), payload.get("confidence", 0.5),
                payload.get("note"), payload.get("source_document_key"),
                now_iso(), json_dumps(payload.get("metadata", {}))
            ))
        else:
            conn.execute("""
                INSERT INTO relations(
                    subject_entity_id, relation_type, object_entity_id, evidence_document_id,
                    confidence, note, source_document_key, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["subject_entity_id"], payload["relation_type"], payload["object_entity_id"],
                payload.get("evidence_document_id"), payload.get("confidence", 0.5),
                payload.get("note"), payload.get("source_document_key"),
                now_iso(), json_dumps(payload.get("metadata", {}))
            ))


def insert_ai_output(payload: dict) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO ai_outputs(run_id, role, provider, model, prompt_text, response_text, json_metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload["run_id"], payload["role"], payload["provider"], payload["model"],
                payload["prompt_text"], payload["response_text"],
                json_dumps(payload.get("json_metadata", {})), now_iso()
            ))
        else:
            conn.execute("""
                INSERT INTO ai_outputs(run_id, role, provider, model, prompt_text, response_text, json_metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["run_id"], payload["role"], payload["provider"], payload["model"],
                payload["prompt_text"], payload["response_text"],
                json_dumps(payload.get("json_metadata", {})), now_iso()
            ))
    return payload


def insert_observation(payload: dict) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO observations(
                    metric_key, metric_name, value, unit, observed_at, frequency,
                    source, asset, metadata_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload["metric_key"], payload["metric_name"], payload.get("value"),
                payload.get("unit"), payload["observed_at"], payload["frequency"],
                payload["source"], payload.get("asset"),
                json_dumps(payload.get("metadata", {})), now_iso()
            ))
        else:
            conn.execute("""
                INSERT INTO observations(
                    metric_key, metric_name, value, unit, observed_at, frequency,
                    source, asset, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["metric_key"], payload["metric_name"], payload.get("value"),
                payload.get("unit"), payload["observed_at"], payload["frequency"],
                payload["source"], payload.get("asset"),
                json_dumps(payload.get("metadata", {})), now_iso()
            ))


def upsert_signal_definition(payload: dict) -> None:
    now = now_iso()
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO signal_definitions(
                    signal_key, name, dimension, frequency, comparator, threshold,
                    metric_key, action_mapping_json, description, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(signal_key) DO UPDATE SET
                    name=EXCLUDED.name, dimension=EXCLUDED.dimension, frequency=EXCLUDED.frequency,
                    comparator=EXCLUDED.comparator, threshold=EXCLUDED.threshold, metric_key=EXCLUDED.metric_key,
                    action_mapping_json=EXCLUDED.action_mapping_json, description=EXCLUDED.description, updated_at=EXCLUDED.updated_at
            """, (
                payload["signal_key"], payload["name"], payload["dimension"], payload["frequency"],
                payload["comparator"], payload["threshold"], payload["metric_key"],
                json_dumps(payload.get("action_mapping", {})), payload.get("description"), now, now
            ))
        else:
            conn.execute("""
                INSERT INTO signal_definitions(
                    signal_key, name, dimension, frequency, comparator, threshold,
                    metric_key, action_mapping_json, description, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(signal_key) DO UPDATE SET
                    name=excluded.name, dimension=excluded.dimension, frequency=excluded.frequency,
                    comparator=excluded.comparator, threshold=excluded.threshold, metric_key=excluded.metric_key,
                    action_mapping_json=excluded.action_mapping_json, description=excluded.description, updated_at=excluded.updated_at
            """, (
                payload["signal_key"], payload["name"], payload["dimension"], payload["frequency"],
                payload["comparator"], payload["threshold"], payload["metric_key"],
                json_dumps(payload.get("action_mapping", {})), payload.get("description"), now, now
            ))


def insert_signal_value(payload: dict) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO signal_values(
                    signal_key, observed_at, raw_value, threshold, status, direction,
                    score, reasoning, metadata_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(signal_key, observed_at) DO UPDATE SET
                    raw_value=EXCLUDED.raw_value, threshold=EXCLUDED.threshold, status=EXCLUDED.status,
                    direction=EXCLUDED.direction, score=EXCLUDED.score, reasoning=EXCLUDED.reasoning,
                    metadata_json=EXCLUDED.metadata_json
            """, (
                payload["signal_key"], payload["observed_at"], payload.get("raw_value"),
                payload.get("threshold"), payload["status"], payload["direction"],
                payload["score"], payload.get("reasoning"),
                json_dumps(payload.get("metadata", {})), now_iso()
            ))
        else:
            conn.execute("""
                INSERT OR REPLACE INTO signal_values(
                    signal_key, observed_at, raw_value, threshold, status, direction,
                    score, reasoning, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["signal_key"], payload["observed_at"], payload.get("raw_value"),
                payload.get("threshold"), payload["status"], payload["direction"],
                payload["score"], payload.get("reasoning"),
                json_dumps(payload.get("metadata", {})), now_iso()
            ))


def insert_signal_score(payload: dict) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO signal_scores(
                    score_date, positive_count, negative_count, neutral_count, total_score,
                    action_suggestion, dimension_breakdown_json, detail_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(score_date) DO UPDATE SET
                    positive_count=EXCLUDED.positive_count, negative_count=EXCLUDED.negative_count,
                    neutral_count=EXCLUDED.neutral_count, total_score=EXCLUDED.total_score,
                    action_suggestion=EXCLUDED.action_suggestion, dimension_breakdown_json=EXCLUDED.dimension_breakdown_json,
                    detail_json=EXCLUDED.detail_json
            """, (
                payload["score_date"], payload["positive_count"], payload["negative_count"],
                payload["neutral_count"], payload["total_score"], payload["action_suggestion"],
                json_dumps(payload.get("dimension_breakdown", {})),
                json_dumps(payload.get("details", [])), now_iso()
            ))
        else:
            conn.execute("""
                INSERT OR REPLACE INTO signal_scores(
                    score_date, positive_count, negative_count, neutral_count, total_score,
                    action_suggestion, dimension_breakdown_json, detail_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["score_date"], payload["positive_count"], payload["negative_count"],
                payload["neutral_count"], payload["total_score"], payload["action_suggestion"],
                json_dumps(payload.get("dimension_breakdown", {})),
                json_dumps(payload.get("details", [])), now_iso()
            ))


def insert_action(payload: dict) -> None:
    with get_connection() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO actions(action_time, asset, action_type, size, reason_signal_ids, risk_control, result_followup, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                payload["action_time"], payload["asset"], payload["action_type"],
                payload.get("size"), payload.get("reason_signal_ids"),
                payload.get("risk_control"), payload.get("result_followup"),
                json_dumps(payload.get("metadata", {}))
            ))
        else:
            conn.execute("""
                INSERT INTO actions(action_time, asset, action_type, size, reason_signal_ids, risk_control, result_followup, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["action_time"], payload["asset"], payload["action_type"],
                payload.get("size"), payload.get("reason_signal_ids"),
                payload.get("risk_control"), payload.get("result_followup"),
                json_dumps(payload.get("metadata", {}))
            ))


def delete_extracted_by_source_document_key(source_document_key: str) -> None:
    if not source_document_key:
        return
    with get_connection() as conn:
        p = _p(1)
        conn.execute(f"DELETE FROM claims WHERE source_document_key = {p}", (source_document_key,))
        conn.execute(f"DELETE FROM relations WHERE source_document_key = {p}", (source_document_key,))
        conn.execute(f"DELETE FROM tasks WHERE source_document_key = {p}", (source_document_key,))


def delete_extracted_by_source_document_hash(source_document_hash: str) -> None:
    delete_extracted_by_source_document_key(source_document_hash)


def claim_validation_summary() -> dict:
    with get_connection() as conn:
        counts = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN validation_status = 'validated' THEN 1 ELSE 0 END) AS validated_count,
                SUM(CASE WHEN validation_status = 'invalidated' THEN 1 ELSE 0 END) AS invalidated_count,
                SUM(CASE WHEN validation_status = 'pending' THEN 1 ELSE 0 END) AS pending_count
            FROM claims
        """).fetchone()
        themes = conn.execute("""
            SELECT subject, COUNT(*) AS claim_count
            FROM claims GROUP BY subject
            ORDER BY claim_count DESC, subject ASC LIMIT 8
        """).fetchall()
        recent = conn.execute("""
            SELECT id, subject, statement, validation_status, validation_note, review_cycle, updated_at
            FROM claims ORDER BY updated_at DESC LIMIT 12
        """).fetchall()
    return {"counts": counts, "themes": themes, "recent": recent}


def list_relations(relation_type: str = None) -> list:
    sql = """
        SELECT r.*, s.name AS subject_name, o.name AS object_name
        FROM relations r
        JOIN entities s ON s.id = r.subject_entity_id
        JOIN entities o ON o.id = r.object_entity_id
        WHERE 1=1
    """
    params = []
    if relation_type:
        p = _p(len(params) + 1)
        sql += f" AND r.relation_type = {p}"
        params.append(relation_type)
    sql += " ORDER BY r.created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(sql, tuple(params) if params else None).fetchall()
    return _decode_rows(rows, ["metadata_json"])
