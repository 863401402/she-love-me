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


def escape_html(s):
    if not isinstance(s, str):
        s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_danger_warnings(danger_warnings):
    if not danger_warnings:
        return '<p style="color:var(--text-subtle);font-size:13px;">本次鉴定未发现明显危险信号</p>'

    level_colors = {
        "极高危": ("#ef4444", "rgba(239,68,68,.12)", "rgba(239,68,68,.25)"),
        "高危":   ("#f97316", "rgba(249,115,22,.12)", "rgba(249,115,22,.25)"),
        "中危":   ("#eab308", "rgba(234,179,8,.12)",  "rgba(234,179,8,.25)"),
        "低危":   ("#22c55e", "rgba(34,197,94,.12)",  "rgba(34,197,94,.25)"),
    }

    items = []
    for w in danger_warnings:
        wtype   = escape_html(w.get("type", ""))
        level   = w.get("level", "中危")
        evidence = escape_html(w.get("evidence", ""))
        color, bg, border = level_colors.get(level, ("#6b7280", "rgba(107,114,128,.12)", "rgba(107,114,128,.25)"))

        # 构建证据内容：优先使用 trigger_met / trigger_status 双阈值结构，回退到 evidence
        trigger_met = w.get("trigger_met") or w.get("trigger_status") or {}
        quantitative = escape_html(trigger_met.get("quantitative", ""))
        textual = escape_html(trigger_met.get("textual", ""))
        note = escape_html(w.get("note", ""))

        evidence_html = ""
        if quantitative or textual:
            evidence_html += f'<div class="warning-trigger"><span class="trigger-label">📊 量化</span>{quantitative}</div>' if quantitative else ""
            evidence_html += f'<div class="warning-trigger"><span class="trigger-label">💬 文本</span>{textual}</div>' if textual else ""
        elif evidence:
            evidence_html = f'<p class="warning-evidence">{evidence}</p>'
        if note:
            evidence_html += f'<p class="warning-note">{note}</p>'

        items.append(f"""
        <div class="warning-card" style="border-color:{border};background:{bg};">
          <div class="warning-header">
            <span class="warning-type">{wtype}</span>
            <span class="warning-badge" style="color:{color};background:{bg};border-color:{border};">{level}</span>
          </div>
          {evidence_html}
        </div>""")
    return "\n".join(items)


def render_sternberg(sternberg):
    passion    = sternberg.get("passion", 0)
    intimacy   = sternberg.get("intimacy", 0)
    commitment = sternberg.get("commitment", 0)
    love_type  = escape_html(sternberg.get("love_type", ""))
    return f"""
    <div class="sternberg-wrap">
      <div class="sternberg-row">
        <span class="sternberg-label">激情 Passion</span>
        <div class="sternberg-track"><div class="sternberg-fill s-passion" style="width:{passion}%"></div></div>
        <span class="sternberg-val">{passion}</span>
      </div>
      <div class="sternberg-row">
        <span class="sternberg-label">亲密 Intimacy</span>
        <div class="sternberg-track"><div class="sternberg-fill s-intimacy" style="width:{intimacy}%"></div></div>
        <span class="sternberg-val">{intimacy}</span>
      </div>
      <div class="sternberg-row">
        <span class="sternberg-label">承诺 Commitment</span>
        <div class="sternberg-track"><div class="sternberg-fill s-commitment" style="width:{commitment}%"></div></div>
        <span class="sternberg-val">{commitment}</span>
      </div>
      <div class="sternberg-type">→ {love_type}</div>
    </div>"""


def render_gottman(gottman):
    ratio    = gottman.get("positive_negative_ratio", 0)
    horsemen = gottman.get("horsemen_detected", [])
    risk     = escape_html(gottman.get("risk_level", ""))
    ratio_pct = min(int(ratio / 10 * 100), 100)
    repair   = gottman.get("repair_attempts", {})

    horsemen_chips = "".join(
        f'<span class="horseman-chip">{escape_html(h)}</span>' for h in horsemen
    )
    if not horsemen_chips:
        horsemen_chips = '<span style="color:var(--text-subtle);font-size:12px;">未检测到四骑士信号</span>'

    risk_color = {"高危": "#ef4444", "中危": "#eab308", "低危": "#22c55e"}.get(risk, "#6b7280")

    repair_html = ""
    if repair:
        who   = escape_html(repair.get("who_initiates", ""))
        who_label = "你先低头" if who == "me" else ("对方先低头" if who == "them" else escape_html(who))
        method = escape_html(repair.get("method", ""))
        resp   = escape_html(repair.get("partner_response", ""))
        rate   = escape_html(repair.get("success_rate", ""))
        repair_html = f"""
      <div class="repair-section">
        <div class="repair-label">修复尝试分析</div>
        <div class="repair-grid">
          {f'<div class="repair-item"><span class="repair-key">主动低头</span><span class="repair-val">{who_label}</span></div>' if who_label else ''}
          {f'<div class="repair-item"><span class="repair-key">修复方式</span><span class="repair-val">{method}</span></div>' if method else ''}
          {f'<div class="repair-item"><span class="repair-key">对方响应</span><span class="repair-val">{resp}</span></div>' if resp else ''}
          {f'<div class="repair-item"><span class="repair-key">成功率</span><span class="repair-val">{rate}</span></div>' if rate else ''}
        </div>
      </div>"""

    return f"""
    <div class="gottman-wrap">
      <div class="gottman-ratio-row">
        <div>
          <div class="gottman-ratio-val">{ratio}<span style="font-size:.5em;font-weight:500;color:var(--text-muted)">:1</span></div>
          <div class="gottman-ratio-label">正负互动比（健康值 ≥ 5:1）</div>
        </div>
        <div class="gottman-risk-badge" style="color:{risk_color};border-color:{risk_color}22;background:{risk_color}11;">{risk}</div>
      </div>
      <div class="gottman-bar-track"><div class="gottman-bar-fill" style="width:{ratio_pct}%;background:{risk_color};"></div></div>
      <div class="gottman-horsemen-label">四骑士检测</div>
      <div class="gottman-horsemen">{horsemen_chips}</div>
      {repair_html}
    </div>"""


