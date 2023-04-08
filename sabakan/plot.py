import hashlib
import json
from pathlib import Path
from pprint import pprint

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def name2color(name):
    return "#" + hashlib.sha256(name.encode()).hexdigest()[:6]


def plot(gpu):
    if len(gpu["processes"]) == 0:
        fig = go.Figure()
        fig.update_xaxes(range=[0, gpu["memory.total"]], tickfont=dict(size=16))
        fig.update_yaxes(range=[0, 1], showticklabels=False)
        fig.update_layout(height=120, margin=dict(l=10, r=10, t=8, b=8), dragmode=False)
        return fig, pd.DataFrame(
            {
                "pid": pd.Series(dtype=int),
                "gpu_memory_usage": pd.Series(dtype=float),
            }
        )

    proc = pd.DataFrame(gpu["processes"]).sort_values(
        "gpu_memory_usage", ascending=False
    )
    proc["color"] = proc["username"].apply(name2color)
    widths = proc["gpu_memory_usage"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=np.ones_like(widths),
            x=np.cumsum(widths) - widths,
            width=widths,
            offset=0,
            marker=dict(color=proc["color"], line=dict(width=1, color="lightgray")),
            customdata=proc["username"].values,
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    fig.update_xaxes(range=[0, gpu["memory.total"]], tickfont=dict(size=16))
    fig.update_yaxes(range=[0, 1], showticklabels=False)
    fig.update_layout(
        height=120,
        margin=dict(l=10, r=10, t=8, b=8),
        dragmode=False,
        hoverlabel=dict(font=dict(size=20)),
    )

    return fig, proc


if __name__ == "__main__":
    data = json.loads(Path("sample/multi_gpustat.json").read_text())
    gpu = json.loads(data["kaya1"]["stdout"])["gpus"][0]
    fig = plot(gpu)
    fig.show()
