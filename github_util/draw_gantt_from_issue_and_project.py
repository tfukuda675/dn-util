#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import pandas as pd
import plotly.express as px

df = pd.DataFrame(
    {
        "issues": ["A", "A", "B", "B"],
        "type": ["Baseline", "Actual", "Baseline", "Actual"],
        "start": ["2025-01-01", "2025-01-03", "2025-02-01", "2025-02-05"],
        "end": ["2025-01-10", "2025-01-13", "2025-02-05", "2025-02-11"],
    }
)

df["start"] = pd.to_datetime(df["start"])
df["end"] = pd.to_datetime(df["end"])

fig = px.timeline(
    df,
    x_start="start",
    x_end="end",
    y="project",
    color="type",
    color_discrete_map={"Baseline": "lightgray", "Actual": "steelblue"},
)

fig.update_layout(
    barmode="group",
    bargap=0.2,
    bargroupgap=0.1,
    title="px.timeline で Baseline/Actual 並列表示",
    height=len(df["project"].unique()) * 120,
    yaxis=dict(
        categoryorder="category ascending",
    ),
)

fig.update_traces(width=0.4)

fig.show()
