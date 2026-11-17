"""遊戲狀態的讀寫。用一個 JSON 檔當簡單的共享資料庫,
讓主持人電腦與 3 組的電腦都讀寫同一份狀態,達到即時同步。
"""
import json
import os
from pathlib import Path

STATE_FILE = Path(__file__).parent / "data" / "state.json"

NUM_GROUPS = 4
_GROUP_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八"]


def default_group_name(i):
    return f"第{_GROUP_NUMERALS[i - 1]}組"

DEFAULT_QUESTIONS = [
    {
        "id": 1,
        "type": "number",
        "title": "暖身題:今年一共修了幾台?",
        "hint": "各組估一個數字,最接近者勝。",
        "options": ["", "", ""],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 2,
        "type": "choice",
        "title": "今年送修量第一名的是哪個系列?",
        "hint": "三選一,其中一個是正解,另外兩個是看起來很像的熱門型號。",
        "options": ["選項 A", "選項 B", "選項 C"],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 3,
        "type": "choice",
        "title": "今年哪個月最忙?",
        "hint": "三選一,揭曉時可以順口講那個月發生了什麼事。",
        "options": ["月份 A", "月份 B", "月份 C"],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 4,
        "type": "number",
        "title": "今年 TAT 最長的那一台卡了幾天?",
        "hint": "估算題,揭曉時說明卡在哪裡(等料/等客戶回覆/等 RD)。",
        "options": ["", "", ""],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 5,
        "type": "choice",
        "title": "真假題:念三句退修單上的客戶原文描述,哪一句是假的?",
        "hint": "客戶名稱與可辨識資訊記得先拿掉,其中一句是自己編的。",
        "options": ["第一句是假的", "第二句是假的", "第三句是假的"],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 6,
        "type": "choice",
        "title": "今年送修回來、檢測完沒有異常(NPF)的大約占幾成?",
        "hint": "給三個區間讓大家選。",
        "options": ["區間 A", "區間 B", "區間 C"],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 7,
        "type": "number",
        "title": "今年送修中,保固內的比例大約占幾成?",
        "hint": "各組估一個百分比數字(例如 70 代表七成),最接近者勝。",
        "options": ["", "", ""],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 8,
        "type": "choice",
        "title": "RMA 團隊最常吃的下午茶點是什麼?",
        "hint": "三選一,其中一個是正解,另外兩個是陪榜的。",
        "options": ["選項 A", "選項 B", "選項 C"],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 9,
        "type": "number",
        "title": "今年我們一共有幾個 Quality Case?",
        "hint": "各組估一個數字,最接近者勝。",
        "options": ["", "", ""],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 10,
        "type": "number",
        "title": "今年我們一共有幾個 CICC 案件?",
        "hint": "各組估一個數字,最接近者勝。",
        "options": ["", "", ""],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
    {
        "id": 11,
        "type": "number",
        "title": "收尾題:平均每個工作天,團隊要修幾台?",
        "hint": "總台數除以工作天數,揭曉時收在「這是大家一起扛下來的」。",
        "options": ["", "", ""],
        "correct_number": None,
        "correct_option": None,
        "story": "",
    },
]


def default_state():
    return {
        "group_names": {str(i): default_group_name(i) for i in range(1, NUM_GROUPS + 1)},
        "questions": DEFAULT_QUESTIONS,
        "current": 1,
        "status": "idle",  # idle / open / closed / revealed
        "answers": {},      # {qid_str: {gid_str: answer}}
        "scores": {str(i): 0 for i in range(1, NUM_GROUPS + 1)},
        "scored": {},        # {qid_str: True} 避免重複計分
        "awarded": {},       # {qid_str: [gid, ...]} 該題拿到分的組,方便撤銷
    }


def _migrate_group_count(state):
    """補上組數變動後缺少的 group_names / scores 欄位(例如從 3 組改成 4 組)。"""
    changed = False
    for i in range(1, NUM_GROUPS + 1):
        gid = str(i)
        if gid not in state["group_names"]:
            state["group_names"][gid] = default_group_name(i)
            changed = True
        if gid not in state["scores"]:
            state["scores"][gid] = 0
            changed = True
    return changed


def load_state():
    if not STATE_FILE.exists():
        state = default_state()
        save_state(state)
        return state
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    if _migrate_group_count(state):
        save_state(state)
    return state


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = STATE_FILE.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, STATE_FILE)


def reset_game(state):
    fresh = default_state()
    fresh["group_names"] = state.get("group_names", fresh["group_names"])
    fresh["questions"] = state.get("questions", fresh["questions"])
    save_state(fresh)
    return fresh
