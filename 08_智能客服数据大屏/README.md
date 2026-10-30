# 智能客服数据大屏 · 整合运行包

热水器行业智能客服项目「数据分析 + 可视化大屏」一站式整合目录，**双击 `启动大屏.cmd` 即可运行**。

> 只想看效果、不想装环境？访问 GitHub Pages 静态版：
> https://ljx-001-00.github.io/dify-chatbot-data-analysis/
>
> 静态版由 `dashboard\export_static.py` 把 Flask 版导成纯静态站点（`docs/`），数据更新后重跑该脚本即可。

## 目录结构

```
智能客服数据大屏\
├── 启动大屏.cmd        ← 一键启动（自动打开浏览器 http://127.0.0.1:5001）
├── requirements.txt    ← Python 依赖清单（说明见下）
├── dashboard\          ← 大屏代码（Flask + ECharts）
│   ├── app.py              主程序：读 CSV → /api/dashboard → 渲染页面
│   ├── templates\index.html
│   └── static\             echarts.min.js / echarts-wordcloud.min.js / css / js / img
├── data_analysis\      ← 数据分析代码（独立文件夹，01~17 号流水线脚本）
│   ├── run_all.py          一键跑完整条分析流水线
│   ├── cfg.py              数据库与词表配置（MySQL: 192.168.1.10）
│   ├── datacube_export\    分析产出的 7 张 CSV —— 大屏的数据来源
│   └── output\             图表与词云图片产物
├── wechat_bot\         ← 微信公众号机器人（项目其他代码）
│   ├── wechat_public_bot.py   Flask :80，安全模式对接 Dify 工作流
│   ├── price_router.py        价格路由
│   └── init_products.py / check_products.py / wechat_dify_server.py
└── mysql_mcp\          ← MySQL MCP 数据库服务（项目其他代码）
    ├── mysql_server_nodep.py  零依赖版（推荐），端口 8095，端点 /mcp
    └── test_mcp*.py           联调测试脚本
```

## 快速开始

### 方式一：双击启动（最简单）
双击 **`启动大屏.cmd`** —— 自动检查 Python、启动服务并打开浏览器。
按 `Ctrl+C` 或直接关窗口即停止服务。

### 方式二：命令行
```bat
cd /d 本目录
python dashboard\app.py
```
浏览器访问 `http://127.0.0.1:5001`。换端口：`set PORT=5002` 后再启动。

### 方式三：PyCharm
用 PyCharm 打开本目录 → 直接运行 `dashboard\app.py`（解释器选系统 Python 3.10 即可，
大屏只依赖 Flask，已装好）。

## 依赖说明

> 本仓库为控制体积，**未包含**原交付包里的 `libs\`（约 400 MB 离线依赖）和 `.venv\`。依赖按下面的清单自行安装即可。

- **大屏（dashboard）**：只需 `flask`，`pip install flask` 后即可运行。
- **数据分析（data_analysis）**：依赖 jieba / pandas / gensim / snownlp / matplotlib / pymysql 等，
  执行 `pip install -r requirements.txt` 安装。
  重跑分析需要能连上 MySQL（`192.168.1.10`，见 `data_analysis\cfg.py`，可用 `MYSQL_HOST` / `MYSQL_PASSWORD` 环境变量覆盖）。

## 数据流

```
MySQL chat.records（22575 条）
   → data_analysis\run_all.py（清洗/分词/情感/LDA主题/词频…）
   → data_analysis\datacube_export\*.csv（7 张）
   → dashboard\app.py 读 CSV → /api/dashboard → 大屏渲染
```

日常演示**不需要**重跑分析：CSV 已随包附带，直接启动大屏即可。

## 大屏功能（本版更新）

- 中间主视觉：**客户之声 · 高频词云**（echarts-wordcloud，60 词，悬停显示词频）
- 左列第三面板：**月度主题趋势 · 五大诉求演变** —— 已去掉堆叠、Y 轴按数据范围自适应
  （不再从 0 起），月度变化幅度清晰可见
- 其余：情感分布双层环图、诉求主题玫瑰图、24 小时密度、月度消息量、情感趋势、运行洞察日志
