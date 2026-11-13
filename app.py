"""Regional growth prioritisation dashboard (Streamlit).

Run locally:  pip install -r requirements.txt  then  streamlit run app.py
Deploy free: push this repo to GitHub, then share.streamlit.io > New app > pick app.py.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from prepare import CLEAN, SCENARIOS, build

st.set_page_config(page_title="Regional growth prioritisation", layout="wide")

if not (CLEAN / "scores.csv").exists():
    build()
ind = pd.read_csv(CLEAN / "indicators.csv").set_index("iso3")
sc = pd.read_csv(CLEAN / "scores.csv").set_index("iso3")
PILLARS = ["size", "growth", "investment", "industry", "urbanisation", "stability"]
LABELS = {
    "size": "Size: industry value added (log)",
    "growth": "Growth: real GDP growth, avg 2021-25",
    "investment": "Investment: capital formation, % of GDP",
    "industry": "Sophistication: medium/high-tech share of manufacturing",
    "urbanisation": "Urbanisation: change in urban share, 2015-25",
    "stability": "Stability: low inflation, avg 2023-25",
}

st.title("Where should an industrial-automation company grow next?")
st.caption("25 countries scored on 6 World Bank pillars (latest data to 2025). Move the weights; the ranking updates. "
           "Built by Pavitra Seth as Honeywell PS-II preparation. Public data, not affiliated with Honeywell.")

with st.sidebar:
    st.header("Weights")
    preset = st.selectbox("Start from a scenario", list(SCENARIOS), index=0)
    raw = {p: st.slider(LABELS[p], 0, 50, int(SCENARIOS[preset][p] * 100), 5, key=f"{preset}-{p}") for p in PILLARS}
    total = sum(raw.values()) or 1
    w = {p: v / total for p, v in raw.items()}
    st.caption(f"Weights are re-scaled to sum to 100% (current raw total: {sum(raw.values())}).")
    hide_bench = st.checkbox("Hide mature benchmarks (US, Germany, Japan, China, South Korea)", value=False)

df = sc.copy()
df["score"] = sum(df[p] * w[p] for p in PILLARS)
if hide_bench:
    df = df.drop(index=[c for c in ["USA", "DEU", "JPN", "CHN", "KOR"] if c in df.index])
df["rank"] = df["score"].rank(ascending=False, method="min").astype(int)
df = df.sort_values("rank")

top = df.head(5)
cols = st.columns(5)
for col, (iso, row) in zip(cols, top.iterrows()):
    col.metric(f"#{row['rank']} {row['country']}", f"{row['score']:.0f} / 100")

left, right = st.columns([3, 2])
with left:
    fig = px.treemap(df.reset_index(), path=[px.Constant("All"), "region", "country"], values="score",
                     color="score", color_continuous_scale="Blues", range_color=(0, 100),
                     title="Attractiveness score by region (box size and colour = score)")
    fig.update_traces(texttemplate="%{label}", hovertemplate="%{label}: %{color:.0f}<extra></extra>", root_color="white")
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=380)
    st.plotly_chart(fig, width="stretch")
with right:
    bar = px.bar(df.head(15).iloc[::-1], x="score", y="country", orientation="h", color="region",
                 title="Top 15", labels={"score": "Score", "country": ""})
    bar.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), legend_title_text="",
                      yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(bar, width="stretch")

c1, c2 = st.columns(2)
with c1:
    scat = px.scatter(df.reset_index().join(ind[["industry_va_usd_bn"]], on="iso3"), x="stability", y="growth",
                      size="industry_va_usd_bn", color="region", hover_name="country", text="iso3",
                      title="Growth vs stability (bubble = industry value added)", size_max=35,
                      labels={"stability": "Stability score", "growth": "Growth score"})
    scat.update_traces(textposition="top center")
    scat.update_layout(height=420, margin=dict(l=0, r=0, t=40, b=0), legend_title_text="")
    st.plotly_chart(scat, width="stretch")
with c2:
    st.subheader("Is the ranking robust?")
    rob = sc[["country", "rank_Base", "rank_Growth chaser", "rank_Low risk", "rank_spread", "max_rank_move_drop_one_pillar"]]
    rob = rob.rename(columns={"rank_Base": "Base", "rank_Growth chaser": "Growth chaser", "rank_Low risk": "Low risk",
                              "rank_spread": "Spread", "max_rank_move_drop_one_pillar": "Max move if one pillar dropped"})
    st.dataframe(rob.sort_values("Base").head(12), width="stretch", height=420)

st.subheader("Country card")
pick = st.selectbox("Country", df["country"].tolist(), index=0)
iso = df.index[df["country"] == pick][0]
r = ind.loc[iso]
a, b, c = st.columns(3)
a.metric("GDP (US$ bn)", f"{r['gdp_usd_bn']:,.0f}", help=f"Year {int(r['gdp_year'])}")
a.metric("Industry value added (US$ bn)", f"{r['industry_va_usd_bn']:,.0f}")
b.metric("Real GDP growth, avg 2021-25", f"{r['gdp_growth_avg_2021_25']:.1f}%")
b.metric("Capital formation, % of GDP", "n/a" if pd.isna(r["capital_formation_pct_gdp"]) else f"{r['capital_formation_pct_gdp']:.1f}%")
c.metric("Medium/high-tech share of manufacturing", f"{r['medhigh_tech_mfg_pct']:.0f}%")
c.metric("Inflation, avg 2023-25", f"{r['inflation_avg_2023_25']:.1f}%")
st.markdown(f"**Honeywell play (analyst view):** {r['play']}")
radar = px.line_polar(pd.DataFrame({"pillar": [LABELS[p].split(':')[0] for p in PILLARS],
                                    "score": [sc.loc[iso, p] for p in PILLARS]}),
                      r="score", theta="pillar", line_close=True, range_r=(0, 100))
radar.update_traces(fill="toself")
radar.update_layout(height=360, margin=dict(l=40, r=40, t=20, b=20))
st.plotly_chart(radar, width="stretch")

st.caption("Data: World Bank World Development Indicators (via the datasets/world-development-indicators mirror). "
           "Scores are min-max scaled 0-100 after capping the top and bottom 5%; missing values take the median and are flagged. "
           "See README for method and limitations.")
