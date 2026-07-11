"""生成・投稿履歴の管理 (SQLite)"""
import json
import sqlite3
from datetime import datetime, timezone

from .config import DATA_DIR

DB_PATH = DATA_DIR / "pipeline.db"


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            title TEXT,
            script_json TEXT,
            video_path TEXT,
            youtube_id TEXT,
            article_slug TEXT,
            article_title TEXT,
            article_html TEXT,
            article_lead TEXT,
            status TEXT DEFAULT 'draft',   -- draft / ready / uploaded / failed / demo
            created_at TEXT,
            uploaded_at TEXT
        )
        """
    )
    # 後から追加したカラムのマイグレーション
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(videos)")}
    if "category" not in cols:
        conn.execute("ALTER TABLE videos ADD COLUMN category TEXT")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def create_entry(topic: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO videos (topic, created_at) VALUES (?, ?)", (topic, _now())
        )
        return cur.lastrowid


def save_script(video_id: int, title: str, script: dict) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE videos SET title=?, script_json=? WHERE id=?",
            (title, json.dumps(script, ensure_ascii=False), video_id),
        )


def save_video_path(video_id: int, path: str) -> None:
    with _conn() as c:
        c.execute("UPDATE videos SET video_path=?, status='ready' WHERE id=?", (path, video_id))


def save_article(
    video_id: int, slug: str, title: str, lead: str, html: str, category: str
) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE videos SET article_slug=?, article_title=?, article_lead=?, "
            "article_html=?, category=? WHERE id=?",
            (slug, title, lead, html, category, video_id),
        )


def mark_uploaded(video_id: int, youtube_id: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE videos SET youtube_id=?, status='uploaded', uploaded_at=? WHERE id=?",
            (youtube_id, _now(), video_id),
        )


def set_status(video_id: int, status: str) -> None:
    with _conn() as c:
        c.execute("UPDATE videos SET status=? WHERE id=?", (status, video_id))


def mark_failed(video_id: int) -> None:
    with _conn() as c:
        c.execute("UPDATE videos SET status='failed' WHERE id=?", (video_id,))


def get_video(video_id: int) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()


def next_ready_video() -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM videos WHERE status='ready' ORDER BY id LIMIT 1"
        ).fetchone()


def used_topics() -> set[str]:
    with _conn() as c:
        rows = c.execute("SELECT topic FROM videos").fetchall()
    return {r["topic"] for r in rows}


def list_videos() -> list[sqlite3.Row]:
    with _conn() as c:
        return c.execute("SELECT * FROM videos ORDER BY id DESC").fetchall()


def published_articles() -> list[sqlite3.Row]:
    """記事が生成済みの動画(サイト掲載対象)"""
    with _conn() as c:
        return c.execute(
            "SELECT * FROM videos WHERE article_slug IS NOT NULL ORDER BY id DESC"
        ).fetchall()
