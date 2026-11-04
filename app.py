#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, random, os, hashlib, urllib.parse, re, html, requests, secrets, base64
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
import bcrypt

IS_CLOUD = "DATABASE_URL" in st.secrets
if IS_CLOUD:
    import psycopg2, psycopg2.extras
else:
    import sqlite3

# ================= 兼容性封装 =================
def _submit(label, **kwargs):
    try:
        return st.form_submit_button(label, use_container_width=True, **kwargs)
    except TypeError:
        return st.form_submit_button(label, **kwargs)

# ================= 密码与安全区 =================
def hash_pwd_sha256(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def hash_pwd_bcrypt(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pwd_bcrypt(pwd: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False

# ================= 时间引擎 =================
TIMEZONES = {
    "北京时间 (UTC+8)": 8.0,
    "东京时间 (UTC+9)": 9.0,
    "悉尼时间 (UTC+10)": 10.0,
    "伦敦时间 (UTC+0)": 0.0,
    "巴黎时间 (UTC+1)": 1.0,
    "纽约时间 (UTC-5)": -5.0,
    "洛杉矶时间 (UTC-8)": -8.0,
    "自定义时区": None
}

def get_user_now(offset_hours: float) -> datetime:
    try:
        oh = float(offset_hours)
    except (TypeError, ValueError):
        oh = 8.0
    oh = max(-12.0, min(14.0, oh))
    tz = timezone(timedelta(hours=oh))
    return datetime.now(tz)

def get_user_today(offset_hours: float) -> date:
    return get_user_now(offset_hours).date()

DB_PATH = Path(__file__).resolve().parent / "study_points.db"
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

DEFAULT_ICON_BASE64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRkZEMzAwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDJMMTUuMDkgOC4yNkwyMiA5LjI3TDE3IDE0LjE0TDE4LjE4IDIxLjAyTDEyIDE3LjU3TDUuODIgMjEuMDJMOSAxNC4xNEwyIDkuMjdMOC45MSA4LjI2TDEyIDJ6Ij48L3BhdGg+PC9zdmc+"

DEFAULT_BONUS_RULES = {
    "weekday": {"single": {"points": 1.0, "full_points": 2.0}, "streak2": {"points": 1.5, "full_points": 3.0}, "streak4": {"points": 2.5, "full_points": 5.0}},
    "weekend": {"single": {"points": 1.0, "full_points": 2.0}},
    "longterm": {
        "week_basic": 3.5, "week_full": 7.0,
        "week_flex_perfect_deduct": 1.0,
        "week_flex_basic_deduct": 0.5,
        "month_basic": 8.0, "month_full": 20.0
    }
}
DEFAULT_EXAM_RULES = {"hit_points": 1.0, "rank_top_percent": 75.0, "rank_base_points": 1.0, "rank_step_percent": 5.0, "rank_step_points": 1.5}
TIER_CN = {"single": "单日达标", "streak2": "连续2日达标", "streak4": "连续4日达标", "weekend_single": "周末单日达标"}
GRADES = ["A+", "A", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E"]

# ================= 数据库封装（加入批量执行提速） =================
class SqliteCursor:
    def __init__(self, cur):
        self._cur = cur
    @property
    def description(self):
        return self._cur.description
    @property
    def rowcount(self):
        return self._cur.rowcount
    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None
    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]
    def __iter__(self):
        return (dict(r) for r in self._cur)

class DBWrapper:
    def __init__(self, conn, is_cloud):
        self.conn = conn
        self.is_cloud = is_cloud
    def execute(self, query, params=()):
        try:
            if self.is_cloud:
                if self.conn.closed != 0:
                    raise psycopg2.OperationalError("Connection closed")
                query = query.replace("?", "%s")
                cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                if params: cur.execute(query, params)
                else: cur.execute(query)
                if cur.description:
                    rows = cur.fetchall()
                    class FakeCursor:
                        def __init__(self, r): self.r = r
                        def fetchone(self): return self.r[0] if self.r else None
                        def fetchall(self): return self.r
                        @property
                        def rowcount(self): return len(self.r)
                    return FakeCursor(rows)
                return cur
            else:
                raw = self.conn.execute(query, params)
                return SqliteCursor(raw)
        except (psycopg2.OperationalError, sqlite3.OperationalError) as e:
            if self.is_cloud and "Connection closed" in str(e):
                st.cache_resource.clear()
            raise RuntimeError(f"数据库网络波动，请刷新页面重试。({str(e)})")
    
    def executemany(self, query, params_list):
        """新增：批量执行，极大地提升循环 UPDATE/INSERT 的速度"""
        try:
            if self.is_cloud:
                if self.conn.closed != 0:
                    raise psycopg2.OperationalError("Connection closed")
                query = query.replace("?", "%s")
                cur = self.conn.cursor()
                cur.executemany(query, params_list)
                return cur
            else:
                return self.conn.executemany(query, params_list)
        except (psycopg2.OperationalError, sqlite3.OperationalError) as e:
            raise RuntimeError(f"数据库批量操作失败。({str(e)})")

    def commit(self):
        self.conn.commit()

@st.cache_resource(show_spinner=False)
def get_db():
    if IS_CLOUD:
        try:
            conn = psycopg2.connect(st.secrets["DATABASE_URL"])
            conn.autocommit = True
            db = DBWrapper(conn, True)
            init_db(db)
            return db
        except Exception as e:
            st.cache_resource.clear()
            raise RuntimeError(f"数据库连接失败，请检查密码是否正确或稍后再试。({str(e)})")
    else:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        db = DBWrapper(conn, False)
        init_db(db)
        return db

def init_db(db):
    tables = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT DEFAULT 'user', security_question TEXT, security_answer TEXT, webhook_url TEXT, makeup_cards INTEGER DEFAULT 0, timezone_offset REAL DEFAULT 8.0, host_id TEXT)",
        "CREATE TABLE IF NOT EXISTS daily_records (day TEXT, owner_id TEXT, done_tasks TEXT, base_score REAL, bonus_score REAL, bonus_detail TEXT, total_score REAL, updated_at TEXT, basic_thr REAL, full_thr REAL)",
        "CREATE TABLE IF NOT EXISTS period_bonus (period_key TEXT, owner_id TEXT, kind TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS redemptions (id SERIAL PRIMARY KEY, owner_id TEXT, item TEXT, cost REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS exam_rewards (id SERIAL PRIMARY KEY, owner_id TEXT, detail TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS special_events (id SERIAL PRIMARY KEY, day TEXT, owner_id TEXT, points REAL, note TEXT, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS extra_points (id SERIAL PRIMARY KEY, owner_id TEXT, name TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS config_tasks (id TEXT, weekday INTEGER, owner_id TEXT, category TEXT, name TEXT, points REAL)",
        "CREATE TABLE IF NOT EXISTS config_shop (id SERIAL PRIMARY KEY, owner_id TEXT, name TEXT, cost REAL)",
        "CREATE TABLE IF NOT EXISTS config_exam (subject TEXT, owner_id TEXT, config_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_exam_rules (owner_id TEXT PRIMARY KEY, config_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_thresholds (weekday INTEGER, owner_id TEXT, basic REAL, \"full\" REAL)",
        "CREATE TABLE IF NOT EXISTS config_bonus_rules (owner_id TEXT PRIMARY KEY, rules_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_exam_multihit (hit_count INTEGER, owner_id TEXT, points REAL)",
        "CREATE TABLE IF NOT EXISTS config_badges (id SERIAL PRIMARY KEY, owner_id TEXT DEFAULT 'system', name TEXT, cond_type TEXT, cond_val REAL, icon_url TEXT)"
    ]
    for t in tables:
        try: db.execute(t)
        except: pass
        
    # 建立数据库索引，极大地加快查询速度
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_daily_records ON daily_records (owner_id, day)",
        "CREATE INDEX IF NOT EXISTS idx_period_bonus ON period_bonus (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_extra_points ON extra_points (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_exam_rewards ON exam_rewards (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_redemptions ON redemptions (owner_id)"
    ]
    for idx in indexes:
        try: db.execute(idx)
        except: pass
    db.commit()

    if db.is_cloud:
        for q in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS security_question TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS security_answer TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_url TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS makeup_cards INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone_offset REAL DEFAULT 8.0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS host_id TEXT",
            "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS basic_thr REAL",
            "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS full_thr REAL",
            "ALTER TABLE period_bonus ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE exam_rewards ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE special_events ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE extra_points ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_tasks ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_shop ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_exam ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_exam_rules ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_thresholds ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_bonus_rules ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_exam_multihit ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
        ]:
            try: db.execute(q)
            except: pass
        db.commit()
    else:
        for q in [
            "ALTER TABLE users ADD COLUMN security_question TEXT",
            "ALTER TABLE users ADD COLUMN security_answer TEXT",
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
            "ALTER TABLE users ADD COLUMN webhook_url TEXT",
            "ALTER TABLE users ADD COLUMN makeup_cards INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN timezone_offset REAL DEFAULT 8.0",
            "ALTER TABLE users ADD COLUMN host_id TEXT",
            "ALTER TABLE daily_records ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE daily_records ADD COLUMN basic_thr REAL",
            "ALTER TABLE daily_records ADD COLUMN full_thr REAL",
            "ALTER TABLE period_bonus ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE redemptions ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE exam_rewards ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE special_events ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE extra_points ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_tasks ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_shop ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_exam ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_exam_rules ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_thresholds ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_bonus_rules ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_exam_multihit ADD COLUMN owner_id TEXT DEFAULT '晴'",
        ]:
            try: db.execute(q)
            except: pass
        db.commit()

    try:
        user_count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        if user_count == 0:
            admin_user = os.getenv("INIT_ADMIN_USER", "admin")
            admin_pwd = os.getenv("INIT_ADMIN_PWD")
            if not admin_pwd:
                admin_pwd = secrets.token_urlsafe(8)
                print("=========================================")
                print("⚠️ 系统检测到无用户，已生成初始管理员！")
                print(f"👤 用户名: {admin_user}")
                print(f"🔑 密码: {admin_pwd}")
                print("请立即登录并修改密码！")
                print("=========================================")

            db.execute(
                "INSERT INTO users (username, password_hash, role, security_question, security_answer) VALUES (?, ?, 'admin', '管理员默认密保', ?)",
                (admin_user, hash_pwd_bcrypt(admin_pwd), hash_pwd_sha256("123456"))
            )
            if not db.execute("SELECT * FROM config_tasks WHERE owner_id=?", (admin_user,)).fetchone():
                init_old_admin_data(db, admin_user)
            db.commit()
    except Exception as e:
        print(f"初始化管理员失败: {e}")

    try:
        global_badge_count = db.execute("SELECT COUNT(*) as c FROM config_badges WHERE owner_id='system'").fetchone()["c"]
        if global_badge_count == 0:
            db.execute("DELETE FROM config_badges")
            default_badges = [
                ("破壳而出", "days", 1), ("持之以恒", "days", 7), ("习惯成自然", "days", 30),
                ("积分大亨", "points", 100), ("完美主义", "perfect", 1), ("考神附体", "exam_hits", 4)
            ]
            for b in default_badges:
                prompt = f"Minimalist flat vector icon for '{b[0]}', clean simple design, ui app icon, no text, white background, not exaggerated"
                icon_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=256&height=256&nologo=true&seed=42"
                db.execute(
                    "INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)",
                    (b[0], b[1], b[2], icon_url)
                )
        db.commit()
    except Exception: pass

