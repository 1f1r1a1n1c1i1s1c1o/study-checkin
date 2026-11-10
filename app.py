#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, random, os, hashlib, urllib.parse, re, html, requests, secrets, base64, uuid, hmac
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
import bcrypt
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import urllib.request

# 【修复 1】: 本地无 secrets 时兜底
try:
    IS_CLOUD = "DATABASE_URL" in st.secrets
except Exception:
    IS_CLOUD = False

if IS_CLOUD:
    import psycopg2, psycopg2.extras
else:
    import sqlite3
    class DummyPsycopg2:
        class OperationalError(Exception): pass
    psycopg2 = DummyPsycopg2()

# ================= 多语言 =================
LANG_PACKS = {
    "zh": {
        "language": "语言 / Language",
        "app_title": "学习打卡系统",
        "login": "登录", "register": "注册", "find_pwd": "找回密码",
        "username": "用户名", "password": "密码",
        "set_username": "设置用户名", "set_pwd": "设置密码", "confirm_pwd": "确认密码",
        "security_q": "密保问题 (如：我的幸运数字？)", "security_a": "密保答案",
        "login_btn": "登录", "register_btn": "注册", "reset_btn": "确认重置密码",
        "wrong_creds": "用户名或密码错误", "fill_all": "请填写所有字段（含密保）",
        "pwd_mismatch": "密码不一致", "reserved_name": "该用户名为系统保留，请换一个",
        "user_exists": "用户名已存在", "register_ok": "注册成功！已为您分配 3 天内测体验。请去登录。",
        "no_security_q": "该账户未设置密保问题，请联系管理员重置密码。",
        "user_not_exist": "该用户名不存在", "reset_ok": "密码重置成功！请去登录。",
        "wrong_answer": "密保答案错误！",
        "reset_intro": "输入用户名，验证密保问题后重设密码。",
        "input_username": "请输入你的用户名", "new_password": "新密码",
        "sidebar_title": "学习打卡", "mobile_mode": "📱 手机精简模式",
        "current_identity": "当前身份", "local_time": "当地时间",
        "makeup_cards": "🎫 补签卡", "available_points": "当前可用积分",
        "timer": "专注计时器 (番茄钟)", "badges": "我的成就徽章",
        "no_badges": "暂无徽章。", "points_detail": "积分明细",
        "checkin_pts": "打卡", "longterm_pts": "长期", "exam_pts": "考试",
        "extra_pts": "偶发", "special_pts": "特殊", "spent_pts": "消耗",
        "account_settings": "账号与数据设置", "timezone": "时区设置",
        "select_timezone": "所在地区/时区", "custom_tz": "自定义时区",
        "tz_offset": "输入 UTC 偏移小时数", "save_tz": "保存时区设置",
        "new_username": "新用户名", "leave_blank": "留空则不修改",
        "change_username": "确认修改用户名", "change_pwd": "确认修改密码",
        "change_security": "修改密保", "new_security_q": "新密保问题",
        "new_security_a": "新密保答案", "save_security": "保存密保",
        "webhook": "防遗忘提醒 Webhook", "save_webhook": "保存 Webhook",
        "export_data": "📥 导出我的数据 (JSON)", "logout_btn": "退出登录",
        "select_child": "选择你要管理/查看的孩子",
        "admin_select_target": "管理员特权：选择操作对象",
        "penetrate": "穿透管理", "no_children_bound": "暂无绑定的孩子，请联系管理员绑定。",
        "role_admin": "管理员", "role_host": "家长", "role_user": "孩子", "role_solo": "独立用户",
        "remaining": "剩余", "permanent": "永久", "expired": "已过期",
        "tab_checkin": "打卡", "tab_extra": "偶发", "tab_history": "历史与图表",
        "tab_shop": "商城", "tab_redeem": "兑换", "tab_exam": "考试",
        "tab_event": "事件", "tab_settings": "系统设置", "tab_leaderboard": "排行榜",
        "no_tasks_today": "今日还没有配置任务哦，请去【系统设置】里添加！",
        "basic_req": "基本要求", "full_req": "满分",
        "today_done": "今日已完成打卡，记录已锁定。",
        "undo_checkin": "撤销今日打卡（重新填写）",
        "base_score": "基础分", "today_total": "今日总分",
        "est_total": "预计总分", "save_checkin": "保存今日打卡",
        "saved": "已保存！", "bonus": "Bonus",
        "shop_empty": "商城空！", "redeem_btn": "兑换",
        "confirm_deduct": "确认扣除", "points_insufficient": "积分不足，兑换失败。",
        "redeem_ok": "兑换成功！", "redeem_history": "兑换历史", "none_yet": "暂无",
        "leaderboard_title": "🏆 兄弟姐妹排行榜",
        "period": "周期", "daily_board": "日榜", "monthly_board": "月榜", "total_board": "总榜",
        "score_col": "分", "no_rank_data": "暂无排行数据",
        "you": "(你)", "only_you": "暂无其他兄弟姐妹参与排行，邀请他们一起来比拼吧！",
    },
    "en": {
        "language": "Language / 语言",
        "app_title": "Study Check-in",
        "login": "Login", "register": "Register", "find_pwd": "Reset Password",
        "username": "Username", "password": "Password",
        "set_username": "Username", "set_pwd": "Password", "confirm_pwd": "Confirm Password",
        "security_q": "Security Question (e.g. My lucky number?)", "security_a": "Security Answer",
        "login_btn": "Sign In", "register_btn": "Sign Up", "reset_btn": "Reset Password",
        "wrong_creds": "Incorrect username or password", "fill_all": "Please fill in all fields (including security question)",
        "pwd_mismatch": "Passwords do not match", "reserved_name": "This username is reserved. Please choose another.",
        "user_exists": "Username already exists", "register_ok": "Registered! You have a 3-day trial. Please log in.",
        "no_security_q": "This account has no security question. Please contact the admin.",
        "user_not_exist": "Username does not exist", "reset_ok": "Password reset successfully! Please log in.",
        "wrong_answer": "Security answer is incorrect!",
        "reset_intro": "Enter username, verify security question, then set a new password.",
        "input_username": "Enter your username", "new_password": "New Password",
        "sidebar_title": "Study Check-in", "mobile_mode": "📱 Mobile Mode",
        "current_identity": "Signed in as", "local_time": "Local time",
        "makeup_cards": "🎫 Makeup Cards", "available_points": "Available Points",
        "timer": "Focus Timer (Pomodoro)", "badges": "My Badges",
        "no_badges": "No badges yet.", "points_detail": "Points Detail",
        "checkin_pts": "Check-in", "longterm_pts": "Long-term", "exam_pts": "Exam",
        "extra_pts": "Extra", "special_pts": "Special", "spent_pts": "Spent",
        "account_settings": "Account & Data", "timezone": "Timezone",
        "select_timezone": "Region / Timezone", "custom_tz": "Custom",
        "tz_offset": "Enter UTC offset (hours)", "save_tz": "Save Timezone",
        "new_username": "New Username", "leave_blank": "Leave blank to keep current",
        "change_username": "Change Username", "change_pwd": "Change Password",
        "change_security": "Change Security", "new_security_q": "New Security Question",
        "new_security_a": "New Security Answer", "save_security": "Save Security",
        "webhook": "Reminder Webhook", "save_webhook": "Save Webhook",
        "export_data": "📥 Export My Data (JSON)", "logout_btn": "Log Out",
        "select_child": "Select a child to manage/view",
        "admin_select_target": "Admin: Select Target User",
        "penetrate": "Drill-down", "no_children_bound": "No child bound. Please contact admin.",
        "role_admin": "Admin", "role_host": "Parent", "role_user": "Child", "role_solo": "Solo",
        "remaining": "Remaining", "permanent": "Lifetime", "expired": "Expired",
        "tab_checkin": "Check-in", "tab_extra": "Extra", "tab_history": "History",
        "tab_shop": "Shop", "tab_redeem": "Redeem", "tab_exam": "Exam",
        "tab_event": "Event", "tab_settings": "Settings", "tab_leaderboard": "Leaderboard",
        "no_tasks_today": "No tasks configured for today. Please add them in Settings.",
        "basic_req": "Basic requirement", "full_req": "Full mark",
        "today_done": "Today's check-in is done and locked.",
        "undo_checkin": "Undo today's check-in (re-enter)",
        "base_score": "Base Score", "today_total": "Today Total",
        "est_total": "Estimated Total", "save_checkin": "Save Check-in",
        "saved": "Saved!", "bonus": "Bonus",
        "shop_empty": "Shop is empty.", "redeem_btn": "Redeem",
        "confirm_deduct": "Confirm Deduct", "points_insufficient": "Not enough points.",
        "redeem_ok": "Redeemed!", "redeem_history": "Redemption History", "none_yet": "None",
        "leaderboard_title": "🏆 Sibling Leaderboard",
        "period": "Period", "daily_board": "Daily", "monthly_board": "Monthly", "total_board": "All-time",
        "score_col": "pts", "no_rank_data": "No leaderboard data yet",
        "you": "(you)", "only_you": "No other siblings yet. Invite them to compete!",
    },
}

def detect_system_language():
    try:
        accept = st.context.headers.get("Accept-Language", "") or ""
        first = accept.split(",")[0].strip().lower()
        if first.startswith("zh"): return "zh"
        if first.startswith("en"): return "en"
    except Exception:
        pass
    return "zh"

def get_lang():
    if "lang" not in st.session_state:
        st.session_state["lang"] = detect_system_language()
    return st.session_state["lang"]

def t(key):
    pack = LANG_PACKS.get(get_lang(), LANG_PACKS["zh"])
    return pack.get(key, LANG_PACKS["zh"].get(key, key))

def render_language_selector(key_suffix=""):
    options = list(LANG_PACKS.keys())
    labels = {"zh": "中文", "en": "English"}
    cur = get_lang()
    idx = options.index(cur) if cur in options else 0
    choice = st.selectbox(t("language"), options, index=idx,
                          format_func=lambda x: labels[x], key=f"lang_sel_{key_suffix}")
    if choice != st.session_state.get("lang"):
        st.session_state["lang"] = choice
        return True
    return False

# ================= 密码与安全区 =================
SECRET_KEY = "study-checkin-super-secret-salt-v1"

def generate_auth_token(username: str, pwd_hash: str) -> str:
    return hmac.new((SECRET_KEY + pwd_hash).encode(), username.encode(), hashlib.sha256).hexdigest()

def verify_auth_token(username: str, token: str, pwd_hash: str) -> bool:
    if not username or not token or not pwd_hash:
        return False
    return hmac.compare_digest(generate_auth_token(username, pwd_hash), token)

