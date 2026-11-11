#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 【v4 安全加固完整版 + 用户搜索 + 7 语言】
# 本次 5 项中危加固：
# 6. 云端 PostgreSQL 增加管理员一键 JSON 全库导出 + 外部备份说明；_backup_sqlite 云端分支只提示不阻塞
# 7. 新增 schema_migrations，把破坏性 DROP CONSTRAINT 清理封装为只执行一次的 run_legacy_constraint_cleanup
# 8. 新增统一权限辅助函数 is_admin / is_host / is_user / is_solo / can_manage_others / can_edit_configs / require_admin / require_admin_or_host
# 9. 新增 validate_password_strength，并在注册、侧边栏修改密码、强制改密、找回密码处增加提示与后端校验；7 语言补齐 pwd_* key
# 10. all_tbls 列表改为不可变常量元组 ALL_TABLES，新增 delete_user_all_data，彻底删除用户统一走安全函数
#
# 保留：7 语言、排行榜、周报、补签、会员到期拦截、webhook、用户搜索、多角色功能。
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

# ==================== 多语言 ====================
# 语言代码：zh 中文 / en 英文 / ja 日文 / fr 法文 / ru 俄文 / es 西班牙文 / ar 阿拉伯文
LANG_PACKS = {
"zh": {
    "language":"语言 / Language","app_title":"学习打卡系统",
    "login":"登录","register":"注册","find_pwd":"找回密码","username":"用户名","password":"密码",
    "set_username":"设置用户名","set_pwd":"设置密码","confirm_pwd":"确认密码",
    "security_q":"密保问题 (如：我的幸运数字？)","security_a":"密保答案",
    "login_btn":"登录","register_btn":"注册","reset_btn":"确认重置密码",
    "wrong_creds":"用户名或密码错误","fill_all":"请填写所有字段（含密保）","pwd_mismatch":"密码不一致",
    "reserved_name":"该用户名为系统保留，请换一个","user_exists":"用户名已存在",
    "register_ok":"注册成功！已为您分配 3 天内测体验。请去登录。",
    "no_security_q":"该账户未设置密保问题，请联系管理员重置密码。","user_not_exist":"该用户名不存在",
    "reset_ok":"密码重置成功！请去登录。","wrong_answer":"密保答案错误！",
    "reset_intro":"输入用户名，验证密保问题后重设密码。","input_username":"请输入你的用户名","new_password":"新密码",
    "pwd_req": "🔐 密码要求：至少 6 位，建议包含字母和数字；不能使用 123456",
    "pwd_err_empty": "密码不能为空",
    "pwd_err_too_short": "密码长度不能少于 6 位",
    "pwd_err_too_long": "密码长度不能超过 72 位",
    "pwd_err_default": "不能使用默认密码 123456",
    "pwd_err_all_digits": "密码不能为纯数字，建议包含字母和数字",
    "op_failed":"操作失败，请稍后重试。","db_failed":"数据库连接失败，请稍后重试。",
    "sidebar_title":"学习打卡","mobile_mode":"📱 手机精简模式","current_identity":"当前身份",
    "local_time":"当地时间","makeup_cards":"🎫 补签卡","available_points":"当前可用积分",
    "timer":"专注计时器 (番茄钟)","badges":"我的成就徽章","no_badges":"暂无徽章。","points_detail":"积分明细",
    "checkin_pts":"打卡","longterm_pts":"长期","exam_pts":"考试","extra_pts":"偶发","special_pts":"特殊","spent_pts":"消耗",
    "account_settings":"账号与数据设置","timezone":"时区设置","select_timezone":"所在地区/时区","custom_tz":"自定义时区",
    "tz_offset":"输入 UTC 偏移小时数","save_tz":"保存时区设置","new_username":"新用户名","leave_blank":"留空则不修改",
    "change_username":"确认修改用户名","change_pwd":"确认修改密码","change_security":"修改密保",
    "new_security_q":"新密保问题","new_security_a":"新密保答案","save_security":"保存密保",
    "webhook":"防遗忘提醒 Webhook","save_webhook":"保存 Webhook","export_data":"📥 导出我的数据 (JSON)","logout_btn":"退出登录",
    "select_child":"选择你要管理/查看的孩子","admin_select_target":"管理员特权：选择操作对象",
    "penetrate":"穿透管理","no_children_bound":"暂无绑定的孩子，请联系管理员绑定。",
    "role_admin":"管理员","role_host":"家长","role_user":"孩子","role_solo":"独立用户",
    "remaining":"剩余","permanent":"永久","expired":"已过期",
    "tab_checkin":"打卡","tab_extra":"偶发","tab_history":"历史与图表","tab_shop":"商城","tab_redeem":"兑换",
    "tab_exam":"考试","tab_event":"事件","tab_settings":"系统设置","tab_leaderboard":"排行榜",
    "search_users":"🔍 搜索用户名","search_children":"🔍 搜索孩子","no_match":"无匹配用户",
    "no_tasks_today":"今日还没有配置任务哦，请去【系统设置】里添加！",
    "basic_req":"基本要求","full_req":"满分","today_done":"今日已完成打卡，记录已锁定。",
    "undo_checkin":"撤销今日打卡（重新填写）","base_score":"基础分","today_total":"今日总分",
    "est_total":"预计总分","save_checkin":"保存今日打卡","saved":"已保存！","bonus":"Bonus",
    "shop_empty":"商城空！","redeem_btn":"兑换","confirm_deduct":"确认扣除",
    "points_insufficient":"积分不足，兑换失败。","redeem_ok":"兑换成功！","redeem_history":"兑换历史","none_yet":"暂无",
    "cancel":"取消","backup_card":"补签卡",
    "history_title":"历史与图表分析","checkin_hist_detail":"历史打卡详情","select_date":"选择日期",
    "time_view":"时间维度","by_day":"按日查看","by_week":"按周查看","by_month":"按月查看",
    "no_data":"暂无数据。","no_record":"暂无记录。","done_items":"完成项：",
    "weekly_report":"### 📊 专属学习周报","week_checkin":"本周打卡","week_total":"本周总分",
    "day_max":"单日最高","gen_report":"📸 生成并下载专属周报图","save_report":"⬇️ 点击保存图片 (发送到微信群)",
    "report_ok":"图片已生成，点击上方按钮保存并发送给家长吧！","report_failed":"生成图片失败，请稍后重试。",
    "makeup_intro":"🎫 **当前配置对象有 {n} 张补签卡，可用于补全最近 7 天内漏掉的打卡：**",
    "makeup_pick_date":"选择要补签的日期","makeup_pick_tasks":"**请勾选你在 {d} 实际完成的任务（提交后将强制算作满分）：**",
    "makeup_submit":"使用 1 张补签卡并提交","makeup_ok":"补签成功！","makeup_fail":"补签失败，请重试。",
    "makeup_no_miss":"最近 7 天全勤！","makeup_tip":"💡 提示：商城有售「补签卡」。",
    "makeup_host_tip":"💡 补签请让孩子在自己的账号里操作。",
    "makeup_host_self":"💡 该账号为家长，请切换选择其名下的孩子进行操作。",
    "exam_title":"考试专项","exam_no_subject":"未设置考试科目！",
    "exam_score":"(满分 {max}, 目标 {target})","exam_grade":"(目标 {target})",
    "exam_ranks":"**语数外排名前百分之多少（填100不参与）**",
    "exam_cn":"语文","exam_ma":"数学","exam_en":"英语",
    "exam_estimate":"### 预计获得：**{pts}** 分（达成 {hits} 门）","exam_save":"保存本次成绩",
    "exam_saved":"已保存！","exam_hit":"达成 {sub} -> +{pts}","exam_over":"  {sub} 超目标 {n} 档 -> +{pts}",
    "exam_up":"  {sub} 升 {n} 档 -> +{pts}","exam_multi":"达成 {n} 门及以上 -> +{pts}",
    "exam_rank":"{sub} 前{pct}% -> +{pts}","exam_rank_more":"  再进{n}档 -> +{pts}",
    "event_title":"特殊事件","event_fired":"今天已经触发过啦：{note} +{pts}分",
    "event_confirm":"🎲 确认消耗今天的机会摇一摇吗？","event_roll":"确认摇一摇","event_roll_btn":"摇一摇",
    "event_got":"获得 {pts} 积分！","event_note":"积分暴击",
    "extra_title":"偶发事件加/扣分","extra_name":"事件名称","extra_points":"分数 (可为负数)",
    "extra_submit":"确认提交","extra_saved":"已记录：{name} ({pts}分)",
    "extra_clear":"清空偶发记录","extra_none":"暂无记录",
    "extra_only_parent":"只有家长或管理员才能添加偶发事件哦。",
    "lb_title":"🏆 兄弟姐妹排行榜","lb_period":"周期","lb_day":"日榜","lb_month":"月榜","lb_total":"总榜",
    "lb_score":"分","lb_no_data":"暂无排行数据","lb_you":"(你)",
    "lb_only_you":"暂无其他兄弟姐妹参与排行，邀请他们一起来比拼吧！",
    "redeem_tip_expired":"【{user}】的内测体验已到期，请向管理员索取兑换码续费。",
    "redeem_code":"请输入兑换码","redeem_activate":"激活","redeem_invalid":"无效或已被使用的兑换码。",
    "redeem_success":"激活成功！","redeem_fail":"激活失败，请检查兑换码或稍后重试。",
    "time_arrive":"时间到！",
    "weekday_short":["周一","周二","周三","周四","周五","周六","周日"],
},
"en": {
    "language":"Language / 语言","app_title":"Study Check-in",
    "login":"Login","register":"Register","find_pwd":"Reset Password","username":"Username","password":"Password",
    "set_username":"Username","set_pwd":"Password","confirm_pwd":"Confirm Password",
    "security_q":"Security Question (e.g. My lucky number?)","security_a":"Security Answer",
    "login_btn":"Sign In","register_btn":"Sign Up","reset_btn":"Reset Password",
    "wrong_creds":"Incorrect username or password","fill_all":"Please fill in all fields (including security question)",
    "pwd_mismatch":"Passwords do not match","reserved_name":"This username is reserved.",
    "user_exists":"Username already exists","register_ok":"Registered! 3-day trial assigned. Please log in.",
    "no_security_q":"This account has no security question. Please contact admin.","user_not_exist":"Username does not exist",
    "reset_ok":"Password reset successfully! Please log in.","wrong_answer":"Security answer is incorrect!",
    "reset_intro":"Enter username, verify security question, then set a new password.",
    "input_username":"Enter your username","new_password":"New Password",
    "pwd_req": "🔐 Password: at least 6 chars, letters + digits recommended; 123456 not allowed",
    "pwd_err_empty": "Password cannot be empty",
    "pwd_err_too_short": "Password must be at least 6 characters",
    "pwd_err_too_long": "Password must be at most 72 characters",
    "pwd_err_default": "Default password 123456 is not allowed",
    "pwd_err_all_digits": "All-digit password not allowed; mix letters and digits",
    "op_failed":"Operation failed. Please try again later.","db_failed":"Database connection failed. Please try again later.",
    "sidebar_title":"Study Check-in","mobile_mode":"📱 Mobile Mode","current_identity":"Signed in as",
    "local_time":"Local time","makeup_cards":"🎫 Makeup Cards","available_points":"Available Points",
    "timer":"Focus Timer (Pomodoro)","badges":"My Badges","no_badges":"No badges yet.","points_detail":"Points Detail",
    "checkin_pts":"Check-in","longterm_pts":"Long-term","exam_pts":"Exam","extra_pts":"Extra","special_pts":"Special","spent_pts":"Spent",
    "account_settings":"Account & Data","timezone":"Timezone","select_timezone":"Region / Timezone","custom_tz":"Custom",
    "tz_offset":"Enter UTC offset (hours)","save_tz":"Save Timezone","new_username":"New Username","leave_blank":"Leave blank to keep current",
    "change_username":"Change Username","change_pwd":"Change Password","change_security":"Change Security",
    "new_security_q":"New Security Question","new_security_a":"New Security Answer","save_security":"Save Security",
    "webhook":"Reminder Webhook","save_webhook":"Save Webhook","export_data":"📥 Export My Data (JSON)","logout_btn":"Log Out",
    "select_child":"Select a child to manage/view","admin_select_target":"Admin: Select Target User",
    "penetrate":"Drill-down","no_children_bound":"No child bound. Please contact admin.",
    "role_admin":"Admin","role_host":"Parent","role_user":"Child","role_solo":"Solo",
    "remaining":"Remaining","permanent":"Lifetime","expired":"Expired",
    "tab_checkin":"Check-in","tab_extra":"Extra","tab_history":"History","tab_shop":"Shop","tab_redeem":"Redeem",
    "tab_exam":"Exam","tab_event":"Event","tab_settings":"Settings","tab_leaderboard":"Leaderboard",
    "search_users":"🔍 Search users","search_children":"🔍 Search children","no_match":"No matching user",
    "no_tasks_today":"No tasks configured for today. Please add them in Settings.",
    "basic_req":"Basic requirement","full_req":"Full mark","today_done":"Today's check-in is done and locked.",
    "undo_checkin":"Undo today's check-in","base_score":"Base Score","today_total":"Today Total",
    "est_total":"Estimated Total","save_checkin":"Save Check-in","saved":"Saved!","bonus":"Bonus",
    "shop_empty":"Shop is empty.","redeem_btn":"Redeem","confirm_deduct":"Confirm Deduct",
    "points_insufficient":"Not enough points.","redeem_ok":"Redeemed!","redeem_history":"Redemption History","none_yet":"None",
    "cancel":"Cancel","backup_card":"Makeup Card",
    "history_title":"History & Charts","checkin_hist_detail":"Check-in Detail","select_date":"Select date",
    "time_view":"Time View","by_day":"Daily","by_week":"Weekly","by_month":"Monthly",
    "no_data":"No data yet.","no_record":"No records.","done_items":"Done:",
    "weekly_report":"### 📊 Weekly Report","week_checkin":"Days this week","week_total":"Weekly total",
    "day_max":"Day max","gen_report":"📸 Generate & Download Weekly Report","save_report":"⬇️ Download image",
    "report_ok":"Report generated. Click above to save and share!","report_failed":"Failed to generate image.",
    "makeup_intro":"🎫 **{n} makeup card(s) available for the last 7 days:**",
    "makeup_pick_date":"Pick a date to makeup","makeup_pick_tasks":"**Check tasks completed on {d} (will be counted as full score):**",
    "makeup_submit":"Use 1 makeup card & submit","makeup_ok":"Makeup succeeded!","makeup_fail":"Makeup failed. Try again.",
    "makeup_no_miss":"Full attendance in the last 7 days!","makeup_tip":"💡 Tip: Buy makeup cards from the shop.",
    "makeup_host_tip":"💡 Makeup should be done by the child on their own account.",
    "makeup_host_self":"💡 This is a parent account. Switch to a child.",
    "exam_title":"Exam","exam_no_subject":"No subjects configured!",
    "exam_score":"(max {max}, target {target})","exam_grade":"(target {target})",
    "exam_ranks":"**Top % in Chinese/Math/English (fill 100 to skip)**",
    "exam_cn":"Chinese","exam_ma":"Math","exam_en":"English",
    "exam_estimate":"### Estimated: **{pts}** pts ({hits} subject(s) hit)","exam_save":"Save exam result",
    "exam_saved":"Saved!","exam_hit":"Hit {sub} -> +{pts}","exam_over":"  {sub} exceeded by {n} tiers -> +{pts}",
    "exam_up":"  {sub} up {n} grades -> +{pts}","exam_multi":"Hit {n} subjects -> +{pts}",
    "exam_rank":"{sub} top {pct}% -> +{pts}","exam_rank_more":"  {n} more tier(s) -> +{pts}",
    "event_title":"Special Events","event_fired":"Already triggered today: {note} +{pts}pts",
    "event_confirm":"🎲 Consume today's chance to roll?","event_roll":"Confirm Roll","event_roll_btn":"Roll",
    "event_got":"Got {pts} points!","event_note":"Point Burst",
    "extra_title":"Extra Points","extra_name":"Event Name","extra_points":"Points (can be negative)",
    "extra_submit":"Submit","extra_saved":"Recorded: {name} ({pts}pts)",
    "extra_clear":"Clear extra records","extra_none":"No records",
    "extra_only_parent":"Only parents or admins can add extra events.",
    "lb_title":"🏆 Sibling Leaderboard","lb_period":"Period","lb_day":"Daily","lb_month":"Monthly","lb_total":"All-time",
    "lb_score":"pts","lb_no_data":"No leaderboard data yet","lb_you":"(you)",
    "lb_only_you":"No other siblings yet. Invite them to compete!",
    "redeem_tip_expired":"Trial of [{user}] has expired. Ask admin for a redeem code.",
    "redeem_code":"Enter redeem code","redeem_activate":"Activate","redeem_invalid":"Invalid or already-used code.",
    "redeem_success":"Activated!","redeem_fail":"Activation failed. Please try again.",
    "time_arrive":"Time's up!",
    "weekday_short":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
},
"ja": {
    "language":"言語 / Language","app_title":"学習チェックイン",
    "login":"ログイン","register":"新規登録","find_pwd":"パスワード再設定","username":"ユーザー名","password":"パスワード",
    "set_username":"ユーザー名","set_pwd":"パスワード","confirm_pwd":"パスワード確認",
    "security_q":"秘密の質問 (例：ラッキーナンバーは？)","security_a":"秘密の答え",
    "login_btn":"ログイン","register_btn":"登録","reset_btn":"パスワードをリセット",
    "wrong_creds":"ユーザー名またはパスワードが違います","fill_all":"すべての項目を入力してください","pwd_mismatch":"パスワードが一致しません",
    "reserved_name":"このユーザー名は予約されています","user_exists":"ユーザー名は既に存在します",
    "register_ok":"登録完了！3日間のトライアルです。ログインしてください。",
    "no_security_q":"秘密の質問が未設定です。管理者に連絡してください。","user_not_exist":"ユーザーが存在しません",
    "reset_ok":"パスワードを再設定しました！ログインしてください。","wrong_answer":"秘密の答えが違います",
    "reset_intro":"ユーザー名を入力し、秘密の質問を検証して新しいパスワードを設定します。",
    "input_username":"ユーザー名を入力","new_password":"新パスワード",
    "pwd_req": "🔐 パスワード：6文字以上、英数字推奨；123456 は使用不可",
    "pwd_err_empty": "パスワードを入力してください",
    "pwd_err_too_short": "パスワードは6文字以上必要です",
    "pwd_err_too_long": "パスワードは72文字以内にしてください",
    "pwd_err_default": "初期パスワード 123456 は使用できません",
    "pwd_err_all_digits": "数字のみのパスワードは不可、英字と数字を混ぜてください",
    "op_failed":"操作に失敗しました。後でもう一度お試しください。","db_failed":"データベース接続に失敗しました。",
    "sidebar_title":"学習チェックイン","mobile_mode":"📱 モバイル簡易モード","current_identity":"ログイン中",
    "local_time":"現地時間","makeup_cards":"🎫 補填カード","available_points":"利用可能ポイント",
    "timer":"集中タイマー (ポモドーロ)","badges":"実績バッジ","no_badges":"バッジなし","points_detail":"ポイント詳細",
    "checkin_pts":"チェックイン","longterm_pts":"長期","exam_pts":"試験","extra_pts":"臨時","special_pts":"特殊","spent_pts":"使用",
    "account_settings":"アカウントとデータ","timezone":"タイムゾーン","select_timezone":"地域 / タイムゾーン","custom_tz":"カスタム",
    "tz_offset":"UTC オフセット (時間)","save_tz":"タイムゾーンを保存","new_username":"新ユーザー名","leave_blank":"空欄で変更なし",
    "change_username":"ユーザー名を変更","change_pwd":"パスワードを変更","change_security":"秘密の質問を変更",
    "new_security_q":"新しい秘密の質問","new_security_a":"新しい秘密の答え","save_security":"保存",
    "webhook":"リマインダー Webhook","save_webhook":"Webhook を保存","export_data":"📥 データをエクスポート (JSON)","logout_btn":"ログアウト",
    "select_child":"管理/閲覧するお子様を選択","admin_select_target":"管理者：操作対象を選択",
    "penetrate":"ドリルダウン","no_children_bound":"お子様が紐付けられていません。管理者に連絡してください。",
    "role_admin":"管理者","role_host":"保護者","role_user":"子供","role_solo":"個人ユーザー",
    "remaining":"残り","permanent":"永久","expired":"期限切れ",
    "tab_checkin":"チェックイン","tab_extra":"臨時","tab_history":"履歴・グラフ","tab_shop":"ショップ","tab_redeem":"交換",
    "tab_exam":"試験","tab_event":"イベント","tab_settings":"設定","tab_leaderboard":"ランキング",
    "search_users":"🔍 ユーザー検索","search_children":"🔍 子供を検索","no_match":"一致するユーザーなし",
    "no_tasks_today":"今日のタスクが未設定です。設定から追加してください。",
    "basic_req":"基本要件","full_req":"満点","today_done":"本日のチェックインは完了しました。",
    "undo_checkin":"本日のチェックインを取り消す","base_score":"基本点","today_total":"本日合計",
    "est_total":"予測合計","save_checkin":"チェックインを保存","saved":"保存しました！","bonus":"ボーナス",
    "shop_empty":"ショップが空です。","redeem_btn":"交換","confirm_deduct":"確認して差し引く",
    "points_insufficient":"ポイント不足です。","redeem_ok":"交換しました！","redeem_history":"交換履歴","none_yet":"なし",
    "cancel":"キャンセル","backup_card":"補填カード",
    "history_title":"履歴とグラフ分析","checkin_hist_detail":"チェックイン詳細","select_date":"日付を選択",
    "time_view":"時間軸","by_day":"日別","by_week":"週別","by_month":"月別",
    "no_data":"データなし","no_record":"記録なし","done_items":"完了項目：",
    "weekly_report":"### 📊 週次レポート","week_checkin":"今週のチェックイン","week_total":"今週の合計",
    "day_max":"一日最大","gen_report":"📸 週次レポートを生成・ダウンロード","save_report":"⬇️ 画像をダウンロード",
    "report_ok":"レポートを生成しました。","report_failed":"画像生成に失敗しました。",
    "makeup_intro":"🎫 **補填カード {n} 枚。過去7日以内の漏れを補えます：**",
    "makeup_pick_date":"補填する日付を選択","makeup_pick_tasks":"**{d} に完了したタスクを選択（満点扱い）：**",
    "makeup_submit":"補填カード1枚使用して送信","makeup_ok":"補填成功！","makeup_fail":"補填失敗。再度お試しください。",
    "makeup_no_miss":"過去7日間、全出席です！","makeup_tip":"💡 ヒント：ショップで補填カード購入可。",
    "makeup_host_tip":"💡 補填はお子様のアカウントで行ってください。",
    "makeup_host_self":"💡 保護者アカウントです。子供を選択してください。",
    "exam_title":"試験専用","exam_no_subject":"試験科目が未設定です！",
    "exam_score":"(満点 {max}, 目標 {target})","exam_grade":"(目標 {target})",
    "exam_ranks":"**国語/数学/英語の上位%（100は無効）**",
    "exam_cn":"国語","exam_ma":"数学","exam_en":"英語",
    "exam_estimate":"### 予測：**{pts}** 点（達成 {hits} 科目）","exam_save":"結果を保存",
    "exam_saved":"保存しました！","exam_hit":"{sub} 達成 -> +{pts}","exam_over":"  {sub} {n}段階超え -> +{pts}",
    "exam_up":"  {sub} {n}段階アップ -> +{pts}","exam_multi":"{n}科目以上達成 -> +{pts}",
    "exam_rank":"{sub} 上位{pct}% -> +{pts}","exam_rank_more":"  {n}段階アップ -> +{pts}",
    "event_title":"特殊イベント","event_fired":"本日は既に発動済み：{note} +{pts}点",
    "event_confirm":"🎲 本日のチャンスを消費して回しますか？","event_roll":"回す","event_roll_btn":"回す",
    "event_got":"{pts} ポイント獲得！","event_note":"ポイントバースト",
    "extra_title":"臨時ポイント加減","extra_name":"イベント名","extra_points":"ポイント (負数可)",
    "extra_submit":"送信","extra_saved":"記録：{name} ({pts}点)",
    "extra_clear":"臨時記録をクリア","extra_none":"記録なし",
    "extra_only_parent":"保護者/管理者のみ追加できます。",
    "lb_title":"🏆 兄弟ランキング","lb_period":"期間","lb_day":"日間","lb_month":"月間","lb_total":"総合",
    "lb_score":"点","lb_no_data":"ランキングデータなし","lb_you":"(あなた)",
    "lb_only_you":"兄弟がいません。招待しましょう！",
    "redeem_tip_expired":"【{user}】のトライアル期限切れ。管理者にコードを請求してください。",
    "redeem_code":"コードを入力","redeem_activate":"有効化","redeem_invalid":"無効または使用済みコード",
    "redeem_success":"有効化成功！","redeem_fail":"有効化に失敗しました。",
    "time_arrive":"時間です！",
    "weekday_short":["月","火","水","木","金","土","日"],
},
"fr": {
    "language":"Langue / Language","app_title":"Suivi d'études",
    "login":"Connexion","register":"Inscription","find_pwd":"Réinitialiser","username":"Nom d'utilisateur","password":"Mot de passe",
    "set_username":"Nom d'utilisateur","set_pwd":"Mot de passe","confirm_pwd":"Confirmer mot de passe",
    "security_q":"Question de sécurité","security_a":"Réponse de sécurité",
    "login_btn":"Connexion","register_btn":"S'inscrire","reset_btn":"Réinitialiser",
    "wrong_creds":"Nom ou mot de passe incorrect","fill_all":"Remplissez tous les champs","pwd_mismatch":"Mots de passe différents",
    "reserved_name":"Nom réservé","user_exists":"Nom déjà utilisé","register_ok":"Inscription réussie ! Essai de 3 jours.",
    "no_security_q":"Pas de question de sécurité. Contactez l'admin.","user_not_exist":"Utilisateur inexistant",
    "reset_ok":"Mot de passe réinitialisé !","wrong_answer":"Réponse incorrecte",
    "reset_intro":"Entrez le nom, vérifiez la question, puis définissez un nouveau mot de passe.",
    "input_username":"Entrez votre nom","new_password":"Nouveau mot de passe",
    "pwd_req": "🔐 Mot de passe : au moins 6 caractères, lettres + chiffres recommandés ; 123456 interdit",
    "pwd_err_empty": "Le mot de passe ne peut pas être vide",
    "pwd_err_too_short": "Le mot de passe doit contenir au moins 6 caractères",
    "pwd_err_too_long": "Le mot de passe ne peut dépasser 72 caractères",
    "pwd_err_default": "Le mot de passe par défaut 123456 est interdit",
    "pwd_err_all_digits": "Mot de passe tout en chiffres interdit ; mélangez lettres et chiffres",
    "op_failed":"Opération échouée.","db_failed":"Échec de connexion à la base.",
    "sidebar_title":"Suivi d'études","mobile_mode":"📱 Mode mobile","current_identity":"Connecté :",
    "local_time":"Heure locale","makeup_cards":"🎫 Cartes rattrapage","available_points":"Points disponibles",
    "timer":"Minuteur (Pomodoro)","badges":"Mes badges","no_badges":"Aucun badge","points_detail":"Détail des points",
    "checkin_pts":"Check","longterm_pts":"Long terme","exam_pts":"Examen","extra_pts":"Extra","special_pts":"Spécial","spent_pts":"Dépensé",
    "account_settings":"Compte & Données","timezone":"Fuseau horaire","select_timezone":"Région / Fuseau","custom_tz":"Personnalisé",
    "tz_offset":"Décalage UTC (h)","save_tz":"Enregistrer","new_username":"Nouveau nom","leave_blank":"Vide = inchangé",
    "change_username":"Changer le nom","change_pwd":"Changer le mot de passe","change_security":"Changer sécurité",
    "new_security_q":"Nouvelle question","new_security_a":"Nouvelle réponse","save_security":"Enregistrer",
    "webhook":"Rappel Webhook","save_webhook":"Enregistrer","export_data":"📥 Exporter (JSON)","logout_btn":"Déconnexion",
    "select_child":"Sélectionner un enfant","admin_select_target":"Admin : Sélectionner la cible",
    "penetrate":"Percer","no_children_bound":"Aucun enfant lié. Contactez l'admin.",
    "role_admin":"Admin","role_host":"Parent","role_user":"Enfant","role_solo":"Solo",
    "remaining":"Restant","permanent":"À vie","expired":"Expiré",
    "tab_checkin":"Check","tab_extra":"Extra","tab_history":"Historique","tab_shop":"Boutique","tab_redeem":"Échange",
    "tab_exam":"Examen","tab_event":"Événement","tab_settings":"Paramètres","tab_leaderboard":"Classement",
    "search_users":"🔍 Rechercher","search_children":"🔍 Rechercher enfants","no_match":"Aucun utilisateur",
    "no_tasks_today":"Aucune tâche aujourd'hui. Ajoutez-les dans Paramètres.",
    "basic_req":"Exigence de base","full_req":"Note parfaite","today_done":"Check-in du jour terminé.",
    "undo_checkin":"Annuler le check-in","base_score":"Points de base","today_total":"Total du jour",
    "est_total":"Total estimé","save_checkin":"Enregistrer","saved":"Enregistré !","bonus":"Bonus",
    "shop_empty":"Boutique vide.","redeem_btn":"Échanger","confirm_deduct":"Confirmer",
    "points_insufficient":"Points insuffisants.","redeem_ok":"Échangé !","redeem_history":"Historique des échanges","none_yet":"Aucun",
    "cancel":"Annuler","backup_card":"Carte rattrapage",
    "history_title":"Historique & Graphiques","checkin_hist_detail":"Détail du check-in","select_date":"Choisir une date",
    "time_view":"Vue temporelle","by_day":"Quotidien","by_week":"Hebdomadaire","by_month":"Mensuel",
    "no_data":"Aucune donnée","no_record":"Aucun enregistrement","done_items":"Terminé :",
    "weekly_report":"### 📊 Rapport hebdomadaire","week_checkin":"Jours cette semaine","week_total":"Total semaine",
    "day_max":"Max du jour","gen_report":"📸 Générer & Télécharger le rapport","save_report":"⬇️ Télécharger l'image",
    "report_ok":"Rapport généré.","report_failed":"Échec de génération.",
    "makeup_intro":"🎫 **{n} carte(s) rattrapage disponible(s) :**",
    "makeup_pick_date":"Choisir une date","makeup_pick_tasks":"**Cochez les tâches faites le {d} :**",
    "makeup_submit":"Utiliser 1 carte","makeup_ok":"Rattrapage réussi !","makeup_fail":"Échec du rattrapage.",
    "makeup_no_miss":"Présence complète sur 7 jours !","makeup_tip":"💡 Astuce : cartes rattrapage en boutique.",
    "makeup_host_tip":"💡 Le rattrapage doit être fait par l'enfant.","makeup_host_self":"💡 Compte parent. Changez d'enfant.",
    "exam_title":"Examens","exam_no_subject":"Aucune matière configurée !",
    "exam_score":"(max {max}, cible {target})","exam_grade":"(cible {target})",
    "exam_ranks":"**Top % en Chinois/Maths/Anglais (100 = skip)**",
    "exam_cn":"Chinois","exam_ma":"Maths","exam_en":"Anglais",
    "exam_estimate":"### Estimé : **{pts}** pts ({hits} matière(s))","exam_save":"Enregistrer le résultat",
    "exam_saved":"Enregistré !","exam_hit":"{sub} atteint -> +{pts}","exam_over":"  {sub} +{n} paliers -> +{pts}",
    "exam_up":"  {sub} +{n} niveaux -> +{pts}","exam_multi":"{n}+ matières -> +{pts}",
    "exam_rank":"{sub} top {pct}% -> +{pts}","exam_rank_more":"  +{n} paliers -> +{pts}",
    "event_title":"Événements spéciaux","event_fired":"Déjà déclenché : {note} +{pts}pts",
    "event_confirm":"🎲 Consommer la chance du jour ?","event_roll":"Confirmer","event_roll_btn":"Lancer",
    "event_got":"+{pts} points !","event_note":"Bonus de points",
    "extra_title":"Points extra","extra_name":"Nom","extra_points":"Points (négatif ok)",
    "extra_submit":"Soumettre","extra_saved":"Noté : {name} ({pts}pts)",
    "extra_clear":"Effacer","extra_none":"Aucun",
    "extra_only_parent":"Parents/admins uniquement.",
    "lb_title":"🏆 Classement frères/sœurs","lb_period":"Période","lb_day":"Jour","lb_month":"Mois","lb_total":"Total",
    "lb_score":"pts","lb_no_data":"Pas de classement","lb_you":"(vous)",
    "lb_only_you":"Pas d'autres frères/sœurs.",
    "redeem_tip_expired":"Essai de [{user}] expiré. Demandez un code à l'admin.",
    "redeem_code":"Code","redeem_activate":"Activer","redeem_invalid":"Code invalide ou utilisé",
    "redeem_success":"Activé !","redeem_fail":"Échec d'activation.",
    "time_arrive":"Temps écoulé !",
    "weekday_short":["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"],
},
"ru": {
    "language":"Язык / Language","app_title":"Учёба",
    "login":"Вход","register":"Регистрация","find_pwd":"Сброс пароля","username":"Имя","password":"Пароль",
    "set_username":"Имя","set_pwd":"Пароль","confirm_pwd":"Пароль ещё раз",
    "security_q":"Секретный вопрос","security_a":"Секретный ответ",
    "login_btn":"Войти","register_btn":"Зарегистрироваться","reset_btn":"Сбросить",
    "wrong_creds":"Неверное имя или пароль","fill_all":"Заполните все поля","pwd_mismatch":"Пароли не совпадают",
    "reserved_name":"Имя зарезервировано","user_exists":"Имя занято","register_ok":"Готово! Пробный период 3 дня.",
    "no_security_q":"Нет секретного вопроса. Свяжитесь с админом.","user_not_exist":"Пользователь не найден",
    "reset_ok":"Пароль сброшен!","wrong_answer":"Неверный ответ",
    "reset_intro":"Введите имя, проверьте вопрос, задайте новый пароль.",
    "input_username":"Введите имя","new_password":"Новый пароль",
    "pwd_req": "🔐 Пароль: не менее 6 символов, буквы + цифры; 123456 запрещён",
    "pwd_err_empty": "Пароль не может быть пустым",
    "pwd_err_too_short": "Пароль должен содержать не менее 6 символов",
    "pwd_err_too_long": "Пароль не должен превышать 72 символа",
    "pwd_err_default": "Пароль по умолчанию 123456 запрещён",
    "pwd_err_all_digits": "Только цифры запрещены; смешивайте буквы и цифры",
    "op_failed":"Операция не удалась.","db_failed":"Ошибка подключения к БД.",
    "sidebar_title":"Учёба","mobile_mode":"📱 Мобильный режим","current_identity":"Вы вошли как",
    "local_time":"Местное время","makeup_cards":"🎫 Карты補填","available_points":"Доступные баллы",
    "timer":"Таймер (Помодоро)","badges":"Мои значки","no_badges":"Нет значков","points_detail":"Детали баллов",
    "checkin_pts":"Отметка","longterm_pts":"Долгосрочные","exam_pts":"Экзамен","extra_pts":"Прочее","special_pts":"Особое","spent_pts":"Потрачено",
    "account_settings":"Аккаунт и данные","timezone":"Часовой пояс","select_timezone":"Регион / Пояс","custom_tz":"Другой",
    "tz_offset":"Смещение UTC (ч)","save_tz":"Сохранить","new_username":"Новое имя","leave_blank":"Пусто = без изменений",
    "change_username":"Изменить имя","change_pwd":"Изменить пароль","change_security":"Изменить вопрос",
    "new_security_q":"Новый вопрос","new_security_a":"Новый ответ","save_security":"Сохранить",
    "webhook":"Webhook напоминаний","save_webhook":"Сохранить","export_data":"📥 Экспорт (JSON)","logout_btn":"Выйти",
    "select_child":"Выберите ребёнка","admin_select_target":"Админ: выберите цель",
    "penetrate":"Проникнуть","no_children_bound":"Нет привязанных детей.",
    "role_admin":"Админ","role_host":"Родитель","role_user":"Ребёнок","role_solo":"Соло",
    "remaining":"Осталось","permanent":"Навсегда","expired":"Истёк",
    "tab_checkin":"Отметка","tab_extra":"Прочее","tab_history":"История","tab_shop":"Магазин","tab_redeem":"Обмен",
    "tab_exam":"Экзамен","tab_event":"Событие","tab_settings":"Настройки","tab_leaderboard":"Рейтинг",
    "search_users":"🔍 Поиск","search_children":"🔍 Поиск детей","no_match":"Не найдено",
    "no_tasks_today":"Нет задач на сегодня. Добавьте в настройках.",
    "basic_req":"Базовое","full_req":"Максимум","today_done":"Отметка завершена.",
    "undo_checkin":"Отменить отметку","base_score":"Базовые баллы","today_total":"Итого за день",
    "est_total":"Прогноз","save_checkin":"Сохранить","saved":"Сохранено!","bonus":"Бонус",
    "shop_empty":"Магазин пуст.","redeem_btn":"Обменять","confirm_deduct":"Списать",
    "points_insufficient":"Недостаточно баллов.","redeem_ok":"Обменяно!","redeem_history":"История обмена","none_yet":"Нет",
    "cancel":"Отмена","backup_card":"Карта補填",
    "history_title":"История и графики","checkin_hist_detail":"Детали отметки","select_date":"Выберите дату",
    "time_view":"Вид","by_day":"По дням","by_week":"По неделям","by_month":"По месяцам",
    "no_data":"Нет данных","no_record":"Нет записей","done_items":"Выполнено:",
    "weekly_report":"### 📊 Недельный отчёт","week_checkin":"Дней за неделю","week_total":"Итого за неделю",
    "day_max":"Максимум за день","gen_report":"📸 Создать и скачать отчёт","save_report":"⬇️ Скачать картинку",
    "report_ok":"Отчёт готов.","report_failed":"Ошибка генерации.",
    "makeup_intro":"🎫 **Доступно карт: {n}**",
    "makeup_pick_date":"Выберите дату","makeup_pick_tasks":"**Отметьте задачи за {d}:**",
    "makeup_submit":"Использовать карту","makeup_ok":"Готово!","makeup_fail":"Ошибка",
    "makeup_no_miss":"Полная посещаемость 7 дней!","makeup_tip":"💡 Карты в магазине.",
    "makeup_host_tip":"💡 Заполнять должен ребёнок.","makeup_host_self":"💡 Родительский аккаунт. Переключите.",
    "exam_title":"Экзамены","exam_no_subject":"Нет предметов!",
    "exam_score":"(макс {max}, цель {target})","exam_grade":"(цель {target})",
    "exam_ranks":"**Top % в языках/матем/англ (100 = пропуск)**",
    "exam_cn":"Кит. язык","exam_ma":"Математика","exam_en":"Английский",
    "exam_estimate":"### Прогноз: **{pts}** баллов ({hits})","exam_save":"Сохранить результат",
    "exam_saved":"Сохранено!","exam_hit":"{sub} → +{pts}","exam_over":"  {sub} +{n} уровней → +{pts}",
    "exam_up":"  {sub} на {n} уровней → +{pts}","exam_multi":"{n}+ предметов → +{pts}",
    "exam_rank":"{sub} топ {pct}% → +{pts}","exam_rank_more":"  ещё {n} → +{pts}",
    "event_title":"Специальные события","event_fired":"Уже запущено сегодня: {note} +{pts}",
    "event_confirm":"🎲 Использовать шанс дня?","event_roll":"Подтвердить","event_roll_btn":"Крутить",
    "event_got":"+{pts} баллов!","event_note":"Взрыв баллов",
    "extra_title":"Доп. баллы","extra_name":"Название","extra_points":"Баллы (можно -)",
    "extra_submit":"Отправить","extra_saved":"Записано: {name} ({pts})",
    "extra_clear":"Очистить","extra_none":"Нет",
    "extra_only_parent":"Только родители/админы.",
    "lb_title":"🏆 Рейтинг братьев/сестёр","lb_period":"Период","lb_day":"День","lb_month":"Месяц","lb_total":"Всего",
    "lb_score":"баллов","lb_no_data":"Нет данных","lb_you":"(вы)",
    "lb_only_you":"Пока нет других участников.",
    "redeem_tip_expired":"Пробный период [{user}] истёк. Запросите код у админа.",
    "redeem_code":"Код","redeem_activate":"Активировать","redeem_invalid":"Неверный или уже использован",
    "redeem_success":"Активировано!","redeem_fail":"Ошибка активации.",
    "time_arrive":"Время вышло!",
    "weekday_short":["Пн","Вт","Ср","Чт","Пт","Сб","Вс"],
},
"es": {
    "language":"Idioma / Language","app_title":"Registro de estudios",
    "login":"Iniciar sesión","register":"Registrarse","find_pwd":"Restablecer","username":"Usuario","password":"Contraseña",
    "set_username":"Usuario","set_pwd":"Contraseña","confirm_pwd":"Confirmar contraseña",
    "security_q":"Pregunta secreta","security_a":"Respuesta secreta",
    "login_btn":"Entrar","register_btn":"Registrarse","reset_btn":"Restablecer",
    "wrong_creds":"Usuario o contraseña incorrectos","fill_all":"Complete todos los campos","pwd_mismatch":"Las contraseñas no coinciden",
    "reserved_name":"Nombre reservado","user_exists":"Usuario ya existe","register_ok":"¡Registrado! Prueba de 3 días.",
    "no_security_q":"Sin pregunta secreta. Contacte al admin.","user_not_exist":"Usuario no existe",
    "reset_ok":"¡Contraseña restablecida!","wrong_answer":"Respuesta incorrecta",
    "reset_intro":"Ingrese el usuario, verifique la pregunta y establezca una nueva contraseña.",
    "input_username":"Ingrese su usuario","new_password":"Nueva contraseña",
    "pwd_req": "🔐 Contraseña: al menos 6 caracteres, letras + números recomendado; 123456 prohibido",
    "pwd_err_empty": "La contraseña no puede estar vacía",
    "pwd_err_too_short": "La contraseña debe tener al menos 6 caracteres",
    "pwd_err_too_long": "La contraseña no puede exceder 72 caracteres",
    "pwd_err_default": "La contraseña por defecto 123456 no está permitida",
    "pwd_err_all_digits": "Contraseña solo con dígitos prohibida; combine letras y números",
    "op_failed":"Operación fallida.","db_failed":"Error de conexión a la base de datos.",
    "sidebar_title":"Registro de estudios","mobile_mode":"📱 Modo móvil","current_identity":"Sesión:",
    "local_time":"Hora local","makeup_cards":"🎫 Tarjetas de recuperación","available_points":"Puntos disponibles",
    "timer":"Temporizador (Pomodoro)","badges":"Mis insignias","no_badges":"Sin insignias","points_detail":"Detalle de puntos",
    "checkin_pts":"Registro","longterm_pts":"Largo plazo","exam_pts":"Examen","extra_pts":"Extra","special_pts":"Especial","spent_pts":"Gastado",
    "account_settings":"Cuenta y datos","timezone":"Zona horaria","select_timezone":"Región / Zona","custom_tz":"Personalizada",
    "tz_offset":"Desfase UTC (h)","save_tz":"Guardar","new_username":"Nuevo usuario","leave_blank":"Vacío = sin cambios",
    "change_username":"Cambiar usuario","change_pwd":"Cambiar contraseña","change_security":"Cambiar seguridad",
    "new_security_q":"Nueva pregunta","new_security_a":"Nueva respuesta","save_security":"Guardar",
    "webhook":"Webhook recordatorio","save_webhook":"Guardar","export_data":"📥 Exportar (JSON)","logout_btn":"Cerrar sesión",
    "select_child":"Seleccione un niño","admin_select_target":"Admin: seleccione el objetivo",
    "penetrate":"Perforar","no_children_bound":"Sin niños vinculados.",
    "role_admin":"Admin","role_host":"Padre/Madre","role_user":"Niño","role_solo":"Solo",
    "remaining":"Quedan","permanent":"Permanente","expired":"Caducado",
    "tab_checkin":"Registro","tab_extra":"Extra","tab_history":"Historial","tab_shop":"Tienda","tab_redeem":"Canje",
    "tab_exam":"Examen","tab_event":"Evento","tab_settings":"Ajustes","tab_leaderboard":"Ranking",
    "search_users":"🔍 Buscar usuarios","search_children":"🔍 Buscar niños","no_match":"Sin coincidencias",
    "no_tasks_today":"No hay tareas hoy. Añádalas en Ajustes.",
    "basic_req":"Requisito básico","full_req":"Puntuación máxima","today_done":"Registro de hoy completado.",
    "undo_checkin":"Deshacer registro de hoy","base_score":"Puntos base","today_total":"Total del día",
    "est_total":"Total estimado","save_checkin":"Guardar registro","saved":"¡Guardado!","bonus":"Bono",
    "shop_empty":"Tienda vacía.","redeem_btn":"Canjear","confirm_deduct":"Confirmar",
    "points_insufficient":"Puntos insuficientes.","redeem_ok":"¡Canjeado!","redeem_history":"Historial de canjes","none_yet":"Ninguno",
    "cancel":"Cancelar","backup_card":"Tarjeta de recuperación",
    "history_title":"Historial y gráficas","checkin_hist_detail":"Detalle del registro","select_date":"Elegir fecha",
    "time_view":"Vista temporal","by_day":"Diario","by_week":"Semanal","by_month":"Mensual",
    "no_data":"Sin datos","no_record":"Sin registros","done_items":"Completado:",
    "weekly_report":"### 📊 Informe semanal","week_checkin":"Días esta semana","week_total":"Total semanal",
    "day_max":"Máximo del día","gen_report":"📸 Generar y descargar informe","save_report":"⬇️ Descargar imagen",
    "report_ok":"Informe generado.","report_failed":"Error al generar.",
    "makeup_intro":"🎫 **{n} tarjeta(s) de recuperación disponibles:**",
    "makeup_pick_date":"Elegir fecha","makeup_pick_tasks":"**Marque las tareas del {d}:**",
    "makeup_submit":"Usar 1 tarjeta","makeup_ok":"¡Recuperación exitosa!","makeup_fail":"Error de recuperación.",
    "makeup_no_miss":"¡Asistencia completa 7 días!","makeup_tip":"💡 Tarjetas en la tienda.",
    "makeup_host_tip":"💡 El niño debe hacerlo en su cuenta.","makeup_host_self":"💡 Cuenta de padre/madre. Cambie de niño.",
    "exam_title":"Exámenes","exam_no_subject":"¡Sin materias configuradas!",
    "exam_score":"(máx {max}, objetivo {target})","exam_grade":"(objetivo {target})",
    "exam_ranks":"**Top % en Chino/Matemáticas/Inglés (100 = omitir)**",
    "exam_cn":"Chino","exam_ma":"Matemáticas","exam_en":"Inglés",
    "exam_estimate":"### Estimado: **{pts}** pts ({hits} materia(s))","exam_save":"Guardar resultado",
    "exam_saved":"¡Guardado!","exam_hit":"{sub} alcanzado -> +{pts}","exam_over":"  {sub} +{n} niveles -> +{pts}",
    "exam_up":"  {sub} sube {n} -> +{pts}","exam_multi":"{n}+ materias -> +{pts}",
    "exam_rank":"{sub} top {pct}% -> +{pts}","exam_rank_more":"  +{n} más -> +{pts}",
    "event_title":"Eventos especiales","event_fired":"Ya activado hoy: {note} +{pts}pts",
    "event_confirm":"🎲 ¿Usar el chance de hoy?","event_roll":"Confirmar","event_roll_btn":"Girar",
    "event_got":"¡+{pts} puntos!","event_note":"Explosión de puntos",
    "extra_title":"Puntos extra","extra_name":"Nombre","extra_points":"Puntos (negativo ok)",
    "extra_submit":"Enviar","extra_saved":"Registrado: {name} ({pts}pts)",
    "extra_clear":"Borrar","extra_none":"Ninguno",
    "extra_only_parent":"Solo padres/admins.",
    "lb_title":"🏆 Ranking hermanos","lb_period":"Periodo","lb_day":"Diario","lb_month":"Mensual","lb_total":"Total",
    "lb_score":"pts","lb_no_data":"Sin datos","lb_you":"(tú)",
    "lb_only_you":"Sin otros hermanos.",
    "redeem_tip_expired":"Prueba de [{user}] caducada. Solicite código al admin.",
    "redeem_code":"Código","redeem_activate":"Activar","redeem_invalid":"Código inválido o usado",
    "redeem_success":"¡Activado!","redeem_fail":"Error de activación.",
    "time_arrive":"¡Tiempo!",
    "weekday_short":["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"],
},
"ar": {
    "language":"اللغة / Language","app_title":"تسجيل الدراسة",
    "login":"تسجيل الدخول","register":"إنشاء حساب","find_pwd":"استعادة كلمة المرور","username":"اسم المستخدم","password":"كلمة المرور",
    "set_username":"اسم المستخدم","set_pwd":"كلمة المرور","confirm_pwd":"تأكيد كلمة المرور",
    "security_q":"سؤال الأمان","security_a":"إجابة الأمان",
    "login_btn":"دخول","register_btn":"تسجيل","reset_btn":"إعادة تعيين",
    "wrong_creds":"اسم أو كلمة مرور خاطئة","fill_all":"املأ جميع الحقول","pwd_mismatch":"كلمتا المرور غير متطابقتين",
    "reserved_name":"الاسم محجوز","user_exists":"الاسم موجود مسبقاً","register_ok":"تم التسجيل! تجربة 3 أيام.",
    "no_security_q":"لا يوجد سؤال أمان. اتصل بالمسؤول.","user_not_exist":"المستخدم غير موجود",
    "reset_ok":"تم إعادة تعيين كلمة المرور!","wrong_answer":"إجابة خاطئة",
    "reset_intro":"أدخل اسم المستخدم، تحقق من السؤال، ثم ضع كلمة مرور جديدة.",
    "input_username":"أدخل اسم المستخدم","new_password":"كلمة مرور جديدة",
    "pwd_req": "🔐 كلمة المرور: 6 أحرف على الأقل، يُنصح بالحروف والأرقام؛ 123456 ممنوعة",
    "pwd_err_empty": "لا يمكن أن تكون كلمة المرور فارغة",
    "pwd_err_too_short": "يجب أن تكون كلمة المرور 6 أحرف على الأقل",
    "pwd_err_too_long": "يجب ألا تتجاوز كلمة المرور 72 حرفاً",
    "pwd_err_default": "كلمة المرور الافتراضية 123456 غير مسموحة",
    "pwd_err_all_digits": "كلمة المرور المكونة من أرقام فقط غير مسموحة؛ اخلط الحروف والأرقام",
    "op_failed":"فشلت العملية.","db_failed":"فشل الاتصال بقاعدة البيانات.",
    "sidebar_title":"تسجيل الدراسة","mobile_mode":"📱 الوضع المبسط","current_identity":"مسجل كـ",
    "local_time":"الوقت المحلي","makeup_cards":"🎫 بطاقات التعويض","available_points":"النقاط المتاحة",
    "timer":"مؤقت التركيز","badges":"شاراتي","no_badges":"لا شارات","points_detail":"تفاصيل النقاط",
    "checkin_pts":"تسجيل","longterm_pts":"طويل الأمد","exam_pts":"اختبار","extra_pts":"إضافي","special_pts":"خاص","spent_pts":"مُنفق",
    "account_settings":"الحساب والبيانات","timezone":"المنطقة الزمنية","select_timezone":"المنطقة / الزمن","custom_tz":"مخصص",
    "tz_offset":"إزاحة UTC (ساعة)","save_tz":"حفظ","new_username":"اسم جديد","leave_blank":"فارغ = دون تغيير",
    "change_username":"تغيير الاسم","change_pwd":"تغيير كلمة المرور","change_security":"تغيير الأمان",
    "new_security_q":"سؤال أمان جديد","new_security_a":"إجابة أمان جديدة","save_security":"حفظ",
    "webhook":"Webhook التذكير","save_webhook":"حفظ","export_data":"📥 تصدير (JSON)","logout_btn":"تسجيل الخروج",
    "select_child":"اختر طفلاً","admin_select_target":"المسؤول: اختر الهدف",
    "penetrate":"اختراق","no_children_bound":"لا يوجد أطفال مرتبطون.",
    "role_admin":"مسؤول","role_host":"ولي أمر","role_user":"طفل","role_solo":"فردي",
    "remaining":"متبقي","permanent":"دائم","expired":"منتهي",
    "tab_checkin":"تسجيل","tab_extra":"إضافي","tab_history":"السجل","tab_shop":"المتجر","tab_redeem":"استبدال",
    "tab_exam":"اختبار","tab_event":"حدث","tab_settings":"إعدادات","tab_leaderboard":"لوحة الصدارة",
    "search_users":"🔍 البحث","search_children":"🔍 البحث عن أطفال","no_match":"لا نتائج",
    "no_tasks_today":"لا توجد مهام اليوم. أضفها في الإعدادات.",
    "basic_req":"الحد الأدنى","full_req":"الدرجة الكاملة","today_done":"اكتمل تسجيل اليوم.",
    "undo_checkin":"إلغاء تسجيل اليوم","base_score":"النقاط الأساسية","today_total":"إجمالي اليوم",
    "est_total":"الإجمالي المتوقع","save_checkin":"حفظ","saved":"تم الحفظ!","bonus":"مكافأة",
    "shop_empty":"المتجر فارغ.","redeem_btn":"استبدال","confirm_deduct":"تأكيد الخصم",
    "points_insufficient":"نقاط غير كافية.","redeem_ok":"تم الاستبدال!","redeem_history":"سجل الاستبدال","none_yet":"لا شيء",
    "cancel":"إلغاء","backup_card":"بطاقة التعويض",
    "history_title":"السجل والرسوم","checkin_hist_detail":"تفاصيل التسجيل","select_date":"اختر التاريخ",
    "time_view":"عرض الوقت","by_day":"يومي","by_week":"أسبوعي","by_month":"شهري",
    "no_data":"لا بيانات","no_record":"لا سجلات","done_items":"المكتمل:",
    "weekly_report":"### 📊 التقرير الأسبوعي","week_checkin":"أيام هذا الأسبوع","week_total":"إجمالي الأسبوع",
    "day_max":"أقصى يوم","gen_report":"📸 توليد وتنزيل التقرير","save_report":"⬇️ تنزيل الصورة",
    "report_ok":"تم إنشاء التقرير.","report_failed":"فشل إنشاء الصورة.",
    "makeup_intro":"🎫 **{n} بطاقة تعويض متاحة:**",
    "makeup_pick_date":"اختر التاريخ","makeup_pick_tasks":"**اختر المهام المنجزة في {d}:**",
    "makeup_submit":"استخدم بطاقة","makeup_ok":"تم التعويض!","makeup_fail":"فشل التعويض.",
    "makeup_no_miss":"حضور كامل 7 أيام!","makeup_tip":"💡 بطاقات في المتجر.",
    "makeup_host_tip":"💡 يجب أن يقوم الطفل بذلك.","makeup_host_self":"💡 حساب ولي الأمر. بدّل الطفل.",
    "exam_title":"الاختبارات","exam_no_subject":"لا مواد مكونة!",
    "exam_score":"(الأقصى {max}، الهدف {target})","exam_grade":"(الهدف {target})",
    "exam_ranks":"**أفضل % في الصيني/الرياضيات/الإنجليزي (100 = تجاهل)**",
    "exam_cn":"الصينية","exam_ma":"الرياضيات","exam_en":"الإنجليزية",
    "exam_estimate":"### المتوقع: **{pts}** نقطة ({hits} مادة)","exam_save":"حفظ النتيجة",
    "exam_saved":"تم الحفظ!","exam_hit":"{sub} محقق -> +{pts}","exam_over":"  {sub} +{n} مستوى -> +{pts}",
    "exam_up":"  {sub} ارتفع {n} -> +{pts}","exam_multi":"{n}+ مواد -> +{pts}",
    "exam_rank":"{sub} أفضل {pct}% -> +{pts}","exam_rank_more":"  +{n} -> +{pts}",
    "event_title":"أحداث خاصة","event_fired":"مُفعّل اليوم: {note} +{pts}",
    "event_confirm":"🎲 استخدام فرصة اليوم؟","event_roll":"تأكيد","event_roll_btn":"أدر",
    "event_got":"+{pts} نقاط!","event_note":"انفجار النقاط",
    "extra_title":"نقاط إضافية","extra_name":"الاسم","extra_points":"النقاط (سالب مسموح)",
    "extra_submit":"إرسال","extra_saved":"مسجل: {name} ({pts})",
    "extra_clear":"مسح","extra_none":"لا شيء",
    "extra_only_parent":"للآباء/المسؤولين فقط.",
    "lb_title":"🏆 ترتيب الأشقاء","lb_period":"الفترة","lb_day":"يومي","lb_month":"شهري","lb_total":"إجمالي",
    "lb_score":"نقطة","lb_no_data":"لا بيانات","lb_you":"(أنت)",
    "lb_only_you":"لا أشقاء آخرون.",
    "redeem_tip_expired":"انتهت تجربة [{user}]. اطلب رمزاً من المسؤول.",
    "redeem_code":"الرمز","redeem_activate":"تفعيل","redeem_invalid":"رمز غير صالح أو مستخدم",
    "redeem_success":"تم التفعيل!","redeem_fail":"فشل التفعيل.",
    "time_arrive":"انتهى الوقت!",
    "weekday_short":["إث","ثل","أر","خم","جم","سب","أح"],
},
}

