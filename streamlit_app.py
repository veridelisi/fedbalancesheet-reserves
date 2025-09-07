import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal")
st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki menüden veya aşağıdaki kısayoldan gidin.")

ok = False
try:
    # Yeni Streamlit sürümlerinde en temiz yol
    st.page_link("pages/01_Reserves.py", label="➡️ Reserves dashboard")
    ok = True
except Exception:
    pass

if not ok:
    # Eski sürüm/önbellek durumlarında garanti olsun diye slugların ikisini de veriyoruz
    st.markdown(
        """
**Kısayol (garanti):**
- [➡️ Reserves](/Reserves)
- [➡️ reserves](/reserves)
        """
    )
