/* =========================================================
   热水器客服 · 聊天数据智能分析大屏  —  前端逻辑
   ========================================================= */
(function () {
  "use strict";

  /* ---------------- 主题色 ---------------- */
  var C = {
    c1: "#35e2ff", c2: "#4b8bff", c3: "#9b6dff",
    c4: "#ffc44d", c5: "#ff5c7a", c6: "#2ee6a8",
    txt: "#e6f4ff", dim: "#7ea6c9",
    axis: "rgba(110,170,215,0.28)",
    split: "rgba(90,150,200,0.10)"
  };
  var PALETTE = [C.c5, C.c4, C.c1, C.c2, C.c3, C.c6];

  /* ---------------- 自适应缩放 ---------------- */
  var stage = document.getElementById("stage");

  function resize() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    var left = (window.innerWidth - 1920 * s) / 2;
    var top = (window.innerHeight - 1080 * s) / 2;
    stage.style.transform = "translate(" + left + "px," + top + "px) scale(" + s + ")";
    stage.style.transformOrigin = "top left";
  }
  window.addEventListener("resize", resize);
  resize();

  /* ---------------- 时钟 ---------------- */
  var WEEK = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
  var elClock = document.getElementById("clock");
  var elDate = document.getElementById("date");

  function tickClock() {
    var d = new Date();
    var p = function (n) { return n < 10 ? "0" + n : "" + n; };
    elClock.textContent = p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
    elDate.textContent = d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + "  " + WEEK[d.getDay()];
  }
  tickClock();
  setInterval(tickClock, 1000);

  /* ---------------- 数字滚动 ---------------- */
  function fmt(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function rollNumber(el, target, suffix, dur) {
    dur = dur || 1500;
    var from = 0;
    var t0 = null;
    var dec = (target % 1 !== 0) ? 1 : 0;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min((ts - t0) / dur, 1);
      var e = 1 - Math.pow(1 - k, 3);
      var v = from + (target - from) * e;
      el.textContent = (dec ? v.toFixed(1) : fmt(v)) + (suffix || "");
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* ---------------- 图表基础样式 ---------------- */
  function axisStyle(extra) {
    var o = {
      axisLine: { lineStyle: { color: C.axis } },
      axisTick: { show: false },
      axisLabel: { color: C.dim, fontSize: 10, fontFamily: "Bahnschrift, Microsoft YaHei" },
      splitLine: { lineStyle: { color: C.split, type: "dashed" } }
    };
    if (extra) for (var k in extra) o[k] = extra[k];
    return o;
  }

  function vGrad(color1, color2) {
    return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: color1 },
      { offset: 1, color: color2 }
    ]);
  }

  var TIP = {
    backgroundColor: "rgba(6,22,42,0.94)",
    borderColor: "rgba(53,226,255,0.42)",
    borderWidth: 1,
    padding: [7, 11],
    textStyle: { color: "#dff2ff", fontSize: 12 },
    extraCssText: "box-shadow:0 6px 24px rgba(0,0,0,.55);border-radius:4px;"
  };

  var charts = [];
  function mk(id, option) {
    var el = document.getElementById(id);
    if (!el) return null;
    var ch = echarts.init(el, null, { renderer: "canvas" });
    ch.setOption(option);
    charts.push(ch);
    return ch;
  }

  /* 自动轮播 tooltip */
  function autoplay(chart, total, delay) {
    if (!chart || total <= 1) return;
    var i = 0;
    setInterval(function () {
      chart.dispatchAction({ type: "downplay", seriesIndex: 0 });
      i = (i + 1) % total;
      chart.dispatchAction({ type: "showTip", seriesIndex: 0, dataIndex: i });
      chart.dispatchAction({ type: "highlight", seriesIndex: 0, dataIndex: i });
    }, delay || 3600);
  }

  /* =========================================================
     渲染主流程
     ========================================================= */
  function render(d) {
    var k = d.kpi || {};

    /* ---- 头部 ---- */
    document.getElementById("genAt").textContent = "更新于 " + (d.generated_at || "--");

    /* ---- KPI ---- */
    rollNumber(document.getElementById("kTotal"), k.total || 0);
    rollNumber(document.getElementById("kMonths"), k.months || 0);
    document.getElementById("kPeak").textContent = k.peak_hour || "--";
    document.getElementById("kPeakLabel").textContent =
      "咨询峰值时段 · " + fmt(k.peak_n || 0) + " 条";
    rollNumber(document.getElementById("kNeg"), k.neg_pct || 0, "%", 1600);

    /* ---- 1. 情感分布 ---- */
    var senti = (d.sentiment || []).map(function (x, i) {
      return {
        name: x.name, value: x.value,
        pct: x.pct,
        itemStyle: {
          color: x.name === "负面" ? C.c5 : (x.name === "正面" ? C.c6 : C.c4)
        }
      };
    });
    var negPct = (senti.filter(function (x) { return x.name === "负面"; })[0] || {}).pct || 0;

    mk("cSentiment", {
      tooltip: Object.assign({}, TIP, {
        trigger: "item",
        formatter: function (p) {
          return p.name + "<br/>" + fmt(p.value) + " 条 · " + p.data.pct + "%";
        }
      }),
      legend: {
        orient: "vertical",
        right: 14,
        top: "center",
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 11,
        textStyle: { color: "#b8d8ee", fontSize: 12 },
        formatter: function (name) {
          var it = senti.filter(function (x) { return x.name === name; })[0];
          if (!it) return name;
          return name + "   " + fmt(it.value) + "  (" + it.pct + "%)";
        }
      },
      series: [{
        type: "pie",
        radius: ["46%", "68%"],
        center: ["28%", "52%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "rgba(4,14,28,0.9)", borderWidth: 2 },
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          scaleSize: 6,
          itemStyle: { shadowBlur: 22, shadowColor: "rgba(53,226,255,0.5)" }
        },
        data: senti
      }, {
        type: "pie",
        radius: ["0%", "0%"],
        center: ["28%", "52%"],
        silent: true,
        label: {
          show: true,
          position: "center",
          formatter: [
            "{a|负面情绪}",
            "{b|" + negPct + "%}",
            "{c|" + fmt(k.neg_n || 0) + " 条}"
          ].join("\n"),
          rich: {
            a: { fontSize: 11, color: "#8fb8d4", lineHeight: 18 },
            b: { fontSize: 26, fontWeight: "bold", color: "#ff8ea3", lineHeight: 32 },
            c: { fontSize: 10, color: "#6f9cbb", lineHeight: 14 }
          }
        },
        data: [{ value: 0 }]
      }]
    });

    /* ---- 2. 主题分布（玫瑰图） ---- */
    var topics = (d.topic_dist || []).slice().sort(function (a, b) { return a.value - b.value; });
    mk("cTopic", {
      tooltip: Object.assign({}, TIP, {
        trigger: "item",
        formatter: function (p) { return p.name + "<br/>占比 " + p.value + "%"; }
      }),
      series: [{
        type: "pie",
        roseType: "radius",
        radius: ["26%", "72%"],
        center: ["50%", "52%"],
        itemStyle: { borderColor: "rgba(4,14,28,0.85)", borderWidth: 2, borderRadius: 3 },
        label: {
          color: "#c5e4f7",
          fontSize: 11,
          formatter: "{b}\n{d}%"
        },
        labelLine: { length: 8, length2: 8, lineStyle: { color: "rgba(110,170,215,0.45)" } },
        emphasis: { itemStyle: { shadowBlur: 20, shadowColor: "rgba(53,226,255,0.55)" } },
        data: topics.map(function (x, i) {
          return { name: x.name, value: x.value, itemStyle: { color: PALETTE[i % PALETTE.length] } };
        })
      }]
    });
  }

  /* ---------------------------------------------------------
     其余图表（依赖同一份数据）
     --------------------------------------------------------- */
  function renderMore(d) {
    var k = d.kpi || {};

    /* ---- 3. 客户之声 · 高频词云（中列大图） ---- */
    var kws = (d.keywords || []).slice(0, 60);
    var wcColors = [C.c4, C.c1, C.c5, C.c2, C.c6, C.c3];
    mk("cWordCloud", {
      tooltip: Object.assign({}, TIP, {
        formatter: function (p) { return p.name + " · " + fmt(p.value) + " 次"; }
      }),
      series: [{
        type: "wordCloud",
        shape: "circle",
        left: "center",
        top: "center",
        width: "97%",
        height: "94%",
        sizeRange: [13, 46],
        rotationRange: [-40, 40],
        rotationStep: 20,
        gridSize: 7,
        drawOutOfBound: false,
        shrinkToFit: true,
        layoutAnimation: true,
        textStyle: {
          fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
          fontWeight: "bold"
        },
        emphasis: {
          textStyle: {
            textShadowBlur: 14,
            textShadowColor: "rgba(53,226,255,0.9)"
          }
        },
        data: kws.map(function (x, i) {
          return {
            name: x.name,
            value: x.value,
            textStyle: { color: wcColors[i % wcColors.length] }
          };
        })
      }]
    });

    /* ---- 4. 月度主题趋势（多线对比 · y 轴聚焦放大幅度） ---- */
    var tt = d.topic_trend || { months: [], series: [] };
    var tcolors = [C.c1, C.c2, C.c3, C.c4, C.c6];
    var ttVals = [];
    (tt.series || []).forEach(function (s) { ttVals = ttVals.concat(s.data || []); });
    var ttLo = ttVals.length ? Math.min.apply(null, ttVals) : 0;
    var ttHi = ttVals.length ? Math.max.apply(null, ttVals) : 100;
    var ttPad = Math.max((ttHi - ttLo) * 0.45, 0.4);
    mk("cTopicTrend", {
      color: tcolors,
      tooltip: Object.assign({}, TIP, {
        trigger: "axis",
        axisPointer: { type: "line", lineStyle: { color: "rgba(53,226,255,0.5)" } },
        valueFormatter: function (v) { return (v == null ? "-" : (+v).toFixed(1) + "%"); }
      }),
      legend: {
        bottom: 0,
        left: "center",
        itemWidth: 10,
        itemHeight: 6,
        itemGap: 9,
        textStyle: { color: "#a9cfe8", fontSize: 10 }
      },
      grid: { left: 40, right: 14, top: 16, bottom: 26 },
      xAxis: axisStyle({
        type: "category",
        boundaryGap: false,
        data: tt.months,
        splitLine: { show: false },
        axisLabel: { color: C.dim, fontSize: 9.5, fontFamily: "Bahnschrift, Microsoft YaHei", interval: 1 }
      }),
      yAxis: axisStyle({
        type: "value",
        min: +(ttLo - ttPad).toFixed(1),
        max: +(ttHi + ttPad).toFixed(1),
        splitNumber: 4,
        axisLabel: { color: C.dim, fontSize: 9.5, fontFamily: "Bahnschrift, Microsoft YaHei", formatter: "{value}%" }
      }),
      series: (tt.series || []).map(function (s, i) {
        return {
          name: s.name,
          type: "line",
          smooth: 0.3,
          symbol: "circle",
          symbolSize: 4.5,
          showSymbol: true,
          lineStyle: { width: 2, color: tcolors[i], shadowBlur: 8, shadowColor: "rgba(" + hex2rgb(tcolors[i]) + ",0.45)" },
          itemStyle: { color: tcolors[i], borderColor: "#04121f", borderWidth: 1 },
          areaStyle: {
            opacity: 0.5,
            color: vGrad(
              "rgba(" + hex2rgb(tcolors[i]) + ",0.22)",
              "rgba(" + hex2rgb(tcolors[i]) + ",0.02)"
            )
          },
          emphasis: { focus: "series" },
          data: s.data
        };
      })
    });

    /* ---- 5. 月度消息量 ---- */
    var mm = d.month_msg || { months: [], counts: [], pct: [] };
    var maxM = Math.max.apply(null, mm.counts.concat([1]));
    mk("cMonth", {
      tooltip: Object.assign({}, TIP, {
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(53,226,255,0.08)" } }
      }),
      grid: { left: 52, right: 52, top: 22, bottom: 26 },
      xAxis: Object.assign({
        type: "category",
        data: mm.months
      }, axisStyle({ splitLine: { show: false } })),
      yAxis: [
        Object.assign({ type: "value", name: "条", nameTextStyle: { color: "rgba(126,166,201,0.7)", fontSize: 10 } }, axisStyle()),
        Object.assign({ type: "value", name: "%", max: 12, nameTextStyle: { color: "rgba(126,166,201,0.7)", fontSize: 10 } }, axisStyle({ splitLine: { show: false } }))
      ],
      series: [{
        name: "消息量",
        type: "bar",
        barWidth: 15,
        itemStyle: {
          borderRadius: [3, 3, 0, 0],
          color: function (p) {
            var isMax = p.value === maxM;
            return vGrad(
              isMax ? "rgba(255,196,77,0.98)" : "rgba(53,226,255,0.95)",
              isMax ? "rgba(255,120,60,0.10)" : "rgba(53,120,255,0.10)"
            );
          }
        },
        emphasis: { itemStyle: { shadowBlur: 16, shadowColor: "rgba(53,226,255,0.6)" } },
        data: mm.counts
      }, {
        name: "占比",
        type: "line",
        yAxisIndex: 1,
        smooth: 0.4,
        symbol: "circle",
        symbolSize: 5,
        lineStyle: { width: 1.8, color: C.c4 },
        itemStyle: { color: C.c4 },
        data: mm.pct
      }]
    });

    /* ---- 6. 24 小时密度 ---- */
    var hm = d.hour_msg || { hours: [], counts: [], pct: [] };
    var peakIdx = hm.counts.indexOf(Math.max.apply(null, hm.counts.concat([0])));
    mk("cHour", {
      tooltip: Object.assign({}, TIP, {
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(53,226,255,0.08)" } },
        formatter: function (p) {
          return p[0].name + " · " + fmt(p[0].value) + " 条 (" + (hm.pct[p[0].dataIndex] || 0) + "%)";
        }
      }),
      grid: { left: 46, right: 16, top: 16, bottom: 24 },
      xAxis: Object.assign({
        type: "category",
        data: hm.hours,
        axisLabel: { color: C.dim, fontSize: 9, interval: 2, fontFamily: "Bahnschrift" }
      }, axisStyle({ splitLine: { show: false } })),
      yAxis: Object.assign({ type: "value" }, axisStyle()),
      series: [{
        type: "bar",
        barWidth: "58%",
        itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: function (p) {
            return p.dataIndex === peakIdx
              ? vGrad("rgba(255,196,77,1)", "rgba(255,110,60,0.12)")
              : vGrad("rgba(53,226,255,0.92)", "rgba(53,120,255,0.08)");
          }
        },
        markPoint: {
          symbol: "pin",
          symbolSize: 26,
          label: { fontSize: 9, color: "#04101f", formatter: "峰" },
          itemStyle: { color: C.c4 },
          data: [{ name: "峰值", coord: [peakIdx, hm.counts[peakIdx] || 0], value: hm.counts[peakIdx] || 0 }]
        },
        data: hm.counts
      }]
    });

    /* ---- 7. 情感趋势 ---- */
    var st = d.sentiment_trend || { months: [] };
    var smeta = [
      { key: "负面", color: C.c5 },
      { key: "中性", color: C.c4 },
      { key: "正面", color: C.c6 }
    ];
    mk("cSentTrend", {
      tooltip: Object.assign({}, TIP, { trigger: "axis" }),
      legend: {
        top: 6,
        right: 10,
        itemWidth: 9,
        itemHeight: 9,
        itemGap: 14,
        textStyle: { color: "#a9cfe8", fontSize: 11 }
      },
      grid: { left: 44, right: 18, top: 42, bottom: 24 },
      xAxis: Object.assign({
        type: "category",
        boundaryGap: false,
        data: st.months
      }, axisStyle({ splitLine: { show: false } })),
      yAxis: Object.assign({
        type: "value",
        name: "%",
        max: 100,
        nameTextStyle: { color: "rgba(126,166,201,0.7)", fontSize: 10 }
      }, axisStyle()),
      series: smeta.map(function (s) {
        return {
          name: s.key,
          type: "line",
          smooth: 0.4,
          symbol: "circle",
          symbolSize: 4,
          showSymbol: false,
          lineStyle: { width: 1.8, color: s.color },
          itemStyle: { color: s.color },
          areaStyle: { opacity: 1, color: vGrad("rgba(" + hex2rgb(s.color) + ",0.28)", "rgba(" + hex2rgb(s.color) + ",0)") },
          data: st[s.key] || []
        };
      })
    });

    /* ---- 运行洞察 ---- */
    renderLog(d);
    /* ---- 跑马灯 ---- */
    renderTicker(d);
  }

  function hex2rgb(h) {
    h = h.replace("#", "");
    return parseInt(h.substring(0, 2), 16) + "," +
           parseInt(h.substring(2, 4), 16) + "," +
           parseInt(h.substring(4, 6), 16);
  }

  /* ---------------- 运行洞察 ---------------- */
  function renderLog(d) {
    var k = d.kpi || {};
    var list = document.getElementById("logList");
    var items = [];
    var hourPct = 0;
    if ((d.hour_msg || {}).counts) {
      var tot = d.hour_msg.counts.reduce(function (a, b) { return a + b; }, 0) || 1;
      hourPct = ((k.peak_n || 0) / tot * 100).toFixed(1);
    }
    items.push({ cls: "", html: "峰值时段 <b>" + (k.peak_hour || "--") + "</b> 共 <b>" + fmt(k.peak_n || 0) + "</b> 条，占全天 " + hourPct + "%" });
    items.push({ cls: "", html: "低谷时段 <b>" + (k.low_hour || "--") + "</b> 仅 <b>" + fmt(k.low_n || 0) + "</b> 条，夜间咨询稀疏" });
    items.push({ cls: "warn", html: "负面情绪 <b>" + (k.neg_pct || 0) + "%</b>，集中在退款 / 质量 / 物流三类" });

    var td = (d.topic_dist || []).slice().sort(function (a, b) { return b.value - a.value; });
    if (td.length) {
      items.push({ cls: "", html: "首要诉求「<b>" + td[0].name + "</b>」占主题 " + td[0].value + "%" });
    }
    if (k.month_top && k.month_top.month && k.month_top.month !== "--") {
      items.push({ cls: "", html: "最高月份 <b>" + k.month_top.month + "</b> " + fmt(k.month_top.n) + " 条，最低 <b>" + k.month_low.month + "</b> " + fmt(k.month_low.n) + " 条" });
    }

    list.innerHTML = items.map(function (it, i) {
      return '<li class="' + it.cls + '" style="animation-delay:' + (0.25 + i * 0.12) + 's">' + it.html + "</li>";
    }).join("");
  }

  /* ---------------- 底部跑马灯 ---------------- */
  function renderTicker(d) {
    var k = d.kpi || {};
    var td = (d.topic_dist || []).slice().sort(function (a, b) { return b.value - a.value; });
    var seg = [
      "累计消息 <b>" + fmt(k.total || 0) + "</b> 条",
      "覆盖 <b>" + (k.months || 0) + "</b> 个月",
      "统计窗口 <b>" + fmt(k.window_total || 0) + "</b> 条",
      "峰值 <b>" + (k.peak_hour || "--") + "</b> / " + fmt(k.peak_n || 0) + " 条",
      "负面占比 <b>" + (k.neg_pct || 0) + "%</b>",
      "识别诉求主题 <b>" + (k.topic_count || 0) + "</b> 类",
      "高频关键词 <b>" + (k.keyword_count || 0) + "</b> 个"
    ];
    if (td.length) seg.push("TOP1 诉求 <b>" + td[0].name + "</b> " + td[0].value + "%");

    var html = seg.map(function (s) { return "<span>" + s + "</span>"; }).join("");
    document.getElementById("ticker").innerHTML = html + html;
  }

  /* =========================================================
     背景粒子
     ========================================================= */
  (function particles() {
    var cv = document.getElementById("fx");
    if (!cv) return;
    var ctx = cv.getContext("2d");
    var w, h, ps = [];

    function init() {
      w = cv.width = window.innerWidth;
      h = cv.height = window.innerHeight;
      ps = [];
      var n = Math.round(w * h / 42000);
      for (var i = 0; i < n; i++) {
        ps.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 1.5 + 0.4,
          vx: (Math.random() - 0.5) * 0.22,
          vy: (Math.random() - 0.5) * 0.22,
          a: Math.random() * 0.45 + 0.15
        });
      }
    }

    var scanY = -0.2;
    function draw() {
      ctx.clearRect(0, 0, w, h);

      /* 粒子 + 近邻连线 */
      for (var i = 0; i < ps.length; i++) {
        var p = ps[i];
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, 6.2832);
        ctx.fillStyle = "rgba(120,215,255," + p.a + ")";
        ctx.fill();

        for (var j = i + 1; j < ps.length; j++) {
          var q = ps[j];
          var dx = p.x - q.x, dy = p.y - q.y;
          var d2 = dx * dx + dy * dy;
          if (d2 < 15000) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = "rgba(60,170,230," + (0.10 * (1 - d2 / 15000)) + ")";
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      /* 扫描光带 */
      scanY += 0.0016;
      if (scanY > 1.2) scanY = -0.2;
      var gy = scanY * h;
      var g = ctx.createLinearGradient(0, gy - 90, 0, gy + 90);
      g.addColorStop(0, "rgba(53,226,255,0)");
      g.addColorStop(0.5, "rgba(53,226,255,0.055)");
      g.addColorStop(1, "rgba(53,226,255,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, gy - 90, w, 180);

      requestAnimationFrame(draw);
    }

    init();
    window.addEventListener("resize", init);
    draw();
  })();

  /* =========================================================
     拉数据
     ========================================================= */
  function boot() {
    fetch("../../data.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        render(d);
        renderMore(d);
        autoplay(echarts.getInstanceByDom(document.getElementById("cSentiment")), 3, 3800);
        autoplay(echarts.getInstanceByDom(document.getElementById("cTopic")), 5, 3400);
        autoplay(echarts.getInstanceByDom(document.getElementById("cTopicTrend")), 12, 3200);
      })
      .catch(function (e) {
        console.error("数据加载失败", e);
        document.getElementById("genAt").textContent = "数据加载失败：" + e;
      });
  }

  window.addEventListener("load", boot);
})();