def render_personality(personality, contact_name):
    user_att    = escape_html(personality.get("user_attachment", ""))
    partner_att = escape_html(personality.get("partner_attachment", ""))
    user_comm   = escape_html(personality.get("user_communication", ""))
    partner_comm = escape_html(personality.get("partner_communication", ""))
    user_lang   = escape_html(personality.get("user_love_language", ""))
    partner_lang = escape_html(personality.get("partner_love_language", ""))
    pursue_dist = personality.get("pursue_distance_cycle", False)
    lang_mismatch = personality.get("love_language_mismatch", False)

    pursue_html = ""
    if pursue_dist:
        loop = personality.get("pursue_distance_loop", {})
        loop_html = ""
        if loop:
            trigger = escape_html(loop.get("trigger", ""))
            retreat = escape_html(loop.get("retreat", ""))
            escalation = escape_html(loop.get("escalation", ""))
            deterioration = escape_html(loop.get("deterioration", ""))
            loop_html = f"""
        <div class="loop-steps">
          {f'<div class="loop-step"><span class="loop-num">1</span><span class="loop-text">触发：{trigger}</span></div>' if trigger else ''}
          {f'<div class="loop-step"><span class="loop-num">2</span><span class="loop-text">撤退：{retreat}</span></div>' if retreat else ''}
          {f'<div class="loop-step"><span class="loop-num">3</span><span class="loop-text">升级：{escalation}</span></div>' if escalation else ''}
          {f'<div class="loop-step"><span class="loop-num">4</span><span class="loop-text">恶化：{deterioration}</span></div>' if deterioration else ''}
        </div>"""
        pursue_html = f"""
      <div class="pursue-alert">
        ⚠️ <strong>追逃循环已形成</strong>：你越追，TA越逃；TA越逃，你越焦虑——负向循环持续强化。
        {loop_html}
      </div>"""

    # 情感可得性
    ea = personality.get("emotional_availability", {})
    ea_html = ""
    if ea:
        ea_level = ea.get("level", "")
        ea_evidence = escape_html(ea.get("evidence", ""))
        ea_risk = escape_html(ea.get("risk_note", ""))
        ea_color = {"高": "#22c55e", "中": "#eab308", "低": "#ef4444"}.get(ea_level, "#6b7280")
        ea_html = f"""
      <div class="ea-card">
        <div class="ea-header">
          <span class="ea-label">情感可得性评估</span>
          <span class="ea-badge" style="color:{ea_color};border-color:{ea_color}33;background:{ea_color}11;">{ea_level}</span>
        </div>
        {f'<p class="ea-evidence">{ea_evidence}</p>' if ea_evidence else ''}
        {f'<p class="ea-risk">{ea_risk}</p>' if ea_risk else ''}
      </div>"""

    lang_mismatch_html = ""
    if lang_mismatch:
        lang_mismatch_html = """
      <div class="lang-mismatch-alert">
        💬 <strong>爱的语言不匹配</strong>：你们表达爱的方式不同，导致给予了但对方感受不到。
      </div>"""

    return f"""
    <div class="personality-table">
      <div class="pt-row pt-header">
        <div class="pt-cell"></div>
        <div class="pt-cell pt-you">你</div>
        <div class="pt-cell pt-them">{escape_html(contact_name)}</div>
      </div>
      <div class="pt-row">
        <div class="pt-cell pt-label">依恋类型</div>
        <div class="pt-cell">{user_att}</div>
        <div class="pt-cell">{partner_att}</div>
      </div>
      <div class="pt-row">
        <div class="pt-cell pt-label">沟通风格</div>
        <div class="pt-cell">{user_comm}</div>
        <div class="pt-cell">{partner_comm}</div>
      </div>
      <div class="pt-row">
        <div class="pt-cell pt-label">爱的语言</div>
        <div class="pt-cell">{user_lang}</div>
        <div class="pt-cell">{partner_lang}</div>
      </div>
    </div>
    {pursue_html}
    {ea_html}
    {lang_mismatch_html}"""


def render_strategist(strategist):
    core    = escape_html(strategist.get("core_problem", ""))
    stops   = strategist.get("stop_doing", [])
    starts  = strategist.get("start_doing", [])
    roadmap = escape_html(strategist.get("roadmap", ""))
    walkaway = strategist.get("walkaway_point", {})

    def render_stop_item(s):
        if isinstance(s, dict):
            action = escape_html(s.get("action", ""))
            reason = escape_html(s.get("reason", ""))
            quote  = escape_html(s.get("quote", ""))
            html   = f'<li class="strategy-stop-item">❌ {action}'
            if reason:
                html += f'<div class="strategy-reason">{reason}</div>'
            if quote:
                html += f'<div class="strategy-quote">「{quote}」</div>'
            return html + '</li>'
        return f'<li class="strategy-stop-item">❌ {escape_html(str(s))}</li>'

    def render_start_item(s):
        if isinstance(s, dict):
            action = escape_html(s.get("action", ""))
            timing = escape_html(s.get("timing", ""))
            reason = escape_html(s.get("reason", ""))
            script = escape_html(s.get("script", ""))
            html   = f'<li class="strategy-start-item">✅ {action}'
            if timing:
                html += f'<div class="strategy-timing">⏰ 时机：{timing}</div>'
            if reason:
                html += f'<div class="strategy-reason">{reason}</div>'
            if script:
                html += f'<div class="strategy-script">参考话术：「{script}」</div>'
            return html + '</li>'
        return f'<li class="strategy-start-item">✅ {escape_html(str(s))}</li>'

    stops_html  = "\n".join(render_stop_item(s) for s in stops)
    starts_html = "\n".join(render_start_item(s) for s in starts)

    walkaway_html = ""
    if walkaway:
        wa_tf      = escape_html(walkaway.get("timeframe", ""))
        wa_trigger = escape_html(walkaway.get("trigger", ""))
        wa_reason  = escape_html(walkaway.get("reason", ""))
        walkaway_html = f"""
      <div class="walkaway-card">
        <div class="walkaway-label">🚩 止损红线（Walk-away Point）</div>
        {f'<p class="walkaway-trigger">如果在 <strong>{wa_tf}</strong> 内，对方仍然出现：{wa_trigger}</p>' if wa_trigger else ''}
        {f'<p class="walkaway-reason">{wa_reason}</p>' if wa_reason else ''}
      </div>"""

    return f"""
    <div class="strategist-wrap">
      <div class="core-problem-card">
        <div class="core-problem-label">核心问题</div>
        <p class="core-problem-text">{core}</p>
      </div>
      <div class="strategy-grid">
        <div class="strategy-col">
          <div class="strategy-col-title stop-title">立即停止</div>
          <ul class="strategy-list">{stops_html}</ul>
        </div>
        <div class="strategy-col">
          <div class="strategy-col-title start-title">立即开始</div>
          <ul class="strategy-list">{starts_html}</ul>
        </div>
      </div>
      <div class="roadmap-card">
        <div class="roadmap-label">推进路线图</div>
        <p class="roadmap-text">{roadmap}</p>
      </div>
      {walkaway_html}
    </div>"""


def render_key_findings(key_findings):
    if not key_findings:
        return '<p style="color:var(--text-subtle);font-size:13px;">暂无鉴定发现</p>'

    items = []
    for i, f in enumerate(key_findings):
        title    = escape_html(f.get("title", f"发现{i+1}"))
        quote    = escape_html(f.get("quote", ""))
        analysis = escape_html(f.get("analysis", ""))
        items.append(f"""
        <div class="finding-card">
          <div class="finding-index">{i+1:02d}</div>
          <div class="finding-body">
            <div class="finding-title">{title}</div>
            {f'<blockquote class="finding-quote">「{quote}」</blockquote>' if quote else ''}
            <p class="finding-analysis">{analysis}</p>
          </div>
        </div>""")
    return "\n".join(items)