LANG_LABELS = {"zh":"中文","en":"English","ja":"日本語","fr":"Français","ru":"Русский","es":"Español","ar":"العربية"}

def detect_system_language():
    try:
        accept = st.context.headers.get("Accept-Language", "") or ""
        first = accept.split(",")[0].strip().lower()
        for code in ["zh","en","ja","fr","ru","es","ar"]:
            if first.startswith(code): return code
    except Exception:
        pass
    return "zh"

def get_lang():
    if "lang" not in st.session_state:
        st.session_state["lang"] = detect_system_language()
    return st.session_state["lang"]

def t(key, **fmt):
    pack = LANG_PACKS.get(get_lang(), LANG_PACKS["zh"])
    s = pack.get(key, LANG_PACKS["en"].get(key, LANG_PACKS["zh"].get(key, key)))
    if isinstance(s, list): return s
    if fmt:
        try: return s.format(**fmt)
        except Exception: return s
    return s

# 【中危加固 9】密码强度统一校验：必须放在 t() 之后
def validate_password_strength(pwd: str) -> str | None:
    """返回错误提示；None 表示通过"""
    if not pwd:
        return t("pwd_err_empty")
    if len(pwd) < 6:
        return t("pwd_err_too_short")
    if len(pwd) > 72:
        return t("pwd_err_too_long")
    if pwd == "123456":
        return t("pwd_err_default")
    if pwd.isdigit():
        return t("pwd_err_all_digits")
    return None

