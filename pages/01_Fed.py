import streamlit as st
import streamlit.components.v1 as components
import os

# Sayfa Ayarları
st.set_page_config(page_title="Fed Balance Sheet Guide", layout="wide")

# Sol Menü (Sidebar)
with st.sidebar:
    st.image("images/book.png", width=200) # Kitap görseliniz
    st.title("Policy Proposals")
    st.write("Select a proposal to view details:")
    
    # 15 Buton Oluşturma
    for i in range(1, 16):
        if st.button(f"Option {i}: {'Discount Window' if i==1 else f'Proposal {i}'}", use_container_width=True):
            st.session_state.selected_proposal = i

# Ana Ekran Mantığı
if 'selected_proposal' in st.session_state:
    prop_id = st.session_state.selected_proposal
    file_path = f"proposals/p{prop_id}.html"
    
    # Dosya var mı kontrol et
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # HTML'i ekrana bas (Yüksekliği içeriğe göre ayarlayabilirsiniz)
        components.html(html_content, height=1800, scrolling=True)
    else:
        st.warning(f"Technical document for Proposal {prop_id} is under preparation.")
        st.info("Please ensure the file exists at: " + file_path)
else:
    # Karşılama Ekranı
    st.header("A User's Guide to Reducing the Federal Reserve's Balance Sheet")
    st.subheader("Interactive Companion Guide by Engin Yılmaz")
    st.markdown("""
    Please select one of the **15 Policy Proposals** from the left sidebar to see:
    * Technical Mechanism
    * Mathematical Estimates ($B)
    * Academic Context & Caveats
    """)