#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, random, os, hashlib, urllib.parse, re, html, requests
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
import streamlit.components.v1 as components

IS_CLOUD = "DATABASE_URL" in st.secrets
if IS_CLOUD:
    import psycopg2, psycopg2.extras
else:
    import sqlite3

BJ_TZ = timezone(timedelta(hours=8))
def bj_now() -> datetime: return datetime.now(BJ_TZ)
def bj_today() -> date: return bj_now().date()
DB_PATH = Path(__file__).resolve().parent / "study_points.db"
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

DEFAULT_ICON_BASE64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRkZEMzAwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDJMMTUuMDkgOC4yNkwyMiA5LjI3TDE3IDE0LjE0TDE4LjE4IDIxLjAyTDEyIDE3LjU3TDUuODIgMjEuMDJMOSAxNC4xNEwyIDkuMjdMOC45MSA4LjI2TDEyIDJ6Ij48L3BhdGg+PC9zdmc+"

# ================= 默认初始配置 =================
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

def hash_pwd(pwd: str) -> str: return hashlib.sha256(pwd.encode()).hexdigest()

# ================= 数据库底层封装 =================
class DBWrapper:
    def __init__(self, conn, is_cloud):
        self.conn = conn; self.is_cloud = is_cloud
    def execute(self, query, params=()):
        if self.is_cloud:
            query = query.replace("?", "%s")
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if params: cur.execute(query, params)
            else: cur.execute(query)
            return cur
        else: 
            return self.conn.execute(query, params)
    def commit(self): self.conn.commit()

@st.cache_resource(show_spinner=False)
def get_db():
    if IS_CLOUD:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        conn.autocommit = True; db = DBWrapper(conn, True)
        init_db(db); return db
    else:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row; db = DBWrapper(conn, False); init_db(db); return db

def init_db(db):
    try:
        if db.is_cloud:
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS security_question TEXT")
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS security_answer TEXT")
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'")
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_url TEXT")
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS makeup_cards INTEGER DEFAULT 0")
        else:
            try: db.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
            except: pass
            try: db.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")
            except: pass
            try: db.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            except: pass
            try: db.execute("ALTER TABLE users ADD COLUMN webhook_url TEXT")
            except: pass
            try: db.execute("ALTER TABLE users ADD COLUMN makeup_cards INTEGER DEFAULT 0")
            except: pass
        db.commit()
    except Exception: pass

    tables = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT DEFAULT 'user', security_question TEXT, security_answer TEXT, webhook_url TEXT, makeup_cards INTEGER DEFAULT 0)",
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
    db.commit()
    
    if db.is_cloud:
        alter_queries = [
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
            "ALTER TABLE config_exam_multihit ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'"
        ]
        for q in alter_queries:
            try: db.execute(q)
            except: pass
        db.commit()
    else:
        alter_queries = [
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
            "ALTER TABLE config_exam_multihit ADD COLUMN owner_id TEXT DEFAULT '晴'"
        ]
        for q in alter_queries:
            try: db.execute(q)
            except: pass
        db.commit()
    
    try:
        row = db.execute("SELECT * FROM users WHERE username='晴'").fetchone()
        if not row:
            db.execute("INSERT INTO users (username, password_hash, role, security_question, security_answer) VALUES (?, ?, 'admin', '管理员默认密保', '123456')", ("晴", hash_pwd("123456")))
            if not db.execute("SELECT * FROM config_tasks WHERE owner_id='晴'").fetchone():
                init_old_admin_data(db)
        else:
            db.execute("UPDATE users SET role='admin' WHERE username='晴'")
        db.commit()
    except Exception: pass
    
    # 【自动注入补签卡】如果商城里没有补签卡，就自动加进去
    try:
        for u in get_all_users(db):
            uname = u["username"]
            has_makeup = db.execute("SELECT * FROM config_shop WHERE owner_id=? AND name='补签卡'", (uname,)).fetchone()
            if not has_makeup:
                db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?, '补签卡', 25)", (uname,))
        db.commit()
    except Exception: pass

    try:
        global_badge_count = db.execute("SELECT COUNT(*) as c FROM config_badges WHERE owner_id='system'").fetchone()["c"]
        if global_badge_count == 0:
            db.execute("DELETE FROM config_badges")
            default_badges = [
                ("破壳而出", "days", 1),
                ("持之以恒", "days", 7),
                ("习惯成自然", "days", 30),
                ("积分大亨", "points", 100),
                ("完美主义", "perfect", 1),
                ("考神附体", "exam_hits", 4)
            ]
            for b in default_badges:
                prompt = f"Minimalist flat vector icon for '{b[0]}', clean simple design, ui app icon, no text, white background, not exaggerated"
                encoded_prompt = urllib.parse.quote(prompt)
                icon_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=256&height=256&nologo=true&seed=42"
                db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)", (b[0], b[1], b[2], icon_url))
        db.commit()
    except Exception:
        pass

def init_old_admin_data(db):
    DEFAULT_TASKS = [("hw_sort", 0, "校内", "作业分类", 1.0), ("hw_done", 0, "校内", "作业完成", 2.0)]
    DEFAULT_SHOP = [("专属夸夸", 6)]
    DEFAULT_EXAM_CONFIG = {"语文": {"type": "score", "target": 105.0, "step": 3.0, "step_points": 2.0}}
    DEFAULT_THRESHOLDS = {0: {"basic": 8.0, "full": 11.0}}
    for t in DEFAULT_TASKS: db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (t[0], t[1], "晴", t[2], t[3], t[4]))
    for s in DEFAULT_SHOP: db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", ("晴", s[0], s[1]))
    for sub, cfg in DEFAULT_EXAM_CONFIG.items(): db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (sub, "晴", json.dumps(cfg)))
    for wd, data in DEFAULT_THRESHOLDS.items(): db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)', (wd, "晴", data["basic"], data["full"]))
    db.execute("INSERT INTO config_exam_rules (owner_id, config_json) VALUES (?,?)", ("晴", json.dumps(DEFAULT_EXAM_RULES)))
    db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", ("晴", json.dumps(DEFAULT_BONUS_RULES)))
    db.commit()

def get_all_users(db): return [{"username": r["username"], "role": r["role"]} for r in db.execute("SELECT username, role FROM users").fetchall()]

def get_thresholds(db, oid):
    rows = db.execute("SELECT * FROM config_thresholds WHERE owner_id=?", (oid,)).fetchall()
    return {r["weekday"]: {"basic": r["basic"], "full": r["full"]} for r in rows}
def get_bonus_rules(db, oid):
    row = db.execute("SELECT rules_json FROM config_bonus_rules WHERE owner_id=?", (oid,)).fetchone()
    if not row: return DEFAULT_BONUS_RULES
    rules = json.loads(row["rules_json"])
    if "week_flex_perfect_deduct" not in rules["longterm"]: rules["longterm"]["week_flex_perfect_deduct"] = 1.0
    if "week_flex_basic_deduct" not in rules["longterm"]: rules["longterm"]["week_flex_basic_deduct"] = 0.5
    return rules
def get_tasks(db, weekday, oid):
    rows = db.execute("SELECT * FROM config_tasks WHERE weekday=? AND owner_id=?", (weekday, oid)).fetchall()
    return [{"id": r["id"], "category": r["category"], "name": r["name"], "points": r["points"]} for r in rows]
def get_shop(db, oid): return [(r["name"], r["cost"]) for r in db.execute("SELECT * FROM config_shop WHERE owner_id=?", (oid,)).fetchall()]
def get_exam_config(db, oid):
    subjects = {r["subject"]: json.loads(r["config_json"]) for r in db.execute("SELECT * FROM config_exam WHERE owner_id=?", (oid,)).fetchall()}
    rule_row = db.execute("SELECT config_json FROM config_exam_rules WHERE owner_id=?", (oid,)).fetchone()
    return subjects, json.loads(rule_row["config_json"]) if rule_row else DEFAULT_EXAM_RULES