def get_weekday(idx):
    pack = LANG_PACKS.get(get_lang(), LANG_PACKS["zh"])
    return pack.get("weekday_short", LANG_PACKS["zh"]["weekday_short"])[idx % 7]

def render_language_selector(key_suffix=""):
    options = list(LANG_PACKS.keys())
    cur = get_lang()
    idx = options.index(cur) if cur in options else 0
    choice = st.selectbox(t("language"), options, index=idx, format_func=lambda x: LANG_LABELS.get(x, x), key=f"lang_sel_{key_suffix}")
    if choice != st.session_state.get("lang"):
        st.session_state["lang"] = choice
        return True
    return False

# ==================== 密码与安全区 ====================
def get_secret_key():
    try:
        if "SECRET_KEY" in st.secrets and st.secrets["SECRET_KEY"]:
            return str(st.secrets["SECRET_KEY"])
    except Exception:
        pass
    env_key = os.getenv("SECRET_KEY")
    if env_key: return env_key
    temp = secrets.token_hex(32)
    print("⚠️ 未配置 SECRET_KEY，使用临时随机密钥，重启后所有登录会话将失效。")
    return temp

SECRET_KEY = get_secret_key()

def generate_auth_token(username, pwd_hash, expire_days=7):
    expire_ts = int((datetime.now(timezone.utc) + timedelta(days=expire_days)).timestamp())
    payload = f"{username}|{expire_ts}"
    sig = hmac.new((SECRET_KEY + pwd_hash).encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode().rstrip("=")

def verify_auth_token(username, token, pwd_hash):
    if not username or not token or not pwd_hash: return False
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        parts = raw.split("|")
        if len(parts) != 3: return False
        t_user, t_exp, t_sig = parts
        if t_user != username: return False
        if int(t_exp) < int(datetime.now(timezone.utc).timestamp()): return False
        expected = hmac.new((SECRET_KEY + pwd_hash).encode(), f"{t_user}|{t_exp}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, t_sig)
    except Exception:
        return False

def hash_pwd_sha256(pwd): return hashlib.sha256(pwd.encode()).hexdigest()
def hash_pwd_bcrypt(pwd): return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
def check_pwd_bcrypt(pwd, hashed):
    try: return bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError: return False

def hash_security_answer(ans): return hash_pwd_bcrypt(ans.strip().lower())
def verify_security_answer(ans, stored):
    if not stored: return False
    try:
        if stored.startswith("$2"): return check_pwd_bcrypt(ans.strip().lower(), stored)
        if len(stored) == 64: return hashlib.sha256(ans.strip().lower().encode()).hexdigest() == stored
    except Exception: pass
    return False

# ==================== 兼容/运维 ====================
def _stretch(kwargs):
    try:
        import inspect
        sig = inspect.signature(st.button)
        if "width" in sig.parameters: kwargs["width"] = "stretch"
        else: kwargs["use_container_width"] = True
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
    except Exception: pass

# 【中危加固 10】表名白名单提升为不可变常量元组，外部不可注入
ALL_TABLES = (
    "users",
    "daily_records", "period_bonus", "redemptions",
    "exam_rewards", "special_events", "extra_points",
    "config_tasks", "config_shop", "config_exam",
    "config_exam_rules", "config_thresholds", "config_bonus_rules",
    "config_exam_multihit", "config_badges", "redeem_codes",
)

def delete_user_all_data(db, uname: str):
    """彻底删除某用户所有数据。表名来自常量 ALL_TABLES，外部不可注入。"""
    db.execute("UPDATE users SET host_id=NULL WHERE host_id=?", (uname,))
    for tbl in ALL_TABLES:
        if tbl == "redeem_codes":
            try:
                db.execute("UPDATE redeem_codes SET used_by=NULL WHERE used_by=?", (uname,))
            except Exception:
                pass
            continue
        col = "username" if tbl == "users" else "owner_id"
        try:
            db.execute(f"DELETE FROM {tbl} WHERE {col}=?", (uname,))
        except Exception as e:
            _log_db_error(f"delete_{tbl}", str(e))

# 【中危加固 6】云端模式不再静默 return，只提示
def _backup_sqlite():
    if IS_CLOUD:
        print("ℹ️ 云端模式：无本地 SQLite 备份；请使用系统设置里的『下载完整备份』或配置外部 pg_dump 定时任务。")
        return
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
        except Exception as e: print(f"备份失败: {e}")

# ==================== 时间引擎 ====================
TIMEZONES = {
    "北京时间 (UTC+8)": 8.0, "东京时间 (UTC+9)": 9.0, "悉尼时间 (UTC+10)": 10.0,
    "伦敦时间 (UTC+0)": 0.0, "巴黎时间 (UTC+1)": 1.0, "纽约时间 (UTC-5)": -5.0,
    "洛杉矶时间 (UTC-8)": -8.0, "自定义时区": None
}

def get_user_now(offset_hours):
    try: oh = float(offset_hours)
    except: oh = 8.0
    oh = max(-12.0, min(14.0, oh))
    return datetime.now(timezone(timedelta(hours=oh)))

def get_user_today(offset_hours): return get_user_now(offset_hours).date()

def get_remaining_days(exp_str):
    if not exp_str: return -1
    if str(exp_str).startswith("2099"): return 9999
    try:
        exp_dt = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
        delta = exp_dt - datetime.now()
        if delta.days < 0: return -1
        return max(0, delta.days + (1 if delta.seconds > 0 else 0))
    except: return -1

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
    except Exception: return None

DB_PATH = Path(__file__).resolve().parent / "study_points.db"
DEFAULT_ICON_BASE64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRkZEMzAwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDJMMTUuMDkgOC4yNkwyMiA5LjI3TDE3IDE0LjE0TDE4LjE4IDIxLjAyTDEyIDE3LjU3TDUuODIgMjEuMDJMOSAxNC4xNEwyIDkuMjdMOC45MSA4LjI2TDEyIDJ6Ij48L3BhdGg+PC9zdmc+"

DEFAULT_BONUS_RULES = {
    "weekday": {"single": {"points": 1.0, "full_points": 2.0}, "streak2": {"points": 1.5, "full_points": 3.0}, "streak4": {"points": 2.5, "full_points": 5.0}},
    "weekend": {"single": {"points": 1.0, "full_points": 2.0}},
    "longterm": {"week_basic": 3.5, "week_full": 7.0, "week_flex_perfect_deduct": 1.0, "week_flex_basic_deduct": 0.5, "month_basic": 8.0, "month_full": 20.0}
}
DEFAULT_EXAM_RULES = {"hit_points": 1.0, "rank_top_percent": 75.0, "rank_base_points": 1.0, "rank_step_percent": 5.0, "rank_step_points": 1.5}
TIER_CN = {"single": "单日达标", "streak2": "连续2日达标", "streak4": "连续4日达标", "weekend_single": "周末单日达标"}
GRADES = ["A+", "A", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E"]

# ==================== 数据库封装 ====================
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
        self.conn = conn; self.is_cloud = is_cloud
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
            raise RuntimeError("数据库操作失败，请刷新重试。")
    def executemany(self, query, params_list):
        try:
            if self.is_cloud:
                if self.conn.closed != 0: raise psycopg2.OperationalError("Connection closed")
                query = query.replace("?", "%s")
                cur = self.conn.cursor()
                cur.executemany(query, params_list)
                return cur
            else: return self.conn.executemany(query, params_list)
        except Exception as e:
            if self.is_cloud: st.cache_resource.clear()
            _log_db_error("executemany", str(e))
            raise RuntimeError("数据库批量操作失败，请稍后重试。")
    def commit(self): self.conn.commit()

@st.cache_resource(show_spinner=False)
def get_db():
    if IS_CLOUD:
        try:
            conn = psycopg2.connect(st.secrets["DATABASE_URL"])
            conn.autocommit = True
            db = DBWrapper(conn, True); init_db(db); return db
        except Exception as e:
            st.cache_resource.clear(); _log_db_error("get_db", str(e))
            raise RuntimeError("数据库连接失败，请稍后重试。")
    else:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        db = DBWrapper(conn, False); init_db(db); _backup_sqlite(); return db

# 【中危加固 7】破坏性 DDL 迁移只执行一次
def run_legacy_constraint_cleanup(db):
    try:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)")
        db.commit()
    except Exception as e:
        print(f"创建 schema_migrations 失败: {e}")

    try:
        row = db.execute("SELECT version FROM schema_migrations WHERE version=?", ("v1_legacy_constraint_cleanup",)).fetchone()
        if row:
            return
    except Exception as e:
        print(f"检查 schema_migrations 失败: {e}")

    try:
        for q in [
            "ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS daily_records_pkey CASCADE",
            "ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS daily_records_day_key CASCADE",
            "ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS daily_records_day_owner_id_key CASCADE",
            "DROP INDEX IF EXISTS daily_records_pkey CASCADE",
            "DROP INDEX IF EXISTS daily_records_day_key CASCADE",
            "DROP INDEX IF EXISTS daily_records_day_owner_id_key CASCADE",
            "ALTER TABLE config_thresholds DROP CONSTRAINT IF EXISTS config_thresholds_pkey CASCADE",
            "DROP INDEX IF EXISTS config_thresholds_pkey CASCADE",
            "ALTER TABLE config_exam DROP CONSTRAINT IF EXISTS config_exam_pkey CASCADE",
            "ALTER TABLE config_exam DROP CONSTRAINT IF EXISTS config_exam_subject_key CASCADE",
            "DROP INDEX IF EXISTS config_exam_pkey CASCADE",
            "DROP INDEX IF EXISTS config_exam_subject_key CASCADE",
            "ALTER TABLE config_exam_multihit DROP CONSTRAINT IF EXISTS config_exam_multihit_pkey CASCADE",
            "DROP INDEX IF EXISTS config_exam_multihit_pkey CASCADE",
            "ALTER TABLE config_bonus_rules DROP CONSTRAINT IF EXISTS config_bonus_rules_pkey CASCADE",
            "DROP INDEX IF EXISTS config_bonus_rules_pkey CASCADE",
            "ALTER TABLE config_tasks DROP CONSTRAINT IF EXISTS config_tasks_pkey CASCADE",
            "ALTER TABLE config_shop DROP CONSTRAINT IF EXISTS config_shop_pkey CASCADE",
            "ALTER TABLE config_badges DROP CONSTRAINT IF EXISTS config_badges_pkey CASCADE",
            "ALTER TABLE special_events DROP CONSTRAINT IF EXISTS special_events_pkey CASCADE",
            "ALTER TABLE extra_points DROP CONSTRAINT IF EXISTS extra_points_pkey CASCADE",
            "ALTER TABLE redemptions DROP CONSTRAINT IF EXISTS redemptions_pkey CASCADE",
        ]:
            try:
                db.execute(q)
            except Exception as e:
                _log_db_error("legacy_constraint_cleanup", str(e))

        try:
            res = db.execute("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'daily_records' AND constraint_type = 'UNIQUE'").fetchall()
            for row in res:
                cname = row["constraint_name"]
                if re.match(r"^[A-Za-z0-9_]+$", str(cname)):
                    try:
                        db.execute(f"ALTER TABLE daily_records DROP CONSTRAINT IF EXISTS {cname} CASCADE")
                    except Exception as e:
                        _log_db_error("legacy_constraint_cleanup_unique", str(e))
        except Exception as e:
            _log_db_error("legacy_constraint_cleanup_query", str(e))

        try:
            db.execute("CREATE SEQUENCE IF NOT EXISTS config_bonus_rules_id_seq")
            db.execute("ALTER TABLE config_bonus_rules ALTER COLUMN id SET DEFAULT nextval('config_bonus_rules_id_seq')")
        except Exception as e:
            _log_db_error("legacy_constraint_cleanup_seq", str(e))

        try:
            db.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                       ("v1_legacy_constraint_cleanup", datetime.now().isoformat()))
        except Exception as e:
            _log_db_error("legacy_constraint_cleanup_mark", str(e))
        db.commit()
    except Exception as e:
        print(f"清理历史约束失败: {e}")

def init_db(db):
    if db.is_cloud:
        # 【中危加固 7】内部自带“只跑一次”判断
        run_legacy_constraint_cleanup(db)
        # 后续建表、ALTER TABLE ADD COLUMN 等幂等操作保留不动

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
    for sql in tables_common:
        try: db.execute(sql)
        except: pass

    pk_expr = "SERIAL PRIMARY KEY" if db.is_cloud else "INTEGER PRIMARY KEY AUTOINCREMENT"
    for tname, cols in [
        ("redemptions", "id {pk}, owner_id TEXT, item TEXT, cost REAL, ts TEXT"),
        ("exam_rewards", "id {pk}, owner_id TEXT, detail TEXT, points REAL, ts TEXT"),
        ("special_events", "id {pk}, day TEXT, owner_id TEXT, points REAL, note TEXT, ts TEXT"),
        ("extra_points", "id {pk}, owner_id TEXT, name TEXT, points REAL, ts TEXT"),
        ("config_shop", "id {pk}, owner_id TEXT, name TEXT, cost REAL"),
        ("config_badges", "id {pk}, owner_id TEXT DEFAULT 'system', name TEXT, cond_type TEXT, cond_val REAL, icon_url TEXT"),
    ]:
        try: db.execute(f"CREATE TABLE IF NOT EXISTS {tname} ({cols.format(pk=pk_expr)})")
        except: pass

    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_daily_records ON daily_records (owner_id, day)",
        "CREATE INDEX IF NOT EXISTS idx_period_bonus ON period_bonus (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_extra_points ON extra_points (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_exam_rewards ON exam_rewards (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_redemptions ON redemptions (owner_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_config_tasks ON config_tasks (owner_id, weekday, category, name)",
    ]:
        try: db.execute(idx)
        except: pass
    db.commit()

    if db.is_cloud:
        for q in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS security_question TEXT","ALTER TABLE users ADD COLUMN IF NOT EXISTS security_answer TEXT","ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'","ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_url TEXT","ALTER TABLE users ADD COLUMN IF NOT EXISTS makeup_cards INTEGER DEFAULT 0","ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone_offset REAL DEFAULT 8.0","ALTER TABLE users ADD COLUMN IF NOT EXISTS host_id TEXT","ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expires_at TEXT","ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT",
            "ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS basic_thr REAL","ALTER TABLE daily_records ADD COLUMN IF NOT EXISTS full_thr REAL",
            "ALTER TABLE period_bonus ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE exam_rewards ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE special_events ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE extra_points ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_tasks ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE config_shop ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE config_exam ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE config_exam_rules ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE config_thresholds ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE config_bonus_rules ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'","ALTER TABLE config_exam_multihit ADD COLUMN IF NOT EXISTS owner_id TEXT DEFAULT '晴'",
        ]:
            try: db.execute(q)
            except: pass
        db.commit()
    else:
        for q in [
            "ALTER TABLE users ADD COLUMN security_question TEXT","ALTER TABLE users ADD COLUMN security_answer TEXT","ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'","ALTER TABLE users ADD COLUMN webhook_url TEXT","ALTER TABLE users ADD COLUMN makeup_cards INTEGER DEFAULT 0","ALTER TABLE users ADD COLUMN timezone_offset REAL DEFAULT 8.0","ALTER TABLE users ADD COLUMN host_id TEXT","ALTER TABLE users ADD COLUMN plan_expires_at TEXT","ALTER TABLE users ADD COLUMN language TEXT",
            "ALTER TABLE daily_records ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE daily_records ADD COLUMN basic_thr REAL","ALTER TABLE daily_records ADD COLUMN full_thr REAL",
            "ALTER TABLE period_bonus ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE redemptions ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE exam_rewards ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE special_events ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE extra_points ADD COLUMN owner_id TEXT DEFAULT '晴'",
            "ALTER TABLE config_tasks ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE config_shop ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE config_exam ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE config_exam_rules ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE config_thresholds ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE config_bonus_rules ADD COLUMN owner_id TEXT DEFAULT '晴'","ALTER TABLE config_exam_multihit ADD COLUMN owner_id TEXT DEFAULT '晴'",
        ]:
            try: db.execute(q)
            except: pass
        db.commit()

    try:
        expire_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        db.execute("UPDATE users SET plan_expires_at=? WHERE plan_expires_at IS NULL AND role IN ('user', 'solo')", (expire_date,))
        db.execute("UPDATE users SET plan_expires_at='2099-12-31 23:59:59' WHERE plan_expires_at IS NULL AND role IN ('admin', 'host')")
        db.commit()
    except Exception as e: print(f"补发老用户试用期失败: {e}")

    try:
        user_count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        if user_count == 0:
            admin_user = os.getenv("INIT_ADMIN_USER", "admin")
            admin_pwd = os.getenv("INIT_ADMIN_PWD", "")
            generated = False
            if not admin_pwd:
                admin_pwd = secrets.token_urlsafe(12); generated = True
            admin_sa = secrets.token_urlsafe(12)
            print(f"⚠️ 生成初始管理员: {admin_user} / {admin_pwd}" + (" (随机生成，请立即查看日志并登录后修改密码)" if generated else ""))
            db.execute("INSERT INTO users (username, password_hash, role, security_question, security_answer, plan_expires_at) VALUES (?, ?, 'admin', ?, ?, '2099-12-31 23:59:59')",
                       (admin_user, hash_pwd_bcrypt(admin_pwd), "初始密保", hash_security_answer(admin_sa)))
            if not db.execute("SELECT * FROM config_tasks WHERE owner_id=?", (admin_user,)).fetchone():
                init_old_admin_data(db, admin_user)
            db.commit()
    except Exception as e: print(f"初始化管理员失败: {e}")

    try:
        global_badge_count = db.execute("SELECT COUNT(*) as c FROM config_badges WHERE owner_id='system'").fetchone()["c"]
        if global_badge_count == 0:
            db.execute("DELETE FROM config_badges")
            for b in [("破壳而出","days",1),("持之以恒","days",7),("习惯成自然","days",30),("积分大亨","points",100),("完美主义","perfect",1),("考神附体","exam_hits",4)]:
                prompt = f"Minimalist flat vector icon for '{b[0]}', clean simple design, ui app icon, no text, white background, not exaggerated"
                icon_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=256&height=256&nologo=true&seed=42"
                db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)", (b[0], b[1], b[2], icon_url))
        db.commit()
    except: pass

