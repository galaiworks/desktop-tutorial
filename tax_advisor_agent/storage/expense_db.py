"""
家計簿・経費データベース（SQLite）

LINE利用者ごとに支出を管理し、個人費・事業費の振り分けを記録する。
"""
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

from ..config import DATA_DIR

DB_PATH = DATA_DIR / "expenses.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    display_name TEXT,
    profile_json TEXT DEFAULT '{}',
    monthly_budget INTEGER DEFAULT 0,
    business_budget INTEGER DEFAULT 0,
    notifications_enabled INTEGER DEFAULT 1,
    notification_hour INTEGER DEFAULT 9,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    date            TEXT NOT NULL,             -- YYYY-MM-DD
    store_name      TEXT DEFAULT '',
    total_amount    INTEGER NOT NULL,          -- 円（税込）
    tax_amount      INTEGER DEFAULT 0,
    category        TEXT DEFAULT 'その他',     -- food / transport / utility / etc.
    expense_type    TEXT DEFAULT 'personal',   -- personal / business / mixed
    business_ratio  REAL DEFAULT 0.0,          -- 事業費割合 0.0〜1.0
    description     TEXT DEFAULT '',
    source          TEXT DEFAULT 'manual',     -- manual / receipt_scan / line
    receipt_json    TEXT DEFAULT '[]',         -- 明細 JSON
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);
CREATE INDEX IF NOT EXISTS idx_expenses_type ON expenses(user_id, expense_type);