def get_exam_multihit(db, oid): return [{"hit_count": r["hit_count"], "points": r["points"]} for r in db.execute("SELECT * FROM config_exam_multihit WHERE owner_id=? ORDER BY hit_count ASC", (oid,)).fetchall()]

def get_badge_configs(db):
    return db.execute("SELECT * FROM config_badges WHERE owner_id='system' ORDER BY id ASC").fetchall()

def compute_bonus_for_day(day: date, lookup: dict, bonus_rules: dict) -> tuple[float, dict]:
    key = day.isoformat(); rec = lookup.get(key)
    if rec is None: return 0.0, {}
    try: base = float(rec["base_score"])
    except: base = 0.0
    wd = day.weekday()
    basic_thr = float(rec.get("basic_thr") or 0)
    full_thr = float(rec.get("full_thr") or 0)
    
    if wd <= 4:
        if base < basic_thr: return 0.0, {"tier": "none"}
        streak_days = []; cur = day
        if wd == 3: streak = 1; all_full = base >= full_thr
        else:
            while cur.weekday() <= 4:
                if cur.weekday() == 3: cur -= timedelta(days=1); continue
                r = lookup.get(cur.isoformat())
                if r is None: break
                cur_basic = float(r.get("basic_thr") or 0)
                if float(r["base_score"]) >= cur_basic: streak_days.append(cur); cur -= timedelta(days=1)
                else: break
            streak = len(streak_days)
            all_full = all(float(lookup[x.isoformat()]["base_score"]) >= float(lookup[x.isoformat()].get("full_thr") or 999) for x in streak_days)
        rule = bonus_rules.get("weekday", DEFAULT_BONUS_RULES["weekday"])
        if streak >= 4: tier = "streak4"; bonus = rule[tier]["full_points"] if all_full else rule[tier]["points"]
        elif streak >= 2: tier = "streak2"; bonus = rule[tier]["full_points"] if all_full else rule[tier]["points"]
        else: tier = "single"; bonus = rule[tier]["full_points"] if base >= full_thr else rule[tier]["points"]
        return float(bonus), {"tier": tier, "streak": streak}
    if base < basic_thr: return 0.0, {"tier": "none"}
    rule = bonus_rules.get("weekend", DEFAULT_BONUS_RULES["weekend"])["single"]; bonus = rule["full_points"] if base >= full_thr else rule["points"]
    return float(bonus), {"tier": "weekend_single"}

def recalc_all_bonus(db, oid):
    try:
        bonus_rules = get_bonus_rules(db, oid)
        rows = db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=?", (oid,)).fetchall()
        lookup = {r["day"]: {"base_score": r["base_score"], "basic_thr": r.get("basic_thr"), "full_thr": r.get("full_thr")} for r in rows}
        for day_str in sorted(lookup):
            d = date.fromisoformat(day_str)
            bonus, detail = compute_bonus_for_day(d, lookup, bonus_rules)
            db.execute("UPDATE daily_records SET bonus_score=?, bonus_detail=?, total_score=? WHERE day=? AND owner_id=?", (bonus, json.dumps(detail), float(lookup[day_str]["base_score"]) + bonus, day_str, oid))
        db.commit()
    except Exception:
        pass

def settle_longterm_bonus(db, oid):
    try:
        bonus_rules = get_bonus_rules(db, oid)
        lt_rules = bonus_rules["longterm"]
        
        rows = db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=?", (oid,)).fetchall()
        scores = {r["day"]: r for r in rows}
        db.execute("DELETE FROM period_bonus WHERE owner_id=?", (oid,))
        if not scores: 
            db.commit(); return

        weeks = {}
        for ds in scores:
            d = date.fromisoformat(ds); y, w, _ = d.isocalendar()
            weeks.setdefault(f"{y}-W{w:02d}", []).append(d)
            
        week_status = {}
        
        for wk, dlist in weeks.items():
            monday = min(dlist) - timedelta(days=min(dlist).weekday())
            full_week = [monday + timedelta(days=i) for i in range(7)]
            if not all(x.isoformat() in scores for x in full_week): 
                week_status[wk] = {'is_perfect': False, 'is_basic': False}
                continue
                
            miss_basic = 0
            miss_full = 0
            for x in full_week:
                day_data = scores[x.isoformat()]
                if float(day_data["base_score"]) < float(day_data.get("basic_thr") or 999): miss_basic += 1
                elif float(day_data["base_score"]) < float(day_data.get("full_thr") or 999): miss_full += 1
                
            target_kind, target_pts = None, 0.0
            is_perfect = False
            is_basic = False

            if miss_basic == 0:
                is_basic = True
                if miss_full == 0:
                    is_perfect = True
                    target_kind = "完美一周(全满分)"
                    target_pts = lt_rules["week_full"]
                elif miss_full == 1:
                    is_perfect = True
                    target_kind = "完美一周(弹性1天)"
                    target_pts = max(0, lt_rules["week_full"] - lt_rules.get("week_flex_perfect_deduct", 1.0))
                else:
                    target_kind = "整周达标"
                    target_pts = lt_rules["week_basic"]
            elif miss_basic == 1:
                is_basic = True
                target_kind = "整周达标(弹性1天)"
                target_pts = max(0, lt_rules["week_basic"] - lt_rules.get("week_flex_basic_deduct", 0.5))
                
            week_status[wk] = {'is_perfect': is_perfect, 'is_basic': is_basic}
            
            if target_kind:
                db.execute("INSERT INTO period_bonus (period_key, owner_id, kind, points, ts) VALUES (?,?,?,?,?)", (f"W:{wk}", oid, target_kind, target_pts, bj_now().isoformat()))

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
            while cur < nxt:
                alldays.append(cur)
                cur += timedelta(days=1)
                
            if not all(x.isoformat() in scores for x in alldays): continue
            
            month_is_perfect = True
            month_is_basic = True
            
            for day_obj in alldays:
                ds = day_obj.isoformat()
                day_data = scores[ds]
                dy, dw, _ = day_obj.isocalendar()
                wk_key = f"{dy}-W{dw:02d}"
                w_stat = week_status.get(wk_key, {'is_perfect': False, 'is_basic': False})
                
                day_full = float(day_data["base_score"]) >= float(day_data.get("full_thr") or 999)
                day_basic = float(day_data["base_score"]) >= float(day_data.get("basic_thr") or 999)
                
                if not day_full and not w_stat['is_perfect']: month_is_perfect = False
                if not day_basic and not w_stat['is_basic']: month_is_basic = False

            target_kind, target_pts = None, 0.0
            if month_is_perfect: target_kind = "完美一月"; target_pts = lt_rules["month_full"]
            elif month_is_basic: target_kind = "整月达标"; target_pts = lt_rules["month_basic"]
                
            if target_kind:
                db.execute("INSERT INTO period_bonus (period_key, owner_id, kind, points, ts) VALUES (?,?,?,?,?)", (f"M:{mk}", oid, target_kind, target_pts, bj_now().isoformat()))
        db.commit()
    except Exception:
        pass