def init_old_admin_data(db, owner_id):
    try:
        for tb in ["config_tasks","config_thresholds","config_shop","config_exam","config_exam_rules","config_bonus_rules"]:
            db.execute(f"DELETE FROM {tb} WHERE owner_id=?", (owner_id,))
        db.commit()
    except Exception as e: print(f"清理旧配置失败: {e}")

    BASE_TASKS = [("hw_sort","校内","作业分类",1.0),("hw_done","校内","作业完成",2.0)]
    for i in range(7):
        for task in BASE_TASKS:
            tid = f"{owner_id}_{task[0]}_d{i}"
            try: db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (tid, i, owner_id, task[1], task[2], task[3]))
            except: pass
        try: db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)', (i, owner_id, 8.0, 11.0))
        except: pass
    try: db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (owner_id, "专属夸夸", 6))
    except: pass
    try: db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", ("语文", owner_id, json.dumps({"type":"score","max_score":150,"target":105.0,"step":3.0,"step_points":2.0})))
    except: pass
    try: db.execute("INSERT INTO config_exam_rules (owner_id, config_json) VALUES (?,?)", (owner_id, json.dumps(DEFAULT_EXAM_RULES)))
    except: pass
    try: db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (owner_id, json.dumps(DEFAULT_BONUS_RULES)))
    except: pass
    try: db.commit()
    except: pass

