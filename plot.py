import json
from pathlib import Path
from pprint import pprint

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot(gpu):
    pprint(gpu)

    if len(gpu["processes"]) == 0:
        fig = go.Figure()
        fig.update_xaxes(range=[0, gpu["memory.total"]])
        fig.update_yaxes(range=[0, 1])
        fig.update_layout(height=100, margin=dict(l=10, r=10, t=20, b=20))
        return fig

    proc = pd.DataFrame(gpu["processes"]).sort_values(
        "gpu_memory_usage", ascending=False
    )
    widths = proc["gpu_memory_usage"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=np.ones_like(widths), x=np.cumsum(widths) - widths, width=widths, offset=0
        )
    )
    fig.update_xaxes(range=[0, gpu["memory.total"]])
    fig.update_yaxes(range=[0, 1])
    fig.update_layout(height=100, margin=dict(l=10, r=10, t=10, b=10))
    # FIXME: インタラクティブ操作をさせない
    return fig


if __name__ == "__main__":
    data = json.loads(Path("sample/multi_gpustat.json").read_text())
    gpu = json.loads(data["kaya1"]["stdout"])["gpus"][0]
    fig = plot(gpu)
    fig.show()
