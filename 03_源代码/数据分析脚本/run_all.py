# -*- coding: utf-8 -*-
"""
一键跑完任务 11~14。

用法： python run_all.py            # 全流程
       python run_all.py --skip-lda # 跳过 LDA（调试用）
"""
import subprocess
import sys
import time

STEPS = [
    ("01_clean.py", "任务11  清洗与探索"),
    ("02_stats.py", "任务11  密度与词频"),
    ("03_lda.py", "任务12  LDA 主题分析"),
    ("04_sentiment.py", "任务13  情感分析"),
    ("05_viz.py", "任务14  可视化"),
]


def main():
    skip = "--skip-lda" in sys.argv
    t0 = time.time()
    for script, title in STEPS:
        if skip and script == "03_lda.py":
            print(f"\n>>> 跳过 {title}")
            continue
        print(f"\n{'#' * 62}\n>>> {title}  ({script})\n{'#' * 62}")
        r = subprocess.run([sys.executable, script])
        if r.returncode != 0:
            print(f"\n!! {script} 失败，已中止")
            sys.exit(r.returncode)
    print(f"\n全部完成，耗时 {time.time() - t0:.1f} 秒")
    print("结果在 output/（CSV + figs/ 图片）")


if __name__ == "__main__":
    main()