# ==================== 用户/配置读取 ====================
@st.cache_data(ttl=60, show_spinner=False)
def get_all_users():
    db = get_db()
    return [{"username": r["username"], "role": r["role"], "plan_expires_at": r["plan_expires_at"]} for r in db.execute("SELECT username, role, plan_expires_at FROM users").fetchall()]

# 【中危加固 8】轻量权限辅助函数，统一权限入口
def is_admin(role): return role == "admin"
def is_host(role): return role == "host"
def is_user(role): return role == "user"
def is_solo(role): return role == "solo"
def can_manage_others(role): return role in ("admin", "host")
def can_edit_configs(role): return role in ("admin", "host", "solo")
def require_admin(role, msg="仅管理员可操作"):
    if not is_admin(role):
        st.error(msg); st.stop()
def require_admin_or_host(role, msg="仅管理员或家长可操作"):
    if not can_manage_others(role):
        st.error(msg); st.stop()

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
def get_balance(oid):
    db = get_db()
    q = """
        SELECT 'daily' as k, COALESCE(SUM(total_score), 0) as s FROM daily_records WHERE owner_id = ?
        UNION ALL SELECT 'period', COALESCE(SUM(points), 0) FROM period_bonus WHERE owner_id = ?
        UNION ALL SELECT 'exam', COALESCE(SUM(points), 0) FROM exam_rewards WHERE owner_id = ?
        UNION ALL SELECT 'special', COALESCE(SUM(points), 0) FROM special_events WHERE owner_id = ?
        UNION ALL SELECT 'spent', COALESCE(SUM(cost), 0) FROM redemptions WHERE owner_id = ?
        UNION ALL SELECT 'extra', COALESCE(SUM(points), 0) FROM extra_points WHERE owner_id = ?
    """
    try:
        rows = db.execute(q, (oid, oid, oid, oid, oid, oid)).fetchall()
        data = {r["k"]: float(r["s"] or 0) for r in rows}
    except: data = {"daily":0.0,"period":0.0,"exam":0.0,"special":0.0,"spent":0.0,"extra":0.0}
    daily, period, exam, special, spent, extra = [round(data[k], 2) for k in ["daily","period","exam","special","spent","extra"]]
    return {"daily":daily,"period":period,"exam":exam,"special":special,"spent":spent,"extra":extra,"balance":round(daily+period+exam+special+extra-spent, 2)}

def get_leaderboard(children, period, tz_offset):
    if not children: return []
    now = get_user_now(tz_offset); today = now.date()
    start = today.isoformat() if period == "day" else (today.replace(day=1).isoformat() if period == "month" else None)
    db = get_db()
    scores = {c: 0.0 for c in children}
    ph = ",".join(["?"] * len(children))
    try:
        if start is None:
            rows = db.execute(f"SELECT owner_id, SUM(total_score) as s FROM daily_records WHERE owner_id IN ({ph}) GROUP BY owner_id", (*children,)).fetchall()
        else:
            rows = db.execute(f"SELECT owner_id, SUM(total_score) as s FROM daily_records WHERE owner_id IN ({ph}) AND day >= ? GROUP BY owner_id", (*children, start)).fetchall()
        for r in rows:
            if r["owner_id"] in scores: scores[r["owner_id"]] += float(r["s"] or 0)
        for tbl in ["period_bonus","exam_rewards","special_events","extra_points"]:
            if start is None:
                rows = db.execute(f"SELECT owner_id, SUM(points) as s FROM {tbl} WHERE owner_id IN ({ph}) GROUP BY owner_id", (*children,)).fetchall()
            else:
                rows = db.execute(f"SELECT owner_id, SUM(points) as s FROM {tbl} WHERE owner_id IN ({ph}) AND substr(ts, 1, 10) >= ? GROUP BY owner_id", (*children, start)).fetchall()
            for r in rows:
                if r["owner_id"] in scores: scores[r["owner_id"]] += float(r["s"] or 0)
    except Exception as e: print(f"leaderboard query failed: {e}")
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

# ==================== 业务逻辑 ====================
def compute_bonus_for_day(day, lookup, bonus_rules):
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
                dd = scores[x.isoformat()]
                if float(dd.get("base_score") or 0) < float(dd.get("basic_thr") or 999): miss_basic += 1
                elif float(dd.get("base_score") or 0) < float(dd.get("full_thr") or 999): miss_full += 1
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
            first = date(y, m, 1); nxt = date(y+1,1,1) if m == 12 else date(y, m+1, 1)
            alldays = []; cur = first
            while cur < nxt: alldays.append(cur); cur += timedelta(days=1)
            if not all(x.isoformat() in scores for x in alldays): continue
            month_is_perfect = True; month_is_basic = True
            for day_obj in alldays:
                ds = day_obj.isoformat(); dd = scores[ds]
                dy, dw, _ = day_obj.isocalendar(); wk_key = f"{dy}-W{dw:02d}"
                w_stat = week_status.get(wk_key, {'is_perfect': False, 'is_basic': False})
                day_full = float(dd.get("base_score") or 0) >= float(dd.get("full_thr") or 999)
                day_basic = float(dd.get("base_score") or 0) >= float(dd.get("basic_thr") or 999)
                if not day_full and not w_stat['is_perfect']: month_is_perfect = False
                if not day_basic and not w_stat['is_basic']: month_is_basic = False
            target_kind, target_pts = None, 0.0
            if month_is_perfect: target_kind = "完美一月"; target_pts = lt_rules["month_full"]
            elif month_is_basic: target_kind = "整月达标"; target_pts = lt_rules["month_basic"]
            if target_kind: inserts.append((f"M:{mk}", oid, target_kind, target_pts, ts))
        if keys_to_delete:
            kl = list(keys_to_delete)
            ph = ",".join(["?"] * len(kl))
            db.execute(f"DELETE FROM period_bonus WHERE owner_id=? AND period_key IN ({ph})", (oid, *kl))
        if inserts: db.executemany("INSERT INTO period_bonus (period_key, owner_id, kind, points, ts) VALUES (?,?,?,?,?)", inserts)
        db.commit()
    except Exception as e: print(f"长期奖励结算失败: {e}")

def save_day(db, day, done_ids, oid, ts):
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

