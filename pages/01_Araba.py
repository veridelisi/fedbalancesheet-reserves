import streamlit as st
import plotly.graph_objects as go
from copy import deepcopy

st.set_page_config(
    page_title="💰 Money Creation Game",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Syne', 'Segoe UI', sans-serif !important;
}
.block-container { padding-top: 0.5rem !important; padding-bottom: 1rem !important; }

.sb-metric {
    background: white;
    border: 0.5px solid rgba(0,0,0,0.12);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 7px;
}
.sb-metric-label { font-size: 10px; color: #6b6b6b; text-transform: uppercase; letter-spacing: 0.5px; }
.sb-metric-val   { font-size: 22px; font-weight: 700; color: #1a1a1a; margin-top: 1px; }
.sb-metric-delta { font-size: 11px; margin-top: 1px; }
.delta-pos { color: #1D9E75; }
.delta-neg { color: #D85A30; }
.delta-neu { color: #a0a0a0; }

.dots-row { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 4px; }
.dot-done   { width:12px;height:12px;border-radius:50%;background:#1D9E75;display:inline-block; }
.dot-active { width:12px;height:12px;border-radius:50%;background:#378ADD;outline:2px solid #B5D4F4;outline-offset:1px;display:inline-block; }
.dot-empty  { width:12px;height:12px;border-radius:50%;background:rgba(0,0,0,0.12);display:inline-block; }

.step-header-card {
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.step-badge {
    background: #E6F1FB; color: #185FA5;
    font-size: 10px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px;
    display: inline-block; margin-bottom: 6px;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.step-title { font-size: 17px; font-weight: 700; color: #1E1B4B; margin-bottom: 4px; }
.step-desc  { font-size: 13px; color: #4B5563; line-height: 1.6; }
.tag { display:inline-block; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; margin-top:7px; }
.tag-green { background:#EAF3DE; color:#3B6D11; }
.tag-red   { background:#FCEBEB; color:#A32D2D; }
.tag-blue  { background:#E6F1FB; color:#185FA5; }

.flow-strip {
    background: #f7f7f5;
    border: 0.5px solid rgba(0,0,0,0.10);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.flow-label { font-size: 10px; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px; }
.flow-row { display: flex; align-items: center; flex-wrap: wrap; row-gap: 8px; }
.flow-node { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.flow-circle {
    width: 46px; height: 46px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; border: 2px solid;
}
.flow-node-lbl { font-size: 9px; color: #6b6b6b; text-align: center; max-width: 54px; line-height: 1.3; }
.flow-arrow { display: flex; flex-direction: column; align-items: center; padding: 0 6px; }
.flow-amt  { font-size: 9px; color: #6b6b6b; font-weight: 700; }
.flow-line { height: 2px; width: 38px; background: rgba(0,0,0,0.2); position: relative; margin: 2px 0; }
.flow-line::after {
    content: ''; position: absolute; right: -5px; top: -4px;
    border-top: 5px solid transparent; border-bottom: 5px solid transparent;
    border-left: 7px solid rgba(0,0,0,0.2);
}
.flow-note { font-size: 9px; color: #a0a0a0; }

.bsheet { border: 0.5px solid rgba(0,0,0,0.12); border-radius: 8px; overflow: hidden; margin-bottom: 8px; }
.bsheet.active { border: 1.5px solid #378ADD; }
.bsheet-head {
    padding: 6px 10px; display: flex; align-items: center; justify-content: space-between;
    border-bottom: 0.5px solid rgba(0,0,0,0.08); background: #f7f7f5;
}
.bsheet-name { font-size: 12px; font-weight: 700; color: #1a1a1a; }
.bsheet-active-badge { font-size: 9px; background: #E6F1FB; color: #185FA5; padding: 1px 7px; border-radius: 10px; font-weight: 700; }
.bsheet-body { display: grid; grid-template-columns: 1fr 1fr; }
.bsheet-col { padding: 7px 9px; }
.bsheet-col-left { border-right: 0.5px solid rgba(0,0,0,0.08); }
.col-title-a { font-size: 9px; text-transform: uppercase; letter-spacing: 0.4px; color: #185FA5; font-weight: 700; margin-bottom: 4px; }
.col-title-l { font-size: 9px; text-transform: uppercase; letter-spacing: 0.4px; color: #A32D2D; font-weight: 700; margin-bottom: 4px; }
.bsheet-row { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6b6b6b; padding: 2px 0; gap: 4px; }
.bsheet-row .bval { font-weight: 700; color: #1a1a1a; white-space: nowrap; }
.bsheet-empty { padding: 14px; text-align: center; font-size: 11px; color: #a0a0a0; }
.bsheet-total { padding: 4px 9px; border-top: 0.5px solid rgba(0,0,0,0.08); display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; background: #f7f7f5; }
.t-a { color: #185FA5; }
.t-l { color: #A32D2D; }

.insight-bar { background: #EAF3DE; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #3B6D11; line-height: 1.6; margin: 4px 0 10px 0; }

.choice-prompt {
    background: #FFFBEB;
    border: 1px solid #FCD34D;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 12px;
}
.choice-prompt-label { font-size: 12px; font-weight: 700; color: #92400E; margin-bottom: 2px; }
.choice-prompt-sub   { font-size: 11px; color: #B45309; }

.chosen-pill {
    display: inline-block;
    background: #1E40AF;
    color: white;
    font-size: 13px;
    font-weight: 700;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 8px;
}

.complete-card { background: linear-gradient(135deg,#DCFCE7,#D1FAE5); border: 1px solid #86EFAC; border-radius: 14px; padding: 28px 32px; text-align: center; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ─── AMOUNT OPTION SETS ───────────────────────────────────────────────────────
LOAN_OPTS     = [100, 200, 300, 400]
RESERVE_OPTS  = [100, 200, 300, 400]
TRANSFER_OPTS = [20, 25, 30, 50]
CASH_OPTS     = [10, 20, 30, 40]
REPAY_OPTS    = [5, 10, 15, 20]

# ─── SCENARIOS ────────────────────────────────────────────────────────────────
# Each scenario: choice_type, choice_opts, choice_label, and tx/flow builders
SCENARIOS = [
    {
        "id": 1, "emoji": "✨",
        "title": "Bank X Creates Money — From Nothing!",
        "short": "Bank X grants Customer A a loan, writing new money into existence.",
        "insight": "Banks don't lend existing money — they create brand new money when they make loans. This is called endogenous money creation. The economy grew from $0 with a single bookkeeping entry.",
        "tag": "💚 Money Created", "tag_type": "green",
        "choice_type": "loan",
        "choice_opts": LOAN_OPTS,
        "choice_label": "How much does Bank X loan to Customer A?",
        "involved": ["Xbank", "CustomerA"],
    },
    {
        "id": 2, "emoji": "🏛️",
        "title": "Central Bank Provides Reserves",
        "short": "The Central Bank lends reserves to Bank X and Bank Y.",
        "insight": "Reserves are the settlement currency between banks — they live only inside the Central Bank's ledger and never enter the public money supply (M1). Banks need reserves to settle payments with each other.",
        "tag": "➡️ No Change in M1", "tag_type": "blue",
        "choice_type": "reserve",
        "choice_opts": RESERVE_OPTS,
        "choice_label": "How much in reserves does the Central Bank provide to each bank?",
        "involved": ["Xbank", "Ybank", "CentralBank"],
    },
    {
        "id": 3, "emoji": "💳",
        "title": "Bank Y Creates a Loan for Customer C",
        "short": "Bank Y grants Customer C a loan — more new money!",
        "insight": "Every bank creates money independently. Money supply doubled again — and we haven't moved a single coin or bill. Pure accounting.",
        "tag": "💚 Money Created", "tag_type": "green",
        "choice_type": "loan",
        "choice_opts": LOAN_OPTS,
        "choice_label": "How much does Bank Y loan to Customer C?",
        "involved": ["Ybank", "CustomerC"],
    },
    {
        "id": 4, "emoji": "💳",
        "title": "Bank X Creates a Loan for Customer B",
        "short": "Bank X grants Customer B a loan — another money-creation event!",
        "insight": "Bank X didn't need Customer A's deposit to fund this loan. Banks are not intermediaries that move existing savings — they manufacture new purchasing power.",
        "tag": "💚 Money Created", "tag_type": "green",
        "choice_type": "loan",
        "choice_opts": LOAN_OPTS,
        "choice_label": "How much does Bank X loan to Customer B?",
        "involved": ["Xbank", "CustomerB"],
    },
    {
        "id": 5, "emoji": "📉",
        "title": "Customer B Repays Part of the Loan",
        "short": "Customer B repays part of the loan to Bank X — destroying money!",
        "insight": "Just as loans create money, loan repayments destroy it. The money simply disappears from the balance sheet. This is debt deflation in miniature.",
        "tag": "🔴 Money Destroyed", "tag_type": "red",
        "choice_type": "repay",
        "choice_opts": REPAY_OPTS,
        "choice_label": "How much (in $) does Customer B repay to Bank X?",
        "involved": ["Xbank", "CustomerB"],
    },
    {
        "id": 6, "emoji": "💸",
        "title": "Customer A Pays Customer B (Same Bank)",
        "short": "Customer A sends money to Customer B — both bank at Bank X.",
        "insight": "Same-bank payments are pure bookkeeping. No reserves move. Bank X acts as an internal clearing house. Money supply stays the same — money just changed hands.",
        "tag": "➡️ Transfer Only", "tag_type": "blue",
        "choice_type": "transfer",
        "choice_opts": TRANSFER_OPTS,
        "choice_label": "How much does Customer A send to Customer B?",
        "involved": ["Xbank", "CustomerA", "CustomerB"],
    },
    {
        "id": 7, "emoji": "🔄",
        "title": "Customer C Pays Customer A (Cross-Bank!)",
        "short": "Customer C (Bank Y) sends money to Customer A (Bank X) — reserves must move!",
        "insight": "Cross-bank payments require reserve transfers. A Bank Y deposit can't move to Bank X's ledger — only central bank reserves cross banks. This is why reserves matter.",
        "tag": "➡️ Transfer Only", "tag_type": "blue",
        "choice_type": "transfer",
        "choice_opts": TRANSFER_OPTS,
        "choice_label": "How much does Customer C send to Customer A?",
        "involved": ["Xbank", "Ybank", "CustomerA", "CustomerC"],
    },
    {
        "id": 8, "emoji": "💵",
        "title": "Banks Withdraw Physical Cash",
        "short": "Each bank converts some reserves into physical cash.",
        "insight": "Cash and reserves are both central bank money — just different formats. Banks get physical cash to hand to customers at ATMs. Total money supply doesn't change.",
        "tag": "➡️ Form Change Only", "tag_type": "blue",
        "choice_type": "cash",
        "choice_opts": CASH_OPTS,
        "choice_label": "How much cash does each bank withdraw from reserves?",
        "involved": ["Xbank", "Ybank", "CentralBank"],
    },
    {
        "id": 9, "emoji": "🏧",
        "title": "Customer A Withdraws Cash",
        "short": "Customer A takes out physical cash from Bank X.",
        "insight": "This converts bank money into central bank money — but total M1 stays the same. Bank X needed physical cash on hand (from Step 8) to do this. It's a format swap, not money creation.",
        "tag": "➡️ Form Change Only", "tag_type": "blue",
        "choice_type": "cash",
        "choice_opts": CASH_OPTS,
        "choice_label": "How much cash does Customer A withdraw?",
        "involved": ["Xbank", "CustomerA"],
    },
    {
        "id": 10, "emoji": "🎓",
        "title": "Full System Review",
        "short": "The complete monetary system — summarized!",
        "insight": "Banks create money through loans, repayments destroy it, reserves settle inter-bank payments, and cash is just a format change. Your choices shaped the final money supply.",
        "tag": "🎓 Complete!", "tag_type": "green",
        "choice_type": "none",
        "choice_opts": [],
        "choice_label": "",
        "involved": [],
    },
]

# ─── TRANSACTION BUILDERS ──────────────────────────────────────────────────────
def build_transactions(sc_id, amt):
    if sc_id == 1:
        return [("Xbank","debit","Credits",amt),("Xbank","credit","CustomerADep",amt),
                ("CustomerA","debit","Deposits",amt),("CustomerA","credit","Credits",amt)]
    elif sc_id == 2:
        return [("Xbank","debit","Reserves",amt),("Xbank","credit","DueCB",amt),
                ("Ybank","debit","Reserves",amt),("Ybank","credit","DueCB",amt),
                ("CentralBank","debit","CreditsToBanks",amt*2),("CentralBank","credit","Reserves",amt*2)]
    elif sc_id == 3:
        return [("Ybank","debit","Credits",amt),("Ybank","credit","CustomerCDep",amt),
                ("CustomerC","debit","Deposits",amt),("CustomerC","credit","Credits",amt)]
    elif sc_id == 4:
        return [("Xbank","debit","Credits",amt),("Xbank","credit","CustomerBDep",amt),
                ("CustomerB","debit","Deposits",amt),("CustomerB","credit","Credits",amt)]
    elif sc_id == 5:
        return [("Xbank","debit","CustomerBDep",amt),("Xbank","credit","Credits",amt),
                ("CustomerB","debit","Credits",amt),("CustomerB","credit","Deposits",amt)]
    elif sc_id == 6:
        return [("Xbank","debit","CustomerADep",amt),("Xbank","credit","CustomerBDep",amt),
                ("CustomerA","debit","NetWorth",amt),("CustomerA","credit","Deposits",amt),
                ("CustomerB","debit","Deposits",amt),("CustomerB","credit","NetWorth",amt)]
    elif sc_id == 7:
        return [("Xbank","debit","Reserves",amt),("Xbank","credit","CustomerADep",amt),
                ("Ybank","debit","CustomerCDep",amt),("Ybank","credit","Reserves",amt),
                ("CustomerA","debit","Deposits",amt),("CustomerA","credit","NetWorth",amt),
                ("CustomerC","debit","NetWorth",amt),("CustomerC","credit","Deposits",amt)]
    elif sc_id == 8:
        return [("Xbank","debit","Cash",amt),("Xbank","credit","Reserves",amt),
                ("Ybank","debit","Cash",amt),("Ybank","credit","Reserves",amt),
                ("CentralBank","debit","Reserves",amt*2),("CentralBank","credit","Cash",amt*2)]
    elif sc_id == 9:
        return [("Xbank","debit","CustomerADep",amt),("Xbank","credit","Cash",amt),
                ("CustomerA","debit","Cash",amt),("CustomerA","credit","Deposits",amt)]
    return []

def build_flow(sc_id, amt):
    a = f"${amt}"
    if sc_id == 1:
        return [
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":f"{a} loan","note":"creates ↗"},
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
        ]
    elif sc_id == 2:
        return [
            {"id":"CentralBank","label":"Central Bank","abbr":"CB","bg":"#E1F5EE","border":"#1D9E75","color":"#0F6E56"},
            {"arrow":True,"amt":f"{a} each","note":"reserves"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":a,"note":"reserves"},
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
        ]
    elif sc_id == 3:
        return [
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
            {"arrow":True,"amt":f"{a} loan","note":"creates ↗"},
            {"id":"CustomerC","label":"Customer C","abbr":"CC","bg":"#FBEAF0","border":"#D4537E","color":"#72243E"},
        ]
    elif sc_id == 4:
        return [
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":f"{a} loan","note":"creates ↗"},
            {"id":"CustomerB","label":"Customer B","abbr":"CB","bg":"#FCEBEB","border":"#D85A30","color":"#993C1D"},
        ]
    elif sc_id == 5:
        return [
            {"id":"CustomerB","label":"Customer B","abbr":"CB","bg":"#FCEBEB","border":"#D85A30","color":"#993C1D"},
            {"arrow":True,"amt":f"{a} repay","note":"destroys ↘"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
        ]
    elif sc_id == 6:
        return [
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
            {"arrow":True,"amt":a,"note":"via Bank X"},
            {"id":"CustomerB","label":"Customer B","abbr":"CB","bg":"#FCEBEB","border":"#D85A30","color":"#993C1D"},
        ]
    elif sc_id == 7:
        return [
            {"id":"CustomerC","label":"Customer C","abbr":"CC","bg":"#FBEAF0","border":"#D4537E","color":"#72243E"},
            {"arrow":True,"amt":f"{a} deposit","note":"Bank Y"},
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
            {"arrow":True,"amt":f"{a} reserves","note":"settles"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":f"{a} deposit","note":"Bank X"},
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
        ]
    elif sc_id == 8:
        return [
            {"id":"CentralBank","label":"Central Bank","abbr":"CB","bg":"#E1F5EE","border":"#1D9E75","color":"#0F6E56"},
            {"arrow":True,"amt":f"{a} each","note":"cash"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":a,"note":""},
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
        ]
    elif sc_id == 9:
        return [
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
            {"arrow":True,"amt":f"{a} withdrawal","note":"format swap"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
        ]
    return []

# ─── ENGINE ───────────────────────────────────────────────────────────────────
ENTITY_DEFS = {
    "Xbank":       {"label":"Bank X",       "assets":{"Cash":0,"Reserves":0,"Credits":0},     "liabilities":{"CustomerADep":0,"CustomerBDep":0,"DueCB":0}},
    "Ybank":       {"label":"Bank Y",       "assets":{"Cash":0,"Reserves":0,"Credits":0},     "liabilities":{"CustomerCDep":0,"DueCB":0}},
    "CentralBank": {"label":"Central Bank", "assets":{"CreditsToBanks":0},                    "liabilities":{"Reserves":0,"Cash":0}},
    "CustomerA":   {"label":"Customer A",   "assets":{"Cash":0,"Deposits":0},                 "liabilities":{"Credits":0,"NetWorth":0}},
    "CustomerB":   {"label":"Customer B",   "assets":{"Deposits":0},                          "liabilities":{"Credits":0,"NetWorth":0}},
    "CustomerC":   {"label":"Customer C",   "assets":{"Deposits":0},                          "liabilities":{"Credits":0,"NetWorth":0}},
}
ENTITY_ORDER = ["Xbank","Ybank","CentralBank","CustomerA","CustomerB","CustomerC"]
FRIENDLY = {
    "CustomerADep":"Cust A Dep","CustomerBDep":"Cust B Dep","CustomerCDep":"Cust C Dep",
    "DueCB":"Due to CB","CreditsToBanks":"Credits→Banks","NetWorth":"Net Worth"
}
def fname(k): return FRIENDLY.get(k, k)

def init_state():
    return {k: {"assets": dict(v["assets"]), "liabilities": dict(v["liabilities"])} for k, v in ENTITY_DEFS.items()}

def apply_tx(state, txs):
    s = deepcopy(state)
    for entity, side, account, amount in txs:
        e = s[entity]
        if side == "debit":
            if account in e["assets"]:        e["assets"][account]      += amount
            elif account in e["liabilities"]: e["liabilities"][account] -= amount
        else:
            if account in e["assets"]:        e["assets"][account]      -= amount
            elif account in e["liabilities"]: e["liabilities"][account] += amount
    return s

def compute_ms(state):
    bank = (state["Xbank"]["liabilities"].get("CustomerADep",0)
          + state["Xbank"]["liabilities"].get("CustomerBDep",0)
          + state["Ybank"]["liabilities"].get("CustomerCDep",0))
    cash = sum(state[e]["assets"].get("Cash",0) for e in ["CustomerA","CustomerB","CustomerC"])
    return bank, cash, bank + cash

# ─── SESSION STATE INIT ───────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 0
if "ledger" not in st.session_state:
    st.session_state.ledger = init_state()
if "ms_history" not in st.session_state:
    bm, cm, tot = compute_ms(init_state())
    st.session_state.ms_history = [{"label":"Start","bank":bm,"cash":cm,"total":tot}]
if "chosen" not in st.session_state:
    st.session_state.chosen = {}       # step_index -> chosen amount
if "confirmed" not in st.session_state:
    st.session_state.confirmed = set() # set of confirmed step indices

# ─── RENDER HELPERS ───────────────────────────────────────────────────────────
def dots_html(current, total=10):
    parts = []
    for i in range(total):
        cls = "dot-done" if i < current else ("dot-active" if i == current else "dot-empty")
        parts.append(f'<span class="{cls}" title="Step {i+1}"></span>')
    return f'<div class="dots-row">{"".join(parts)}</div>'

def flow_html(nodes):
    if not nodes:
        return '<div style="font-size:12px;color:#a0a0a0;padding:4px 0;">All steps complete — full system simulated.</div>'
    parts = []
    for n in nodes:
        if n.get("id"):
            parts.append(
                f'<div class="flow-node">'
                f'<div class="flow-circle" style="background:{n["bg"]};border-color:{n["border"]};color:{n["color"]};">{n["abbr"]}</div>'
                f'<div class="flow-node-lbl">{n["label"]}</div>'
                f'</div>'
            )
        elif n.get("arrow"):
            parts.append(
                f'<div class="flow-arrow">'
                f'<div class="flow-amt">{n["amt"]}</div>'
                f'<div class="flow-line"></div>'
                f'<div class="flow-note">{n.get("note","")}</div>'
                f'</div>'
            )
    return f'<div class="flow-row">{"".join(parts)}</div>'

def bsheet_html(ek, state, active):
    e = state[ek]
    label = ENTITY_DEFS[ek]["label"]
    assets = [(k,v) for k,v in e["assets"].items() if v != 0]
    liabs  = [(k,v) for k,v in e["liabilities"].items() if v != 0]
    ta = sum(v for _,v in assets)
    tl = sum(v for _,v in liabs)
    if ta == 0 and tl == 0:
        return (f'<div class="bsheet"><div class="bsheet-head">'
                f'<span class="bsheet-name" style="color:#a0a0a0;">{label}</span></div>'
                f'<div class="bsheet-empty">empty</div></div>')
    badge = '<span class="bsheet-active-badge">active</span>' if active else ""
    acls  = " active" if active else ""
    ar = "".join(
        f'<div class="bsheet-row"><span>{fname(k)}</span><span class="bval">${v}</span></div>'
        for k,v in assets
    ) or '<div class="bsheet-row" style="color:#ccc;font-size:10px;">—</div>'
    lr = ""
    for k, v in liabs:
        val_str = f"-${abs(v)}" if v < 0 else f"${v}"
        lr += f'<div class="bsheet-row"><span>{fname(k)}</span><span class="bval">{val_str}</span></div>'
    if not lr:
        lr = '<div class="bsheet-row" style="color:#ccc;font-size:10px;">—</div>'
    tl_str = f"-${abs(tl)}" if tl < 0 else f"${tl}"
    return (
        f'<div class="bsheet{acls}">'
        f'<div class="bsheet-head"><span class="bsheet-name">{label}</span>{badge}</div>'
        f'<div class="bsheet-body">'
        f'<div class="bsheet-col bsheet-col-left"><div class="col-title-a">Assets</div>{ar}</div>'
        f'<div class="bsheet-col"><div class="col-title-l">Liabilities</div>{lr}</div>'
        f'</div>'
        f'<div class="bsheet-total"><span class="t-a">${ta}</span><span class="t-l">{tl_str}</span></div>'
        f'</div>'
    )

def ms_chart(history, height=240):
    labels = [d["label"] for d in history]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=[d["bank"] for d in history],
                         name="Bank Deposits", marker_color="#85B7EB"))
    fig.add_trace(go.Bar(x=labels, y=[d["cash"] for d in history],
                         name="Cash in Circulation", marker_color="#C084FC"))
    fig.add_trace(go.Scatter(x=labels, y=[d["total"] for d in history],
                             name="Total M1", mode="lines+markers",
                             line=dict(color="#EF9F27", width=3, shape="spline"),
                             marker=dict(size=8, color="#EF9F27", line=dict(width=2, color="white"))))
    if history:
        last = history[-1]
        fig.add_annotation(x=last["label"], y=last["total"],
                           text=f"<b>${last['total']}</b>", showarrow=True,
                           arrowhead=2, arrowcolor="#EF9F27", ax=0, ay=-36,
                           font=dict(size=13, color="#D97706"),
                           bgcolor="white", bordercolor="#EF9F27", borderwidth=1.5, borderpad=4)
    fig.update_layout(
        barmode="stack", height=height,
        margin=dict(t=30, b=20, l=40, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        xaxis=dict(showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10)),
    )
    return fig

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    step_i = st.session_state.step
    sc = SCENARIOS[min(step_i, len(SCENARIOS)-1)]

    # Progress
    st.markdown(f'<div class="sb-metric"><div class="sb-metric-label">Progress</div>'
                f'<div class="sb-metric-val">Step {step_i+1} / {len(SCENARIOS)}</div>'
                f'{dots_html(step_i)}</div>', unsafe_allow_html=True)

    # M1
    bm, cm, tot = compute_ms(st.session_state.ledger)
    prev_tot = st.session_state.ms_history[-2]["total"] if len(st.session_state.ms_history) > 1 else 0
    delta = tot - prev_tot
    if delta > 0:
        delta_html = f'<div class="sb-metric-delta delta-pos">▲ +${delta} this step</div>'
    elif delta < 0:
        delta_html = f'<div class="sb-metric-delta delta-neg">▼ −${abs(delta)} this step</div>'
    else:
        delta_html = f'<div class="sb-metric-delta delta-neu">→ No change this step</div>'

    st.markdown(
        f'<div class="sb-metric">'
        f'<div class="sb-metric-label">Money Supply (M1)</div>'
        f'<div class="sb-metric-val">${tot}</div>'
        f'{delta_html}'
        f'<div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;background:#EEF6FF;border-radius:6px;padding:5px 8px;">'
        f'<span style="font-size:10px;color:#3B6D9E;">🏦 Bank Deposits</span>'
        f'<span style="font-size:13px;font-weight:800;color:#185FA5;">${bm}</span></div>'
        f'<div style="margin-top:4px;display:flex;justify-content:space-between;align-items:center;background:#F5F0FF;border-radius:6px;padding:5px 8px;">'
        f'<span style="font-size:10px;color:#7C3AED;">💵 Cash in Circ.</span>'
        f'<span style="font-size:13px;font-weight:800;color:#6D28D9;">${cm}</span></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Balance sheets
    st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:#a0a0a0;margin:8px 0 4px 0;">Balance Sheets</div>', unsafe_allow_html=True)
    active_entities = sc["involved"] if step_i in st.session_state.confirmed else []
    for ek in ENTITY_ORDER:
        st.markdown(bsheet_html(ek, st.session_state.ledger, ek in active_entities), unsafe_allow_html=True)

    st.markdown("---")
    if st.button("↺ Restart", use_container_width=True):
        for key in ["step","ledger","ms_history","chosen","confirmed"]:
            del st.session_state[key]
        st.rerun()
    st.markdown(
        '<div style="margin-top:auto;padding-top:24px;">'
        '<div style="background:#F0F4FF;border-radius:10px;padding:12px 14px;">'
        '<div style="font-size:10px;color:#4B5563;line-height:1.7;margin-bottom:8px;">'
        'If you study or work with money, you need a framework grounded in how money actually works.<br><br>'
        
        '</div>'
        '<a href="https://www.amazon.com/Modern-Monetary-System-Theory-Practice/dp/B0G584KJ73" '
        'target="_blank" style="color:#1E40AF;text-decoration:underline;font-weight:700;">'
        '📘 Modern Monetary System in Theory and Practice: Who Creates Money?</a>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )
# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────
step_i = st.session_state.step
sc     = SCENARIOS[min(step_i, len(SCENARIOS)-1)]

# ── Complete screen ──
if step_i >= len(SCENARIOS):
    st.markdown(
        '<div class="complete-card">'
        '<div style="font-size:48px;margin-bottom:8px;">🎓</div>'
        '<div style="font-size:22px;font-weight:800;color:#065F46;margin-bottom:6px;">Simulation Complete!</div>'
        '<div style="font-size:14px;color:#047857;line-height:1.6;">'
        'You navigated the entire monetary system. Your choices shaped the final money supply.'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )
    bm, cm, tot = compute_ms(st.session_state.ledger)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Final M1", f"${tot}")
    with c2:
        st.metric("Bank Deposits", f"${bm}")
    with c3:
        st.metric("Cash in Circ.", f"${cm}")

    # Journey summary
    st.markdown("### 📊 Your Money Supply Journey")
    st.plotly_chart(ms_chart(st.session_state.ms_history, height=300), use_container_width=True)

    # Choices recap
    st.markdown("### 🎯 Your Choices")
    cols = st.columns(5)
    for i, sc_item in enumerate(SCENARIOS[:9]):
        with cols[i % 5]:
            amt = st.session_state.chosen.get(i, "—")
            st.markdown(
                f'<div style="background:#f7f7f5;border:0.5px solid rgba(0,0,0,0.1);border-radius:8px;padding:10px;text-align:center;">'
                f'<div style="font-size:20px;">{sc_item["emoji"]}</div>'
                f'<div style="font-size:10px;color:#6b6b6b;margin:3px 0;">Step {sc_item["id"]}</div>'
                f'<div style="font-size:16px;font-weight:800;color:#1a1a1a;">${amt}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    if st.button("↺ Play Again", type="primary", use_container_width=True):
        for key in ["step","ledger","ms_history","chosen","confirmed"]:
            del st.session_state[key]
        st.rerun()
    st.stop()

# ── Step header ──
tag_cls = {"green":"tag-green","red":"tag-red","blue":"tag-blue"}[sc["tag_type"]]
st.markdown(
    f'<div class="step-header-card">'
    f'<span class="step-badge">Step {sc["id"]} of {len(SCENARIOS)}</span>'
    f'<div class="step-title">{sc["emoji"]} {sc["title"]}</div>'
    f'<div class="step-desc">{sc["short"]}</div>'
    f'<span class="tag {tag_cls}">{sc["tag"]}</span>'
    f'</div>',
    unsafe_allow_html=True
)

col_main, col_chart = st.columns([3, 2])

with col_main:
    # ── Choice Section ──
    if sc["choice_type"] != "none":
        already_confirmed = step_i in st.session_state.confirmed
        already_chosen    = step_i in st.session_state.chosen

        if not already_confirmed:
            # Show choice prompt
            st.markdown(
                f'<div class="choice-prompt">'
                f'<div class="choice-prompt-label">🎯 Make Your Choice</div>'
                f'<div class="choice-prompt-sub">{sc["choice_label"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            btn_cols = st.columns(len(sc["choice_opts"]))
            for idx, opt in enumerate(sc["choice_opts"]):
                with btn_cols[idx]:
                    is_selected = st.session_state.chosen.get(step_i) == opt
                    if st.button(
                        f"${opt}",
                        key=f"opt_{step_i}_{opt}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True
                    ):
                        st.session_state.chosen[step_i] = opt
                        st.rerun()

            # Confirm button
            chosen_amt = st.session_state.chosen.get(step_i)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if chosen_amt is not None:
                if st.button(f"✓ Confirm ${chosen_amt} and Apply Transaction", type="primary", use_container_width=True):
                    txs = build_transactions(sc["id"], chosen_amt)
                    new_ledger = apply_tx(st.session_state.ledger, txs)
                    st.session_state.ledger = new_ledger
                    bm, cm, tot = compute_ms(new_ledger)
                    st.session_state.ms_history.append({
                        "label": f"Step {sc['id']}", "bank": bm, "cash": cm, "total": tot
                    })
                    st.session_state.confirmed.add(step_i)
                    st.rerun()
            else:
                st.markdown(
                    '<div style="text-align:center;color:#9CA3AF;font-size:12px;padding:8px 0;">👆 Pick an amount above to continue</div>',
                    unsafe_allow_html=True
                )

        else:
            # Already confirmed — show chosen amount + flow + insight
            chosen_amt = st.session_state.chosen[step_i]
            st.markdown(f'<span class="chosen-pill">✓ You chose: ${chosen_amt}</span>', unsafe_allow_html=True)

            flow_nodes = build_flow(sc["id"], chosen_amt)
            st.markdown(
                f'<div class="flow-strip">'
                f'<div class="flow-label">Transaction Flow</div>'
                f'{flow_html(flow_nodes)}'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown(f'<div class="insight-bar">💡 {sc["insight"]}</div>', unsafe_allow_html=True)

    else:
        # Step 10: review only
        st.markdown(f'<div class="insight-bar">💡 {sc["insight"]}</div>', unsafe_allow_html=True)
        st.session_state.confirmed.add(step_i)

    # ── Navigation ──
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("← Back", use_container_width=True, disabled=(step_i == 0)):
            st.session_state.step = max(0, step_i - 1)
            st.rerun()
    with nav2:
        can_advance = (step_i in st.session_state.confirmed)
        label = "Finish 🎓" if step_i == len(SCENARIOS) - 1 else "Next Step →"
        if st.button(label, use_container_width=True, disabled=(not can_advance), type="primary"):
            st.session_state.step = step_i + 1
            st.rerun()

with col_chart:
    if len(st.session_state.ms_history) > 1:
        st.plotly_chart(ms_chart(st.session_state.ms_history), use_container_width=True)
    else:
        st.markdown(
            '<div style="background:#f7f7f5;border:0.5px solid rgba(0,0,0,0.10);border-radius:10px;padding:40px;text-align:center;">'
            '<div style="font-size:24px;">📊</div>'
            '<div style="font-size:12px;color:#a0a0a0;margin-top:6px;">Money supply chart appears<br>as you complete steps</div>'
            '</div>',
            unsafe_allow_html=True
        )
