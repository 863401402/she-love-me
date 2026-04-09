"""
generate_html_report.py - 生成 HTML 报告

读取 stats.json + analysis.json，生成现代风格的分析报告
设计风格：Spotify Wrapped 风格 - 深色底、大字排版、渐变色、现代卡片
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_chart_data(stats):
    trend = stats.get("daily_trend", [])
    trend_labels = [d["date"] for d in trend[-60:]]
    trend_data = [d["count"] for d in trend[-60:]]

    hours = stats.get("active_hours", {})
    hour_labels = [f"{i}" for i in range(24)]
    hour_data = [hours.get(str(i), 0) for i in range(24)]

    basic = stats.get("basic", {})
    pie_data = [basic.get("my_messages", 0), basic.get("their_messages", 0)]

    return {
        "trend_labels": trend_labels,
        "trend_data": trend_data,
        "hour_labels": hour_labels,
        "hour_data": hour_data,
        "pie_data": pie_data,
    }


def render_html(stats, analysis, contact_name):
    scores = stats.get("scores", {})
    simp = scores.get("simp_index", 0)
    loved = scores.get("loved_index", 0)
    cold = scores.get("cold_index", 0)
    basic = stats.get("basic", {})
    initiative = stats.get("initiative", {})
    reply = stats.get("reply_speed", {})
    bombing = stats.get("bombing", {})
    goodnight = stats.get("goodnight", {})
    msg_len = stats.get("message_length", {})

    relationship_type = analysis.get("relationship_type", "未知")
    relationship_label = analysis.get("relationship_label", "")
    verdict = analysis.get("verdict", "")
    key_findings = analysis.get("key_findings", [])

    chart = build_chart_data(stats)
    chart_data_js = json.dumps(chart, ensure_ascii=False)
    date_str = datetime.now().strftime("%Y.%m.%d")

    date_range = basic.get("date_range", ["?", "?"])
    total_days = basic.get("total_days", 1)
    my_ratio = int(basic.get("my_ratio", 0) * 100)
    their_ratio = int(basic.get("their_ratio", 0) * 100)
    speed_ratio = reply.get("speed_ratio", 1)

    findings_html = "\n".join(
        f"""<div class="finding-card">
          <div class="finding-index">{i + 1:02d}</div>
          <p>{f}</p>
        </div>"""
        for i, f in enumerate(key_findings)
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>她爱你吗 · {contact_name}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0a0a0f;
    --surface: #111118;
    --surface-2: #18181f;
    --border: rgba(255,255,255,0.06);
    --border-hover: rgba(255,255,255,0.12);
    --text: #f0f0f5;
    --text-muted: #6b6b80;
    --text-subtle: #3a3a4a;
    --accent-1: #a855f7;
    --accent-2: #ec4899;
    --accent-3: #3b82f6;
    --accent-warm: #f59e0b;
    --grad-love: linear-gradient(135deg, #a855f7, #ec4899);
    --grad-simp: linear-gradient(135deg, #f59e0b, #ef4444);
    --grad-cold: linear-gradient(135deg, #3b82f6, #06b6d4);
    --radius: 16px;
    --radius-sm: 10px;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }}

  /* ── Hero ── */
  .hero {{
    position: relative;
    overflow: hidden;
    padding: 80px 24px 64px;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }}
  .hero::before {{
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 50% at 30% 0%, rgba(168,85,247,.18) 0%, transparent 70%),
      radial-gradient(ellipse 60% 50% at 70% 0%, rgba(236,72,153,.18) 0%, transparent 70%);
    pointer-events: none;
  }}
  .hero-eyebrow {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .15em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 20px;
  }}
  .hero-title {{
    font-size: clamp(48px, 10vw, 96px);
    font-weight: 900;
    line-height: 1;
    letter-spacing: -.03em;
    background: var(--grad-love);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 16px;
  }}
  .hero-contact {{
    font-size: 20px;
    font-weight: 500;
    color: var(--text-muted);
    margin-bottom: 8px;
  }}
  .hero-contact span {{ color: var(--text); font-weight: 700; }}
  .hero-date {{ font-size: 13px; color: var(--text-subtle); }}

  /* ── Layout ── */
  .container {{ max-width: 960px; margin: 0 auto; padding: 48px 24px 80px; }}
  .section {{ margin-bottom: 64px; }}
  .section-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--text-subtle);
    margin-bottom: 20px;
  }}

  /* ── Score Hero Cards ── */
  .score-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .score-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: border-color .2s;
  }}
  .score-card:hover {{ border-color: var(--border-hover); }}
  .score-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
  }}
  .score-card.simp::before {{ background: var(--grad-simp); }}
  .score-card.loved::before {{ background: var(--grad-love); }}
  .score-card.cold::before {{ background: var(--grad-cold); }}
  .score-emoji {{ font-size: 24px; margin-bottom: 12px; }}
  .score-label {{ font-size: 11px; font-weight: 600; color: var(--text-muted); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; }}
  .score-value {{ font-size: 56px; font-weight: 900; line-height: 1; letter-spacing: -.04em; }}
  .score-card.simp .score-value {{ background: var(--grad-simp); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
  .score-card.loved .score-value {{ background: var(--grad-love); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
  .score-card.cold .score-value {{ background: var(--grad-cold); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
  .score-bar {{
    margin-top: 16px;
    height: 3px;
    background: var(--surface-2);
    border-radius: 99px;
    overflow: hidden;
  }}
  .score-bar-fill {{ height: 100%; border-radius: 99px; }}
  .score-card.simp .score-bar-fill {{ background: var(--grad-simp); }}
  .score-card.loved .score-bar-fill {{ background: var(--grad-love); }}
  .score-card.cold .score-bar-fill {{ background: var(--grad-cold); }}

  /* ── 成分表 ── */
  .ingredient-list {{ display: flex; flex-direction: column; gap: 14px; }}
  .ingredient-row {{
    display: grid;
    grid-template-columns: 110px 1fr 52px;
    align-items: center;
    gap: 14px;
  }}
  .ingredient-name {{ font-size: 13px; font-weight: 500; color: var(--text-muted); }}
  .ingredient-track {{
    height: 6px;
    background: var(--surface-2);
    border-radius: 99px;
    overflow: hidden;
  }}
  .ingredient-fill {{ height: 100%; border-radius: 99px; }}
  .i-simp {{ background: var(--grad-simp); }}
  .i-loved {{ background: var(--grad-love); }}
  .i-cold {{ background: var(--grad-cold); }}
  .i-tool {{ background: linear-gradient(90deg, #374151, #6b7280); }}
  .ingredient-pct {{ font-size: 14px; font-weight: 700; text-align: right; }}

  /* ── Stat Grid ── */
  .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
  @media(min-width:640px) {{ .stat-grid {{ grid-template-columns: repeat(4, 1fr); }} }}
  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 20px 16px;
    transition: border-color .2s;
  }}
  .stat-card:hover {{ border-color: var(--border-hover); }}
  .stat-meta {{ font-size: 11px; font-weight: 500; color: var(--text-subtle); letter-spacing: .05em; text-transform: uppercase; margin-bottom: 10px; }}
  .stat-main {{ font-size: 28px; font-weight: 800; letter-spacing: -.02em; line-height: 1; }}
  .stat-sub {{ font-size: 11px; color: var(--text-muted); margin-top: 6px; line-height: 1.5; }}

  /* ── Compare Bars ── */
  .compare-list {{ display: flex; flex-direction: column; gap: 20px; }}
  .compare-row {{ }}
  .compare-header {{
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 8px;
  }}
  .compare-track {{
    position: relative;
    height: 8px;
    background: var(--surface-2);
    border-radius: 99px;
    overflow: hidden;
  }}
  .compare-you {{
    position: absolute;
    left: 0; top: 0; bottom: 0;
    border-radius: 99px;
    background: var(--grad-simp);
  }}
  .compare-them {{
    position: absolute;
    right: 0; top: 0; bottom: 0;
    border-radius: 99px;
    background: var(--grad-love);
  }}

  /* ── Findings ── */
  .findings-list {{ display: flex; flex-direction: column; gap: 12px; }}
  .finding-card {{
    display: grid;
    grid-template-columns: 40px 1fr;
    gap: 16px;
    align-items: start;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 20px;
    transition: border-color .2s;
  }}
  .finding-card:hover {{ border-color: var(--border-hover); }}
  .finding-index {{
    font-size: 11px;
    font-weight: 700;
    color: var(--text-subtle);
    font-variant-numeric: tabular-nums;
    letter-spacing: .05em;
    padding-top: 2px;
  }}
  .finding-card p {{ font-size: 14px; line-height: 1.7; color: var(--text-muted); }}

  /* ── Verdict ── */
  .verdict-card {{
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 48px 40px;
    text-align: center;
    overflow: hidden;
  }}
  .verdict-card::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse 80% 60% at 50% 100%, rgba(168,85,247,.08) 0%, transparent 70%);
    pointer-events: none;
  }}
  .verdict-type-badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--accent-1);
    background: rgba(168,85,247,.12);
    border: 1px solid rgba(168,85,247,.2);
    border-radius: 99px;
    padding: 6px 14px;
    margin-bottom: 20px;
  }}
  .verdict-type {{
    font-size: clamp(32px, 6vw, 52px);
    font-weight: 900;
    letter-spacing: -.03em;
    background: var(--grad-love);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}
  .verdict-label {{
    font-size: 15px;
    color: var(--text-muted);
    margin-bottom: 28px;
  }}
  .verdict-divider {{
    width: 40px;
    height: 1px;
    background: var(--border);
    margin: 0 auto 28px;
  }}
  .verdict-text {{
    font-size: 16px;
    line-height: 1.8;
    color: var(--text-muted);
    max-width: 600px;
    margin: 0 auto;
  }}

  /* ── Charts ── */
  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px;
  }}
  .chart-title {{ font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 20px; }}
  .chart-wrap {{ position: relative; height: 180px; }}
  .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}

  /* ── Footer ── */
  .footer {{
    text-align: center;
    padding: 32px 24px;
    font-size: 11px;
    color: var(--text-subtle);
    border-top: 1px solid var(--border);
    letter-spacing: .03em;
  }}

  @media (max-width: 500px) {{
    .score-grid {{ grid-template-columns: 1fr; }}
    .charts-row {{ grid-template-columns: 1fr; }}
    .ingredient-row {{ grid-template-columns: 90px 1fr 40px; }}
    .verdict-card {{ padding: 32px 20px; }}
  }}
</style>
</head>
<body>

<!-- Hero -->
<header class="hero">
  <p class="hero-eyebrow">舔狗鉴定所 · 聊天记录分析报告</p>
  <h1 class="hero-title">她爱你吗？</h1>
  <p class="hero-contact">与 <span>{contact_name}</span> 的聊天记录</p>
  <p class="hero-date">{date_range[0]} — {date_range[1]} · {total_days} 天 · {basic.get('total_messages', 0):,} 条消息</p>
</header>

<main class="container">

  <!-- 三大指数 -->
  <section class="section">
    <p class="section-label">鉴定指数</p>
    <div class="score-grid">
      <div class="score-card simp">
        <div class="score-emoji">🐶</div>
        <div class="score-label">舔狗指数</div>
        <div class="score-value">{simp}</div>
        <div class="score-bar"><div class="score-bar-fill" style="width:{simp}%"></div></div>
      </div>
      <div class="score-card loved">
        <div class="score-emoji">💜</div>
        <div class="score-label">被爱指数</div>
        <div class="score-value">{loved}</div>
        <div class="score-bar"><div class="score-bar-fill" style="width:{loved}%"></div></div>
      </div>
      <div class="score-card cold">
        <div class="score-emoji">🧊</div>
        <div class="score-label">冷淡指数</div>
        <div class="score-value">{cold}</div>
        <div class="score-bar"><div class="score-bar-fill" style="width:{cold}%"></div></div>
      </div>
    </div>
  </section>

  <!-- 恋爱成分表 -->
  <section class="section">
    <p class="section-label">恋爱成分表</p>
    <div class="ingredient-list">
      <div class="ingredient-row">
        <span class="ingredient-name">🐶 舔犬成分</span>
        <div class="ingredient-track"><div class="ingredient-fill i-simp" style="width:{simp}%"></div></div>
        <span class="ingredient-pct">{simp}%</span>
      </div>
      <div class="ingredient-row">
        <span class="ingredient-name">💜 被爱成分</span>
        <div class="ingredient-track"><div class="ingredient-fill i-loved" style="width:{loved}%"></div></div>
        <span class="ingredient-pct">{loved}%</span>
      </div>
      <div class="ingredient-row">
        <span class="ingredient-name">🧊 冷淡成分</span>
        <div class="ingredient-track"><div class="ingredient-fill i-cold" style="width:{cold}%"></div></div>
        <span class="ingredient-pct">{cold}%</span>
      </div>
      <div class="ingredient-row">
        <span class="ingredient-name">🔧 工具人成分</span>
        <div class="ingredient-track"><div class="ingredient-fill i-tool" style="width:{max(0, simp - loved - 10)}%"></div></div>
        <span class="ingredient-pct">{max(0, simp - loved - 10)}%</span>
      </div>
    </div>
  </section>

  <!-- 关键数据 -->
  <section class="section">
    <p class="section-label">关键数据</p>
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-meta">消息占比</div>
        <div class="stat-main">{my_ratio}<span style="font-size:.5em;font-weight:500;color:var(--text-muted)">%</span></div>
        <div class="stat-sub">你 · 对方 {their_ratio}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">主动发起</div>
        <div class="stat-main">{initiative.get('my_starts', 0)}<span style="font-size:.4em;font-weight:500;color:var(--text-muted)"> 次</span></div>
        <div class="stat-sub">对方 {initiative.get('their_starts', 0)} 次</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">你的回复速度</div>
        <div class="stat-main" style="font-size:20px;font-weight:800">{reply.get('my_avg_human', 'N/A')}</div>
        <div class="stat-sub">对方 {reply.get('their_avg_human', 'N/A')}</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">回速差距</div>
        <div class="stat-main">{speed_ratio}<span style="font-size:.45em;font-weight:500;color:var(--text-muted)">x</span></div>
        <div class="stat-sub">对方比你慢这么多倍</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">你的轰炸次数</div>
        <div class="stat-main">{bombing.get('my_bomb_count', 0)}</div>
        <div class="stat-sub">最多连发 {bombing.get('my_max_consecutive', 0)} 条</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">先说晚安</div>
        <div class="stat-main">{goodnight.get('my_goodnight', 0)}<span style="font-size:.4em;font-weight:500;color:var(--text-muted)"> 次</span></div>
        <div class="stat-sub">对方先说 {goodnight.get('their_goodnight', 0)} 次</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">你的平均字数</div>
        <div class="stat-main">{msg_len.get('my_avg_chars', 0)}<span style="font-size:.4em;font-weight:500;color:var(--text-muted)"> 字</span></div>
        <div class="stat-sub">对方 {msg_len.get('their_avg_chars', 0)} 字</div>
      </div>
      <div class="stat-card">
        <div class="stat-meta">日均消息</div>
        <div class="stat-main">{basic.get('avg_daily', 0)}</div>
        <div class="stat-sub">条 / 天</div>
      </div>
    </div>
  </section>

  <!-- 对比分析 -->
  <section class="section">
    <p class="section-label">双方对比</p>
    <div class="compare-list">
      <div class="compare-row">
        <div class="compare-header">
          <span>你 · 消息量 {my_ratio}%</span>
          <span>{their_ratio}% · 对方</span>
        </div>
        <div class="compare-track">
          <div class="compare-you" style="width:{my_ratio}%"></div>
          <div class="compare-them" style="width:{their_ratio}%"></div>
        </div>
      </div>
      <div class="compare-row">
        <div class="compare-header">
          <span>你 · 主动发起 {initiative.get('my_starts', 0)}次</span>
          <span>{initiative.get('their_starts', 0)}次 · 对方</span>
        </div>
        <div class="compare-track">
          <div class="compare-you" style="width:{int(initiative.get('my_starts',0)/(max(initiative.get('my_starts',0)+initiative.get('their_starts',0),1))*100)}%"></div>
          <div class="compare-them" style="width:{int(initiative.get('their_starts',0)/(max(initiative.get('my_starts',0)+initiative.get('their_starts',0),1))*100)}%"></div>
        </div>
      </div>
      <div class="compare-row">
        <div class="compare-header">
          <span>你 · 先说晚安 {goodnight.get('my_goodnight', 0)}次</span>
          <span>{goodnight.get('their_goodnight', 0)}次 · 对方</span>
        </div>
        <div class="compare-track">
          <div class="compare-you" style="width:{int(goodnight.get('my_goodnight',0)/(max(goodnight.get('my_goodnight',0)+goodnight.get('their_goodnight',0),1))*100)}%"></div>
          <div class="compare-them" style="width:{int(goodnight.get('their_goodnight',0)/(max(goodnight.get('my_goodnight',0)+goodnight.get('their_goodnight',0),1))*100)}%"></div>
        </div>
      </div>
    </div>
  </section>

  <!-- 趋势图表 -->
  <section class="section">
    <p class="section-label">数据可视化</p>
    <div class="chart-card" style="margin-bottom:12px">
      <div class="chart-title">消息趋势（最近60天）</div>
      <div class="chart-wrap"><canvas id="trendChart"></canvas></div>
    </div>
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">活跃时段分布</div>
        <div class="chart-wrap"><canvas id="hourChart"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">消息占比</div>
        <div class="chart-wrap"><canvas id="pieChart"></canvas></div>
      </div>
    </div>
  </section>

  <!-- 鉴定发现 -->
  <section class="section">
    <p class="section-label">鉴定发现</p>
    <div class="findings-list">
      {findings_html}
    </div>
  </section>

  <!-- 最终鉴定 -->
  <section class="section">
    <p class="section-label">最终鉴定</p>
    <div class="verdict-card">
      <div class="verdict-type-badge">舔狗鉴定所 · 官方认证</div>
      <div class="verdict-type">{relationship_type}</div>
      <div class="verdict-label">{relationship_label}</div>
      <div class="verdict-divider"></div>
      <div class="verdict-text">{verdict}</div>
    </div>
  </section>

</main>

<footer class="footer">
  仅供娱乐 · 数据本地处理，不上传任何服务器 · 她爱你吗？舔狗鉴定所 · {date_str}
</footer>

<script>
const d = {chart_data_js};
const base = {{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{
      backgroundColor: '#18181f',
      borderColor: 'rgba(255,255,255,0.06)',
      borderWidth: 1,
      titleColor: '#f0f0f5',
      bodyColor: '#6b6b80',
      padding: 12,
    }}
  }}
}};

new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: d.trend_labels,
    datasets: [{{
      data: d.trend_data,
      borderColor: '#a855f7',
      backgroundColor: 'rgba(168,85,247,.08)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      borderWidth: 2,
    }}]
  }},
  options: {{
    ...base,
    scales: {{
      x: {{ ticks: {{ color: '#3a3a4a', maxTicksLimit: 8, font: {{ size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.03)' }}, border: {{ display: false }} }},
      y: {{ ticks: {{ color: '#3a3a4a', font: {{ size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.03)' }}, border: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById('hourChart'), {{
  type: 'bar',
  data: {{
    labels: d.hour_labels,
    datasets: [{{
      data: d.hour_data,
      backgroundColor: 'rgba(168,85,247,.5)',
      borderColor: 'rgba(168,85,247,.8)',
      borderWidth: 1,
      borderRadius: 3,
    }}]
  }},
  options: {{
    ...base,
    scales: {{
      x: {{ ticks: {{ color: '#3a3a4a', font: {{ size: 10 }}, maxTicksLimit: 8 }}, grid: {{ display: false }}, border: {{ display: false }} }},
      y: {{ ticks: {{ color: '#3a3a4a', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.03)' }}, border: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['你', '{contact_name}'],
    datasets: [{{
      data: d.pie_data,
      backgroundColor: ['rgba(245,158,11,.8)', 'rgba(168,85,247,.8)'],
      borderColor: ['#f59e0b', '#a855f7'],
      borderWidth: 2,
    }}]
  }},
  options: {{
    ...base,
    plugins: {{
      ...base.plugins,
      legend: {{
        display: true,
        position: 'bottom',
        labels: {{ color: '#6b6b80', font: {{ size: 11 }}, padding: 16, boxWidth: 10 }}
      }}
    }},
    cutout: '65%'
  }}
}});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--contact", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    stats = load_json(args.stats)
    analysis = load_json(args.analysis)

    html = render_html(stats, analysis, args.contact)

    os.makedirs(args.output, exist_ok=True)
    date_tag = datetime.now().strftime("%Y%m%d_%H%M")
    safe_name = re.sub(r'[^\w\-]', '_', args.contact) if args.contact else "contact"
    out_path = os.path.join(args.output, f"{safe_name}_{date_tag}.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[+] 报告已生成: {out_path}", file=sys.stderr)
    print(json.dumps({"status": "ok", "path": out_path}))


if __name__ == "__main__":
    main()
