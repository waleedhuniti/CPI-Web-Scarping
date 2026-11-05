"""TrendX(90) as the team defines it (run_date panel, 2 Oct = 100 standing for September, October = mean 2-31 Oct),
the repo variant (scripts/build_pages_site.py keeps Electricity -> 95 series), and a naive November forecast with its
random-walk interval (sigma from 03_backtest's business-day panel)."""
import numpy as np
import pandas as pd

from common import load, index_keys, jevons, trading_panel

d = load()
ik = index_keys(d)
runp = d.pivot(index="run_date", columns="key", values="price").sort_index()
i90 = jevons(runp[ik])
i95 = jevons(runp[[k for k in runp.columns if not k.startswith("Index |")]])
octm = i90[(i90.index >= "2026-10-02") & (i90.index <= "2026-10-31")].mean()
print(f"run-date TrendX(90): 2 Oct=100, 31 Oct {i90.loc['2026-10-31']:.2f}, 2 Nov {i90.iloc[-1]:.2f}, "
      f"October mean {octm:.2f}")
print(f"repo build_pages_site.py variant (95 series incl. Electricity): 2 Nov {i95.iloc[-1]:.2f} "
      f"-> electricity moves it by {i95.iloc[-1]-i90.iloc[-1]:+.2f} pts")
bd = trading_panel(d)
s = np.diff(np.log(jevons(bd[ik]).values)).std(ddof=1)
last = i90.iloc[-1]
n = 21
f = np.sqrt((n + 1) * (2 * n + 1) / (6 * n))
print(f"naive November-average forecast: {last:.2f}; 80% PI {last*np.exp(-1.2816*s*f):.2f}..{last*np.exp(1.2816*s*f):.2f}; "
      f"95% PI {last*np.exp(-1.96*s*f):.2f}..{last*np.exp(1.96*s*f):.2f}  (sigma {s*100:.3f}%/day)")
print(f"naive end-November level: 95% PI {last*np.exp(-1.96*s*np.sqrt(n)):.2f}..{last*np.exp(1.96*s*np.sqrt(n)):.2f}")