def get_balance(db, oid) -> dict:
    daily = db.execute("SELECT COALESCE(SUM(total_score),0) as s FROM daily_records WHERE owner_id=?", (oid,)).fetchone()["s"]
    period = db.execute("SELECT COALESCE(SUM(points),0) as s FROM period_bonus WHERE owner_id=?", (oid,)).fetchone()["s"]
    exam = db.execute("SELECT COALESCE(SUM(points),0) as s FROM exam_rewards WHERE owner_id=?", (oid,)).fetchone()["s"]
    special = db.execute("SELECT COALESCE(SUM(points),0) as s FROM special_events WHERE owner_id=?", (oid,)).fetchone()["s"]
    spent = db.execute("SELECT COALESCE(SUM(cost),0) as s FROM redemptions WHERE owner_id=?", (oid,)).fetchone()["s"]
    extra = db.execute("SELECT COALESCE(SUM(points),0) as s FROM extra_points WHERE owner_id=?", (oid,)).fetchone()["s"]
    
    return {
        "daily": round(float(daily), 2), "period": round(float(period), 2), 
        "exam": round(float(exam), 2), "special": round(float(special), 2), 
        "spent": round(float(spent), 2), "extra": round(float(extra), 2), 
        "balance": round(float(daily) + float(period) + float(exam) + float(special) + float(extra) - float(spent), 2)
    }

def grade_gap(target: str, actual: str) -> int: 
    if target not in GRADES or actual not in GRADES: return 0
    return GRADES.index(target) - GRADES.index(actual)

def calc_exam_bonus(db, scores: dict, ranks: dict, oid: str) -> tuple[float, list[str], int]:
    try:
        exam_config, exam_rules = get_exam_config(db, oid); multihit_rules = get_exam_multihit(db, oid)
    except Exception:
        return 0.0, ["数据配置异常，无法结算"], 0
        
    total = 0.0; lines = []; hit_count = 0
    for subject, cfg in exam_config.items():
        actual = scores.get(subject)
        if actual is None: continue
        if cfg.get("type") == "score":
            hit = actual >= cfg.get("target", 0)
            if hit: total += exam_rules.get("hit_points", 1); hit_count += 1; lines.append(f"达成 {subject} -> +{exam_rules.get('hit_points', 1)}")
            
            step = cfg.get("step", 0)
            tiers = int((actual - cfg.get("target", 0)) // step) if step > 0 and actual > cfg.get("target", 0) else 0
            if tiers > 0: 
                gain = tiers * cfg.get("step_points", 0); total += gain; lines.append(f"  {subject} 超目标 {tiers} 档 -> +{gain}")
        else:
            gap = grade_gap(cfg.get("target", "C"), actual); hit = gap >= 0
            if hit: total += exam_rules.get("hit_points", 1); hit_count += 1; lines.append(f"达成 {subject} -> +{exam_rules.get('hit_points', 1)}")
            if gap > 0: 
                gain = gap * cfg.get("step_points", 0); total += gain; lines.append(f"  {subject} 升 {gap} 档 -> +{gain}")
                
    for mh in sorted(multihit_rules, key=lambda x: x["hit_count"], reverse=True):
        if hit_count >= mh["hit_count"]: total += mh["points"]; lines.append(f"达成 {mh['hit_count']} 门及以上 -> +{mh['points']}"); break 
        
    for subject in ["语文", "数学", "英语"]:
        pct = ranks.get(subject)
        if pct is not None and 0 <= pct < 100 and pct <= exam_rules.get("rank_top_percent", 75):
            total += exam_rules.get("rank_base_points", 1); lines.append(f"{subject} 前{pct:.0f}% -> +{exam_rules.get('rank_base_points', 1)}")
            pct_step = exam_rules.get("rank_step_percent", 5)
            extra = int((exam_rules.get("rank_top_percent", 75) - pct) // pct_step) if pct_step > 0 else 0
            if extra > 0: 
                gain = extra * exam_rules.get("rank_step_points", 1.5); total += gain; lines.append(f"  再进{extra}档 -> +{gain}")
                
    return round(total, 2), lines, hit_count

def save_day(db, day: date, done_ids: list[str], oid: str):
    tasks = get_tasks(db, day.weekday(), oid)
    base = sum(t["points"] for t in tasks if t["id"] in set(done_ids))
    ts = bj_now().isoformat(timespec="seconds")
    thresholds = get_thresholds(db, oid)
    thr = thresholds.get(day.weekday(), {"basic": 0, "full": 0})
    db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (day.isoformat(), oid))
    db.execute("""
        INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) 
        VALUES (?, ?, ?, ?, 0, '{}', ?, ?, ?, ?)
    """, (day.isoformat(), oid, json.dumps(sorted(done_ids)), base, base, ts, thr["basic"], thr["full"]))
    db.commit()
    recalc_all_bonus(db, oid)
    settle_longterm_bonus(db, oid)

# ================= 动态徽章判定逻辑 =================
def get_user_badges(db, oid):
    try:
        configs = get_badge_configs(db)
    except Exception:
        return []
        
    earned = []
    try:
        days_count = db.execute("SELECT COUNT(*) as c FROM daily_records WHERE owner_id=?", (oid,)).fetchone()["c"]
        bal = get_balance(db, oid)
        total_earned = bal['balance'] + bal['spent']
        perfect_count = db.execute("SELECT COUNT(*) as c FROM period_bonus WHERE owner_id=? AND kind LIKE ?", (oid, '%完美%')).fetchone()["c"]
        
        max_exam_hits = 0
        exam_rewards = db.execute("SELECT detail FROM exam_rewards WHERE owner_id=?", (oid,)).fetchall()
        for er in exam_rewards:
            if er["detail"]:
                match = re.search(r'达成 (\d+) 门', er["detail"])
                if match:
                    hits = int(match.group(1))
                    if hits > max_exam_hits: max_exam_hits = hits
    except Exception:
        return []

    for cfg in configs:
        try:
            cond_type = cfg["cond_type"]
            cond_val = float(cfg["cond_val"])
            is_hit = False
            
            if cond_type == 'days' and days_count >= cond_val: is_hit = True
            elif cond_type == 'points' and total_earned >= cond_val: is_hit = True
            elif cond_type == 'perfect' and perfect_count >= cond_val: is_hit = True
            elif cond_type == 'exam_hits' and max_exam_hits >= cond_val: is_hit = True
            
            if is_hit:
                earned.append({"name": html.escape(cfg["name"]), "icon": cfg["icon_url"]})
        except Exception:
            continue
    return earned

# ================= 前端计时器组件 =================
def render_timer():
    timer_html = """
    <style>
        .timer-container { font-family: sans-serif; text-align: center; padding: 15px; background: #f8f9fa; border-radius: 10px; }
        .timer-display { font-size: 40px; font-weight: bold; margin: 10px 0; color: #2c3e50; }
        .btn-group { display: flex; justify-content: center; gap: 10px; margin-top: 10px; flex-wrap: wrap;}
        button { padding: 8px 15px; font-size: 14px; cursor: pointer; border: none; border-radius: 5px; background: #007bff; color: white; transition: 0.2s; }
        button:hover { background: #0056b3; }
        .btn-stop { background: #dc3545; } .btn-stop:hover { background: #c82333; }
        .btn-reset { background: #6c757d; } .btn-reset:hover { background: #5a6268; }
        input[type="number"] { padding: 5px; width: 60px; font-size: 14px; margin: 0 5px; }
    </style>
    <div class="timer-container">
        <div class="timer-display" id="display">00:00</div>
        <div style="margin-bottom: 10px;">
            模式: 
            <select id="mode" style="padding:5px; border-radius:5px;">
                <option value="stopwatch">正计时</option>
                <option value="countdown">倒计时</option>
            </select>
            设定: <input type="number" id="minutes" value="25" min="1"> 分钟
        </div>
        <div class="btn-group">
            <button onclick="startTimer()">开始</button>
            <button class="btn-stop" onclick="stopTimer()">暂停</button>
            <button class="btn-reset" onclick="resetTimer()">重置</button>
        </div>
    </div>
    <script>
        let timerId = null;
        let isRunning = false;
        let totalSeconds = 0;
        let currentSeconds = 0;
        
        function updateDisplay() {
            let m = Math.floor(currentSeconds / 60).toString().padStart(2, '0');
            let s = (currentSeconds % 60).toString().padStart(2, '0');
            document.getElementById('display').innerText = m + ":" + s;
        }
        
        function startTimer() {
            if(isRunning) return;
            let mode = document.getElementById('mode').value;
            if(!isRunning && currentSeconds === 0) {
                if(mode === 'countdown') {
                    let mins = document.getElementById('minutes').value;
                    totalSeconds = mins * 60;
                    currentSeconds = totalSeconds;
                } else {
                    totalSeconds = 0;
                    currentSeconds = 0;
                }
            }
            isRunning = true;
            timerId = setInterval(() => {
                if(document.getElementById('mode').value === 'stopwatch') {
                    currentSeconds++;
                } else {
                    if(currentSeconds > 0) currentSeconds--;
                    else {
                        clearInterval(timerId); isRunning = false;
                        alert("时间到！"); return;
                    }
                }
                updateDisplay();
            }, 1000);
        }
        
        function stopTimer() {
            clearInterval(timerId);
            isRunning = false;
        }
        
        function resetTimer() {
            clearInterval(timerId);
            isRunning = false;
            currentSeconds = 0;
            updateDisplay();
        }
        updateDisplay();
    </script>
    """
    return components.html(timer_html, height=220)

# ================= 页面渲染 =================
def login_page(db):
    st.title("学习打卡系统")
    tab1, tab2, tab3 = st.tabs(["登录", "注册", "找回密码"])
    
    with tab1:
        with st.form("login_form"):
            u = st.text_input("用户名"); p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", type="primary", use_container_width=True):
                user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
                if user and user["password_hash"] == hash_pwd(p):
                    st.session_state.user = u
                    st.session_state.role = user["role"]
                    st.rerun()
                else: st.error("用户名或密码错误")
                
    with tab2:
        with st.form("reg_form"):
            u = st.text_input("设置用户名"); p = st.text_input("设置密码", type="password"); p2 = st.text_input("确认密码", type="password")
            sq = st.text_input("密保问题 (如：我的幸运数字？)")
            sa = st.text_input("密保答案")
            if st.form_submit_button("注册", type="primary", use_container_width=True):
                if not u or not p or not sq or not sa: st.error("请填写所有字段（含密保）")
                elif p != p2: st.error("密码不一致")
                elif u.lower() in ["system", "admin", "晴"]: st.error("该用户名为系统保留，请换一个")
                elif db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone(): st.error("用户名已存在")
                else:
                    db.execute("INSERT INTO users (username, password_hash, role, security_question, security_answer) VALUES (?, ?, 'user', ?, ?)", (u, hash_pwd(p), sq, hash_pwd(sa.strip().lower())))
                    db.commit()
                    st.success("注册成功！请去登录。")

    with tab3:
        st.write("输入用户名，验证密保问题后重设密码。")
        u_reset = st.text_input("请输入你的用户名", key="reset_u")
        if u_reset:
            user = db.execute("SELECT * FROM users WHERE username=?", (u_reset,)).fetchone()
            if user:
                sq = user.get("security_question")
                if not sq:
                    st.warning("该账户未设置密保问题，请联系管理员重置密码。")
                else:
                    with st.form("reset_form"):
                        st.info(f"密保问题：{html.escape(sq)}")
                        ans = st.text_input("密保答案")
                        new_p = st.text_input("新密码", type="password")
                        if st.form_submit_button("确认重置密码", type="primary"):
                            if not ans or not new_p: st.error("请填写完整")
                            elif hash_pwd(ans.strip().lower()) == user["security_answer"]:
                                db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd(new_p), u_reset))
                                db.commit()
                                st.success("密码重置成功！请去登录。")
                            else:
                                st.error("密保答案错误！")
            else:
                st.error("该用户名不存在")