def init_old_admin_data(db, owner_id):
    DEFAULT_TASKS = [("hw_sort", 0, "校内", "作业分类", 1.0), ("hw_done", 0, "校内", "作业完成", 2.0)]
    DEFAULT_SHOP = [("专属夸夸", 6)]
    DEFAULT_EXAM_CONFIG = {"语文": {"type": "score", "max_score": 150, "target": 105.0, "step": 3.0, "step_points": 2.0}}
    DEFAULT_THRESHOLDS = {0: {"basic": 8.0, "full": 11.0}}
    for t in DEFAULT_TASKS:
        db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (t[0], t[1], owner_id, t[2], t[3], t[4]))
    for s in DEFAULT_SHOP:
        db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (owner_id, s[0], s[1]))
    for sub, cfg in DEFAULT_EXAM_CONFIG.items():
        db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (sub, owner_id, json.dumps(cfg)))
    for wd, data in DEFAULT_THRESHOLDS.items():
        db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)', (wd, owner_id, data["basic"], data["full"]))
    db.execute("INSERT INTO config_exam_rules (owner_id, config_json) VALUES (?,?)", (owner_id, json.dumps(DEFAULT_EXAM_RULES)))
    db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (owner_id, json.dumps(DEFAULT_BONUS_RULES)))
    db.commit()

@st.cache_data(ttl=60, show_spinner=False)
def get_all_users(db):
    return [{"username": r["username"], "role": r["role"]} for r in db.execute("SELECT username, role FROM users").fetchall()]

# ================= 三级权限 =================
@st.cache_data(ttl=60, show_spinner=False)
def get_visible_users(db, current_user, current_role):
    if current_role == "admin":
        return [u["username"] for u in get_all_users(db)]
    if current_role == "host":
        rows = db.execute(
            "SELECT username FROM users WHERE username=? OR host_id=?",
            (current_user, current_user)
        ).fetchall()
        return [r["username"] for r in rows]
    return [current_user]

def _remaining_admins(db, exclude_username):
    try:
        return db.execute(
            "SELECT COUNT(*) as c FROM users WHERE role='admin' AND username != ?",
            (exclude_username,)
        ).fetchone()["c"]
    except Exception:
        return 0

@st.cache_data(ttl=3600, show_spinner=False)
def get_thresholds(oid):
    db = get_db()
    rows = db.execute("SELECT * FROM config_thresholds WHERE owner_id=?", (oid,)).fetchall()
    return {r["weekday"]: {"basic": float(r["basic"] or 0), "full": float(r["full"] or 0)} for r in rows}

@st.cache_data(ttl=3600, show_spinner=False)
def get_bonus_rules(oid):
    db = get_db()
    row = db.execute("SELECT rules_json FROM config_bonus_rules WHERE owner_id=?", (oid,)).fetchone()
    if not row: return DEFAULT_BONUS_RULES
    rules = json.loads(row["rules_json"])
    if "week_flex_perfect_deduct" not in rules["longterm"]: rules["longterm"]["week_flex_perfect_deduct"] = 1.0
    if "week_flex_basic_deduct" not in rules["longterm"]: rules["longterm"]["week_flex_basic_deduct"] = 0.5
    return rules

@st.cache_data(ttl=3600, show_spinner=False)
def get_tasks(weekday, oid):
    db = get_db()
    rows = db.execute("SELECT * FROM config_tasks WHERE weekday=? AND owner_id=?", (weekday, oid)).fetchall()
    return [{"id": r["id"], "category": r["category"], "name": r["name"], "points": float(r["points"] or 0)} for r in rows]

@st.cache_data(ttl=3600, show_spinner=False)
def get_shop(oid):
    db = get_db()
    items = [(r["name"], float(r["cost"] or 0)) for r in db.execute("SELECT * FROM config_shop WHERE owner_id=?", (oid,)).fetchall()]
    if not any(i[0] == "补签卡" for i in items):
        items.insert(0, ("补签卡", 25.0))
    return items

@st.cache_data(ttl=3600, show_spinner=False)
def get_exam_config(oid):
    db = get_db()
    subjects = {r["subject"]: json.loads(r["config_json"]) for r in db.execute("SELECT * FROM config_exam WHERE owner_id=?", (oid,)).fetchall()}
    rule_row = db.execute("SELECT config_json FROM config_exam_rules WHERE owner_id=?", (oid,)).fetchone()
    return subjects, json.loads(rule_row["config_json"]) if rule_row else DEFAULT_EXAM_RULES

@st.cache_data(ttl=3600, show_spinner=False)
def get_exam_multihit(oid):
    db = get_db()
    return [{"hit_count": r["hit_count"], "points": float(r["points"] or 0)}
            for r in db.execute("SELECT * FROM config_exam_multihit WHERE owner_id=? ORDER BY hit_count ASC", (oid,)).fetchall()]

@st.cache_data(ttl=3600, show_spinner=False)
def get_badge_configs():
    db = get_db()
    return [dict(r) for r in db.execute("SELECT * FROM config_badges WHERE owner_id='system' ORDER BY id ASC").fetchall()]

@st.cache_data(ttl=10, show_spinner=False)
def get_balance(oid) -> dict:
    db = get_db()
    query = """
        SELECT 'daily' as k, COALESCE(SUM(total_score), 0) as s FROM daily_records WHERE owner_id = ?
        UNION ALL
        SELECT 'period', COALESCE(SUM(points), 0) FROM period_bonus WHERE owner_id = ?
        UNION ALL
        SELECT 'exam', COALESCE(SUM(points), 0) FROM exam_rewards WHERE owner_id = ?
        UNION ALL
        SELECT 'special', COALESCE(SUM(points), 0) FROM special_events WHERE owner_id = ?
        UNION ALL
        SELECT 'spent', COALESCE(SUM(cost), 0) FROM redemptions WHERE owner_id = ?
        UNION ALL
        SELECT 'extra', COALESCE(SUM(points), 0) FROM extra_points WHERE owner_id = ?
    """
    try:
        rows = db.execute(query, (oid, oid, oid, oid, oid, oid)).fetchall()
        data = {r["k"]: float(r["s"] or 0) for r in rows}
    except Exception:
        data = {"daily": 0.0, "period": 0.0, "exam": 0.0, "special": 0.0, "spent": 0.0, "extra": 0.0}

    daily = round(data["daily"], 2)
    period = round(data["period"], 2)
    exam = round(data["exam"], 2)
    special = round(data["special"], 2)
    spent = round(data["spent"], 2)
    extra = round(data["extra"], 2)
    
    return {
        "daily": daily, "period": period, "exam": exam,
        "special": special, "spent": spent, "extra": extra,
        "balance": round(daily + period + exam + special + extra - spent, 2)
    }