CREATE TABLE IF NOT EXISTS monthly_budgets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    year_month      TEXT NOT NULL,             -- YYYY-MM
    personal_budget INTEGER DEFAULT 0,
    business_budget INTEGER DEFAULT 0,
    memo            TEXT DEFAULT '',
    UNIQUE(user_id, year_month)
);
"""

# 支出カテゴリ定義
CATEGORIES = {
    "food":        "食費",
    "dining":      "外食・接待",
    "transport":   "交通費",
    "utility":     "水道光熱費",
    "communication": "通信費",
    "medical":     "医療費",
    "education":   "教育・書籍",
    "entertainment": "娯楽・趣味",
    "clothing":    "衣類・日用品",
    "equipment":   "設備・機器",
    "software":    "ソフトウェア・サブスク",
    "advertising": "広告・宣伝",
    "office":      "事務用品",
    "rent":        "家賃・地代",
    "insurance":   "保険料",
    "tax":         "税金・公租公課",
    "other":       "その他",
}


class ExpenseDB:
    """SQLite 家計簿・経費データベース"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── ユーザー管理 ─────────────────────────────────────

    def upsert_user(
        self,
        user_id: str,
        display_name: str = "",
        profile_json: dict | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO users(user_id, display_name, profile_json)
                   VALUES(?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     display_name = excluded.display_name""",
                (user_id, display_name, json.dumps(profile_json or {}, ensure_ascii=False)),
            )

    def get_user(self, user_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["profile_json"] = json.loads(d.get("profile_json") or "{}")
        return d

    def update_user_settings(self, user_id: str, **kwargs) -> None:
        allowed = {
            "monthly_budget", "business_budget",
            "notifications_enabled", "notification_hour", "display_name",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        placeholders = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE users SET {placeholders} WHERE user_id = ?",
                (*updates.values(), user_id),
            )

    def get_all_users_with_notifications(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE notifications_enabled = 1"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── 支出管理 ─────────────────────────────────────────

    def add_expense(
        self,
        user_id: str,
        date: str,
        total_amount: int,
        category: str = "other",
        expense_type: str = "personal",
        business_ratio: float = 0.0,
        store_name: str = "",
        description: str = "",
        source: str = "manual",
        receipt_items: list[dict] | None = None,
        tax_amount: int = 0,
    ) -> int:
        """支出を登録して ID を返す"""
        receipt_json = json.dumps(receipt_items or [], ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO expenses
                   (user_id, date, store_name, total_amount, tax_amount,
                    category, expense_type, business_ratio,
                    description, source, receipt_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    user_id, date, store_name, total_amount, tax_amount,
                    category, expense_type, business_ratio,
                    description, source, receipt_json,
                ),
            )
            return cur.lastrowid

    def get_monthly_expenses(
        self,
        user_id: str,
        year_month: str,  # YYYY-MM
        expense_type: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT * FROM expenses
            WHERE user_id = ? AND date LIKE ?
        """
        params: list = [user_id, f"{year_month}%"]
        if expense_type:
            query += " AND expense_type = ?"
            params.append(expense_type)
        query += " ORDER BY date DESC, id DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["receipt_items"] = json.loads(d.pop("receipt_json", "[]"))
            result.append(d)
        return result

    def get_monthly_summary(self, user_id: str, year_month: str) -> dict:
        """月次集計サマリーを返す"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    expense_type,
                    category,
                    SUM(total_amount) as total,
                    COUNT(*) as cnt
                FROM expenses
                WHERE user_id = ? AND date LIKE ?
                GROUP BY expense_type, category
                """,
                (user_id, f"{year_month}%"),
            ).fetchall()

        summary: dict = {
            "year_month": year_month,
            "personal_total": 0,
            "business_total": 0,
            "mixed_total": 0,
            "grand_total": 0,
            "by_category": {},
            "by_type": {"personal": 0, "business": 0, "mixed": 0},
        }

        for r in rows:
            t = r["expense_type"]
            cat = r["category"]
            amt = r["total"]
            summary["by_type"][t] = summary["by_type"].get(t, 0) + amt
            summary["by_category"].setdefault(cat, {"personal": 0, "business": 0, "mixed": 0, "total": 0})
            summary["by_category"][cat][t] = summary["by_category"][cat].get(t, 0) + amt
            summary["by_category"][cat]["total"] += amt
            summary["grand_total"] += amt

        summary["personal_total"] = summary["by_type"].get("personal", 0)
        summary["business_total"] = summary["by_type"].get("business", 0)
        summary["mixed_total"] = summary["by_type"].get("mixed", 0)
        return summary

    def get_recent_expenses(self, user_id: str, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM expenses WHERE user_id = ?
                   ORDER BY date DESC, id DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["receipt_items"] = json.loads(d.pop("receipt_json", "[]"))
            result.append(d)
        return result

    def delete_expense(self, user_id: str, expense_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM expenses WHERE id = ? AND user_id = ?",
                (expense_id, user_id),
            )
        return cur.rowcount > 0

    # ── 予算管理 ─────────────────────────────────────────

    def set_monthly_budget(
        self,
        user_id: str,
        year_month: str,
        personal_budget: int = 0,
        business_budget: int = 0,
        memo: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO monthly_budgets
                       (user_id, year_month, personal_budget, business_budget, memo)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(user_id, year_month) DO UPDATE SET
                     personal_budget = excluded.personal_budget,
                     business_budget = excluded.business_budget,
                     memo = excluded.memo""",
                (user_id, year_month, personal_budget, business_budget, memo),
            )

    def get_budget_vs_actual(self, user_id: str, year_month: str) -> dict:
        """予算 vs 実績を返す"""
        summary = self.get_monthly_summary(user_id, year_month)
        with self._connect() as conn:
            budget_row = conn.execute(
                "SELECT * FROM monthly_budgets WHERE user_id = ? AND year_month = ?",
                (user_id, year_month),
            ).fetchone()
        budget = dict(budget_row) if budget_row else {}

        personal_budget = budget.get("personal_budget", 0)
        business_budget = budget.get("business_budget", 0)

        return {
            "year_month": year_month,
            "personal": {
                "budget": personal_budget,
                "actual": summary["personal_total"],
                "remaining": personal_budget - summary["personal_total"],
                "ratio": round(summary["personal_total"] / personal_budget * 100, 1) if personal_budget else None,
            },
            "business": {
                "budget": business_budget,
                "actual": summary["business_total"],
                "remaining": business_budget - summary["business_total"],
                "ratio": round(summary["business_total"] / business_budget * 100, 1) if business_budget else None,
            },
            "grand_total": summary["grand_total"],
            "by_category": summary["by_category"],
        }

    def get_category_name(self, key: str) -> str:
        return CATEGORIES.get(key, key)
