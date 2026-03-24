import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from copy import deepcopy

st.set_page_config(
    page_title="💰 Money Creation Game",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

/* Hide default streamlit top padding */
.block-container { padding-top: 1rem !important; }

/* Quiz answer buttons */
.quiz-option button {
    width: 100%;
    text-align: left !important;
    border-radius: 10px !important;
    border: 1.5px solid #C7D2FE !important;
    background: white !important;
    color: #1E1B4B !important;
    font-size: 14px !important;
    font-family: 'Syne', sans-serif !important;
    transition: all 0.2s ease;
    padding: 10px 16px !important;
}
.quiz-option button:hover {
    border-color: #6366F1 !important;
    background: #EEF2FF !important;
}

/* Myth card */
.myth-card {
    background: linear-gradient(135deg, #FFF1F2, #FFF7ED);
    border: 1.5px solid #FECACA;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 14px;
}

/* Streak badge */
.streak-badge {
    background: linear-gradient(135deg, #F59E0B, #EF4444);
    color: white;
    border-radius: 30px;
    padding: 4px 16px;
    font-weight: 700;
    font-size: 14px;
    display: inline-block;
}

/* Progress steps */
.step-dot {
    width: 12px; height: 12px;
    border-radius: 50%;
    display: inline-block;
    margin: 0 2px;
}
</style>
""", unsafe_allow_html=True)

# ─── GAME DATA ────────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "id": 1, "emoji": "✨",
        "title": "Bank X Creates Money — From Nothing!",
        "short": "Bank X grants Customer A a $100 loan, writing new money into existence.",
        "description": (
            "Bank X opens a $100 deposit account for Customer A and records a $100 loan "
            "on its own books. No prior savings were needed.\n\n"
            "🔑 The economy started with **$0**. Now it has **$100**. "
            "Banks don't lend out existing money — they **create brand new money** when they "
            "make loans. This is called **endogenous money creation** and it's how most "
            "modern money is born."
        ),
        "transactions": [
            ("Xbank", "debit", "Credits", 100),
            ("Xbank", "credit", "Customer A Deposit", 100),
            ("CustomerA", "debit", "Deposits", 100),
            ("CustomerA", "credit", "Credits", 100),
        ],
        "involved": ["Xbank", "CustomerA"],
        "tag": "💚 Money Created", "tag_color": "#16A34A",
        "quiz": {
            "question": "Where does Bank X get the $100 it lends to Customer A?",
            "options": [
                "From other depositors' savings",
                "From the Central Bank's printing press",
                "It creates it from nothing via a bookkeeping entry ✓",
                "From its own profit reserves",
            ],
            "correct": 2,
            "explanation": "Correct! Banks create money by simply typing a number into a deposit account. This is called **credit money creation** — no prior savings needed."
        }
    },
    {
        "id": 2, "emoji": "🏛️",
        "title": "Central Bank Provides Reserves",
        "short": "The Central Bank lends $100 in reserves to each commercial bank.",
        "description": (
            "The Central Bank creates brand new reserves and lends them to Bank X and Bank Y.\n\n"
            "🔑 Reserves are the 'settlement currency' between banks — they live only in the "
            "Central Bank's ledger and never leave the banking system. "
            "Banks need reserves to settle payments with each other. "
            "Notice that reserves **do not count** in the public money supply (M1) — "
            "they are behind-the-scenes plumbing!"
        ),
        "transactions": [
            ("Xbank", "debit", "Reserves", 100),
            ("Xbank", "credit", "Due to Central Bank", 100),
            ("Ybank", "debit", "Reserves", 100),
            ("Ybank", "credit", "Due to Central Bank", 100),
            ("CentralBank", "debit", "Credits to Banks", 200),
            ("CentralBank", "credit", "Reserves", 200),
        ],
        "involved": ["Xbank", "Ybank", "CentralBank"],
        "tag": "➡️ No Change in M1", "tag_color": "#3B82F6",
        "quiz": {
            "question": "Why do banks need reserves?",
            "options": [
                "To fund new loans to customers",
                "To settle payments between banks ✓",
                "To pay interest to depositors",
                "To meet government tax obligations",
            ],
            "correct": 1,
            "explanation": "Exactly! Reserves exist exclusively for inter-bank settlement. When your bank sends money to another bank, reserves move between their Central Bank accounts."
        }
    },
    {
        "id": 3, "emoji": "💳",
        "title": "Bank Y Creates a Loan for Customer C",
        "short": "Bank Y grants Customer C a $100 loan — even more new money!",
        "description": (
            "Same magic as Step 1, but now Bank Y creates $100 for Customer C.\n\n"
            "🔑 Every bank can create money independently. "
            "Money supply is now **$200** — double what it was — "
            "and we haven't moved a single coin or bill. Pure accounting!"
        ),
        "transactions": [
            ("Ybank", "debit", "Credits", 100),
            ("Ybank", "credit", "Customer C Deposit", 100),
            ("CustomerC", "debit", "Deposits", 100),
            ("CustomerC", "credit", "Credits", 100),
        ],
        "involved": ["Ybank", "CustomerC"],
        "tag": "💚 Money Created", "tag_color": "#16A34A",
        "quiz": {
            "question": "After this step, what is the total money supply?",
            "options": ["$100", "$150", "$200 ✓", "$300"],
            "correct": 2,
            "explanation": "Right! $100 from Step 1 + $100 from this step = **$200** total bank money in the economy."
        }
    },
    {
        "id": 4, "emoji": "💳",
        "title": "Bank X Creates a Loan for Customer B",
        "short": "Bank X grants Customer B a $100 loan — the third money-creation event!",
        "description": (
            "Bank X writes $100 into Customer B's deposit account and records a $100 loan asset.\n\n"
            "🔑 Bank X didn't need Customer A's deposit to fund this loan! "
            "Banks are not intermediaries that move existing savings — they "
            "**manufacture new purchasing power**. Money supply is now **$300**."
        ),
        "transactions": [
            ("Xbank", "debit", "Credits", 100),
            ("Xbank", "credit", "Customer B Deposit", 100),
            ("CustomerB", "debit", "Deposits", 100),
            ("CustomerB", "credit", "Credits", 100),
        ],
        "involved": ["Xbank", "CustomerB"],
        "tag": "💚 Money Created", "tag_color": "#16A34A",
        "quiz": {
            "question": "Bank X already has a loan to Customer A. How does it fund Customer B's loan?",
            "options": [
                "By using Customer A's deposit as collateral",
                "By borrowing from the Central Bank first",
                "By creating a new deposit entry — no funding needed ✓",
                "By calling in Customer A's loan first",
            ],
            "correct": 2,
            "explanation": "Precisely! Banks don't move existing money around — each loan is a fresh creation. This is why banks can lend in parallel to many borrowers simultaneously."
        }
    },
    {
        "id": 5, "emoji": "📉",
        "title": "Customer B Repays Part of the Loan",
        "short": "Customer B repays $70 to Bank X — destroying money!",
        "description": (
            "Customer B's deposit falls by $70 and Bank X cancels $70 of the outstanding loan. "
            "The money simply disappears.\n\n"
            "🔑 Just as loans **create** money, loan repayments **destroy** it! "
            "Money supply drops $300 → $230. "
            "When societies pay down debt faster than banks lend, the money supply shrinks — "
            "this is called **debt deflation**."
        ),
        "transactions": [
            ("Xbank", "debit", "Customer B Deposit", 70),
            ("Xbank", "credit", "Credits", 70),
            ("CustomerB", "debit", "Credits", 70),
            ("CustomerB", "credit", "Deposits", 70),
        ],
        "involved": ["Xbank", "CustomerB"],
        "tag": "🔴 Money Destroyed", "tag_color": "#EF4444",
        "quiz": {
            "question": "What happens to money when a loan is repaid?",
            "options": [
                "It goes into the bank's vault",
                "It is sent to the Central Bank",
                "It is redistributed to other depositors",
                "It is destroyed — it ceases to exist ✓",
            ],
            "correct": 3,
            "explanation": "Exactly! Loan repayment is the mirror image of loan creation. The money vanishes from the balance sheet just as it appeared — through a bookkeeping entry."
        }
    },
    {
        "id": 6, "emoji": "💸",
        "title": "Customer A Pays Customer B (Same Bank)",
        "short": "Customer A sends $50 to Customer B — both bank at Bank X.",
        "description": (
            "Bank X simply moves $50 from Customer A's account to Customer B's account. "
            "No reserves move. No cash changes hands.\n\n"
            "🔑 Payments within the same bank are pure bookkeeping — "
            "Bank X acts as an internal clearing house. Money supply stays **$230**. "
            "Money just changed hands."
        ),
        "transactions": [
            ("Xbank", "debit", "Customer A Deposit", 50),
            ("Xbank", "credit", "Customer B Deposit", 50),
            ("CustomerA", "debit", "Equity", 50),
            ("CustomerA", "credit", "Deposits", 50),
            ("CustomerB", "debit", "Deposits", 50),
            ("CustomerB", "credit", "Equity", 50),
        ],
        "involved": ["Xbank", "CustomerA", "CustomerB"],
        "tag": "➡️ Transfer Only", "tag_color": "#3B82F6",
        "quiz": {
            "question": "When Customer A pays Customer B (both at Bank X), do reserves move?",
            "options": [
                "Yes, reserves always move in any payment",
                "No — it's internal bookkeeping only ✓",
                "Only if the amount exceeds $100",
                "Only if the Central Bank approves it",
            ],
            "correct": 1,
            "explanation": "Correct! Same-bank transfers are just internal ledger adjustments. No reserves needed. This is why banks love customers who bank with them — cheaper to process!"
        }
    },
    {
        "id": 7, "emoji": "🔄",
        "title": "Customer C Pays Customer A (Cross-Bank!)",
        "short": "Customer C (Bank Y) sends $50 to Customer A (Bank X) — reserves must move!",
        "description": (
            "Bank Y reduces Customer C's deposit and transfers $50 of reserves to Bank X. "
            "Bank X credits Customer A with $50.\n\n"
            "🔑 Cross-bank payments require **reserve transfers** between banks. "
            "This is why Step 2 mattered — without reserves, the payment can't happen. "
            "Money supply stays $230 — money just moved between banks."
        ),
        "transactions": [
            ("Xbank", "debit", "Reserves", 50),
            ("Xbank", "credit", "Customer A Deposit", 50),
            ("Ybank", "debit", "Customer C Deposit", 50),
            ("Ybank", "credit", "Reserves", 50),
            ("CustomerA", "debit", "Deposits", 50),
            ("CustomerA", "credit", "Equity", 50),
            ("CustomerC", "debit", "Equity", 50),
            ("CustomerC", "credit", "Deposits", 50),
        ],
        "involved": ["Xbank", "Ybank", "CustomerA", "CustomerC"],
        "tag": "➡️ Transfer Only", "tag_color": "#3B82F6",
        "quiz": {
            "question": "Why can't Bank Y just send the customer deposit directly to Bank X?",
            "options": [
                "Regulations prohibit direct transfers",
                "Bank deposits only exist inside their own bank's ledger — only reserves cross banks ✓",
                "The Central Bank must approve all cross-bank flows",
                "There is no technical reason; banks just prefer reserves",
            ],
            "correct": 1,
            "explanation": "Spot on! A Bank Y deposit is Bank Y's liability — it can't move to Bank X's ledger. Only central bank reserves are universally accepted for inter-bank settlement."
        }
    },
    {
        "id": 8, "emoji": "💵",
        "title": "Banks Withdraw Physical Cash",
        "short": "Each bank withdraws $20 in physical cash from the Central Bank.",
        "description": (
            "Banks swap $20 of electronic reserves for $20 of physical cash bills. "
            "The Central Bank's reserves fall; cash in circulation rises.\n\n"
            "🔑 Cash and reserves are both forms of **central bank money** — "
            "just different formats of the same thing. "
            "Banks get physical cash so they can hand it to customers at ATMs. "
            "Total money supply doesn't change — only the form shifts."
        ),
        "transactions": [
            ("Xbank", "debit", "Cash", 20),
            ("Xbank", "credit", "Reserves", 20),
            ("Ybank", "debit", "Cash", 20),
            ("Ybank", "credit", "Reserves", 20),
            ("CentralBank", "debit", "Reserves", 40),
            ("CentralBank", "credit", "Cash", 40),
        ],
        "involved": ["Xbank", "Ybank", "CentralBank"],
        "tag": "➡️ Form Change Only", "tag_color": "#3B82F6",
        "quiz": {
            "question": "When banks convert reserves into physical cash, what happens to the money supply?",
            "options": [
                "It increases — cash is 'real' money",
                "It decreases — reserves are more powerful",
                "Nothing changes — it's just a format swap ✓",
                "It depends on the Central Bank's policy rate",
            ],
            "correct": 2,
            "explanation": "Exactly! Both reserves and cash are central bank money. Converting one into the other changes the form, not the total. Like swapping a $20 bill for four $5 bills."
        }
    },
    {
        "id": 9, "emoji": "🏧",
        "title": "Customer A Withdraws Cash",
        "short": "Customer A takes out $20 in physical cash from Bank X.",
        "description": (
            "Customer A's bank deposit decreases by $20 and they receive $20 in physical banknotes.\n\n"
            "🔑 This converts **bank money** into **central bank money** — "
            "but total money supply stays at $230. "
            "Bank X needed physical cash on hand (from Step 8) to do this. "
            "This is why banks manage their cash reserves so carefully!"
        ),
        "transactions": [
            ("Xbank", "debit", "Customer A Deposit", 20),
            ("Xbank", "credit", "Cash", 20),
            ("CustomerA", "debit", "Cash", 20),
            ("CustomerA", "credit", "Deposits", 20),
        ],
        "involved": ["Xbank", "CustomerA"],
        "tag": "➡️ Form Change Only", "tag_color": "#3B82F6",
        "quiz": {
            "question": "When Customer A withdraws $20 cash, what happens to the money supply?",
            "options": [
                "It increases — physical money is 'created'",
                "It decreases — bank deposit money is 'better'",
                "It stays the same — bank money converts to cash ✓",
                "The Central Bank must print $20 of new money",
            ],
            "correct": 2,
            "explanation": "Right! Bank deposits (M1) and cash (M0) both count in the broad money supply. Withdrawing cash just shifts the form — from a number in a computer to a physical note."
        }
    },
    {
        "id": 10, "emoji": "🎓",
        "title": "Full System Review",
        "short": "The complete monetary system — from $0 to $230!",
        "description": (
            "**Congratulations!** You've just simulated a complete modern monetary system!\n\n"
            "**The journey:** $0 → $100 → $200 → $300 → $230 → $230 → $230 → $230 → $230\n\n"
            "**What you learned:**\n"
            "- ✨ Banks **create** money from nothing when they make loans\n"
            "- 📉 Loan repayments **destroy** money\n"
            "- 🏛️ Central banks provide reserves for inter-bank settlement\n"
            "- 💸 Same-bank payments are just internal bookkeeping\n"
            "- 🔄 Cross-bank payments require reserve transfers\n"
            "- 💵 Cash is just a different form of the same money\n\n"
            "**This is exactly how the real monetary system works!** 🌍"
        ),
        "transactions": [],
        "involved": ["Xbank", "Ybank", "CentralBank", "CustomerA", "CustomerB", "CustomerC"],
        "tag": "🎓 Complete!", "tag_color": "#16A34A",
        "quiz": None
    },
]

# ─── MYTH BUSTING DATA ────────────────────────────────────────────────────────
MYTHS = [
    {
        "myth": "❌ Central banks create most of the money in circulation.",
        "truth": "✅ Commercial banks create ~97% of money through lending. Central banks only create reserves (used between banks) and physical cash — a small fraction of total money.",
        "detail": "In most modern economies, over 95% of the money supply consists of bank deposits created by commercial banks when they issue loans.",
        "emoji": "🏛️"
    },
    {
        "myth": "❌ Banks lend out money that depositors have saved.",
        "truth": "✅ Banks create new deposits when they make loans. Savings come *after* lending, not before. A bank doesn't need your deposit to give a loan.",
        "detail": "This 'loanable funds' myth is taught in many textbooks but contradicted by Bank of England research (2014) and central bank publications worldwide.",
        "emoji": "💳"
    },
    {
        "myth": "❌ Banks can lend out 10x their deposits (money multiplier model).",
        "truth": "✅ The 'money multiplier' is a textbook simplification. In reality, banks make loans first, then seek reserves afterwards. Lending is constrained by demand for loans, not by deposits.",
        "detail": "The Federal Reserve and Bank of England have both acknowledged the money multiplier model is not how modern banking works in practice.",
        "emoji": "✖️"
    },
    {
        "myth": "❌ Printing money always causes inflation.",
        "truth": "✅ Money creation causes inflation only when it outpaces productive capacity. Newly created money spent on productive investment can grow the economy without inflating prices.",
        "detail": "Japan has engaged in massive money creation for decades with minimal inflation. Context — what money is created for and how much productive capacity exists — matters enormously.",
        "emoji": "📊"
    },
    {
        "myth": "❌ A government must balance its budget like a household.",
        "truth": "✅ A currency-issuing government is fundamentally different from a household. It can create its own currency. The real constraints are inflation and productive capacity, not running out of money.",
        "detail": "This is the core insight of Modern Monetary Theory (MMT). Countries that issue their own currency (US, UK, Japan) cannot 'run out' of their own money the way households can.",
        "emoji": "🏛️"
    },
]

# ─── GLOSSARY DATA ────────────────────────────────────────────────────────────
GLOSSARY = {
    "Endogenous Money": "Money created inside the banking system by commercial banks when they make loans. The supply of money is determined by demand for loans, not by central bank policy.",
    "Reserves": "Electronic balances held by commercial banks at the Central Bank. Used only for inter-bank settlement — customers never touch reserves directly.",
    "M1 Money Supply": "The narrow measure of money: physical cash + bank deposits. This is the money the public actually uses.",
    "M0 (Monetary Base)": "Central bank money only: reserves + physical cash. This is what the Central Bank controls directly.",
    "Double-Entry Bookkeeping": "Every financial transaction records both a debit and a credit of equal amount. Assets always equal Liabilities + Equity.",
    "Debt Deflation": "When the economy-wide repayment of debt destroys money faster than new lending creates it, causing the money supply to shrink and prices to fall.",
    "Loanable Funds (Myth)": "The incorrect textbook model suggesting banks collect deposits and lend them out. In reality, banks create deposits when they lend.",
    "Monetary Hierarchy": "The layered system of money: Central bank money (reserves, cash) at the top, commercial bank money (deposits) below it. Higher layers settle lower layer obligations.",
    "Credit Creation": "The process by which commercial banks create new purchasing power by issuing loans and simultaneously creating matching deposit liabilities.",
    "Quantitative Easing": "A Central Bank policy of buying financial assets to inject reserves into the banking system, aiming to lower interest rates and stimulate lending.",
}

# ─── INITIAL STATE ────────────────────────────────────────────────────────────
def get_initial_state():
    return {
        "Xbank": {
            "assets": {"Cash": 0, "Reserves": 0, "Credits": 0},
            "liabilities": {"Customer A Deposit": 0, "Customer B Deposit": 0, "Due to Central Bank": 0},
        },
        "Ybank": {
            "assets": {"Cash": 0, "Reserves": 0, "Credits": 0},
            "liabilities": {"Customer C Deposit": 0, "Due to Central Bank": 0},
        },
        "CentralBank": {
            "assets": {"Credits to Banks": 0},
            "liabilities": {"Reserves": 0, "Cash": 0},
        },
        "CustomerA": {
            "assets": {"Cash": 0, "Deposits": 0},
            "liabilities": {"Credits": 0, "Equity": 0},
        },
        "CustomerB": {
            "assets": {"Deposits": 0},
            "liabilities": {"Credits": 0, "Equity": 0},
        },
        "CustomerC": {
            "assets": {"Deposits": 0},
            "liabilities": {"Credits": 0, "Equity": 0},
        },
    }

# ─── BOOKKEEPING ENGINE ───────────────────────────────────────────────────────
def apply_transaction(state, entity, side, account, amount):
    s = state[entity]
    if side == "debit":
        if account in s["assets"]:
            s["assets"][account] += amount
        elif account in s["liabilities"]:
            s["liabilities"][account] -= amount
    elif side == "credit":
        if account in s["assets"]:
            s["assets"][account] -= amount
        elif account in s["liabilities"]:
            s["liabilities"][account] += amount

def apply_scenario(state, scenario):
    new_state = deepcopy(state)
    for entity, side, account, amount in scenario["transactions"]:
        apply_transaction(new_state, entity, side, account, amount)
    return new_state

def compute_money_supply(state):
    bank_money = 0
    for key in ["Customer A Deposit", "Customer B Deposit", "Customer C Deposit"]:
        bank_money += state["Xbank"]["liabilities"].get(key, 0)
        bank_money += state["Ybank"]["liabilities"].get(key, 0)
    central_bank_money = 0
    for entity in ["CustomerA", "CustomerB", "CustomerC", "Xbank", "Ybank"]:
        central_bank_money += state[entity]["assets"].get("Cash", 0)
    return bank_money, central_bank_money, bank_money + central_bank_money

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "current_step" not in st.session_state:
    st.session_state.current_step = 0
if "state_history" not in st.session_state:
    st.session_state.state_history = [get_initial_state()]
if "money_supply_history" not in st.session_state:
    st.session_state.money_supply_history = [
        {"step": 0, "label": "Start", "bank_money": 0, "cb_money": 0, "total": 0}
    ]
if "last_scenario" not in st.session_state:
    st.session_state.last_scenario = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "streak" not in st.session_state:
    st.session_state.streak = 0
if "quiz_answered" not in st.session_state:
    st.session_state.quiz_answered = {}
if "quiz_result" not in st.session_state:
    st.session_state.quiz_result = {}
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "simulator"
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

def current_state():
    return st.session_state.state_history[-1]

def reset_game():
    st.session_state.current_step = 0
    st.session_state.state_history = [get_initial_state()]
    st.session_state.money_supply_history = [
        {"step": 0, "label": "Start", "bank_money": 0, "cb_money": 0, "total": 0}
    ]
    st.session_state.last_scenario = None
    st.session_state.score = 0
    st.session_state.streak = 0
    st.session_state.quiz_answered = {}
    st.session_state.quiz_result = {}

def advance_step(scenario):
    new_state = apply_scenario(current_state(), scenario)
    st.session_state.state_history.append(new_state)
    st.session_state.current_step += 1
    bm, cbm, total = compute_money_supply(new_state)
    st.session_state.money_supply_history.append({
        "step": st.session_state.current_step,
        "label": f"Step {scenario['id']}",
        "bank_money": bm,
        "cb_money": cbm,
        "total": total,
    })
    st.session_state.last_scenario = scenario

# ─── ENTITY CONFIG ────────────────────────────────────────────────────────────
ENTITY_COLORS = {
    "Xbank": "#3B82F6",
    "Ybank": "#22C55E",
    "CentralBank": "#A855F7",
    "CustomerA": "#F97316",
    "CustomerB": "#EAB308",
    "CustomerC": "#06B6D4",
}
ENTITY_NAMES = {
    "Xbank": "🏦 Bank X",
    "Ybank": "🏦 Bank Y",
    "CentralBank": "🏛️ Central Bank",
    "CustomerA": "👤 Customer A",
    "CustomerB": "👤 Customer B",
    "CustomerC": "👤 Customer C",
}

# ─── BALANCE SHEET RENDERER ───────────────────────────────────────────────────
def render_balance_sheet(entity_key, state, highlight=False):
    s = state[entity_key]
    color = ENTITY_COLORS[entity_key]
    name = ENTITY_NAMES[entity_key]

    assets_items = [(k, v) for k, v in s["assets"].items() if v != 0]
    liab_items = [(k, v) for k, v in s["liabilities"].items() if v != 0]
    total_assets = sum(v for _, v in assets_items)
    total_liabs = sum(v for _, v in liab_items)

    if total_assets == 0 and total_liabs == 0:
        st.markdown(
            f'<div style="border:1px dashed {color}50;border-radius:10px;padding:10px 14px;'
            f'text-align:center;color:{color}80;font-size:12px;margin-bottom:10px;">'
            f'{name} &mdash; <em>empty</em></div>',
            unsafe_allow_html=True,
        )
        return

    border = f"2px solid {color}" if highlight else f"1px solid {color}30"
    shadow = "box-shadow:0 2px 12px rgba(0,0,0,0.08);" if highlight else ""
    bg = f"background:linear-gradient(135deg,{color}12,{color}06);" if highlight else "background:#fafafa;"

    rows_a = "".join(
        f'<tr><td style="padding:4px 8px;color:#374151;">{k}</td>'
        f'<td style="text-align:right;padding:4px 8px;font-weight:600;color:#2563EB;">${v}</td>'
        f'<td style="width:8px;"></td><td></td><td></td></tr>'
        for k, v in assets_items
    )
    rows_l = "".join(
        f'<tr><td></td><td></td><td style="width:8px;"></td>'
        f'<td style="padding:4px 8px;color:#374151;">{k}</td>'
        f'<td style="text-align:right;padding:4px 8px;font-weight:600;color:#DC2626;">${v}</td></tr>'
        for k, v in liab_items
    )

    st.markdown(f"""
    <div style="border:{border};border-radius:12px;padding:12px 14px;{bg}{shadow}margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-weight:700;font-size:13px;color:{color};">{name}</span>
        {"<span style='background:" + color + "22;color:" + color + ";font-size:10px;padding:2px 8px;border-radius:20px;font-weight:600;'>active</span>" if highlight else ""}
      </div>
      <table style="width:100%;font-size:12px;border-collapse:collapse;">
        <tr style="border-bottom:1px solid #e0e0e0;">
          <th style="text-align:left;padding:3px 8px;color:#2563EB;font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Assets</th>
          <th style="text-align:right;padding:3px 8px;color:#2563EB;font-size:10px;"></th>
          <th style="width:8px;"></th>
          <th style="text-align:left;padding:3px 8px;color:#DC2626;font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Liabilities</th>
          <th style="text-align:right;padding:3px 8px;color:#DC2626;font-size:10px;"></th>
        </tr>
        {rows_a}{rows_l}
        <tr style="border-top:1px solid #e0e0e0;">
          <td style="padding:4px 8px;font-size:11px;font-weight:700;color:#6B7280;">Total</td>
          <td style="text-align:right;padding:4px 8px;font-weight:700;color:#2563EB;">${total_assets}</td>
          <td></td>
          <td style="padding:4px 8px;font-size:11px;font-weight:700;color:#6B7280;">Total</td>
          <td style="text-align:right;padding:4px 8px;font-weight:700;color:#DC2626;">${total_liabs}</td>
        </tr>
      </table>
    </div>
    """, unsafe_allow_html=True)

# ─── CHART RENDERER ───────────────────────────────────────────────────────────
def render_money_supply_chart():
    history = st.session_state.money_supply_history
    df = pd.DataFrame(history)
    max_total = max(df["total"].max(), 1)
    y_max = max_total + 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["label"], y=df["bank_money"],
        name="Bank Money (Deposits)",
        marker=dict(color="#60A5FA", opacity=0.9, line=dict(width=0)),
        hovertemplate="<b>Bank Money</b>: $%{y}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["label"], y=df["cb_money"],
        name="Cash in Circulation",
        marker=dict(color="#C084FC", opacity=0.9, line=dict(width=0)),
        hovertemplate="<b>Cash</b>: $%{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["label"], y=df["total"],
        name="Total Money Supply",
        mode="lines+markers",
        line=dict(color="#F59E0B", width=3, shape="spline", smoothing=0.6),
        marker=dict(size=10, color="#F59E0B", line=dict(width=2, color="white")),
        hovertemplate="<b>Total M1</b>: $%{y}<extra></extra>",
    ))

    if len(df) > 0:
        last = df.iloc[-1]
        fig.add_annotation(
            x=last["label"], y=last["total"],
            text=f"<b>${int(last['total'])}</b>",
            showarrow=True, arrowhead=2, arrowcolor="#F59E0B",
            ax=0, ay=-36,
            font=dict(size=13, color="#D97706"),
            bgcolor="white", bordercolor="#F59E0B", borderwidth=1.5, borderpad=4,
        )

    fig.update_layout(
        barmode="stack", height=340,
        margin=dict(t=50, b=20, l=55, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0, font=dict(size=11)),
        yaxis=dict(range=[0, y_max], gridcolor="#f0f0f0", gridwidth=1,
                   tickprefix="$", tickfont=dict(size=11),
                   title=dict(text="Money Supply ($)", font=dict(size=12))),
        xaxis=dict(tickfont=dict(size=11), title=None),
        hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#ddd"),
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True)

def render_flow_diagram(scenario):
    """Render a simple SVG money-flow diagram for the scenario."""
    if not scenario or not scenario["transactions"]:
        return

    involved = scenario["involved"]
    if len(involved) < 2:
        return

    # Map entity positions
    positions = {}
    n = len(involved)
    for i, ent in enumerate(involved):
        x = 80 + int(i * (640 / max(n - 1, 1)))
        y = 120
        positions[ent] = (x, y)

    circles_svg = ""
    for ent, (x, y) in positions.items():
        color = ENTITY_COLORS.get(ent, "#888")
        label = ENTITY_NAMES.get(ent, ent)
        short = label.split(" ", 1)[1] if " " in label else label
        circles_svg += f'''
        <circle cx="{x}" cy="{y}" r="38" fill="{color}22" stroke="{color}" stroke-width="2"/>
        <text x="{x}" y="{y - 6}" text-anchor="middle" font-size="18">{label[0]}</text>
        <text x="{x}" y="{y + 10}" text-anchor="middle" font-size="10" fill="{color}" font-weight="700">{short[:10]}</text>
        '''

    # Draw arrows for each transaction (debit side = source, credit side = destination)
    arrows_svg = ""
    seen_pairs = set()
    for entity, side, account, amount in scenario["transactions"]:
        if side == "debit":
            for entity2, side2, account2, amount2 in scenario["transactions"]:
                if side2 == "credit" and entity2 != entity and (entity, entity2) not in seen_pairs:
                    if entity in positions and entity2 in positions:
                        x1, y1 = positions[entity]
                        x2, y2 = positions[entity2]
                        color = ENTITY_COLORS.get(entity, "#888")
                        mid_x = (x1 + x2) / 2
                        seen_pairs.add((entity, entity2))
                        arrows_svg += f'''
                        <defs>
                          <marker id="arrow_{entity}_{entity2}" markerWidth="8" markerHeight="8"
                            refX="6" refY="3" orient="auto">
                            <path d="M0,0 L0,6 L8,3 z" fill="{color}" />
                          </marker>
                        </defs>
                        <line x1="{x1+38}" y1="{y1}" x2="{x2-38}" y2="{y2}"
                          stroke="{color}" stroke-width="2" stroke-dasharray="5,3"
                          marker-end="url(#arrow_{entity}_{entity2})"/>
                        <text x="{mid_x}" y="{y1 - 14}" text-anchor="middle"
                          font-size="11" fill="{color}" font-weight="600">${amount}</text>
                        '''
                    break

    svg = f'''
    <svg viewBox="0 0 800 240" xmlns="http://www.w3.org/2000/svg"
      style="width:100%;max-height:200px;background:linear-gradient(135deg,#f0f4ff,#faf5ff);
      border-radius:12px;border:1px solid #E0E7FF;">
      <text x="16" y="24" font-size="12" fill="#6366F1" font-weight="700"
        font-family="monospace">💸 Transaction Flow — Step {scenario['id']}</text>
      {circles_svg}
      {arrows_svg}
    </svg>
    '''
    st.markdown(svg, unsafe_allow_html=True)

# ─── QUIZ RENDERER ────────────────────────────────────────────────────────────
def render_quiz(scenario):
    if not scenario or not scenario.get("quiz"):
        return
    quiz = scenario["quiz"]
    step_id = scenario["id"]

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#FFF7ED,#FFFBEB);border:1.5px solid #FDE68A;
    border-radius:14px;padding:18px 22px;margin-top:10px;">
      <div style="font-size:11px;color:#D97706;font-weight:700;text-transform:uppercase;
      letter-spacing:1px;margin-bottom:6px;">🧠 Quick Check</div>
      <div style="font-weight:600;font-size:14px;color:#1C1917;margin-bottom:12px;">{quiz['question']}</div>
    """, unsafe_allow_html=True)

    already_answered = step_id in st.session_state.quiz_answered

    if not already_answered:
        cols = st.columns(2)
        for i, option in enumerate(quiz["options"]):
            with cols[i % 2]:
                if st.button(option, key=f"quiz_{step_id}_{i}"):
                    st.session_state.quiz_answered[step_id] = i
                    correct = (i == quiz["correct"])
                    st.session_state.quiz_result[step_id] = correct
                    if correct:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                    else:
                        st.session_state.streak = 0
                    st.rerun()
    else:
        user_ans = st.session_state.quiz_answered[step_id]
        correct = st.session_state.quiz_result[step_id]
        if correct:
            st.markdown(f"""
            <div style="background:#DCFCE7;border-radius:10px;padding:12px 16px;border:1px solid #86EFAC;">
              <span style="color:#15803D;font-weight:700;">✅ Correct! +10 pts</span><br>
              <span style="font-size:13px;color:#166534;">{quiz['explanation']}</span>
            </div>""", unsafe_allow_html=True)
        else:
            correct_text = quiz["options"][quiz["correct"]]
            st.markdown(f"""
            <div style="background:#FEF2F2;border-radius:10px;padding:12px 16px;border:1px solid #FECACA;">
              <span style="color:#DC2626;font-weight:700;">❌ Not quite.</span><br>
              <span style="font-size:13px;color:#991B1B;">The answer was: <strong>{correct_text}</strong></span><br>
              <span style="font-size:13px;color:#991B1B;">{quiz['explanation']}</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Language toggle
    lang_col1, lang_col2 = st.columns(2)
    with lang_col1:
        if st.button("🇬🇧 EN", use_container_width=True,
                     type="primary" if st.session_state.lang == "EN" else "secondary"):
            st.session_state.lang = "EN"
            st.rerun()
    with lang_col2:
        if st.button("🇹🇷 TR", use_container_width=True,
                     type="primary" if st.session_state.lang == "TR" else "secondary"):
            st.session_state.lang = "TR"
            st.rerun()

    if st.session_state.lang == "TR":
        st.info("🇹🇷 Türkçe mod: Açıklamalar yakında eklenecek. Şimdilik İngilizce arayüz gösterilmektedir.")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#DBEAFE,#EDE9FE);
    border-radius:12px;padding:14px 16px;margin-bottom:8px;">
      <div style="font-size:1.1em;font-weight:700;color:#1E3A5F;">🎮 Game Controls</div>
    </div>
    """, unsafe_allow_html=True)

    step_now = st.session_state.current_step
    total_steps = len(SCENARIOS)
    st.progress(step_now / total_steps, text=f"Step {step_now} of {total_steps}")

    # Score & streak display
    score = st.session_state.score
    streak = st.session_state.streak
    col_s, col_str = st.columns(2)
    with col_s:
        st.metric("🏆 Score", f"{score} pts")
    with col_str:
        streak_label = f"🔥 {streak}" if streak >= 2 else f"{streak}"
        st.metric("⚡ Streak", streak_label)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    bm, cbm, total_ms = compute_money_supply(current_state())
    hist = st.session_state.money_supply_history
    prev_total = hist[-2]["total"] if len(hist) > 1 else None
    delta_str = None
    if prev_total is not None:
        dv = total_ms - prev_total
        delta_str = f"+${dv}" if dv >= 0 else f"-${abs(dv)}"

    st.metric("🏦 Bank Money", f"${bm}")
    st.metric("💵 Cash in Circulation", f"${cbm}")
    st.metric("📊 Total Money Supply", f"${total_ms}", delta=delta_str)

    st.markdown("---")

    # Navigation
    st.markdown("**📑 Sections**")
    if st.button("🎮 Simulator", use_container_width=True,
                 type="primary" if st.session_state.active_tab == "simulator" else "secondary"):
        st.session_state.active_tab = "simulator"
        st.rerun()
    if st.button("💥 Myth Busting", use_container_width=True,
                 type="primary" if st.session_state.active_tab == "myths" else "secondary"):
        st.session_state.active_tab = "myths"
        st.rerun()
    if st.button("📚 Glossary", use_container_width=True,
                 type="primary" if st.session_state.active_tab == "glossary" else "secondary"):
        st.session_state.active_tab = "glossary"
        st.rerun()

    st.markdown("---")

    if st.button("🔄 Reset Game", use_container_width=True, type="secondary"):
        reset_game()
        st.rerun()

    st.markdown("---")
    st.markdown("**🎯 Players**")
    for key, name in ENTITY_NAMES.items():
        color = ENTITY_COLORS[key]
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;">'
            f'<div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;"></div>'
            f'<span style="font-size:13px;">{name}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#9CA3AF;line-height:1.6;">
    📘 Based on <em>Modern Monetary System in Theory and Practice</em> by <strong>Engin Yılmaz</strong>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:linear-gradient(135deg,#DBEAFE,#EDE9FE);
border-radius:16px;padding:24px 32px;margin-bottom:4px;">
  <h1 style="margin:0;font-size:2.2em;font-weight:800;letter-spacing:-0.5px;color:#1E3A5F;
  font-family:'Syne',sans-serif;">
    💰 Money Creation Simulator
  </h1>
  <p style="margin:8px 0 0 0;font-size:1.05em;color:#4B5563;max-width:680px;">
    The economy starts with <strong>$0</strong>.
    Watch banks conjure money from thin air — one transaction at a time.
  </p>
</div>
""", unsafe_allow_html=True)
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: MYTH BUSTING
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.active_tab == "myths":
    st.markdown("""
    <div style="background:linear-gradient(135deg,#FFF1F2,#FFF7ED);border-radius:14px;
    padding:18px 24px;margin-bottom:16px;border:1px solid #FECACA;">
      <h2 style="margin:0 0 4px 0;color:#9F1239;font-size:1.4em;">💥 Myth Busting Mode</h2>
      <p style="margin:0;color:#6B7280;font-size:14px;">
        These are the most widespread misconceptions about how money works. Challenge your assumptions.
      </p>
    </div>
    """, unsafe_allow_html=True)

    for i, myth in enumerate(MYTHS):
        with st.expander(f"{myth['emoji']} Myth #{i+1}: {myth['myth']}", expanded=(i == 0)):
            st.markdown(f"""
            <div style="background:#DCFCE7;border-radius:10px;padding:14px 18px;margin-bottom:10px;
            border:1px solid #86EFAC;">
              <div style="font-weight:700;color:#15803D;margin-bottom:4px;">The Truth:</div>
              <div style="color:#166534;font-size:14px;">{myth['truth']}</div>
            </div>
            <div style="background:#EFF6FF;border-radius:10px;padding:12px 16px;
            border:1px solid #BFDBFE;">
              <div style="font-weight:600;color:#1D4ED8;margin-bottom:4px;">🔍 More detail:</div>
              <div style="color:#1E40AF;font-size:13px;">{myth['detail']}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: GLOSSARY
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.active_tab == "glossary":
    st.markdown("""
    <div style="background:linear-gradient(135deg,#F0FDF4,#ECFDF5);border-radius:14px;
    padding:18px 24px;margin-bottom:16px;border:1px solid #BBF7D0;">
      <h2 style="margin:0 0 4px 0;color:#14532D;font-size:1.4em;">📚 Glossary</h2>
      <p style="margin:0;color:#6B7280;font-size:14px;">
        Key terms in monetary economics — expand any term to read the definition.
      </p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    for i, (term, definition) in enumerate(GLOSSARY.items()):
        with cols[i % 2]:
            with st.expander(f"📖 {term}"):
                st.markdown(f"""
                <div style="font-size:14px;color:#374151;line-height:1.7;padding:4px 0;">
                {definition}
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: SIMULATOR (default)
# ══════════════════════════════════════════════════════════════════════════════
else:
    step_now = st.session_state.current_step

    # ── SCENARIO CARD ─────────────────────────────────────────────────────────
    if step_now < len(SCENARIOS):
        sc = SCENARIOS[step_now]
        tag_html = (
            f'<span style="background:{sc["tag_color"]}22;color:{sc["tag_color"]};'
            f'font-size:11px;padding:3px 10px;border-radius:20px;font-weight:600;'
            f'border:1px solid {sc["tag_color"]}44;">{sc["tag"]}</span>'
        )
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);
        border-radius:16px;padding:20px 28px;margin-bottom:12px;border:1px solid #C7D2FE;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
              <div style="font-size:11px;color:#6366F1;text-transform:uppercase;
              letter-spacing:1px;margin-bottom:4px;font-weight:600;">Step {sc['id']} of 10</div>
              <h2 style="margin:0 0 6px 0;color:#1E1B4B;font-size:1.35em;font-weight:700;">
                {sc['emoji']} {sc['title']}
              </h2>
              <p style="margin:0 0 10px 0;color:#4B5563;font-size:0.95em;">{sc['short']}</p>
              {tag_html}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        col_btn, col_info = st.columns([1, 2], gap="medium")
        with col_btn:
            lbl = f"▶️ Execute Step {sc['id']}" if sc["transactions"] else "🎓 See Summary"
            if st.button(lbl, use_container_width=True, type="primary"):
                advance_step(sc)
                st.rerun()
    else:
        # Completion card
        total_correct = sum(1 for v in st.session_state.quiz_result.values() if v)
        total_q = len(st.session_state.quiz_result)
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#DCFCE7,#D1FAE5);
        border-radius:16px;padding:24px 32px;text-align:center;border:1px solid #86EFAC;">
          <div style="font-size:3em;">🎉</div>
          <h2 style="color:#14532D;margin:8px 0 4px 0;font-size:1.6em;">All 10 Steps Completed!</h2>
          <p style="color:#166534;margin:0 0 12px 0;">You now understand how money really works in the modern economy.</p>
          <div style="display:flex;justify-content:center;gap:24px;flex-wrap:wrap;">
            <div style="background:white;border-radius:12px;padding:12px 24px;border:1px solid #BBF7D0;">
              <div style="font-size:1.8em;font-weight:800;color:#15803D;">{st.session_state.score}</div>
              <div style="font-size:12px;color:#6B7280;">Total Points</div>
            </div>
            <div style="background:white;border-radius:12px;padding:12px 24px;border:1px solid #BBF7D0;">
              <div style="font-size:1.8em;font-weight:800;color:#15803D;">{total_correct}/{total_q}</div>
              <div style="font-size:12px;color:#6B7280;">Quiz Correct</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Play Again", use_container_width=True, type="primary"):
            reset_game()
            st.rerun()

    # ── FLOW DIAGRAM ────────────────────────────────────────────────────────
    if st.session_state.last_scenario:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        render_flow_diagram(st.session_state.last_scenario)

    # ── EXPLANATION ─────────────────────────────────────────────────────────
    if st.session_state.last_scenario:
        ls = st.session_state.last_scenario
        color = ls["tag_color"]
        st.markdown(f"""
        <div style="background:{color}0D;border-left:4px solid {color};
        border-radius:0 10px 10px 0;padding:14px 18px;margin:10px 0 4px 0;">
          <div style="font-weight:700;color:{color};margin-bottom:6px;font-size:13px;">
            ✅ Step {ls['id']} — What happened?
          </div>
          <div style="font-size:13px;line-height:1.6;color:#333;">
            {ls['description'].replace(chr(10), '<br>')}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── QUIZ ──────────────────────────────────────────────────────────
        render_quiz(ls)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.divider()

    # ── LIVE BALANCE SHEETS ──────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:1.15em;font-weight:700;margin-bottom:4px;">📊 Live Balance Sheets</div>
    <div style="font-size:12px;color:#888;margin-bottom:12px;">
      Updates instantly with each step &nbsp;·&nbsp; Highlighted = active in last transaction
    </div>
    """, unsafe_allow_html=True)

    highlighted = set(st.session_state.last_scenario["involved"]) if st.session_state.last_scenario else set()

    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        st.markdown('<div style="font-size:12px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Commercial Banks</div>', unsafe_allow_html=True)
        render_balance_sheet("Xbank", current_state(), "Xbank" in highlighted)
        render_balance_sheet("Ybank", current_state(), "Ybank" in highlighted)
    with col2:
        st.markdown('<div style="font-size:12px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Customers</div>', unsafe_allow_html=True)
        render_balance_sheet("CustomerA", current_state(), "CustomerA" in highlighted)
        render_balance_sheet("CustomerB", current_state(), "CustomerB" in highlighted)
        render_balance_sheet("CustomerC", current_state(), "CustomerC" in highlighted)
    with col3:
        st.markdown('<div style="font-size:12px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Central Bank</div>', unsafe_allow_html=True)
        render_balance_sheet("CentralBank", current_state(), "CentralBank" in highlighted)

    st.markdown("""
    <div style="background:#FAF5FF;border-radius:10px;padding:12px 14px;margin-top:6px;
    font-size:12px;color:#6D28D9;line-height:1.6;border:1px solid #E9D5FF;">
      <strong>💡 The Golden Rule</strong><br>
      For every entry, <strong>Debits = Credits</strong>.<br>
      Assets always equal Liabilities + Equity.<br>
      Every dollar that appears somewhere must disappear somewhere else — <em>double-entry bookkeeping</em>.
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── MONEY SUPPLY CHART ──────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:1.15em;font-weight:700;margin-bottom:2px;">📈 Money Supply Over Time</div>
    <div style="font-size:12px;color:#888;margin-bottom:4px;">
      Orange line = Total M1 · Blue bars = Bank deposits · Purple = Cash held by public
    </div>
    """, unsafe_allow_html=True)
    render_money_supply_chart()