@st.cache_data(ttl=10, show_spinner=False)
def get_makeup_cards_of(username):
    try:
        db = get_db()
        row = db.execute("SELECT makeup_cards FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return 0
        return int(dict(row).get("makeup_cards") or 0)
    except Exception:
        return 0

@st.cache_data(ttl=10, show_spinner=False)
def get_user_badges(oid):
    db = get_db()
    try: configs = get_badge_configs()
    except Exception: return []
    earned = []
    try:
        days_count = db.execute("SELECT COUNT(*) as c FROM daily_records WHERE owner_id=?", (oid,)).fetchone()["c"]
        bal = get_balance(oid); total_earned = bal['balance'] + bal['spent']
        perfect_count = db.execute("SELECT COUNT(*) as c FROM period_bonus WHERE owner_id=? AND kind LIKE ?", (oid, '%完美%')).fetchone()["c"]
        max_exam_hits = 0
        for er in db.execute("SELECT detail FROM exam_rewards WHERE owner_id=?", (oid,)).fetchall():
            if er["detail"]:
                match = re.search(r'达成 (\d+) 门', er["detail"])
                if match:
                    hits = int(match.group(1))
                    if hits > max_exam_hits: max_exam_hits = hits
    except Exception: return []
    for cfg in configs:
        try:
            cond_type = cfg["cond_type"]; cond_val = float(cfg["cond_val"] or 0)
            if ((cond_type == 'days' and days_count >= cond_val) or
                (cond_type == 'points' and total_earned >= cond_val) or
                (cond_type == 'perfect' and perfect_count >= cond_val) or
                (cond_type == 'exam_hits' and max_exam_hits >= cond_val)):
                earned.append({"name": html.escape(cfg["name"]), "icon": html.escape(cfg["icon_url"] or "", quote=True)})
        except Exception: continue
    return earned

def compute_bonus_for_day(day: date, lookup: dict, bonus_rules: dict):
    key = day.isoformat(); rec = lookup.get(key)
    if rec is None: return 0.0, {}
    try: base = float(rec.get("base_score") or 0)
    except: base = 0.0
    wd = day.weekday(); basic_thr = float(rec.get("basic_thr") or 0); full_thr = float(rec.get("full_thr") or 0)
    if wd <= 4:
        if base < basic_thr: return 0.0, {"tier": "none"}
        streak_days = []; cur = day
        if wd == 3:
            streak = 1; all_full = base >= full_thr
        else:
            while cur.weekday() <= 4:
                if cur.weekday() == 3: cur -= timedelta(days=1); continue
                r = lookup.get(cur.isoformat())
                if r is None: break
                cur_basic = float(r.get("basic_thr") or 0)
                if float(r.get("base_score") or 0) >= cur_basic: streak_days.append(cur); cur -= timedelta(days=1)
                else: break
            streak = len(streak_days)
            all_full = all(float(lookup[x.isoformat()].get("base_score") or 0) >= float(lookup[x.isoformat()].get("full_thr") or 999) for x in streak_days)
        rule = bonus_rules.get("weekday", DEFAULT_BONUS_RULES["weekday"])
        if streak >= 4: tier = "streak4"; bonus = rule[tier]["full_points"] if all_full else rule[tier]["points"]
        elif streak >= 2: tier = "streak2"; bonus = rule[tier]["full_points"] if all_full else rule[tier]["points"]
        else: tier = "single"; bonus = rule[tier]["full_points"] if base >= full_thr else rule[tier]["points"]
        return float(bonus), {"tier": tier, "streak": streak}
    if base < basic_thr: return 0.0, {"tier": "none"}
    rule = bonus_rules.get("weekend", DEFAULT_BONUS_RULES["weekend"])["single"]
    bonus = rule["full_points"] if base >= full_thr else rule["points"]
    return float(bonus), {"tier": "weekend_single"}

def recalc_all_bonus(db, oid):
    """【性能重构】：不再全表重算，只针对最近 30 天批量重算。"""
    try:
        bonus_rules = get_bonus_rules(oid)
        start_d = (get_user_today(8.0) - timedelta(days=30)).isoformat()
        rows = db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=? AND day >= ?", (oid, start_d)).fetchall()
        if not rows: return
        
        lookup = {r["day"]: {"base_score": float(r["base_score"] or 0), "basic_thr": float(r.get("basic_thr") or 0), "full_thr": float(r.get("full_thr") or 0)} for r in rows}
        updates = []
        for day_str in sorted(lookup):
            try: d = date.fromisoformat(day_str)
            except ValueError: continue
            bonus, detail = compute_bonus_for_day(d, lookup, bonus_rules)
            updates.append((bonus, json.dumps(detail), float(lookup[day_str]["base_score"]) + bonus, day_str, oid))
        
        # 批量提交，速度起飞
        if updates:
            db.executemany("UPDATE daily_records SET bonus_score=?, bonus_detail=?, total_score=? WHERE day=? AND owner_id=?", updates)
            db.commit()
    except Exception: pass

def settle_longterm_bonus(db, oid, ts):
    """【性能重构】：不再全表重算，只针对最近 60 天的周/月批量结算。"""
    try:
        bonus_rules = get_bonus_rules(oid); lt_rules = bonus_rules["longterm"]
        start_d = (get_user_today(8.0) - timedelta(days=60)).isoformat()
        rows = db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=? AND day >= ?", (oid, start_d)).fetchall()
        if not rows: return

        scores = {}
        for r in rows:
            try: date.fromisoformat(r["day"])
            except ValueError: continue
            scores[r["day"]] = r

        # 清理旧奖励
        db.execute("DELETE FROM period_bonus WHERE owner_id=?", (oid,))
        
        weeks = {}
        for ds in scores:
            d = date.fromisoformat(ds); y, w, _ = d.isocalendar()
            weeks.setdefault(f"{y}-W{w:02d}", []).append(d)
        week_status = {}
        inserts = []
        
        for wk, dlist in weeks.items():
            monday = min(dlist) - timedelta(days=min(dlist).weekday())
            full_week = [monday + timedelta(days=i) for i in range(7)]
            if not all(x.isoformat() in scores for x in full_week):
                week_status[wk] = {'is_perfect': False, 'is_basic': False}; continue
            miss_basic = 0; miss_full = 0
            for x in full_week:
                day_data = scores[x.isoformat()]
                if float(day_data.get("base_score") or 0) < float(day_data.get("basic_thr") or 999): miss_basic += 1
                elif float(day_data.get("base_score") or 0) < float(day_data.get("full_thr") or 999): miss_full += 1
            target_kind, target_pts = None, 0.0; is_perfect = False; is_basic = False
            if miss_basic == 0:
                is_basic = True
                if miss_full == 0:
                    is_perfect = True; target_kind = "完美一周(全满分)"; target_pts = lt_rules["week_full"]
                elif miss_full == 1:
                    is_perfect = True; target_kind = "完美一周(弹性1天)"; target_pts = max(0, lt_rules["week_full"] - lt_rules.get("week_flex_perfect_deduct", 1.0))
                else:
                    target_kind = "整周达标"; target_pts = lt_rules["week_basic"]
            elif miss_basic == 1:
                is_basic = True; target_kind = "整周达标(弹性1天)"; target_pts = max(0, lt_rules["week_basic"] - lt_rules.get("week_flex_basic_deduct", 0.5))
            week_status[wk] = {'is_perfect': is_perfect, 'is_basic': is_basic}
            if target_kind:
                inserts.append((f"W:{wk}", oid, target_kind, target_pts, ts))

        months = {}
        for ds in scores:
            d = date.fromisoformat(ds); y, m = d.year, d.month
            months.setdefault(f"{y}-{m:02d}", []).append(d)
            
        for mk, dlist in months.items():
            y, m = int(mk.split("-")[0]), int(mk.split("-")[1])
            first = date(y, m, 1)
            nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
            alldays = []
            cur = first
            while cur < nxt: alldays.append(cur); cur += timedelta(days=1)
            if not all(x.isoformat() in scores for x in alldays): continue
            month_is_perfect = True; month_is_basic = True
            for day_obj in alldays:
                ds = day_obj.isoformat(); day_data = scores[ds]
                dy, dw, _ = day_obj.isocalendar(); wk_key = f"{dy}-W{dw:02d}"
                w_stat = week_status.get(wk_key, {'is_perfect': False, 'is_basic': False})
                day_full = float(day_data.get("base_score") or 0) >= float(day_data.get("full_thr") or 999)
                day_basic = float(day_data.get("base_score") or 0) >= float(day_data.get("basic_thr") or 999)
                if not day_full and not w_stat['is_perfect']: month_is_perfect = False
                if not day_basic and not w_stat['is_basic']: month_is_basic = False
            target_kind, target_pts = None, 0.0
            if month_is_perfect: target_kind = "完美一月"; target_pts = lt_rules["month_full"]
            elif month_is_basic: target_kind = "整月达标"; target_pts = lt_rules["month_basic"]
            if target_kind:
                inserts.append((f"M:{mk}", oid, target_kind, target_pts, ts))
                
        if inserts:
            db.executemany("INSERT INTO period_bonus (period_key, owner_id, kind, points, ts) VALUES (?,?,?,?,?)", inserts)
        db.commit()
    except Exception: pass

def save_day(db, day: date, done_ids: list, oid: str, ts: str):
    tasks = get_tasks(day.weekday(), oid)
    base = sum(t["points"] for t in tasks if t["id"] in set(done_ids))
    thresholds = get_thresholds(oid); thr = thresholds.get(day.weekday(), {"basic": 0, "full": 0})
    db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (day.isoformat(), oid))
    db.execute(
        "INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) VALUES (?, ?, ?, ?, 0, '{}', ?, ?, ?, ?)",
        (day.isoformat(), oid, json.dumps(sorted(done_ids)), base, base, ts, thr["basic"], thr["full"])
    )
    db.commit()
    recalc_all_bonus(db, oid)
    settle_longterm_bonus(db, oid, ts)
    st.cache_data.clear()

