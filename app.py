"""RMA 午餐猜謎遊戲 — Streamlit 版
3 台電腦各自連到同一個網址:
  - 主持人那台選「主持人」,控制題目開放/公布、看即時計分
  - 其餘 3 台各自選「第1組/第2組/第3組」,負責送出該組答案
狀態共用一份 data/state.json,所有電腦連到同一網址即可即時同步。
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from state import load_state, save_state, reset_game

st.set_page_config(page_title="RMA 午餐猜謎", page_icon="🎉", layout="centered")

STATUS_LABEL = {
    "idle": "⏳ 尚未開放作答",
    "open": "🟢 作答中",
    "closed": "🔒 已鎖定,等待公布",
    "revealed": "✅ 已公布答案",
}


def get_question(state, qid):
    for q in state["questions"]:
        if q["id"] == qid:
            return q
    return None


def submit_answer(state, qid, gid, value):
    qid_s, gid_s = str(qid), str(gid)
    state["answers"].setdefault(qid_s, {})[gid_s] = value
    save_state(state)


def open_question(state, qid):
    state["current"] = qid
    state["status"] = "open"
    save_state(state)


def close_question(state):
    state["status"] = "closed"
    save_state(state)


def reveal_question(state, qid):
    qid_s = str(qid)
    if state["scored"].get(qid_s):
        state["status"] = "revealed"
        save_state(state)
        return
    q = get_question(state, qid)
    answers = state["answers"].get(qid_s, {})
    winners = []
    if q["type"] == "number" and q["correct_number"] is not None:
        diffs = {}
        for gid, val in answers.items():
            try:
                diffs[gid] = abs(float(val) - float(q["correct_number"]))
            except (TypeError, ValueError):
                continue
        if diffs:
            best = min(diffs.values())
            winners = [gid for gid, d in diffs.items() if d == best]
    elif q["type"] == "choice" and q["correct_option"] is not None:
        for gid, val in answers.items():
            if val is not None and int(val) == int(q["correct_option"]):
                winners.append(gid)

    for gid in winners:
        state["scores"][gid] = state["scores"].get(gid, 0) + 1

    state["awarded"][qid_s] = winners
    state["scored"][qid_s] = True
    state["status"] = "revealed"
    save_state(state)


def undo_reveal(state, qid):
    qid_s = str(qid)
    for gid in state["awarded"].get(qid_s, []):
        state["scores"][gid] = state["scores"].get(gid, 0) - 1
    state["awarded"][qid_s] = []
    state["scored"][qid_s] = False
    state["status"] = "closed"
    save_state(state)


def next_question(state):
    if state["current"] < len(state["questions"]):
        state["current"] += 1
        state["status"] = "idle"
        save_state(state)


# ---------------- 側邊欄:身份選擇 ----------------
st.sidebar.title("🎉 RMA 午餐猜謎")
role = st.sidebar.radio(
    "你是誰?",
    ["🎤 主持人", "1️⃣ 第1組", "2️⃣ 第2組", "3️⃣ 第3組"],
    key="role",
)

state = load_state()

# ================= 主持人畫面 =================
if role == "🎤 主持人":
    mode = st.sidebar.radio("模式", ["🎮 遊戲控制台", "📝 題目與答案設定"], key="host_mode")

    if mode == "📝 題目與答案設定":
        st.header("📝 題目與答案設定")
        st.caption("活動前先把每題的正解、選項內容填好。隨時存檔,隨時可以調整。")

        with st.expander("✏️ 修改組名", expanded=False):
            cols = st.columns(3)
            new_names = {}
            for i, c in enumerate(cols, start=1):
                new_names[str(i)] = c.text_input(f"第{i}組", state["group_names"][str(i)], key=f"gname_{i}")
            if st.button("儲存組名"):
                state["group_names"] = new_names
                save_state(state)
                st.success("已儲存")

        for q in state["questions"]:
            with st.expander(f"第 {q['id']} 題:{q['title']}", expanded=False):
                st.caption(q["hint"])
                q["title"] = st.text_input("題目文字", q["title"], key=f"title_{q['id']}")
                q["type"] = st.selectbox(
                    "題型", ["number", "choice"],
                    index=["number", "choice"].index(q["type"]),
                    format_func=lambda x: "數字估算(最接近者得分)" if x == "number" else "三選一(答對得分)",
                    key=f"type_{q['id']}",
                )
                if q["type"] == "number":
                    q["correct_number"] = st.number_input(
                        "正確數字",
                        value=float(q["correct_number"]) if q["correct_number"] is not None else 0.0,
                        key=f"num_{q['id']}",
                    )
                else:
                    for i in range(3):
                        q["options"][i] = st.text_input(
                            f"選項 {chr(65+i)}", q["options"][i], key=f"opt_{q['id']}_{i}"
                        )
                    current_idx = q["correct_option"] if q["correct_option"] is not None else 0
                    q["correct_option"] = ["A", "B", "C"].index(
                        st.radio(
                            "正確答案",
                            ["A", "B", "C"],
                            index=current_idx,
                            horizontal=True,
                            key=f"ans_{q['id']}",
                        )
                    )
                q["story"] = st.text_area("揭曉時要講的小故事(給自己看的備忘)", q["story"], key=f"story_{q['id']}")
                if st.button("儲存這一題", key=f"save_{q['id']}"):
                    save_state(state)
                    st.success("已儲存")

    else:
        st_autorefresh(interval=2000, key="host_refresh")
        st.header("🎮 遊戲控制台")

        total_q = len(state["questions"])
        cur_qid = state["current"]
        q = get_question(state, cur_qid)

        st.subheader(f"第 {cur_qid} / {total_q} 題")
        st.markdown(f"**{q['title']}**")
        st.caption(q["hint"])
        st.markdown(f"狀態:{STATUS_LABEL[state['status']]}")

        answers = state["answers"].get(str(cur_qid), {})
        cols = st.columns(3)
        for i, c in enumerate(cols, start=1):
            gid = str(i)
            name = state["group_names"][gid]
            val = answers.get(gid)
            if val is None or val == "":
                c.metric(name, "尚未作答")
            else:
                label = val if q["type"] == "number" else ["A", "B", "C"][int(val)]
                c.metric(name, label)

        btn_cols = st.columns(4)
        if btn_cols[0].button("🟢 開放作答", use_container_width=True):
            open_question(state, cur_qid)
            st.rerun()
        if btn_cols[1].button("🔒 鎖定作答", use_container_width=True):
            close_question(state)
            st.rerun()
        if btn_cols[2].button("✅ 公布答案", use_container_width=True):
            reveal_question(state, cur_qid)
            st.rerun()
        if btn_cols[3].button("↩️ 撤銷公布", use_container_width=True):
            undo_reveal(state, cur_qid)
            st.rerun()

        if state["status"] == "revealed":
            if q["type"] == "number":
                st.info(f"正確答案:{q['correct_number']}")
            else:
                correct_opt = q["correct_option"]
                if correct_opt is not None:
                    st.info(f"正確答案:{['A','B','C'][correct_opt]}. {q['options'][correct_opt]}")
            winners = state["awarded"].get(str(cur_qid), [])
            if winners:
                st.success("得分:" + "、".join(state["group_names"][g] for g in winners))
            else:
                st.warning("這題沒有組別得分")
            if q["story"]:
                st.markdown(f"💬 小故事:{q['story']}")

        st.divider()
        if st.button("➡️ 下一題", disabled=cur_qid >= total_q, use_container_width=True):
            next_question(state)
            st.rerun()

        st.divider()
        st.subheader("🏆 即時排行榜")
        score_cols = st.columns(3)
        ranking = sorted(state["scores"].items(), key=lambda kv: -kv[1])
        for i, c in enumerate(score_cols, start=1):
            gid = str(i)
            c.metric(state["group_names"][gid], f"{state['scores'][gid]} 分")
        if cur_qid >= total_q and state["status"] == "revealed":
            top_score = ranking[0][1]
            top_groups = [state["group_names"][g] for g, s in ranking if s == top_score]
            st.balloons()
            st.success(f"🎉 冠軍:{ '、'.join(top_groups) } — 加點飲料!其他組也有肉圓可以多拿 🍡")

        with st.expander("⚠️ 重置整場遊戲(清空所有答案與分數)"):
            if st.button("我確定要重置", type="primary"):
                reset_game(state)
                st.rerun()

# ================= 小組作答畫面 =================
else:
    st_autorefresh(interval=2000, key="group_refresh")
    gid = {"1️⃣ 第1組": "1", "2️⃣ 第2組": "2", "3️⃣ 第3組": "3"}[role]
    gname = state["group_names"][gid]
    st.header(f"👋 {gname}")

    cur_qid = state["current"]
    q = get_question(state, cur_qid)
    status = state["status"]

    st.subheader(f"第 {cur_qid} / {len(state['questions'])} 題")
    st.markdown(f"狀態:{STATUS_LABEL[status]}")

    answers = state["answers"].get(str(cur_qid), {})
    my_answer = answers.get(gid)

    if status == "idle":
        st.info("請等待主持人開放這一題作答 🙏")
    else:
        st.markdown(f"### {q['title']}")

        if status == "open":
            if q["type"] == "number":
                default_val = float(my_answer) if my_answer not in (None, "") else 0.0
                val = st.number_input("你們這組的答案", value=default_val, step=1.0, key=f"input_{cur_qid}")
                if st.button("📨 送出 / 修改答案"):
                    submit_answer(state, cur_qid, gid, val)
                    st.rerun()
            else:
                opt_labels = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(q["options"])]
                default_idx = int(my_answer) if my_answer not in (None, "") else 0
                choice = st.radio("你們這組的答案", opt_labels, index=default_idx, key=f"choice_{cur_qid}")
                if st.button("📨 送出 / 修改答案"):
                    submit_answer(state, cur_qid, gid, opt_labels.index(choice))
                    st.rerun()

            if my_answer not in (None, ""):
                shown = my_answer if q["type"] == "number" else opt_labels[int(my_answer)]
                st.success(f"✅ 已送出:{shown}(作答中可隨時修改)")
            else:
                st.warning("⚠️ 還沒送出答案")

        else:  # closed or revealed
            if my_answer not in (None, ""):
                shown = my_answer if q["type"] == "number" else ["A", "B", "C"][int(my_answer)]
                st.write(f"你們送出的答案:**{shown}**")
            else:
                st.write("這題沒有送出答案")

            if status == "revealed":
                if q["type"] == "number":
                    st.info(f"正確答案:{q['correct_number']}")
                else:
                    st.info(f"正確答案:{q['options'][q['correct_option']]}")
                winners = state["awarded"].get(str(cur_qid), [])
                if gid in winners:
                    st.success("🎉 這題你們得分!")
                else:
                    st.warning("這題沒得分,下一題加油")

    st.divider()
    st.subheader("🏆 目前排行榜")
    score_cols = st.columns(3)
    for i, c in enumerate(score_cols, start=1):
        gi = str(i)
        c.metric(state["group_names"][gi], f"{state['scores'][gi]} 分")