def render_relationship_stage(rel_stage):
    """渲染关系阶段时间线"""
    if not rel_stage:
        return ""
    stage       = rel_stage.get("stage", "")
    description = escape_html(rel_stage.get("stage_description", ""))
    is_situ     = rel_stage.get("is_situationship", False)
    situ_ev     = escape_html(rel_stage.get("situationship_evidence", ""))
    stage_risk  = escape_html(rel_stage.get("stage_risk", ""))
    adv_path    = escape_html(rel_stage.get("advancement_path", ""))

    stages = ["初识试探期", "暧昧升温期", "拉锯确认期", "实名化前夜", "正式确认期", "关系维护期", "降温衰退期"]
    current_idx = stages.index(stage) if stage in stages else -1

    nodes_html = ""
    for i, s in enumerate(stages):
        is_current = (i == current_idx)
        cls = "stage-node active" if is_current else "stage-node"
        label_cls = "stage-label active-label" if is_current else "stage-label"
        nodes_html += f'<div class="{cls}"><div class="stage-dot"></div><div class="{label_cls}">{escape_html(s)}</div></div>'

    situ_badge = ""
    if is_situ:
        situ_badge = f"""
      <div class="situ-badge">
        <span>⚠ 实名化前夜</span> · 除了一个名分，其余情侣待遇你们都有了
      </div>
      {f'<p class="stage-evidence">证据：{situ_ev}</p>' if situ_ev else ''}"""

    risk_html = f'<div class="stage-risk-row"><span class="stage-risk-label">当前风险</span> <span class="stage-risk-text">{stage_risk}</span></div>' if stage_risk else ""
    adv_html  = f'<div class="stage-adv-row"><span class="stage-adv-label">推进方向</span> <span class="stage-adv-text">{adv_path}</span></div>' if adv_path else ""

    return f"""
    <div class="stage-wrap">
      <div class="stage-timeline">{nodes_html}</div>
      {situ_badge}
      <div class="stage-desc">{description}</div>
      {risk_html}
      {adv_html}
    </div>"""


def render_emotional_asymmetry(asym):
    """渲染情感不对称分析"""
    if not asym:
        return ""
    score       = asym.get("symmetry_score", 5)
    anchor      = asym.get("anchor_person", "me")
    anchor_desc = escape_html(asym.get("anchor_description", ""))
    conflict    = escape_html(asym.get("conflict_pattern", ""))
    power_dyn   = escape_html(asym.get("power_dynamics", ""))
    turning     = asym.get("key_turning_point", {})

    score_pct = int(score / 10 * 100)
    anchor_label = "你" if anchor == "me" else "对方"
    float_label  = "对方" if anchor == "me" else "你"

    score_color = "#a855f7" if score >= 7 else ("#eab308" if score >= 4 else "#ef4444")

    turning_html = ""
    if turning and turning.get("date"):
        t_date  = escape_html(turning.get("date", ""))
        t_event = escape_html(turning.get("event", ""))
        turning_html = f"""
      <div class="asym-turning">
        <span class="asym-turning-label">⚡ 关键转折点</span>
        <span class="asym-turning-date">{t_date}</span>
        <p class="asym-turning-event">{t_event}</p>
      </div>"""

    power_html = f'<div class="asym-power"><span class="asym-power-label">权力动态</span> {power_dyn}</div>' if power_dyn else ""

    return f"""
    <div class="asym-wrap">
      <div class="asym-score-row">
        <div class="asym-score-info">
          <div class="asym-score-val" style="color:{score_color}">{score}<span style="font-size:.5em;font-weight:500;color:var(--text-muted)">/10</span></div>
          <div class="asym-score-label">情感对称性</div>
        </div>
        <div class="asym-roles">
          <span class="asym-role anchor-role">⚓ {anchor_label} = 锚</span>
          <span class="asym-role float-role">🪁 {float_label} = 浮标</span>
        </div>
      </div>
      <div class="asym-bar-track"><div class="asym-bar-fill" style="width:{score_pct}%;background:{score_color};"></div></div>
      {f'<p class="asym-anchor-desc">{anchor_desc}</p>' if anchor_desc else ''}
      {f'<div class="asym-conflict"><span class="asym-conflict-label">冲突模式</span> {conflict}</div>' if conflict else ''}
      {power_html}
      {turning_html}
    </div>"""


def render_personality_portrait(portrait, contact_name):
    """渲染人格深度画像"""
    if not portrait:
        return ""

    def render_person(person_data, label):
        if not person_data:
            return ""
        core_traits = person_data.get("core_traits", [])
        core_needs  = escape_html(person_data.get("core_needs", ""))
        defenses    = person_data.get("defense_mechanisms", [])
        b5          = person_data.get("big_five_sketch", {})
        trust       = escape_html(person_data.get("trust_architecture", ""))

        traits_html = "".join(f'<span class="trait-chip">{escape_html(t)}</span>' for t in core_traits)

        defenses_html = ""
        for d in defenses:
            dtype   = escape_html(d.get("type", ""))
            trigger = escape_html(d.get("trigger", ""))
            evidence= escape_html(d.get("evidence", ""))
            meaning = escape_html(d.get("real_meaning", ""))
            defenses_html += f"""
          <div class="defense-item">
            <div class="defense-type">{dtype}</div>
            <div class="defense-detail">触发：{trigger}</div>
            {f'<div class="defense-quote">「{evidence}」</div>' if evidence else ''}
            {f'<div class="defense-meaning">真实含义：{meaning}</div>' if meaning else ''}
          </div>"""

        b5_html = ""
        if b5:
            b5_map = {
                "conscientiousness": "尽责性",
                "neuroticism": "神经质",
                "agreeableness": "亲和力",
                "openness": "开放性",
                "extraversion": "外向性"
            }
            b5_rows = ""
            for key, label_cn in b5_map.items():
                val = escape_html(b5.get(key, ""))
                if val:
                    level = val.split(" ")[0] if " " in val or "—" in val else val[:1]
                    level_color = {"高": "#a855f7", "中": "#6b7280", "低": "#3b82f6"}.get(level, "#6b7280")
                    b5_rows += f'<div class="b5-row"><span class="b5-label">{label_cn}</span><span class="b5-val" style="color:{level_color}">{val}</span></div>'
            b5_html = f'<div class="b5-section">{b5_rows}</div>'

        return f"""
        <div class="portrait-person">
          <div class="portrait-person-title">{label}</div>
          <div class="portrait-traits">{traits_html}</div>
          {f'<div class="portrait-needs"><span class="needs-label">底层需求</span> {core_needs}</div>' if core_needs else ''}
          {f'<div class="portrait-defenses-title">防御机制</div>{defenses_html}' if defenses_html else ''}
          {b5_html}
          {f'<div class="portrait-trust"><span class="trust-label">信任架构</span> {trust}</div>' if trust else ''}
        </div>"""

    # 需求-行为解码
    needs_map_html = ""
    user_data    = portrait.get("user", {})
    partner_data = portrait.get("partner", {})
    partner_needs_map = partner_data.get("needs_behavior_map", [])
    if partner_needs_map:
        items = ""
        for m in partner_needs_map:
            behavior = escape_html(m.get("behavior", ""))
            need     = escape_html(m.get("need", ""))
            decode   = escape_html(m.get("decode", ""))
            items += f"""
        <div class="nbm-item">
          <div class="nbm-behavior">「{behavior}」</div>
          <div class="nbm-arrow">↓</div>
          <div class="nbm-need">{need}</div>
          {f'<div class="nbm-decode">{decode}</div>' if decode else ''}
        </div>"""
        needs_map_html = f'<div class="nbm-section"><div class="nbm-title">行为解码：对方真正想要的是什么</div><div class="nbm-list">{items}</div></div>'

    user_html    = render_person(user_data, "你")
    partner_html = render_person(partner_data, escape_html(contact_name))

    return f"""
    <div class="portrait-grid">
      {user_html}
      {partner_html}
    </div>
    {needs_map_html}"""