def hash_pwd_sha256(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def hash_pwd_bcrypt(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pwd_bcrypt(pwd: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False

# ================= 兼容性封装与运维工具 =================
def _stretch(kwargs):
    try:
        import inspect
        sig = inspect.signature(st.button)
        if "width" in sig.parameters:
            kwargs["width"] = "stretch"
        else:
            kwargs["use_container_width"] = True
    except Exception:
        kwargs["use_container_width"] = True
    return kwargs

def _submit(label, **kwargs):
    return st.form_submit_button(label, **_stretch(kwargs))

def _log_db_error(op_type, err_msg):
    try:
        log_file = DB_PATH.parent / "error.log"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {op_type} | {err_msg}\n")
    except Exception:
        pass

def _backup_sqlite():
    if IS_CLOUD: return
    if not DB_PATH.exists(): return
    backup_dir = DB_PATH.parent / "backup"
    backup_dir.mkdir(exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    backup_file = backup_dir / f"study_points_{today_str}.db"
    if not backup_file.exists():
        try:
            import shutil
            shutil.copy2(DB_PATH, backup_file)
            files = sorted(backup_dir.glob("study_points_*.db"))
            if len(files) > 7:
                for f in files[:-7]:
                    try: f.unlink()
                    except: pass
        except Exception as e:
            print(f"备份失败: {e}")

# ================= 时间引擎 =================
TIMEZONES = {
    "北京时间 (UTC+8)": 8.0, "东京时间 (UTC+9)": 9.0, "悉尼时间 (UTC+10)": 10.0,
    "伦敦时间 (UTC+0)": 0.0, "巴黎时间 (UTC+1)": 1.0, "纽约时间 (UTC-5)": -5.0,
    "洛杉矶时间 (UTC-8)": -8.0, "自定义时区": None
}

def get_user_now(offset_hours: float) -> datetime:
    try: oh = float(offset_hours)
    except: oh = 8.0
    oh = max(-12.0, min(14.0, oh))
    tz = timezone(timedelta(hours=oh))
    return datetime.now(tz)

def get_user_today(offset_hours: float) -> date:
    return get_user_now(offset_hours).date()

def get_remaining_days(exp_str):
    if not exp_str: return -1
    if str(exp_str).startswith("2099"): return 9999
    try:
        exp_dt = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
        delta = exp_dt - datetime.now()
        if delta.days < 0: return -1
        return max(0, delta.days + (1 if delta.seconds > 0 else 0))
    except:
        return -1

def setup_chinese_font():
    font_path = "SimHei.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf"
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            print(f"字体下载失败: {e}")
            return None
    try:
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.sans-serif'] = [prop.get_name()]
        plt.rcParams['axes.unicode_minus'] = False
        return prop
    except Exception:
        return None

DB_PATH = Path(__file__).resolve().parent / "study_points.db"
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
DEFAULT_ICON_BASE64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRkZEMzAwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDJMMTUuMDkgOC4yNkwyMiA5LjI3TDE3IDE0LjE0TDE4LjE4IDIxLjAyTDEyIDE3LjU3TDUuODIgMjEuMDJMOSAxNC4xNEwyIDkuMjdMOC45MSA4LjI2TDEyIDJ6Ij48L3BhdGg+PC9zdmc+"

DEFAULT_BONUS_RULES = {
    "weekday": {"single": {"points": 1.0, "full_points": 2.0}, "streak2": {"points": 1.5, "full_points": 3.0}, "streak4": {"points": 2.5, "full_points": 5.0}},
    "weekend": {"single": {"points": 1.0, "full_points": 2.0}},
    "longterm": {"week_basic": 3.5, "week_full": 7.0, "week_flex_perfect_deduct": 1.0, "week_flex_basic_deduct": 0.5, "month_basic": 8.0, "month_full": 20.0}
}
DEFAULT_EXAM_RULES = {"hit_points": 1.0, "rank_top_percent": 75.0, "rank_base_points": 1.0, "rank_step_percent": 5.0, "rank_step_points": 1.5}
TIER_CN = {"single": "单日达标", "streak2": "连续2日达标", "streak4": "连续4日达标", "weekend_single": "周末单日达标"}
GRADES = ["A+", "A", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E"]

# ================= 数据库封装 =================
class SqliteCursor:
    def __init__(self, cur): self._cur = cur
    @property
    def description(self): return self._cur.description
    @property
    def rowcount(self): return self._cur.rowcount
    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None
    def fetchall(self): return [dict(r) for r in self._cur.fetchall()]
    def __iter__(self): return (dict(r) for r in self._cur)

class DBWrapper:
    def __init__(self, conn, is_cloud):
        self.conn = conn
        self.is_cloud = is_cloud

    def begin(self):
        if self.is_cloud: self.conn.autocommit = False
        else: self.conn.execute("BEGIN")
        
    def rollback(self):
        try: self.conn.rollback()
        except: pass

    def end(self):
        if self.is_cloud: self.conn.autocommit = True

    def execute(self, query, params=()):
        try:
            if self.is_cloud:
                if self.conn.closed != 0: raise psycopg2.OperationalError("Connection closed")
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
        except Exception as e:
            if self.is_cloud: st.cache_resource.clear()
            _log_db_error("execute", str(e))
            raise RuntimeError(f"数据库操作失败，请刷新重试。({str(e)})")
    
    def executemany(self, query, params_list):
        try:
            if self.is_cloud:
                if self.conn.closed != 0: raise psycopg2.OperationalError("Connection closed")
                query = query.replace("?", "%s")
                cur = self.conn.cursor()
                cur.executemany(query, params_list)
                return cur
            else:
                return self.conn.executemany(query, params_list)
        except Exception as e:
            if self.is_cloud: st.cache_resource.clear()
            _log_db_error("executemany", str(e))
            raise RuntimeError(f"数据库批量操作失败。({str(e)})")

    def commit(self): self.conn.commit()

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
        _backup_sqlite()
        return db

def init_db(db):
    if db.is_cloud:
        try:
            db.execute("ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS daily_records_pkey CASCADE")
            db.execute("ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS daily_records_day_key CASCADE")
            db.execute("ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS daily_records_day_owner_id_key CASCADE")
            db.execute("DROP INDEX IF EXISTS daily_records_pkey CASCADE")
            db.execute("DROP INDEX IF EXISTS daily_records_day_key CASCADE")
            db.execute("DROP INDEX IF EXISTS daily_records_day_owner_id_key CASCADE")
            db.execute("ALTER TABLE config_thresholds DROP CONSTRAINT IF EXISTS config_thresholds_pkey CASCADE")
            db.execute("DROP INDEX IF EXISTS config_thresholds_pkey CASCADE")
            db.execute("ALTER TABLE config_exam DROP CONSTRAINT IF EXISTS config_exam_pkey CASCADE")
            db.execute("ALTER TABLE config_exam DROP CONSTRAINT IF EXISTS config_exam_subject_key CASCADE")
            db.execute("DROP INDEX IF EXISTS config_exam_pkey CASCADE")
            db.execute("DROP INDEX IF EXISTS config_exam_subject_key CASCADE")
            db.execute("ALTER TABLE config_exam_multihit DROP CONSTRAINT IF EXISTS config_exam_multihit_pkey CASCADE")
            db.execute("DROP INDEX IF EXISTS config_exam_multihit_pkey CASCADE")
            db.execute("ALTER TABLE config_bonus_rules DROP CONSTRAINT IF EXISTS config_bonus_rules_pkey CASCADE")
            db.execute("DROP INDEX IF EXISTS config_bonus_rules_pkey CASCADE")
            db.execute("ALTER TABLE config_tasks DROP CONSTRAINT IF EXISTS config_tasks_pkey CASCADE")
            db.execute("ALTER TABLE config_shop DROP CONSTRAINT IF EXISTS config_shop_pkey CASCADE")
            db.execute("ALTER TABLE config_badges DROP CONSTRAINT IF EXISTS config_badges_pkey CASCADE")
            db.execute("ALTER TABLE special_events DROP CONSTRAINT IF EXISTS special_events_pkey CASCADE")
            db.execute("ALTER TABLE extra_points DROP CONSTRAINT IF EXISTS extra_points_pkey CASCADE")
            db.execute("ALTER TABLE redemptions DROP CONSTRAINT IF EXISTS redemptions_pkey CASCADE")
            res = db.execute("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'daily_records' AND constraint_type = 'UNIQUE'").fetchall()
            for row in res:
                db.execute(f"ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS {row['constraint_name']} CASCADE")
            try:
                db.execute("CREATE SEQUENCE IF NOT EXISTS config_bonus_rules_id_seq")
                db.execute("ALTER TABLE config_bonus_rules ALTER COLUMN id SET DEFAULT nextval('config_bonus_rules_id_seq')")
            except: pass
            db.commit()
        except Exception as e: print(f"清理历史约束失败: {e}")

    tables_common = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT DEFAULT 'user', security_question TEXT, security_answer TEXT, webhook_url TEXT, makeup_cards INTEGER DEFAULT 0, timezone_offset REAL DEFAULT 8.0, host_id TEXT, plan_expires_at TEXT, language TEXT)",
        "CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, days INTEGER, is_used INTEGER DEFAULT 0, used_by TEXT, created_at TEXT)",
        "CREATE TABLE IF NOT EXISTS daily_records (day TEXT, owner_id TEXT, done_tasks TEXT, base_score REAL, bonus_score REAL, bonus_detail TEXT, total_score REAL, updated_at TEXT, basic_thr REAL, full_thr REAL)",
        "CREATE TABLE IF NOT EXISTS period_bonus (period_key TEXT, owner_id TEXT, kind TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS config_tasks (id TEXT, weekday INTEGER, owner_id TEXT, category TEXT, name TEXT, points REAL)",
        "CREATE TABLE IF NOT EXISTS config_exam (subject TEXT, owner_id TEXT, config_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_exam_rules (owner_id TEXT PRIMARY KEY, config_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_thresholds (weekday INTEGER, owner_id TEXT, basic REAL, \"full\" REAL)",
        "CREATE TABLE IF NOT EXISTS config_bonus_rules (owner_id TEXT PRIMARY KEY, rules_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_exam_multihit (hit_count INTEGER, owner_id TEXT, points REAL)",
    ]
    for t_sql in tables_common:
        try: db.execute(t_sql)
        except: pass

    pk_expr = "SERIAL PRIMARY KEY" if db.is_cloud else "INTEGER PRIMARY KEY AUTOINCREMENT"
    tables_pk_cols = [
        ("redemptions", "id {pk}, owner_id TEXT, item TEXT, cost REAL, ts TEXT"),
        ("exam_rewards", "id {pk}, owner_id TEXT, detail TEXT, points REAL, ts TEXT"),
        ("special_events", "id {pk}, day TEXT, owner_id TEXT, points REAL, note TEXT, ts TEXT"),
        ("extra_points", "id {pk}, owner_id TEXT, name TEXT, points REAL, ts TEXT"),
        ("config_shop", "id {pk}, owner_id TEXT, name TEXT, cost REAL"),
        ("config_badges", "id {pk}, owner_id TEXT DEFAULT 'system', name TEXT, cond_type TEXT, cond_val REAL, icon_url TEXT"),
    ]
    for tname, cols in tables_pk_cols:
        try: db.execute(f"CREATE TABLE IF NOT EXISTS {tname} ({cols.format(pk=pk_expr)})")
        except: pass

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_daily_records ON daily_records (owner_id, day)",
        "CREATE INDEX IF NOT EXISTS idx_period_bonus ON period_bonus (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_extra_points ON extra_points (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_exam_rewards ON exam_rewards (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_redemptions ON redemptions (owner_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_config_tasks ON config_tasks (owner_id, weekday, category, name)"
    ]
    for idx in indexes:
        try: db.execute(idx)
        except: pass
    db.commit()

    if db.is_cloud:
        for q in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS security_question TEXT", "ALTER TABLE users ADD COLUMN IF NOT EXISTS security_answer TEXT", "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'", "ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_url TEXT", "ALTER TABLE users ADD COLUMN IF NOT EXISTS makeup_cards INTEGER DEFAULT 0", "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone_offset REAL DEFAULT 8.0", "ALTER TABLE users ADD COLUMN IF NOT EXISTS host_id TEXT", "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expires_at TEXT", "ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT",
            "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS basic_thr REAL", "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS full_thr REAL",
            "ALTER TABLE period_bonus ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE exam_rewards ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE special_events ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE extra_points ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_tasks ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_shop ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_exam ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_exam_rules ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_thresholds ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_bonus_rules ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_exam_multihit ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'"
        ]:
            try: db.execute(q)
            except: pass
        db.commit()
    else:
        for q in [
            "ALTER TABLE users ADD COLUMN security_question TEXT", "ALTER TABLE users ADD COLUMN security_answer TEXT", "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'", "ALTER TABLE users ADD COLUMN webhook_url TEXT", "ALTER TABLE users ADD COLUMN makeup_cards INTEGER DEFAULT 0", "ALTER TABLE users ADD COLUMN timezone_offset REAL DEFAULT 8.0", "ALTER TABLE users ADD COLUMN host_id TEXT", "ALTER TABLE users ADD COLUMN plan_expires_at TEXT", "ALTER TABLE users ADD COLUMN language TEXT",
            "ALTER TABLE daily_records ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE daily_records ADD COLUMN basic_thr REAL", "ALTER TABLE daily_records ADD COLUMN full_thr REAL",
            "ALTER TABLE period_bonus ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE redemptions ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE exam_rewards ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE special_events ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE extra_points ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_tasks ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_shop ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_exam ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_exam_rules ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_thresholds ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_bonus_rules ADD COLUMN owner_id TEXT DEFAULT '晴'", "ALTER TABLE config_exam_multihit ADD COLUMN owner_id TEXT DEFAULT '晴'"
        ]:
            try: db.execute(q)
            except: pass
        db.commit()

    try:
        expire_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        db.execute("UPDATE users SET plan_expires_at=? WHERE plan_expires_at IS NULL AND role IN ('user', 'solo')", (expire_date,))
        db.execute("UPDATE users SET plan_expires_at='2099-12-31 23:59:59' WHERE plan_expires_at IS NULL AND role IN ('admin', 'host')")
        db.commit()
    except Exception as e:
        print(f"补发老用户试用期失败: {e}")

    try:
        user_count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        if user_count == 0:
            admin_user = os.getenv("INIT_ADMIN_USER", "admin")
            admin_pwd = os.getenv("INIT_ADMIN_PWD", "admin123")
            admin_sa = secrets.token_urlsafe(12)
            print(f"⚠️ 生成初始管理员: {admin_user} / {admin_pwd}")
            db.execute("INSERT INTO users (username, password_hash, role, security_question, security_answer, plan_expires_at) VALUES (?, ?, 'admin', ?, ?, '2099-12-31 23:59:59')",
                       (admin_user, hash_pwd_bcrypt(admin_pwd), "初始密保", hash_pwd_sha256(admin_sa.strip().lower())))
            if not db.execute("SELECT * FROM config_tasks WHERE owner_id=?", (admin_user,)).fetchone():
                init_old_admin_data(db, admin_user)
            db.commit()
    except Exception as e: print(f"初始化管理员失败: {e}")

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
                db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)", (b[0], b[1], b[2], icon_url))
        db.commit()
    except: pass

def init_old_admin_data(db, owner_id):
    try:
        db.execute("DELETE FROM config_tasks WHERE owner_id=?", (owner_id,))
        db.execute("DELETE FROM config_thresholds WHERE owner_id=?", (owner_id,))
        db.execute("DELETE FROM config_shop WHERE owner_id=?", (owner_id,))
        db.execute("DELETE FROM config_exam WHERE owner_id=?", (owner_id,))
        db.execute("DELETE FROM config_exam_rules WHERE owner_id=?", (owner_id,))
        db.execute("DELETE FROM config_bonus_rules WHERE owner_id=?", (owner_id,))
        db.commit()
    except Exception as e: print(f"清理旧配置失败: {e}")

    BASE_TASKS = [("hw_sort", "校内", "作业分类", 1.0), ("hw_done", "校内", "作业完成", 2.0)]
    DEFAULT_SHOP = [("专属夸夸", 6)]
    DEFAULT_EXAM_CONFIG = {"语文": {"type": "score", "max_score": 150, "target": 105.0, "step": 3.0, "step_points": 2.0}}
    
    for i in range(7):
        for task in BASE_TASKS:
            task_id = f"{owner_id}_{task[0]}_d{i}"
            try: db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (task_id, i, owner_id, task[1], task[2], task[3]))
            except Exception as e: print(f"插入任务失败: {e}")
        try: db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)', (i, owner_id, 8.0, 11.0))
        except Exception as e: print(f"插入阈值失败: {e}")

    for s in DEFAULT_SHOP:
        try: db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (owner_id, s[0], s[1]))
        except Exception as e: print(f"插入商城失败: {e}")
    for sub, cfg in DEFAULT_EXAM_CONFIG.items():
        try: db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (sub, owner_id, json.dumps(cfg)))
        except Exception as e: print(f"插入考试科目失败: {e}")
    
    try: db.execute("INSERT INTO config_exam_rules (owner_id, config_json) VALUES (?,?)", (owner_id, json.dumps(DEFAULT_EXAM_RULES)))
    except Exception as e: print(f"插入考试规则失败: {e}")
    try: db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (owner_id, json.dumps(DEFAULT_BONUS_RULES)))
    except Exception as e: print(f"插入加分规则失败: {e}")
    try: db.commit()
    except Exception as e: print(f"提交默认配置失败: {e}")

# ================= 用户列表相关 =================
@st.cache_data(ttl=60, show_spinner=False)
def get_all_users():
    db = get_db()
    return [{"username": r["username"], "role": r["role"], "plan_expires_at": r["plan_expires_at"]} for r in db.execute("SELECT username, role, plan_expires_at FROM users").fetchall()]

@st.cache_data(ttl=60, show_spinner=False)
def get_visible_users(current_user, current_role):
    if current_role == "admin": return [u["username"] for u in get_all_users()]
    if current_role == "host":
        db = get_db()
        rows = db.execute("SELECT username FROM users WHERE host_id=?", (current_user,)).fetchall()
        return [r["username"] for r in rows]
    return [current_user]

def _remaining_admins(db, exclude_username):
    try: return db.execute("SELECT COUNT(*) as c FROM users WHERE role='admin' AND username != ?", (exclude_username,)).fetchone()["c"]
    except: return 0

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
    if not any(i[0] == "补签卡" for i in items): items.insert(0, ("补签卡", 25.0))
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
    return [{"hit_count": r["hit_count"], "points": float(r["points"] or 0)} for r in db.execute("SELECT * FROM config_exam_multihit WHERE owner_id=? ORDER BY hit_count ASC", (oid,)).fetchall()]

@st.cache_data(ttl=3600, show_spinner=False)
def get_badge_configs():
    db = get_db()
    return [dict(r) for r in db.execute("SELECT * FROM config_badges WHERE owner_id='system' ORDER BY id ASC").fetchall()]

@st.cache_data(ttl=10, show_spinner=False)
def get_balance(oid) -> dict:
    db = get_db()
    query = """
        SELECT 'daily' as k, COALESCE(SUM(total_score), 0) as s FROM daily_records WHERE owner_id = ?
        UNION ALL SELECT 'period', COALESCE(SUM(points), 0) FROM period_bonus WHERE owner_id = ?
        UNION ALL SELECT 'exam', COALESCE(SUM(points), 0) FROM exam_rewards WHERE owner_id = ?
        UNION ALL SELECT 'special', COALESCE(SUM(points), 0) FROM special_events WHERE owner_id = ?
        UNION ALL SELECT 'spent', COALESCE(SUM(cost), 0) FROM redemptions WHERE owner_id = ?
        UNION ALL SELECT 'extra', COALESCE(SUM(points), 0) FROM extra_points WHERE owner_id = ?
    """
    try:
        rows = db.execute(query, (oid, oid, oid, oid, oid, oid)).fetchall()
        data = {r["k"]: float(r["s"] or 0) for r in rows}
    except: data = {"daily": 0.0, "period": 0.0, "exam": 0.0, "special": 0.0, "spent": 0.0, "extra": 0.0}
    daily, period, exam, special, spent, extra = [round(data[k], 2) for k in ["daily", "period", "exam", "special", "spent", "extra"]]
    return {"daily": daily, "period": period, "exam": exam, "special": special, "spent": spent, "extra": extra, "balance": round(daily + period + exam + special + extra - spent, 2)}

# ================= 排行榜 =================
def get_leaderboard(children, period, tz_offset):
    if not children:
        return []
    now = get_user_now(tz_offset)
    today = now.date()
    if period == "day":
        start = today.isoformat()
    elif period == "month":
        start = today.replace(day=1).isoformat()
    else:
        start = None

    db = get_db()
    scores = {c: 0.0 for c in children}
    placeholders = ",".join(["?"] * len(children))
    try:
        if start is None:
            rows = db.execute(
                f"SELECT owner_id, SUM(total_score) as s FROM daily_records WHERE owner_id IN ({placeholders}) GROUP BY owner_id",
                (*children,)
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT owner_id, SUM(total_score) as s FROM daily_records WHERE owner_id IN ({placeholders}) AND day >= ? GROUP BY owner_id",
                (*children, start)
            ).fetchall()
        for r in rows:
            if r["owner_id"] in scores:
                scores[r["owner_id"]] += float(r["s"] or 0)

        for tbl in ["period_bonus", "exam_rewards", "special_events", "extra_points"]:
            if start is None:
                rows = db.execute(
                    f"SELECT owner_id, SUM(points) as s FROM {tbl} WHERE owner_id IN ({placeholders}) GROUP BY owner_id",
                    (*children,)
                ).fetchall()
            else:
                rows = db.execute(
                    f"SELECT owner_id, SUM(points) as s FROM {tbl} WHERE owner_id IN ({placeholders}) AND substr(ts, 1, 10) >= ? GROUP BY owner_id",
                    (*children, start)
                ).fetchall()
            for r in rows:
                if r["owner_id"] in scores:
                    scores[r["owner_id"]] += float(r["s"] or 0)
    except Exception as e:
        print(f"leaderboard query failed: {e}")

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [{"username": u, "score": round(s, 2), "rank": i + 1} for i, (u, s) in enumerate(ranked)]