def calc_exam_bonus(scores, ranks, oid):
    try:
        exam_config, exam_rules = get_exam_config(oid); multihit_rules = get_exam_multihit(oid)
    except: return 0.0, [], 0
    total = 0.0; lines = []; hit_count = 0
    for subject, cfg in exam_config.items():
        actual = scores.get(subject)
        if actual is None: continue
        if cfg.get("type") == "score":
            hit = actual >= cfg.get("target", 0)
            if hit: total += exam_rules.get("hit_points", 1); hit_count += 1; lines.append(t("exam_hit", sub=subject, pts=exam_rules.get("hit_points",1)))
            step = cfg.get("step", 0); tiers = int((actual - cfg.get("target", 0)) // step) if step > 0 and actual > cfg.get("target", 0) else 0
            if tiers > 0:
                gain = tiers * cfg.get("step_points", 0); total += gain; lines.append(t("exam_over", sub=subject, n=tiers, pts=gain))
        else:
            if cfg.get("target") not in GRADES or actual not in GRADES: continue
            gap = GRADES.index(cfg["target"]) - GRADES.index(actual); hit = gap >= 0
            if hit: total += exam_rules.get("hit_points", 1); hit_count += 1; lines.append(t("exam_hit", sub=subject, pts=exam_rules.get("hit_points",1)))
            if gap > 0:
                gain = gap * cfg.get("step_points", 0); total += gain; lines.append(t("exam_up", sub=subject, n=gap, pts=gain))
    for mh in sorted(multihit_rules, key=lambda x: x["hit_count"], reverse=True):
        if hit_count >= mh["hit_count"]:
            total += mh["points"]; lines.append(t("exam_multi", n=mh["hit_count"], pts=mh["points"])); break
    for subject in ["语文", "数学", "英语"]:
        pct = ranks.get(subject)
        if pct is not None and 0 <= pct < 100 and pct <= exam_rules.get("rank_top_percent", 75):
            total += exam_rules.get("rank_base_points", 1); lines.append(t("exam_rank", sub=subject, pct=pct, pts=exam_rules.get("rank_base_points",1)))
            pct_step = exam_rules.get("rank_step_percent", 5); extra = int((exam_rules.get("rank_top_percent", 75) - pct) // pct_step) if pct_step > 0 else 0
            if extra > 0:
                gain = extra * exam_rules.get("rank_step_points", 1.5); total += gain; lines.append(t("exam_rank_more", n=extra, pts=gain))
    return round(total, 2), lines, hit_count

def render_timer():
    timer_html = """
    <style>body{margin:0;padding:0;overflow:hidden}.timer-container{font-family:sans-serif;text-align:center;padding:10px 5px;background:#f8f9fa;border-radius:10px}.timer-display{font-size:36px;font-weight:bold;margin:5px 0 15px 0;color:#2c3e50}.row{display:flex;justify-content:center;align-items:center;gap:8px;margin-bottom:15px;font-size:14px}.row select,.row input{padding:5px;border-radius:5px;border:1px solid #ccc}.row input{width:50px;text-align:center}.btn-group{display:flex;justify-content:center;gap:8px}button{flex:1;padding:8px 0;font-size:14px;cursor:pointer;border:none;border-radius:5px;background:#007bff;color:white;transition:0.2s}button:hover{background:#0056b3}.btn-stop{background:#dc3545}.btn-stop:hover{background:#c82333}.btn-reset{background:#6c757d}.btn-reset:hover{background:#5a6268}</style>
    <div class="timer-container"><div class="timer-display" id="display">00:00</div><div class="row"><select id="mode"><option value="stopwatch">↗</option><option value="countdown">⏳</option></select><span><input type="number" id="minutes" value="25" min="1">'</span></div><div class="btn-group"><button onclick="startTimer()">▶</button><button class="btn-stop" onclick="stopTimer()">⏸</button><button class="btn-reset" onclick="resetTimer()">↺</button></div></div>
    <script>let timerId=null;let isRunning=false;let currentSeconds=0;function updateDisplay(){let m=Math.floor(currentSeconds/60).toString().padStart(2,'0');let s=(currentSeconds%60).toString().padStart(2,'0');document.getElementById('display').innerText=m+":"+s;}function startTimer(){if(isRunning)return;let mode=document.getElementById('mode').value;if(!isRunning&&currentSeconds===0){if(mode==='countdown'){let mins=document.getElementById('minutes').value;currentSeconds=mins*60;}}isRunning=true;timerId=setInterval(()=>{if(document.getElementById('mode').value==='stopwatch'){currentSeconds++;}else{if(currentSeconds>0)currentSeconds--;else{clearInterval(timerId);isRunning=false;return;}}updateDisplay();},1000);}function stopTimer(){clearInterval(timerId);isRunning=false;}function resetTimer(){clearInterval(timerId);isRunning=false;currentSeconds=0;updateDisplay();}updateDisplay();</script>
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
                            if user.get("language") in LANG_PACKS: st.session_state["lang"] = user["language"]
                            st.query_params["user"] = u
                            st.query_params["auth"] = generate_auth_token(u, stored_hash)
                            if p == "123456": st.session_state.force_pwd_change = True
                            st.rerun()
                        else: st.error(t("wrong_creds"))
                    else: st.error(t("wrong_creds"))
                except RuntimeError: st.error(t("op_failed"))

    with tab2:
        with st.form(f"reg_form_{uid}"):
            u = st.text_input(t("set_username"), max_chars=20)
            p = st.text_input(t("set_pwd"), type="password", max_chars=72)
            # 【中危加固 9】注册页密码提示
            st.caption(t("pwd_req"))
            p2 = st.text_input(t("confirm_pwd"), type="password", max_chars=72)
            sq = st.text_input(t("security_q"), max_chars=50)
            sa = st.text_input(t("security_a"), max_chars=50)
            if _submit(t("register_btn"), **_stretch({"type": "primary"})):
                if not u or not p or not sq or not sa: st.error(t("fill_all"))
                elif p != p2: st.error(t("pwd_mismatch"))
                elif u.lower() in ["system", "admin"]: st.error(t("reserved_name"))
                else:
                    # 【中危加固 9】任何数据库操作之前校验密码强度
                    err = validate_password_strength(p)
                    if err:
                        st.error(err); st.stop()
                    try:
                        if db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone(): st.error(t("user_exists"))
                        else:
                            trial_exp = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
                            db.execute("INSERT INTO users (username, password_hash, role, security_question, security_answer, plan_expires_at, language) VALUES (?, ?, 'user', ?, ?, ?, ?)",
                                (u, hash_pwd_bcrypt(p), sq, hash_security_answer(sa), trial_exp, get_lang()))
                            db.commit()
                            try: init_old_admin_data(db, u)
                            except Exception as e: print(f"初始化新用户默认配置失败: {e}")
                            st.cache_data.clear(); st.success(t("register_ok"))
                    except RuntimeError: st.error(t("op_failed"))

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
                            # 【中危加固 9】找回密码页也统一提示与校验
                            st.caption(t("pwd_req"))
                            if _submit(t("reset_btn"), **_stretch({"type": "primary"})):
                                if not ans or not new_p: st.error(t("fill_all"))
                                else:
                                    err = validate_password_strength(new_p)
                                    if err:
                                        st.error(err); st.stop()
                                    if verify_security_answer(ans, user["security_answer"]):
                                        new_hash = hash_pwd_bcrypt(new_p)
                                        db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, u_reset))
                                        db.commit(); st.success(t("reset_ok"))
                                    else: st.error(t("wrong_answer"))
                else: st.error(t("user_not_exist"))
            except RuntimeError: st.error(t("op_failed"))

def main():
    st.set_page_config(page_title="学习打卡系统", layout="centered", initial_sidebar_state="collapsed")
    try: db = get_db()
    except RuntimeError: st.error(t("db_failed")); st.stop()

    if "user" not in st.session_state:
        pu = st.query_params.get("user"); pa = st.query_params.get("auth")
        if pu and pa:
            try:
                row = db.execute("SELECT * FROM users WHERE username=?", (pu,)).fetchone()
                if row and verify_auth_token(pu, pa, row["password_hash"]):
                    st.session_state.user = row["username"]; st.session_state.role = row["role"]
                    if row.get("language") in LANG_PACKS: st.session_state["lang"] = row["language"]
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
    except RuntimeError: st.error(t("op_failed")); st.stop()

    if st.session_state.get("force_pwd_change"):
        st.title("⚠️ 安全提示：请修改默认密码")
        st.warning("检测到您正在使用系统默认密码 (123456)，为了您的数据安全，请立即修改后才能继续使用。")
        with st.form("force_pwd_form"):
            new_p = st.text_input(t("new_password"), type="password", max_chars=72)
            # 【中危加固 9】强制改密页密码提示
            st.caption(t("pwd_req"))
            confirm_p = st.text_input(t("confirm_pwd"), type="password", max_chars=72)
            submit = _submit("提交修改", **_stretch({"type": "primary"}))
            if submit:
                if not new_p or not confirm_p: st.error(t("fill_all"))
                elif new_p != confirm_p: st.error(t("pwd_mismatch"))
                else:
                    err = validate_password_strength(new_p)
                    if err:
                        st.error(err); st.stop()
                    try:
                        new_hash = hash_pwd_bcrypt(new_p)
                        db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, current_user))
                        db.commit()
                        del st.session_state.force_pwd_change
                        st.query_params["auth"] = generate_auth_token(current_user, new_hash)
                        st.success("✅ 密码修改成功！"); st.rerun()
                    except RuntimeError: st.error(t("op_failed"))
        st.stop()

    current_role = user_row["role"]; st.session_state.role = current_role
    try: all_users_data = get_all_users()
    except: all_users_data = []

    user_tz = user_row.get("timezone_offset") or 8.0
    now = get_user_now(user_tz); today = now.date()

    try:
        if now.hour >= 21:
            tr = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (today.isoformat(), current_user)).fetchone()
            if not tr and user_row.get("webhook_url") and st.session_state.get(f"alerted_{today}") != True:
                url = user_row["webhook_url"]
                if "bark" in url: requests.get(f"{url}/今天还没打卡哦！", timeout=2)
                elif "serverchan" in url: requests.post(url, data={"title":"提醒","desp":"今天还没打卡哦！"}, timeout=2)
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
            except: pass
        is_mobile_mode = st.checkbox(t("mobile_mode"), value=False)
        bal = {"balance":0,"daily":0,"period":0,"exam":0,"special":0,"spent":0,"extra":0}

        view_as = current_user; view_role = current_role
        if is_user(current_role): view_as = current_user; view_role = "user"
        elif is_host(current_role):
            try:
                children = db.execute("SELECT username FROM users WHERE host_id=?", (current_user,)).fetchall()
                child_names = [r["username"] for r in children]
            except: child_names = []
            if not child_names: view_as = None; st.warning(t("no_children_bound"))
            else:
                # 多孩子时提供搜索
                if len(child_names) > 5:
                    kw = st.text_input(t("search_children"), key="host_child_search")
                    if kw:
                        child_names = [c for c in child_names if kw.lower() in c.lower()]
                        if not child_names: st.warning(t("no_match"))
                if child_names:
                    view_as = st.selectbox(t("select_child"), child_names, index=0); view_role = "user"
        elif is_solo(current_role):
            view_as = current_user; view_role = "solo"
        elif is_admin(current_role):
            try: all_users = db.execute("SELECT username, role FROM users").fetchall()
            except: all_users = []
            user_list = [u["username"] for u in all_users]
            if current_user in user_list: user_list.remove(current_user); user_list.insert(0, current_user)
            # 侧边栏搜索用户
            kw = st.text_input(t("search_users"), key="admin_sidebar_search")
            if kw: user_list = [x for x in user_list if kw.lower() in x.lower()]
            if not user_list: st.warning(t("no_match"))
            else:
                selected_target = st.selectbox(t("admin_select_target"), user_list, index=0)
                try:
                    target_role_row = db.execute("SELECT role FROM users WHERE username=?", (selected_target,)).fetchone()
                    target_role = target_role_row["role"] if target_role_row else "user"
                except: target_role = "user"
                if is_host(target_role):
                    try:
                        children = db.execute("SELECT username FROM users WHERE host_id=?", (selected_target,)).fetchall()
                        child_names = [r["username"] for r in children]
                    except: child_names = []
                    if child_names:
                        selected_child = st.selectbox(f"{t('penetrate')}: {selected_target}", child_names, index=0)
                        view_as = selected_child; view_role = "user"
                    else:
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
            role_display = {"admin":t("role_admin"),"host":t("role_host"),"user":t("role_user"),"solo":t("role_solo")}.get(view_role, view_role)
            plan_exp_str = ""
            if is_user(view_role) or is_solo(view_role) or is_admin(view_role):
                rd = get_remaining_days(plan_exp)
                if rd == 9999: plan_exp_str = f"\n\n⏳ {t('remaining')}: {t('permanent')}"
                elif rd < 0: plan_exp_str = f"\n\n⚠️ {t('expired')}"
                else: plan_exp_str = f"\n\n⏳ {t('remaining')}: {rd} d"
            st.info(f"{t('current_identity')}: {html.escape(view_as)} ({role_display}){plan_exp_str}\n\n{t('local_time')}: {get_user_now(target_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n{t('makeup_cards')}: {view_makeup_sidebar}")
            try: bal = get_balance(view_as)
            except: pass
            if not is_host(view_role): st.metric(t("available_points"), f"{bal['balance']:.1f}")
        else:
            st.info(f"{t('current_identity')}: {html.escape(current_user)} ({t('role_host')})\n\n{t('no_children_bound')}")

        if not is_mobile_mode and (is_admin(view_role) or is_solo(view_role) or (is_host(view_role) and view_as)):
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
                                    st.markdown(f'<div style="height:70px;display:flex;align-items:center;justify-content:center;"><img src="{b["icon"]}" width="60" loading="lazy" onerror="this.src=\'{DEFAULT_ICON_BASE64}\'"></div>', unsafe_allow_html=True)
                                    st.markdown(f"<div style='text-align:center;font-size:14px;'>{b['name']}</div>", unsafe_allow_html=True)
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
                    try: db.execute("UPDATE users SET timezone_offset=? WHERE username=?", (final_tz, current_user)); db.commit(); st.success("OK"); st.rerun()
                    except RuntimeError: st.error(t("op_failed"))

                st.divider()
                new_name = st.text_input(t("new_username"), placeholder=t("leave_blank"), max_chars=20)
                if st.button(t("change_username"), **_stretch({})):
                    if new_name and new_name != current_user:
                        if new_name.lower() in ["system","admin"]: st.error(t("reserved_name"))
                        else:
                            try:
                                if db.execute("SELECT * FROM users WHERE username=?", (new_name,)).fetchone(): st.error(t("user_exists"))
                                else:
                                    db.begin()
                                    try:
                                        for tbl in ["daily_records","period_bonus","redemptions","exam_rewards","special_events","extra_points","config_tasks","config_shop","config_exam","config_exam_rules","config_thresholds","config_bonus_rules","config_exam_multihit"]:
                                            db.execute(f"UPDATE {tbl} SET owner_id=? WHERE owner_id=?", (new_name, current_user))
                                        db.execute("UPDATE users SET host_id=? WHERE host_id=?", (new_name, current_user))
                                        db.execute("UPDATE redeem_codes SET used_by=? WHERE used_by=?", (new_name, current_user))
                                        db.execute("UPDATE users SET username=? WHERE username=?", (new_name, current_user))
                                        db.commit(); db.end()
                                        st.session_state.user = new_name
                                        st.query_params["user"] = new_name
                                        st.query_params["auth"] = generate_auth_token(new_name, user_row["password_hash"])
                                        st.cache_data.clear(); st.success("OK"); st.rerun()
                                    except Exception:
                                        db.rollback(); db.end(); st.error(t("op_failed"))
                            except RuntimeError: st.error(t("op_failed"))

                st.divider()
                new_pwd = st.text_input(t("new_password"), type="password", key="new_pwd", max_chars=72)
                # 【中危加固 9】侧边栏修改密码提示
                st.caption(t("pwd_req"))
                if st.button(t("change_pwd"), **_stretch({})):
                    if new_pwd:
                        err = validate_password_strength(new_pwd)
                        if err:
                            st.error(err); st.stop()
                        try:
                            new_hash = hash_pwd_bcrypt(new_pwd)
                            db.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, current_user))
                            db.commit()
                            st.query_params["auth"] = generate_auth_token(current_user, new_hash)
                            st.success("OK")
                        except RuntimeError: st.error(t("op_failed"))

                st.divider()
                st.markdown(f"**{t('change_security')}**")
                new_sq = st.text_input(t("new_security_q"), max_chars=50, key="new_sq")
                new_sa = st.text_input(t("new_security_a"), max_chars=50, key="new_sa")
                if st.button(t("save_security"), **_stretch({})):
                    if not new_sq or not new_sa: st.error(t("fill_all"))
                    else:
                        try:
                            db.execute("UPDATE users SET security_question=?, security_answer=? WHERE username=?", (new_sq, hash_security_answer(new_sa), current_user))
                            db.commit(); st.success("OK")
                        except RuntimeError: st.error(t("op_failed"))

                st.divider()
                webhook_input = st.text_input(t("webhook"), value=user_row.get("webhook_url") or "")
                if st.button(t("save_webhook"), **_stretch({})):
                    try: db.execute("UPDATE users SET webhook_url=? WHERE username=?", (webhook_input, current_user)); db.commit(); st.success("OK")
                    except RuntimeError: st.error(t("op_failed"))

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

    if is_host(view_role) and view_as is None:
        st.info(t("no_children_bound")); st.stop()

    if is_user(view_role) or is_solo(view_role):
        target_exp = user_row.get("plan_expires_at") if view_as == current_user else db.execute("SELECT plan_expires_at FROM users WHERE username=?", (view_as,)).fetchone()
        exp_str = target_exp.get("plan_expires_at") if isinstance(target_exp, dict) else target_exp
        is_expired = False
        if exp_str and str(exp_str).startswith("2099"): is_expired = False
        elif not exp_str: is_expired = True
        else:
            try:
                if datetime.now() > datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S'): is_expired = True
            except: is_expired = True
        if is_expired:
            st.error(t("redeem_tip_expired", user=view_as))
            with st.form(f"redeem_form_{view_as}"):
                c_code = st.text_input(t("redeem_code"))
                submit = st.form_submit_button(t("redeem_activate"), type="primary")
                if submit and c_code:
                    c_code = c_code.strip().upper()
                    db.begin()
                    try:
                        cur = db.execute("UPDATE redeem_codes SET is_used=1, used_by=? WHERE code=? AND is_used=0", (view_as, c_code))
                        if getattr(cur, "rowcount", 0) == 0:
                            db.rollback(); db.end(); st.error(t("redeem_invalid"))
                        else:
                            code_row = db.execute("SELECT days FROM redeem_codes WHERE code=?", (c_code,)).fetchone()
                            days = int(code_row["days"])
                            new_exp = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
                            db.execute("UPDATE users SET plan_expires_at=? WHERE username=?", (new_exp, view_as))
                            db.commit(); db.end(); st.success(t("redeem_success")); st.rerun()
                    except Exception:
                        db.rollback(); db.end(); st.error(t("redeem_fail"))
            st.stop()

    base_desktop = [t("tab_checkin"),t("tab_extra"),t("tab_history"),t("tab_shop"),t("tab_redeem"),t("tab_exam"),t("tab_event")]
    base_mobile = [t("tab_checkin"),t("tab_shop"),t("tab_redeem")]
    base_desktop_user = [t("tab_checkin"),t("tab_leaderboard"),t("tab_history"),t("tab_shop"),t("tab_redeem"),t("tab_exam"),t("tab_event")]
    base_mobile_user = [t("tab_checkin"),t("tab_leaderboard"),t("tab_shop"),t("tab_redeem")]

    if is_admin(current_role) or is_solo(current_role):
        tabs = base_mobile + [t("tab_settings")] if is_mobile_mode else base_desktop + [t("tab_settings")]
    elif is_host(current_role):
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
                try: thresholds = get_thresholds(view_as); thr = thresholds.get(view_today.weekday(), {"basic":0,"full":0})
                except: thr = {"basic":0,"full":0}
                st.subheader(f"{view_today.strftime('%m-%d')} - {get_weekday(view_today.weekday())}")
                st.caption(f"{t('basic_req')}: {thr['basic']} {t('lb_score')} | {t('full_req')}: {thr['full']} {t('lb_score')}")
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
                            if st.checkbox(f"{html.escape(task['name'])} ({task['points']}{t('lb_score')})", value=(task["id"] in done_ids), key=f"cb_{view_today}_{view_as}_{task['id']}", disabled=already_done):
                                if not already_done: selected_ids.append(task["id"])
                    else:
                        cols = st.columns(2)
                        for i, task in enumerate(items):
                            with cols[i % 2]:
                                if st.checkbox(f"{html.escape(task['name'])} ({task['points']}{t('lb_score')})", value=(task["id"] in done_ids), key=f"cb_{view_today}_{view_as}_{task['id']}", disabled=already_done):
                                    if not already_done: selected_ids.append(task["id"])
                st.divider()
                c1, c2, c3 = st.columns(3)
                if already_done:
                    c1.metric(t("base_score"), f"{float(existing['base_score'] or 0):.1f}")
                    c2.metric(t("bonus"), f"{float(existing['bonus_score'] or 0):.1f}")
                    c3.metric(t("today_total"), f"{float(existing['total_score'] or 0):.1f}")
                    st.success(t("today_done"))
                    if st.button(t("undo_checkin"), **_stretch({"type": "secondary"})):
                        try:
                            db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)); db.commit()
                            recalc_all_bonus(db, view_as); settle_longterm_bonus(db, view_as, now.isoformat())
                            st.cache_data.clear(); st.rerun()
                        except RuntimeError: st.error(t("op_failed"))
                else:
                    base_now = sum(task["points"] for task in tasks if task["id"] in set(selected_ids))
                    try:
                        lookup = {r["day"]: {"base_score": float(r["base_score"] or 0), "basic_thr": float(r.get("basic_thr") or 0), "full_thr": float(r.get("full_thr") or 0)} for r in db.execute("SELECT day, base_score, basic_thr, full_thr FROM daily_records WHERE owner_id=?", (view_as,)).fetchall()}
                        lookup[view_today.isoformat()] = {"base_score": base_now, "basic_thr": thr["basic"], "full_thr": thr["full"]}
                        bonus, detail = compute_bonus_for_day(view_today, lookup, get_bonus_rules(view_as))
                    except: bonus, detail = 0.0, {}
                    c1.metric(t("base_score"), f"{base_now:.1f}")
                    c2.metric(t("bonus"), f"{bonus:.1f}")
                    c3.metric(t("est_total"), f"{base_now + bonus:.1f}")
                    if st.button(t("save_checkin"), **_stretch({"type": "primary"})):
                        try: save_day(db, view_today, selected_ids, view_as, now.isoformat()); st.success(t("saved")); st.rerun()
                        except RuntimeError: st.error(t("op_failed"))

    # ============ 排行榜 ============
    if t("tab_leaderboard") in tab_dict and (is_host(current_role) or is_user(current_role)):
        with tab_dict[t("tab_leaderboard")]:
            st.subheader(t("lb_title"))
            if is_host(current_role):
                try: lb_children = [r["username"] for r in db.execute("SELECT username FROM users WHERE host_id=?", (current_user,)).fetchall()]
                except Exception: lb_children = []
            else:
                try:
                    my_row = db.execute("SELECT host_id FROM users WHERE username=?", (current_user,)).fetchone()
                    my_host = dict(my_row).get("host_id") if my_row else None
                    if my_host:
                        lb_children = [r["username"] for r in db.execute("SELECT username FROM users WHERE host_id=?", (my_host,)).fetchall()]
                    else: lb_children = [current_user]
                except Exception: lb_children = [current_user]
            if not lb_children: st.info(t("lb_no_data"))
            else:
                if is_user(current_role) and len(lb_children) <= 1: st.info(t("lb_only_you"))
                period = st.radio(t("lb_period"), options=["day","month","all"],
                    format_func=lambda x: t({"day":"lb_day","month":"lb_month","all":"lb_total"}[x]),
                    horizontal=True, key=f"lb_period_{current_role}")
                board = get_leaderboard(lb_children, period, user_tz)
                medals = ["🥇","🥈","🥉"]
                max_score = max((b["score"] for b in board), default=0) or 1
                for item in board:
                    rank_icon = medals[item["rank"]-1] if item["rank"] <= 3 else f"#{item['rank']}"
                    is_me = (is_user(current_role) and item["username"] == current_user)
                    nm = html.escape(item["username"])
                    if is_me: nm = f"**{nm}** :orange[**{t('lb_you')}**]"
                    st.markdown(f"**{rank_icon}  {nm}**  —  {item['score']:.1f} {t('lb_score')}")
                    st.progress(min(item["score"] / max_score, 1.0))

    # ============ 偶发 ============
    if t("tab_extra") in tab_dict:
        with tab_dict[t("tab_extra")]:
            # 【中危加固 8】偶发事件统一权限入口；保留 solo 可编辑自身配置的行为
            if not can_edit_configs(current_role):
                st.warning(t("extra_only_parent")); st.stop()
            st.subheader(t("extra_title"))
            with st.form("extra_point_form"):
                col1, col2, col3 = st.columns([4,2,2])
                e_name = col1.text_input(t("extra_name"))
                e_pts = col2.number_input(t("extra_points"), value=1.0, step=0.5)
                if _submit(t("extra_submit"), **_stretch({"type": "primary"})):
                    if e_name:
                        try:
                            db.execute("INSERT INTO extra_points (owner_id, name, points, ts) VALUES (?,?,?,?)", (view_as, e_name, e_pts, now.isoformat()))
                            db.commit(); st.cache_data.clear()
                            st.success(t("extra_saved", name=html.escape(e_name), pts=e_pts)); st.rerun()
                        except RuntimeError: st.error(t("op_failed"))
            st.divider()
            try: ex_rows = db.execute("SELECT * FROM extra_points WHERE owner_id=? ORDER BY id DESC LIMIT 20", (view_as,)).fetchall()
            except: ex_rows = []
            if ex_rows:
                st.dataframe([{"Time": r["ts"], "Event": html.escape(r["name"]), "Pts": float(r["points"] or 0)} for r in ex_rows], use_container_width=True, hide_index=True)
                if st.button(t("extra_clear"), **_stretch({})):
                    try: db.execute("DELETE FROM extra_points WHERE owner_id=?", (view_as,)); db.commit(); st.cache_data.clear(); st.rerun()
                    except RuntimeError: st.error(t("op_failed"))
            else: st.caption(t("extra_none"))

    # ============ 历史 ============
    if t("tab_history") in tab_dict:
        with tab_dict[t("tab_history")]:
            st.subheader(t("history_title"))
            view_makeup_hist = get_makeup_cards_of(view_as)
            if is_host(current_role) and is_user(view_role): st.info(t("makeup_host_tip"))
            elif is_host(view_role): st.info(t("makeup_host_self"))
            else:
                if view_makeup_hist > 0:
                    st.markdown(t("makeup_intro", n=view_makeup_hist))
                    try:
                        missing_dates = [view_today - timedelta(days=i) for i in range(1, 8) if not db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", ((view_today - timedelta(days=i)).isoformat(), view_as)).fetchone()]
                    except: missing_dates = []
                    if missing_dates:
                        sel_date = st.selectbox(t("makeup_pick_date"), missing_dates, format_func=lambda x: x.strftime('%Y-%m-%d') + f" ({get_weekday(x.weekday())})")
                        past_tasks = get_tasks(sel_date.weekday(), view_as)
                        st.write(t("makeup_pick_tasks", d=sel_date.strftime('%m-%d')))
                        with st.form("makeup_form"):
                            selected_past_ids = [task["id"] for task in past_tasks if st.checkbox(f"{html.escape(task['name'])} ({task['points']}{t('lb_score')})", key=f"makeup_cb_{sel_date}_{task['id']}")]
                            if _submit(t("makeup_submit"), **_stretch({"type": "primary"})):
                                db.begin()
                                try:
                                    cur = db.execute("UPDATE users SET makeup_cards = makeup_cards - 1 WHERE username=? AND makeup_cards > 0", (view_as,))
                                    if getattr(cur, "rowcount", 0) == 0:
                                        db.rollback(); db.end(); st.error(t("op_failed"))
                                    else:
                                        t_thr = get_thresholds(view_as).get(sel_date.weekday(), {"basic": 8, "full": 11})
                                        db.execute("DELETE FROM daily_records WHERE day=? AND owner_id=?", (sel_date.isoformat(), view_as))
                                        db.execute("INSERT INTO daily_records(day, owner_id, done_tasks, base_score, bonus_score, bonus_detail, total_score, updated_at, basic_thr, full_thr) VALUES (?, ?, ?, ?, 0, '{}', ?, ?, ?, ?)",
                                            (sel_date.isoformat(), view_as, json.dumps(sorted(selected_past_ids)), t_thr["full"], t_thr["full"], now.isoformat(), t_thr["basic"], t_thr["full"]))
                                        db.commit(); db.end()
                                        recalc_all_bonus(db, view_as); settle_longterm_bonus(db, view_as, now.isoformat())
                                        st.cache_data.clear(); st.success(t("makeup_ok")); st.rerun()
                                except Exception:
                                    db.rollback(); db.end(); st.error(t("makeup_fail"))
                    else: st.info(t("makeup_no_miss"))
                else: st.info(t("makeup_tip"))

            if is_user(view_role) or is_solo(view_role) or (is_admin(current_role) and view_as == current_user):
                st.divider()
                st.markdown(t("weekly_report"))
                start_date = view_today - timedelta(days=6)
                try:
                    week_records = db.execute("SELECT day, total_score FROM daily_records WHERE owner_id=? AND day >= ? AND day <= ? ORDER BY day ASC", (view_as, start_date.isoformat(), view_today.isoformat())).fetchall()
                except: week_records = []
                full_week = []
                for i in range(7):
                    d_str = (start_date + timedelta(days=i)).isoformat()
                    rec = next((r for r in week_records if r["day"] == d_str), None)
                    full_week.append({"day": d_str, "total_score": float(rec["total_score"]) if rec else 0.0})
                week_records = full_week
                scores = [r["total_score"] for r in week_records]
                days_count = len([s for s in scores if s > 0]); total_pts = sum(scores)
                max_daily_score = max(scores) if scores else 0.0
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric(t("week_checkin"), f"{days_count} d")
                rc2.metric(t("week_total"), f"{total_pts:.1f}")
                rc3.metric(t("day_max"), f"{max_daily_score:.1f}")
                if st.button(t("gen_report"), **_stretch({"type": "primary"})):
                    with st.spinner("..."):
                        try:
                            prop = setup_chinese_font()
                            dates_labels = [r["day"][5:] for r in week_records]
                            fig, ax = plt.subplots(figsize=(10, 6), facecolor='#f8f9fa'); ax.set_facecolor('#f8f9fa')
                            bars = ax.bar(dates_labels, scores, color='#4CAF50', width=0.5, zorder=3)
                            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
                            ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
                            for bar in bars:
                                yv = bar.get_height()
                                if yv > 0: ax.text(bar.get_x() + bar.get_width()/2, yv + 0.1, f'{yv:.1f}', ha='center', va='bottom', fontsize=10, fontproperties=prop)
                            title_text = f"🌟 {view_as} 🌟"
                            summary_text = f"{t('week_checkin')}: {days_count} | {t('week_total')}: {total_pts:.1f} | {t('day_max')}: {max_daily_score:.1f}"
                            if prop:
                                ax.set_title(title_text, fontproperties=prop, fontsize=18, pad=20)
                                fig.text(0.5, 0.88, summary_text, ha='center', fontsize=13, fontproperties=prop)
                                plt.xticks(fontproperties=prop); plt.yticks(fontproperties=prop)
                            else:
                                ax.set_title(title_text, fontsize=18, pad=20)
                                fig.text(0.5, 0.88, summary_text, ha='center', fontsize=13)
                            plt.tight_layout(rect=[0,0,1,0.85])
                            buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=200, bbox_inches="tight"); buf.seek(0); plt.close(fig)
                            st.image(buf, use_container_width=True)
                            st.download_button(t("save_report"), data=buf, file_name=f"{view_as}_weekly_{start_date.isoformat()}.png", mime="image/png", **_stretch({"type":"secondary"}))
                            st.success(t("report_ok"))
                        except Exception: st.error(t("report_failed"))

            st.divider()
            time_view = st.radio(t("time_view"), [t("by_day"), t("by_week"), t("by_month")], horizontal=True)
            try: all_recs = db.execute("SELECT day, total_score FROM daily_records WHERE owner_id=? ORDER BY day ASC", (view_as,)).fetchall()
            except: all_recs = []
            if all_recs:
                df = pd.DataFrame([{"Date": r["day"], "Score": float(r["total_score"] or 0)} for r in all_recs])
                df["Date"] = pd.to_datetime(df["Date"])
                if time_view == t("by_day"): df_grouped = df.copy(); x_title = t("by_day")
                elif time_view == t("by_week"): df_grouped = df.set_index("Date").resample('W-MON', label='left', closed='left').sum().reset_index(); x_title = t("by_week")
                else: df_grouped = df.set_index("Date").resample('MS').sum().reset_index(); x_title = t("by_month")
                st.altair_chart(alt.Chart(df_grouped).mark_line(point=True, color='#1f77b4').encode(x=alt.X('Date:T', title=x_title, axis=alt.Axis(labelAngle=0)), y=alt.Y('Score:Q', title=t("lb_score"), axis=alt.Axis(labelAngle=0)), tooltip=[alt.Tooltip('Date:T', format='%Y-%m-%d'), 'Score:Q']).interactive(), use_container_width=True)
                st.altair_chart(alt.Chart(df_grouped).mark_bar().encode(x=alt.X('Date:T', title=x_title, axis=alt.Axis(labelAngle=0)), y=alt.Y('Score:Q', title=t("lb_score"), axis=alt.Axis(labelAngle=0)), color=alt.Color('Score:Q', scale=alt.Scale(scheme='greens'), legend=None), tooltip=[alt.Tooltip('Date:T', format='%Y-%m-%d'), 'Score:Q']), use_container_width=True)
            else: st.info(t("no_data"))

            st.divider(); st.subheader(t("checkin_hist_detail"))
            try: days = [r["day"] for r in db.execute("SELECT day FROM daily_records WHERE owner_id=? ORDER BY day DESC", (view_as,)).fetchall()]
            except: days = []
            if days:
                sel = st.selectbox(t("select_date"), days)
                try:
                    row = db.execute("SELECT * FROM daily_records WHERE day=? AND owner_id=?", (sel, view_as)).fetchone()
                    st.write(f"**{t('today_total')}: {float(row['total_score'] or 0):.1f}** ({t('base_score')} {float(row['base_score'] or 0):.1f} + {t('bonus')} {float(row['bonus_score'] or 0):.1f})")
                    done = json.loads(row["done_tasks"]) if row["done_tasks"] else []
                    st.write(t("done_items"), ", ".join([html.escape(task["name"]) for task in get_tasks(date.fromisoformat(sel).weekday(), view_as) if task["id"] in done]) or t("none_yet"))
                except: pass
            else: st.info(t("no_record"))

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
                    display_name = t("backup_card") if name == "补签卡" else name
                    c1, c2, c3 = st.columns([5,2,2])
                    c1.write(f"**{html.escape(display_name)}**"); c2.write(f"`{cost} {t('lb_score')}`")
                    ck = f"confirm_buy_{view_as}_{name}"
                    if st.session_state.get(ck):
                        cc1, cc2 = st.columns(2)
                        if cc1.button(t("confirm_deduct"), key=f"yes_{view_as}_{name}", **_stretch({"type":"primary"})):
                            db.begin()
                            try:
                                q = "SELECT (SELECT COALESCE(SUM(total_score),0) FROM daily_records WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM period_bonus WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM exam_rewards WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM special_events WHERE owner_id=?)+(SELECT COALESCE(SUM(points),0) FROM extra_points WHERE owner_id=?)-(SELECT COALESCE(SUM(cost),0) FROM redemptions WHERE owner_id=?) AS bal"
                                row = db.execute(q, (view_as,view_as,view_as,view_as,view_as,view_as)).fetchone()
                                if float(row["bal"] or 0) < cost:
                                    db.end(); st.error(t("points_insufficient"))
                                else:
                                    db.execute("INSERT INTO redemptions (owner_id, item, cost, ts) VALUES (?,?,?,?)", (view_as, name, cost, now.isoformat()))
                                    if name == "补签卡": db.execute("UPDATE users SET makeup_cards = makeup_cards + 1 WHERE username=?", (view_as,))
                                    db.commit(); db.end()
                                    st.session_state[ck] = False; st.cache_data.clear(); st.success(t("redeem_ok")); st.rerun()
                            except Exception:
                                db.rollback(); db.end(); st.error(t("op_failed"))
                        if cc2.button(t("cancel"), key=f"no_{view_as}_{name}", **_stretch({})):
                            st.session_state[ck] = False; st.rerun()
                    else:
                        if c3.button(t("redeem_btn"), key=f"buy_{view_as}_{name}", disabled=(bal["balance"] < cost), **_stretch({})):
                            st.session_state[ck] = True; st.rerun()

    # ============ 兑换 ============
    if t("tab_redeem") in tab_dict:
        with tab_dict[t("tab_redeem")]:
            st.subheader(t("redeem_history"))
            try: rows = db.execute("SELECT * FROM redemptions WHERE owner_id=? ORDER BY id DESC", (view_as,)).fetchall()
            except: rows = []
            if rows:
                st.dataframe([{"Time": r["ts"], "Reward": html.escape(r["item"]), "Cost": float(r["cost"] or 0)} for r in rows], use_container_width=True)
            else: st.info(t("none_yet"))

    # ============ 考试 ============
    if t("tab_exam") in tab_dict:
        with tab_dict[t("tab_exam")]:
            st.subheader(t("exam_title"))
            try: exam_config, _ = get_exam_config(view_as)
            except: exam_config = {}
            if not exam_config: st.warning(t("exam_no_subject"))
            else:
                scores = {}; ranks = {}
                subj_list = list(exam_config.keys())
                for i in range(0, len(subj_list), 3):
                    cols = st.columns(3)
                    for j in range(3):
                        if i + j < len(subj_list):
                            sub = subj_list[i+j]; cfg = exam_config[sub]
                            with cols[j]:
                                if cfg["type"] == "score":
                                    max_s = float(cfg.get("max_score", 150))
                                    scores[sub] = st.number_input(html.escape(sub) + " " + t("exam_score", max=max_s, target=cfg['target']), min_value=0.0, max_value=max_s, value=float(cfg.get('target', 0)), key=f"ex_{view_as}_{sub}")
                                else:
                                    ti = GRADES.index(cfg['target']) if cfg['target'] in GRADES else 0
                                    scores[sub] = st.selectbox(html.escape(sub) + " " + t("exam_grade", target=cfg['target']), GRADES, index=ti, key=f"ex_sel_{view_as}_{sub}")
                st.write(t("exam_ranks"))
                c1, c2, c3 = st.columns(3)
                ranks["语文"] = c1.number_input(t("exam_cn"), 0.0, 100.0, 100.0, key=f"rk_cn_{view_as}")
                ranks["数学"] = c2.number_input(t("exam_ma"), 0.0, 100.0, 100.0, key=f"rk_ma_{view_as}")
                ranks["英语"] = c3.number_input(t("exam_en"), 0.0, 100.0, 100.0, key=f"rk_en_{view_as}")
                total_pts, lines, hit_count = calc_exam_bonus(scores, ranks, view_as)
                st.divider()
                st.markdown(t("exam_estimate", pts=f"{total_pts:.1f}", hits=hit_count))
                for ln in lines: st.write(ln)
                if st.button(t("exam_save"), **_stretch({"type": "primary"})):
                    try:
                        detail_text = f"hit={hit_count} | " + "/".join([f"{k}:{v}" for k, v in scores.items()])
                        db.execute("INSERT INTO exam_rewards (owner_id, detail, points, ts) VALUES (?,?,?,?)", (view_as, detail_text, total_pts, now.isoformat()))
                        db.commit(); st.cache_data.clear(); st.success(t("exam_saved")); st.rerun()
                    except RuntimeError: st.error(t("op_failed"))

    # ============ 事件 ============
    if t("tab_event") in tab_dict:
        with tab_dict[t("tab_event")]:
            st.subheader(t("event_title"))
            try: fired = db.execute("SELECT * FROM special_events WHERE day=? AND owner_id=?", (view_today.isoformat(), view_as)).fetchone()
            except: fired = None
            if fired:
                st.info(t("event_fired", note=html.escape(fired['note']), pts=float(fired['points'] or 0)))
            else:
                if st.session_state.get("confirm_roll"):
                    st.warning(t("event_confirm"))
                    rc1, rc2 = st.columns(2)
                    if rc1.button(t("event_roll"), **_stretch({"type": "primary"})):
                        try:
                            roll = random.random()
                            pts = random.randint(1,2) if roll < 0.4 else random.randint(3,5) if roll < 0.8 else random.randint(6,8) if roll < 0.95 else random.randint(10,15)
                            db.execute("INSERT INTO special_events (day, owner_id, points, note, ts) VALUES (?,?,?,?,?)", (view_today.isoformat(), view_as, pts, t("event_note"), now.isoformat()))
                            db.commit(); st.session_state["confirm_roll"] = False; st.cache_data.clear(); st.balloons(); st.success(t("event_got", pts=pts)); st.rerun()
                        except RuntimeError: st.error(t("op_failed"))
                    if rc2.button(t("cancel"), **_stretch({})): st.session_state["confirm_roll"] = False; st.rerun()
                else:
                    if st.button(t("event_roll_btn"), **_stretch({})): st.session_state["confirm_roll"] = True; st.rerun()

    # ============ 系统设置（保留中文/英文为主，因管理员操作） ============
    if t("tab_settings") in tab_dict:
        with tab_dict[t("tab_settings")]:
            st.subheader(t("tab_settings"))
            role_names = {"admin":t("role_admin"),"host":t("role_host"),"user":t("role_user"),"solo":t("role_solo")}
            if view_as == current_user: st.info(f"{html.escape(view_as)}")
            else: st.info(f"{html.escape(view_as)} ({role_names.get(view_role, view_role)})")

            st.markdown("### 1. 修改每日任务")
            sel_wd = st.selectbox(t("select_date") if False else "选择要修改的星期", range(7), format_func=lambda x: get_weekday(x))
            try: tasks_list = db.execute("SELECT * FROM config_tasks WHERE weekday=? AND owner_id=? ORDER BY category ASC, name ASC", (sel_wd, view_as)).fetchall()
            except: tasks_list = []
            edit_mode_key = f"task_edit_mode_{view_as}_{sel_wd}"
            if edit_mode_key not in st.session_state: st.session_state[edit_mode_key] = False
            header_cols = st.columns([3,1])
            header_cols[0].markdown(f"**{get_weekday(sel_wd)} ({len(tasks_list)})**")
            if header_cols[1].button("完成编辑" if st.session_state[edit_mode_key] else "✏️ 编辑", key=f"toggle_edit_{view_as}_{sel_wd}"):
                st.session_state[edit_mode_key] = not st.session_state[edit_mode_key]; st.rerun()
            selected_task_ids = []
            if tasks_list:
                for task in tasks_list:
                    if st.session_state[edit_mode_key]:
                        c1, c2, c3, c4 = st.columns([1,2,4,2])
                        if c1.checkbox("", key=f"chk_{view_as}_{sel_wd}_{task['id']}", label_visibility="collapsed"): selected_task_ids.append(task["id"])
                        c2.write(f"`{html.escape(str(task.get('category') or ''))}`"); c3.write(f"**{html.escape(str(task['name']))}**"); c4.write(f"{float(task['points'] or 0)}")
                    else:
                        c1, c2, c3 = st.columns([2,4,2])
                        c1.write(f"`{html.escape(str(task.get('category') or ''))}`"); c2.write(f"**{html.escape(str(task['name']))}**"); c3.write(f"{float(task['points'] or 0)}")
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
                                    ph = ",".join(["?"] * len(selected_task_ids))
                                    db.execute(f"DELETE FROM config_tasks WHERE id IN ({ph}) AND owner_id=?", (*selected_task_ids, view_as))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("OK"); st.rerun()
                                except Exception: db.rollback(); db.end(); st.error(t("op_failed"))
                        with ac3:
                            if st.button("🔄 同步到其他星期", **_stretch({})): st.session_state[f"syncing_tasks_{view_as}_{sel_wd}"] = selected_task_ids
                        edit_task_id = st.session_state.get(f"editing_task_id_{view_as}_{sel_wd}")
                        if edit_task_id:
                            t_te = next((x for x in tasks_list if x["id"] == edit_task_id), None)
                            if t_te:
                                with st.form(f"edit_task_form_{view_as}_{sel_wd}_{edit_task_id}"):
                                    ec1, ec2, ec3 = st.columns([2,3,2])
                                    e_cat = ec1.text_input("分类", value=t_te["category"] or "", key=f"ec_{edit_task_id}")
                                    e_name = ec2.text_input("任务名称", value=t_te["name"], key=f"en_{edit_task_id}")
                                    e_pts = ec3.text_input("分数", value=str(t_te["points"]), key=f"ep_{edit_task_id}")
                                    cs, cx = st.columns(2)
                                    if cs.form_submit_button("保存修改", type="primary", use_container_width=True):
                                        if not e_name.strip(): st.error("不能为空")
                                        else:
                                            try:
                                                pv = float(e_pts.strip() or "0")
                                                db.execute("UPDATE config_tasks SET category=?, name=?, points=? WHERE id=? AND owner_id=?", (e_cat.strip(), e_name.strip(), pv, edit_task_id, view_as))
                                                db.commit(); st.cache_data.clear(); st.session_state.pop(f"editing_task_id_{view_as}_{sel_wd}", None); st.success("OK"); st.rerun()
                                            except ValueError: st.error("数字")
                                            except RuntimeError: st.error(t("op_failed"))
                                    if cx.form_submit_button("取消编辑", use_container_width=True): st.session_state.pop(f"editing_task_id_{view_as}_{sel_wd}", None); st.rerun()
                        syncing_ids = st.session_state.get(f"syncing_tasks_{view_as}_{sel_wd}")
                        if syncing_ids:
                            with st.form(f"sync_tasks_form_{view_as}_{sel_wd}"):
                                target_days = []
                                scols = st.columns(7)
                                for i in range(7):
                                    if i != sel_wd:
                                        if scols[i].checkbox(get_weekday(i), key=f"sync_day_{view_as}_{sel_wd}_{i}"): target_days.append(i)
                                    else: scols[i].caption("当前")
                                if st.form_submit_button("确认同步", type="primary", use_container_width=True):
                                    if not target_days: st.warning("请选择")
                                    else:
                                        db.begin()
                                        try:
                                            for target_wd in target_days:
                                                for tt in [x for x in tasks_list if x["id"] in syncing_ids]:
                                                    nid = uuid.uuid4().hex
                                                    db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?) ON CONFLICT (owner_id, weekday, category, name) DO NOTHING", (nid, target_wd, view_as, tt["category"], tt["name"], tt["points"]))
                                            db.commit(); db.end(); st.cache_data.clear(); st.success("OK"); st.session_state.pop(f"syncing_tasks_{view_as}_{sel_wd}", None); st.rerun()
                                        except Exception: db.rollback(); db.end(); st.error(t("op_failed"))
                            if st.button("取消同步", key=f"cancel_sync_{view_as}_{sel_wd}"): st.session_state.pop(f"syncing_tasks_{view_as}_{sel_wd}", None); st.rerun()
                    else: st.caption("请勾选")
            with st.form(f"add_task_form_{view_as}_{sel_wd}", clear_on_submit=True):
                st.markdown("**➕ 新增任务**")
                tc1, tc2, tc3 = st.columns([2,3,2])
                new_cat = tc1.text_input("分类", key=f"new_task_cat_{view_as}_{sel_wd}")
                new_name = tc2.text_input("任务名称", key=f"new_task_name_{view_as}_{sel_wd}")
                new_pts_str = tc3.text_input("分数", key=f"new_task_pts_{view_as}_{sel_wd}")
                if _submit("➕ 添加任务", **_stretch({"type": "primary"})):
                    if not new_name.strip(): st.error("不能为空")
                    else:
                        try: pv = float((new_pts_str or "0").strip() or "0")
                        except ValueError: st.error("数字")
                        else:
                            try:
                                db.execute("INSERT INTO config_tasks (id, weekday, owner_id, category, name, points) VALUES (?,?,?,?,?,?)", (uuid.uuid4().hex, sel_wd, view_as, new_cat.strip(), new_name.strip(), pv))
                                db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                            except RuntimeError: st.error(t("op_failed"))

            st.divider(); st.markdown("### 2. 修改商城奖励")
            try: shop_list = db.execute("SELECT * FROM config_shop WHERE owner_id=? ORDER BY id ASC", (view_as,)).fetchall()
            except: shop_list = []
            edit_shop_key = f"shop_edit_mode_{view_as}"
            if edit_shop_key not in st.session_state: st.session_state[edit_shop_key] = False
            header_cols = st.columns([3,1])
            header_cols[0].markdown(f"**商城奖励 ({len(shop_list)})**")
            if header_cols[1].button("完成编辑" if st.session_state[edit_shop_key] else "✏️ 编辑", key=f"toggle_edit_shop_{view_as}"):
                st.session_state[edit_shop_key] = not st.session_state[edit_shop_key]; st.rerun()
            selected_shop_ids = []
            if shop_list:
                for s in shop_list:
                    if st.session_state[edit_shop_key]:
                        c1, c2, c3 = st.columns([1,5,2])
                        if c1.checkbox("", key=f"chk_shop_{view_as}_{s['id']}", label_visibility="collapsed"): selected_shop_ids.append(s["id"])
                        c2.write(f"**{html.escape(str(s['name']))}**"); c3.write(f"{float(s['cost'] or 0)}")
                    else:
                        c1, c2 = st.columns([5,2])
                        c1.write(f"**{html.escape(str(s['name']))}**"); c2.write(f"{float(s['cost'] or 0)}")
                if st.session_state[edit_shop_key]:
                    st.divider()
                    if selected_shop_ids:
                        ac1, ac2 = st.columns(2)
                        if len(selected_shop_ids) == 1:
                            with ac1:
                                if st.button("✏️ 编辑选中奖励", key=f"edit_shop_btn_{view_as}"): st.session_state[f"editing_shop_id_{view_as}"] = selected_shop_ids[0]
                        with ac2:
                            if st.button("🗑 删除选中奖励", key=f"del_shop_btn_{view_as}", **_stretch({"type":"primary"})):
                                db.begin()
                                try:
                                    ph = ",".join(["?"] * len(selected_shop_ids))
                                    db.execute(f"DELETE FROM config_shop WHERE id IN ({ph}) AND owner_id=?", (*selected_shop_ids, view_as))
                                    db.commit(); db.end(); st.cache_data.clear(); st.success("OK"); st.rerun()
                                except Exception: db.rollback(); db.end(); st.error(t("op_failed"))
                        edit_shop_id = st.session_state.get(f"editing_shop_id_{view_as}")
                        if edit_shop_id:
                            s_te = next((x for x in shop_list if x["id"] == edit_shop_id), None)
                            if s_te:
                                with st.form(f"edit_shop_form_{view_as}_{edit_shop_id}"):
                                    ec1, ec2 = st.columns(2)
                                    e_name = ec1.text_input("奖励名称", value=s_te["name"], key=f"es_name_{edit_shop_id}")
                                    e_cost = ec2.text_input("所需积分", value=str(s_te["cost"]), key=f"es_cost_{edit_shop_id}")
                                    cs, cx = st.columns(2)
                                    if cs.form_submit_button("保存修改", type="primary", use_container_width=True):
                                        if not e_name.strip(): st.error("不能为空")
                                        else:
                                            try:
                                                cv = float(e_cost.strip() or "0")
                                                db.execute("UPDATE config_shop SET name=?, cost=? WHERE id=? AND owner_id=?", (e_name.strip(), cv, edit_shop_id, view_as))
                                                db.commit(); st.cache_data.clear(); st.session_state.pop(f"editing_shop_id_{view_as}", None); st.success("OK"); st.rerun()
                                            except ValueError: st.error("数字")
                                            except RuntimeError: st.error(t("op_failed"))
                                    if cx.form_submit_button("取消编辑", use_container_width=True): st.session_state.pop(f"editing_shop_id_{view_as}", None); st.rerun()
            with st.form(f"add_shop_form_{view_as}", clear_on_submit=True):
                st.markdown("**➕ 新增奖励**")
                sc1, sc2 = st.columns([3,2])
                new_shop_name = sc1.text_input("奖励名称", key=f"new_shop_name_{view_as}")
                new_shop_cost_str = sc2.text_input("所需积分", key=f"new_shop_cost_{view_as}")
                if _submit("➕ 添加奖励", **_stretch({"type": "primary"})):
                    if not new_shop_name.strip(): st.error("不能为空")
                    else:
                        try: cv = float((new_shop_cost_str or "0").strip() or "0")
                        except ValueError: st.error("数字")
                        else:
                            try:
                                db.execute("INSERT INTO config_shop (owner_id, name, cost) VALUES (?,?,?)", (view_as, new_shop_name.strip(), cv))
                                db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                            except RuntimeError: st.error(t("op_failed"))

            st.divider(); st.markdown("### 3. 修改考试科目")
            try: exam_config, _ = get_exam_config(view_as)
            except: exam_config = {}
            if exam_config:
                for sub, cfg in exam_config.items():
                    c1, c2 = st.columns([3,1])
                    c1.write(f"**{html.escape(sub)}** — {cfg.get('target')}")
                    if c2.button("删除", key=f"del_sub_{sub}"):
                        try:
                            db.execute("DELETE FROM config_exam WHERE subject=? AND owner_id=?", (sub, view_as)); db.commit(); st.cache_data.clear(); st.rerun()
                        except RuntimeError: st.error(t("op_failed"))
            with st.form(f"add_exam_form_{view_as}", clear_on_submit=True):
                st.markdown("**➕ 新增科目（分数制）**")
                ec1, ec2, ec3 = st.columns(3)
                new_sub = ec1.text_input("科目名称", key=f"new_exam_sub_{view_as}")
                new_max = ec2.text_input("满分", value="150", key=f"new_exam_max_{view_as}")
                new_tgt = ec3.text_input("目标", value="105", key=f"new_exam_tgt_{view_as}")
                ec4, ec5 = st.columns(2)
                new_step = ec4.text_input("分差", value="3", key=f"new_exam_step_{view_as}")
                new_sp = ec5.text_input("单档奖励", value="2", key=f"new_exam_sp_{view_as}")
                if _submit("➕ 添加科目", **_stretch({"type": "primary"})):
                    if not new_sub.strip(): st.error("不能为空")
                    else:
                        try:
                            cfg = {"type":"score","max_score":float(new_max),"target":float(new_tgt),"step":float(new_step),"step_points":float(new_sp)}
                            db.execute("INSERT INTO config_exam (subject, owner_id, config_json) VALUES (?,?,?)", (new_sub.strip(), view_as, json.dumps(cfg)))
                            db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                        except (ValueError, RuntimeError): st.error(t("op_failed"))

            st.divider(); st.markdown("### 4. 修改多科达成奖励")
            try: mh_list = get_exam_multihit(view_as)
            except: mh_list = []
            if mh_list:
                for mh in mh_list:
                    c1, c2 = st.columns([5,1])
                    c1.write(f"**达成 {mh['hit_count']} 门及以上** → +{mh['points']}")
                    if c2.button("删除", key=f"del_mh_{mh['hit_count']}"):
                        try:
                            db.execute("DELETE FROM config_exam_multihit WHERE hit_count=? AND owner_id=?", (mh["hit_count"], view_as)); db.commit(); st.cache_data.clear(); st.rerun()
                        except RuntimeError: st.error(t("op_failed"))
            with st.form(f"add_mh_form_{view_as}", clear_on_submit=True):
                st.markdown("**➕ 新增多科奖励**")
                mc1, mc2 = st.columns(2)
                nmc = mc1.text_input("达成科目数", key=f"new_mh_count_{view_as}")
                nmp = mc2.text_input("奖励分数", value="2", key=f"new_mh_pts_{view_as}")
                if _submit("➕ 添加档位", **_stretch({"type": "primary"})):
                    try:
                        cv = int(nmc.strip()); pv = float(nmp.strip())
                        db.execute("INSERT INTO config_exam_multihit (hit_count, owner_id, points) VALUES (?,?,?)", (cv, view_as, pv))
                        db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                    except (ValueError, RuntimeError): st.error(t("op_failed"))

            st.divider(); st.markdown("### 5. 阈值与 Bonus 规则")
            try: thresholds = get_thresholds(view_as); bonus_rules = get_bonus_rules(view_as)
            except: thresholds = {}; bonus_rules = DEFAULT_BONUS_RULES
            with st.form(f"bonus_form_{view_as}"):
                t_cols = st.columns(7); tinp = {}
                for i in range(7):
                    with t_cols[i]:
                        st.markdown(f"**{get_weekday(i)}**")
                        tinp[i] = {"basic": st.number_input("基本", value=float(thresholds.get(i,{"basic":0})["basic"]), key=f"th_b_{view_as}_{i}"), "full": st.number_input("满分", value=float(thresholds.get(i,{"full":0})["full"]), key=f"th_f_{view_as}_{i}")}
                c1, c2 = st.columns(2)
                with c1:
                    wd_single = st.number_input("单日达标", value=float(bonus_rules["weekday"]["single"]["points"]), step=0.5, key=f"b1_{view_as}")
                    wd_single_full = st.number_input("单日满分", value=float(bonus_rules["weekday"]["single"]["full_points"]), step=0.5, key=f"b2_{view_as}")
                    wd_2 = st.number_input("连2达标", value=float(bonus_rules["weekday"]["streak2"]["points"]), step=0.5, key=f"b3_{view_as}")
                    wd_2_full = st.number_input("连2满分", value=float(bonus_rules["weekday"]["streak2"]["full_points"]), step=0.5, key=f"b4_{view_as}")
                    wd_4 = st.number_input("连4达标", value=float(bonus_rules["weekday"]["streak4"]["points"]), step=0.5, key=f"b5_{view_as}")
                    wd_4_full = st.number_input("连4满分", value=float(bonus_rules["weekday"]["streak4"]["full_points"]), step=0.5, key=f"b6_{view_as}")
                with c2:
                    we_single = st.number_input("周末单日达标", value=float(bonus_rules["weekend"]["single"]["points"]), step=0.5, key=f"b7_{view_as}")
                    we_single_full = st.number_input("周末单日满分", value=float(bonus_rules["weekend"]["single"]["full_points"]), step=0.5, key=f"b8_{view_as}")
                    lt_wb = st.number_input("整周达标", value=float(bonus_rules["longterm"]["week_basic"]), step=0.5, key=f"b9_{view_as}")
                    lt_wf = st.number_input("完美一周", value=float(bonus_rules["longterm"]["week_full"]), step=0.5, key=f"b10_{view_as}")
                    lt_mb = st.number_input("整月达标", value=float(bonus_rules["longterm"]["month_basic"]), step=0.5, key=f"b11_{view_as}")
                    lt_mf = st.number_input("完美一月", value=float(bonus_rules["longterm"]["month_full"]), step=0.5, key=f"b12_{view_as}")
                    flex_p = st.number_input("弹性完美扣减", value=float(bonus_rules["longterm"].get("week_flex_perfect_deduct",1.0)), step=0.5, key=f"b13_{view_as}")
                    flex_b = st.number_input("弹性达标扣减", value=float(bonus_rules["longterm"].get("week_flex_basic_deduct",0.5)), step=0.5, key=f"b14_{view_as}")
                if _submit("保存新规则", **_stretch({"type": "primary"})):
                    try:
                        for i in range(7):
                            db.execute("DELETE FROM config_thresholds WHERE weekday=? AND owner_id=?", (i, view_as))
                            db.execute('INSERT INTO config_thresholds (weekday, owner_id, basic, "full") VALUES (?,?,?,?)', (i, view_as, tinp[i]["basic"], tinp[i]["full"]))
                        nb = {
                            "weekday": {"single": {"points": wd_single, "full_points": wd_single_full}, "streak2": {"points": wd_2, "full_points": wd_2_full}, "streak4": {"points": wd_4, "full_points": wd_4_full}},
                            "weekend": {"single": {"points": we_single, "full_points": we_single_full}},
                            "longterm": {"week_basic": lt_wb, "week_full": lt_wf, "month_basic": lt_mb, "month_full": lt_mf, "week_flex_perfect_deduct": flex_p, "week_flex_basic_deduct": flex_b}
                        }
                        db.execute("DELETE FROM config_bonus_rules WHERE owner_id=?", (view_as,))
                        db.execute("INSERT INTO config_bonus_rules (owner_id, rules_json) VALUES (?,?)", (view_as, json.dumps(nb)))
                        db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                    except RuntimeError: st.error(t("op_failed"))

            # 徽章管理
            st.divider(); st.markdown("### 6. 全局徽章")
            if is_admin(view_role):
                require_admin(view_role)
                with st.form("add_badge_form"):
                    c1, c2, c3 = st.columns([3,2,2])
                    bn = c1.text_input("徽章名称")
                    bt = c2.selectbox("条件", options=["days","points","perfect","exam_hits"], format_func=lambda x: {"days":"打卡天数","points":"累计积分","perfect":"完美次数","exam_hits":"单次达成科目数"}.get(x,x))
                    bv = c3.number_input("数值", min_value=1.0, step=1.0)
                    if _submit("✨ 生成并添加", **_stretch({"type": "primary"})):
                        if bn:
                            try:
                                seed = random.randint(1, 99999)
                                prompt = f"Minimalist flat vector icon for '{bn}', clean simple design, ui app icon, no text, white background."
                                icon = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=256&height=256&nologo=true&seed={seed}"
                                db.execute("INSERT INTO config_badges (owner_id, name, cond_type, cond_val, icon_url) VALUES ('system', ?, ?, ?, ?)", (bn, bt, bv, icon))
                                db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                            except RuntimeError: st.error(t("op_failed"))
            else: st.info("管理员配置")

            # 用户管理（含搜索）
            if is_admin(view_role):
                require_admin(view_role)
                st.divider(); st.markdown("### 7. 用户管理与权限控制")
                # 搜索框
                user_kw = st.text_input(t("search_users"), key="admin_user_search")
                filtered_users = all_users_data
                if user_kw:
                    filtered_users = [u for u in all_users_data if user_kw.lower() in u["username"].lower()]
                st.caption(f"共 {len(filtered_users)} / {len(all_users_data)} 人")
                if not filtered_users:
                    st.warning(t("no_match"))
                for u in filtered_users:
                    uname = u["username"]; urole = u["role"]
                    try: host_row = db.execute("SELECT host_id FROM users WHERE username=?", (uname,)).fetchone(); uhost = dict(host_row).get("host_id") if host_row else None
                    except: uhost = None
                    is_self = (uname == current_user)
                    role_badge = {"admin":"🟢","host":"🟡","user":"⚪","solo":"🔵"}.get(urole, urole)
                    plan_exp = u.get("plan_expires_at") or ""
                    is_perm = str(plan_exp).startswith("2099")
                    plan_str = " [∞]" if is_perm else (f" [{str(plan_exp)[:10]}]" if plan_exp else " [exp]")
                    c1, c2, c3, c4 = st.columns([3,2,3,2])
                    c1.write(f"👤 **{html.escape(uname)}**{plan_str}" + (" (you)" if is_self else ""))
                    c2.write(role_badge)
                    c3.write(f"↳ {html.escape(uhost)}" if uhost else "—")
                    if not is_self:
                        with c4:
                            with st.expander("操作"):
                                if st.button("→ Admin", key=f"set_admin_{uname}", **_stretch({})):
                                    try: db.execute("UPDATE users SET role='admin' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                    except RuntimeError: st.error(t("op_failed"))
                                if st.button("→ Host", key=f"set_host_{uname}", disabled=(urole == "host"), **_stretch({})):
                                    try: db.execute("UPDATE users SET role='host' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                    except RuntimeError: st.error(t("op_failed"))
                                if st.button("→ User", key=f"set_user_{uname}", disabled=(urole == "user"), **_stretch({})):
                                    try: db.execute("UPDATE users SET role='user' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                    except RuntimeError: st.error(t("op_failed"))
                                if st.button("→ Solo", key=f"set_solo_{uname}", disabled=(urole == "solo"), **_stretch({})):
                                    try: db.execute("UPDATE users SET role='solo' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                    except RuntimeError: st.error(t("op_failed"))
                                if st.button("⭐ 永久", key=f"set_perm_{uname}", disabled=is_perm, **_stretch({})):
                                    try: db.execute("UPDATE users SET plan_expires_at='2099-12-31 23:59:59' WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                    except RuntimeError: st.error(t("op_failed"))
                                if st.button("重置密码", key=f"reset_{uname}", **_stretch({})):
                                    try: db.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_pwd_bcrypt("123456"), uname)); db.commit(); st.success("OK")
                                    except RuntimeError: st.error(t("op_failed"))
                                bv = st.text_input("绑定 host", value=uhost or "", key=f"bind_val_{uname}", label_visibility="collapsed")
                                if st.button("保存绑定", key=f"save_bind_{uname}", **_stretch({})):
                                    tgt = (bv or "").strip()
                                    if not tgt: st.error("空")
                                    elif tgt == uname: st.error("不能绑定自己")
                                    else:
                                        try:
                                            t_row = db.execute("SELECT role FROM users WHERE username=?", (tgt,)).fetchone()
                                            if not t_row or t_row["role"] not in ("host","admin"): st.error("目标无效")
                                            else:
                                                db.execute("UPDATE users SET host_id=? WHERE username=?", (tgt, uname)); db.commit(); st.cache_data.clear(); st.success("OK"); st.rerun()
                                        except RuntimeError: st.error(t("op_failed"))
                                if st.button("解绑", key=f"unbind_{uname}", disabled=(not uhost), **_stretch({})):
                                    try: db.execute("UPDATE users SET host_id=NULL WHERE username=?", (uname,)); db.commit(); st.cache_data.clear(); st.rerun()
                                    except RuntimeError: st.error(t("op_failed"))
                                # 【中危加固 10】彻底删除用户统一走 delete_user_all_data
                                st.markdown("**危险操作**")
                                confirm_del = st.checkbox("确认彻底删除该用户", key=f"confirm_del_{uname}")
                                if st.button("🗑 彻底删除用户", key=f"del_user_{uname}", disabled=(not confirm_del), **_stretch({"type": "primary"})):
                                    require_admin(view_role)
                                    if urole == "admin" and _remaining_admins(db, uname) == 0:
                                        st.error("不能删除最后一个管理员")
                                    else:
                                        try:
                                            delete_user_all_data(db, uname)
                                            db.commit(); st.cache_data.clear(); st.success("已彻底删除"); st.rerun()
                                        except Exception:
                                            st.error(t("op_failed"))
                    st.divider()

                with st.expander("💳 生成兑换码"):
                    vd = st.number_input("有效天数", min_value=1, value=30)
                    if st.button("生成", type="primary"):
                        nc = uuid.uuid4().hex[:8].upper()
                        try:
                            db.execute("INSERT INTO redeem_codes (code, days, is_used, created_at) VALUES (?,?,0,?)", (nc, int(vd), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            db.commit(); st.success("OK"); st.code(nc, language="text")
                        except RuntimeError: st.error(t("op_failed"))

                # 【中危加固 6】云端数据库备份（管理员）
                with st.expander("☁️ 云端数据库备份（管理员）"):
                    st.caption("Streamlit 没有后台定时任务能力，应用内提供一键 JSON 全库导出，作为云端 PostgreSQL 的最大补偿。")
                    if st.button("📥 生成完整备份 (JSON)", key="cloud_backup_generate"):
                        try:
                            backup_data = {}
                            for tbl in ALL_TABLES:
                                try:
                                    rows = db.execute(f"SELECT * FROM {tbl}").fetchall()
                                    backup_data[tbl] = [dict(r) for r in rows]
                                except Exception:
                                    continue
                            st.session_state["cloud_backup_json"] = json.dumps(backup_data, ensure_ascii=False, indent=2, default=str)
                            st.session_state["cloud_backup_filename"] = f"study_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            st.success("备份已生成，请点击下方按钮下载。")
                        except Exception:
                            st.error(t("op_failed"))
                    if st.session_state.get("cloud_backup_json"):
                        st.download_button(
                            "📥 下载完整备份 (JSON)",
                            data=st.session_state.get("cloud_backup_json"),
                            file_name=st.session_state.get("cloud_backup_filename", "study_backup.json"),
                            mime="application/json",
                            key="cloud_backup_download"
                        )
                    with st.expander("📖 如何配置外部定时备份"):
                        st.markdown("""
- **推荐方案**：在你的 PostgreSQL 服务商（如 Supabase、Neon）控制台开启自动备份。
- **或配置外部 cron**：定时执行 `pg_dump`，把 SQL 文件保存到对象存储。
- **应用本身无法后台备份**：这是 Streamlit 的请求驱动架构限制；本页 JSON 导出只能在管理员打开页面时手动触发。
- 密码哈希已原样导出，备份文件请妥善保管，不要公开分享。
""")

if __name__ == "__main__":
    main()