def main():
    st.set_page_config(page_title="学习打卡系统", layout="centered", initial_sidebar_state="collapsed")
    db = get_db()
    now = bj_now(); today = now.date()

    if "user" not in st.session_state:
        login_page(db); return

    current_user = st.session_state.user
    user_row = db.execute("SELECT * FROM users WHERE username=?", (current_user,)).fetchone()
    if not user_row:
        del st.session_state.user; st.rerun()
    
    current_role = user_row["role"]
    st.session_state.role = current_role
    all_users_data = get_all_users(db)
    user_names = [u["username"] for u in all_users_data]

    # ================= 主动提醒逻辑 =================
    try:
        if now.hour >= 21:
            today_record = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (today.isoformat(), current_user)).fetchone()
            if not today_record and user_row.get("webhook_url") and st.session_state.get(f"alerted_{today}") != True:
                url = user_row["webhook_url"]
                if "bark" in url:
                    requests.get(f"{url}/今天还没打卡哦，连续记录快断了！", timeout=3)
                elif "serverchan" in url:
                    requests.post(url, data={"title": "学习打卡提醒", "desp": "今天还没打卡哦，快去保住你的积分和连击！"}, timeout=3)
                else:
                    requests.get(url, timeout=3)
                st.session_state[f"alerted_{today}"] = True
    except Exception:
        pass

    with st.sidebar:
        st.title("学习打卡")
        
        # 手机精简模式开关
        is_mobile_mode = st.checkbox("📱 手机精简模式", value=False, help="开启后仅保留核心功能，隐藏复杂配置")
        
        if current_role == "admin":
            view_as = st.selectbox("管理员特权：切换账号", user_names, index=user_names.index(current_user) if current_user in user_names else 0)
        else:
            view_as = current_user
        
        makeup_cards = user_row.get("makeup_cards") or 0
        st.info(f"当前身份：{html.escape(view_as)} ({current_role})\n\n北京时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n\n🎫 补签卡：{makeup_cards} 张")
        bal = get_balance(db, view_as)
        st.metric("当前可用积分", f"{bal['balance']:.1f}")
        
        if not is_mobile_mode:
            with st.expander("专注计时器 (番茄钟)", expanded=False):
                render_timer()
            
            with st.expander("我的成就徽章"):
                user_badges = get_user_badges(db, view_as)
                if user_badges:
                    for i in range(0, len(user_badges), 3):
                        cols = st.columns(3)
                        for j in range(3):
                            if i + j < len(user_badges):
                                b = user_badges[i+j]
                                with cols[j]:
                                    st.markdown(f'''
                                        <div style="height:70px; display:flex; align-items:center; justify-content:center;">
                                            <img src="{b["icon"]}" width="60" loading="lazy" onerror="this.src='{DEFAULT_ICON_BASE64}'">
                                        </div>
                                    ''', unsafe_allow_html=True)
                                    st.caption(f"<center>{b['name']}</center>", unsafe_allow_html=True)
                else:
                    st.caption("暂无徽章，快去打卡吧！")

            with st.expander("积分明细"):
                st.write(f"打卡：{bal['daily']:.1f} | 长期：{bal['period']:.1f}")
                st.write(f"考试：{bal['exam']:.1f} | 偶发：{bal['extra']:.1f}")
                st.write(f"特殊：{bal['special']:.1f} | 消耗：-{bal['spent']:.1f}")

            st.divider()
            with st.expander("账号与数据设置"):
                new_name = st.text_input("新用户名", placeholder="留空则不修改")
                if st.button("确认修改用户名"):
                    if new_name and new_name != current_user:
                        if new_name.lower() in ["system", "admin", "晴"]: st.error("该用户名为系统保留，请换一个")
                        elif db.execute("SELECT * FROM users WHERE username=?", (new_name,)).fetchone():
                            st.error("该用户名已被占用")
                        else:
                            tables_with_owner = ["daily_records", "period_bonus", "redemptions", "exam_rewards", "special_events", "extra_points", "config_tasks", "config_shop", "config_exam", "config_exam_rules", "config_thresholds", "config_bonus_rules", "config_exam_multihit"]
                            for tbl in tables_with_owner:
                                db.execute(f"UPDATE {tbl} SET owner_id=? WHERE owner_id=?", (new_name, current_user))
                            db.execute("UPDATE users SET username=? WHERE username=?", (new_name, current_user))
                            db.commit()
                            st.session_state.user = new_name
                            st.success("用户名修改成功！")
                            st.rerun()
                
                st.divider()
                new_pwd = st.text_input("新密码", type="password", key="new_pwd")
                if st.button("确认修改密码"):
                    if new_pwd:
                        db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd(new_pwd), current_user))
                        db.commit(); st.success("密码已修改！")
                
                st.divider()
                webhook_input = st.text_input("防遗忘提醒 Webhook", value=user_row.get("webhook_url") or "", help="超过21:00未打卡将推送")
                if st.button("保存 Webhook"):
                    db.execute("UPDATE users SET webhook_url=? WHERE username=?", (webhook_input, current_user))
                    db.commit(); st.success("保存成功！")
                
                st.divider()
                st.write("**数据备份**")
                my_data = {
                    "daily_records": [dict(r) for r in db.execute("SELECT * FROM daily_records WHERE owner_id=?", (current_user,)).fetchall()],
                    "exam_rewards": [dict(r) for r in db.execute("SELECT * FROM exam_rewards WHERE owner_id=?", (current_user,)).fetchall()],
                    "redemptions": [dict(r) for r in db.execute("SELECT * FROM redemptions WHERE owner_id=?", (current_user,)).fetchall()],
                    "extra_points": [dict(r) for r in db.execute("SELECT * FROM extra_points WHERE owner_id=?", (current_user,)).fetchall()],
                    "special_events": [dict(r) for r in db.execute("SELECT * FROM special_events WHERE owner_id=?", (current_user,)).fetchall()]
                }
                json_str = json.dumps(my_data, ensure_ascii=False, indent=2, default=str)
                st.download_button(
                    label="📥 导出我的数据备份 (JSON)",
                    data=json_str,
                    file_name=f"backup_{current_user}_{today.isoformat()}.json",
                    mime="application/json",
                    use_container_width=True
                )

                if current_role == "admin":
                    st.divider()
                    st.write("**全站数据备份（管理员专属）**")
                    all_data = {
                        "users": [{"username": r["username"], "role": r["role"]} for r in db.execute("SELECT username, role FROM users").fetchall()],
                        "daily_records": [dict(r) for r in db.execute("SELECT * FROM daily_records").fetchall()],
                        "period_bonus": [dict(r) for r in db.execute("SELECT * FROM period_bonus").fetchall()],
                        "exam_rewards": [dict(r) for r in db.execute("SELECT * FROM exam_rewards").fetchall()],
                        "redemptions": [dict(r) for r in db.execute("SELECT * FROM redemptions").fetchall()],
                        "extra_points": [dict(r) for r in db.execute("SELECT * FROM extra_points").fetchall()],
                        "special_events": [dict(r) for r in db.execute("SELECT * FROM special_events").fetchall()],
                        "config_tasks": [dict(r) for r in db.execute("SELECT * FROM config_tasks").fetchall()],
                        "config_shop": [dict(r) for r in db.execute("SELECT * FROM config_shop").fetchall()],
                        "config_exam": [dict(r) for r in db.execute("SELECT * FROM config_exam").fetchall()],
                        "config_badges": [dict(r) for r in db.execute("SELECT * FROM config_badges").fetchall()]
                    }
                    json_str_all = json.dumps(all_data, ensure_ascii=False, indent=2, default=str)
                    st.download_button(
                        label="📥 导出全站备份 (JSON)",
                        data=json_str_all,
                        file_name=f"global_backup_{today.isoformat()}.json",
                        mime="application/json",
                        use_container_width=True
                    )
        
        st.divider()
        if st.button("退出登录"):
            del st.session_state.user
            del st.session_state.role
            st.rerun()

    # 精简模式：只显示打卡、商城、兑换，以及设置（管理员需要）
    if is_mobile_mode:
        tabs = ["打卡", "商城", "兑换"]
        if current_role == "admin": tabs.append("系统设置")
    else:
        tabs = ["打卡", "偶发", "历史与图表", "商城", "兑换", "考试", "事件", "系统设置"]
        
    tab_objs = st.tabs(tabs)
    
    # 记录当前 Tab 索引，方便下面分发
    tab_dict = {name: obj for name, obj in zip(tabs, tab_objs)}

    with tab_dict["打卡"]:
        tasks = get_tasks(db, today.weekday(), view_as)
        if not tasks:
            st.warning("今日还没有配置任务哦，请去【系统设置】里添加！")
        else:
            thresholds = get_thresholds(db, view_as); thr = thresholds.get(today.weekday(), {"basic":0,"full":0})
            st.subheader(f"{today.strftime('%m月%d日')} - {WEEKDAY_CN[today.weekday()]}")
            st.caption(f"基本要求：{thr['basic']} 分 | 满分：{thr['full']} 分")
            
            existing = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (today.isoformat(), view_as)).fetchone()
            already_done = existing is not None
            done_ids = set(json.loads(existing["done_tasks"])) if existing else set()
            
            cats = {}
            for t in tasks: cats.setdefault(t["category"], []).append(t)
            selected_ids = []
            for cat, items in cats.items():
                st.markdown(f"**{html.escape(cat)}**")
                if is_mobile_mode:
                    # 手机端极端单列
                    for t in items:
                        if st.checkbox(f"{html.escape(t['name'])} ({t['points']}分)", value=(t["id"] in done_ids), key=f"cb_{today}_{view_as}_{t['id']}", disabled=already_done):
                            if not already_done: selected_ids.append(t["id"])
                else:
                    # 电脑端双列
                    cols = st.columns(2)
                    for i, t in enumerate(items):
                        with cols[i % 2]:
                            if st.checkbox(f"{html.escape(t['name'])} ({t['points']}分)", value=(t["id"] in done_ids), key=f"cb_{today}_{view_as}_{t['id']}", disabled=already_done):
                                if not already_done: selected_ids.append(t["id"])
                            
            st.divider(); c1, c2, c3 = st.columns(3)
            if already_done:
                c1.metric("基础分", f"{existing['base_score']:.1f}"); c2.metric("Bonus", f"{existing['bonus_score']:.1f}"); c3.metric("今日总分", f"{existing['total_score']:.1f}")
                st.success("今日已完成打卡，记录已锁定。")
                if st.button("撤销今日打卡（重新填写）", type="secondary", use_container_width=True):
                    db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (today.isoformat(), view_as))
                    db.commit(); recalc_all_bonus(db, view_as); settle_longterm_bonus(db, view_as); st.rerun()
            else:
                base_now = sum(t["points"] for t in tasks if t["id"] in set(selected_ids))
                lookup = {r["day"]: {"base_score": r["base_score"], "basic_thr": r.get("basic_thr"), "full_thr": r.get("full_thr")} for r in db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=?", (view_as,)).fetchall()}
                lookup[today.isoformat()] = {"base_score": base_now, "basic_thr": thr["basic"], "full_thr": thr["full"]}
                bonus, detail = compute_bonus_for_day(today, lookup, get_bonus_rules(db, view_as))
                c1.metric("基础分", f"{base_now:.1f}"); c2.metric("Bonus", f"{bonus:.1f}"); c3.metric("预计总分", f"{base_now + bonus:.1f}")
                if detail.get("tier") in TIER_CN: st.info(f"Bonus 判定：{TIER_CN[detail['tier']]}")
                
                if st.button("保存今日打卡", type="primary", use_container_width=True):
                    current_today = bj_now().date()
                    save_day(db, current_today, selected_ids, view_as); st.success("已保存！"); st.rerun()

    if "偶发" in tab_dict:
        with tab_dict["偶发"]:
            st.subheader("偶发事件加/扣分")
            with st.form("extra_point_form"):
                col1, col2, col3 = st.columns([4, 2, 2])
                e_name = col1.text_input("事件名称", placeholder="例如：高分作文...")
                e_pts = col2.number_input("分数 (可为负数)", value=1.0, step=0.5)
                if st.form_submit_button("确认提交", type="primary", use_container_width=True):
                    if e_name:
                        db.execute("INSERT INTO extra_points (owner_id, name, points, ts) VALUES (?,?,?,?)", (view_as, e_name, e_pts, bj_now().isoformat(timespec="seconds")))
                        db.commit(); st.success(f"已记录：{html.escape(e_name)} ({e_pts}分)"); st.rerun()
            st.divider()
            ex_rows = db.execute("SELECT * FROM extra_points WHERE owner_id=? ORDER BY id DESC LIMIT 20", (view_as,)).fetchall()
            if ex_rows:
                st.dataframe([{"时间": r["ts"], "事件": html.escape(r["name"]), "积分": r["points"]} for r in ex_rows], use_container_width=True, hide_index=True)
                if st.button("清空偶发记录"):
                    db.execute("DELETE FROM extra_points WHERE owner_id=?", (view_as,)); db.commit(); st.rerun()
            else: st.caption("暂无记录")

    if "历史与图表" in tab_dict:
        with tab_dict["历史与图表"]:
            st.subheader("历史与图表分析")
            makeup_cards = user_row.get("makeup_cards") or 0
            if makeup_cards > 0:
                st.markdown(f"🎫 **你有 {makeup_cards} 张补签卡，可用于补全最近 7 天内漏掉的打卡：**")
                missing_dates = []
                for i in range(1, 8):
                    past_date = today - timedelta(days=i)
                    rec = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (past_date.isoformat(), view_as)).fetchone()
                    if not rec: missing_dates.append(past_date)
                
                if missing_dates:
                    with st.form("makeup_form"):
                        sel_date = st.selectbox("选择要补签的日期", missing_dates, format_func=lambda x: x.strftime('%Y-%m-%d') + f" ({WEEKDAY_CN[x.weekday()]})")
                        st.caption("补签将使用当天的满分标准为您记录。")
                        if st.form_submit_button("使用 1 张补签卡", type="primary"):
                            t_thr = get_thresholds(db, view_as).get(sel_date.weekday(), {"basic": 8, "full": 11})
                            db.execute("UPDATE users SET makeup_cards = makeup_cards - 1 WHERE username=?", (current_user,))
                            db.execute("""
                                INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) 
                                VALUES (?, ?, '["补签"]', ?, 0, '{}', ?, ?, ?, ?)
                            """, (sel_date.isoformat(), view_as, t_thr["full"], t_thr["full"], bj_now().isoformat(), t_thr["basic"], t_thr["full"]))
                            db.commit()
                            recalc_all_bonus(db, view_as); settle_longterm_bonus(db, view_as)
                            st.success("补签成功！")
                            st.rerun()
                else:
                    st.info("最近 7 天都全勤了，太棒了，无需补签！")
            else:
                st.info("💡 提示：商城有售“补签卡”，可用于补全漏掉的打卡。")
                
            st.divider()
            time_view = st.radio("选择时间维度查看走势", ["按日查看", "按周查看", "按月查看"], horizontal=True)
            all_recs = db.execute("SELECT day, total_score FROM daily_records WHERE owner_id=? ORDER BY day ASC", (view_as,)).fetchall()
            if all_recs:
                df = pd.DataFrame([{"日期": r["day"], "总分": r["total_score"]} for r in all_recs])
                df["日期"] = pd.to_datetime(df["日期"])
                if time_view == "按日查看": df_grouped = df.copy(); x_title = "日期 (每日)"
                elif time_view == "按周查看": df_grouped = df.set_index("日期").resample('W-MON', label='left', closed='left').sum().reset_index(); x_title = "日期 (每周一)"
                else: df_grouped = df.set_index("日期").resample('MS').sum().reset_index(); x_title = "日期 (每月1日)"
                
                st.markdown(f"**{time_view}得分走势**")
                line_chart = alt.Chart(df_grouped).mark_line(point=True, color='#1f77b4').encode(
                    x=alt.X('日期:T', title=x_title, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('总分:Q', title='总分', axis=alt.Axis(labelAngle=0)),
                    tooltip=[alt.Tooltip('日期:T', format='%Y-%m-%d'), '总分:Q']
                ).interactive()
                st.altair_chart(line_chart, use_container_width=True)
                
                st.markdown(f"**{time_view}得分柱状图**")
                bar_chart = alt.Chart(df_grouped).mark_bar().encode(
                    x=alt.X('日期:T', title=x_title, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('总分:Q', title='总分', axis=alt.Axis(labelAngle=0)),
                    color=alt.Color('总分:Q', scale=alt.Scale(scheme='greens'), legend=None),
                    tooltip=[alt.Tooltip('日期:T', format='%Y-%m-%d'), '总分:Q']
                )
                st.altair_chart(bar_chart, use_container_width=True)
            else:
                st.info("暂无打卡数据，快去打卡吧！")
                
            st.divider()
            st.subheader("历史打卡详情")
            days = [r["day"] for r in db.execute("SELECT day FROM daily_records WHERE owner_id=? ORDER BY day DESC", (view_as,)).fetchall()]
            if days:
                sel = st.selectbox("选择日期", days)
                row = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (sel, view_as)).fetchone()
                st.write(f"**总分: {row['total_score']:.1f}** (基础 {row['base_score']:.1f} + Bonus {row['bonus_score']:.1f})")
                done = json.loads(row["done_tasks"])
                st.write("完成项：", ", ".join([html.escape(t["name"]) for t in get_tasks(db, date.fromisoformat(sel).weekday(), view_as) if t["id"] in done]) or "无")
                st.caption(f"当时判定标准：基本 {row.get('basic_thr')} 分 / 满分 {row.get('full_thr')} 分")
            else: st.info("暂无记录")

    with tab_dict["商城"]:
        st.subheader("商城")
        shop_items = get_shop(db, view_as)
        if not shop_items:
            st.warning("商城还是空的哦，请去【系统设置】里添加奖励！")
        else:
            bal = get_balance(db, view_as)
            for name, cost in shop_items:
                c1, c2, c3 = st.columns([5, 2, 2])
                c1.write(f"**{html.escape(name)}**"); c2.write(f"`{cost} 分`")
                if c3.button("兑换", key=f"buy_{view_as}_{name}", disabled=(bal["balance"] < cost)):
                    if name == "补签卡":
                        db.execute("UPDATE users SET makeup_cards = makeup_cards + 1 WHERE username=?", (current_user,))
                        db.execute("INSERT INTO redemptions (owner_id, item, cost, ts) VALUES (?,?,?,?)", (view_as, name, cost, bj_now().isoformat()))
                        db.commit(); st.success("兑换成功！获得 1 张补签卡。"); st.rerun()
                    else:
                        db.execute("INSERT INTO redemptions (owner_id, item, cost, ts) VALUES (?,?,?,?)", (view_as, name, cost, bj_now().isoformat()))
                        db.commit(); st.success("兑换成功！"); st.rerun()

    with tab_dict["兑换"]:
        st.subheader("兑换历史")
        rows = db.execute("SELECT * FROM redemptions WHERE owner_id=? ORDER BY id DESC", (view_as,)).fetchall()
        if rows: st.dataframe([{"时间": r["ts"], "奖励": html.escape(r["item"]), "消耗": r["cost"]} for r in rows], use_container_width=True)
        else: st.info("暂无")

    if "考试" in tab_dict:
        with tab_dict["考试"]:
            st.subheader("考试专项")
            exam_config, _ = get_exam_config(db, view_as)
            if not exam_config:
                st.warning("还没有设置考试科目哦，请去【系统设置】里添加！")
            else:
                scores = {}; ranks = {}
                subjects_list = list(exam_config.keys())
                for i in range(0, len(subjects_list), 3):
                    cols = st.columns(3)
                    for j in range(3):
                        if i + j < len(subjects_list):
                            sub = subjects_list[i + j]; cfg = exam_config[sub]
                            with cols[j]:
                                if cfg["type"] == "score": scores[sub] = st.number_input(f"{html.escape(sub)} (目标{cfg['target']})", value=float(cfg['target']), key=f"ex_{view_as}_{sub}")
                                else: 
                                    target_idx = GRADES.index(cfg['target']) if cfg['target'] in GRADES else 0
                                    scores[sub] = st.selectbox(f"{html.escape(sub)} (目标{cfg['target']})", GRADES, index=target_idx, key=f"ex_sel_{view_as}_{sub}")
                st.write("**语数外排名前百分之多少（填100不参与）**")
                c1, c2, c3 = st.columns(3)
                ranks["语文"] = c1.number_input("语文", 0.0, 100.0, 100.0, key=f"rk_cn_{view_as}")
                ranks["数学"] = c2.number_input("数学", 0.0, 100.0, 100.0, key=f"rk_ma_{view_as}")
                ranks["英语"] = c3.number_input("英语", 0.0, 100.0, 100.0, key=f"rk_en_{view_as}")

                total_pts, lines, hit_count = calc_exam_bonus(db, scores, ranks, view_as)
                st.divider()
                st.markdown(f"### 预计获得：**{total_pts:.1f}** 分（达成 {hit_count} 门）")
                for ln in lines: st.write(ln)
                if st.button("保存本次成绩", type="primary"):
                    detail_text = f"达成 {hit_count} 门 | " + "/".join([f"{k}:{v}" for k,v in scores.items()])
                    db.execute("INSERT INTO exam_rewards (owner_id, detail, points, ts) VALUES (?,?,?,?)", (view_as, detail_text, total_pts, bj_now().isoformat()))
                    db.commit(); st.success("已保存！"); st.rerun()

    if "事件" in tab_dict:
        with tab_dict["事件"]:
            st.subheader("特殊事件")
            fired = db.execute("SELECT * FROM special_events WHERE day=? AND owner_id=?", (today.isoformat(), view_as)).fetchone()
            if fired: st.info(f"今天已经触发过啦：{html.escape(fired['note'])} +{fired['points']}分")
            else:
                if st.button("摇一摇", use_container_width=True):
                    roll = random.random()
                    pts = random.randint(1, 2) if roll < 0.4 else random.randint(3, 5) if roll < 0.8 else random.randint(6, 8) if roll < 0.95 else random.randint(10, 15)
                    db.execute("INSERT INTO special_events (day, owner_id, points, note, ts) VALUES (?,?,?,?,?)", (today.isoformat(), view_as, pts, "积分暴击", bj_now().isoformat()))
                    db.commit(); st.balloons(); st.success(f"获得 {pts} 积分！"); st.rerun()

    if "系统设置" in tab_dict:
        with tab_dict["系统设置"]:
            st.subheader("系统设置")
            if current_role == "admin":
                st.info(f"当前正在配置的用户：**{html.escape(view_as)}** （你可以在左侧边栏切换你要修改谁的数据）")
            else:
                st.info(f"当前正在配置你的专属设置。")

            st.markdown("### 1. 修改每日任务 (若为空白可在此添加)")
            sel_wd = st.selectbox("选择要修改的星期", range(7), format_func=lambda x: WEEKDAY_CN[x])
            tasks_df = db.execute("SELECT * FROM config_tasks WHERE weekday=? AND owner_id=?", (sel_wd, view_as)).fetchall()
            edited_tasks = st.data_editor([dict(t) for t in tasks_df], column_config={"id": st.column_config.TextColumn("任务ID", required=True), "weekday": None, "owner_id": None, "category": st.column_config.TextColumn("分类"), "name": st.column_config.TextColumn("任务名称", required=True), "points": st.column_config.NumberColumn("分数", min_value=0.0, step=0.5)}, num_rows="dynamic", use_container_width=True, key=f"edit_task_{view_as}_{sel_wd}")
            if st.button("保存任务修改"):
                db.execute("DELETE FROM config_tasks WHERE weekday=? AND owner_id=?", (sel_wd, view_as))
                for t in edited_tasks:
                    if t.get("id") and t.get("name"): db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (t["id"], sel_wd, view_as, t["category"], t["name"], t["points"]))
                db.commit(); st.success("任务已更新！"); st.rerun()

            st.divider()
            st.markdown("### 2. 修改商城奖励 (若为空白可在此添加)")
            shop_df = db.execute("SELECT id, name, cost FROM config_shop WHERE owner_id=?", (view_as,)).fetchall()
            edited_shop = st.data_editor([dict(s) for s in shop_df], column_config={"id": None, "name": st.column_config.TextColumn("奖励名称", required=True), "cost": st.column_config.NumberColumn("所需积分", min_value=0.0, step=1.0)}, num_rows="dynamic", use_container_width=True, key=f"edit_shop_{view_as}")
            if st.button("保存商城修改"):
                db.execute("DELETE FROM config_shop WHERE owner_id=?", (view_as,))
                for s in edited_shop:
                    if s.get("name") and s.get("cost") is not None: db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (view_as, s["name"], s["cost"]))
                db.commit(); st.success("商城已更新！"); st.rerun()

            st.divider()
            st.markdown("### 3. 修改考试科目 (若为空白可在此添加)")
            exam_config, exam_rules = get_exam_config(db, view_as)
            df_exam_data = []
            for k, v in exam_config.items():
                df_exam_data.append({"科目": k, "类型": v["type"], "目标": str(v["target"]), "分差": v.get("step", 0), "单档奖励": v["step_points"]})
            df_exam = pd.DataFrame(df_exam_data)
            if df_exam.empty: df_exam = pd.DataFrame(columns=["科目", "类型", "目标", "分差", "单档奖励"])

            edited_exam = st.data_editor(
                df_exam,
                column_config={
                    "科目": st.column_config.TextColumn("科目", required=True),
                    "类型": st.column_config.SelectboxColumn("类型", options=["score", "grade"], required=True, help="score=按分数，grade=按等级"),
                    "目标": st.column_config.TextColumn("目标", required=True, help="填数字(如105) 或 等级(如A+)"),
                    "分差": st.column_config.NumberColumn("分差", min_value=0.0, step=1.0, help="仅分数模式有效"),
                    "单档奖励": st.column_config.NumberColumn("单档奖励", min_value=0.0, step=0.5)
                },
                num_rows="dynamic", use_container_width=True, key=f"edit_exam_{view_as}"
            )
            
            if st.button("保存考试科目修改"):
                db.execute("DELETE FROM config_exam WHERE owner_id=?", (view_as,))
                has_error = False
                for _, row in edited_exam.iterrows():
                    if pd.notna(row["科目"]) and row["科目"]:
                        sub = row["科目"]; e_type = str(row["类型"]).strip().lower(); e_target = str(row["目标"]).strip()
                        if e_type not in ["score", "grade"]: st.error(f"科目 {sub} 类型错误"); has_error = True; break
                        if e_type == "score":
                            try: e_target_val = float(e_target)
                            except ValueError: st.error(f"科目 {sub} 目标必须是数字"); has_error = True; break
                            cfg = {"type": "score", "target": e_target_val, "step": float(row["分差"] or 0), "step_points": float(row["单档奖励"] or 0)}
                        else:
                            if e_target not in GRADES: st.error(f"科目 {sub} 目标必须在 11 档内"); has_error = True; break
                            cfg = {"type": "grade", "target": e_target, "step_points": float(row["单档奖励"] or 0)}
                        db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (sub, view_as, json.dumps(cfg)))
                if has_error: db.commit()
                else: db.commit(); st.success("科目已更新！"); st.rerun()

            st.divider()
            st.markdown("### 4. 修改多科达成奖励")
            mh_df = pd.DataFrame(get_exam_multihit(db, view_as))
            if mh_df.empty: mh_df = pd.DataFrame(columns=["hit_count", "points"])
            edited_mh = st.data_editor(mh_df, column_config={"hit_count": st.column_config.NumberColumn("达成科目数", min_value=1, step=1), "points": st.column_config.NumberColumn("奖励分数", min_value=0.0, step=0.5)}, num_rows="dynamic", use_container_width=True, key=f"edit_mh_{view_as}")
            if st.button("保存多科奖励修改"):
                db.execute("DELETE FROM config_exam_multihit WHERE owner_id=?", (view_as,))
                for _, row in edited_mh.iterrows():
                    if pd.notna(row["hit_count"]) and pd.notna(row["points"]): db.execute("INSERT INTO config_exam_multihit (hit_count, owner_id, points) VALUES (?,?,?)", (int(row["hit_count"]), view_as, float(row["points"])))
                db.commit(); st.success("多科奖励已更新！"); st.rerun()

            st.divider()
            st.markdown("### 5. 修改阈值与 Bonus 规则 (老数据不受影响)")
            thresholds = get_thresholds(db, view_as); bonus_rules = get_bonus_rules(db, view_as)
            with st.form(f"bonus_form_{view_as}"):
                t_cols = st.columns(7); t_inputs = {}
                for i in range(7):
                    with t_cols[i]:
                        st.markdown(f"**{WEEKDAY_CN[i]}**")
                        t_inputs[i] = {"basic": st.number_input("基本", value=float(thresholds.get(i, {"basic":0})["basic"]), key=f"th_b_{view_as}_{i}"), "full": st.number_input("满分", value=float(thresholds.get(i, {"full":0})["full"]), key=f"th_f_{view_as}_{i}")}
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

                if st.form_submit_button("保存新规则 (即刻生效)", type="primary", use_container_width=True):
                    for i in range(7): 
                        db.execute("DELETE FROM config_thresholds WHERE weekday=? AND owner_id=?", (i, view_as))
                        db.execute("INSERT INTO config_thresholds (weekday, owner_id, basic, \"full\") VALUES (?,?,?,?)", (i, view_as, t_inputs[i]["basic"], t_inputs[i]["full"]))
                    
                    new_bonus = {
                        "weekday": {"single": {"points": wd_single, "full_points": wd_single_full}, "streak2": {"points": wd_2, "full_points": wd_2_full}, "streak4": {"points": wd_4, "full_points": wd_4_full}}, 
                        "weekend": {"single": {"points": we_single, "full_points": we_single_full}}, 
                        "longterm": {
                            "week_basic": lt_wb, "week_full": lt_wf, "month_basic": lt_mb, "month_full": lt_mf,
                            "week_flex_perfect_deduct": flex_p, "week_flex_basic_deduct": flex_b
                        }
                    }
                    db.execute("DELETE FROM config_bonus_rules WHERE owner_id=?", (view_as,))
                    db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (view_as, json.dumps(new_bonus)))
                    db.commit(); st.success("✅ 新标准已启用！未来打卡生效。"); st.rerun()

            st.divider()
            st.markdown("### 6. 全局徽章配置与 AI 生成 (仅管理员可操作)")
            if current_role != "admin":
                st.info("全局徽章由管理员统一配置，普通用户无法修改。")
            else:
                st.write("你可以为全站用户添加通用的成就徽章。输入名称后，系统会调用 AI 自动绘制符合含义的扁平化图标。")
                with st.form("add_badge_form"):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    b_name = c1.text_input("徽章名称 (如：早起鸟、自律达人)")
                    b_type = c2.selectbox("达成条件", options=["days", "points", "perfect", "exam_hits"], format_func=lambda x: {"days": "累计打卡天数", "points": "累计赚取积分", "perfect": "完美周/月次数", "exam_hits": "单次考试达成科目数"}.get(x, x))
                    b_val = c3.number_input("达成数值", min_value=1.0, step=1.0)
                    
                    if st.form_submit_button("✨ AI 生成并添加全局徽章", type="primary"):
                        if b_name:
                            seed = random.randint(1, 99999)
                            prompt = f"Minimalist flat vector icon for '{b_name}', clean simple design, ui app icon, no text, white background, not exaggerated."
                            encoded_prompt = urllib.parse.quote(prompt)
                            icon_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=256&height=256&nologo=true&seed={seed}"
                            db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)", (b_name, b_type, b_val, icon_url))
                            db.commit()
                            st.success(f"全局徽章「{html.escape(b_name)}」已生成并配置！")
                            st.rerun()
                
                st.markdown("**当前全局已配置的徽章：**")
                existing_badges = get_badge_configs(db)
                if existing_badges:
                    for b in existing_badges:
                        c1, c2, c3, c4 = st.columns([2, 3, 3, 2])
                        with c1: st.markdown(f'<img src="{b["icon_url"]}" width="50" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'">', unsafe_allow_html=True)
                        c2.write(f"**{html.escape(b['name'])}**")
                        type_cn = {"days": "打卡天数", "points": "累计积分", "perfect": "完美次数", "exam_hits": "单次考试达科目数"}.get(b["cond_type"], b["cond_type"])
                        c3.write(f"条件：{type_cn} ≥ {b['cond_val']}")
                        if c4.button("删除", key=f"del_badge_{b['id']}"):
                            db.execute("DELETE FROM config_badges WHERE id=?", (b["id"],))
                            db.commit(); st.rerun()
                else: st.caption("暂无全局自定义徽章。")

            if current_role == "admin":
                st.divider()
                st.markdown("### 7. 用户管理与权限控制")
                for u in all_users_data:
                    uname = u["username"]; urole = u["role"]
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
                    c1.write(f"用户：**{html.escape(uname)}**")
                    
                    if urole == "admin":
                        c2.success("🟢 管理员")
                        if uname != current_user: 
                            if c3.button("降级为普通用户", key=f"demote_{uname}"):
                                db.execute("UPDATE users SET role='user' WHERE username=?", (uname,))
                                db.commit(); st.rerun()
                    else:
                        c2.info("⚪ 普通用户")
                        if c3.button("提升为管理员", key=f"promote_{uname}"):
                            db.execute("UPDATE users SET role='admin' WHERE username=?", (uname,))
                            db.commit(); st.rerun()
                    
                    if c4.button("重置密码", key=f"reset_{uname}"):
                        db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd("123456"), uname))
                        db.commit(); st.success(f"用户 {uname} 的密码已重置为 123456")
                    
                    if uname != current_user:
                        if c5.button("删除账号", key=f"del_{uname}"):
                            for tbl in ["users", "daily_records", "period_bonus", "redemptions", "exam_rewards", "special_events", "extra_points", "config_tasks", "config_shop", "config_exam", "config_exam_rules", "config_thresholds", "config_bonus_rules", "config_exam_multihit"]:
                                col = "username" if tbl == "users" else "owner_id"
                                db.execute(f"DELETE FROM {tbl} WHERE {col}=?", (uname,))
                            db.commit(); st.success(f"用户 {uname} 已彻底删除"); st.rerun()

if __name__ == "__main__":
    main()