@st.cache_data(ttl=10, show_spinner=False)
def get_makeup_cards_of(username):
    try:
        db = get_db()
        row = db.execute("SELECT makeup_cards FROM users WHERE username=?", (username,)).fetchone()
        return int(dict(row).get("makeup_cards") or 0) if row else 0
    except: return 0

@st.cache_data(ttl=10, show_spinner=False)
def get_user_badges(oid):
    db = get_db()
    try: configs = get_badge_configs()
    except: return []
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
    except: return []
    for cfg in configs:
        try:
            cond_type = cfg["cond_type"]; cond_val = float(cfg["cond_val"] or 0)
            if ((cond_type == 'days' and days_count >= cond_val) or (cond_type == 'points' and total_earned >= cond_val) or
                (cond_type == 'perfect' and perfect_count >= cond_val) or (cond_type == 'exam_hits' and max_exam_hits >= cond_val)):
                earned.append({"name": html.escape(cfg["name"]), "icon": html.escape(cfg["icon_url"] or "", quote=True)})
        except: continue
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
        if wd == 3: streak = 1; all_full = base >= full_thr
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
    try:
        bonus_rules = get_bonus_rules(oid)
        start_d = (get_user_today(8.0) - timedelta(days=30)).isoformat()
        rows = db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=? AND day >= ?", (oid, start_d)).fetchall()
        if not rows: return
        lookup = {r["day"]: {"base_score": float(r["base_score"] or 0), "basic_thr": float(r.get("basic_thr") or 0), "full_thr": float(r.get("full_thr") or 0)} for r in rows}
        updates = []
        for day_str in sorted(lookup):
            try: d = date.fromisoformat(day_str)
            except: continue
            bonus, detail = compute_bonus_for_day(d, lookup, bonus_rules)
            updates.append((bonus, json.dumps(detail), float(lookup[day_str]["base_score"]) + bonus, day_str, oid))
        if updates:
            db.executemany("UPDATE daily_records SET bonus_score=?, bonus_detail=?, total_score=? WHERE day=? AND owner_id=?", updates)
            db.commit()
    except Exception as e: print(f"日常连击奖励重算失败: {e}")

def settle_longterm_bonus(db, oid, ts):
    try:
        bonus_rules = get_bonus_rules(oid); lt_rules = bonus_rules["longterm"]
        today = get_user_today(8.0)
        min_row = db.execute("SELECT MIN(day) as min_day FROM daily_records WHERE owner_id=?", (oid,)).fetchone()
        if not min_row or not min_row["min_day"]: return
        actual_min = min_row["min_day"]
        base_start_date = today - timedelta(days=60)
        base_start_str = max(actual_min, base_start_date.isoformat())
        d_start = date.fromisoformat(base_start_str)
        start_monday = (d_start - timedelta(days=d_start.weekday())).isoformat()
        start_month = date(d_start.year, d_start.month, 1).isoformat()
        final_start = min(start_monday, start_month)
        rows = db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=? AND day >= ?", (oid, final_start)).fetchall()
        scores = {r["day"]: r for r in rows}
        if not scores: return

        inserts = []; keys_to_delete = set()
        weeks = {}
        for ds in scores:
            d = date.fromisoformat(ds); y, w, _ = d.isocalendar()
            weeks.setdefault(f"{y}-W{w:02d}", []).append(d)
            
        week_status = {}
        for wk, dlist in weeks.items():
            keys_to_delete.add(f"W:{wk}")
            monday = min(dlist) - timedelta(days=min(dlist).weekday())
            full_week = [monday + timedelta(days=i) for i in range(7)]
            if not all(x.isoformat() in scores for x in full_week):
                week_status[wk] = {'is_perfect': False, 'is_basic': False}; continue
            miss_basic = 0; miss_full = 0
            for x in full_week:
                day_data = scores[x.isoformat()]
                if float(day_data.get("base_score") or 0) < float(day_data.get("basic_thr") or 999): miss_basic += 1
                elif float(day_data.get("base_score") or 0) < float(day_data.get("full_thr") or 999): miss_full += 1
            target_kind, target_pts = None, 0.0
            is_perfect = False; is_basic = False
            if miss_basic == 0:
                is_basic = True
                if miss_full == 0: is_perfect = True; target_kind = "完美一周(全满分)"; target_pts = lt_rules["week_full"]
                elif miss_full == 1: is_perfect = True; target_kind = "完美一周(弹性1天)"; target_pts = max(0, lt_rules["week_full"] - lt_rules.get("week_flex_perfect_deduct", 1.0))
                else: target_kind = "整周达标"; target_pts = lt_rules["week_basic"]
            elif miss_basic == 1: is_basic = True; target_kind = "整周达标(弹性1天)"; target_pts = max(0, lt_rules["week_basic"] - lt_rules.get("week_flex_basic_deduct", 0.5))
            week_status[wk] = {'is_perfect': is_perfect, 'is_basic': is_basic}
            if target_kind: inserts.append((f"W:{wk}", oid, target_kind, target_pts, ts))

        months = {}
        for ds in scores:
            d = date.fromisoformat(ds); y, m = d.year, d.month
            months.setdefault(f"{y}-{m:02d}", []).append(d)
        for mk, dlist in months.items():
            keys_to_delete.add(f"M:{mk}")
            y, m = int(mk.split("-")[0]), int(mk.split("-")[1])
            first = date(y, m, 1); nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
            alldays = []; cur = first
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
            if target_kind: inserts.append((f"M:{mk}", oid, target_kind, target_pts, ts))

        if keys_to_delete:
            keys_list = list(keys_to_delete)
            placeholders = ",".join(["?"] * len(keys_list))
            db.execute(f"DELETE FROM period_bonus WHERE owner_id=? AND period_key IN ({placeholders})", (oid, *keys_list))
        if inserts: db.executemany("INSERT INTO period_bonus (period_key, owner_id, kind, points, ts) VALUES (?,?,?,?,?)", inserts)
        db.commit()
    except Exception as e: print(f"长期奖励结算失败: {e}")

def save_day(db, day: date, done_ids: list, oid: str, ts: str):
    tasks = get_tasks(day.weekday(), oid)
    base = sum(task["points"] for task in tasks if task["id"] in set(done_ids))
    thresholds = get_thresholds(oid); thr = thresholds.get(day.weekday(), {"basic": 0, "full": 0})
    
    existing = db.execute("SELECT day FROM daily_records WHERE day=? AND owner_id=?", (day.isoformat(), oid)).fetchone()
    if existing:
        db.execute("UPDATE daily_records SET done_tasks=?, base_score=?, bonus_score=0, bonus_detail='{}', total_score=?, updated_at=?, basic_thr=?, full_thr=? WHERE day=? AND owner_id=?",
            (json.dumps(sorted(done_ids)), base, base, ts, thr["basic"], thr["full"], day.isoformat(), oid))
    else:
        db.execute("INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) VALUES (?, ?, ?, ?, 0, '{}', ?, ?, ?, ?)",
            (day.isoformat(), oid, json.dumps(sorted(done_ids)), base, base, ts, thr["basic"], thr["full"]))
    db.commit()
    recalc_all_bonus(db, oid)
    settle_longterm_bonus(db, oid, ts)
    st.cache_data.clear()

def calc_exam_bonus(scores: dict, ranks: dict, oid: str):
    try: exam_config, exam_rules = get_exam_config(oid); multihit_rules = get_exam_multihit(oid)
    except: return 0.0, ["数据配置异常，无法结算"], 0
    total = 0.0; lines = []; hit_count = 0
    for subject, cfg in exam_config.items():
        actual = scores.get(subject)
        if actual is None: continue
        if cfg.get("type") == "score":
            hit = actual >= cfg.get("target", 0)
            if hit: total += exam_rules.get("hit_points", 1); hit_count += 1; lines.append(f"达成 {subject} -> +{exam_rules.get('hit_points', 1)}")
            step = cfg.get("step", 0); tiers = int((actual - cfg.get("target", 0)) // step) if step > 0 and actual > cfg.get("target", 0) else 0
            if tiers > 0: gain = tiers * cfg.get("step_points", 0); total += gain; lines.append(f"  {subject} 超目标 {tiers} 档 -> +{gain}")
        else:
            if cfg.get("target") not in GRADES or actual not in GRADES: continue
            gap = GRADES.index(cfg["target"]) - GRADES.index(actual); hit = gap >= 0
            if hit: total += exam_rules.get("hit_points", 1); hit_count += 1; lines.append(f"达成 {subject} -> +{exam_rules.get('hit_points', 1)}")
            if gap > 0: gain = gap * cfg.get("step_points", 0); total += gain; lines.append(f"  {subject} 升 {gap} 档 -> +{gain}")
    for mh in sorted(multihit_rules, key=lambda x: x["hit_count"], reverse=True):
        if hit_count >= mh["hit_count"]: total += mh["points"]; lines.append(f"达成 {mh['hit_count']} 门及以上 -> +{mh['points']}"); break
    for subject in ["语文", "数学", "英语"]:
        pct = ranks.get(subject)
        if pct is not None and 0 <= pct < 100 and pct <= exam_rules.get("rank_top_percent", 75):
            total += exam_rules.get("rank_base_points", 1); lines.append(f"{subject} 前{pct:.0f}% -> +{exam_rules.get('rank_base_points', 1)}")
            pct_step = exam_rules.get("rank_step_percent", 5); extra = int((exam_rules.get("rank_top_percent", 75) - pct) // pct_step) if pct_step > 0 else 0
            if extra > 0: gain = extra * exam_rules.get("rank_step_points", 1.5); total += gain; lines.append(f"  再进{extra}档 -> +{gain}")
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
            <select id="mode"><option value="stopwatch">正计时</option><option value="countdown">倒计时</option></select>
            <span><input type="number" id="minutes" value="25" min="1"> 分</span>
        </div>
        <div class="btn-group">
            <button onclick="startTimer()">开始</button><button class="btn-stop" onclick="stopTimer()">暂停</button><button class="btn-reset" onclick="resetTimer()">重置</button>
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
    try: st.iframe(data_uri, height=220)
    except AttributeError:
        import streamlit.components.v1 as components
        components.html(timer_html, height=220)

def login_page(db):
    st.title(t("app_title"))
    render_language_selector("login_top")
    if "login_page_uid" not in st.session_state: st.session_state.login_page_uid = secrets.token_hex(4)
    uid = st.session_state.login_page_uid
    tab1, tab2, tab3 = st.tabs([t("login"), t("register"), t("find_pwd")])

    with tab1:
        with st.form(f"login_form_{uid}"):
            u = st.text_input(t("username"), max_chars=20)
            p = st.text_input(t("password"), type="password", max_chars=72)
            if _submit(t("login_btn"), **_stretch({"type": "primary"})):
                try:
                    user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
                    if user:
                        stored_hash = user["password_hash"]; is_valid = False
                        if len(stored_hash) == 64:
                            if stored_hash == hash_pwd_sha256(p):
                                is_valid = True; new_hash = hash_pwd_bcrypt(p)
                                db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, u)); db.commit()
                                stored_hash = new_hash
                        else:
                            if check_pwd_bcrypt(p, stored_hash): is_valid = True
                        if is_valid:
                            st.session_state.user = u; st.session_state.role = user["role"]
                            if user.get("language") in LANG_PACKS:
                                st.session_state["lang"] = user["language"]
                            st.query_params["user"] = u
                            st.query_params["auth"] = generate_auth_token(u, stored_hash)
                            if p == "123456": st.session_state.force_pwd_change = True
                            st.rerun()
                        else: st.error(t("wrong_creds"))
                    else: st.error(t("wrong_creds"))
                except RuntimeError as e: st.error(str(e))

    with tab2:
        with st.form(f"reg_form_{uid}"):
            u = st.text_input(t("set_username"), max_chars=20)
            p = st.text_input(t("set_pwd"), type="password", max_chars=72)
            p2 = st.text_input(t("confirm_pwd"), type="password", max_chars=72)
            sq = st.text_input(t("security_q"), max_chars=50)
            sa = st.text_input(t("security_a"), max_chars=50)
            if _submit(t("register_btn"), **_stretch({"type": "primary"})):
                if not u or not p or not sq or not sa: st.error(t("fill_all"))
                elif p != p2: st.error(t("pwd_mismatch"))
                elif u.lower() in ["system", "admin"]: st.error(t("reserved_name"))
                else:
                    try:
                        if db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone(): st.error(t("user_exists"))
                        else:
                            trial_exp = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
                            db.execute("INSERT INTO users (username, password_hash, role, security_question, security_answer, plan_expires_at, language) VALUES (?, ?, 'user', ?, ?, ?, ?)",
                                (u, hash_pwd_bcrypt(p), sq, hash_pwd_sha256(sa.strip().lower()), trial_exp, get_lang()))
                            db.commit()
                            try: init_old_admin_data(db, u)
                            except Exception as e: print(f"初始化新用户默认配置失败（静默处理）: {e}")
                            st.cache_data.clear(); st.success(t("register_ok"))
                    except RuntimeError as e: st.error(str(e))

    with tab3:
        st.write(t("reset_intro"))
        u_reset = st.text_input(t("input_username"), key=f"reset_u_{uid}", max_chars=20)
        if u_reset:
            try:
                user = db.execute("SELECT * FROM users WHERE username=?", (u_reset,)).fetchone()
                if user:
                    sq = user.get("security_question")
                    if not sq: st.warning(t("no_security_q"))
                    else:
                        with st.form(f"reset_form_{uid}"):
                            st.info(f"{t('security_q')}: {html.escape(sq)}")
                            ans = st.text_input(t("security_a"), max_chars=50)
                            new_p = st.text_input(t("new_password"), type="password", max_chars=72)
                            if _submit(t("reset_btn"), **_stretch({"type": "primary"})):
                                if not ans or not new_p: st.error(t("fill_all"))
                                elif hash_pwd_sha256(ans.strip().lower()) == user["security_answer"]:
                                    new_hash = hash_pwd_bcrypt(new_p)
                                    db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, u_reset))
                                    db.commit(); st.success(t("reset_ok"))
                                else: st.error(t("wrong_answer"))
                else: st.error(t("user_not_exist"))
            except RuntimeError as e: st.error(str(e))