def calc_exam_bonus(scores: dict, ranks: dict, oid: str):
    try:
        exam_config, exam_rules = get_exam_config(oid); multihit_rules = get_exam_multihit(oid)
    except Exception:
        return 0.0, ["数据配置异常，无法结算"], 0
    total = 0.0; lines = []; hit_count = 0
    for subject, cfg in exam_config.items():
        actual = scores.get(subject)
        if actual is None: continue
        if cfg.get("type") == "score":
            hit = actual >= cfg.get("target", 0)
            if hit:
                total += exam_rules.get("hit_points", 1); hit_count += 1
                lines.append(f"达成 {subject} -> +{exam_rules.get('hit_points', 1)}")
            step = cfg.get("step", 0)
            tiers = int((actual - cfg.get("target", 0)) // step) if step > 0 and actual > cfg.get("target", 0) else 0
            if tiers > 0:
                gain = tiers * cfg.get("step_points", 0); total += gain
                lines.append(f"  {subject} 超目标 {tiers} 档 -> +{gain}")
        else:
            if cfg.get("target") not in GRADES or actual not in GRADES: continue
            gap = GRADES.index(cfg["target"]) - GRADES.index(actual); hit = gap >= 0
            if hit:
                total += exam_rules.get("hit_points", 1); hit_count += 1
                lines.append(f"达成 {subject} -> +{exam_rules.get('hit_points', 1)}")
            if gap > 0:
                gain = gap * cfg.get("step_points", 0); total += gain
                lines.append(f"  {subject} 升 {gap} 档 -> +{gain}")
    for mh in sorted(multihit_rules, key=lambda x: x["hit_count"], reverse=True):
        if hit_count >= mh["hit_count"]:
            total += mh["points"]; lines.append(f"达成 {mh['hit_count']} 门及以上 -> +{mh['points']}"); break
    for subject in ["语文", "数学", "英语"]:
        pct = ranks.get(subject)
        if pct is not None and 0 <= pct < 100 and pct <= exam_rules.get("rank_top_percent", 75):
            total += exam_rules.get("rank_base_points", 1)
            lines.append(f"{subject} 前{pct:.0f}% -> +{exam_rules.get('rank_base_points', 1)}")
            pct_step = exam_rules.get("rank_step_percent", 5)
            extra = int((exam_rules.get("rank_top_percent", 75) - pct) // pct_step) if pct_step > 0 else 0
            if extra > 0:
                gain = extra * exam_rules.get("rank_step_points", 1.5); total += gain
                lines.append(f"  再进{extra}档 -> +{gain}")
    return round(total, 2), lines, hit_count

def render_timer():
    timer_html = """
    <style>
        body { margin: 0; padding: 0; overflow: hidden; }
        .timer-container { font-family: sans-serif; text-align: center; padding: 10px 5px; background: #f8f9fa; border-radius: 10px; }
        .timer-display { font-size: 36px; font-weight: bold; margin: 5px 0 15px 0; color: #2c3e50; }
        .row { display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 15px; font-size: 14px; }
        .row select, .row input { padding: 5px; border-radius: 5px; border: 1px solid #ccc; }
        .row input { width: 50px; text-align: center; }
        .btn-group { display: flex; justify-content: center; gap: 8px; }
        button { flex: 1; padding: 8px 0; font-size: 14px; cursor: pointer; border: none; border-radius: 5px; background: #007bff; color: white; transition: 0.2s; }
        button:hover { background: #0056b3; }
        .btn-stop { background: #dc3545; } .btn-stop:hover { background: #c82333; }
        .btn-reset { background: #6c757d; } .btn-reset:hover { background: #5a6268; }
    </style>
    <div class="timer-container">
        <div class="timer-display" id="display">00:00</div>
        <div class="row">
            <select id="mode">
                <option value="stopwatch">正计时</option>
                <option value="countdown">倒计时</option>
            </select>
            <span><input type="number" id="minutes" value="25" min="1"> 分</span>
        </div>
        <div class="btn-group">
            <button onclick="startTimer()">开始</button>
            <button class="btn-stop" onclick="stopTimer()">暂停</button>
            <button class="btn-reset" onclick="resetTimer()">重置</button>
        </div>
    </div>
    <script>
        let timerId = null; let isRunning = false; let totalSeconds = 0; let currentSeconds = 0;
        function updateDisplay() {
            let m = Math.floor(currentSeconds / 60).toString().padStart(2, '0');
            let s = (currentSeconds % 60).toString().padStart(2, '0');
            document.getElementById('display').innerText = m + ":" + s;
        }
        function startTimer() {
            if(isRunning) return;
            let mode = document.getElementById('mode').value;
            if(!isRunning && currentSeconds === 0) {
                if(mode === 'countdown') { let mins = document.getElementById('minutes').value; totalSeconds = mins * 60; currentSeconds = totalSeconds; }
                else { totalSeconds = 0; currentSeconds = 0; }
            }
            isRunning = true;
            timerId = setInterval(() => {
                if(document.getElementById('mode').value === 'stopwatch') { currentSeconds++; }
                else { if(currentSeconds > 0) currentSeconds--; else { clearInterval(timerId); isRunning = false; alert("时间到！"); return; } }
                updateDisplay();
            }, 1000);
        }
        function stopTimer() { clearInterval(timerId); isRunning = false; }
        function resetTimer() { clearInterval(timerId); isRunning = false; currentSeconds = 0; updateDisplay(); }
        updateDisplay();
    </script>
    """
    encoded = base64.b64encode(timer_html.encode('utf-8')).decode('ascii')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded}"
    try:
        st.iframe(data_uri, height=220)
    except AttributeError:
        import streamlit.components.v1 as components
        components.html(timer_html, height=220)

def login_page(db):
    st.title("学习打卡系统")
    if "login_page_uid" not in st.session_state:
        st.session_state.login_page_uid = secrets.token_hex(4)
    uid = st.session_state.login_page_uid

    tab1, tab2, tab3 = st.tabs(["登录", "注册", "找回密码"])

    with tab1:
        with st.form(f"login_form_{uid}"):
            u = st.text_input("用户名", max_chars=20)
            p = st.text_input("密码", type="password", max_chars=72)
            if _submit("登录", type="primary"):
                try:
                    user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
                    if user:
                        stored_hash = user["password_hash"]
                        is_valid = False
                        if len(stored_hash) == 64:
                            if stored_hash == hash_pwd_sha256(p):
                                is_valid = True
                                new_hash = hash_pwd_bcrypt(p)
                                db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, u))
                                db.commit()
                        else:
                            if check_pwd_bcrypt(p, stored_hash):
                                is_valid = True
                        if is_valid:
                            st.session_state.user = u
                            st.session_state.role = user["role"]
                            if p == "123456":
                                st.session_state.force_pwd_change = True
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
                    else:
                        st.error("用户名或密码错误")
                except RuntimeError as e:
                    st.error(str(e))

    with tab2:
        with st.form(f"reg_form_{uid}"):
            u = st.text_input("设置用户名", max_chars=20)
            p = st.text_input("设置密码", type="password", max_chars=72)
            p2 = st.text_input("确认密码", type="password", max_chars=72)
            sq = st.text_input("密保问题 (如：我的幸运数字？)", max_chars=50)
            sa = st.text_input("密保答案", max_chars=50)
            if _submit("注册", type="primary"):
                if not u or not p or not sq or not sa:
                    st.error("请填写所有字段（含密保）")
                elif p != p2:
                    st.error("密码不一致")
                elif u.lower() in ["system", "admin"]:
                    st.error("该用户名为系统保留，请换一个")
                else:
                    try:
                        if db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone():
                            st.error("用户名已存在")
                        else:
                            db.execute(
                                "INSERT INTO users (username, password_hash, role, security_question, security_answer) VALUES (?, ?, 'user', ?, ?)",
                                (u, hash_pwd_bcrypt(p), sq, hash_pwd_sha256(sa.strip().lower()))
                            )
                            db.commit(); st.success("注册成功！请去登录。")
                    except RuntimeError as e:
                        st.error(str(e))

    with tab3:
        st.write("输入用户名，验证密保问题后重设密码。")
        u_reset = st.text_input("请输入你的用户名", key=f"reset_u_{uid}", max_chars=20)
        if u_reset:
            try:
                user = db.execute("SELECT * FROM users WHERE username=?", (u_reset,)).fetchone()
                if user:
                    sq = user.get("security_question")
                    if not sq:
                        st.warning("该账户未设置密保问题，请联系管理员重置密码。")
                    else:
                        with st.form(f"reset_form_{uid}"):
                            st.info(f"密保问题：{html.escape(sq)}")
                            ans = st.text_input("密保答案", max_chars=50)
                            new_p = st.text_input("新密码", type="password", max_chars=72)
                            if _submit("确认重置密码", type="primary"):
                                if not ans or not new_p:
                                    st.error("请填写完整")
                                elif hash_pwd_sha256(ans.strip().lower()) == user["security_answer"]:
                                    db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt(new_p), u_reset))
                                    db.commit(); st.success("密码重置成功！请去登录。")
                                else:
                                    st.error("密保答案错误！")
                else:
                    st.error("该用户名不存在")
            except RuntimeError as e:
                st.error(str(e))


