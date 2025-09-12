# ===== Chart 3: 01.01.2025 Spreads to SOFR (bps) =====
st.markdown("### 📅 01.01.2025 Spreads to SOFR (bps)")
ytd_mask = spread_long["date"] >= pd.to_datetime(date(2025,1,1))
ytd = spread_long[ytd_mask]

sel_ytd = st.multiselect(
    "Add rates to the 2025-YTD chart:",
    options=opts,
    default=[],
    key="sel_ytd",
)
ytd = ytd[ytd["series"].isin(sel_ytd)] if sel_ytd else ytd.iloc[0:0]

base_ytd = alt.Chart(ytd).properties(height=320)
lines_ytd = base_ytd.mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")]
)

zero_rule_ytd = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule().encode(y="y:Q")
zero_text_ytd = alt.Chart(pd.DataFrame({"y":[0]})).mark_text(
    align="left", dx=5, dy=-8
).encode(y="y:Q", text=alt.value("SOFR baseline (0 bps)"))

st.altair_chart((lines_ytd + zero_rule_ytd + zero_text_ytd), use_container_width=True)