def main():
    st.set_page_config(page_title="学习打卡系统", layout="centered", initial_sidebar_state="collapsed")
    try: db = get_db()
    except RuntimeError as e: st.error(str(e)); st.stop()

    old_warn = st.session_state.get("_old_sqlite_warning")
    if old_warn: st.warning(old_warn)

    if "user" not in st.session_state:
        param_user = st.query_params.get("user")
        param_auth = st.query_params.get("auth")
        if param_user and param_auth:
            try:
                row = db.execute("SELECT * FROM users WHERE username=?", (param_user,)).fetchone()
                if row and verify_auth_token(param_user, param_auth, row["password_hash"]):
                    st.session_state.user = row["username"]
                    st.session_state.role = row["role"]
                    if row.get("language") in LANG_PACKS:
                        st.session_state["lang"] = row["language"]
                    if check_pwd_bcrypt("123456", row["password_hash"]): st.session_state.force_pwd_change = True
                else:
                    st.query_params.clear(); login_page(db); return
            except Exception:
                st.query_params.clear(); login_page(db); return
        else:
            login_page(db); return

    current_user = st.session_state.user
    try:
        user_row = db.execute("SELECT * FROM users WHERE username=?", (current_user,)).fetchone()
        if not user_row:
            del st.session_state.user; del st.session_state.role; st.query_params.clear(); st.rerun()
    except RuntimeError as e: st.error(str(e)); st.stop()

    if st.session_state.get("force_pwd_change"):
        st.title("⚠️ 安全提示：请修改默认密码")
        st.warning("检测到您正在使用系统默认密码 (123456)，为了您的数据安全，请立即修改后才能继续使用。")
        with st.form("force_pwd_form"):
            new_p = st.text_input(t("new_password"), type="password", max_chars=72)
            confirm_p = st.text_input(t("confirm_pwd"), type="password", max_chars=72)
            submit = _submit("提交修改", **_stretch({"type": "primary"}))
            if submit:
                if not new_p or not confirm_p: st.error(t("fill_all"))
                elif new_p != confirm_p: st.error(t("pwd_mismatch"))
                elif len(new_p) < 6: st.error("新密码长度不能少于 6 位")
                elif new_p == "123456": st.error("新密码不能与默认密码相同")
                else:
                    try:
                        new_hash = hash_pwd_bcrypt(new_p)
                        db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, current_user))
                        db.commit()
                        del st.session_state.force_pwd_change
                        st.query_params["auth"] = generate_auth_token(current_user, new_hash)
                        st.success("✅ 密码修改成功！正在进入系统..."); st.rerun()
                    except RuntimeError as e: st.error(str(e))
        st.stop()

    current_role = user_row["role"]
    st.session_state.role = current_role

    try: all_users_data = get_all_users()
    except: all_users_data = []

    user_tz = user_row.get("timezone_offset") or 8.0
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
    except: pass

    with st.sidebar:
        st.title(t("sidebar_title"))
        render_language_selector("sidebar")
        if st.session_state.get("lang") and user_row.get("language") != st.session_state["lang"]:
            try:
                db.execute("UPDATE users SET language=? WHERE username=?", (st.session_state["lang"], current_user))
                db.commit()
            except Exception:
                pass
        is_mobile_mode = st.checkbox(t("mobile_mode"), value=False)
        bal = {"balance": 0, "daily": 0, "period": 0, "exam": 0, "special": 0, "spent": 0, "extra": 0}

        view_as = current_user; view_role = current_role
        if current_role == "user": view_as = current_user; view_role = "user"
        elif current_role == "host":
            try:
                children = db.execute("SELECT username FROM users WHERE host_id=?", (current_user,)).fetchall()
                child_names = [r["username"] for r in children]
            except: child_names = []
            if not child_names: view_as = None; st.warning(t("no_children_bound"))
            else: view_as = st.selectbox(t("select_child"), child_names, index=0); view_role = "user"
        elif current_role == "solo":
            view_as = current_user
            view_role = "solo"
        elif current_role == "admin":
            try: all_users = db.execute("SELECT username, role FROM users").fetchall()
            except: all_users = []
            user_list = [u["username"] for u in all_users]
            if current_user in user_list: user_list.remove(current_user); user_list.insert(0, current_user)
            selected_target = st.selectbox(t("admin_select_target"), user_list, index=0)
            try:
                target_role_row = db.execute("SELECT role FROM users WHERE username=?", (selected_target,)).fetchone()
                target_role = target_role_row["role"] if target_role_row else "user"
            except: target_role = "user"
            if target_role == "host":
                try:
                    children = db.execute("SELECT username FROM users WHERE host_id=?", (selected_target,)).fetchall()
                    child_names = [r["username"] for r in children]
                except: child_names = []
                if child_names:
                    selected_child = st.selectbox(f"{t('penetrate')}: {selected_target}", child_names, index=0)
                    view_as = selected_child; view_role = "user"
                else:
                    st.caption("该家长名下暂无孩子，当前配置的是家长本人")
                    view_as = selected_target; view_role = "host"
            else: view_as = selected_target; view_role = target_role

        if view_as:
            try:
                target_urow = db.execute("SELECT * FROM users WHERE username=?", (view_as,)).fetchone()
                target_tz = target_urow.get("timezone_offset") if target_urow else 8.0
                if target_tz is None: target_tz = 8.0
                plan_exp = target_urow.get("plan_expires_at") if target_urow else None
            except: target_tz = 8.0; plan_exp = None
            
            view_today = get_user_today(target_tz)
            view_makeup_sidebar = get_makeup_cards_of(view_as)
            role_display = {"admin": t("role_admin"), "host": t("role_host"), "user": t("role_user"), "solo": t("role_solo")}.get(view_role, view_role)
            
            plan_exp_str = ""
            if view_role in ["user", "solo", "admin"]:
                rem_days = get_remaining_days(plan_exp)
                if rem_days == 9999: plan_exp_str = f"\n\n⏳ {t('remaining')}: {t('permanent')}"
                elif rem_days < 0: plan_exp_str = f"\n\n⚠️ {t('expired')}"
                else: plan_exp_str = f"\n\n⏳ {t('remaining')}: {rem_days} 天"
            
            st.info(f"{t('current_identity')}: {html.escape(view_as)} ({role_display}){plan_exp_str}\n\n{t('local_time')}: {get_user_now(target_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n{t('makeup_cards')}: {view_makeup_sidebar}")
            try: bal = get_balance(view_as)
            except: pass
            if view_role != "host": st.metric(t("available_points"), f"{bal['balance']:.1f}")
        else:
            st.info(f"{t('current_identity')}: {html.escape(current_user)} ({t('role_host')})\n\n{t('no_children_bound')}")

        if not is_mobile_mode and (view_role in ("admin", "solo") or (view_role == "host" and view_as)):
            with st.expander(t("timer"), expanded=False): render_timer()
            with st.expander(t("badges")):
                try: user_badges = get_user_badges(view_as)
                except: user_badges = []
                if user_badges:
                    for i in range(0, len(user_badges), 3):
                        cols = st.columns(3)
                        for j in range(3):
                            if i + j < len(user_badges):
                                b = user_badges[i + j]
                                with cols[j]:
                                    st.markdown(f'<div style="height:70px; display:flex; align-items:center; justify-content:center;"><img src="{b["icon"]}" width="60" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'"></div>', unsafe_allow_html=True)
                                    st.markdown(f"<div style='text-align: center; font-size: 14px;'>{b['name']}</div>", unsafe_allow_html=True)
                else: st.caption(t("no_badges"))
            with st.expander(t("points_detail")):
                st.write(f"{t('checkin_pts')}: {bal['daily']:.1f} | {t('longterm_pts')}: {bal['period']:.1f}")
                st.write(f"{t('exam_pts')}: {bal['exam']:.1f} | {t('extra_pts')}: {bal['extra']:.1f}")
                st.write(f"{t('special_pts')}: {bal['special']:.1f} | {t('spent_pts')}: -{bal['spent']:.1f}")

            st.divider()
            with st.expander(t("account_settings")):
                st.markdown(f"**{t('timezone')}**")
                curr_tz_name = next((k for k, v in TIMEZONES.items() if v == user_tz), "自定义时区")
                new_tz_name = st.selectbox(t("select_timezone"), list(TIMEZONES.keys()), index=list(TIMEZONES.keys()).index(curr_tz_name))
                if new_tz_name == "自定义时区":
                    custom_tz = st.number_input(t("tz_offset"), value=float(user_tz), step=0.5, min_value=-12.0, max_value=14.0)
                    final_tz = custom_tz
                else: final_tz = TIMEZONES[new_tz_name]
                if st.button(t("save_tz"), **_stretch({})):
                    try: db.execute("UPDATE users SET timezone_offset=? WHERE username=?", (final_tz, current_user)); db.commit(); st.success("时区已更新！"); st.rerun()
                    except RuntimeError as e: st.error(str(e))

                st.divider()
                new_name = st.text_input(t("new_username"), placeholder=t("leave_blank"), max_chars=20)
                if st.button(t("change_username"), **_stretch({})):
                    if new_name and new_name != current_user:
                        if new_name.lower() in ["system", "admin"]: st.error(t("reserved_name"))
                        else:
                            try:
                                if db.execute("SELECT * FROM users WHERE username=?", (new_name,)).fetchone(): st.error("该用户名已被占用")
                                else:
                                    db.begin()
                                    try:
                                        for tbl in ["daily_records", "period_bonus", "redemptions", "exam_rewards", "special_events", "extra_points", "config_tasks", "config_shop", "config_exam", "config_exam_rules", "config_thresholds", "config_bonus_rules", "config_exam_multihit"]:
                                            db.execute(f"UPDATE {tbl} SET owner_id=? WHERE owner_id=?", (new_name, current_user))
                                        db.execute("UPDATE users SET host_id=? WHERE host_id=?", (new_name, current_user))
                                        db.execute("UPDATE redeem_codes SET used_by=? WHERE used_by=?", (new_name, current_user))
                                        db.execute("UPDATE users SET username=? WHERE username=?", (new_name, current_user))
                                        db.commit(); db.end()
                                        st.session_state.user = new_name
                                        st.query_params["user"] = new_name
                                        st.query_params["auth"] = generate_auth_token(new_name, user_row["password_hash"])
                                        st.cache_data.clear(); st.success("用户名修改成功！"); st.rerun()
                                    except Exception as e:
                                        db.rollback(); db.end(); st.error(f"修改失败：{str(e)}")
                            except RuntimeError as e: st.error(str(e))

                st.divider()
                new_pwd = st.text_input(t("new_password"), type="password", key="new_pwd", max_chars=72)
                if st.button(t("change_pwd"), **_stretch({})):
                    if new_pwd:
                        try:
                            new_hash = hash_pwd_bcrypt(new_pwd)
                            db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, current_user))
                            db.commit()
                            st.query_params["auth"] = generate_auth_token(current_user, new_hash)
                            st.success("密码已修改！")
                        except RuntimeError as e: st.error(str(e))

                st.divider()
                st.markdown(f"**{t('change_security')}**")
                new_sq = st.text_input(t("new_security_q"), max_chars=50, key="new_sq")
                new_sa = st.text_input(t("new_security_a"), max_chars=50, key="new_sa")
                if st.button(t("save_security"), **_stretch({})):
                    if not new_sq or not new_sa: st.error("密保问题和答案不能为空")
                    else:
                        try:
                            hashed_sa = hash_pwd_sha256(new_sa.strip().lower())
                            db.execute("UPDATE users SET security_question=?, security_answer=? WHERE username=?", (new_sq, hashed_sa, current_user))
                            db.commit(); st.success("密保已修改！")
                        except RuntimeError as e: st.error(str(e))

                st.divider()
                webhook_input = st.text_input(t("webhook"), value=user_row.get("webhook_url") or "")
                if st.button(t("save_webhook"), **_stretch({})):
                    try: db.execute("UPDATE users SET webhook_url=? WHERE username=?", (webhook_input, current_user)); db.commit(); st.success("保存成功！")
                    except RuntimeError as e: st.error(str(e))

                st.divider()
                try:
                    my_data = {
                        "daily_records": [dict(r) for r in db.execute("SELECT * FROM daily_records WHERE owner_id=?", (current_user,)).fetchall()],
                        "exam_rewards": [dict(r) for r in db.execute("SELECT * FROM exam_rewards WHERE owner_id=?", (current_user,)).fetchall()],
                        "redemptions": [dict(r) for r in db.execute("SELECT * FROM redemptions WHERE owner_id=?", (current_user,)).fetchall()],
                        "extra_points": [dict(r) for r in db.execute("SELECT * FROM extra_points WHERE owner_id=?", (current_user,)).fetchall()],
                        "special_events": [dict(r) for r in db.execute("SELECT * FROM special_events WHERE owner_id=?", (current_user,)).fetchall()]
                    }
                    st.download_button(t("export_data"), data=json.dumps(my_data, ensure_ascii=False, indent=2, default=str), file_name=f"backup_{current_user}.json", mime="application/json", **_stretch({}))
                except: pass

        st.divider()
        if st.button(t("logout_btn"), **_stretch({})):
            del st.session_state.user; del st.session_state.role; st.query_params.clear(); st.rerun()

    if view_role == "host" and view_as is None:
        st.info(t("no_children_bound")); st.stop()

    # 【会员到期拦截】
    if view_role in ["user", "solo"]:
        target_exp = user_row.get("plan_expires_at") if view_as == current_user else db.execute("SELECT plan_expires_at FROM users WHERE username=?", (view_as,)).fetchone()
        exp_str = target_exp.get("plan_expires_at") if isinstance(target_exp, dict) else target_exp
        is_expired = False
        if exp_str and str(exp_str).startswith("2099"):
            is_expired = False
        elif not exp_str:
            is_expired = True
        else:
            try:
                if datetime.now() > datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S'):
                    is_expired = True
            except:
                is_expired = True
        
        if is_expired:
            st.error(f"【{view_as}】的内测体验已到期，请向管理员索取兑换码续费。")
            with st.form(f"redeem_form_{view_as}"):
                c_code = st.text_input("请输入兑换码")
                submit = st.form_submit_button("激活", type="primary")
                if submit and c_code:
                    c_code = c_code.strip().upper()
                    db.begin()
                    try:
                        cur = db.execute("UPDATE redeem_codes SET is_used=1, used_by=? WHERE code=? AND is_used=0", (view_as, c_code))
                        if getattr(cur, "rowcount", 0) == 0:
                            db.rollback(); db.end()
                            st.error("无效或已被使用的兑换码。")
                        else:
                            code_row = db.execute("SELECT days FROM redeem_codes WHERE code=?", (c_code,)).fetchone()
                            days = int(code_row["days"])
                            new_exp = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
                            db.execute("UPDATE users SET plan_expires_at=? WHERE username=?", (new_exp, view_as))
                            db.commit(); db.end()
                            st.success("激活成功！")
                            st.rerun()
                    except Exception as e:
                        db.rollback(); db.end()
                        st.error(f"激活失败：{str(e)}")
            st.stop()

    base_desktop = [t("tab_checkin"), t("tab_extra"), t("tab_history"), t("tab_shop"), t("tab_redeem"), t("tab_exam"), t("tab_event")]
    base_mobile = [t("tab_checkin"), t("tab_shop"), t("tab_redeem")]
    # 孩子（user）桌面/手机模式均加入排行榜
    base_desktop_user = [t("tab_checkin"), t("tab_leaderboard"), t("tab_history"), t("tab_shop"), t("tab_redeem"), t("tab_exam"), t("tab_event")]
    base_mobile_user = [t("tab_checkin"), t("tab_leaderboard"), t("tab_shop"), t("tab_redeem")]

    if current_role in ("admin", "solo"):
        tabs = base_mobile + [t("tab_settings")] if is_mobile_mode else base_desktop + [t("tab_settings")]
    elif current_role == "host":
        tabs = [t("tab_history"), t("tab_leaderboard"), t("tab_extra"), t("tab_settings")]
    else:
        tabs = base_mobile_user if is_mobile_mode else base_desktop_user

    tab_objs = st.tabs(tabs)
    tab_dict = {name: obj for name, obj in zip(tabs, tab_objs)}

    # ============ 打卡 ============
    if t("tab_checkin") in tab_dict:
        with tab_dict[t("tab_checkin")]:
            try: tasks = get_tasks(view_today.weekday(), view_as)
            except: tasks = []
            if not tasks: st.warning(t("no_tasks_today"))
            else:
                try: thresholds = get_thresholds(view_as); thr = thresholds.get(view_today.weekday(), {"basic": 0, "full": 0})
                except: thr = {"basic": 0, "full": 0}
                st.subheader(f"{view_today.strftime('%m月%d日')} - {WEEKDAY_CN[view_today.weekday()]}")
                st.caption(f"{t('basic_req')}: {thr['basic']} {t('score_col')} | {t('full_req')}: {thr['full']} {t('score_col')}")
                try: existing = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)).fetchone()
                except: existing = None
                already_done = existing is not None
                done_ids = set(json.loads(existing["done_tasks"])) if (existing and existing["done_tasks"]) else set()
                cats = {}
                for task in tasks: cats.setdefault(task["category"], []).append(task)
                selected_ids = []
                for cat, items in cats.items():
                    st.markdown(f"**{html.escape(cat)}**")
                    if is_mobile_mode:
                        for task in items:
                            if st.checkbox(f"{html.escape(task['name'])} ({task['points']}{t('score_col')})", value=(task["id"] in done_ids), key=f"cb_{view_today}_{view_as}_{task['id']}", disabled=already_done):
                                if not already_done: selected_ids.append(task["id"])
                    else:
                        cols = st.columns(2)
                        for i, task in enumerate(items):
                            with cols[i % 2]:
                                if st.checkbox(f"{html.escape(task['name'])} ({task['points']}{t('score_col')})", value=(task["id"] in done_ids), key=f"cb_{view_today}_{view_as}_{task['id']}", disabled=already_done):
                                    if not already_done: selected_ids.append(task["id"])
                st.divider()
                c1, c2, c3 = st.columns(3)
                if already_done:
                    c1.metric(t("base_score"), f"{float(existing['base_score'] or 0):.1f}"); c2.metric(t("bonus"), f"{float(existing['bonus_score'] or 0):.1f}"); c3.metric(t("today_total"), f"{float(existing['total_score'] or 0):.1f}")
                    st.success(t("today_done"))
                    if st.button(t("undo_checkin"), **_stretch({"type": "secondary"})):
                        try:
                            db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)); db.commit()
                            recalc_all_bonus(db, view_as); settle_longterm_bonus(db, view_as, now.isoformat())
                            st.cache_data.clear(); st.rerun()
                        except RuntimeError as e: st.error(str(e))
                else:
                    base_now = sum(task["points"] for task in tasks if task["id"] in set(selected_ids))
                    try:
                        lookup = {r["day"]: {"base_score": float(r["base_score"] or 0), "basic_thr": float(r.get("basic_thr") or 0), "full_thr": float(r.get("full_thr") or 0)} for r in db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=?", (view_as,)).fetchall()}
                        lookup[view_today.isoformat()] = {"base_score": base_now, "basic_thr": thr["basic"], "full_thr": thr["full"]}
                        bonus, detail = compute_bonus_for_day(view_today, lookup, get_bonus_rules(view_as))
                    except: bonus, detail = 0.0, {}
                    c1.metric(t("base_score"), f"{base_now:.1f}"); c2.metric(t("bonus"), f"{bonus:.1f}"); c3.metric(t("est_total"), f"{base_now + bonus:.1f}")
                    if detail.get("tier") in TIER_CN: st.info(f"{t('bonus')}: {TIER_CN[detail['tier']]}")
                    if st.button(t("save_checkin"), **_stretch({"type": "primary"})):
                        try: save_day(db, view_today, selected_ids, view_as, now.isoformat()); st.success(t("saved")); st.rerun()
                        except RuntimeError as e: st.error(str(e))

    # ============ 排行榜（host + user） ============
    if t("tab_leaderboard") in tab_dict and current_role in ("host", "user"):
        with tab_dict[t("tab_leaderboard")]:
            st.subheader(t("leaderboard_title"))
            # 取要比较的孩子列表：host 直接查；user 先查自己的 host，再取该 host 名下所有孩子
            if current_role == "host":
                try:
                    child_rows = db.execute("SELECT username FROM users WHERE host_id=?", (current_user,)).fetchall()
                    lb_children = [r["username"] for r in child_rows]
                except Exception:
                    lb_children = []
            else:  # user
                try:
                    my_row = db.execute("SELECT host_id FROM users WHERE username=?", (current_user,)).fetchone()
                    my_host = dict(my_row).get("host_id") if my_row else None
                    if my_host:
                        sib_rows = db.execute("SELECT username FROM users WHERE host_id=?", (my_host,)).fetchall()
                        lb_children = [r["username"] for r in sib_rows]
                    else:
                        lb_children = [current_user]
                except Exception:
                    lb_children = [current_user]

            if not lb_children:
                st.info(t("no_rank_data"))
            else:
                if current_role == "user" and len(lb_children) <= 1:
                    st.info(t("only_you"))
                period = st.radio(
                    t("period"),
                    options=["day", "month", "all"],
                    format_func=lambda x: t({"day": "daily_board", "month": "monthly_board", "all": "total_board"}[x]),
                    horizontal=True,
                    key=f"leaderboard_period_{current_role}",
                )
                board = get_leaderboard(lb_children, period, user_tz)
                medals = ["🥇", "🥈", "🥉"]
                max_score = max((b["score"] for b in board), default=0) or 1
                for item in board:
                    rank_icon = medals[item["rank"] - 1] if item["rank"] <= 3 else f"#{item['rank']}"
                    is_me = (current_role == "user" and item["username"] == current_user)
                    name_display = html.escape(item["username"])
                    if is_me:
                        name_display = f"**{name_display}** :orange[**{t('you')}**]"
                    st.markdown(f"**{rank_icon}  {name_display}**  —  {item['score']:.1f} {t('score_col')}")
                    st.progress(min(item["score"] / max_score, 1.0))

    # ============ 偶发 ============
    if t("tab_extra") in tab_dict:
        with tab_dict[t("tab_extra")]:
            if current_role == "user": st.warning("只有家长或管理员才能添加偶发事件哦。"); st.stop()
            st.subheader("偶发事件加/扣分")
            with st.form("extra_point_form"):
                col1, col2, col3 = st.columns([4, 2, 2])
                e_name = col1.text_input("事件名称", placeholder="例如：高分作文...")
                e_pts = col2.number_input("分数 (可为负数)", value=1.0, step=0.5)
                if _submit("确认提交", **_stretch({"type": "primary"})):
                    if e_name:
                        try: db.execute("INSERT INTO extra_points (owner_id, name, points, ts) VALUES (?,?,?,?)", (view_as, e_name, e_pts, now.isoformat())); db.commit(); st.cache_data.clear(); st.success(f"已记录：{html.escape(e_name)} ({e_pts}分)"); st.rerun()
                        except RuntimeError as e: st.error(str(e))
            st.divider()
            try: ex_rows = db.execute("SELECT * FROM extra_points WHERE owner_id=? ORDER BY id DESC LIMIT 20", (view_as,)).fetchall()
            except: ex_rows = []
            if ex_rows:
                st.dataframe([{"时间": r["ts"], "事件": html.escape(r["name"]), "积分": float(r["points"] or 0)} for r in ex_rows], use_container_width=True, hide_index=True)
                if st.button("清空偶发记录", **_stretch({})):
                    try: db.execute("DELETE FROM extra_points WHERE owner_id=?", (view_as,)); db.commit(); st.cache_data.clear(); st.rerun()
                    except RuntimeError as e: st.error(str(e))
            else: st.caption("暂无记录")

    # ============ 历史与图表 ============
    if t("tab_history") in tab_dict:
        with tab_dict[t("tab_history")]:
            st.subheader("历史与图表分析")
            view_makeup_hist = get_makeup_cards_of(view_as)
            
            if current_role == "host" and view_role == "user": st.info("💡 补签请让孩子在自己的账号里操作。")
            elif view_role == "host": st.info("💡 该账号为家长，请切换选择其名下的孩子进行操作。")
            else:
                if view_makeup_hist > 0:
                    st.markdown(f"🎫 **当前配置对象有 {view_makeup_hist} 张补签卡，可用于补全最近 7 天内漏掉的打卡：**")
                    try: missing_dates = [view_today - timedelta(days=i) for i in range(1, 8) if not db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", ((view_today - timedelta(days=i)).isoformat(), view_as)).fetchone()]
                    except: missing_dates = []
                    if missing_dates:
                        sel_date = st.selectbox("选择要补签的日期", missing_dates, format_func=lambda x: x.strftime('%Y-%m-%d') + f" ({WEEKDAY_CN[x.weekday()]})")
                        past_tasks = get_tasks(sel_date.weekday(), view_as)
                        st.write(f"**请勾选你在 {sel_date.strftime('%m月%d日')} 实际完成的任务（提交后将强制算作满分）：**")
                        with st.form("makeup_form"):
                            selected_past_ids = [task["id"] for task in past_tasks if st.checkbox(f"{html.escape(task['name'])} ({task['points']}分)", key=f"makeup_cb_{sel_date}_{task['id']}")]
                            if _submit("使用 1 张补签卡并提交", **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    cur = db.execute("UPDATE users SET makeup_cards = makeup_cards - 1 WHERE username=? AND makeup_cards > 0", (view_as,))
                                    if getattr(cur, "rowcount", 0) == 0:
                                        db.rollback(); db.end(); st.error("余额不足或并发冲突，无法补签。")
                                    else:
                                        t_thr = get_thresholds(view_as).get(sel_date.weekday(), {"basic": 8, "full": 11})
                                        db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (sel_date.isoformat(), view_as))
                                        db.execute("INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) VALUES (?, ?, ?, ?, 0, '{}', ?, ?, ?, ?)",
                                            (sel_date.isoformat(), view_as, json.dumps(sorted(selected_past_ids)), t_thr["full"], t_thr["full"], now.isoformat(), t_thr["basic"], t_thr["full"]))
                                        db.commit(); db.end()
                                        recalc_all_bonus(db, view_as); settle_longterm_bonus(db, view_as, now.isoformat())
                                        st.cache_data.clear(); st.success("补签成功！"); st.rerun()
                                except Exception as e:
                                    db.rollback(); db.end(); st.error(f"补签失败，请重试：{str(e)}")
                    else: st.info("最近 7 天全勤！")
                else: st.info('💡 提示：商城有售「补签卡」。')

            if view_role in ["user", "solo"] or (current_role == "admin" and view_as == current_user):
                st.divider()
                st.markdown("### 📊 专属学习周报")
                
                start_date = view_today - timedelta(days=6)
                try:
                    week_records = db.execute("SELECT day, total_score FROM daily_records WHERE owner_id=? AND day >= ? AND day <= ? ORDER BY day ASC", (view_as, start_date.isoformat(), view_today.isoformat())).fetchall()
                except:
                    week_records = []
                
                full_week = []
                for i in range(7):
                    d_str = (start_date + timedelta(days=i)).isoformat()
                    rec = next((r for r in week_records if r["day"] == d_str), None)
                    full_week.append({"day": d_str, "total_score": float(rec["total_score"]) if rec else 0.0})
                
                week_records = full_week
                scores = [r["total_score"] for r in week_records]
                days_count = len([s for s in scores if s > 0])
                total_pts = sum(scores)
                max_daily_score = max(scores) if scores else 0.0

                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("本周打卡", f"{days_count} 天")
                rc2.metric("本周总分", f"{total_pts:.1f} 分")
                rc3.metric("单日最高", f"{max_daily_score:.1f} 分")

                if st.button("📸 生成并下载专属周报图", **_stretch({"type": "primary"})):
                    with st.spinner("正在生成精美周报..."):
                        try:
                            prop = setup_chinese_font()
                            dates_labels = [r["day"][5:] for r in week_records]
                            fig, ax = plt.subplots(figsize=(10, 6), facecolor='#f8f9fa')
                            ax.set_facecolor('#f8f9fa')
                            bars = ax.bar(dates_labels, scores, color='#4CAF50', width=0.5, zorder=3)
                            ax.spines['top'].set_visible(False)
                            ax.spines['right'].set_visible(False)
                            ax.spines['left'].set_visible(False)
                            ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
                            ax.set_ylabel("每日得分", fontsize=12, fontproperties=prop)
                            for bar in bars:
                                yval = bar.get_height()
                                if yval > 0:
                                    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, f'{yval:.1f}', ha='center', va='bottom', fontsize=10, fontproperties=prop)
                            title_text = f"🌟 {view_as} 的专属学习周报 🌟\n"
                            summary_text = f"本周打卡：{days_count} 天 | 累计积分：{total_pts:.1f} 分 | 单日最高：{max_daily_score:.1f} 分"
                            if prop:
                                ax.set_title(title_text, fontproperties=prop, fontsize=18, pad=20, color='#333333', fontweight='bold')
                                fig.text(0.5, 0.88, summary_text, ha='center', fontsize=14, color='#666666', fontproperties=prop)
                                plt.xticks(fontproperties=prop)
                                plt.yticks(fontproperties=prop)
                            else:
                                ax.set_title(title_text, fontsize=18, pad=20, color='#333333', fontweight='bold')
                                fig.text(0.5, 0.88, summary_text, ha='center', fontsize=14, color='#666666')
                            plt.tight_layout(rect=[0, 0, 1, 0.85])
                            buf = io.BytesIO()
                            fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
                            buf.seek(0)
                            plt.close(fig)
                            st.image(buf, use_container_width=True)
                            st.download_button(
                                label="⬇️ 点击保存图片 (发送到微信群)",
                                data=buf,
                                file_name=f"{view_as}_周报_{start_date.isoformat()}.png",
                                mime="image/png",
                                **_stretch({"type": "secondary"})
                            )
                            st.success("图片已生成，点击上方按钮保存并发送给家长吧！")
                        except Exception as e:
                            st.error(f"生成图片失败：{e}")

            st.divider()
            time_view = st.radio("时间维度", ["按日查看", "按周查看", "按月查看"], horizontal=True)
            try: all_recs = db.execute("SELECT day, total_score FROM daily_records WHERE owner_id=? ORDER BY day ASC", (view_as,)).fetchall()
            except: all_recs = []
            if all_recs:
                df = pd.DataFrame([{"日期": r["day"], "总分": float(r["total_score"] or 0)} for r in all_recs])
                df["日期"] = pd.to_datetime(df["日期"])
                if time_view == "按日查看": df_grouped = df.copy(); x_title = "日期 (每日)"
                elif time_view == "按周查看": df_grouped = df.set_index("日期").resample('W-MON', label='left', closed='left').sum().reset_index(); x_title = "日期 (每周一)"
                else: df_grouped = df.set_index("日期").resample('MS').sum().reset_index(); x_title = "日期 (每月1日)"
                st.altair_chart(alt.Chart(df_grouped).mark_line(point=True, color='#1f77b4').encode(x=alt.X('日期:T', title=x_title, axis=alt.Axis(labelAngle=0)), y=alt.Y('总分:Q', title='总分', axis=alt.Axis(labelAngle=0)), tooltip=[alt.Tooltip('日期:T', format='%Y-%m-%d'), '总分:Q']).interactive(), use_container_width=True)
                st.altair_chart(alt.Chart(df_grouped).mark_bar().encode(x=alt.X('日期:T', title=x_title, axis=alt.Axis(labelAngle=0)), y=alt.Y('总分:Q', title='总分', axis=alt.Axis(labelAngle=0)), color=alt.Color('总分:Q', scale=alt.Scale(scheme='greens'), legend=None), tooltip=[alt.Tooltip('日期:T', format='%Y-%m-%d'), '总分:Q']), use_container_width=True)
            else: st.info("暂无数据。")

            st.divider(); st.subheader("历史打卡详情")
            try: days = [r["day"] for r in db.execute("SELECT day FROM daily_records WHERE owner_id=? ORDER BY day DESC", (view_as,)).fetchall()]
            except: days = []
            if days:
                sel = st.selectbox("选择日期", days)
                try:
                    row = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (sel, view_as)).fetchone()
                    st.write(f"**总分: {float(row['total_score'] or 0):.1f}** (基础 {float(row['base_score'] or 0):.1f} + Bonus {float(row['bonus_score'] or 0):.1f})")
                    done = json.loads(row["done_tasks"]) if row["done_tasks"] else []
                    st.write("完成项：", ", ".join([html.escape(task["name"]) for task in get_tasks(date.fromisoformat(sel).weekday(), view_as) if task["id"] in done]) or "无")
                except: pass
            else: st.info("暂无记录")

    # ============ 商城 ============
    if t("tab_shop") in tab_dict:
        with tab_dict[t("tab_shop")]:
            st.subheader(t("tab_shop"))
            try: shop_items = get_shop(view_as)
            except: shop_items = []
            if not shop_items: st.warning(t("shop_empty"))
            else:
                try: bal = get_balance(view_as)
                except: bal = {"balance": 0}
                for name, cost in shop_items:
                    c1, c2, c3 = st.columns([5, 2, 2])
                    c1.write(f"**{html.escape(name)}**"); c2.write(f"`{cost} {t('score_col')}`")
                    confirm_key = f"confirm_buy_{view_as}_{name}"
                    if st.session_state.get(confirm_key):
                        cc1, cc2 = st.columns(2)
                        if cc1.button(t("confirm_deduct"), key=f"yes_{view_as}_{name}", **_stretch({"type": "primary"})):
                            db.begin()
                            try:
                                q = "SELECT (SELECT COALESCE(SUM(total_score),0) FROM daily_records WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM period_bonus WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM exam_rewards WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM special_events WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM extra_points WHERE owner_id=?)-(SELECT COALESCE(SUM(cost),0) FROM redemptions WHERE owner_id=?) AS bal"
                                row = db.execute(q, (view_as, view_as, view_as, view_as, view_as, view_as)).fetchone()
                                curr_bal = float(row["bal"] or 0)
                                if curr_bal < cost:
                                    db.end(); st.error(t("points_insufficient"))
                                else:
                                    db.execute("INSERT INTO redemptions (owner_id, item, cost, ts) VALUES (?,?,?,?)", (view_as, name, cost, now.isoformat()))
                                    if name == "补签卡": db.execute("UPDATE users SET makeup_cards = makeup_cards + 1 WHERE username=?", (view_as,))
                                    db.commit(); db.end()
                                    st.session_state[confirm_key] = False; st.cache_data.clear(); st.success(t("redeem_ok")); st.rerun()
                            except Exception as e:
                                db.rollback(); db.end(); st.error(f"兑换失败：{str(e)}")
                        if cc2.button(t("cancel") if "cancel" in LANG_PACKS[get_lang()] else "取消", key=f"no_{view_as}_{name}", **_stretch({})):
                            st.session_state[confirm_key] = False; st.rerun()
                    else:
                        if c3.button(t("redeem_btn"), key=f"buy_{view_as}_{name}", disabled=(bal["balance"] < cost), **_stretch({})):
                            st.session_state[confirm_key] = True; st.rerun()

    # ============ 兑换 ============
    if t("tab_redeem") in tab_dict:
        with tab_dict[t("tab_redeem")]:
            st.subheader(t("redeem_history"))
            try: rows = db.execute("SELECT * FROM redemptions WHERE owner_id=? ORDER BY id DESC", (view_as,)).fetchall()
            except: rows = []
            if rows: st.dataframe([{"时间": r["ts"], "奖励": html.escape(r["item"]), "消耗": float(r["cost"] or 0)} for r in rows], use_container_width=True)
            else: st.info(t("none_yet"))

    # ============ 考试 ============
    if t("tab_exam") in tab_dict:
        with tab_dict[t("tab_exam")]:
            st.subheader("考试专项")
            try: exam_config, _ = get_exam_config(view_as)
            except: exam_config = {}
            if not exam_config: st.warning("未设置考试科目！")
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
                for ln in lines: st.write(ln)
                if st.button("保存本次成绩", **_stretch({"type": "primary"})):
                    try:
                        detail_text = f"达成 {hit_count} 门 | " + "/".join([f"{k}:{v}" for k, v in scores.items()])
                        db.execute("INSERT INTO exam_rewards (owner_id, detail, points, ts) VALUES (?,?,?,?)", (view_as, detail_text, total_pts, now.isoformat()))
                        db.commit(); st.cache_data.clear(); st.success("已保存！"); st.rerun()
                    except RuntimeError as e: st.error(str(e))

    # ============ 事件 ============
    if t("tab_event") in tab_dict:
        with tab_dict[t("tab_event")]:
            st.subheader("特殊事件")
            try: fired = db.execute("SELECT * FROM special_events WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)).fetchone()
            except: fired = None
            if fired: st.info(f"今天已经触发过啦：{html.escape(fired['note'])} +{float(fired['points'] or 0)}分")
            else:
                if st.session_state.get("confirm_roll"):
                    st.warning("🎲 确认消耗今天的机会摇一摇吗？")
                    rc1, rc2 = st.columns(2)
                    if rc1.button("确认摇一摇", **_stretch({"type": "primary"})):
                        try:
                            roll = random.random()
                            pts = random.randint(1, 2) if roll < 0.4 else random.randint(3, 5) if roll < 0.8 else random.randint(6, 8) if roll < 0.95 else random.randint(10, 15)
                            db.execute("INSERT INTO special_events (day, owner_id, points, note, ts) VALUES (?,?,?,?,?)", (view_today.isoformat(), view_as, pts, "积分暴击", now.isoformat()))
                            db.commit(); st.session_state["confirm_roll"] = False; st.cache_data.clear(); st.balloons(); st.success(f"获得 {pts} 积分！"); st.rerun()
                        except RuntimeError as e: st.error(str(e))
                    if rc2.button("取消", **_stretch({})): st.session_state["confirm_roll"] = False; st.rerun()
                else:
                    if st.button("摇一摇", **_stretch({})): st.session_state["confirm_roll"] = True; st.rerun()

    # ============ 系统设置 ============
    if t("tab_settings") in tab_dict:
        with tab_dict[t("tab_settings")]:
            st.subheader("系统设置")
            role_names = {"admin": t("role_admin"), "host": t("role_host"), "user": t("role_user"), "solo": t("role_solo")}
            if view_as == current_user: st.info(f"当前正在配置：**{html.escape(view_as)}**（你自己）")
            else: st.info(f"当前正在配置：**{html.escape(view_as)}**（身份：{role_names.get(view_role, view_role)}）")

            # ---- 1. 修改每日任务 ----
            st.markdown("### 1. 修改每日任务")
            sel_wd = st.selectbox("选择要修改的星期", range(7), format_func=lambda x: WEEKDAY_CN[x])
            try: tasks_list = db.execute("SELECT * FROM config_tasks WHERE weekday=? AND owner_id=? ORDER BY category ASC, name ASC", (sel_wd, view_as)).fetchall()
            except: tasks_list = []

            edit_mode_key = f"task_edit_mode_{view_as}_{sel_wd}"
            if edit_mode_key not in st.session_state: st.session_state[edit_mode_key] = False
            header_cols = st.columns([3, 1])
            header_cols[0].markdown(f"**{WEEKDAY_CN[sel_wd]} 当前任务（共 {len(tasks_list)} 项）**")
            if header_cols[1].button("完成编辑" if st.session_state[edit_mode_key] else "✏️ 编辑", key=f"toggle_edit_{view_as}_{sel_wd}"):
                st.session_state[edit_mode_key] = not st.session_state[edit_mode_key]; st.rerun()

            selected_task_ids = []
            if tasks_list:
                for task in tasks_list:
                    if st.session_state[edit_mode_key]:
                        c1, c2, c3, c4 = st.columns([1, 2, 4, 2])
                        if c1.checkbox("", key=f"chk_{view_as}_{sel_wd}_{task['id']}", label_visibility="collapsed"): selected_task_ids.append(task["id"])
                        c2.write(f"`{html.escape(str(task.get('category') or ''))}`"); c3.write(f"**{html.escape(str(task['name']))}**"); c4.write(f"{float(task['points'] or 0)} 分")
                    else:
                        c1, c2, c3 = st.columns([2, 4, 2])
                        c1.write(f"`{html.escape(str(task.get('category') or ''))}`"); c2.write(f"**{html.escape(str(task['name']))}**"); c3.write(f"{float(task['points'] or 0)} 分")
                if st.session_state[edit_mode_key]:
                    st.divider()
                    if selected_task_ids:
                        st.write(f"已选中 **{len(selected_task_ids)}** 项")
                        ac1, ac2, ac3 = st.columns(3)
                        if len(selected_task_ids) == 1:
                            with ac1:
                                if st.button("✏️ 编辑选中任务", **_stretch({})): st.session_state[f"editing_task_id_{view_as}_{sel_wd}"] = selected_task_ids[0]
                        with ac2:
                            if st.button("🗑 删除选中任务", **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    placeholders = ",".join(["?"] * len(selected_task_ids))
                                    db.execute(f"DELETE FROM config_tasks WHERE id IN ({placeholders}) AND owner_id=?", (*selected_task_ids, view_as))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("批量删除成功！"); st.rerun()
                                except Exception as e: db.rollback(); db.end(); st.error(f"删除失败：{e}")
                        with ac3:
                            if st.button("🔄 同步到其他星期", **_stretch({})): st.session_state[f"syncing_tasks_{view_as}_{sel_wd}"] = selected_task_ids

                        edit_task_id = st.session_state.get(f"editing_task_id_{view_as}_{sel_wd}")
                        if edit_task_id:
                            t_to_edit = next((x for x in tasks_list if x["id"] == edit_task_id), None)
                            if t_to_edit:
                                st.info(f"正在编辑：{t_to_edit['name']}")
                                with st.form(f"edit_task_form_{view_as}_{sel_wd}_{edit_task_id}"):
                                    ec1, ec2, ec3 = st.columns([2, 3, 2])
                                    e_cat = ec1.text_input("分类", value=t_to_edit["category"] or "", key=f"ec_{edit_task_id}")
                                    e_name = ec2.text_input("任务名称", value=t_to_edit["name"], key=f"en_{edit_task_id}")
                                    e_pts = ec3.text_input("分数", value=str(t_to_edit["points"]), key=f"ep_{edit_task_id}")
                                    col_save, col_cancel = st.columns(2)
                                    if col_save.form_submit_button("保存修改", type="primary", use_container_width=True):
                                        if not e_name.strip(): st.error("任务名称不能为空")
                                        else:
                                            try:
                                                pts_val = float(e_pts.strip() or "0")
                                                db.execute("UPDATE config_tasks SET category=?, name=?, points=? WHERE id=? AND owner_id=?", (e_cat.strip(), e_name.strip(), pts_val, edit_task_id, view_as))
                                                db.commit(); st.cache_data.clear(); st.session_state.pop(f"editing_task_id_{view_as}_{sel_wd}", None); st.success("任务已更新！"); st.rerun()
                                            except ValueError: st.error("分数必须为数字")
                                            except RuntimeError as ex: st.error(str(ex))
                                    if col_cancel.form_submit_button("取消编辑", use_container_width=True): st.session_state.pop(f"editing_task_id_{view_as}_{sel_wd}", None); st.rerun()

                        syncing_ids = st.session_state.get(f"syncing_tasks_{view_as}_{sel_wd}")
                        if syncing_ids:
                            st.info(f"将选中的 {len(syncing_ids)} 个任务同步到以下星期：")
                            with st.form(f"sync_tasks_form_{view_as}_{sel_wd}"):
                                target_days = []
                                scols = st.columns(7)
                                for i in range(7):
                                    if i != sel_wd:
                                        if scols[i].checkbox(WEEKDAY_CN[i], key=f"sync_day_{view_as}_{sel_wd}_{i}"): target_days.append(i)
                                    else: scols[i].caption("当前星期")
                                if st.form_submit_button("确认同步", type="primary", use_container_width=True):
                                    if not target_days: st.warning("请至少选择一个目标星期")
                                    else:
                                        db.begin()
                                        try:
                                            tasks_to_sync = [x for x in tasks_list if x["id"] in syncing_ids]
                                            for target_wd in target_days:
                                                for task in tasks_to_sync:
                                                    new_id = uuid.uuid4().hex
                                                    db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?) ON CONFLICT (owner_id, weekday, category, name) DO NOTHING", (new_id, target_wd, view_as, task["category"], task["name"], task["points"]))
                                            db.commit(); db.end(); st.cache_data.clear(); st.success("任务同步成功！"); st.session_state.pop(f"syncing_tasks_{view_as}_{sel_wd}", None); st.rerun()
                                        except Exception as ex: db.rollback(); db.end(); st.error(f"同步失败：{ex}")
                            if st.button("取消同步", key=f"cancel_sync_{view_as}_{sel_wd}"): st.session_state.pop(f"syncing_tasks_{view_as}_{sel_wd}", None); st.rerun()
                    else: st.caption("请勾选任务以进行编辑、删除或同步操作。")
            else: st.caption("当前星期暂无任务。")

            with st.form(f"add_task_form_{view_as}_{sel_wd}", clear_on_submit=True):
                st.markdown("**➕ 新增任务**")
                tc1, tc2, tc3 = st.columns([2, 3, 2])
                new_cat = tc1.text_input("分类", placeholder="如：校内", key=f"new_task_cat_{view_as}_{sel_wd}")
                new_name = tc2.text_input("任务名称", placeholder="如：背单词", key=f"new_task_name_{view_as}_{sel_wd}")
                new_pts_str = tc3.text_input("分数", placeholder="如：2", key=f"new_task_pts_{view_as}_{sel_wd}")
                if _submit("➕ 添加任务", **_stretch({"type": "primary"})):
                    if not new_name.strip(): st.error("任务名称不能为空")
                    else:
                        pts_val = None
                        try: pts_val = float((new_pts_str or "0").strip() or "0")
                        except ValueError: st.error("分数必须为数字")
                        if pts_val is not None:
                            try:
                                task_id = uuid.uuid4().hex
                                db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (task_id, sel_wd, view_as, new_cat.strip(), new_name.strip(), float(pts_val)))
                                db.commit(); st.cache_data.clear(); st.success("任务已添加！"); st.rerun()
                            except RuntimeError as e: st.error(str(e))

            # ---- 2. 修改商城奖励 ----
            st.divider(); st.markdown("### 2. 修改商城奖励")
            try: shop_list = db.execute("SELECT * FROM config_shop WHERE owner_id=? ORDER BY id ASC", (view_as,)).fetchall()
            except: shop_list = []
            edit_shop_key = f"shop_edit_mode_{view_as}"
            if edit_shop_key not in st.session_state: st.session_state[edit_shop_key] = False
            header_cols = st.columns([3, 1])
            header_cols[0].markdown(f"**商城奖励（共 {len(shop_list)} 项）**")
            if header_cols[1].button("完成编辑" if st.session_state[edit_shop_key] else "✏️ 编辑", key=f"toggle_edit_shop_{view_as}"):
                st.session_state[edit_shop_key] = not st.session_state[edit_shop_key]; st.rerun()
            selected_shop_ids = []
            if shop_list:
                for s in shop_list:
                    if st.session_state[edit_shop_key]:
                        c1, c2, c3 = st.columns([1, 5, 2])
                        if c1.checkbox("", key=f"chk_shop_{view_as}_{s['id']}", label_visibility="collapsed"): selected_shop_ids.append(s["id"])
                        c2.write(f"**{html.escape(str(s['name']))}**"); c3.write(f"{float(s['cost'] or 0)} 分")
                    else:
                        c1, c2 = st.columns([5, 2])
                        c1.write(f"**{html.escape(str(s['name']))}**"); c2.write(f"{float(s['cost'] or 0)} 分")
                if st.session_state[edit_shop_key]:
                    st.divider()
                    if selected_shop_ids:
                        st.write(f"已选中 **{len(selected_shop_ids)}** 项")
                        ac1, ac2 = st.columns(2)
                        if len(selected_shop_ids) == 1:
                            with ac1:
                                if st.button("✏️ 编辑选中奖励", key=f"edit_shop_btn_{view_as}"): st.session_state[f"editing_shop_id_{view_as}"] = selected_shop_ids[0]
                        with ac2:
                            if st.button("🗑 删除选中奖励", key=f"del_shop_btn_{view_as}", **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    placeholders = ",".join(["?"] * len(selected_shop_ids))
                                    db.execute(f"DELETE FROM config_shop WHERE id IN ({placeholders}) AND owner_id=?", (*selected_shop_ids, view_as))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("批量删除成功！"); st.rerun()
                                except Exception as e: db.rollback(); db.end(); st.error(f"删除失败：{e}")
                        edit_shop_id = st.session_state.get(f"editing_shop_id_{view_as}")
                        if edit_shop_id:
                            s_to_edit = next((x for x in shop_list if x["id"] == edit_shop_id), None)
                            if s_to_edit:
                                st.info(f"正在编辑奖励：{s_to_edit['name']}")
                                with st.form(f"edit_shop_form_{view_as}_{edit_shop_id}"):
                                    ec1, ec2 = st.columns(2)
                                    e_name = ec1.text_input("奖励名称", value=s_to_edit["name"], key=f"es_name_{edit_shop_id}")
                                    e_cost = ec2.text_input("所需积分", value=str(s_to_edit["cost"]), key=f"es_cost_{edit_shop_id}")
                                    col_save, col_cancel = st.columns(2)
                                    if col_save.form_submit_button("保存修改", type="primary", use_container_width=True):
                                        if not e_name.strip(): st.error("名称不能为空")
                                        else:
                                            try:
                                                c_val = float(e_cost.strip() or "0")
                                                db.execute("UPDATE config_shop SET name=?, cost=? WHERE id=? AND owner_id=?", (e_name.strip(), c_val, edit_shop_id, view_as))
                                                db.commit(); st.cache_data.clear(); st.session_state.pop(f"editing_shop_id_{view_as}", None); st.success("奖励已更新！"); st.rerun()
                                            except ValueError: st.error("积分必须为数字")
                                            except RuntimeError as ex: st.error(str(ex))
                                    if col_cancel.form_submit_button("取消编辑", use_container_width=True): st.session_state.pop(f"editing_shop_id_{view_as}", None); st.rerun()
                    else: st.caption("请勾选奖励以进行编辑或删除操作。")
            else: st.caption("暂无商城奖励。")

            with st.form(f"add_shop_form_{view_as}", clear_on_submit=True):
                st.markdown("**➕ 新增奖励**")
                sc1, sc2 = st.columns([3, 2])
                new_shop_name = sc1.text_input("奖励名称", placeholder="如：专属夸夸", key=f"new_shop_name_{view_as}")
                new_shop_cost_str = sc2.text_input("所需积分", placeholder="如：5", key=f"new_shop_cost_{view_as}")
                if _submit("➕ 添加奖励", **_stretch({"type": "primary"})):
                    if not new_shop_name.strip(): st.error("奖励名称不能为空")
                    else:
                        cost_val = None
                        try: cost_val = float((new_shop_cost_str or "0").strip() or "0")
                        except ValueError: st.error("所需积分必须为数字")
                        if cost_val is not None:
                            try: db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (view_as, new_shop_name.strip(), float(cost_val))); db.commit(); st.cache_data.clear(); st.success("奖励已添加！"); st.rerun()
                            except RuntimeError as e: st.error(str(e))

            # ---- 3. 修改考试科目 ----
            st.divider(); st.markdown("### 3. 修改考试科目")
            try: exam_config, exam_rules = get_exam_config(view_as)
            except: exam_config = {}
            edit_exam_key = f"exam_edit_mode_{view_as}"
            if edit_exam_key not in st.session_state: st.session_state[edit_exam_key] = False
            header_cols = st.columns([3, 1])
            header_cols[0].markdown(f"**考试科目（共 {len(exam_config)} 项）**")
            if header_cols[1].button("完成编辑" if st.session_state[edit_exam_key] else "✏️ 编辑", key=f"toggle_edit_exam_{view_as}"):
                st.session_state[edit_exam_key] = not st.session_state[edit_exam_key]; st.rerun()
            selected_exam_subs = []
            if exam_config:
                for sub, cfg in exam_config.items():
                    if st.session_state[edit_exam_key]:
                        c1, c2, c3, c4 = st.columns([1, 2, 4, 2])
                        if c1.checkbox("", key=f"chk_exam_{view_as}_{sub}", label_visibility="collapsed"): selected_exam_subs.append(sub)
                        c2.write(f"**{html.escape(str(sub))}**")
                        if cfg.get("type") == "score": c3.write(f"分数制 | 满分 {cfg.get('max_score', 150)} | 目标 {cfg.get('target')}")
                        else: c3.write(f"等级制 | 目标 {cfg.get('target')}")
                        c4.write(f"单档 {cfg.get('step_points', 0)} 分")
                    else:
                        c1, c2, c3 = st.columns([2, 5, 2])
                        c1.write(f"**{html.escape(str(sub))}**")
                        if cfg.get("type") == "score": c2.write(f"分数制 | 满分 {cfg.get('max_score', 150)} | 目标 {cfg.get('target')}")
                        else: c2.write(f"等级制 | 目标 {cfg.get('target')}")
                        c3.write(f"单档 {cfg.get('step_points', 0)} 分")
                if st.session_state[edit_exam_key]:
                    st.divider()
                    if selected_exam_subs:
                        st.write(f"已选中 **{len(selected_exam_subs)}** 项")
                        ac1, ac2 = st.columns(2)
                        if len(selected_exam_subs) == 1:
                            with ac1:
                                if st.button("✏️ 编辑选中科目", key=f"edit_exam_btn_{view_as}"): st.session_state[f"editing_exam_sub_{view_as}"] = selected_exam_subs[0]
                        with ac2:
                            if st.button("🗑 删除选中科目", key=f"del_exam_btn_{view_as}", **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    placeholders = ",".join(["?"] * len(selected_exam_subs))
                                    db.execute(f"DELETE FROM config_exam WHERE subject IN ({placeholders}) AND owner_id=?", (*selected_exam_subs, view_as))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("批量删除成功！"); st.rerun()
                                except Exception as e: db.rollback(); db.end(); st.error(f"删除失败：{e}")
                        edit_sub = st.session_state.get(f"editing_exam_sub_{view_as}")
                        if edit_sub and edit_sub in exam_config:
                            cfg = exam_config[edit_sub]
                            st.info(f"正在编辑科目：{edit_sub}")
                            with st.form(f"edit_exam_form_{view_as}_{edit_sub}"):
                                ec1, ec2, ec3 = st.columns(3)
                                e_sub = ec1.text_input("科目名称", value=edit_sub, key=f"e_sub_{edit_sub}")
                                e_type = ec2.selectbox("类型", ["score", "grade"], index=0 if cfg.get("type")=="score" else 1, format_func=lambda x: "分数制" if x=="score" else "等级制")
                                e_target = ec3.text_input("目标 (分数或等级)", value=str(cfg.get("target", "")), key=f"e_tgt_{edit_sub}")
                                ec4, ec5, ec6 = st.columns(3)
                                e_max = ec4.text_input("满分 (仅分数制)", value=str(cfg.get("max_score", "150")), key=f"e_max_{edit_sub}")
                                e_step = ec5.text_input("分差 (仅分数制)", value=str(cfg.get("step", "0")), key=f"e_step_{edit_sub}")
                                e_pts = ec6.text_input("单档奖励", value=str(cfg.get("step_points", "0")), key=f"e_pts_{edit_sub}")
                                col_save, col_cancel = st.columns(2)
                                if col_save.form_submit_button("保存修改", type="primary", use_container_width=True):
                                    if not e_sub.strip() or not e_target.strip(): st.error("科目名称和目标不能为空")
                                    else:
                                        try:
                                            pts_v = float(e_pts.strip() or "0")
                                            if e_type == "score": cfg_new = {"type": "score", "max_score": float(e_max.strip() or "150"), "target": float(e_target.strip()), "step": float(e_step.strip() or "0"), "step_points": pts_v}
                                            else: cfg_new = {"type": "grade", "target": e_target.strip(), "step_points": pts_v}
                                            if e_sub.strip() != edit_sub:
                                                if db.execute("SELECT 1 FROM config_exam WHERE subject=? AND owner_id=?", (e_sub.strip(), view_as)).fetchone(): st.error("新科目名称已存在"); st.stop()
                                            db.execute("DELETE FROM config_exam WHERE subject=? AND owner_id=?", (edit_sub, view_as))
                                            db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (e_sub.strip(), view_as, json.dumps(cfg_new)))
                                            db.commit(); st.cache_data.clear(); st.session_state.pop(f"editing_exam_sub_{view_as}", None); st.success("科目已更新！"); st.rerun()
                                        except ValueError: st.error("分数/目标必须为数字")
                                        except RuntimeError as ex: st.error(str(ex))
                                if col_cancel.form_submit_button("取消编辑", use_container_width=True): st.session_state.pop(f"editing_exam_sub_{view_as}", None); st.rerun()
                    else: st.caption("请勾选科目以进行编辑或删除操作。")
            else: st.caption("暂无考试科目。")

            st.markdown("**➕ 新增科目**")
            exam_type_choice = st.radio("选择类型", ["score", "grade"], format_func=lambda x: "分数制" if x == "score" else "等级制", horizontal=True, key=f"new_exam_type_{view_as}")
            if exam_type_choice == "score":
                with st.form(f"add_exam_score_form_{view_as}", clear_on_submit=True):
                    ec1, ec2, ec3 = st.columns(3)
                    new_exam_sub = ec1.text_input("科目名称", placeholder="如：语文", key=f"new_exam_sub_s_{view_as}")
                    new_exam_max_str = ec2.text_input("满分", placeholder="如：150", key=f"new_exam_max_{view_as}")
                    new_exam_target_str = ec3.text_input("目标分数", placeholder="如：105", key=f"new_exam_target_{view_as}")
                    ec4, ec5 = st.columns(2)
                    new_exam_step_str = ec4.text_input("分差", placeholder="如：3", key=f"new_exam_step_{view_as}")
                    new_exam_step_pts_str = ec5.text_input("单档奖励", placeholder="如：2", key=f"new_exam_step_pts_{view_as}")
                    if _submit("➕ 添加科目", **_stretch({"type": "primary"})):
                        if not new_exam_sub.strip(): st.error("科目名称不能为空")
                        else:
                            try:
                                max_val = float((new_exam_max_str or "150").strip() or "150")
                                target_val = float((new_exam_target_str or "").strip())
                                step_val = float((new_exam_step_str or "0").strip() or "0")
                                step_pts_val = float((new_exam_step_pts_str or "0").strip() or "0")
                            except ValueError: st.error("满分/目标/分差/单档奖励必须为数字")
                            else:
                                try:
                                    if db.execute("SELECT * FROM config_exam WHERE subject=? AND owner_id=?", (new_exam_sub.strip(), view_as)).fetchone(): st.warning("该科目已存在，请先删除旧配置。")
                                    else:
                                        cfg = {"type": "score", "max_score": max_val, "target": target_val, "step": step_val, "step_points": step_pts_val}
                                        db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (new_exam_sub.strip(), view_as, json.dumps(cfg)))
                                        db.commit(); st.cache_data.clear(); st.success("科目已添加！"); st.rerun()
                                except RuntimeError as e: st.error(str(e))
            else:
                with st.form(f"add_exam_grade_form_{view_as}", clear_on_submit=True):
                    ec1, ec2, ec3 = st.columns([3, 3, 2])
                    new_exam_sub = ec1.text_input("科目名称", placeholder="如：语文", key=f"new_exam_sub_g_{view_as}")
                    new_exam_target = ec2.selectbox("目标等级", GRADES, key=f"new_exam_target_g_{view_as}")
                    new_exam_step_pts_str = ec3.text_input("单档奖励", placeholder="如：2", key=f"new_exam_step_pts_g_{view_as}")
                    if _submit("➕ 添加科目", **_stretch({"type": "primary"})):
                        if not new_exam_sub.strip(): st.error("科目名称不能为空")
                        else:
                            try: step_pts_val = float((new_exam_step_pts_str or "0").strip() or "0")
                            except ValueError: st.error("单档奖励必须为数字")
                            else:
                                try:
                                    if db.execute("SELECT * FROM config_exam WHERE subject=? AND owner_id=?", (new_exam_sub.strip(), view_as)).fetchone(): st.warning("该科目已存在，请先删除旧配置。")
                                    else:
                                        cfg = {"type": "grade", "target": new_exam_target, "step_points": step_pts_val}
                                        db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (new_exam_sub.strip(), view_as, json.dumps(cfg)))
                                        db.commit(); st.cache_data.clear(); st.success("科目已添加！"); st.rerun()
                                except RuntimeError as e: st.error(str(e))

            # ---- 4. 修改多科达成奖励 ----
            st.divider(); st.markdown("### 4. 修改多科达成奖励")
            try: mh_list = get_exam_multihit(view_as)
            except: mh_list = []
            edit_mh_key = f"mh_edit_mode_{view_as}"
            if edit_mh_key not in st.session_state: st.session_state[edit_mh_key] = False
            header_cols = st.columns([3, 1])
            header_cols[0].markdown(f"**多科奖励（共 {len(mh_list)} 项）**")
            if header_cols[1].button("完成编辑" if st.session_state[edit_mh_key] else "✏️ 编辑", key=f"toggle_edit_mh_{view_as}"):
                st.session_state[edit_mh_key] = not st.session_state[edit_mh_key]; st.rerun()
            selected_mh_counts = []
            if mh_list:
                for mh in mh_list:
                    if st.session_state[edit_mh_key]:
                        c1, c2, c3 = st.columns([1, 4, 3])
                        if c1.checkbox("", key=f"chk_mh_{view_as}_{mh['hit_count']}", label_visibility="collapsed"): selected_mh_counts.append(mh["hit_count"])
                        c2.write(f"达成 **{mh['hit_count']}** 门及以上"); c3.write(f"+{mh['points']} 分")
                    else:
                        c1, c2 = st.columns([4, 3])
                        c1.write(f"达成 **{mh['hit_count']}** 门及以上"); c2.write(f"+{mh['points']} 分")
                if st.session_state[edit_mh_key]:
                    st.divider()
                    if selected_mh_counts:
                        st.write(f"已选中 **{len(selected_mh_counts)}** 项")
                        ac1, ac2 = st.columns(2)
                        if len(selected_mh_counts) == 1:
                            with ac1:
                                if st.button("✏️ 编辑选中档位", key=f"edit_mh_btn_{view_as}"): st.session_state[f"editing_mh_count_{view_as}"] = selected_mh_counts[0]
                        with ac2:
                            if st.button("🗑 删除选中档位", key=f"del_mh_btn_{view_as}", **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    placeholders = ",".join(["?"] * len(selected_mh_counts))
                                    db.execute(f"DELETE FROM config_exam_multihit WHERE hit_count IN ({placeholders}) AND owner_id=?", (*selected_mh_counts, view_as))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("批量删除成功！"); st.rerun()
                                except Exception as e: db.rollback(); db.end(); st.error(f"删除失败：{e}")
                        edit_mh_count = st.session_state.get(f"editing_mh_count_{view_as}")
                        if edit_mh_count:
                            mh_to_edit = next((x for x in mh_list if x["hit_count"] == edit_mh_count), None)
                            if mh_to_edit:
                                st.info(f"正在编辑：达成 {edit_mh_count} 门奖励")
                                with st.form(f"edit_mh_form_{view_as}_{edit_mh_count}"):
                                    ec1, ec2 = st.columns(2)
                                    e_count = ec1.text_input("达成科目数", value=str(mh_to_edit["hit_count"]), key=f"emc_{edit_mh_count}")
                                    e_pts = ec2.text_input("奖励分数", value=str(mh_to_edit["points"]), key=f"emp_{edit_mh_count}")
                                    col_save, col_cancel = st.columns(2)
                                    if col_save.form_submit_button("保存修改", type="primary", use_container_width=True):
                                        try:
                                            c_val = int(e_count.strip()); p_val = float(e_pts.strip())
                                            if c_val < 1: st.error("科目数必须≥1")
                                            elif c_val != edit_mh_count and db.execute("SELECT 1 FROM config_exam_multihit WHERE hit_count=? AND owner_id=?", (c_val, view_as)).fetchone(): st.error("该达成科目数已存在")
                                            else:
                                                db.execute("DELETE FROM config_exam_multihit WHERE hit_count=? AND owner_id=?", (edit_mh_count, view_as))
                                                db.execute("INSERT INTO config_exam_multihit (hit_count, owner_id, points) VALUES (?,?,?)", (c_val, view_as, p_val))
                                                db.commit(); st.cache_data.clear(); st.session_state.pop(f"editing_mh_count_{view_as}", None); st.success("档位已更新！"); st.rerun()
                                        except ValueError: st.error("科目数和奖励分数必须为数字")
                                        except RuntimeError as ex: st.error(str(ex))
                                    if col_cancel.form_submit_button("取消编辑", use_container_width=True): st.session_state.pop(f"editing_mh_count_{view_as}", None); st.rerun()
                    else: st.caption("请勾选档位以进行编辑或删除操作。")
            else: st.caption("暂无多科达成奖励配置。")

            with st.form(f"add_mh_form_{view_as}", clear_on_submit=True):
                st.markdown("**➕ 新增多科奖励档位**")
                mc1, mc2 = st.columns(2)
                new_mh_count_str = mc1.text_input("达成科目数", placeholder="如：3", key=f"new_mh_count_{view_as}")
                new_mh_pts_str = mc2.text_input("奖励分数", placeholder="如：2", key=f"new_mh_pts_{view_as}")
                if _submit("➕ 添加档位", **_stretch({"type": "primary"})):
                    try: count_val = int((new_mh_count_str or "").strip()); pts_val = float((new_mh_pts_str or "0").strip() or "0")
                    except ValueError: st.error("达成科目数必须为整数，奖励分数必须为数字")
                    else:
                        if count_val < 1: st.error("达成科目数必须 ≥ 1")
                        else:
                            try:
                                if db.execute("SELECT * FROM config_exam_multihit WHERE hit_count=? AND owner_id=?", (count_val, view_as)).fetchone(): st.warning("该达成科目数已存在，请先删除旧配置。")
                                else: db.execute("INSERT INTO config_exam_multihit (hit_count, owner_id, points) VALUES (?,?,?)", (count_val, view_as, float(pts_val))); db.commit(); st.cache_data.clear(); st.success("档位已添加！"); st.rerun()
                            except RuntimeError as e: st.error(str(e))

            # ---- 5. 修改阈值与 Bonus 规则 ----
            st.divider(); st.markdown("### 5. 修改阈值与 Bonus 规则（阈值与 Bonus 规则下次打卡时生效）")
            try: thresholds = get_thresholds(view_as); bonus_rules = get_bonus_rules(view_as)
            except: thresholds = {}; bonus_rules = DEFAULT_BONUS_RULES
            with st.form(f"bonus_form_{view_as}"):
                t_cols = st.columns(7); t_inputs = {}
                for i in range(7):
                    with t_cols[i]:
                        st.markdown(f"**{WEEKDAY_CN[i]}**")
                        t_inputs[i] = {"basic": st.number_input("基本", value=float(thresholds.get(i, {"basic": 0})["basic"]), key=f"th_b_{view_as}_{i}"), "full": st.number_input("满分", value=float(thresholds.get(i, {"full": 0})["full"]), key=f"th_f_{view_as}_{i}")}
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
                if _submit("保存新规则 (下次打卡时生效)", **_stretch({"type": "primary"})):
                    try:
                        for i in range(7):
                            db.execute("DELETE FROM config_thresholds WHERE weekday=? AND owner_id=?", (i, view_as))
                            db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)', (i, view_as, t_inputs[i]["basic"], t_inputs[i]["full"]))
                        new_bonus = {
                            "weekday": {"single": {"points": wd_single, "full_points": wd_single_full}, "streak2": {"points": wd_2, "full_points": wd_2_full}, "streak4": {"points": wd_4, "full_points": wd_4_full}},
                            "weekend": {"single": {"points": we_single, "full_points": we_single_full}},
                            "longterm": {"week_basic": lt_wb, "week_full": lt_wf, "month_basic": lt_mb, "month_full": lt_mf, "week_flex_perfect_deduct": flex_p, "week_flex_basic_deduct": flex_b}
                        }
                        db.execute("DELETE FROM config_bonus_rules WHERE owner_id=?", (view_as,))
                        db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (view_as, json.dumps(new_bonus)))
                        db.commit(); st.cache_data.clear(); st.success("✅ 新规则已保存，下次打卡时生效。"); st.rerun()
                    except RuntimeError as e: st.error(str(e))

            # ---- 6. 全局徽章配置 ----
            st.divider(); st.markdown("### 6. 全局徽章配置与 AI 生成")
            if view_role == "admin":
                with st.form("add_badge_form"):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    b_name = c1.text_input("徽章名称", placeholder="如：持之以恒")
                    b_type = c2.selectbox("达成条件", options=["days", "points", "perfect", "exam_hits"], format_func=lambda x: {"days": "累计打卡天数", "points": "累计赚取积分", "perfect": "完美周/月次数", "exam_hits": "单次考试达成科目数"}.get(x, x))
                    b_val = c3.number_input("达成数值", min_value=1.0, step=1.0)
                    if _submit("✨ AI 生成并添加", **_stretch({"type": "primary"})):
                        if b_name:
                            try:
                                seed = random.randint(1, 99999)
                                prompt = f"Minimalist flat vector icon for '{b_name}', clean simple design, ui app icon, no text, white background, not exaggerated."
                                icon_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=256&height=256&nologo=true&seed={seed}"
                                db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)", (b_name, b_type, b_val, icon_url))
                                db.commit(); st.cache_data.clear(); st.success(f"徽章「{html.escape(b_name)}」已生成！"); st.rerun()
                            except RuntimeError as e: st.error(str(e))
                st.markdown("**当前全局已配置的徽章：**")
                try: existing_badges = get_badge_configs()
                except: existing_badges = []
                edit_badge_key = "badge_edit_mode"
                if edit_badge_key not in st.session_state: st.session_state[edit_badge_key] = False
                header_cols = st.columns([3, 1])
                header_cols[0].markdown(f"**已配置徽章（共 {len(existing_badges)} 项）**")
                if header_cols[1].button("完成编辑" if st.session_state[edit_badge_key] else "✏️ 编辑", key="toggle_edit_badge"):
                    st.session_state[edit_badge_key] = not st.session_state[edit_badge_key]; st.rerun()
                selected_badge_ids = []
                if existing_badges:
                    for b in existing_badges:
                        if st.session_state[edit_badge_key]:
                            c1, c2, c3, c4 = st.columns([1, 2, 5, 2])
                            if c1.checkbox("", key=f"chk_badge_{b['id']}", label_visibility="collapsed"): selected_badge_ids.append(b["id"])
                            with c2: st.markdown(f'<img src="{html.escape(b["icon_url"] or "", quote=True)}" width="40" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'">', unsafe_allow_html=True)
                            c3.write(f"**{html.escape(b['name'])}**")
                            type_cn = {"days": "打卡天数", "points": "累计积分", "perfect": "完美次数", "exam_hits": "单次考试达科目数"}.get(b["cond_type"], b["cond_type"])
                            c4.write(f"条件：{type_cn} ≥ {b['cond_val']}")
                        else:
                            c1, c2, c3 = st.columns([2, 5, 2])
                            with c1: st.markdown(f'<img src="{html.escape(b["icon_url"] or "", quote=True)}" width="50" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'">', unsafe_allow_html=True)
                            c2.write(f"**{html.escape(b['name'])}**")
                            type_cn = {"days": "打卡天数", "points": "累计积分", "perfect": "完美次数", "exam_hits": "单次考试达科目数"}.get(b["cond_type"], b["cond_type"])
                            c3.write(f"条件：{type_cn} ≥ {b['cond_val']}")
                    if st.session_state[edit_badge_key]:
                        st.divider()
                        if selected_badge_ids:
                            st.write(f"已选中 **{len(selected_badge_ids)}** 项")
                            if st.button("🗑 删除选中徽章", key="del_badge_btn", **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    placeholders = ",".join(["?"] * len(selected_badge_ids))
                                    db.execute(f"DELETE FROM config_badges WHERE id IN ({placeholders})", (*selected_badge_ids,))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("批量删除成功！"); st.rerun()
                                except Exception as e: db.rollback(); db.end(); st.error(f"删除失败：{e}")
                        else: st.caption("请勾选徽章以进行删除操作。")
                else: st.caption("暂无全局徽章。")
            else: st.info("全局徽章由管理员配置。")

            # ---- 7. 用户管理与权限控制 ----
            if view_role == "admin":
                st.divider(); st.markdown("### 7. 用户管理与权限控制")
                all_tbls = ["users", "daily_records", "period_bonus", "redemptions", "exam_rewards", "special_events", "extra_points", "config_tasks", "config_shop", "config_exam", "config_exam_rules", "config_thresholds", "config_bonus_rules", "config_exam_multihit"]
                edit_user_key = "user_edit_mode"
                if edit_user_key not in st.session_state: st.session_state[edit_user_key] = False
                header_cols = st.columns([3, 1])
                header_cols[0].markdown(f"**系统用户（共 {len(all_users_data)} 人）**")
                if header_cols[1].button("完成编辑" if st.session_state[edit_user_key] else "✏️ 编辑", key="toggle_edit_user"):
                    st.session_state[edit_user_key] = not st.session_state[edit_user_key]; st.rerun()
                selected_usernames = []
                for u in all_users_data:
                    uname = u["username"]; urole = u["role"]
                    try: host_row = db.execute("SELECT host_id FROM users WHERE username=?", (uname,)).fetchone(); uhost = dict(host_row).get("host_id") if host_row else None
                    except: uhost = None
                    is_self = (uname == current_user)
                    role_badge = {"admin": "🟢 管理员", "host": "🟡 Host", "user": "⚪ 普通用户", "solo": "🔵 独立用户"}.get(urole, urole)
                    plan_exp = u.get("plan_expires_at") or ""
                    is_perm = str(plan_exp).startswith("2099")
                    plan_str = " [永久]" if is_perm else (f" [{str(plan_exp)[:10]}]" if plan_exp else " [过期]")
                    
                    if st.session_state[edit_user_key]:
                        if is_self:
                            c1, c2, c3, c4 = st.columns([1, 3, 2, 3])
                            c1.write(""); c2.write(f"👤 **{html.escape(uname)}** (你自己){plan_str}"); c3.write(role_badge); c4.write(f"↳ Host: **{html.escape(uhost)}**" if uhost else "↳ Host: —")
                        else:
                            c1, c2, c3, c4 = st.columns([1, 3, 2, 3])
                            if c1.checkbox("", key=f"chk_user_{uname}", label_visibility="collapsed"): selected_usernames.append(uname)
                            c2.write(f"👤 **{html.escape(uname)}**{plan_str}"); c3.write(role_badge); c4.write(f"↳ Host: **{html.escape(uhost)}**" if uhost else "↳ Host: —")
                    else:
                        c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
                        c1.write(f"👤 **{html.escape(uname)}**{plan_str}" + (" (你自己)" if is_self else "")); c2.write(role_badge); c3.write(f"↳ Host: **{html.escape(uhost)}**" if uhost else "↳ Host: —")
                        if not is_self:
                            with c4:
                                with st.expander("操作"):
                                    if st.button("→ 管理员", key=f"set_admin_{uname}", **_stretch({})):
                                        try: db.execute("UPDATE users SET role='admin' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                        except RuntimeError as e: st.error(str(e))
                                    if st.button("→ Host", key=f"set_host_{uname}", disabled=(urole == "host"), **_stretch({})):
                                        try:
                                            blocked = False
                                            if urole == "admin":
                                                if _remaining_admins(db, uname) == 0: st.error("这是系统里最后一个管理员，不能降级为 Host。请先提升另一个用户为管理员。"); blocked = True
                                            if not blocked:
                                                if urole == "host":
                                                    bound_count = db.execute("SELECT COUNT(*) as c FROM users WHERE host_id=?", (uname,)).fetchone()["c"]
                                                    if bound_count > 0: st.session_state[f"confirm_demote_{uname}"] = 'host'; st.rerun()
                                                if urole != "host": db.execute("UPDATE users SET role='host' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                        except RuntimeError as e: st.error(str(e))
                                    if st.button("→ 普通用户", key=f"set_user_{uname}", disabled=(urole == "user"), **_stretch({})):
                                        try:
                                            blocked = False
                                            if urole == "admin":
                                                if _remaining_admins(db, uname) == 0: st.error("这是系统里最后一个管理员，不能降级为普通用户。请先提升另一个用户为管理员。"); blocked = True
                                            if not blocked:
                                                if urole == "host":
                                                    bound_count = db.execute("SELECT COUNT(*) as c FROM users WHERE host_id=?", (uname,)).fetchone()["c"]
                                                    if bound_count > 0: st.session_state[f"confirm_demote_{uname}"] = 'user'; st.rerun()
                                                if urole != "host": db.execute("UPDATE users SET role='user' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                        except RuntimeError as e: st.error(str(e))
                                    if st.button("→ 独立用户", key=f"set_solo_{uname}", disabled=(urole == "solo"), **_stretch({})):
                                        try:
                                            db.execute("UPDATE users SET role='solo' WHERE username=?", (uname,))
                                            db.commit(); st.cache_data.clear(); st.rerun()
                                        except RuntimeError as e: st.error(str(e))
                                    
                                    if st.button("⭐ 设为永久", key=f"set_perm_{uname}", disabled=is_perm, **_stretch({})):
                                        try:
                                            db.execute("UPDATE users SET plan_expires_at='2099-12-31 23:59:59' WHERE username=?", (uname,))
                                            db.commit(); st.cache_data.clear(); st.success("已设为永久！"); st.rerun()
                                        except RuntimeError as e: st.error(str(e))
                                    
                                    if st.button("重置密码", key=f"reset_{uname}", **_stretch({})):
                                        try: db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt("123456"), uname)); db.commit(); st.success(f"密码已重置")
                                        except RuntimeError as e: st.error(str(e))
                                    bind_val = st.text_input("绑定到 host", value=uhost or "", key=f"bind_val_{uname}", label_visibility="collapsed", placeholder="输入 host 用户名")
                                    if st.button("保存绑定", key=f"save_bind_{uname}", **_stretch({})):
                                        target = (bind_val or "").strip()
                                        if not target: st.error("Host 用户名不能为空")
                                        elif target == uname: st.error("不能绑定到自己")
                                        else:
                                            try:
                                                t_row = db.execute("SELECT role FROM users WHERE username=?", (target,)).fetchone()
                                                if not t_row: st.error(f"目标不存在")
                                                elif t_row["role"] not in ("host", "admin"): st.error(f"目标不是 host/admin")
                                                else:
                                                    visited = {uname}; cur = target; cyclic = False
                                                    while cur:
                                                        if cur in visited: cyclic = True; break
                                                        visited.add(cur)
                                                        c_row = db.execute("SELECT host_id FROM users WHERE username=?", (cur,)).fetchone()
                                                        cur = dict(c_row).get("host_id") if c_row else None
                                                    if cyclic: st.error("检测到循环绑定")
                                                    else: db.execute("UPDATE users SET host_id=? WHERE username=?", (target, uname)); db.commit(); st.cache_data.clear(); st.success(f"已绑定"); st.rerun()
                                            except RuntimeError as e: st.error(str(e))
                                    if st.button("解绑", key=f"unbind_{uname}", disabled=(not uhost), **_stretch({})):
                                        try: db.execute("UPDATE users SET host_id=NULL WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.success("已解绑"); st.rerun()
                                        except RuntimeError as e: st.error(str(e))
                    st.divider()
                if st.session_state[edit_user_key]:
                    if selected_usernames:
                        st.write(f"已选中 **{len(selected_usernames)}** 名用户")
                        ac1, ac2 = st.columns(2)
                        with ac1:
                            if st.button("🔑 批量重置密码为123456", key="batch_reset_pwd", **_stretch({})):
                                try:
                                    for u in selected_usernames: db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt("123456"), u))
                                    db.commit(); st.success("批量重置成功！")
                                except Exception as e: st.error(str(e))
                        with ac2:
                            if st.button("🗑 彻底删除选中用户", key="batch_del_users", **_stretch({"type": "primary"})): st.session_state["confirm_batch_del_users"] = True
                        if st.session_state.get("confirm_batch_del_users"):
                            st.warning("⚠️ 危险操作：即将彻底删除选中的用户及其全部数据（打卡、积分、配置等），此操作不可逆！")
                            c1, c2 = st.columns(2)
                            if c1.button("确认删除", key="confirm_del_btn", type="primary"):
                                db.begin()
                                try:
                                    for uname in selected_usernames:
                                        urole_row = db.execute("SELECT role FROM users WHERE username=?", (uname,)).fetchone()
                                        if urole_row and urole_row["role"] == "admin":
                                            if _remaining_admins(db, uname) == 0: st.error(f"用户 {uname} 是最后一个管理员，无法删除。操作已中止。"); raise RuntimeError("无法删除最后一个管理员")
                                        db.execute("UPDATE users SET host_id=NULL WHERE host_id=?", (uname,))
                                        for tbl in all_tbls:
                                            col = "username" if tbl == "users" else "owner_id"
                                            db.execute(f"DELETE FROM {tbl} WHERE {col}=?", (uname,))
                                    db.commit(); db.end(); st.session_state.pop("confirm_batch_del_users", None); st.cache_data.clear(); st.success("用户已彻底删除！"); st.rerun()
                                except Exception as e: db.rollback(); db.end(); st.error(f"删除失败：{str(e)}")
                            if c2.button("取消删除", key="cancel_del_btn"): st.session_state.pop("confirm_batch_del_users", None); st.rerun()
                    else: st.caption("请勾选用户以进行批量重置密码或删除操作。")
                for uname in [u["username"] for u in all_users_data]:
                    if st.session_state.get(f"confirm_demote_{uname}"):
                        target_role = st.session_state[f"confirm_demote_{uname}"]
                        try: bound_count = db.execute("SELECT COUNT(*) as c FROM users WHERE host_id=?", (uname,)).fetchone()["c"]
                        except: bound_count = 0
                        st.warning(f"该 host 下有 {bound_count} 个 user，降级/变更后将解绑。是否确认将 {uname} 变更为 {target_role}？")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("确认降级", key=f"confirm_demote_btn_{uname}", **_stretch({"type": "primary"})):
                            try:
                                db.execute("UPDATE users SET host_id=NULL WHERE host_id=?", (uname,))
                                db.execute("UPDATE users SET role=? WHERE username=?", (target_role, uname))
                                db.commit(); del st.session_state[f"confirm_demote_{uname}"]; st.cache_data.clear(); st.rerun()
                            except RuntimeError as e: st.error(str(e))
                        if cc2.button("取消", key=f"cancel_demote_{uname}", **_stretch({})):
                            del st.session_state[f"confirm_demote_{uname}"]; st.rerun()

                with st.expander("💳 生成内测/续期兑换码"):
                    val_days = st.number_input("有效天数", min_value=1, value=30)
                    if st.button("生成兑换码", type="primary"):
                        new_code = uuid.uuid4().hex[:8].upper()
                        try:
                            db.execute("INSERT INTO redeem_codes (code, days, is_used, created_at) VALUES (?,?,0,?)", (new_code, int(val_days), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            db.commit()
                            st.success("生成成功！")
                            st.code(new_code, language="text")
                        except RuntimeError as e:
                            st.error(f"生成失败：{e}")

if __name__ == "__main__":
    main()