def main():
    st.set_page_config(page_title="学习打卡系统", layout="centered", initial_sidebar_state="collapsed")
    try:
        db = get_db()
    except RuntimeError as e:
        st.error(str(e)); st.stop()

    if "user" not in st.session_state:
        login_page(db); return

    current_user = st.session_state.user
    try:
        user_row = db.execute("SELECT * FROM users WHERE username=?", (current_user,)).fetchone()
        if not user_row:
            del st.session_state.user
            st.rerun()
    except RuntimeError as e:
        st.error(str(e)); st.stop()

    try:
        _ = dict(user_row).get("host_id")
    except Exception:
        _ = None

    if st.session_state.get("force_pwd_change"):
        st.title("⚠️ 安全提示：请修改默认密码")
        st.warning("检测到您正在使用系统默认密码 (123456)，为了您的数据安全，请立即修改后才能继续使用。")

        with st.form("force_pwd_form"):
            new_p = st.text_input("新密码", type="password", max_chars=72)
            confirm_p = st.text_input("确认新密码", type="password", max_chars=72)
            submit = _submit("提交修改", type="primary")

            if submit:
                if not new_p or not confirm_p:
                    st.error("请填写完整")
                elif new_p != confirm_p:
                    st.error("两次输入的新密码不一致")
                elif len(new_p) < 6:
                    st.error("新密码长度不能少于 6 位")
                elif new_p == "123456":
                    st.error("新密码不能与默认密码相同")
                else:
                    try:
                        db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt(new_p), current_user))
                        db.commit()
                        del st.session_state.force_pwd_change
                        st.success("✅ 密码修改成功！正在进入系统...")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
        st.stop()

    current_role = user_row["role"]
    st.session_state.role = current_role

    try:
        all_users_data = get_all_users(db)
    except Exception:
        all_users_data = []

    user_tz = user_row.get("timezone_offset")
    if user_tz is None:
        user_tz = 8.0
    now = get_user_now(user_tz)
    today = now.date()

    try:
        if now.hour >= 21:
            today_record = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (today.isoformat(), current_user)).fetchone()
            if not today_record and user_row.get("webhook_url") and st.session_state.get(f"alerted_{today}") != True:
                url = user_row["webhook_url"]
                if "bark" in url: requests.get(f"{url}/今天还没打卡哦！", timeout=2)
                elif "serverchan" in url: requests.post(url, data={"title": "学习打卡提醒", "desp": "今天还没打卡哦！"}, timeout=2)
                else: requests.get(url, timeout=2)
                st.session_state[f"alerted_{today}"] = True
    except Exception: pass

    with st.sidebar:
        st.title("学习打卡")
        is_mobile_mode = st.checkbox("📱 手机精简模式", value=False)

        try:
            visible_users = get_visible_users(db, current_user, current_role)
        except Exception:
            visible_users = [current_user]
        if current_user not in visible_users:
            visible_users = [current_user] + visible_users

        if current_role == "user":
            view_as = current_user
        elif current_role in ("admin", "host"):
            idx = visible_users.index(current_user) if current_user in visible_users else 0
            label = "管理员特权：切换账号" if current_role == "admin" else "切换配置对象"
            view_as = st.selectbox(label, visible_users, index=idx)
        else:
            view_as = current_user

        if view_as not in visible_users:
            view_as = current_user

        try:
            target_urow = db.execute("SELECT timezone_offset FROM users WHERE username=?", (view_as,)).fetchone()
            target_tz = target_urow.get("timezone_offset") if target_urow else 8.0
            if target_tz is None: target_tz = 8.0
        except Exception:
            target_tz = 8.0
        view_today = get_user_today(target_tz)

        view_makeup_sidebar = get_makeup_cards_of(view_as)

        role_display = {"admin": "管理员", "host": "Host", "user": "普通用户"}.get(current_role, current_role)
        st.info(f"当前身份：{html.escape(view_as)} ({role_display})\n\n当地时间：{get_user_now(target_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n🎫 补签卡：{view_makeup_sidebar} 张")
        try:
            bal = get_balance(view_as)
        except Exception:
            bal = {"balance": 0, "daily": 0, "period": 0, "exam": 0, "special": 0, "spent": 0, "extra": 0}
        st.metric("当前可用积分", f"{bal['balance']:.1f}")

        if not is_mobile_mode:
            with st.expander("专注计时器 (番茄钟)", expanded=False):
                render_timer()
            with st.expander("我的成就徽章"):
                try:
                    user_badges = get_user_badges(view_as)
                except Exception:
                    user_badges = []
                if user_badges:
                    for i in range(0, len(user_badges), 3):
                        cols = st.columns(3)
                        for j in range(3):
                            if i + j < len(user_badges):
                                b = user_badges[i + j]
                                with cols[j]:
                                    st.markdown(
                                        f'<div style="height:70px; display:flex; align-items:center; justify-content:center;">'
                                        f'<img src="{b["icon"]}" width="60" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'">'
                                        f'</div>', unsafe_allow_html=True
                                    )
                                    st.markdown(f"<div style='text-align: center; font-size: 14px;'>{b['name']}</div>", unsafe_allow_html=True)
                else:
                    st.caption("暂无徽章。")

            with st.expander("积分明细"):
                st.write(f"打卡：{bal['daily']:.1f} | 长期：{bal['period']:.1f}")
                st.write(f"考试：{bal['exam']:.1f} | 偶发：{bal['extra']:.1f}")
                st.write(f"特殊：{bal['special']:.1f} | 消耗：-{bal['spent']:.1f}")

            st.divider()
            with st.expander("账号与数据设置"):
                st.markdown("**时区设置**")
                curr_tz_name = next((k for k, v in TIMEZONES.items() if v == user_tz), "自定义时区")
                new_tz_name = st.selectbox("所在地区/时区", list(TIMEZONES.keys()), index=list(TIMEZONES.keys()).index(curr_tz_name))

                if new_tz_name == "自定义时区":
                    custom_tz = st.number_input("输入 UTC 偏移小时数 (如 5.5 代表印度)", value=float(user_tz), step=0.5, min_value=-12.0, max_value=14.0)
                    final_tz = custom_tz
                else:
                    final_tz = TIMEZONES[new_tz_name]

                if st.button("保存时区设置", use_container_width=True):
                    try:
                        db.execute("UPDATE users SET timezone_offset=? WHERE username=?", (final_tz, current_user))
                        db.commit(); st.success("时区已更新！"); st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))

                st.divider()
                new_name = st.text_input("新用户名", placeholder="留空则不修改", max_chars=20)
                if st.button("确认修改用户名", use_container_width=True):
                    if new_name and new_name != current_user:
                        if new_name.lower() in ["system", "admin"]:
                            st.error("该用户名为系统保留，请换一个")
                        else:
                            try:
                                if db.execute("SELECT * FROM users WHERE username=?", (new_name,)).fetchone():
                                    st.error("该用户名已被占用")
                                else:
                                    for tbl in ["daily_records", "period_bonus", "redemptions", "exam_rewards", "special_events", "extra_points", "config_tasks", "config_shop", "config_exam", "config_exam_rules", "config_thresholds", "config_bonus_rules", "config_exam_multihit"]:
                                        db.execute(f"UPDATE {tbl} SET owner_id=? WHERE owner_id=?", (new_name, current_user))
                                    db.execute("UPDATE users SET host_id=? WHERE host_id=?", (new_name, current_user))
                                    db.execute("UPDATE users SET username=? WHERE username=?", (new_name, current_user))
                                    db.commit(); st.session_state.user = new_name; st.cache_data.clear(); st.success("用户名修改成功！"); st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))

                st.divider()
                new_pwd = st.text_input("新密码", type="password", key="new_pwd", max_chars=72)
                if st.button("确认修改密码", use_container_width=True):
                    if new_pwd:
                        try:
                            db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt(new_pwd), current_user))
                            db.commit(); st.success("密码已修改！")
                        except RuntimeError as e:
                            st.error(str(e))

                st.divider()
                webhook_input = st.text_input("防遗忘提醒 Webhook", value=user_row.get("webhook_url") or "")
                if st.button("保存 Webhook", use_container_width=True):
                    try:
                        db.execute("UPDATE users SET webhook_url=? WHERE username=?", (webhook_input, current_user))
                        db.commit(); st.success("保存成功！")
                    except RuntimeError as e:
                        st.error(str(e))

                st.divider()
                try:
                    my_data = {
                        "daily_records": [dict(r) for r in db.execute("SELECT * FROM daily_records WHERE owner_id=?", (current_user,)).fetchall()],
                        "exam_rewards": [dict(r) for r in db.execute("SELECT * FROM exam_rewards WHERE owner_id=?", (current_user,)).fetchall()],
                        "redemptions": [dict(r) for r in db.execute("SELECT * FROM redemptions WHERE owner_id=?", (current_user,)).fetchall()],
                        "extra_points": [dict(r) for r in db.execute("SELECT * FROM extra_points WHERE owner_id=?", (current_user,)).fetchall()],
                        "special_events": [dict(r) for r in db.execute("SELECT * FROM special_events WHERE owner_id=?", (current_user,)).fetchall()]
                    }
                    st.download_button(
                        "📥 导出我的数据 (JSON)",
                        data=json.dumps(my_data, ensure_ascii=False, indent=2, default=str),
                        file_name=f"backup_{current_user}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                except Exception: pass

        st.divider()
        if st.button("退出登录", use_container_width=True):
            del st.session_state.user
            del st.session_state.role
            st.rerun()

    base_desktop = ["打卡", "偶发", "历史与图表", "商城", "兑换", "考试", "事件"]
    base_mobile = ["打卡", "商城", "兑换"]
    can_config = current_role in ("admin", "host")

    if is_mobile_mode:
        tabs = base_mobile + (["系统设置"] if can_config else [])
    else:
        tabs = base_desktop + (["系统设置"] if can_config else [])

    tab_objs = st.tabs(tabs)
    tab_dict = {name: obj for name, obj in zip(tabs, tab_objs)}

    # ============ 打卡 ============
    with tab_dict.get("打卡"):
        try:
            tasks = get_tasks(view_today.weekday(), view_as)
        except Exception:
            tasks = []

        if not tasks:
            st.warning("今日还没有配置任务哦，请去【系统设置】里添加！")
        else:
            try:
                thresholds = get_thresholds(view_as); thr = thresholds.get(view_today.weekday(), {"basic": 0, "full": 0})
            except Exception:
                thr = {"basic": 0, "full": 0}

            st.subheader(f"{view_today.strftime('%m月%d日')} - {WEEKDAY_CN[view_today.weekday()]}")
            st.caption(f"基本要求：{thr['basic']} 分 | 满分：{thr['full']} 分")

            try:
                existing = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)).fetchone()
            except Exception:
                existing = None

            already_done = existing is not None
            done_ids = set(json.loads(existing["done_tasks"])) if (existing and existing["done_tasks"]) else set()

            cats = {}
            for t in tasks:
                cats.setdefault(t["category"], []).append(t)

            selected_ids = []
            for cat, items in cats.items():
                st.markdown(f"**{html.escape(cat)}**")
                if is_mobile_mode:
                    for t in items:
                        if st.checkbox(f"{html.escape(t['name'])} ({t['points']}分)", value=(t["id"] in done_ids), key=f"cb_{view_today}_{view_as}_{t['id']}", disabled=already_done):
                            if not already_done: selected_ids.append(t["id"])
                else:
                    cols = st.columns(2)
                    for i, t in enumerate(items):
                        with cols[i % 2]:
                            if st.checkbox(f"{html.escape(t['name'])} ({t['points']}分)", value=(t["id"] in done_ids), key=f"cb_{view_today}_{view_as}_{t['id']}", disabled=already_done):
                                if not already_done: selected_ids.append(t["id"])

            st.divider()
            c1, c2, c3 = st.columns(3)
            if already_done:
                c1.metric("基础分", f"{float(existing['base_score'] or 0):.1f}")
                c2.metric("Bonus", f"{float(existing['bonus_score'] or 0):.1f}")
                c3.metric("今日总分", f"{float(existing['total_score'] or 0):.1f}")
                st.success("今日已完成打卡，记录已锁定。")
                if st.button("撤销今日打卡（重新填写）", type="secondary", use_container_width=True):
                    try:
                        db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as))
                        db.commit()
                        recalc_all_bonus(db, view_as)
                        settle_longterm_bonus(db, view_as, now.isoformat())
                        st.cache_data.clear()
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
            else:
                base_now = sum(t["points"] for t in tasks if t["id"] in set(selected_ids))
                try:
                    lookup = {r["day"]: {"base_score": float(r["base_score"] or 0), "basic_thr": float(r.get("basic_thr") or 0), "full_thr": float(r.get("full_thr") or 0)}
                              for r in db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=?", (view_as,)).fetchall()}
                    lookup[view_today.isoformat()] = {"base_score": base_now, "basic_thr": thr["basic"], "full_thr": thr["full"]}
                    bonus, detail = compute_bonus_for_day(view_today, lookup, get_bonus_rules(view_as))
                except Exception:
                    bonus, detail = 0.0, {}

                c1.metric("基础分", f"{base_now:.1f}")
                c2.metric("Bonus", f"{bonus:.1f}")
                c3.metric("预计总分", f"{base_now + bonus:.1f}")
                if detail.get("tier") in TIER_CN:
                    st.info(f"Bonus 判定：{TIER_CN[detail['tier']]}")
                if st.button("保存今日打卡", type="primary", use_container_width=True):
                    try:
                        save_day(db, view_today, selected_ids, view_as, now.isoformat())
                        st.success("已保存！"); st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))

    # ============ 偶发 ============
    if "偶发" in tab_dict:
        with tab_dict["偶发"]:
            st.subheader("偶发事件加/扣分")
            with st.form("extra_point_form"):
                col1, col2, col3 = st.columns([4, 2, 2])
                e_name = col1.text_input("事件名称", placeholder="例如：高分作文...")
                e_pts = col2.number_input("分数 (可为负数)", value=1.0, step=0.5)
                if _submit("确认提交", type="primary"):
                    if e_name:
                        try:
                            db.execute("INSERT INTO extra_points (owner_id, name, points, ts) VALUES (?,?,?,?)", (view_as, e_name, e_pts, now.isoformat()))
                            db.commit(); st.cache_data.clear(); st.success(f"已记录：{html.escape(e_name)} ({e_pts}分)"); st.rerun()
                        except RuntimeError as e:
                            st.error(str(e))
            st.divider()
            try:
                ex_rows = db.execute("SELECT * FROM extra_points WHERE owner_id=? ORDER BY id DESC LIMIT 20", (view_as,)).fetchall()
            except Exception:
                ex_rows = []
            if ex_rows:
                st.dataframe([{"时间": r["ts"], "事件": html.escape(r["name"]), "积分": float(r["points"] or 0)} for r in ex_rows], use_container_width=True, hide_index=True)
                if st.button("清空偶发记录", use_container_width=True):
                    try:
                        db.execute("DELETE FROM extra_points WHERE owner_id=?", (view_as,))
                        db.commit(); st.cache_data.clear(); st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
            else:
                st.caption("暂无记录")

    # ============ 历史与图表 ============
    if "历史与图表" in tab_dict:
        with tab_dict["历史与图表"]:
            st.subheader("历史与图表分析")
            view_makeup_hist = get_makeup_cards_of(view_as)
            if view_makeup_hist > 0:
                st.markdown(f"🎫 **当前配置对象有 {view_makeup_hist} 张补签卡，可用于补全最近 7 天内漏掉的打卡：**")
                try:
                    missing_dates = [view_today - timedelta(days=i) for i in range(1, 8)
                                     if not db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", ((view_today - timedelta(days=i)).isoformat(), view_as)).fetchone()]
                except Exception:
                    missing_dates = []

                if missing_dates:
                    sel_date = st.selectbox("选择要补签的日期", missing_dates, format_func=lambda x: x.strftime('%Y-%m-%d') + f" ({WEEKDAY_CN[x.weekday()]})")
                    past_tasks = get_tasks(sel_date.weekday(), view_as)
                    st.write(f"**请勾选你在 {sel_date.strftime('%m月%d日')} 实际完成的任务（提交后将强制算作满分）：**")
                    with st.form("makeup_form"):
                        selected_past_ids = [t["id"] for t in past_tasks if st.checkbox(f"{html.escape(t['name'])} ({t['points']}分)", key=f"makeup_cb_{sel_date}_{t['id']}")]
                        if _submit("使用 1 张补签卡并提交", type="primary"):
                            try:
                                cur = db.execute("UPDATE users SET makeup_cards = makeup_cards - 1 WHERE username=? AND makeup_cards > 0", (view_as,))
                                db.commit()
                                if cur.rowcount > 0:
                                    t_thr = get_thresholds(view_as).get(sel_date.weekday(), {"basic": 8, "full": 11})
                                    db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (sel_date.isoformat(), view_as))
                                    db.execute(
                                        "INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) VALUES (?, ?, ?, ?, 0, '{}', ?, ?, ?, ?)",
                                        (sel_date.isoformat(), view_as, json.dumps(sorted(selected_past_ids)), t_thr["full"], t_thr["full"], now.isoformat(), t_thr["basic"], t_thr["full"])
                                    )
                                    db.commit()
                                    recalc_all_bonus(db, view_as)
                                    settle_longterm_bonus(db, view_as, now.isoformat())
                                    st.cache_data.clear(); st.success("补签成功！"); st.rerun()
                                else:
                                    st.error("补签失败，当前配置对象余额不足。")
                            except RuntimeError as e:
                                st.error(str(e))
                else:
                    st.info("最近 7 天全勤！")
            else:
                st.info('💡 提示：商城有售「补签卡」。')

            st.divider()
            time_view = st.radio("时间维度", ["按日查看", "按周查看", "按月查看"], horizontal=True)
            try:
                all_recs = db.execute("SELECT day, total_score FROM daily_records WHERE owner_id=? ORDER BY day ASC", (view_as,)).fetchall()
            except Exception:
                all_recs = []

            if all_recs:
                df = pd.DataFrame([{"日期": r["day"], "总分": float(r["total_score"] or 0)} for r in all_recs])
                df["日期"] = pd.to_datetime(df["日期"])
                if time_view == "按日查看":
                    df_grouped = df.copy(); x_title = "日期 (每日)"
                elif time_view == "按周查看":
                    df_grouped = df.set_index("日期").resample('W-MON', label='left', closed='left').sum().reset_index(); x_title = "日期 (每周一)"
                else:
                    df_grouped = df.set_index("日期").resample('MS').sum().reset_index(); x_title = "日期 (每月1日)"

                st.altair_chart(
                    alt.Chart(df_grouped).mark_line(point=True, color='#1f77b4').encode(
                        x=alt.X('日期:T', title=x_title, axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('总分:Q', title='总分', axis=alt.Axis(labelAngle=0)),
                        tooltip=[alt.Tooltip('日期:T', format='%Y-%m-%d'), '总分:Q']
                    ).interactive(),
                    use_container_width=True
                )
                st.altair_chart(
                    alt.Chart(df_grouped).mark_bar().encode(
                        x=alt.X('日期:T', title=x_title, axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('总分:Q', title='总分', axis=alt.Axis(labelAngle=0)),
                        color=alt.Color('总分:Q', scale=alt.Scale(scheme='greens'), legend=None),
                        tooltip=[alt.Tooltip('日期:T', format='%Y-%m-%d'), '总分:Q']
                    ),
                    use_container_width=True
                )
            else:
                st.info("暂无数据。")

            st.divider(); st.subheader("历史打卡详情")
            try:
                days = [r["day"] for r in db.execute("SELECT day FROM daily_records WHERE owner_id=? ORDER BY day DESC", (view_as,)).fetchall()]
            except Exception:
                days = []

            if days:
                sel = st.selectbox("选择日期", days)
                try:
                    row = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (sel, view_as)).fetchone()
                    st.write(f"**总分: {float(row['total_score'] or 0):.1f}** (基础 {float(row['base_score'] or 0):.1f} + Bonus {float(row['bonus_score'] or 0):.1f})")
                    done = json.loads(row["done_tasks"]) if row["done_tasks"] else []
                    st.write("完成项：", ", ".join([html.escape(t["name"]) for t in get_tasks(date.fromisoformat(sel).weekday(), view_as) if t["id"] in done]) or "无")
                except Exception: pass
            else:
                st.info("暂无记录")

    # ============ 商城 ============
    if "商城" in tab_dict:
        with tab_dict["商城"]:
            st.subheader("商城")
            try:
                shop_items = get_shop(view_as)
            except Exception:
                shop_items = []

            if not shop_items:
                st.warning("商城空！")
            else:
                try:
                    bal = get_balance(view_as)
                except Exception:
                    bal = {"balance": 0}

                for name, cost in shop_items:
                    c1, c2, c3 = st.columns([5, 2, 2])
                    c1.write(f"**{html.escape(name)}**")
                    c2.write(f"`{cost} 分`")
                    confirm_key = f"confirm_buy_{view_as}_{name}"
                    if st.session_state.get(confirm_key):
                        cc1, cc2 = st.columns(2)
                        if cc1.button("确认扣除", key=f"yes_{view_as}_{name}", type="primary", use_container_width=True):
                            try:
                                curr_bal = get_balance(view_as)
                                if curr_bal["balance"] < cost:
                                    st.error("积分不足，兑换失败。")
                                else:
                                    if name == "补签卡":
                                        db.execute("UPDATE users SET makeup_cards = makeup_cards + 1 WHERE username=?", (view_as,))
                                    db.execute("INSERT INTO redemptions (owner_id, item, cost, ts) VALUES (?,?,?,?)", (view_as, name, cost, now.isoformat()))
                                    db.commit()
                                    st.session_state[confirm_key] = False
                                    st.cache_data.clear(); st.success("兑换成功！"); st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                        if cc2.button("取消", key=f"no_{view_as}_{name}", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
                    else:
                        if c3.button("兑换", key=f"buy_{view_as}_{name}", disabled=(bal["balance"] < cost), use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()

    # ============ 兑换 ============
    if "兑换" in tab_dict:
        with tab_dict["兑换"]:
            st.subheader("兑换历史")
            try:
                rows = db.execute("SELECT * FROM redemptions WHERE owner_id=? ORDER BY id DESC", (view_as,)).fetchall()
            except Exception:
                rows = []

            if rows:
                st.dataframe([{"时间": r["ts"], "奖励": html.escape(r["item"]), "消耗": float(r["cost"] or 0)} for r in rows], use_container_width=True)
            else:
                st.info("暂无")

    # ============ 考试 ============
    if "考试" in tab_dict:
        with tab_dict["考试"]:
            st.subheader("考试专项")
            try:
                exam_config, _ = get_exam_config(view_as)
            except Exception:
                exam_config = {}

            if not exam_config:
                st.warning("未设置考试科目！")
            else:
                scores = {}; ranks = {}
                subjects_list = list(exam_config.keys())
                for i in range(0, len(subjects_list), 3):
                    cols = st.columns(3)
                    for j in range(3):
                        if i + j < len(subjects_list):
                            sub = subjects_list[i + j]; cfg = exam_config[sub]
                            with cols[j]:
                                if cfg["type"] == "score":
                                    max_s = float(cfg.get("max_score", 150))
                                    scores[sub] = st.number_input(f"{html.escape(sub)} (满分{max_s:.0f}, 目标{cfg['target']})", min_value=0.0, max_value=max_s, value=float(cfg.get('target', 0)), key=f"ex_{view_as}_{sub}")
                                else:
                                    target_idx = GRADES.index(cfg['target']) if cfg['target'] in GRADES else 0
                                    scores[sub] = st.selectbox(f"{html.escape(sub)} (目标{cfg['target']})", GRADES, index=target_idx, key=f"ex_sel_{view_as}_{sub}")
                st.write("**语数外排名前百分之多少（填100不参与）**")
                c1, c2, c3 = st.columns(3)
                ranks["语文"] = c1.number_input("语文", 0.0, 100.0, 100.0, key=f"rk_cn_{view_as}")
                ranks["数学"] = c2.number_input("数学", 0.0, 100.0, 100.0, key=f"rk_ma_{view_as}")
                ranks["英语"] = c3.number_input("英语", 0.0, 100.0, 100.0, key=f"rk_en_{view_as}")

                total_pts, lines, hit_count = calc_exam_bonus(scores, ranks, view_as)
                st.divider()
                st.markdown(f"### 预计获得：**{total_pts:.1f}** 分（达成 {hit_count} 门）")
                for ln in lines:
                    st.write(ln)
                if st.button("保存本次成绩", type="primary", use_container_width=True):
                    try:
                        detail_text = f"达成 {hit_count} 门 | " + "/".join([f"{k}:{v}" for k, v in scores.items()])
                        db.execute("INSERT INTO exam_rewards (owner_id, detail, points, ts) VALUES (?,?,?,?)", (view_as, detail_text, total_pts, now.isoformat()))
                        db.commit(); st.cache_data.clear(); st.success("已保存！"); st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))

    # ============ 事件 ============
    if "事件" in tab_dict:
        with tab_dict["事件"]:
            st.subheader("特殊事件")
            try:
                fired = db.execute("SELECT * FROM special_events WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)).fetchone()
            except Exception:
                fired = None

            if fired:
                st.info(f"今天已经触发过啦：{html.escape(fired['note'])} +{float(fired['points'] or 0)}分")
            else:
                if st.session_state.get("confirm_roll"):
                    st.warning("🎲 确认消耗今天的机会摇一摇吗？")
                    rc1, rc2 = st.columns(2)
                    if rc1.button("确认摇一摇", type="primary", use_container_width=True):
                        try:
                            roll = random.random()
                            pts = random.randint(1, 2) if roll < 0.4 else random.randint(3, 5) if roll < 0.8 else random.randint(6, 8) if roll < 0.95 else random.randint(10, 15)
                            db.execute("INSERT INTO special_events (day, owner_id, points, note, ts) VALUES (?,?,?,?,?)", (view_today.isoformat(), view_as, pts, "积分暴击", now.isoformat()))
                            db.commit()
                            st.session_state["confirm_roll"] = False
                            st.cache_data.clear(); st.balloons(); st.success(f"获得 {pts} 积分！"); st.rerun()
                        except RuntimeError as e:
                            st.error(str(e))
                    if rc2.button("取消", use_container_width=True):
                        st.session_state["confirm_roll"] = False
                        st.rerun()
                else:
                    if st.button("摇一摇", use_container_width=True):
                        st.session_state["confirm_roll"] = True
                        st.rerun()

    # ============ 系统设置 ============
    if "系统设置" in tab_dict:
        with tab_dict["系统设置"]:
            st.subheader("系统设置")
            if current_role == "admin":
                st.info(f"当前正在配置：**{html.escape(view_as)}**")
            elif current_role == "host":
                st.info(f"当前正在配置：**{html.escape(view_as)}**")
            else:
                st.info("当前正在配置你的专属设置。")

            # ---- 1. 修改每日任务 ----
            st.markdown("### 1. 修改每日任务")
            sel_wd = st.selectbox("选择要修改的星期", range(7), format_func=lambda x: WEEKDAY_CN[x])
            try:
                tasks_df = db.execute("SELECT * FROM config_tasks WHERE weekday=? AND owner_id=?", (sel_wd, view_as)).fetchall()
            except Exception:
                tasks_df = []

            edited_tasks = st.data_editor(
                [dict(t) for t in tasks_df],
                column_config={
                    "id": st.column_config.TextColumn("任务ID", required=True),
                    "weekday": None, "owner_id": None,
                    "category": st.column_config.TextColumn("分类"),
                    "name": st.column_config.TextColumn("任务名称", required=True),
                    "points": st.column_config.NumberColumn("分数", min_value=0.0, step=0.5)
                },
                num_rows="dynamic", use_container_width=True, key=f"edit_task_{view_as}_{sel_wd}"
            )
            if st.button("保存任务修改", use_container_width=True):
                try:
                    db.execute("DELETE FROM config_tasks WHERE weekday=? AND owner_id=?", (sel_wd, view_as))
                    for t in edited_tasks:
                        if t.get("id") and t.get("name"):
                            db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)",
                                       (t["id"], sel_wd, view_as, t.get("category") or "", t["name"], float(t.get("points") or 0)))
                    db.commit(); st.cache_data.clear(); st.success("任务已更新！"); st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

            # ---- 2. 修改商城奖励 ----
            st.divider()
            st.markdown("### 2. 修改商城奖励")
            try:
                shop_df = db.execute("SELECT id, name, cost FROM config_shop WHERE owner_id=?", (view_as,)).fetchall()
            except Exception:
                shop_df = []

            edited_shop = st.data_editor(
                [dict(s) for s in shop_df],
                column_config={
                    "id": None,
                    "name": st.column_config.TextColumn("奖励名称", required=True),
                    "cost": st.column_config.NumberColumn("所需积分", min_value=0.0, step=1.0)
                },
                num_rows="dynamic", use_container_width=True, key=f"edit_shop_{view_as}"
            )
            if st.button("保存商城修改", use_container_width=True):
                try:
                    db.execute("DELETE FROM config_shop WHERE owner_id=?", (view_as,))
                    for s in edited_shop:
                        if s.get("name") and s.get("cost") is not None:
                            db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (view_as, s["name"], float(s["cost"])))
                    db.commit(); st.cache_data.clear(); st.success("商城已更新！"); st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

            # ---- 3. 修改考试科目 ----
            st.divider()
            st.markdown("### 3. 修改考试科目")
            try:
                exam_config, exam_rules = get_exam_config(view_as)
            except Exception:
                exam_config = {}

            df_exam_data = []
            for k, v in exam_config.items():
                max_s = v.get("max_score") if v["type"] == "score" else None
                step_s = v.get("step") if v["type"] == "score" else None
                df_exam_data.append({"科目": k, "类型": v["type"], "满分": max_s, "目标": str(v["target"]), "分差": step_s, "单档奖励": v["step_points"]})
            df_exam = pd.DataFrame(df_exam_data)
            if df_exam.empty:
                df_exam = pd.DataFrame(columns=["科目", "类型", "满分", "目标", "分差", "单档奖励"])

            edited_exam = st.data_editor(
                df_exam,
                column_config={
                    "科目": st.column_config.TextColumn("科目", required=True),
                    "类型": st.column_config.SelectboxColumn("类型", options=["score", "grade"], required=True),
                    "满分": st.column_config.NumberColumn("满分", min_value=0.0, step=1.0),
                    "目标": st.column_config.TextColumn("目标", required=True),
                    "分差": st.column_config.NumberColumn("分差", min_value=0.0, step=1.0),
                    "单档奖励": st.column_config.NumberColumn("单档奖励", min_value=0.0, step=0.5)
                }, num_rows="dynamic", use_container_width=True, key=f"edit_exam_{view_as}"
            )

            if st.button("保存考试科目修改", use_container_width=True):
                try:
                    db.execute("DELETE FROM config_exam WHERE owner_id=?", (view_as,))
                    has_error = False
                    for _, row in edited_exam.iterrows():
                        if pd.notna(row["科目"]) and row["科目"]:
                            sub = row["科目"]; e_type = str(row["类型"]).strip().lower(); e_target = str(row["目标"]).strip()
                            if e_type not in ["score", "grade"]:
                                st.error(f"科目 {sub} 类型错误"); has_error = True; break
                            if e_type == "score":
                                try:
                                    e_target_val = float(e_target)
                                except ValueError:
                                    st.error(f"科目 {sub} 目标必须是数字"); has_error = True; break
                                cfg = {"type": "score", "max_score": float(row["满分"] or 150), "target": e_target_val,
                                       "step": float(row["分差"] or 0), "step_points": float(row["单档奖励"] or 0)}
                            else:
                                if e_target not in GRADES:
                                    st.error(f"科目 {sub} 目标必须在 11 档内"); has_error = True; break
                                cfg = {"type": "grade", "target": e_target, "step_points": float(row["单档奖励"] or 0)}
                            db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (sub, view_as, json.dumps(cfg)))
                    if has_error:
                        db.commit()
                    else:
                        db.commit(); st.cache_data.clear(); st.success("科目已更新！"); st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

            # ---- 4. 修改多科达成奖励 ----
            st.divider()
            st.markdown("### 4. 修改多科达成奖励")
            try:
                mh_list = get_exam_multihit(view_as)
            except Exception:
                mh_list = []
            mh_df = pd.DataFrame(mh_list)
            if mh_df.empty:
                mh_df = pd.DataFrame(columns=["hit_count", "points"])
            edited_mh = st.data_editor(
                mh_df,
                column_config={
                    "hit_count": st.column_config.NumberColumn("达成科目数", min_value=1, step=1),
                    "points": st.column_config.NumberColumn("奖励分数", min_value=0.0, step=0.5)
                },
                num_rows="dynamic", use_container_width=True, key=f"edit_mh_{view_as}"
            )
            if st.button("保存多科奖励修改", use_container_width=True):
                try:
                    db.execute("DELETE FROM config_exam_multihit WHERE owner_id=?", (view_as,))
                    for _, row in edited_mh.iterrows():
                        if pd.notna(row["hit_count"]) and pd.notna(row["points"]):
                            db.execute("INSERT INTO config_exam_multihit (hit_count, owner_id, points) VALUES (?,?,?)",
                                       (int(row["hit_count"]), view_as, float(row["points"])))
                    db.commit(); st.cache_data.clear(); st.success("多科奖励已更新！"); st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

            # ---- 5. 修改阈值与 Bonus 规则 ----
            st.divider()
            st.markdown("### 5. 修改阈值与 Bonus 规则（阈值与 Bonus 规则下次打卡时生效）")
            try:
                thresholds = get_thresholds(view_as); bonus_rules = get_bonus_rules(view_as)
            except Exception:
                thresholds = {}; bonus_rules = DEFAULT_BONUS_RULES

            with st.form(f"bonus_form_{view_as}"):
                t_cols = st.columns(7); t_inputs = {}
                for i in range(7):
                    with t_cols[i]:
                        st.markdown(f"**{WEEKDAY_CN[i]}**")
                        t_inputs[i] = {
                            "basic": st.number_input("基本", value=float(thresholds.get(i, {"basic": 0})["basic"]), key=f"th_b_{view_as}_{i}"),
                            "full": st.number_input("满分", value=float(thresholds.get(i, {"full": 0})["full"]), key=f"th_f_{view_as}_{i}")
                        }
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**周中**")
                    wd_single = st.number_input("单日达标", value=float(bonus_rules["weekday"]["single"]["points"]), step=0.5, key=f"b1_{view_as}")
                    wd_single_full = st.number_input("单日满分", value=float(bonus_rules["weekday"]["single"]["full_points"]), step=0.5, key=f"b2_{view_as}")
                    wd_2 = st.number_input("连2达标", value=float(bonus_rules["weekday"]["streak2"]["points"]), step=0.5, key=f"b3_{view_as}")
                    wd_2_full = st.number_input("连2满分", value=float(bonus_rules["weekday"]["streak2"]["full_points"]), step=0.5, key=f"b4_{view_as}")
                    wd_4 = st.number_input("连4达标", value=float(bonus_rules["weekday"]["streak4"]["points"]), step=0.5, key=f"b5_{view_as}")
                    wd_4_full = st.number_input("连4满分", value=float(bonus_rules["weekday"]["streak4"]["full_points"]), step=0.5, key=f"b6_{view_as}")
                with c2:
                    st.markdown("**周末及长期**")
                    we_single = st.number_input("周末单日达标", value=float(bonus_rules["weekend"]["single"]["points"]), step=0.5, key=f"b7_{view_as}")
                    we_single_full = st.number_input("周末单日满分", value=float(bonus_rules["weekend"]["single"]["full_points"]), step=0.5, key=f"b8_{view_as}")
                    lt_wb = st.number_input("整周达标", value=float(bonus_rules["longterm"]["week_basic"]), step=0.5, key=f"b9_{view_as}")
                    lt_wf = st.number_input("完美一周", value=float(bonus_rules["longterm"]["week_full"]), step=0.5, key=f"b10_{view_as}")
                    lt_mb = st.number_input("整月达标", value=float(bonus_rules["longterm"]["month_basic"]), step=0.5, key=f"b11_{view_as}")
                    lt_mf = st.number_input("完美一月", value=float(bonus_rules["longterm"]["month_full"]), step=0.5, key=f"b12_{view_as}")

                    st.markdown("**弹性容错扣减分**")
                    flex_p = st.number_input("弹性完美扣减 (少1天满分)", value=float(bonus_rules["longterm"].get("week_flex_perfect_deduct", 1.0)), step=0.5, key=f"b13_{view_as}")
                    flex_b = st.number_input("弹性达标扣减 (少1天达标)", value=float(bonus_rules["longterm"].get("week_flex_basic_deduct", 0.5)), step=0.5, key=f"b14_{view_as}")

                if _submit("保存新规则 (下次打卡时生效)", type="primary"):
                    try:
                        for i in range(7):
                            db.execute("DELETE FROM config_thresholds WHERE weekday=? AND owner_id=?", (i, view_as))
                            db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)',
                                       (i, view_as, t_inputs[i]["basic"], t_inputs[i]["full"]))

                        new_bonus = {
                            "weekday": {
                                "single": {"points": wd_single, "full_points": wd_single_full},
                                "streak2": {"points": wd_2, "full_points": wd_2_full},
                                "streak4": {"points": wd_4, "full_points": wd_4_full}
                            },
                            "weekend": {"single": {"points": we_single, "full_points": we_single_full}},
                            "longterm": {
                                "week_basic": lt_wb, "week_full": lt_wf,
                                "month_basic": lt_mb, "month_full": lt_mf,
                                "week_flex_perfect_deduct": flex_p, "week_flex_basic_deduct": flex_b
                            }
                        }
                        db.execute("DELETE FROM config_bonus_rules WHERE owner_id=?", (view_as,))
                        db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (view_as, json.dumps(new_bonus)))
                        db.commit(); st.cache_data.clear(); st.success("✅ 新规则已保存，下次打卡时生效。"); st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))

            # ---- 6. 全局徽章配置 ----
            st.divider()
            st.markdown("### 6. 全局徽章配置与 AI 生成")
            if current_role == "admin":
                with st.form("add_badge_form"):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    b_name = c1.text_input("徽章名称")
                    b_type = c2.selectbox("达成条件", options=["days", "points", "perfect", "exam_hits"],
                                          format_func=lambda x: {"days": "累计打卡天数", "points": "累计赚取积分", "perfect": "完美周/月次数", "exam_hits": "单次考试达成科目数"}.get(x, x))
                    b_val = c3.number_input("达成数值", min_value=1.0, step=1.0)

                    if _submit("✨ AI 生成并添加", type="primary"):
                        if b_name:
                            try:
                                seed = random.randint(1, 99999)
                                prompt = f"Minimalist flat vector icon for '{b_name}', clean simple design, ui app icon, no text, white background, not exaggerated."
                                icon_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=256&height=256&nologo=true&seed={seed}"
                                db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)",
                                           (b_name, b_type, b_val, icon_url))
                                db.commit(); st.cache_data.clear(); st.success(f"徽章「{html.escape(b_name)}」已生成！"); st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))

                st.markdown("**当前全局已配置的徽章：**")
                try:
                    existing_badges = get_badge_configs()
                except Exception:
                    existing_badges = []

                if existing_badges:
                    for b in existing_badges:
                        c1, c2, c3, c4 = st.columns([2, 3, 3, 2])
                        with c1:
                            st.markdown(f'<img src="{html.escape(b["icon_url"] or "", quote=True)}" width="50" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'">', unsafe_allow_html=True)
                        c2.write(f"**{html.escape(b['name'])}**")
                        type_cn = {"days": "打卡天数", "points": "累计积分", "perfect": "完美次数", "exam_hits": "单次考试达科目数"}.get(b["cond_type"], b["cond_type"])
                        c3.write(f"条件：{type_cn} ≥ {b['cond_val']}")
                        if c4.button("删除", key=f"del_badge_{b['id']}", use_container_width=True):
                            try:
                                db.execute("DELETE FROM config_badges WHERE id=?", (b["id"],))
                                db.commit(); st.cache_data.clear(); st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
            else:
                st.info("全局徽章由管理员配置。")

            # ---- 7. 用户管理与权限控制 ----
            if current_role == "admin":
                st.divider()
                st.markdown("### 7. 用户管理与权限控制")

                all_tbls = ["users", "daily_records", "period_bonus", "redemptions", "exam_rewards",
                            "special_events", "extra_points", "config_tasks", "config_shop",
                            "config_exam", "config_exam_rules", "config_thresholds",
                            "config_bonus_rules", "config_exam_multihit"]

                for u in all_users_data:
                    uname = u["username"]; urole = u["role"]
                    try:
                        host_row = db.execute("SELECT host_id FROM users WHERE username=?", (uname,)).fetchone()
                        uhost = dict(host_row).get("host_id") if host_row else None
                    except Exception:
                        uhost = None

                    is_self = (uname == current_user)
                    role_badge = {"admin": "🟢 管理员", "host": "🟡 Host", "user": "⚪ 普通用户"}.get(urole, urole)

                    i1, i2, i3 = st.columns([3, 2, 3])
                    i1.write(f"👤 **{html.escape(uname)}**" + (" (你自己)" if is_self else ""))
                    i2.write(role_badge)
                    i3.write(f"↳ Host: **{html.escape(uhost)}**" if uhost else "↳ Host: —")

                    if not is_self:
                        rc1, rc2, rc3, rc4, rc5 = st.columns(5)

                        if rc1.button("→ 管理员", key=f"set_admin_{uname}", disabled=(urole == "admin"), use_container_width=True):
                            try:
                                db.execute("UPDATE users SET role='admin' WHERE username=?", (uname,))
                                db.commit(); st.rerun()
                            except RuntimeError as e: st.error(str(e))

                        if rc2.button("→ Host", key=f"set_host_{uname}", disabled=(urole == "host"), use_container_width=True):
                            try:
                                blocked = False
                                if urole == "admin":
                                    if _remaining_admins(db, uname) == 0:
                                        st.error("这是系统里最后一个管理员，不能降级为 Host。请先提升另一个用户为管理员。")
                                        blocked = True
                                if not blocked:
                                    db.execute("UPDATE users SET role='host' WHERE username=?", (uname,))
                                    db.commit(); st.rerun()
                            except RuntimeError as e: st.error(str(e))

                        if rc3.button("→ 普通用户", key=f"set_user_{uname}", disabled=(urole == "user"), use_container_width=True):
                            try:
                                blocked = False
                                if urole == "admin":
                                    if _remaining_admins(db, uname) == 0:
                                        st.error("这是系统里最后一个管理员，不能降级为普通用户。请先提升另一个用户为管理员。")
                                        blocked = True
                                if not blocked:
                                    db.execute("UPDATE users SET role='user' WHERE username=?", (uname,))
                                    db.commit(); st.rerun()
                            except RuntimeError as e: st.error(str(e))

                        if rc4.button("重置密码", key=f"reset_{uname}", use_container_width=True):
                            try:
                                db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt("123456"), uname))
                                db.commit(); st.success(f"用户 {uname} 的密码已重置为 123456")
                            except RuntimeError as e: st.error(str(e))

                        if rc5.button("删除", key=f"del_{uname}", use_container_width=True):
                            st.session_state[f"pending_del_{uname}"] = True
                            st.rerun()

                        bc1, bc2, bc3 = st.columns([3, 1, 1])
                        bind_val = bc1.text_input("绑定到 host", value=uhost or "", key=f"bind_val_{uname}", label_visibility="collapsed", placeholder="输入 host 用户名")
                        if bc2.button("保存绑定", key=f"save_bind_{uname}", use_container_width=True):
                            target = (bind_val or "").strip()
                            if not target:
                                st.error("Host 用户名不能为空")
                            elif target == uname:
                                st.error("不能绑定到自己")
                            else:
                                try:
                                    t_row = db.execute("SELECT role FROM users WHERE username=?", (target,)).fetchone()
                                    if not t_row:
                                        st.error(f"目标 {target} 不存在")
                                    elif t_row["role"] not in ("host", "admin"):
                                        st.error(f"目标 {target} 不是 host/admin")
                                    else:
                                        visited = {uname}; cur = target; cyclic = False
                                        while cur:
                                            if cur in visited:
                                                cyclic = True; break
                                            visited.add(cur)
                                            c_row = db.execute("SELECT host_id FROM users WHERE username=?", (cur,)).fetchone()
                                            cur = dict(c_row).get("host_id") if c_row else None
                                        if cyclic:
                                            st.error("检测到循环绑定，操作被拒绝")
                                        else:
                                            db.execute("UPDATE users SET host_id=? WHERE username=?", (target, uname))
                                            db.commit(); st.success(f"{uname} 已绑定到 {target}"); st.rerun()
                                except RuntimeError as e: st.error(str(e))
                        if bc3.button("解绑", key=f"unbind_{uname}", disabled=(not uhost), use_container_width=True):
                            try:
                                db.execute("UPDATE users SET host_id=NULL WHERE username=?", (uname,))
                                db.commit(); st.success(f"{uname} 已解绑"); st.rerun()
                            except RuntimeError as e: st.error(str(e))

                        pending_key = f"pending_del_{uname}"
                        if st.session_state.get(pending_key):
                            st.warning(f"确认删除用户 **{html.escape(uname)}**？此操作不可撤销。")
                            try:
                                bound_count = db.execute("SELECT COUNT(*) as c FROM users WHERE host_id=?", (uname,)).fetchone()["c"]
                            except Exception:
                                bound_count = 0
                            if bound_count > 0:
                                st.warning(f"该用户名下有 {bound_count} 个 user，删除后将解绑（user 数据保留）。")

                            cc1, cc2 = st.columns(2)
                            if cc1.button(f"确认删除 {uname}", key=f"confirm_del_{uname}", type="primary", use_container_width=True):
                                try:
                                    blocked = False
                                    if urole == "admin":
                                        if _remaining_admins(db, uname) == 0:
                                            st.error("这是系统里最后一个管理员，不能删除。请先提升另一个用户为管理员。")
                                            blocked = True
                                    if not blocked:
                                        db.execute("UPDATE users SET host_id=NULL WHERE host_id=?", (uname,))
                                        for tbl in all_tbls:
                                            col = "username" if tbl == "users" else "owner_id"
                                            db.execute(f"DELETE FROM {tbl} WHERE {col}=?", (uname,))
                                        db.commit()
                                        st.session_state.pop(pending_key, None)
                                        st.success(f"用户 {uname} 已彻底删除")
                                        st.rerun()
                                except RuntimeError as e: st.error(str(e))
                            if cc2.button("取消删除", key=f"cancel_del_{uname}", use_container_width=True):
                                st.session_state.pop(pending_key, None)
                                st.rerun()

                    st.divider()

if __name__ == "__main__":
    main()