def render_language_patterns(lang_patterns, linguistic_stats, contact_name):
    """渲染语言模式分析"""
    if not lang_patterns:
        return ""
    hedging      = escape_html(lang_patterns.get("hedging_density", ""))
    future_ori   = escape_html(lang_patterns.get("future_orientation", ""))
    valence      = escape_html(lang_patterns.get("emotional_valence_ratio", ""))
    conditional  = escape_html(lang_patterns.get("conditional_density", ""))
    key_finding  = escape_html(lang_patterns.get("key_linguistic_finding", ""))

    density_color = {"高": "#ef4444", "中": "#eab308", "低": "#22c55e"}

    hedging_color     = density_color.get(hedging.split(" ")[0] if hedging else "", "#6b7280")
    conditional_color = density_color.get(conditional.split(" ")[0] if conditional else "", "#6b7280")

    future_color = {"真实期待": "#22c55e", "虚假承诺": "#ef4444", "中性": "#6b7280"}.get(future_ori, "#6b7280")

    # 从统计数据补充数值
    we_me    = linguistic_stats.get("pronoun_we_count", {}).get("me", 0)
    we_them  = linguistic_stats.get("pronoun_we_count", {}).get("them", 0)
    rev_me   = linguistic_stats.get("revoke_count", {}).get("me", 0)
    rev_them = linguistic_stats.get("revoke_count", {}).get("them", 0)

    return f"""
    <div class="lang-wrap">
      <div class="lang-cards">
        <div class="lang-card">
          <div class="lang-card-label">模糊词密度</div>
          <div class="lang-card-val" style="color:{hedging_color}">{hedging or "—"}</div>
          <div class="lang-card-sub">也许/可能/感觉/好像</div>
        </div>
        <div class="lang-card">
          <div class="lang-card-label">条件句密度</div>
          <div class="lang-card-val" style="color:{conditional_color}">{conditional or "—"}</div>
          <div class="lang-card-sub">如果/要是/假如</div>
        </div>
        <div class="lang-card">
          <div class="lang-card-label">未来指向</div>
          <div class="lang-card-val" style="color:{future_color};font-size:14px">{future_ori or "—"}</div>
          <div class="lang-card-sub">以后/将来/等你</div>
        </div>
        <div class="lang-card">
          <div class="lang-card-label">情绪正负比</div>
          <div class="lang-card-val" style="font-size:13px">{valence or "—"}</div>
          <div class="lang-card-sub">正向 vs 负向情绪词</div>
        </div>
      </div>
      <div class="lang-stats-row">
        <span class="lang-stat-item">「我们」：你 {we_me} 次 / 对方 {we_them} 次</span>
        <span class="lang-stat-sep">·</span>
        <span class="lang-stat-item">撤回消息：你 {rev_me} 次 / 对方 {rev_them} 次</span>
      </div>
      {f'<div class="lang-finding"><span class="lang-finding-label">语言洞察</span><p>{key_finding}</p></div>' if key_finding else ''}
    </div>"""


