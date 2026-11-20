"""Figures and atomic, self-contained result bundles."""
import csv
import io
import json
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap

TEAL = "#00786e"
GOLD = "#ca7333"


def summary(result, split):
    names, raw, states, _, _ = result
    rows = []
    for i, name in enumerate(names):
        valid = states[:, i] >= 0
        low = states[:, i] == 0
        starts = low & ~np.r_[False, low[:-1]]
        rows.append((name, "Control" if i < split else "Experimental", int(valid.sum()),
                     int((~valid).sum()), float(np.nanmean(raw[:, i])), int(low.sum()),
                     float(100 * low.sum() / valid.sum()), int(starts.sum())))
    return rows


def make_figure(result, split, dt, mouse=None):
    names, raw, states, prob, _ = result
    fig = Figure(figsize=(8, 5), dpi=100, layout="constrained")
    unit = "Time (s)" if dt else "Sample (zero-based)"
    step = dt or 1.
    if mouse is None:
        ax, chart = fig.subplots(1, 2, width_ratios=[2, 1])
        heat = np.ma.masked_less(states.T, 0)
        cmap = ListedColormap([TEAL, "#e1eae7"])
        cmap.set_bad("#aa8c9c")
        ax.imshow(heat, aspect="auto", interpolation="nearest", cmap=cmap, vmin=0, vmax=1,
                  extent=(0, len(raw)*step, len(names)+.5, .5))
        ax.axhline(split+.5, color=GOLD, linewidth=1.5)
        ax.set(xlabel=unit, ylabel="Mouse (column order)", title="State map · teal = low motion")
        ax.yaxis.get_major_locator().set_params(integer=True)
        rows = summary(result, split)
        for j, group in enumerate((rows[:split], rows[split:])):
            values = [x[6] for x in group]
            offsets = np.zeros(1) if len(values) == 1 else np.linspace(-.12, .12, len(values))
            chart.scatter(j + offsets, values, color=[TEAL, GOLD][j], s=28)
            chart.plot([j-.23, j+.23], [np.mean(values)]*2, color="#182d31", lw=2)
        chart.set(xticks=[0, 1], xticklabels=["Control", "Experimental"], xlim=(-.5,1.5),
                  ylim=(-2,102), ylabel="Low-motion samples (%)", title="Mice and group means")
        chart.grid(axis="y", alpha=.2)
    else:
        ax, chart = fig.subplots(2, 1, sharex=True, height_ratios=[2,1])
        t = np.arange(len(raw))*step
        ax.plot(t, raw[:, mouse], color=TEAL, lw=.8)
        ax.set(title=f"Motion index  /  column {mouse+1}", ylabel="Motion index")
        chart.plot(t, prob[:, mouse], color="#345a75", lw=.9, label="Posterior P(low)")
        chart.step(t, np.where(states[:,mouse]<0, np.nan, states[:,mouse]==0),
                   where="post", color=GOLD, alpha=.75, lw=.8, label="Viterbi low")
        chart.set(ylabel="Low motion", xlabel=unit, ylim=(-.05,1.05))
        chart.legend(loc="upper right", ncol=2, fontsize=8)
    for ax in fig.axes:
        ax.spines[["top","right"]].set_visible(False)
        ax.tick_params(labelsize=8)
        ax.title.set_fontsize(11)
    return fig


def export_bundle(target, result, split, dt, mouse):
    names, raw, states, prob, meta = result
    target = Path(target)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
        staging = Path(f.name)
    try:
        with ZipFile(staging, "w", ZIP_DEFLATED) as z:
            def table(name, header, rows):
                with z.open(name, "w") as binary, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(header)
                    writer.writerows(rows)
            rows = summary(result, split)
            table("mice.csv", ["mouse","group","valid","missing","mean_motion","low_samples","low_pct","low_bouts"], rows)
            groups = []
            for group in (rows[:split], rows[split:]):
                values = [r[6] for r in group]
                groups.append((group[0][1],len(group),np.mean(values),np.std(values,ddof=1) if len(group)>1 else ""))
            table("groups.csv", ["group","mice","mean_low_pct","sd_low_pct"], groups)
            def observations():
                for j, name in enumerate(names):
                    for i in range(len(raw)):
                        state = states[i,j]
                        yield (name, i, i*dt if dt else "", raw[i,j] if state>=0 else "",
                               ("low","high")[state] if state>=0 else "", prob[i,j] if state>=0 else "")
            table("observations.csv", ["mouse","sample","seconds","motion_index","state","p_low"], observations())
            metadata = dict(meta, control_columns=split, seconds_per_sample=dt, mice=names, trace_mouse=names[mouse])
            z.writestr("model.json", json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False))
            for label, index in (("groups",None),("trace",mouse)):
                fig = make_figure(result, split, dt, index)
                for ext in ("png","svg"):
                    buffer = io.BytesIO()
                    fig.savefig(buffer, format=ext, dpi=300)
                    z.writestr(f"{label}.{ext}", buffer.getvalue())
                fig.clear()
        staging.replace(target)
    finally:
        staging.unlink(missing_ok=True)

