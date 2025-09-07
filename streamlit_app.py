import streamlit as st

# ---- 1) Tüm sayfaları Streamlit'e bildir ----
PAGES = [
    st.Page("streamlit_app.py",      title="Home",     icon="🏠"),
    st.Page("pages/01_Reserves.py",  title="Reserves", icon="🏦", url_path="Reserves"),
    # ileride eklersin:
    # st.Page("pages/02_Labor.py",    title="Labor",    icon="👷", url_path="Labor"),
    # st.Page("pages/03_Markets.py",  title="Markets",  icon="📈", url_path="Markets"),
]

# ---- 2) Varsayılan navigasyonu gizle ----
nav = st.navigation(pages=PAGES, position="hidden")

# ---- Home içeriği (kendi menün) ----
st.set_page_config(page_title="Veridelisi • Analytics Portal", layout="wide", initial_sidebar_state="collapsed")
st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki menü yerine aşağıdaki kısayollardan gidin.")

# Kendi linklerin — artık çalışır çünkü sayfalar önceden bildirildi
st.page_link("pages/01_Reserves.py", label="➡️ Reserves dashboard")

# (İstersen buton/kolon/grid ile zenginleştir)
# with st.columns(3)[0]:
#     st.page_link("pages/02_Labor.py",   label="👷 Labor / Employment")
# with st.columns(3)[1]:
#     st.page_link("pages/03_Markets.py", label="📈 Markets / Rates")

# ---- Router'ı çalıştır (son satırda olsun) ----
nav.run()