def render_patriarch_wisdom(wisdom):
    """渲染祖师爷寄语（童锦程视角）"""
    if not wisdom:
        return ""

    situation = escape_html(wisdom.get("situation_read", ""))
    tactics   = wisdom.get("advance_tactics", [])
    mistake   = escape_html(wisdom.get("fatal_mistake", ""))
    quote     = escape_html(wisdom.get("closing_quote", ""))

    tactics_html = ""
    for i, t in enumerate(tactics, 1):
        title  = escape_html(t.get("title", ""))
        logic  = escape_html(t.get("logic", ""))
        action = escape_html(t.get("action", ""))
        tactics_html += f"""
        <div class="patriarch-tactic">
          <div class="patriarch-tactic-num">{i:02d}</div>
          <div class="patriarch-tactic-body">
            <div class="patriarch-tactic-title">「{title}」</div>
            {f'<p class="patriarch-tactic-logic">{logic}</p>' if logic else ''}
            {f'<div class="patriarch-tactic-action">怎么做：{action}</div>' if action else ''}
          </div>
        </div>"""

    return f"""
    <div class="patriarch-wrap">
      <div class="patriarch-avatar-row">
        <div class="patriarch-avatar">👴</div>
        <div class="patriarch-identity">
          <div class="patriarch-name">童锦程 · 深情祖师爷</div>
          <div class="patriarch-subtitle">街头智慧 · 真诚才是最高级的套路</div>
        </div>
      </div>

      {f'<div class="patriarch-read"><span class="patriarch-read-label">读局</span><p class="patriarch-read-text">{situation}</p></div>' if situation else ''}

      {f'<div class="patriarch-tactics-title">三条实招</div><div class="patriarch-tactics">{tactics_html}</div>' if tactics_html else ''}

      {f'''<div class="patriarch-mistake">
        <div class="patriarch-mistake-label">⚠️ 必须改掉的一件事</div>
        <p class="patriarch-mistake-text">{mistake}</p>
      </div>''' if mistake else ''}

      {f'<blockquote class="patriarch-quote">「{quote}」</blockquote>' if quote else ''}
    </div>"""



    scores    = stats.get("scores", {})
    simp      = scores.get("simp_index", 0)
    loved     = scores.get("loved_index", 0)
    cold      = scores.get("cold_index", 0)
    basic     = stats.get("basic", {})
    initiative = stats.get("initiative", {})
    reply     = stats.get("reply_speed", {})
    bombing   = stats.get("bombing", {})
    goodnight = stats.get("goodnight", {})
    msg_len   = stats.get("message_length", {})
    linguistic_stats = stats.get("linguistic", {})

    relationship_type  = escape_html(analysis.get("relationship_type", "未知"))
    relationship_label = escape_html(analysis.get("relationship_label", ""))
    relationship_trend = escape_html(analysis.get("relationship_trend", ""))
    verdict            = escape_html(analysis.get("verdict", ""))
    simp_description   = escape_html(analysis.get("simp_description", ""))
    love_description   = escape_html(analysis.get("love_description", ""))

    danger_warnings_html   = render_danger_warnings(analysis.get("danger_warnings", []))
    sternberg_html         = render_sternberg(analysis.get("sternberg", {}))
    gottman_html           = render_gottman(analysis.get("gottman", {}))
    personality_html       = render_personality(analysis.get("personality", {}), contact_name)
    strategist_html        = render_strategist(analysis.get("strategist", {}))
    findings_html          = render_key_findings(analysis.get("key_findings", []))
    relationship_stage_html = render_relationship_stage(analysis.get("relationship_stage"))
    emotional_asym_html    = render_emotional_asymmetry(analysis.get("emotional_asymmetry"))
    portrait_html          = render_personality_portrait(analysis.get("personality_portrait"), contact_name)
    lang_patterns_html     = render_language_patterns(
        analysis.get("language_patterns"), linguistic_stats, contact_name
    )
    patriarch_wisdom_html  = render_patriarch_wisdom(analysis.get("patriarch_wisdom"))

    chart = build_chart_data(stats)
    chart_data_js = json.dumps(chart, ensure_ascii=False)
    date_str = datetime.now().strftime("%Y.%m.%d")

    date_range = basic.get("date_range", ["?", "?"])
    total_days = basic.get("total_days", 1)
    my_ratio   = int(basic.get("my_ratio", 0) * 100)
    their_ratio = int(basic.get("their_ratio", 0) * 100)
    speed_ratio = reply.get("speed_ratio", 1)

    trend_icon = {"升温中": "🔥", "平稳维持": "➡️", "逐渐降温": "❄️", "已经凉透": "💀"}.get(
        analysis.get("relationship_trend", ""), "📊"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>她不一样 · {escape_html(contact_name)}</title>
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

  /* ── Danger Warnings ── */
  .warning-card {{
    border: 1px solid;
    border-radius: var(--radius-sm);
    padding: 18px 20px;
    margin-bottom: 12px;
  }}
  .warning-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }}
  .warning-type {{
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }}
  .warning-badge {{
    font-size: 11px;
    font-weight: 700;
    border: 1px solid;
    border-radius: 99px;
    padding: 3px 10px;
    letter-spacing: .06em;
  }}
  .warning-evidence {{
    font-size: 13px;
    line-height: 1.7;
    color: var(--text-muted);
  }}

  /* ── Sternberg ── */
  .sternberg-wrap {{ display: flex; flex-direction: column; gap: 16px; }}
  .sternberg-row {{
    display: grid;
    grid-template-columns: 130px 1fr 40px;
    align-items: center;
    gap: 14px;
  }}
  .sternberg-label {{ font-size: 12px; font-weight: 600; color: var(--text-muted); }}
  .sternberg-track {{
    height: 8px;
    background: var(--surface-2);
    border-radius: 99px;
    overflow: hidden;
  }}
  .sternberg-fill {{ height: 100%; border-radius: 99px; }}
  .s-passion    {{ background: linear-gradient(90deg, #ec4899, #f97316); }}
  .s-intimacy   {{ background: linear-gradient(90deg, #a855f7, #3b82f6); }}
  .s-commitment {{ background: linear-gradient(90deg, #22c55e, #06b6d4); }}
  .sternberg-val {{ font-size: 14px; font-weight: 700; text-align: right; color: var(--text-muted); }}
  .sternberg-type {{
    margin-top: 8px;
    font-size: 14px;
    font-weight: 600;
    color: var(--accent-1);
    padding: 10px 16px;
    background: rgba(168,85,247,.08);
    border: 1px solid rgba(168,85,247,.15);
    border-radius: var(--radius-sm);
  }}

  /* ── Gottman ── */
  .gottman-wrap {{ display: flex; flex-direction: column; gap: 14px; }}
  .gottman-ratio-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .gottman-ratio-val {{
    font-size: 40px;
    font-weight: 900;
    letter-spacing: -.03em;
    color: var(--text);
  }}
  .gottman-ratio-label {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}
  .gottman-risk-badge {{
    font-size: 12px;
    font-weight: 700;
    border: 1px solid;
    border-radius: 99px;
    padding: 6px 14px;
    letter-spacing: .06em;
  }}
  .gottman-bar-track {{
    height: 6px;
    background: var(--surface-2);
    border-radius: 99px;
    overflow: hidden;
  }}
  .gottman-bar-fill {{ height: 100%; border-radius: 99px; }}
  .gottman-horsemen-label {{ font-size: 11px; font-weight: 600; color: var(--text-subtle); letter-spacing: .08em; text-transform: uppercase; margin-top: 4px; }}
  .gottman-horsemen {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }}
  .horseman-chip {{
    font-size: 12px;
    font-weight: 600;
    color: #ef4444;
    background: rgba(239,68,68,.1);
    border: 1px solid rgba(239,68,68,.2);
    border-radius: 99px;
    padding: 4px 12px;
  }}

  /* ── Personality Table ── */
  .personality-table {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    overflow: hidden;
    margin-bottom: 16px;
  }}
  .pt-row {{
    display: grid;
    grid-template-columns: 90px 1fr 1fr;
    border-bottom: 1px solid var(--border);
  }}
  .pt-row:last-child {{ border-bottom: none; }}
  .pt-cell {{
    padding: 14px 16px;
    font-size: 13px;
    color: var(--text-muted);
    border-right: 1px solid var(--border);
  }}
  .pt-cell:last-child {{ border-right: none; }}
  .pt-header .pt-cell {{ font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--text-subtle); }}
  .pt-you   {{ color: #f59e0b !important; font-weight: 600; }}
  .pt-them  {{ color: #a855f7 !important; font-weight: 600; }}
  .pt-label {{ font-weight: 600; color: var(--text-subtle) !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: .06em; }}
  .pursue-alert {{
    font-size: 13px;
    line-height: 1.7;
    color: #f97316;
    background: rgba(249,115,22,.08);
    border: 1px solid rgba(249,115,22,.2);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    margin-bottom: 12px;
  }}
  .lang-mismatch-alert {{
    font-size: 13px;
    line-height: 1.7;
    color: #eab308;
    background: rgba(234,179,8,.08);
    border: 1px solid rgba(234,179,8,.2);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
  }}

  /* ── Strategist ── */
  .strategist-wrap {{ display: flex; flex-direction: column; gap: 16px; }}
  .core-problem-card {{
    background: rgba(168,85,247,.06);
    border: 1px solid rgba(168,85,247,.15);
    border-radius: var(--radius-sm);
    padding: 20px;
  }}
  .core-problem-label {{ font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--accent-1); margin-bottom: 10px; }}
  .core-problem-text {{ font-size: 14px; line-height: 1.8; color: var(--text-muted); }}
  .strategy-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  @media(max-width:560px) {{ .strategy-grid {{ grid-template-columns: 1fr; }} }}
  .strategy-col {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 18px;
  }}
  .strategy-col-title {{ font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 14px; }}
  .stop-title  {{ color: #ef4444; }}
  .start-title {{ color: #22c55e; }}
  .strategy-list {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
  .strategy-stop-item,
  .strategy-start-item {{ font-size: 13px; line-height: 1.7; color: var(--text-muted); }}
  .roadmap-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 20px;
  }}
  .roadmap-label {{ font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--accent-3); margin-bottom: 10px; }}
  .roadmap-text {{ font-size: 14px; line-height: 1.9; color: var(--text-muted); }}

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
  .finding-title {{ font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 10px; }}
  .finding-quote {{
    font-size: 13px;
    font-style: italic;
    color: var(--accent-1);
    border-left: 2px solid rgba(168,85,247,.4);
    padding-left: 12px;
    margin-bottom: 10px;
    line-height: 1.6;
  }}
  .finding-analysis {{ font-size: 13px; line-height: 1.7; color: var(--text-muted); }}

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
  .verdict-meta-row {{
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 20px;
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
  }}
  .verdict-trend-badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .08em;
    color: var(--text-muted);
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 99px;
    padding: 6px 14px;
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

  /* ── Analysis Row ── */
  .analysis-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  @media(max-width:560px) {{ .analysis-row {{ grid-template-columns: 1fr; }} }}
  .analysis-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 24px;
  }}
  .analysis-card-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--text-subtle);
    margin-bottom: 16px;
  }}

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
    .analysis-row {{ grid-template-columns: 1fr; }}
    .portrait-grid {{ grid-template-columns: 1fr; }}
    .lang-cards {{ grid-template-columns: repeat(2, 1fr); }}
  }}

  /* ── Score Description ── */
  .score-desc {{
    margin-top: 10px;
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.6;
    text-align: left;
  }}

  /* ── Relationship Stage Timeline ── */
  .stage-wrap {{ padding: 4px 0; }}
  .stage-timeline {{
    display: flex;
    align-items: flex-start;
    gap: 0;
    overflow-x: auto;
    padding-bottom: 12px;
    margin-bottom: 20px;
    scrollbar-width: none;
  }}
  .stage-timeline::-webkit-scrollbar {{ display: none; }}
  .stage-node {{
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    min-width: 80px;
    position: relative;
  }}
  .stage-node::before {{
    content: '';
    position: absolute;
    top: 8px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: var(--surface-2);
    z-index: 0;
  }}
  .stage-node:last-child::before {{ display: none; }}
  .stage-dot {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--surface-2);
    border: 2px solid var(--border);
    position: relative;
    z-index: 1;
    margin-bottom: 8px;
    transition: all .3s;
  }}
  .stage-node.active .stage-dot {{
    background: var(--accent-1);
    border-color: var(--accent-1);
    box-shadow: 0 0 12px rgba(168,85,247,.5);
    transform: scale(1.3);
  }}
  .stage-label {{
    font-size: 10px;
    color: var(--text-subtle);
    text-align: center;
    line-height: 1.4;
  }}
  .stage-node.active .active-label {{
    color: var(--accent-1);
    font-weight: 600;
    font-size: 11px;
  }}
  .situ-badge {{
    background: rgba(234,179,8,.08);
    border: 1px solid rgba(234,179,8,.2);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    font-size: 13px;
    color: #eab308;
    font-weight: 500;
    margin-bottom: 12px;
  }}
  .stage-evidence {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
    margin-bottom: 12px;
  }}
  .stage-desc {{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.7;
    margin-bottom: 12px;
  }}
  .stage-risk-row, .stage-adv-row {{
    display: flex;
    gap: 10px;
    font-size: 13px;
    margin-bottom: 8px;
    align-items: flex-start;
  }}
  .stage-risk-label {{ color: #ef4444; font-weight: 600; white-space: nowrap; }}
  .stage-adv-label  {{ color: #22c55e; font-weight: 600; white-space: nowrap; }}
  .stage-risk-text, .stage-adv-text {{ color: var(--text-muted); }}

  /* ── Emotional Asymmetry ── */
  .asym-wrap {{ padding: 4px 0; }}
  .asym-score-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    gap: 16px;
  }}
  .asym-score-val {{ font-size: 48px; font-weight: 900; line-height: 1; letter-spacing: -.03em; }}
  .asym-score-label {{ font-size: 11px; color: var(--text-muted); font-weight: 500; margin-top: 4px; }}
  .asym-roles {{ display: flex; flex-direction: column; gap: 6px; }}
  .asym-role {{
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 99px;
    border: 1px solid;
  }}
  .anchor-role {{ color: #a855f7; border-color: rgba(168,85,247,.3); background: rgba(168,85,247,.08); }}
  .float-role  {{ color: #6b7280; border-color: rgba(107,114,128,.3); background: rgba(107,114,128,.08); }}
  .asym-bar-track {{ height: 4px; background: var(--surface-2); border-radius: 99px; overflow: hidden; margin-bottom: 14px; }}
  .asym-bar-fill  {{ height: 100%; border-radius: 99px; transition: width .6s; }}
  .asym-anchor-desc {{ font-size: 13px; color: var(--text-muted); line-height: 1.7; margin-bottom: 10px; }}
  .asym-conflict {{ font-size: 13px; color: var(--text-muted); }}
  .asym-conflict-label {{ color: #eab308; font-weight: 600; margin-right: 8px; }}

  /* ── Language Patterns ── */
  .lang-wrap {{ padding: 4px 0; }}
  .lang-cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 14px;
  }}
  .lang-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 16px 12px;
    text-align: center;
  }}
  .lang-card-label {{ font-size: 10px; font-weight: 600; color: var(--text-subtle); letter-spacing: .05em; text-transform: uppercase; margin-bottom: 8px; }}
  .lang-card-val   {{ font-size: 18px; font-weight: 800; margin-bottom: 4px; }}
  .lang-card-sub   {{ font-size: 10px; color: var(--text-subtle); }}
  .lang-stats-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}
  .lang-stat-sep {{ color: var(--text-subtle); }}
  .lang-finding {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-1);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
  }}
  .lang-finding-label {{ font-size: 10px; font-weight: 600; color: var(--accent-1); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; display: block; }}
  .lang-finding p {{ font-size: 13px; color: var(--text-muted); line-height: 1.7; }}

  /* ── Personality Portrait ── */
  .portrait-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  .portrait-person {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
  }}
  .portrait-person-title {{ font-size: 13px; font-weight: 700; color: var(--text-muted); letter-spacing: .05em; text-transform: uppercase; margin-bottom: 12px; }}
  .portrait-traits {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }}
  .trait-chip {{
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 99px;
    background: rgba(168,85,247,.12);
    border: 1px solid rgba(168,85,247,.25);
    color: #c084fc;
  }}
  .portrait-needs {{ font-size: 13px; color: var(--text-muted); margin-bottom: 14px; line-height: 1.6; }}
  .needs-label {{ color: var(--accent-1); font-weight: 600; margin-right: 6px; }}
  .portrait-defenses-title {{ font-size: 11px; font-weight: 600; color: var(--text-subtle); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 10px; }}
  .defense-item {{
    background: var(--surface-2);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    margin-bottom: 8px;
  }}
  .defense-type {{ font-size: 12px; font-weight: 700; color: #f97316; margin-bottom: 4px; }}
  .defense-detail {{ font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }}
  .defense-quote {{
    font-size: 12px;
    color: var(--text-muted);
    font-style: italic;
    padding: 4px 8px;
    border-left: 2px solid rgba(249,115,22,.3);
    margin: 6px 0;
  }}
  .defense-meaning {{ font-size: 12px; color: #6b7280; line-height: 1.6; margin-top: 4px; }}
  .b5-section {{ margin-top: 14px; }}
  .b5-row {{ display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid var(--border); font-size: 12px; }}
  .b5-label {{ color: var(--text-muted); }}
  .b5-val {{ font-weight: 600; font-size: 11px; max-width: 60%; text-align: right; line-height: 1.4; }}
  .portrait-trust {{ font-size: 12px; color: var(--text-muted); margin-top: 12px; line-height: 1.6; }}
  .trust-label {{ color: #3b82f6; font-weight: 600; margin-right: 6px; }}

  /* ── Needs-Behavior Map ── */
  .nbm-section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
  }}
  .nbm-title {{ font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 16px; }}
  .nbm-list {{ display: flex; flex-direction: column; gap: 14px; }}
  .nbm-item {{
    background: var(--surface-2);
    border-radius: var(--radius-sm);
    padding: 14px;
  }}
  .nbm-behavior {{ font-size: 13px; font-style: italic; color: var(--text); margin-bottom: 4px; }}
  .nbm-arrow {{ font-size: 18px; color: var(--accent-1); margin: 2px 0; }}
  .nbm-need {{ font-size: 13px; font-weight: 700; color: #c084fc; margin-bottom: 6px; }}
  .nbm-decode {{ font-size: 12px; color: var(--text-muted); line-height: 1.6; }}

  /* ── Strategy Quote/Script ── */
  .strategy-reason {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; line-height: 1.5; }}
  .strategy-timing {{
    font-size: 11px;
    color: #a855f7;
    margin-top: 4px;
    font-weight: 500;
  }}
  .strategy-quote {{
    font-size: 11px;
    font-style: italic;
    color: #6b7280;
    padding: 4px 8px;
    border-left: 2px solid rgba(239,68,68,.4);
    margin-top: 6px;
  }}
  .strategy-script {{
    font-size: 11px;
    font-style: italic;
    color: #6b7280;
    padding: 4px 8px;
    border-left: 2px solid rgba(34,197,94,.4);
    margin-top: 6px;
  }}

  /* ── Walk-away Point ── */
  .walkaway-card {{
    background: rgba(239,68,68,.06);
    border: 1px solid rgba(239,68,68,.2);
    border-left: 3px solid #ef4444;
    border-radius: var(--radius-sm);
    padding: 18px 20px;
  }}
  .walkaway-label {{ font-size: 12px; font-weight: 700; color: #ef4444; letter-spacing: .06em; margin-bottom: 10px; }}
  .walkaway-trigger {{ font-size: 13px; color: var(--text-muted); line-height: 1.7; margin-bottom: 6px; }}
  .walkaway-reason {{ font-size: 12px; color: #6b7280; line-height: 1.6; }}

  /* ── Repair Attempts ── */
  .repair-section {{ margin-top: 14px; }}
  .repair-label {{ font-size: 11px; font-weight: 600; color: var(--text-subtle); text-transform: uppercase; letter-spacing: .07em; margin-bottom: 8px; }}
  .repair-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
  .repair-item {{ background: var(--surface-2); border-radius: 6px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }}
  .repair-key {{ font-size: 10px; color: var(--text-subtle); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }}
  .repair-val {{ font-size: 12px; color: var(--text-muted); line-height: 1.5; }}

  /* ── Emotional Availability ── */
  .ea-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 16px 18px;
    margin-top: 12px;
  }}
  .ea-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .ea-label {{ font-size: 12px; font-weight: 700; color: var(--text-muted); }}
  .ea-badge {{ font-size: 11px; font-weight: 700; border: 1px solid; border-radius: 99px; padding: 3px 10px; letter-spacing: .05em; }}
  .ea-evidence {{ font-size: 13px; color: var(--text-muted); line-height: 1.7; margin-bottom: 6px; }}
  .ea-risk {{ font-size: 12px; color: #6b7280; line-height: 1.6; }}

  /* ── Pursue-Distance Loop Steps ── */
  .loop-steps {{ margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }}
  .loop-step {{ display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: var(--text-muted); line-height: 1.5; }}
  .loop-num {{ min-width: 20px; height: 20px; border-radius: 50%; background: rgba(249,115,22,.2); color: #f97316; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}

  /* ── Asymmetry Power/Turning ── */
  .asym-power {{ font-size: 12px; color: var(--text-muted); margin-top: 8px; line-height: 1.6; }}
  .asym-power-label {{ color: #3b82f6; font-weight: 600; margin-right: 6px; }}
  .asym-turning {{ margin-top: 12px; background: var(--surface-2); border-radius: var(--radius-sm); padding: 12px 14px; }}
  .asym-turning-label {{ font-size: 11px; font-weight: 600; color: #eab308; letter-spacing: .06em; }}
  .asym-turning-date {{ font-size: 11px; color: var(--text-subtle); margin-left: 8px; }}
  .asym-turning-event {{ font-size: 12px; color: var(--text-muted); margin-top: 6px; line-height: 1.6; }}

  /* ── Patriarch Wisdom ── */
  .patriarch-wrap {{
    background: linear-gradient(135deg, rgba(251,191,36,.05) 0%, rgba(245,158,11,.03) 100%);
    border: 1px solid rgba(251,191,36,.2);
    border-left: 3px solid #f59e0b;
    border-radius: var(--radius);
    padding: 28px;
    position: relative;
    overflow: hidden;
  }}
  .patriarch-wrap::before {{
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 120px; height: 120px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(251,191,36,.08) 0%, transparent 70%);
    pointer-events: none;
  }}
  .patriarch-avatar-row {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 22px;
  }}
  .patriarch-avatar {{
    font-size: 36px;
    width: 56px;
    height: 56px;
    background: rgba(251,191,36,.1);
    border: 1px solid rgba(251,191,36,.25);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .patriarch-name {{
    font-size: 15px;
    font-weight: 700;
    color: #f59e0b;
    margin-bottom: 4px;
  }}
  .patriarch-subtitle {{
    font-size: 11px;
    color: var(--text-subtle);
    letter-spacing: .04em;
  }}
  .patriarch-read {{
    background: rgba(0,0,0,.2);
    border: 1px solid rgba(251,191,36,.12);
    border-radius: var(--radius-sm);
    padding: 16px 18px;
    margin-bottom: 20px;
  }}
  .patriarch-read-label {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #f59e0b;
    margin-bottom: 8px;
    display: block;
  }}
  .patriarch-read-text {{
    font-size: 14px;
    color: var(--text);
    line-height: 1.8;
    font-style: italic;
  }}
  .patriarch-tactics-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: rgba(251,191,36,.6);
    margin-bottom: 12px;
  }}
  .patriarch-tactics {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .patriarch-tactic {{
    display: grid;
    grid-template-columns: 36px 1fr;
    gap: 12px;
    align-items: start;
    background: rgba(0,0,0,.15);
    border: 1px solid rgba(251,191,36,.1);
    border-radius: var(--radius-sm);
    padding: 14px;
  }}
  .patriarch-tactic-num {{
    font-size: 11px;
    font-weight: 800;
    color: #f59e0b;
    font-variant-numeric: tabular-nums;
    padding-top: 2px;
  }}
  .patriarch-tactic-title {{
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 8px;
  }}
  .patriarch-tactic-logic {{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.7;
    margin-bottom: 8px;
  }}
  .patriarch-tactic-action {{
    font-size: 12px;
    color: #f59e0b;
    background: rgba(245,158,11,.08);
    border: 1px solid rgba(245,158,11,.15);
    border-radius: 6px;
    padding: 8px 12px;
    line-height: 1.6;
  }}
  .patriarch-mistake {{
    background: rgba(239,68,68,.05);
    border: 1px solid rgba(239,68,68,.15);
    border-radius: var(--radius-sm);
    padding: 16px 18px;
    margin-bottom: 20px;
  }}
  .patriarch-mistake-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .08em;
    color: #ef4444;
    margin-bottom: 8px;
  }}
  .patriarch-mistake-text {{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.7;
  }}
  .patriarch-quote {{
    font-size: 15px;
    font-weight: 600;
    color: #f59e0b;
    font-style: italic;
    text-align: center;
    border: none;
    padding: 0;
    margin: 0;
    line-height: 1.7;
    opacity: .9;
  }}
</style>
</head>
<body>

<!-- Hero -->
<header class="hero">
  <p class="hero-eyebrow">深度关系分析</p>
  <h1 class="hero-title">她不一样</h1>
  <p class="hero-contact">与 <span>{escape_html(contact_name)}</span> 的聊天记录</p>
  <p class="hero-date">{date_range[0]} — {date_range[1]} · {total_days} 天 · {basic.get('total_messages', 0):,} 条消息</p>
</header>

<main class="container">

  <!-- 三大指数 -->
  <section class="section">
    <p class="section-label">鉴定指数</p>
    <div class="score-grid">
      <div class="score-card simp">
        <div class="score-emoji">🔥</div>
        <div class="score-label">主动指数</div>
        <div class="score-value">{simp}</div>
        <div class="score-bar"><div class="score-bar-fill" style="width:{simp}%"></div></div>
        {f'<div class="score-desc">{simp_description}</div>' if simp_description else ''}
      </div>
      <div class="score-card loved">
        <div class="score-emoji">💜</div>
        <div class="score-label">被爱指数</div>
        <div class="score-value">{loved}</div>
        <div class="score-bar"><div class="score-bar-fill" style="width:{loved}%"></div></div>
        {f'<div class="score-desc">{love_description}</div>' if love_description else ''}
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
        <span class="ingredient-name">🔥 主动投入</span>
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

  <!-- 语言模式分析 -->
  {f'''<section class="section">
    <p class="section-label">语言模式分析</p>
    {lang_patterns_html}
  </section>''' if lang_patterns_html else ''}

  <!-- ⚠️ 危险预警 -->
  <section class="section">
    <p class="section-label">⚠️ 危险预警</p>
    {danger_warnings_html}
  </section>

  <!-- 关系阶段 -->
  {f'''<section class="section">
    <p class="section-label">关系阶段定位</p>
    {relationship_stage_html}
  </section>''' if relationship_stage_html else ''}

  <!-- 关系分析：Sternberg + Gottman + 情感不对称 -->
  <section class="section">
    <p class="section-label">关系诊断</p>
    <div class="analysis-row">
      <div class="analysis-card">
        <div class="analysis-card-title">Sternberg 爱情三角</div>
        {sternberg_html}
      </div>
      <div class="analysis-card">
        <div class="analysis-card-title">Gottman 关系健康度</div>
        {gottman_html}
      </div>
    </div>
    {f'''<div class="analysis-card" style="margin-top:12px">
      <div class="analysis-card-title">情感投入不对称</div>
      {emotional_asym_html}
    </div>''' if emotional_asym_html else ''}
  </section>

  <!-- 人格分析 -->
  <section class="section">
    <p class="section-label">人格与依恋分析</p>
    {personality_html}
  </section>

  <!-- 人格深度画像 -->
  {f'''<section class="section">
    <p class="section-label">人格深度画像 🧬</p>
    {portrait_html}
  </section>''' if portrait_html else ''}

  <!-- 军师建议 -->
  <section class="section">
    <p class="section-label">🎯 军师建议</p>
    {strategist_html}
  </section>

  <!-- 祖师爷寄语 -->
  {f'''<section class="section">
    <p class="section-label">👴 祖师爷寄语 · 童锦程</p>
    {patriarch_wisdom_html}
  </section>''' if patriarch_wisdom_html else ''}

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
      <div class="verdict-meta-row">
        <span class="verdict-type-badge">她不一样 · 深度分析报告</span>
        {f'<span class="verdict-trend-badge">{trend_icon} {relationship_trend}</span>' if relationship_trend else ''}
      </div>
      <div class="verdict-type">{relationship_type}</div>
      <div class="verdict-label">{relationship_label}</div>
      <div class="verdict-divider"></div>
      <div class="verdict-text">{verdict}</div>
    </div>
  </section>

</main>

<footer class="footer">
  <p style="margin:0 0 14px;font-size:14px;line-height:1.9;color:var(--text-muted);max-width:620px;margin-left:auto;margin-right:auto;font-style:italic;opacity:.85;">
    你愿意走到这里，本身就已经说明了一切。<br>
    能为一段感情认真复盘、鼓起勇气直视现实的人，从来不缺被爱的资格。<br>
    算法能还原对话的节奏，却读不懂你在屏幕前的那一声心跳。<br>
    这份报告是一面镜子——照见的是数据，照不见的，才是真正的你们。<br><br>
    放下这份冰冷的报告，去现实里，用真心换真心。<br>
    爱情从来不需要算法背书，它只需要你，开口。
  </p>
  仅供参考 · 数据本地处理，不上传任何服务器 · <a href="https://github.com/863401402/she-love-me" target="_blank" style="color:inherit;opacity:.6;text-decoration:none;">她不一样 · 开源地址</a> · {date_str}
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
    labels: ['你', '{escape_html(contact_name)}'],
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
