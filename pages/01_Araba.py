import streamlit as st
import plotly.graph_objects as go
from copy import deepcopy

st.set_page_config(
    page_title="💰 Money Creation Game",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------------- STOP Expanded -----------------

st.markdown(

    """

<style>

    [data-testid="stSidebarNav"] {display: none;}

    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}

</style>

""",

    unsafe_allow_html=True,

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

.complete-card { background: linear-gradient(135deg,#DCFCE7,#D1FAE5); border: 1px solid #86EFAC; border-radius: 14px; padding: 28px 32px; text-align: center; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ─── SCENARIOS ────────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "id": 1, "emoji": "✨",
        "title": "Bank X Creates Money — From Nothing!",
        "short": "Bank X grants Customer A a $100 loan, writing new money into existence.",
        "insight": "Banks don't lend existing money — they create brand new money when they make loans. This is called endogenous money creation. The economy went from $0 to $100 with a single bookkeeping entry.",
        "tag": "💚 Money Created", "tag_type": "green",
        "transactions": [("Xbank","debit","Credits",100),("Xbank","credit","CustomerADep",100),("CustomerA","debit","Deposits",100),("CustomerA","credit","Credits",100)],
        "flow": [
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":"$100 loan","note":"creates ↗"},
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
        ],
        "involved": ["Xbank","CustomerA"],
    },
    {
        "id": 2, "emoji": "🏛️",
        "title": "Central Bank Provides Reserves",
        "short": "The Central Bank lends $100 in reserves to Bank X and Bank Y.",
        "insight": "Reserves are the settlement currency between banks — they live only inside the Central Bank's ledger and never enter the public money supply (M1). Banks need reserves to settle payments with each other.",
        "tag": "➡️ No Change in M1", "tag_type": "blue",
        "transactions": [("Xbank","debit","Reserves",100),("Xbank","credit","DueCB",100),("Ybank","debit","Reserves",100),("Ybank","credit","DueCB",100),("CentralBank","debit","CreditsToBanks",200),("CentralBank","credit","Reserves",200)],
        "flow": [
            {"id":"CentralBank","label":"Central Bank","abbr":"CB","bg":"#E1F5EE","border":"#1D9E75","color":"#0F6E56"},
            {"arrow":True,"amt":"$100 each","note":"reserves"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":"$100","note":"reserves"},
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
        ],
        "involved": ["Xbank","Ybank","CentralBank"],
    },
    {
        "id": 3, "emoji": "💳",
        "title": "Bank Y Creates a Loan for Customer C",
        "short": "Bank Y grants Customer C a $100 loan — more new money!",
        "insight": "Every bank creates money independently. Money supply is now $200 — double what it was — and we haven't moved a single coin or bill. Pure accounting.",
        "tag": "💚 Money Created", "tag_type": "green",
        "transactions": [("Ybank","debit","Credits",100),("Ybank","credit","CustomerCDep",100),("CustomerC","debit","Deposits",100),("CustomerC","credit","Credits",100)],
        "flow": [
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
            {"arrow":True,"amt":"$100 loan","note":"creates ↗"},
            {"id":"CustomerC","label":"Customer C","abbr":"CC","bg":"#FBEAF0","border":"#D4537E","color":"#72243E"},
        ],
        "involved": ["Ybank","CustomerC"],
    },
    {
        "id": 4, "emoji": "💳",
        "title": "Bank X Creates a Loan for Customer B",
        "short": "Bank X grants Customer B a $100 loan — the third money-creation event!",
        "insight": "Bank X didn't need Customer A's deposit to fund this loan. Banks are not intermediaries that move existing savings — they manufacture new purchasing power. Money supply is now $300.",
        "tag": "💚 Money Created", "tag_type": "green",
        "transactions": [("Xbank","debit","Credits",100),("Xbank","credit","CustomerBDep",100),("CustomerB","debit","Deposits",100),("CustomerB","credit","Credits",100)],
        "flow": [
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":"$100 loan","note":"creates ↗"},
            {"id":"CustomerB","label":"Customer B","abbr":"CB","bg":"#FCEBEB","border":"#D85A30","color":"#993C1D"},
        ],
        "involved": ["Xbank","CustomerB"],
    },
    {
        "id": 5, "emoji": "📉",
        "title": "Customer B Repays Part of the Loan",
        "short": "Customer B repays $70 to Bank X — destroying money!",
        "insight": "Just as loans create money, loan repayments destroy it. The money simply disappears from the balance sheet. Money supply drops $300 → $230. This is debt deflation in miniature.",
        "tag": "🔴 Money Destroyed", "tag_type": "red",
        "transactions": [("Xbank","debit","CustomerBDep",70),("Xbank","credit","Credits",70),("CustomerB","debit","Credits",70),("CustomerB","credit","Deposits",70)],
        "flow": [
            {"id":"CustomerB","label":"Customer B","abbr":"CB","bg":"#FCEBEB","border":"#D85A30","color":"#993C1D"},
            {"arrow":True,"amt":"$70 repay","note":"destroys ↘"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
        ],
        "involved": ["Xbank","CustomerB"],
    },
    {
        "id": 6, "emoji": "💸",
        "title": "Customer A Pays Customer B (Same Bank)",
        "short": "Customer A sends $50 to Customer B — both bank at Bank X.",
        "insight": "Same-bank payments are pure bookkeeping. No reserves move. Bank X acts as an internal clearing house. Money supply stays at $230 — money just changed hands.",
        "tag": "➡️ Transfer Only", "tag_type": "blue",
        "transactions": [("Xbank","debit","CustomerADep",50),("Xbank","credit","CustomerBDep",50),("CustomerA","debit","NetWorth",50),("CustomerA","credit","Deposits",50),("CustomerB","debit","Deposits",50),("CustomerB","credit","NetWorth",50)],
        "flow": [
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
            {"arrow":True,"amt":"$50","note":"via Bank X"},
            {"id":"CustomerB","label":"Customer B","abbr":"CB","bg":"#FCEBEB","border":"#D85A30","color":"#993C1D"},
        ],
        "involved": ["Xbank","CustomerA","CustomerB"],
    },
    {
        "id": 7, "emoji": "🔄",
        "title": "Customer C Pays Customer A (Cross-Bank!)",
        "short": "Customer C (Bank Y) sends $50 to Customer A (Bank X) — reserves must move!",
        "insight": "Cross-bank payments require reserve transfers. A Bank Y deposit can't move to Bank X's ledger — only central bank reserves cross banks. This is why Step 2 mattered.",
        "tag": "➡️ Transfer Only", "tag_type": "blue",
        "transactions": [("Xbank","debit","Reserves",50),("Xbank","credit","CustomerADep",50),("Ybank","debit","CustomerCDep",50),("Ybank","credit","Reserves",50),("CustomerA","debit","Deposits",50),("CustomerA","credit","NetWorth",50),("CustomerC","debit","NetWorth",50),("CustomerC","credit","Deposits",50)],
        "flow": [
            {"id":"CustomerC","label":"Customer C","abbr":"CC","bg":"#FBEAF0","border":"#D4537E","color":"#72243E"},
            {"arrow":True,"amt":"$50 deposit","note":"Bank Y"},
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
            {"arrow":True,"amt":"$50 reserves","note":"settles"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":"$50 deposit","note":"Bank X"},
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
        ],
        "involved": ["Xbank","Ybank","CustomerA","CustomerC"],
    },
    {
        "id": 8, "emoji": "💵",
        "title": "Banks Withdraw Physical Cash",
        "short": "Each bank converts $20 of reserves into physical cash.",
        "insight": "Cash and reserves are both central bank money — just different formats of the same thing. Banks get physical cash to hand to customers at ATMs. Total money supply doesn't change.",
        "tag": "➡️ Form Change Only", "tag_type": "blue",
        "transactions": [("Xbank","debit","Cash",20),("Xbank","credit","Reserves",20),("Ybank","debit","Cash",20),("Ybank","credit","Reserves",20),("CentralBank","debit","Reserves",40),("CentralBank","credit","Cash",40)],
        "flow": [
            {"id":"CentralBank","label":"Central Bank","abbr":"CB","bg":"#E1F5EE","border":"#1D9E75","color":"#0F6E56"},
            {"arrow":True,"amt":"$20 each","note":"cash"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
            {"arrow":True,"amt":"$20","note":""},
            {"id":"Ybank","label":"Bank Y","abbr":"BY","bg":"#EAF3DE","border":"#1D9E75","color":"#3B6D11"},
        ],
        "involved": ["Xbank","Ybank","CentralBank"],
    },
    {
        "id": 9, "emoji": "🏧",
        "title": "Customer A Withdraws Cash",
        "short": "Customer A takes out $20 in physical cash from Bank X.",
        "insight": "This converts bank money into central bank money — but total M1 stays at $230. Bank X needed physical cash on hand (from Step 8) to do this. It's a format swap, not money creation.",
        "tag": "➡️ Form Change Only", "tag_type": "blue",
        "transactions": [("Xbank","debit","CustomerADep",20),("Xbank","credit","Cash",20),("CustomerA","debit","Cash",20),("CustomerA","credit","Deposits",20)],
        "flow": [
            {"id":"CustomerA","label":"Customer A","abbr":"CA","bg":"#FAEEDA","border":"#EF9F27","color":"#854F0B"},
            {"arrow":True,"amt":"$20 withdrawal","note":"format swap"},
            {"id":"Xbank","label":"Bank X","abbr":"BX","bg":"#E6F1FB","border":"#378ADD","color":"#185FA5"},
        ],
        "involved": ["Xbank","CustomerA"],
    },
    {
        "id": 10, "emoji": "🎓",
        "title": "Full System Review",
        "short": "The complete monetary system — from $0 to $230!",
        "insight": "Journey: $0→$100→$200→$300→$230→$230→$230→$230→$230. Banks create money, repayments destroy it, reserves settle inter-bank payments, cash is just a format.",
        "tag": "🎓 Complete!", "tag_type": "green",
        "transactions": [], "flow": [], "involved": [],
    },
]

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
FRIENDLY = {"CustomerADep":"Cust A Dep","CustomerBDep":"Cust B Dep","CustomerCDep":"Cust C Dep","DueCB":"Due to CB","CreditsToBanks":"Credits→Banks","NetWorth":"Net Worth"}
def fname(k): return FRIENDLY.get(k, k)

def init_state():
    return {k: {"assets": dict(v["assets"]), "liabilities": dict(v["liabilities"])} for k, v in ENTITY_DEFS.items()}

def apply_tx(state, txs):
    s = deepcopy(state)
    for entity, side, account, amount in txs:
        e = s[entity]
        if side == "debit":
            if account in e["assets"]:           e["assets"][account]      += amount
            elif account in e["liabilities"]:    e["liabilities"][account] -= amount
        else:
            if account in e["assets"]:           e["assets"][account]      -= amount
            elif account in e["liabilities"]:    e["liabilities"][account] += amount
    return s

def compute_ms(state):
    bank = sum(state["Xbank"]["liabilities"].get(k,0) + state["Ybank"]["liabilities"].get(k,0)
               for k in ["CustomerADep","CustomerBDep","CustomerCDep"])
    cash = sum(state[e]["assets"].get("Cash",0) for e in ["CustomerA","CustomerB","CustomerC","Xbank","Ybank"])
    return bank, cash, bank + cash

SNAPSHOTS = [init_state()]
for sc in SCENARIOS:
    SNAPSHOTS.append(apply_tx(SNAPSHOTS[-1], sc["transactions"]))

MS_HISTORY = []
for i, snap in enumerate(SNAPSHOTS):
    bm, cm, tot = compute_ms(snap)
    MS_HISTORY.append({"label": "Start" if i == 0 else f"Step {i}", "bank": bm, "cash": cm, "total": tot})

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 0

def go_prev(): st.session_state.step = max(0, st.session_state.step - 1)
def go_next(): st.session_state.step = min(9, st.session_state.step + 1)
def reset():   st.session_state.step = 0

# ─── RENDER HELPERS ───────────────────────────────────────────────────────────
def dots_html(current):
    parts = []
    for i in range(10):
        cls = "dot-done" if i < current else ("dot-active" if i == current else "dot-empty")
        parts.append(f'<span class="{cls}" title="Step {i+1}"></span>')
    return f'<div class="dots-row">{"".join(parts)}</div>'

def flow_html(nodes):
    if not nodes:
        return '<div style="font-size:12px;color:#a0a0a0;padding:4px 0;">All steps complete — full system simulated.</div>'
    parts = []
    for n in nodes:
        if n.get("id"):
            parts.append(f'<div class="flow-node"><div class="flow-circle" style="background:{n["bg"]};border-color:{n["border"]};color:{n["color"]};">{n["abbr"]}</div><div class="flow-node-lbl">{n["label"]}</div></div>')
        elif n.get("arrow"):
            parts.append(f'<div class="flow-arrow"><div class="flow-amt">{n["amt"]}</div><div class="flow-line"></div><div class="flow-note">{n["note"]}</div></div>')
    return f'<div class="flow-row">{"".join(parts)}</div>'

def bsheet_html(ek, state, active):
    e = state[ek]
    label = ENTITY_DEFS[ek]["label"]
    assets = [(k,v) for k,v in e["assets"].items() if v != 0]
    liabs  = [(k,v) for k,v in e["liabilities"].items() if v != 0]
    ta = sum(v for _,v in assets)
    tl = sum(v for _,v in liabs)
    if ta == 0 and tl == 0:
        return f'<div class="bsheet"><div class="bsheet-head"><span class="bsheet-name" style="color:#a0a0a0;">{label}</span></div><div class="bsheet-empty">empty</div></div>'
    badge = '<span class="bsheet-active-badge">active</span>' if active else ""
    acls  = " active" if active else ""
    ar = "".join(f'<div class="bsheet-row"><span>{fname(k)}</span><span class="bval">${v}</span></div>' for k,v in assets) or '<div class="bsheet-row" style="color:#ccc;font-size:10px;">—</div>'
    lr = "".join(f'<div class="bsheet-row"><span>{fname(k)}</span><span class="bval">${abs(v)}</span></div>' for k,v in liabs) or '<div class="bsheet-row" style="color:#ccc;font-size:10px;">—</div>'
    return f'''<div class="bsheet{acls}">
      <div class="bsheet-head"><span class="bsheet-name">{label}</span>{badge}</div>
      <div class="bsheet-body">
        <div class="bsheet-col bsheet-col-left"><div class="col-title-a">Assets</div>{ar}</div>
        <div class="bsheet-col"><div class="col-title-l">Liabilities</div>{lr}</div>
      </div>
      <div class="bsheet-total"><span class="t-a">${ta}</span><span class="t-l">${abs(tl)}</span></div>
    </div>'''

def ms_chart(step):
    visible = MS_HISTORY[:step+2]
    labels  = [d["label"] for d in visible]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=[d["bank"] for d in visible], name="Bank Money (Deposits)", marker_color="#85B7EB"))
    fig.add_trace(go.Bar(x=labels, y=[d["cash"] for d in visible], name="Cash in Circulation",   marker_color="#C084FC"))
    fig.add_trace(go.Scatter(
        x=labels, y=[d["total"] for d in visible], name="Total Money Supply",
        mode="lines+markers",
        line=dict(color="#EF9F27", width=3, shape="spline"),
        marker=dict(size=8, color="#EF9F27", line=dict(width=2, color="white")),
    ))
    if visible:
        last = visible[-1]
        fig.add_annotation(x=last["label"], y=last["total"], text=f"<b>${last['total']}</b>",
            showarrow=True, arrowhead=2, arrowcolor="#EF9F27", ax=0, ay=-36,
            font=dict(size=13, color="#D97706"), bgcolor="white", bordercolor="#EF9F27", borderwidth=1.5, borderpad=4)
    fig.update_layout(
        barmode="stack", height=260,
        margin=dict(t=40, b=20, l=50, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        yaxis=dict(range=[0,400], gridcolor="#f0f0f0", tickprefix="$", tickfont=dict(size=10)),
        xaxis=dict(tickfont=dict(size=10), gridcolor="rgba(0,0,0,0)"),
        bargap=0.3,
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 💰 Money Game")
    st.caption("Who creates money?")
    st.markdown("---")

    step = st.session_state.step
    ms   = MS_HISTORY[step + 1]
    pms  = MS_HISTORY[step]

    st.markdown('<div style="font-size:10px;color:#a0a0a0;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">Progress</div>', unsafe_allow_html=True)
    st.markdown(dots_html(step), unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:11px;color:#6b6b6b;margin-top:4px;margin-bottom:8px;">Step {step+1} of 10</div>', unsafe_allow_html=True)

    diff = ms["total"] - pms["total"]
    if   diff > 0: delta_html = f'<div class="sb-metric-delta delta-pos">+${diff} this step</div>'
    elif diff < 0: delta_html = f'<div class="sb-metric-delta delta-neg">−${abs(diff)} destroyed</div>'
    else:          delta_html = '<div class="sb-metric-delta delta-neu">no change</div>'

    st.markdown(f"""
    <div class="sb-metric">
      <div class="sb-metric-label">Total money supply</div>
      <div class="sb-metric-val">${ms['total']}</div>
      {delta_html}
    </div>
    <div class="sb-metric">
      <div class="sb-metric-label">Bank money</div>
      <div class="sb-metric-val">${ms['bank']}</div>
    </div>
    <div class="sb-metric">
      <div class="sb-metric-label">Cash in circulation</div>
      <div class="sb-metric-val">${ms['cash']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-size:10px;color:#a0a0a0;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px;">Players</div>', unsafe_allow_html=True)
    for name, color in [("Bank X","#378ADD"),("Bank Y","#1D9E75"),("Central Bank","#9FE1CB"),("Customer A","#EF9F27"),("Customer B","#D85A30"),("Customer C","#D4537E")]:
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:12px;color:#6b6b6b;"><div style="width:9px;height:9px;border-radius:50%;background:{color};flex-shrink:0;"></div>{name}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-size:10px;color:#a0a0a0;line-height:1.6;">📘 Based on <em>Modern Monetary System in Theory and Practice</em> by Engin Yılmaz</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
step  = st.session_state.step
sc    = SCENARIOS[step]
state = SNAPSHOTS[step + 1]

# ── STEP HEADER ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="step-header-card">
  <span class="step-badge">Step {sc['id']} of 10</span>
  <div class="step-title">{sc['emoji']} {sc['title']}</div>
  <div class="step-desc">{sc['short']}</div>
  <span class="tag tag-{sc['tag_type']}">{sc['tag']}</span>
</div>
""", unsafe_allow_html=True)

# ── NAV BUTTONS ───────────────────────────────────────────────────────────────
c1, c2, c3, _ = st.columns([1, 1.6, 1, 4])
with c1:
    st.button("← Back", on_click=go_prev, disabled=(step == 0), use_container_width=True)
with c2:
    if step == 9:
        st.button("✓ Completed!", disabled=True, use_container_width=True, type="primary")
    else:
        lbl = f"Execute Step {sc['id']} →" if step == 0 else f"Next: Step {step+2} →"
        st.button(lbl, on_click=go_next, use_container_width=True, type="primary")
with c3:
    st.button("↺ Reset", on_click=reset, use_container_width=True)

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ── FLOW DIAGRAM ──────────────────────────────────────────────────────────────
st.markdown(f'<div class="flow-strip"><div class="flow-label">transaction flow</div>{flow_html(sc["flow"])}</div>', unsafe_allow_html=True)

# ── INSIGHT ───────────────────────────────────────────────────────────────────
st.markdown(f'<div class="insight-bar">💡 {sc["insight"]}</div>', unsafe_allow_html=True)

# ── BALANCE SHEETS ────────────────────────────────────────────────────────────
st.markdown('<div style="font-size:10px;color:#a0a0a0;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px;">Live balance sheets — highlighted = active this step</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="small")
with col1:
    st.markdown('<div style="font-size:10px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;">Commercial Banks</div>', unsafe_allow_html=True)
    for ek in ["Xbank","Ybank"]:
        st.markdown(bsheet_html(ek, state, ek in sc["involved"]), unsafe_allow_html=True)

with col2:
    st.markdown('<div style="font-size:10px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;">Customers</div>', unsafe_allow_html=True)
    for ek in ["CustomerA","CustomerB","CustomerC"]:
        st.markdown(bsheet_html(ek, state, ek in sc["involved"]), unsafe_allow_html=True)

with col3:
    st.markdown('<div style="font-size:10px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;">Central Bank</div>', unsafe_allow_html=True)
    st.markdown(bsheet_html("CentralBank", state, "CentralBank" in sc["involved"]), unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#FAF5FF;border-radius:8px;padding:10px 12px;margin-top:6px;font-size:11px;color:#6D28D9;line-height:1.6;border:1px solid #E9D5FF;">
      <strong>💡 Golden Rule</strong><br>
      Debits = Credits always.<br>
      Assets = Liabilities + Net Worth.
    </div>
    """, unsafe_allow_html=True)

# ── COMPLETION ────────────────────────────────────────────────────────────────
if step == 9:
    st.markdown("""
    <div class="complete-card">
      <div style="font-size:2.5em;">🎉</div>
      <h2 style="color:#14532D;margin:8px 0 6px;">All 10 Steps Completed!</h2>
      <p style="color:#166534;">You now understand how money really works in the modern economy.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── CHART ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="font-size:14px;font-weight:700;margin-bottom:2px;">📈 Money Supply Over Time</div>
<div style="font-size:11px;color:#a0a0a0;margin-bottom:4px;">Orange line = Total M1 · Blue bars = Bank deposits · Purple = Cash held by public</div>
""", unsafe_allow_html=True)
st.plotly_chart(ms_chart(step), use_container_width=True)