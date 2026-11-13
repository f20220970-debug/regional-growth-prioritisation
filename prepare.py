"""Clean the raw indicators and score countries.

Outputs data/clean/indicators.csv (one row per country, raw values with the year used)
and data/clean/scores.csv (pillar scores 0-100 and ranks under three weighting scenarios).
Run: python prepare.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"

COUNTRIES = {
    "IND": "India", "IDN": "Indonesia", "VNM": "Vietnam", "THA": "Thailand", "MYS": "Malaysia",
    "PHL": "Philippines", "BGD": "Bangladesh", "SAU": "Saudi Arabia", "ARE": "United Arab Emirates",
    "QAT": "Qatar", "EGY": "Egypt", "TUR": "Turkiye", "NGA": "Nigeria", "KEN": "Kenya",
    "ZAF": "South Africa", "MEX": "Mexico", "BRA": "Brazil", "CHL": "Chile", "COL": "Colombia",
    "POL": "Poland", "USA": "United States", "DEU": "Germany", "CHN": "China", "JPN": "Japan",
    "KOR": "South Korea",
}
REGION = {
    "IND": "South Asia", "BGD": "South Asia", "IDN": "Southeast Asia", "VNM": "Southeast Asia",
    "THA": "Southeast Asia", "MYS": "Southeast Asia", "PHL": "Southeast Asia", "SAU": "Middle East",
    "ARE": "Middle East", "QAT": "Middle East", "EGY": "Africa", "NGA": "Africa", "KEN": "Africa",
    "ZAF": "Africa", "TUR": "Europe", "POL": "Europe", "DEU": "Europe", "MEX": "Latin America",
    "BRA": "Latin America", "CHL": "Latin America", "COL": "Latin America", "USA": "North America",
    "CHN": "East Asia", "JPN": "East Asia", "KOR": "East Asia",
}
# Analyst view of the Honeywell automation play in each market (judgment, not data).
PLAY = {
    "IND": "Buildings and data centres; process automation for chemicals and refining",
    "IDN": "Process automation for nickel, refining and LNG",
    "VNM": "Factory and warehouse automation for relocating manufacturers",
    "THA": "Petrochemicals and buildings", "MYS": "LNG, semiconductors back-end, buildings",
    "PHL": "Buildings, airports, power", "BGD": "Power and textiles; early stage",
    "SAU": "LNG, refining and giga-project buildings", "ARE": "Smart buildings, refining, LNG",
    "QAT": "LNG expansion (North Field)", "EGY": "Refining, fertiliser, new cities",
    "TUR": "Process industries and buildings", "NGA": "Oil and gas, early stage",
    "KEN": "Infrastructure, early stage", "ZAF": "Mining and process industries",
    "MEX": "Nearshoring factory automation", "BRA": "Oil and gas, pulp and paper",
    "CHL": "Mining, green hydrogen", "COL": "Oil and gas, buildings",
    "POL": "Manufacturing and energy transition", "USA": "Benchmark: largest installed base",
    "DEU": "Benchmark: mature industrial base", "CHN": "Benchmark: largest but local competition",
    "JPN": "Benchmark: mature", "KOR": "Semiconductors, batteries",
}

SCENARIOS = {
    "Base": {"size": 0.25, "growth": 0.25, "investment": 0.20, "industry": 0.15, "urbanisation": 0.05, "stability": 0.10},
    "Growth chaser": {"size": 0.10, "growth": 0.40, "investment": 0.25, "industry": 0.10, "urbanisation": 0.10, "stability": 0.05},
    "Low risk": {"size": 0.30, "growth": 0.15, "investment": 0.15, "industry": 0.15, "urbanisation": 0.00, "stability": 0.25},
}


def load(code):
    d = pd.read_csv(RAW / f"{code}.csv")
    d = d[d["Country Code"].isin(COUNTRIES)].dropna(subset=["Value"])
    return d


def latest(code, min_year=2019):
    d = load(code)
    d = d[d["Year"] >= min_year].sort_values("Year").groupby("Country Code").tail(1)
    return d.set_index("Country Code")[["Value", "Year"]]


def avg(code, start, end):
    d = load(code)
    d = d[(d["Year"] >= start) & (d["Year"] <= end)]
    return d.groupby("Country Code")["Value"].mean()


def change(code, start, end):
    d = load(code).set_index(["Country Code", "Year"])["Value"]
    out = {}
    for c in COUNTRIES:
        try:
            out[c] = d.loc[(c, end)] - d.loc[(c, start)]
        except KeyError:
            out[c] = np.nan
    return pd.Series(out)


def minmax(s, invert=False, lo_q=0.05, hi_q=0.95):
    s = s.clip(s.quantile(lo_q), s.quantile(hi_q))
    z = (s - s.min()) / (s.max() - s.min()) * 100
    return 100 - z if invert else z


def build():
    CLEAN.mkdir(parents=True, exist_ok=True)
    gdp = latest("ny.gdp.mktp.cd")
    ind = latest("nv.ind.totl.zs")
    gcf = latest("ne.gdi.totl.zs")
    tech = latest("nv.mnf.tech.zs.un", 2018)
    urb = latest("sp.urb.totl.in.zs")
    df = pd.DataFrame(index=list(COUNTRIES))
    df["country"] = pd.Series(COUNTRIES)
    df["region"] = pd.Series(REGION)
    df["gdp_usd_bn"] = gdp["Value"] / 1e9
    df["gdp_year"] = gdp["Year"]
    df["industry_pct_gdp"] = ind["Value"]
    df["industry_va_usd_bn"] = df["gdp_usd_bn"] * df["industry_pct_gdp"] / 100
    df["gdp_growth_avg_2021_25"] = avg("ny.gdp.mktp.kd.zg", 2021, 2025)
    df["gdp_growth_2025"] = latest("ny.gdp.mktp.kd.zg")["Value"]
    df["capital_formation_pct_gdp"] = gcf["Value"]
    df["capital_formation_year"] = gcf["Year"]
    df["medhigh_tech_mfg_pct"] = tech["Value"]
    df["medhigh_tech_year"] = tech["Year"]
    df["urban_pct"] = urb["Value"]
    df["urban_change_pp_2015_25"] = change("sp.urb.totl.in.zs", 2015, 2025)
    df["elec_kwh_pc"] = latest("eg.use.elec.kh.pc", 2015)["Value"]
    df["inflation_avg_2023_25"] = avg("fp.cpi.totl.zg", 2023, 2025)
    df["play"] = pd.Series(PLAY)
    df.index.name = "iso3"

    # Pillar scores 0-100 (missing values flagged, scored at the median, never zero)
    df["missing"] = df[["industry_va_usd_bn", "gdp_growth_avg_2021_25", "capital_formation_pct_gdp",
                        "medhigh_tech_mfg_pct", "urban_change_pp_2015_25", "inflation_avg_2023_25"]].isna().sum(axis=1)
    fill = lambda s: s.fillna(s.median())
    sc = pd.DataFrame(index=df.index)
    sc["size"] = minmax(np.log10(fill(df["industry_va_usd_bn"])))
    sc["growth"] = minmax(fill(df["gdp_growth_avg_2021_25"]))
    sc["investment"] = minmax(fill(df["capital_formation_pct_gdp"]))
    sc["industry"] = minmax(fill(df["medhigh_tech_mfg_pct"]))
    sc["urbanisation"] = minmax(fill(df["urban_change_pp_2015_25"]))
    sc["stability"] = minmax(fill(df["inflation_avg_2023_25"]).abs(), invert=True)
    for name, w in SCENARIOS.items():
        assert abs(sum(w.values()) - 1) < 1e-9, name
        sc[f"score_{name}"] = sum(sc[k] * v for k, v in w.items())
        sc[f"rank_{name}"] = sc[f"score_{name}"].rank(ascending=False, method="min").astype(int)
    ranks = sc[[c for c in sc if c.startswith("rank_")]]
    sc["rank_spread"] = ranks.max(axis=1) - ranks.min(axis=1)
    # leave-one-pillar-out test on the base case
    base = SCENARIOS["Base"]
    worst = pd.Series(0, index=sc.index)
    for drop in base:
        w = {k: v for k, v in base.items() if k != drop}
        tot = sum(w.values())
        r = (sum(sc[k] * v / tot for k, v in w.items())).rank(ascending=False, method="min")
        worst = np.maximum(worst, (r - sc["rank_Base"]).abs())
    sc["max_rank_move_drop_one_pillar"] = worst.astype(int)

    df.round(3).to_csv(CLEAN / "indicators.csv")
    out = df[["country", "region", "play", "missing"]].join(sc.round(1)).sort_values("rank_Base")
    out.to_csv(CLEAN / "scores.csv")
    return df, out


if __name__ == "__main__":
    _, s = build()
    cols = ["country", "score_Base", "rank_Base", "rank_Growth chaser", "rank_Low risk", "rank_spread", "max_rank_move_drop_one_pillar"]
    print(s[cols].to_string())
