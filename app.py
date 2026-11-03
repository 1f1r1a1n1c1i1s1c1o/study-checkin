#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, random, os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
import pandas as pd

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

DEFAULT_THRESHOLDS = {0: {"basic": 8.0, "full": 11.0}, 1: {"basic": 8.0, "full": 11.0}, 2: {"basic": 8.0, "full": 11.0}, 3: {"basic": 6.0, "full": 7.0}, 4: {"basic": 8.0, "full": 11.0}, 5: {"basic": 10.0, "full": 13.0}, 6: {"basic": 10.0, "full": 13.0}}
DEFAULT_TASKS = [
    ("hw_sort", 0, "校内", "作业分类", 1.0), ("hw_done", 0, "校内", "作业完成", 2.0), ("math_ab", 0, "附加", "数学模卷1-10、13-15、17-19", 1.5), ("math_c", 0, "附加", "解析几何", 1.0), ("eng_a", 0, "附加", "1h背单词+抽检", 1.0), ("eng_bc", 0, "附加", "英语模卷GVC+ABCD", 1.5), ("meals", 0, "生活", "一日三餐", 1.5), ("sleep65", 0, "生活", "睡足6.5小时", 1.5),
    ("hw_sort", 1, "校内", "作业分类", 1.0), ("hw_done", 1, "校内", "作业完成", 2.0), ("math_ab", 1, "附加", "数学专题练习", 1.5), ("math_c", 1, "附加", "解析几何", 1.0), ("eng_a", 1, "附加", "1h背单词+抽检", 1.0), ("eng_bc", 1, "附加", "英语专题练习", 1.5), ("meals", 1, "生活", "一日三餐", 1.5), ("sleep65", 1, "生活", "睡足6.5小时", 1.5),
    ("hw_sort", 2, "校内", "作业分类", 1.0), ("hw_done", 2, "校内", "作业完成", 2.0), ("math_ab", 2, "附加", "数学模卷1-10、13-15、17-19", 1.5), ("math_c", 2, "附加", "解析几何", 1.0), ("eng_a", 2, "附加", "1h背单词+抽检", 1.0), ("eng_bc", 2, "附加", "英语模卷GVC+ABCD", 1.5), ("meals", 2, "生活", "一日三餐", 1.5), ("sleep65", 2, "生活", "睡足6.5小时", 1.5),
    ("hw_sort", 3, "校内", "作业分类", 1.0), ("hw_done", 3, "校内", "作业完成", 2.0), ("meals", 3, "生活", "一日三餐", 2.0), ("rest", 3, "生活", "好好休息", 2.0),
    ("hw_sort", 4, "校内", "作业分类", 1.0), ("hw_done", 4, "校内", "作业完成", 2.0), ("math_ab", 4, "附加", "数学专题练习", 1.5), ("math_c", 4, "附加", "解析几何", 1.0), ("eng_a", 4, "附加", "1h背单词+抽检", 1.0), ("eng_bc", 4, "附加", "英语专题练习", 1.5), ("meals", 4, "生活", "一日三餐", 1.5), ("sleep65", 4, "生活", "睡足6.5小时", 1.5),
    ("eng_paper", 5, "学习", "英语整卷", 1.5), ("math_paper", 5, "学习", "数学整卷", 1.5), ("vocab_check", 5, "学习", "背单词抽查", 1.0), ("math_review", 5, "学习", "数学复盘", 1.5), ("eng_review", 5, "学习", "英语复盘", 1.5), ("eng_lecture", 5, "学习", "英语讲评", 1.5), ("math_lecture", 5, "学习", "数学讲评", 1.5), ("meals", 5, "生活", "一日三餐", 1.0), ("sleep75", 5, "生活", "睡满7.5小时", 2.0),
    ("eng_class", 6, "学习", "英语课", 2.0), ("school_hw", 6, "学习", "学校作业", 2.0), ("back_school", 6, "学习", "回校上课", 1.0), ("recite_eng", 6, "学习", "背英语", 1.0), ("eng_pl", 6, "学习", "英语卷+讲评", 2.0), ("math_pl", 6, "学习", "数学专题+讲评", 2.0), ("meals", 6, "生活", "一日三餐", 1.0), ("sleep75", 6, "生活", "睡满7.5小时", 2.0),
]
DEFAULT_SHOP = [("专属夸夸", 6), ("点歌", 10), ("免除一次日常小惩罚", 15), ("专属定制外卖", 20), ("周末伺候小晴晴（如按摩）", 30), ("任晴摆布（低配，一次性）", 50), ("任晴摆布（高配，一整个周末）", 100), ("大餐 / date", 120), ("侍寝", 135), ("一日游", 150), ("免死金牌", 200)]
DEFAULT_EXAM_CONFIG = {"语文": {"type": "score", "target": 105.0, "step": 3.0, "step_points": 2.0}, "数学": {"type": "score", "target": 95.0, "step": 3.0, "step_points": 2.0}, "英语": {"type": "score", "target": 82.0, "step": 3.0, "step_points": 2.0}, "政治": {"type": "grade", "target": "B+", "step_points": 1.5}, "历史": {"type": "grade", "target": "C", "step_points": 1.5}, "生物": {"type": "grade", "target": "C+", "step_points": 1.5}}
DEFAULT_EXAM_MULTIHIT = [{"hit_count": 4, "points": 3.0}, {"hit_count": 6, "points": 5.0}]
DEFAULT_EXAM_RULES = {"hit_points": 1.0, "rank_top_percent": 75.0, "rank_base_points": 1.0, "rank_step_percent": 5.0, "rank_step_points": 1.5}
DEFAULT_BONUS_RULES = {"weekday": {"single": {"points": 1.0, "full_points": 2.0}, "streak2": {"points": 1.5, "full_points": 3.0}, "streak4": {"points": 2.5, "full_points": 5.0}}, "weekend": {"single": {"points": 1.0, "full_points": 2.0}}, "longterm": {"week_basic": 3.5, "week_full": 7.0, "month_basic": 8.0, "month_full": 20.0}}
TIER_CN = {"single": "单日达标", "streak2": "连续2日达标", "streak4": "连续4日达标", "weekend_single": "周末单日达标"}
GRADES = ["A+", "A", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E"]

class DBWrapper:
    def __init__(self, conn, is_cloud):
        self.conn = conn; self.is_cloud = is_cloud
    def execute(self, query, params=()):
        if self.is_cloud:
            query = query.replace("?", "%s")
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(query, params); return cur
        else: return self.conn.execute(query, params)
    def commit(self): self.conn.commit()

@st.cache_resource(show_spinner=False)
def get_db():
    if IS_CLOUD:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        conn.autocommit = True; db = DBWrapper(conn, True)
        init_cloud_data(db); return db
    else:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row; db = DBWrapper(conn, False); return db

def init_cloud_data(db):
    tables = [
        "CREATE TABLE IF NOT EXISTS daily_records (day TEXT PRIMARY KEY, done_tasks TEXT, base_score REAL, bonus_score REAL, bonus_detail TEXT, total_score REAL, updated_at TEXT)",
        "CREATE TABLE IF NOT EXISTS period_bonus (period_key TEXT PRIMARY KEY, kind TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS redemptions (id SERIAL PRIMARY KEY, item TEXT, cost REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS exam_rewards (id SERIAL PRIMARY KEY, detail TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS special_events (id SERIAL PRIMARY KEY, day TEXT, points REAL, note TEXT, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS config_tasks (id TEXT, weekday INTEGER, category TEXT, name TEXT, points REAL, PRIMARY KEY (id, weekday))",
        "CREATE TABLE IF NOT EXISTS config_shop (id SERIAL PRIMARY KEY, name TEXT, cost REAL)",
        "CREATE TABLE IF NOT EXISTS config_exam (subject TEXT PRIMARY KEY, config_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_exam_rules (id INTEGER PRIMARY KEY, config_json TEXT)",
        "CREATE TABLE IF NOT EXISTS config_thresholds (weekday INTEGER PRIMARY KEY, basic REAL, \"full\" REAL)",
        "CREATE TABLE IF NOT EXISTS config_bonus_rules (id INTEGER PRIMARY KEY, rules_json TEXT)",
        "CREATE TABLE IF NOT EXISTS extra_points (id SERIAL PRIMARY KEY, name TEXT, points REAL, ts TEXT)",
        "CREATE TABLE IF NOT EXISTS config_exam_multihit (hit_count INTEGER PRIMARY KEY, points REAL)"
    ]
    for t in tables: db.execute(t)
    
    if db.execute("SELECT COUNT(*) as c FROM config_tasks").fetchone()["c"] == 0:
        for t in DEFAULT_TASKS: db.execute("INSERT INTO config_tasks VALUES (%s,%s,%s,%s,%s)", t)
        for s in DEFAULT_SHOP: db.execute("INSERT INTO config_shop(name, cost) VALUES (%s,%s)", s)
        for sub, cfg in DEFAULT_EXAM_CONFIG.items(): db.execute("INSERT INTO config_exam VALUES (%s,%s)", (sub, json.dumps(cfg)))
        db.execute("INSERT INTO config_exam_rules VALUES (1, %s)", (json.dumps(DEFAULT_EXAM_RULES),))
        for wd, data in DEFAULT_THRESHOLDS.items(): db.execute('INSERT INTO config_thresholds VALUES (%s,%s,%s)', (wd, data["basic"], data["full"]))
        db.execute("INSERT INTO config_bonus_rules VALUES (1, %s)", (json.dumps(DEFAULT_BONUS_RULES),))
        for mh in DEFAULT_EXAM_MULTIHIT: db.execute("INSERT INTO config_exam_multihit VALUES (%s,%s)", (mh["hit_count"], mh["points"]))

def get_thresholds(db):
    rows = db.execute("SELECT * FROM config_thresholds").fetchall()
    return {r["weekday"]: {"basic": r["basic"], "full": r["full"]} for r in rows}
def get_bonus_rules(db): return json.loads(db.execute("SELECT rules_json FROM config_bonus_rules WHERE id=1").fetchone()["rules_json"])
def get_tasks(db, weekday):
    rows = db.execute("SELECT * FROM config_tasks WHERE weekday=?", (weekday,)).fetchall()
    return [{"id": r["id"], "category": r["category"], "name": r["name"], "points": r["points"]} for r in rows]
def get_shop(db): return [(r["name"], r["cost"]) for r in db.execute("SELECT * FROM config_shop").fetchall()]
def get_exam_config(db):
    subjects = {r["subject"]: json.loads(r["config_json"]) for r in db.execute("SELECT * FROM config_exam").fetchall()}
    rules = json.loads(db.execute("SELECT config_json FROM config_exam_rules WHERE id=1").fetchone()["config_json"])
    return subjects, rules
def get_exam_multihit(db): return [{"hit_count": r["hit_count"], "points": r["points"]} for r in db.execute("SELECT * FROM config_exam_multihit ORDER BY hit_count ASC").fetchall()]

def compute_bonus_for_day(day: date, lookup: dict, thresholds: dict, bonus_rules: dict) -> tuple[float, dict]:
    key = day.isoformat(); rec = lookup.get(key)
    if rec is None: return 0.0, {}
    base = float(rec["base_score"]); wd = day.weekday(); thr = thresholds[wd]
    if wd <= 4:
        if base < thr["basic"]: return 0.0, {"tier": "none"}
        streak_days = []; cur = day
        if wd == 3: streak = 1; all_full = base >= thr["full"]
        else:
            while cur.weekday() <= 4:
                if cur.weekday() == 3: cur -= timedelta(days=1); continue
                r = lookup.get(cur.isoformat())
                if r is None: break
                cur_thr = thresholds[cur.weekday()]
                if float(r["base_score"]) >= cur_thr["basic"]: streak_days.append(cur); cur -= timedelta(days=1)
                else: break
            streak = len(streak_days)
            all_full = all(float(lookup[x.isoformat()]["base_score"]) >= thresholds[x.weekday()]["full"] for x in streak_days)
        rule = bonus_rules["weekday"]
        if streak >= 4: tier = "streak4"; bonus = rule[tier]["full_points"] if all_full else rule[tier]["points"]
        elif streak >= 2: tier = "streak2"; bonus = rule[tier]["full_points"] if all_full else rule[tier]["points"]
        else: tier = "single"; bonus = rule[tier]["full_points"] if base >= thr["full"] else rule[tier]["points"]
        return float(bonus), {"tier": tier, "streak": streak}
    if base < thr["basic"]: return 0.0, {"tier": "none"}
    rule = bonus_rules["weekend"]["single"]; bonus = rule["full_points"] if base >= thr["full"] else rule["points"]
    return float(bonus), {"tier": "weekend_single"}

def recalc_all_bonus(db):
    thresholds = get_thresholds(db); bonus_rules = get_bonus_rules(db)
    rows = db.execute("SELECT day, base_score FROM daily_records").fetchall()
    lookup = {r["day"]: {"base_score": r["base_score"]} for r in rows}
    for day_str in sorted(lookup):
        d = date.fromisoformat(day_str)
        bonus, detail = compute_bonus_for_day(d, lookup, thresholds, bonus_rules)
        db.execute("UPDATE daily_records SET bonus_score=?, bonus_detail=?, total_score=? WHERE day=?", (bonus, json.dumps(detail), lookup[day_str]["base_score"] + bonus, day_str))
    db.commit()

def settle_longterm_bonus(db):
    thresholds = get_thresholds(db); bonus_rules = get_bonus_rules(db)
    rows = db.execute("SELECT day, base_score FROM daily_records").fetchall()
    scores = {r["day"]: float(r["base_score"]) for r in rows}
    if not scores: return
    weeks = {}
    for ds in scores:
        d = date.fromisoformat(ds); y, w, _ = d.isocalendar()
        weeks.setdefault(f"{y}-W{w:02d}", []).append(d)
    for wk, dlist in weeks.items():
        monday = min(dlist) - timedelta(days=min(dlist).weekday())
        full_week = [monday + timedelta(days=i) for i in range(7)]
        if not all(x.isoformat() in scores for x in full_week): continue
        basic_ok = all(scores[x.isoformat()] >= thresholds[x.weekday()]["basic"] for x in full_week)
        full_ok = all(scores[x.isoformat()] >= thresholds[x.weekday()]["full"] for x in full_week)
        if full_ok: db.execute("INSERT INTO period_bonus(period_key, kind, points, ts) VALUES (?,?,?,?) ON CONFLICT(period_key) DO NOTHING", (f"W:{wk}", "完美一周", bonus_rules["longterm"]["week_full"], bj_now().isoformat()))
        elif basic_ok: db.execute("INSERT INTO period_bonus(period_key, kind, points, ts) VALUES (?,?,?,?) ON CONFLICT(period_key) DO NOTHING", (f"W:{wk}", "整周达标", bonus_rules["longterm"]["week_basic"], bj_now().isoformat()))
    db.commit()

def save_day(db, day: date, done_ids: list[str]):
    tasks = get_tasks(db, day.weekday())
    base = sum(t["points"] for t in tasks if t["id"] in set(done_ids))
    ts = bj_now().isoformat(timespec="seconds")
    db.execute("INSERT INTO daily_records(day, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at) VALUES (?, ?, ?, 0, '{}', ?, ?) ON CONFLICT(day) DO UPDATE SET done_tasks=excluded.done_tasks, base_score=excluded.base_score, updated_at=excluded.updated_at", (day.isoformat(), json.dumps(sorted(done_ids)), base, base, ts))
    db.commit(); recalc_all_bonus(db); settle_longterm_bonus(db)

def get_balance(db) -> dict:
    daily = db.execute("SELECT COALESCE(SUM(total_score),0) as s FROM daily_records").fetchone()["s"]
    period = db.execute("SELECT COALESCE(SUM(points),0) as s FROM period_bonus").fetchone()["s"]
    exam = db.execute("SELECT COALESCE(SUM(points),0) as s FROM exam_rewards").fetchone()["s"]
    special = db.execute("SELECT COALESCE(SUM(points),0) as s FROM special_events").fetchone()["s"]
    spent = db.execute("SELECT COALESCE(SUM(cost),0) as s FROM redemptions").fetchone()["s"]
    extra = db.execute("SELECT COALESCE(SUM(points),0) as s FROM extra_points").fetchone()["s"]
    return {"daily": daily, "period": period, "exam": exam, "special": special, "spent": spent, "extra": extra,
            "balance": float(daily + period + exam + special + extra - spent)}

def grade_gap(target: str, actual: str) -> int: return GRADES.index(target) - GRADES.index(actual)

def calc_exam_bonus(db, scores: dict, ranks: dict) -> tuple[float, list[str], int]:
    exam_config, exam_rules = get_exam_config(db)
    multihit_rules = get_exam_multihit(db)
    total = 0.0; lines = []; hit_count = 0
    
    for subject, cfg in exam_config.items():
        actual = scores.get(subject)
        if actual is None: continue
        if cfg["type"] == "score":
            hit = actual >= cfg["target"]
            if hit: total += exam_rules["hit_points"]; hit_count += 1; lines.append(f"达成 {subject} 目标 {cfg['target']} -> +{exam_rules['hit_points']}")
            tiers = int((actual - cfg["target"]) // cfg["step"]) if actual > cfg["target"] else 0
            if tiers > 0: gain = tiers * cfg["step_points"]; total += gain; lines.append(f"  {subject} 超目标 {tiers} 档 -> +{gain}")
        else:
            gap = grade_gap(cfg["target"], actual); hit = gap >= 0
            if hit: total += exam_rules["hit_points"]; hit_count += 1; lines.append(f"达成 {subject} 目标 {cfg['target']} -> +{exam_rules['hit_points']}")
            if gap > 0: gain = gap * cfg["step_points"]; total += gain; lines.append(f"  {subject} 升 {gap} 档 -> +{gain}")
            
    sorted_mh = sorted(multihit_rules, key=lambda x: x["hit_count"], reverse=True)
    for mh in sorted_mh:
        if hit_count >= mh["hit_count"]:
            total += mh["points"]; lines.append(f"达成 {mh['hit_count']} 门及以上 -> +{mh['points']}")
            break 

    for subject in ["语文", "数学", "英语"]:
        pct = ranks.get(subject)
        if pct is not None and 0 <= pct < 100 and pct <= exam_rules["rank_top_percent"]:
            total += exam_rules["rank_base_points"]; lines.append(f"{subject} 前{pct:.0f}% -> +{exam_rules['rank_base_points']}")
            extra = int((exam_rules["rank_top_percent"] - pct) // exam_rules["rank_step_percent"])
            if extra > 0: gain = extra * exam_rules["rank_step_points"]; total += gain; lines.append(f"  再进{extra}档 -> +{gain}")
    return total, lines, hit_count

def main():
    st.set_page_config(page_title="学习打卡系统", layout="centered", initial_sidebar_state="collapsed")
    db = get_db(); now = bj_now(); today = now.date()

    with st.sidebar:
        st.title("学习打卡")
        st.info(f"北京时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n\n{WEEKDAY_CN[today.weekday()]}")
        bal = get_balance(db)
        st.metric("当前可用积分", f"{bal['balance']:.1f}")
        with st.expander("积分明细"):
            st.write(f"打卡：{bal['daily']:.1f} | 长期：{bal['period']:.1f}")
            st.write(f"考试：{bal['exam']:.1f} | 偶发：{bal['extra']:.1f}")
            st.write(f"特殊：{bal['special']:.1f} | 消耗：-{bal['spent']:.1f}")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["打卡", "偶发", "历史", "商城", "兑换", "考试", "事件", "设置"])

    with tab1:
        thresholds = get_thresholds(db); thr = thresholds[today.weekday()]
        st.subheader(f"{today.strftime('%m月%d日')} - {WEEKDAY_CN[today.weekday()]}")
        st.caption(f"基本要求：{thr['basic']} 分 | 满分：{thr['full']} 分")
        tasks = get_tasks(db, today.weekday())
        
        # 【关键修改】判断今天是否已经打卡
        existing = db.execute("SELECT * FROM daily_records WHERE day=?", (today.isoformat(),)).fetchone()
        already_done = existing is not None
        done_ids = set(json.loads(existing["done_tasks"])) if existing else set()
        
        cats = {}
        for t in tasks: cats.setdefault(t["category"], []).append(t)
        selected_ids = []
        for cat, items in cats.items():
            st.markdown(f"**{cat}**")
            cols = st.columns(2)
            for i, t in enumerate(items):
                with cols[i % 2]:
                    # 如果已经打卡，禁用复选框
                    if st.checkbox(f"{t['name']} ({t['points']}分)", value=(t["id"] in done_ids), key=f"cb_{today}_{t['id']}", disabled=already_done):
                        if not already_done: selected_ids.append(t["id"])
                        
        st.divider(); c1, c2, c3 = st.columns(3)
        
        if already_done:
            # 如果已打卡，显示数据库里的分数，而不是实时计算的
            c1.metric("基础分", f"{existing['base_score']:.1f}")
            c2.metric("Bonus", f"{existing['bonus_score']:.1f}")
            c3.metric("今日总分", f"{existing['total_score']:.1f}")
            st.success("✅ 今日已完成打卡，记录已锁定。")
            
            # 提供撤销按钮，应对填错情况
            if st.button("🔄 撤销今日打卡（重新填写）", type="secondary", use_container_width=True):
                db.execute("DELETE FROM daily_records WHERE day=?", (today.isoformat(),))
                db.commit()
                recalc_all_bonus(db) # 撤销后需要重算一次，因为可能影响连击
                st.rerun()
        else:
            # 正常实时计算预览
            base_now = sum(t["points"] for t in tasks if t["id"] in set(selected_ids))
            lookup = {r["day"]: {"base_score": r["base_score"]} for r in db.execute("SELECT day, base_score FROM daily_records").fetchall()}
            lookup[today.isoformat()] = {"base_score": base_now}
            bonus, detail = compute_bonus_for_day(today, lookup, thresholds, get_bonus_rules(db))
            
            c1.metric("基础分", f"{base_now:.1f}"); c2.metric("Bonus", f"{bonus:.1f}"); c3.metric("预计总分", f"{base_now + bonus:.1f}")
            if detail.get("tier") in TIER_CN: st.info(f"Bonus 判定：{TIER_CN[detail['tier']]}")
            
            if st.button("保存今日打卡", type="primary", use_container_width=True):
                save_day(db, today, selected_ids); st.success("已保存！"); st.rerun()

    with tab2:
        st.subheader("偶发事件加/扣分")
        st.write("随时记录特殊事件（如：高分作文+1分、犯错-2分）")
        with st.form("extra_point_form"):
            col1, col2, col3 = st.columns([4, 2, 2])
            e_name = col1.text_input("事件名称", placeholder="例如：高分作文、主动做家务...")
            e_pts = col2.number_input("分数 (可为负数)", value=1.0, step=0.5)
            if st.form_submit_button("确认提交", type="primary", use_container_width=True):
                if e_name:
                    db.execute("INSERT INTO extra_points(name, points, ts) VALUES (?,?,?)", (e_name, e_pts, bj_now().isoformat(timespec="seconds")))
                    db.commit(); st.success(f"已记录：{e_name} ({e_pts}分)"); st.rerun()
        
        st.divider()
        st.markdown("**最近偶发记录**")
        ex_rows = db.execute("SELECT * FROM extra_points ORDER BY id DESC LIMIT 20").fetchall()
        if ex_rows:
            st.dataframe([{"时间": r["ts"], "事件": r["name"], "积分": r["points"]} for r in ex_rows], use_container_width=True, hide_index=True)
            if st.button("清空偶发记录"):
                db.execute("DELETE FROM extra_points"); db.commit(); st.rerun()
        else: st.caption("暂无记录")

    with tab3:
        st.subheader("历史记录")
        days = [r["day"] for r in db.execute("SELECT day FROM daily_records ORDER BY day DESC").fetchall()]
        if days:
            sel = st.selectbox("选择日期", days)
            row = db.execute("SELECT * FROM daily_records WHERE day=?", (sel,)).fetchone()
            st.write(f"**总分: {row['total_score']:.1f}** (基础 {row['base_score']:.1f} + Bonus {row['bonus_score']:.1f})")
            done = json.loads(row["done_tasks"])
            st.write("完成项：", ", ".join([t["name"] for t in get_tasks(db, date.fromisoformat(sel).weekday()) if t["id"] in done]) or "无")
        else: st.info("暂无记录")

    with tab4:
        st.subheader("商城")
        bal = get_balance(db)
        for name, cost in get_shop(db):
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.write(f"**{name}**"); c2.write(f"`{cost} 分`")
            if c3.button("兑换", key=f"buy_{name}", disabled=(bal["balance"] < cost)):
                db.execute("INSERT INTO redemptions(item, cost, ts) VALUES (?,?,?)", (name, cost, bj_now().isoformat()))
                db.commit(); st.success("兑换成功！"); st.rerun()

    with tab5:
        st.subheader("兑换历史")
        rows = db.execute("SELECT * FROM redemptions ORDER BY id DESC").fetchall()
        if rows: st.dataframe([{"时间": r["ts"], "奖励": r["item"], "消耗": r["cost"]} for r in rows], use_container_width=True)
        else: st.info("暂无")

    with tab6:
        st.subheader("考试专项")
        exam_config, _ = get_exam_config(db)
        scores = {}; ranks = {}
        subjects_list = list(exam_config.keys())
        
        for i in range(0, len(subjects_list), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(subjects_list):
                    sub = subjects_list[i + j]; cfg = exam_config[sub]
                    with cols[j]:
                        if cfg["type"] == "score": scores[sub] = st.number_input(f"{sub} (目标{cfg['target']})", value=float(cfg['target']), key=f"ex_{sub}")
                        else: scores[sub] = st.selectbox(f"{sub} (目标{cfg['target']})", GRADES, index=GRADES.index(cfg['target']), key=f"ex_{sub}")
        
        st.write("**语数外排名前百分之多少（填100不参与）**")
        c1, c2, c3 = st.columns(3)
        ranks["语文"] = c1.number_input("语文", 0.0, 100.0, 100.0)
        ranks["数学"] = c2.number_input("数学", 0.0, 100.0, 100.0)
        ranks["英语"] = c3.number_input("英语", 0.0, 100.0, 100.0)

        total_pts, lines, hit_count = calc_exam_bonus(db, scores, ranks)
        st.divider()
        st.markdown(f"### 预计获得：**{total_pts:.1f}** 分（达成 {hit_count} 门）")
        for ln in lines: st.write(ln)
        
        if st.button("保存本次成绩", type="primary"):
            detail_text = f"达成 {hit_count} 门 | " + "/".join([f"{k}:{v}" for k,v in scores.items()])
            db.execute("INSERT INTO exam_rewards(detail, points, ts) VALUES (?,?,?)", (detail_text, total_pts, bj_now().isoformat()))
            db.commit(); st.success("已保存！"); st.rerun()

    with tab7:
        st.subheader("特殊事件")
        fired = db.execute("SELECT * FROM special_events WHERE day=?", (today.isoformat(),)).fetchone()
        if fired: st.info(f"今天已经触发过啦：{fired['note']} +{fired['points']}分")
        else:
            if st.button("摇一摇", use_container_width=True):
                roll = random.random()
                pts = random.randint(1, 2) if roll < 0.4 else random.randint(3, 5) if roll < 0.8 else random.randint(6, 8) if roll < 0.95 else random.randint(10, 15)
                db.execute("INSERT INTO special_events(day, points, note, ts) VALUES (?,?,?,?)", (today.isoformat(), pts, "积分暴击", bj_now().isoformat()))
                db.commit(); st.balloons(); st.success(f"获得 {pts} 积分！"); st.rerun()

    with tab8:
        st.subheader("系统设置")
        
        st.markdown("### 1. 修改每日任务")
        sel_wd = st.selectbox("选择要修改的星期", range(7), format_func=lambda x: WEEKDAY_CN[x])
        tasks_df = db.execute("SELECT * FROM config_tasks WHERE weekday=?", (sel_wd,)).fetchall()
        edited_tasks = st.data_editor([dict(t) for t in tasks_df], column_config={"id": st.column_config.TextColumn("任务ID", required=True), "weekday": None, "category": st.column_config.TextColumn("分类"), "name": st.column_config.TextColumn("任务名称", required=True), "points": st.column_config.NumberColumn("分数", min_value=0.0, step=0.5)}, num_rows="dynamic", use_container_width=True, key=f"edit_task_{sel_wd}")
        if st.button("保存任务修改"):
            db.execute("DELETE FROM config_tasks WHERE weekday=?", (sel_wd,))
            for t in edited_tasks:
                if t.get("id") and t.get("name"): db.execute("INSERT INTO config_tasks VALUES (?,?,?,?,?)", (t["id"], sel_wd, t["category"], t["name"], t["points"]))
            db.commit(); st.success("任务已更新！"); st.rerun()

        st.divider()
        st.markdown("### 2. 修改积分商城奖励")
        shop_df = db.execute("SELECT id, name, cost FROM config_shop").fetchall()
        edited_shop = st.data_editor([dict(s) for s in shop_df], column_config={"id": None, "name": st.column_config.TextColumn("奖励名称", required=True), "cost": st.column_config.NumberColumn("所需积分", min_value=0.0, step=1.0)}, num_rows="dynamic", use_container_width=True, key="edit_shop")
        if st.button("保存商城修改"):
            db.execute("DELETE FROM config_shop")
            for s in edited_shop:
                if s.get("name") and s.get("cost") is not None: db.execute("INSERT INTO config_shop(name, cost) VALUES (?,?)", (s["name"], s["cost"]))
            db.commit(); st.success("商城已更新！"); st.rerun()

        st.divider()
        st.markdown("### 3. 修改考试科目 (可自由增删改)")
        exam_config, exam_rules = get_exam_config(db)
        df_exam = pd.DataFrame([{"科目": k, "类型": v["type"], "目标": v["target"], "分差": v.get("step", 0), "单档奖励": v["step_points"]} for k, v in exam_config.items()])
        edited_exam = st.data_editor(df_exam, num_rows="dynamic", use_container_width=True, key="edit_exam_subjects")
        if st.button("保存考试科目修改"):
            db.execute("DELETE FROM config_exam")
            for _, row in edited_exam.iterrows():
                if pd.notna(row["科目"]) and row["科目"]:
                    sub = row["科目"]
                    if row["类型"] == "score": cfg = {"type": "score", "target": float(row["目标"]), "step": float(row["分差"]), "step_points": float(row["单档奖励"])}
                    else: cfg = {"type": "grade", "target": row["目标"], "step_points": float(row["单档奖励"])}
                    db.execute("INSERT INTO config_exam VALUES (?,?)", (sub, json.dumps(cfg)))
            db.commit(); st.success("考试科目已更新！"); st.rerun()

        st.divider()
        st.markdown("### 4. 修改多科达成奖励")
        mh_df = pd.DataFrame(get_exam_multihit(db))
        if mh_df.empty: mh_df = pd.DataFrame([{"hit_count": 4, "points": 3.0}])
        edited_mh = st.data_editor(mh_df, column_config={"hit_count": st.column_config.NumberColumn("达成科目数", min_value=1, step=1), "points": st.column_config.NumberColumn("奖励分数", min_value=0.0, step=0.5)}, num_rows="dynamic", use_container_width=True, key="edit_exam_mh")
        if st.button("保存多科奖励修改"):
            db.execute("DELETE FROM config_exam_multihit")
            for _, row in edited_mh.iterrows():
                if pd.notna(row["hit_count"]) and pd.notna(row["points"]): db.execute("INSERT INTO config_exam_multihit VALUES (?,?)", (int(row["hit_count"]), float(row["points"])))
            db.commit(); st.success("多科奖励规则已更新！"); st.rerun()

        st.divider()
        st.markdown("### 5. 修改阈值与 Bonus 规则")
        thresholds = get_thresholds(db); bonus_rules = get_bonus_rules(db)
        with st.form("bonus_settings_form"):
            t_cols = st.columns(7); t_inputs = {}
            for i in range(7):
                with t_cols[i]:
                    st.markdown(f"**{WEEKDAY_CN[i]}**")
                    t_inputs[i] = {"basic": st.number_input("基本", value=float(thresholds[i]["basic"]), key=f"th_b_{i}"), "full": st.number_input("满分", value=float(thresholds[i]["full"]), key=f"th_f_{i}")}
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**周中**")
                wd_single = st.number_input("单日达标", value=float(bonus_rules["weekday"]["single"]["points"]), step=0.5)
                wd_single_full = st.number_input("单日满分", value=float(bonus_rules["weekday"]["single"]["full_points"]), step=0.5)
                wd_2 = st.number_input("连2达标", value=float(bonus_rules["weekday"]["streak2"]["points"]), step=0.5)
                wd_2_full = st.number_input("连2满分", value=float(bonus_rules["weekday"]["streak2"]["full_points"]), step=0.5)
                wd_4 = st.number_input("连4达标", value=float(bonus_rules["weekday"]["streak4"]["points"]), step=0.5)
                wd_4_full = st.number_input("连4满分", value=float(bonus_rules["weekday"]["streak4"]["full_points"]), step=0.5)
            with c2:
                st.markdown("**周末及长期**")
                we_single = st.number_input("周末单日达标", value=float(bonus_rules["weekend"]["single"]["points"]), step=0.5)
                we_single_full = st.number_input("周末单日满分", value=float(bonus_rules["weekend"]["single"]["full_points"]), step=0.5)
                lt_wb = st.number_input("整周达标", value=float(bonus_rules["longterm"]["week_basic"]), step=0.5)
                lt_wf = st.number_input("完美一周", value=float(bonus_rules["longterm"]["week_full"]), step=0.5)
                lt_mb = st.number_input("整月达标", value=float(bonus_rules["longterm"]["month_basic"]), step=0.5)
                lt_mf = st.number_input("完美一月", value=float(bonus_rules["longterm"]["month_full"]), step=0.5)

            if st.form_submit_button("保存并重算历史", type="primary", use_container_width=True):
                for i in range(7): db.execute("UPDATE config_thresholds SET basic=?, \"full\"=? WHERE weekday=?", (t_inputs[i]["basic"], t_inputs[i]["full"], i))
                new_bonus = {"weekday": {"single": {"points": wd_single, "full_points": wd_single_full}, "streak2": {"points": wd_2, "full_points": wd_2_full}, "streak4": {"points": wd_4, "full_points": wd_4_full}}, "weekend": {"single": {"points": we_single, "full_points": we_single_full}}, "longterm": {"week_basic": lt_wb, "week_full": lt_wf, "month_basic": lt_mb, "month_full": lt_mf}}
                db.execute("UPDATE config_bonus_rules SET rules_json=? WHERE id=1", (json.dumps(new_bonus),))
                db.commit(); recalc_all_bonus(db); st.success("已更新并重算！"); st.rerun()

if __name__ == "__main__":
    main()
