import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="SmartPlate | Food Waste Analytics", page_icon="♻️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: #f6f8fa; padding: 16px 18px; border-radius: 12px;}
.small-note {color: #64748b; font-size: 0.88rem;}
</style>
""", unsafe_allow_html=True)

st.title("♻️ SmartPlate")
st.caption("SCHOOL FOOD WASTE ANALYTICS | DATA-DRIVEN DECISION SUPPORT")

APP_DIR = Path(__file__).parent
DEFAULT_FILE = APP_DIR / "Food waste data school Finland 2024-2025.xlsx"
BASELINE_DAYS = 135  # dataset authors: first 135 school days = baseline, final 20 = intervention

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Optional: upload a newer version of the Excel file", type=["xlsx"])
    st.divider()
    st.caption("By default the dashboard loads the Finland secondary-school dataset (Kuusisto, Latva & Wilén, Zenodo, DOI 10.5281/zenodo.20825233). Menu codes are identifiers, not dish names.")

file_bytes, source = None, None
if uploaded is not None:
    file_bytes, source = uploaded.getvalue(), f"Uploaded file: {uploaded.name}"
else:
    candidates = [DEFAULT_FILE] if DEFAULT_FILE.exists() else sorted(APP_DIR.glob("*.xlsx"))
    if candidates:
        file_bytes, source = candidates[0].read_bytes(), "Built-in dataset: food waste, secondary school in Finland 2024–2025"

if file_bytes is None:
    st.info("Upload **Food waste data school Finland 2024-2025.xlsx** in the sidebar to load the dashboard.")
    st.markdown("### What this dashboard analyses")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Waste overview**")
        st.write("Plate Waste (PW), Kitchen & Serving Waste (KSW), total recorded waste and waste per diner.")
        st.markdown("**Menu analysis**")
        st.write("Compare menu codes by recorded waste and grams per diner.")
    with c2:
        st.markdown("**Daily trends**")
        st.write("Explore changes in daily waste over the recorded period.")
        st.markdown("**Key findings**")
        st.write("Highlight the highest-waste menu codes and the relative contribution of waste categories.")
    st.stop()

@st.cache_data
def load_data(file_bytes):
    from io import BytesIO
    data = pd.read_excel(BytesIO(file_bytes), sheet_name="food waste school meals 2024-25")
    required = ["DATE", "MENU", "KSW kg", "PW kg", "PW g", "DINERS"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    data["DATE"] = pd.to_datetime(data["DATE"], errors="coerce")
    for col in ["MENU", "KSW kg", "PW kg", "PW g", "DINERS"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["DATE", "DINERS"]).sort_values("DATE").reset_index(drop=True)
    data["PW g/diner"] = data["PW kg"] * 1000 / data["DINERS"]
    data["KSW g/diner"] = data["KSW kg"] * 1000 / data["DINERS"]
    data["Recorded total kg"] = data["PW kg"] + data["KSW kg"]
    data["Period"] = np.where(data.index < BASELINE_DAYS, "Baseline", "Intervention")
    return data

try:
    df = load_data(file_bytes)
except Exception as e:
    st.error(f"Could not read this workbook: {e}")
    st.stop()

pw_total = df["PW kg"].sum()
ksw_total = df["KSW kg"].sum(min_count=1)
combined_total = pw_total + ksw_total
pw_diners = df.loc[df["PW kg"].notna(), "DINERS"].sum()
ksw_diners = df.loc[df["KSW kg"].notna(), "DINERS"].sum()
pw_rate = pw_total * 1000 / pw_diners if pw_diners else np.nan
ksw_rate = ksw_total * 1000 / ksw_diners if ksw_diners else np.nan
pw_share = pw_total / combined_total * 100 if combined_total else 0
ksw_share = ksw_total / combined_total * 100 if combined_total else 0

st.caption(source)
st.caption(f"Data period: {df['DATE'].min():%d %b %Y} – {df['DATE'].max():%d %b %Y}  ·  {len(df):,} records  ·  {df['DINERS'].sum():,.0f} diners")

# KPI row
k1, k2, k3, k4 = st.columns(4)
k1.metric("Plate Waste", f"{pw_total:,.1f} kg", f"{pw_rate:.2f} g / diner")
k2.metric("Kitchen & Serving Waste", f"{ksw_total:,.1f} kg", f"{ksw_rate:.2f} g / diner")
k3.metric("Combined recorded waste", f"{combined_total:,.1f} kg")
k4.metric("Total diners", f"{df['DINERS'].sum():,.0f}")

st.divider()
tab_overview, tab_period, tab_menu, tab_trends, tab_data = st.tabs(["Overview", "Baseline vs Intervention", "Menu Analysis", "Waste Trends", "Data Quality"])

with tab_overview:
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Waste by category")
        cat = pd.DataFrame({"Category": ["Plate Waste", "Kitchen & Serving Waste"], "Waste (kg)": [pw_total, ksw_total]})
        fig = px.pie(cat, names="Category", values="Waste (kg)", hole=0.58)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), legend_title="")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Weighted waste per diner")
        rates = pd.DataFrame({"Category": ["Plate Waste", "Kitchen & Serving Waste"], "g per diner": [pw_rate, ksw_rate]})
        fig = px.bar(rates, x="Category", y="g per diner", text_auto=".2f")
        fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), xaxis_title="", yaxis_title="Grams per diner")
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("At a glance")
    st.write(f"Plate Waste accounts for **{pw_share:.1f}%** of the combined recorded waste; Kitchen & Serving Waste accounts for **{ksw_share:.1f}%**.")
    st.caption("Rates are weighted totals: total waste in grams divided by diners in rows where that waste category is available. Missing KSW values are not treated as zero.")

def weighted(frame):
    d = frame["DINERS"].sum()
    return pd.Series({"PW g/diner": frame["PW kg"].sum() * 1000 / d,
                      "KSW g/diner": frame["KSW kg"].sum() * 1000 / d,
                      "Total g/diner": (frame["PW kg"] + frame["KSW kg"]).sum() * 1000 / d,
                      "Days": len(frame), "Diners": d})

with tab_period:
    st.subheader("Baseline vs intervention: weighted waste per diner")
    cc = df.dropna(subset=["PW kg", "KSW kg"])  # complete cases so PW, KSW and total use the same days
    base_all = cc[cc["Period"] == "Baseline"]
    inter = cc[cc["Period"] == "Intervention"]
    if inter.empty:
        st.info("No intervention days found in this file.")
    else:
        benchmark = st.radio("Compare the intervention with",
                             ["Full baseline", "Baseline days with the same MENU codes", "Recent baseline (last 25 days)"],
                             horizontal=True)
        if benchmark == "Full baseline":
            base = base_all
        elif benchmark.startswith("Baseline days with the same"):
            base = base_all[base_all["MENU"].isin(inter["MENU"].unique())]
        else:
            base = df[df["Period"] == "Baseline"].tail(25).dropna(subset=["PW kg", "KSW kg"])
        b, i = weighted(base), weighted(inter)
        c1, c2, c3 = st.columns(3)
        for col, name in zip([c1, c2, c3], ["PW g/diner", "KSW g/diner", "Total g/diner"]):
            change = (i[name] - b[name]) / b[name] * 100
            col.metric(name.replace(" g/diner", " waste per diner").replace("PW", "Plate").replace("KSW", "Kitchen & serving"),
                       f"{i[name]:.2f} g", f"{change:+.1f}% vs {b[name]:.2f} g", delta_color="inverse")
        comp = pd.DataFrame({"Measure": ["Plate waste (PW)", "Kitchen & serving waste (KSW)", "Total waste"] * 2,
                             "Period": ["Baseline"] * 3 + ["Intervention"] * 3,
                             "g per diner": [b["PW g/diner"], b["KSW g/diner"], b["Total g/diner"],
                                             i["PW g/diner"], i["KSW g/diner"], i["Total g/diner"]]})
        fig = px.bar(comp, x="Measure", y="g per diner", color="Period", barmode="group", text_auto=".2f",
                     color_discrete_map={"Baseline": "#1F4E79", "Intervention": "#F2B705"})
        fig.update_layout(xaxis_title="", yaxis_title="Grams per diner", legend_title="", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Baseline group: {int(b['Days'])} days, {b['Diners']:,.0f} diners · Intervention: {int(i['Days'])} days, {i['Diners']:,.0f} diners. "
                   "Periods follow the dataset authors' definition (first 135 school days = baseline, final 20 = intervention). "
                   "This is an observational before-and-after comparison, not proof that the intervention caused the change.")

        st.markdown("**Menu-level change (total waste per diner)**")
        mb = base_all.groupby("MENU").apply(lambda g: (g["PW kg"] + g["KSW kg"]).sum() * 1000 / g["DINERS"].sum())
        mi = inter.groupby("MENU").apply(lambda g: (g["PW kg"] + g["KSW kg"]).sum() * 1000 / g["DINERS"].sum())
        mtab = pd.DataFrame({"Baseline g/diner": mb, "Intervention g/diner": mi}).dropna()
        mtab["Change %"] = (mtab["Intervention g/diner"] / mtab["Baseline g/diner"] - 1) * 100
        mtab = mtab.reset_index().sort_values("Change %")
        fig = px.bar(mtab, x="MENU", y="Change %", text_auto=".1f",
                     color=np.where(mtab["Change %"] > 0, "Higher", "Lower"),
                     color_discrete_map={"Higher": "#C0392B", "Lower": "#1F4E79"})
        fig.update_xaxes(type="category")
        fig.update_layout(xaxis_title="Menu code", yaxis_title="Change in total waste per diner (%)", legend_title="", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

with tab_menu:
    st.subheader("Menu code comparison")
    menu = df.groupby("MENU", dropna=False).agg(
        Days=("DATE", "count"),
        Diners=("DINERS", "sum"),
        **{"Plate Waste (kg)": ("PW kg", "sum"), "Kitchen & Serving Waste (kg)": ("KSW kg", "sum")}
    ).reset_index()
    menu["Combined recorded waste (kg)"] = menu["Plate Waste (kg)"] + menu["Kitchen & Serving Waste (kg)"]
    menu["PW g/diner"] = menu["Plate Waste (kg)"] * 1000 / menu["Diners"]
    valid_ksw = df[df["KSW kg"].notna()].groupby("MENU")["DINERS"].sum()
    menu["KSW valid diners"] = menu["MENU"].map(valid_ksw)
    menu["KSW g/diner"] = menu["Kitchen & Serving Waste (kg)"] * 1000 / menu["KSW valid diners"]
    menu["Total g/diner"] = menu["Combined recorded waste (kg)"] * 1000 / menu["KSW valid diners"]
    metric = st.radio("Rank menu codes by", ["Total g/diner", "Combined recorded waste (kg)", "Plate Waste (kg)", "Kitchen & Serving Waste (kg)", "PW g/diner"], horizontal=True)
    ranked = menu.sort_values(metric, ascending=False)
    ranked = ranked.assign(MENU=ranked["MENU"].astype("Int64").astype(str))
    fig = px.bar(ranked, x="MENU", y=metric, text_auto=".2f", title=f"Menu codes ranked by {metric}")
    fig.update_layout(xaxis_title="Menu code", yaxis_title=metric, margin=dict(t=55,b=10,l=10,r=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ranked.round(2), use_container_width=True, hide_index=True)
    st.caption("Menu codes identify menu entries; the dataset does not provide dish names. Total kilograms can be influenced by how many diners were served, so also consider per-diner rates.")

with tab_trends:
    st.subheader("Daily waste over time")
    daily = df.groupby("DATE", as_index=False).agg(
        **{"Plate Waste (kg)": ("PW kg", "sum"), "Kitchen & Serving Waste (kg)": ("KSW kg", "sum"), "Diners": ("DINERS", "sum")}
    )
    daily["Combined recorded waste (kg)"] = daily["Plate Waste (kg)"] + daily["Kitchen & Serving Waste (kg)"]
    daily["PW g/diner"] = daily["Plate Waste (kg)"] * 1000 / daily["Diners"]
    daily["KSW g/diner"] = daily["Kitchen & Serving Waste (kg)"] * 1000 / daily["Diners"]
    selected = st.selectbox("View trend", ["Combined recorded waste (kg)", "Plate Waste (kg)", "Kitchen & Serving Waste (kg)", "PW g/diner", "KSW g/diner"])
    fig = px.line(daily, x="DATE", y=selected, markers=True)
    inter_dates = df.loc[df["Period"] == "Intervention", "DATE"]
    if len(inter_dates):
        fig.add_vrect(x0=inter_dates.min(), x1=inter_dates.max(), fillcolor="#F2B705", opacity=0.18, line_width=0)
        fig.add_annotation(x=inter_dates.min(), y=1, yref="paper", text="Intervention period", showarrow=False, xanchor="left", yanchor="bottom")
    fig.update_layout(xaxis_title="Date", yaxis_title=selected, margin=dict(t=20,b=10,l=10,r=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Daily trends are descriptive. They do not establish why waste changed or prove an intervention effect.")

with tab_data:
    st.subheader("Data quality checks")
    q1, q2, q3 = st.columns(3)
    q1.metric("Missing KSW records", f"{df['KSW kg'].isna().sum()}")
    q2.metric("Duplicate dates", f"{df['DATE'].duplicated().sum()}")
    q3.metric("Menu codes", f"{df['MENU'].nunique()}")
    st.markdown("**Missing values by column**")
    st.dataframe(df.isna().sum().rename("Missing values").to_frame(), use_container_width=True)
    mismatch = df[(df["PW kg"].notna()) & (df["PW g"].notna()) & ((df["PW kg"]*1000 - df["PW g"]).abs() > 1)]
    if len(mismatch):
        st.warning(f"PW kg and PW g differ in {len(mismatch)} record(s). This dashboard uses PW kg consistently for Plate Waste calculations.")
        st.dataframe(mismatch[["DATE", "PW kg", "PW g"]], use_container_width=True, hide_index=True)
    st.info("The dataset does not contain dish names, ingredient costs, recipes, emissions factors, or documented intervention labels. The dashboard therefore does not estimate financial savings, carbon reductions, or causal intervention effects.")

st.divider()
st.caption("SmartPlate · Historical food-waste analysis · Data: Kuusisto, Latva & Wilén, Food waste dataset: secondary school in Finland 2024–2025 (Zenodo)")
