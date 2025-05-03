#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import sys
import os
from logging import getLogger, StreamHandler, FileHandler, Formatter, DEBUG, INFO
import click
import pandas as pd
import plotly.express as px

os.environ["PATH"] = "/Users/tfuku/Tools/miniforge3/envs/py313/bin:" + os.environ["PATH"]

#     ____________________
#____/ [*] logger設定      \____________________
#
def setup_logger(name, logfile='logger_log.log'):
    logger = getLogger(__name__)
    logger.setLevel(INFO)


    # create file handler with a info log level
    fh = FileHandler(logfile)
    fh.setLevel(DEBUG)
    fh_formatter = Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # create console handler with a info log level
    ch = StreamHandler()
    ch.setLevel(INFO)
    ch_formatter = Formatter('%(asctime)s - %(levelname)s - %(message)s', '%y-%m-%d %h:%m:%s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    return logger

logger = setup_logger(__name__)




#     ____________________
#____/ [*] click設定       \____________________
#

@click.command()
@click.option('--csv', '-c', required=True, type=str)
def run(csv):
    create_graph(csv)


#     ____________________
#____/ [*] functions      \____________________
#
def create_graph(csv):

    df = pd.read_csv(csv, parse_dates=["Date"])

    # グラフの見た目の共通設定
    common_layout = dict(
        plot_bgcolor="white",
        title=dict(
            x=0.5,
            font=dict(size=24, family="Arial", color="black")
        ),
        xaxis=dict(
            title=dict(
                text="Date",
                font=dict(size=20, family="Arial", color="black"),
            ),
            gridcolor="lightgray",
            gridwidth=1,
            griddash="dot"
        ),
        yaxis=dict(
            title=dict(
                text="Total Area",
                font=dict(size=20, family="Arial", color="black"),
            ),
            gridcolor="lightgray",
            gridwidth=1,
            griddash="dot",
            zeroline=True,
            zerolinecolor="gray"
        ),
        margin=dict(t=100)
    )    

    # グラフ作成
    fig = px.line(
        df,
        x="Date",
        y="Total Area",
        color="target module",
        markers=True,
        title="Total Area Over Time by Target Module",
        hover_data=["Impl-SfM", "Design-SfM"]
    )

    # グラフの共通の見た目の更新
    fig.update_layout(common_layout)

    # グラフの見た目、個別対応
    fig.update_layout(
        yaxis=dict(
            range=[0,df["Total Area"].max() * 1.1]
        )
    )

    # マーカーサイズの変更
    fig.update_traces(marker=dict(size=8))

    # HTML出力（CDN使用）
    fig.write_html("total_area_plot.html", include_plotlyjs="cdn")

    # PNG出力（kaleidoが必要）
    fig.write_image("total_area_plot.png")

    del fig

    for module, tmp_df in df.groupby("target module"):

        # グラフ作成
        fig = px.line(
            tmp_df,
            x="Date",
            y="Total Area",
            color="target module",
            markers=True,
            title=f"Total Area Over Time - {module}",
            hover_data=["Impl-SfM", "Design-SfM"]
        )

        # グラフの共通の見た目の更新
        fig.update_layout(common_layout)

        # グラフの見た目、個別対応
        fig.update_layout(
            yaxis=dict(
                range=[0,tmp_df["Total Area"].max() * 1.1]
            )
        )

        # マーカーサイズの変更
        fig.update_traces(marker=dict(size=8))

        # HTML出力（CDN使用）
        fig.write_html(f"{module}_area_plot.html", include_plotlyjs="cdn")

        # PNG出力（kaleidoが必要）
        fig.write_image(f"{module}_area_plot.png")

        del fig


if __name__ == '__main__':
    run()


