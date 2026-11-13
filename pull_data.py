"""Download the World Bank indicators used by the dashboard into data/raw/.

Source: World Development Indicators, via the public datasets/world-development-indicators
mirror on GitHub (one CSV per indicator: Country Name, Country Code, Year, Value).
Official alternative: pip install wbgapi, then wb.data.DataFrame(code, economy=..., time=...).
Run: python pull_data.py
"""
from pathlib import Path
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/datasets/world-development-indicators/main/indicators/{code}/data.csv"

INDICATORS = {
    "ny.gdp.mktp.cd": "GDP (current US$)",
    "ny.gdp.mktp.kd.zg": "GDP growth (annual %)",
    "nv.ind.totl.zs": "Industry, value added (% of GDP)",
    "ne.gdi.totl.zs": "Gross capital formation (% of GDP)",
    "sp.urb.totl.in.zs": "Urban population (% of total)",
    "nv.mnf.tech.zs.un": "Medium and high-tech manufacturing (% of manufacturing value added)",
    "eg.use.elec.kh.pc": "Electric power consumption (kWh per capita)",
    "fp.cpi.totl.zg": "Inflation, consumer prices (annual %)",
    "sp.pop.totl": "Population, total",
}


def main():
    out = Path(__file__).parent / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    for code, name in INDICATORS.items():
        with urlopen(BASE.format(code=code), timeout=60) as r:
            data = r.read()
        (out / f"{code}.csv").write_bytes(data)
        print(f"{code:<22} {len(data) / 1024:>7.0f} KB  {name}")


if __name__ == "__main__":
    main()
