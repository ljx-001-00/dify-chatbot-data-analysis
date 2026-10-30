# 智能数据分析与可视化（任务 11–14）

数据来源：node2 的 MySQL

- `chat.records`：84,252 条预置客服咨询（2023-03 ~ 2024-08）
- `wechat.chathistory`：公众号真实对话（本次实训产生）

## 目录

```
data_analysis/
├── cfg.py              公共配置（数据库、停用词、自定义词典）
├── 01_clean.py         任务11  清洗与探索      → data/clean.csv
├── 02_stats.py         任务11  密度与词频      → 3 张 CSV
├── 03_lda.py           任务12  LDA 主题分析    → 2 张 CSV
├── 04_sentiment.py     任务13  情感分析        → 2 张 CSV
├── 05_viz.py           任务14  可视化          → 5 张 PNG
├── run_all.py          一键全跑
├── data/               中间数据（clean.csv、tokens.pkl）
└── output/             交付物（CSV + figs/ 图片）
```

## 运行

```bash
pip install pandas numpy jieba gensim snownlp matplotlib scikit-learn wordcloud
python run_all.py
```

> 本机 pip 走 HTTPS 会失败，用 HTTP 镜像：
> `-i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com`

## 产出清单（可直接放报告/演示）

| 文件 | 内容 | 用于 |
|---|---|---|
| `output/聊天密度小时分布.csv` | 24 行：小时 / 消息数 / 占比 | 排班依据 |
| `output/聊天密度月分布.csv` | 近 12 月：月份 / 消息数 / 占比 | 业务增长 |
| `output/聊天词语频次数据.csv` | TOP100 词语与频次 | 词云、需求热点 |
| `output/LDA主题词表.csv` | 每主题 TOP10 词及权重 | 主题命名依据 |
| `output/月度主题趋势数据.csv` | 月份 × 主题占比 | 关注点迁移 |
| `output/情感分布.csv` | 正/中/负 数量与占比 | 满意度基线 |
| `output/情感趋势数据.csv` | 月份 × 情感占比 | 舆情预警 |
| `output/figs/*.png` | 5 张图 | 答辩展示 |

## 关键结论（跑完自动打印，抄进报告）

1. 咨询量在 9–22 点占绝对主体，夜间 0–6 点极少 → 人工客服可只排白天，夜间交给 AI 助手
2. 2024 年起月均咨询量约为 2023 年的 1.9 倍 → 业务量翻倍，人力没同比增加，所以必须上 AI
3. 高频词集中在安装、保修、漏水、优惠券 → 四个主题与业务痛点完全对应
4. 负面情感占比低（客服记录多为中性咨询而非投诉）→ 情感分析的价值在"趋势突变"而非绝对值
