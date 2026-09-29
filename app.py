"""쇼핑리스트 앱 (Streamlit)

실행: streamlit run app.py
"""

import json
import os
import uuid

import streamlit as st

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shopping_list.json")

# 아이템 데이터 모델 (PRD 5장)
# {
#     "id": str,        # uuid4, 고유 식별자
#     "name": str,      # 아이템 이름
#     "quantity": int,  # 수량 (1 이상)
#     "checked": bool,  # 구매 완료 여부
# }


# ---------- 파일 저장 / 불러오기 ----------
def load_items():
    """shopping_list.json에서 아이템 목록을 읽어온다. 파일이 없거나 깨져 있으면 빈 목록."""
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    items = []
    for raw in data:
        # 형식이 맞지 않는 아이템은 건너뛴다.
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str) or not raw["name"].strip():
            continue
        try:
            quantity = max(1, int(raw.get("quantity", 1)))
        except (TypeError, ValueError):
            quantity = 1
        items.append({
            "id": str(raw.get("id") or uuid.uuid4()),
            "name": raw["name"].strip(),
            "quantity": quantity,
            "checked": bool(raw.get("checked", False)),
        })
    return items


def save_items():
    """현재 아이템 목록을 shopping_list.json에 저장한다."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state["items"], f, ensure_ascii=False, indent=2)


# ---------- 상태 초기화 ----------
def init_state():
    # "items"는 dict 메서드 이름과 겹치므로 st.session_state["items"]로 접근한다.
    if "items" not in st.session_state:
        st.session_state["items"] = load_items()
    if "editing_id" not in st.session_state:
        st.session_state["editing_id"] = None
    if "edit_error" not in st.session_state:
        st.session_state["edit_error"] = False


def find_item(item_id):
    for item in st.session_state["items"]:
        if item["id"] == item_id:
            return item
    return None


# ---------- 아이템 조작 ----------
def add_item(name, quantity):
    """새 아이템을 목록 끝에 추가한다."""
    st.session_state["items"].append({
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": max(1, int(quantity)),
        "checked": False,
    })
    save_items()


def update_item(item_id, name, quantity):
    """id로 아이템을 찾아 이름과 수량을 변경한다."""
    item = find_item(item_id)
    if item:
        item["name"] = name
        item["quantity"] = max(1, int(quantity))
        save_items()


def delete_item(item_id):
    """id에 해당하는 아이템을 삭제한다."""
    st.session_state["items"] = [i for i in st.session_state["items"] if i["id"] != item_id]
    if st.session_state["editing_id"] == item_id:
        st.session_state["editing_id"] = None
    save_items()


def toggle_item(item_id):
    """체크박스 값에 맞춰 아이템의 구매 완료 여부를 바꾼다."""
    item = find_item(item_id)
    if item:
        item["checked"] = st.session_state[f"chk_{item_id}"]
        save_items()


def clear_checked():
    """체크된 아이템을 모두 삭제한다."""
    st.session_state["items"] = [i for i in st.session_state["items"] if not i["checked"]]
    if find_item(st.session_state["editing_id"]) is None:
        st.session_state["editing_id"] = None
    save_items()


# ---------- 수정 모드 콜백 ----------
def start_edit(item_id):
    item = find_item(item_id)
    if item is None:
        return
    # 이전 편집에서 남은 입력값이 보이지 않도록 현재 값으로 채운다.
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    st.session_state[f"edit_qty_{item_id}"] = item["quantity"]
    st.session_state["editing_id"] = item_id
    st.session_state["edit_error"] = False


def save_edit(item_id):
    name = st.session_state[f"edit_name_{item_id}"].strip()
    if not name:
        st.session_state["edit_error"] = True
        return
    update_item(item_id, name, st.session_state[f"edit_qty_{item_id}"])
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = False
    notify(f"'{name}'(으)로 수정했어요", "✏️")


def cancel_edit():
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = False


# ---------- 삭제 콜백 (알림 포함) ----------
def on_delete(item_id):
    item = find_item(item_id)
    delete_item(item_id)
    if item:
        notify(f"'{item['name']}'을(를) 삭제했어요", "🗑️")


def on_clear_checked():
    count = sum(1 for i in st.session_state["items"] if i["checked"])
    clear_checked()
    notify(f"완료 항목 {count}개를 삭제했어요", "🧹")


# ---------- 화면 도우미 ----------
def notify(message, icon):
    """다음 실행 때 st.toast로 보여줄 알림을 예약한다 (콜백·rerun 직후에도 사라지지 않게)."""
    st.session_state["toast"] = (message, icon)


def md_escape(text):
    """아이템 이름에 들어간 마크다운 기호가 서식으로 해석되지 않게 이스케이프한다."""
    return "".join("\\" + c if c in "\\`*_{}[]()#+-.!|~<>$:" else c for c in text)


# 좁은 화면에서도 목록·요약 행이 세로로 쪼개지지 않도록 가로 배치를 유지한다.
CSS = """
<style>
.st-key-summary [data-testid="stHorizontalBlock"],
.st-key-item_list [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; gap: 0.5rem; }
.st-key-summary [data-testid="stColumn"],
.st-key-item_list [data-testid="stColumn"] { min-width: 0 !important; }
/* Streamlit 기본값(margin-bottom:-1rem) 때문에 이름이 체크박스·아이콘보다 아래로 처지는 것을 막는다. */
.st-key-item_list [data-testid="stMarkdownContainer"] { margin-bottom: 0; }
.st-key-item_list [data-testid="stMarkdownContainer"] p { margin: 0; overflow-wrap: anywhere; }
</style>
"""


# ---------- 화면 ----------
st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")
init_state()
st.markdown(CSS, unsafe_allow_html=True)

if "toast" in st.session_state:
    message, icon = st.session_state.pop("toast")
    st.toast(message, icon=icon)

st.title("🛒 쇼핑리스트")

items = st.session_state["items"]

# [요약 영역] 전체 / 완료 / 남은 개수 + 진행률
total = len(items)
done = sum(1 for i in items if i["checked"])
with st.container(key="summary"):
    col_total, col_done, col_left = st.columns(3)
    col_total.metric("전체", f"{total}개")
    col_done.metric("완료", f"{done}개")
    col_left.metric("남은", f"{total - done}개")
    st.progress(done / total if total else 0.0, text=f"{round(done / total * 100) if total else 0}% 담음")

# [입력 폼 영역] 아이템 이름 + 수량 + 추가 버튼
with st.form("add_form", clear_on_submit=True, border=True):
    col_name, col_qty, col_btn = st.columns([6, 2, 2], vertical_alignment="bottom")
    new_name = col_name.text_input("아이템 이름", max_chars=60, placeholder="예: 우유")
    new_qty = col_qty.number_input("수량", min_value=1, max_value=99, value=1, step=1)
    submitted = col_btn.form_submit_button("추가", type="primary", width="stretch")

if submitted:
    if new_name.strip():
        add_item(new_name.strip(), new_qty)
        notify(f"'{new_name.strip()}'을(를) 추가했어요", "🛒")
        st.rerun()
    else:
        st.warning("아이템 이름을 입력해 주세요.", icon="⚠️")

# [목록 영역] 체크박스 / 이름 / 수량 / 수정 / 삭제
if not items:
    st.info("쇼핑리스트가 비어 있습니다. 위 입력창에 첫 아이템을 추가해 보세요.", icon="🛒")


def render_row(item):
    item_id = item["id"]

    if item_id == st.session_state["editing_id"]:
        # 편집 모드 행: 테두리 상자로 구분
        with st.container(border=True):
            col_name, col_qty, col_save, col_cancel = st.columns([5, 2, 1.5, 1.5], vertical_alignment="bottom")
            col_name.text_input("이름", key=f"edit_name_{item_id}", max_chars=60)
            col_qty.number_input("수량", key=f"edit_qty_{item_id}", min_value=1, max_value=99, step=1)
            col_save.button("저장", key=f"save_{item_id}", on_click=save_edit, args=(item_id,), type="primary", width="stretch")
            col_cancel.button("취소", key=f"cancel_{item_id}", on_click=cancel_edit, width="stretch")
            if st.session_state["edit_error"]:
                st.warning("이름은 비워둘 수 없어요.", icon="⚠️")
        return

    # 일반 행
    col_chk, col_name, col_qty, col_edit, col_del = st.columns([0.6, 6, 1.2, 0.8, 0.8], vertical_alignment="center")
    col_chk.checkbox(
        item["name"],
        value=item["checked"],
        key=f"chk_{item_id}",
        on_change=toggle_item,
        args=(item_id,),
        label_visibility="collapsed",
    )
    name = md_escape(item["name"])
    if item["checked"]:
        col_name.markdown(f":gray[~~{name}~~]")
        col_qty.markdown(f":gray[x{item['quantity']}]")
    else:
        col_name.markdown(name)
        col_qty.markdown(f"x{item['quantity']}")
    col_edit.button("✏️", key=f"edit_{item_id}", on_click=start_edit, args=(item_id,), type="tertiary", help="수정")
    col_del.button("🗑️", key=f"del_{item_id}", on_click=on_delete, args=(item_id,), type="tertiary", help="삭제")


if items:
    # 미완료 → 완료 순으로 보여준다. 표시만 정렬하고 원본 순서(st.session_state["items"])는 그대로 둔다.
    todo = [i for i in items if not i["checked"]]
    got = [i for i in items if i["checked"]]
    with st.container(border=True, key="item_list"):
        for item in todo:
            render_row(item)
        if todo and got:
            st.caption("장바구니에 담음")
        for item in got:
            render_row(item)

# [하단 버튼 영역] 완료 항목 모두 삭제
if items:
    st.button("완료 항목 모두 삭제", on_click=on_clear_checked, disabled=done == 0, icon="🧹")
