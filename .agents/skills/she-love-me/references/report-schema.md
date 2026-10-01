# analysis.json Schema

完整的 AI 分析结果 JSON 结构定义。Step 7 完成分析后保存到 `data/analysis.json`。

---

## 评分推导规则

### 证据回查协议（analysis schema_version 2.1）

新分析必须加入顶层 `schema_version: "2.1"` 和 `messages_digest`，摘要从当前 `stats.json` 或 `chat_history.txt` 原样复制，不自行编造。每条 `key_findings` 和 `danger_warnings` 必须带非空 `evidence_message_ids`，ID 从采样文件 `[id=msg_...]` 原样复制。引用依据仍应满足下方分析框架，不因具备 ID 就视为推断成立。

```json
{
  "schema_version": "2.1",
  "messages_digest": "复制当前消息数据的 SHA-256 摘要",
  "prompt_version": "evidence-2.1",
  "model": "填写实际使用的模型，未知则 null",
  "key_findings": [
    {
      "title": "对方表达想念",
      "quote": "想你",
      "analysis": "本次对话中对方直接表达想念，单条表达不足以判断长期承诺。",
      "evidence_level": "low",
      "evidence_message_ids": ["复制真实消息的完整 msg_ ID"],
      "stats_fields": ["basic.total_messages"]
    }
  ]
}
```

上例为字段示意，不可直接拿占位符生成报告。`evidence_level` 可为 `high` / `medium` / `low` / `insufficient`；引用 `quote` 必须是关联消息正文或转写的真实连续片段，多条消息的引用分别填写。`stats_fields` 使用点分路径（如 `initiative.my_starts`），字段必须存在；缺失值不得充当中高等级证据。其他分析模块也可以加入这两个引用数组，报告会递归校验并展示。

报告生成时传入 `--messages "<bundle_dir>/messages.json"`，省略时会寻找 `stats.json` 同目录的消息文件。统计、分析和消息摘要不一致，或 ID / 原文不匹配时停止生成；重新统计并重做分析后再生成。每份报告的 `.manifest.json` 保存对应统计和分析快照，允许复查当时的结论；引用存在的校验不等于语境推断已被证明。

### 统计可靠性约定（stats_version 2.2）

- `reply_speed.my_avg_seconds` / `their_avg_seconds` / `speed_ratio` 在无有效样本时为 `null`。先检查 `my_sample_count` / `their_sample_count`，不得把 `null` 当作 0 秒、秒回或不回复的证据。
- 回复间隔口径是相邻双方消息的 10 秒至 24 小时间隔，另有中位数和 P90；不包含阅读状态。不得仅凭间隔写“已读不回”。
- 对称性评分从 `balance_calibration` 原样读取；缺失维度、权重覆盖及原因由统计引擎返回，不能把缺失维度当作平衡。
- `cold_response` 只表示词表候选命中，`requires_context=true`；`my_short_count` / `their_short_count` 是中性的短句统计。不能把“嗯”“哈哈”“好的”等词表命中直接认定为冷淡，要结合相邻对话。
- 冷淡词表比例以各方 `my_text_count` / `their_text_count` 为分母，避免表情和图片稀释文字比例。没有文本样本不代表态度热情。
- `scoring_version=2.2` 的分数为行为启发式指标；不得解释为爱情概率。比较历史报告前，使用同一算法版本重新统计，并核对有效维度与权重覆盖是否一致。

在填写以下三类评分前，**必须先从 `data/stats.json` 读取对应字段**，以统计数据为基础推导，再用文本证据校正，不得凭感觉直接写数字。

### 对称性评分（symmetry_score，0–10）

从 `stats.json.balance_calibration.symmetry_score` 原样读取（包括 `null`），不得由 Agent 自行打分或文本调分。报告优先展示统计引擎结果；证据版分析中的分数与引擎不一致时会停止生成。

引擎对四个维度都使用 `2 × min(双方观测值) / (双方观测值之和)`，值域 0–1，交换双方后结果不变：

| 维度 | 观测值 | 权重 | 最小样本 |
| --- | --- | --- | --- |
| initiative | 双方对话发起次数 | 30% | 合计 4 次 |
| reply | 双方有效回复间隔中位数 | 20% | 各 3 个有效间隔 |
| resumption | 双方在超过 24 小时沉默后恢复发言的次数 | 30% | 合计 2 次 |
| messages | 双方消息量 | 20% | 合计 20 条 |

仅当消息量和对话发起维度有效、且有效权重覆盖至少 70% 时输出分数：`round(10 × 有效维度加权和 / 有效权重覆盖, 1)`；否则为 `null`。样本门槛和权重是项目启发式规则，尚未经过实证校准，不代表统计置信度。

`investment_direction` 独立描述双方消息量、发起、沉默后恢复的占比。只有消息量和发起占比均超过 60% / 低于 40% 时，标为偏向我方 / 对方；不能从低对称分数推断偏向哪一方，更不能据此断言谁更爱谁。

必须说明分数、有效权重覆盖、缺失维度及原因。没有长沉默样本不代表恢复行为对等；沉默后恢复不等于冲突修复。文本分析独立记录在 `symmetry_derivation`、`anchor_description` 等字段，并附证据。若量化低分且文本与方向共同支持明显单向投入，再按危险预警双阈值规则处理。

### Sternberg 三角（passion / intimacy / commitment，各 0–100）

每个维度由文本信号**计数累积**，不是凭感觉写。

| 维度 | 计数信号 | 满分对应 |
|------|---------|---------|
| 激情 passion | 见面渴望表达、"想你/好想见你"、亲密称呼密度、肢体/情欲描述 | 10+ 个信号 → 90+ 分 |
| 亲密 intimacy | 脆弱分享（且对方有回应）、深度情感倾诉次数、共同记忆引用、互相支持事件 | 10+ 个信号 → 90+ 分 |
| 承诺 commitment | 含具体时间/地点的未来规划、危机后主动坚持、"我们"后跟具体行动 | 6+ 个信号 → 90+ 分 |

**必须列举具体计入的信号原文**，不得只给分数。

### Gottman 正负比（positive_negative_ratio）

**优先读取 `stats.json` 中的 `positive_emotion_count` 和 `negative_emotion_count`**，计算基础比值。

然后用文本判断校正以下边界情况（`stats.json` 词典无法区分的）：
- 「随便」：在冷战语境 → 计入负向；在轻松语境 → 不计
- 「无所谓」：在拒绝情感请求后 → 计入负向；作为口头禅 → 不计
- 讽刺/反语：词面积极但语境贬低 → 计入负向（蔑视）

**输出格式**：「Gottman 比值 X.X:1（词典统计基础值 X.X，文本校正 ±X.X，原因：[具体说明]）」

---

## 可空字段规则

以下字段允许输出 `null`，当且仅当证据不足时。**不得为了"完整"而强行推断**。

使用以下结构代替 `null`，保留可观察到的信号：

```json
{
  "value": null,
  "evidence_level": "insufficient",
  "reason": "证据不足的具体原因",
  "observable_signals": ["能观察到的信号1", "能观察到的信号2"]
}
```

| 字段 | 输出 null 的条件 |
|------|----------------|
| `partner_attachment` | 对方文字消息不足 80 条，或行为模式高度混合无法归类 |
| `core_fear` | 未识别到明确的触发情境与防御反应对 |
| `trauma_bonding` | 无痛苦经历与粘连程度同时升高的共现模式 |
| `future_faking` | 聊天记录中无未来承诺类语句 |
| `fatal_mistake` | 未发现明显的自我价值损耗行为 |
| `advancement_path` | 关系类型为「名存实亡」或「朋友边界」时 |
| `pursue_distance_loop` | 未发现典型追逃案发现场 |

---

## 完整 JSON Schema

```json
{
  "relationship_type": "深陷单恋",
  "relationship_label": "严重单向投入，建议认真评估关系价值",
  "relationship_trend": "逐渐降温",

  "relationship_stage": {
    "stage": "实名化前夜",
    "stage_description": "情感深度已达情侣水准，但缺少一个正式确认的仪式。",
    "is_situationship": true,
    "situationship_evidence": "双方互称老公老婆，有过线下亲密，但从未明确定义关系",
    "stage_risk": "长期不确定性会加剧焦虑型依恋的追逃循环",
    "advancement_path": "需要一次明确的、低压力的关系定义对话——不是逼问，而是自然表达"
  },

  "emotional_asymmetry": {
    "symmetry_score": 4,
    "symmetry_derivation": "你发起对话占比 72%，双方平均回复时间差 4.2 小时，修复发起比 7:1，消息量比 65:35",
    "anchor_person": "me",
    "anchor_description": "用户明显是关系中投入更多的那个，对方处于观望和评估状态",
    "conflict_pattern": "用户在冲突中倾向于追，对方倾向于沉默或撤退",
    "power_dynamics": "话题发起：你 XX 次 vs 对方 XX 次；话题终结：你 XX 次 vs 对方 XX 次",
    "key_turning_point": {
      "date": "YYYY-MM-DD",
      "event": "那次关于XX的争吵后，对方回复速度断崖式下降，从分钟级变为天级"
    }
  },

  "personality_portrait": {
    "user": {
      "core_traits": ["热情投入", "情绪敏感", "缺乏边界感"],
      "defense_mechanisms": [
        {
          "type": "情感轰炸",
          "trigger": "感到对方疏远或不回应时",
          "evidence": "「你怎么了？你不理我了？你是不是不喜欢我了？」连发三条",
          "real_meaning": "用信息量掩盖内心恐惧，但这恰恰会让回避型对方更想逃"
        }
      ],
      "core_fear": {
        "value": "被抛弃恐惧",
        "evidence_level": "high",
        "evidence": "频繁确认「你还在吗」、消息未秒回即追问，行为模式一致"
      },
      "core_needs": "被选中感和确定性",
      "needs_behavior_map": [
        {
          "behavior": "连续发消息没有回应还继续发",
          "need": "需要确认对方还在，关系还在",
          "decode": "焦虑型依恋的超激活策略"
        }
      ],
      "trust_architecture": "信任一旦建立很坚固，但需要对方持续的一致性行为来维持",
      "big_five_sketch": {
        "conscientiousness": "中",
        "neuroticism": "高 — 情绪波动明显，对对方的细微变化高度敏感",
        "agreeableness": "高 — 倾向于迎合对方，难以表达自己的不满",
        "openness": "中",
        "extraversion": "高 — 主动发起互动，用语言和情感词填充对话空间"
      }
    },
    "partner": {
      "core_traits": ["清醒理性", "自我保护", "高度自主"],
      "defense_mechanisms": [
        {
          "type": "防御性撤退",
          "trigger": "感到关系威胁到自己的独立性或未来规划时",
          "evidence": "「我们不合适」「一开始就是错的」",
          "real_meaning": "情绪低落时的自我保护，说完后通常还是会主动联系"
        }
      ],
      "core_fear": {
        "value": null,
        "evidence_level": "insufficient",
        "reason": "观察到防御性撤退行为，但核心恐惧类型（被吞噬 vs 被贬低）信号混合，无法可靠归类",
        "observable_signals": ["在感情升温时突然消失", "强调独立/事业"]
      },
      "core_needs": "唯一性与确定性",
      "needs_behavior_map": [
        {
          "behavior": "提事业/不想虚度/担心被耽误",
          "need": "保留自我价值感和独立性",
          "decode": "在测试这段关系是否值得她放弃部分控制感"
        }
      ],
      "trust_architecture": "信任建立缓慢但一旦建立会深度投入",
      "big_five_sketch": {
        "conscientiousness": "高 — 事业心强，有清晰的人生规划",
        "neuroticism": "中高 — 外表清醒，内心细腻",
        "agreeableness": "中",
        "openness": "中",
        "extraversion": "中 — 有边界感，选择性开放"
      }
    }
  },

  "language_patterns": {
    "pronoun_we_ratio": "「我们」合计出现约 XX 次",
    "hedging_density": "高 — 对方频繁使用「也许/感觉/好像」",
    "future_orientation": "中性偏虚 — 有未来规划的表达，但多数未落地为具体行动",
    "emotional_valence_ratio": "用户正负比约 3:1，对方正负比约 2:1",
    "conditional_density": "高 — 对方频繁使用条件句",
    "key_linguistic_finding": "对方在同一段对话中同时出现「我会好好爱你」和「我们不合适」"
  },

  "sternberg": {
    "passion": 70,
    "passion_signals": ["「好想见你」出现 8 次", "亲昵称呼密度高", "3 次肢体亲近描述"],
    "intimacy": 40,
    "intimacy_signals": ["2 次脆弱分享（家庭话题）", "对方有回应 1 次", "共同记忆引用 3 次"],
    "commitment": 20,
    "commitment_signals": ["「以后」出现 5 次但无具体时间地点", "危机后坚持 1 次"],
    "love_type": "浪漫之爱（Romantic Love）"
  },

  "gottman": {
    "positive_negative_ratio": 2.3,
    "ratio_derivation": "词典统计基础值 2.8，文本校正 -0.5（识别到 3 处讽刺性「随便」计入蔑视）",
    "horsemen_detected": ["蔑视", "冷战/筑墙"],
    "risk_level": "高危",
    "repair_attempts": {
      "who_initiates": "me",
      "method": "发表情包/转移话题",
      "partner_response": "继续冷漠，拒绝接受修复",
      "success_rate": "约 2/5 次成功，修复弹性较低"
    }
  },

  "personality": {
    "user_attachment": "焦虑型（Anxious-Preoccupied）",
    "partner_attachment": {
      "value": "恐惧型（Fearful-Avoidant）",
      "evidence_level": "medium",
      "reason": "同时具有高焦虑和高回避信号，但样本中有 2 段反常行为待解释",
      "observable_signals": ["忽冷忽热", "主动靠近后拉开距离", "撤回情感消息"]
    },
    "pursue_distance_cycle": true,
    "pursue_distance_loop": {
      "trigger": "我说了「你今天好像有点冷漠」，触发了TA的被吞噬恐惧",
      "retreat": "TA停止回复，消失了两天",
      "escalation": "我连发5条消息追问「你怎么了」",
      "deterioration": "此次循环后，TA的平均回复时间从2小时增至1天"
    },
    "emotional_availability": {
      "level": "低",
      "evidence": "对方在我倾诉脆弱时总是回「嗯」或给建议，从未深入共情",
      "risk_note": "对方当前情感通道基本关闭，继续高强度投入只会换来失望"
    },
    "user_communication": "情绪型 + 迎合型",
    "partner_communication": "事务型 + 防御性开放型",
    "user_love_language": "肯定的言辞",
    "partner_love_language": "精心的时刻",
    "love_language_mismatch": true
  },

  "danger_warnings": [
    {
      "type": "间歇性强化",
      "level": "中危",
      "trigger_met": {
        "quantitative": "近30天我方主动占比 78%，对方修复次数 0，消息密度方差系数 0.82（高度不均匀）",
        "textual": "用户消息中出现「她今天回我了是不是说明在意我」类解读 3 次，连续未回复后追发 ≥3 条事件 7 次"
      },
      "evidence": "对方每隔3-5天会突然热情一次，其余时间几乎不回复"
    }
  ],

  "strategist": {
    "core_problem": "你是焦虑型，TA是恐惧型，你们正陷入追逃循环",
    "stop_doing": [
      {
        "action": "停止连续发送多条未回复的消息",
        "reason": "这会让恐惧型对方感到窒息并触发防御性撤退",
        "quote": "「你在吗？你怎么了？你不理我了？」——你发了三条，TA消失了两天"
      }
    ],
    "start_doing": [
      {
        "action": "回复后留白，给对方来找你的空间",
        "timing": "在对方下次主动找你之后，或断联满5天后",
        "reason": "恐惧型需要感到「是我在选择亲近」",
        "script": "分享一件有趣的事然后结尾，不问问题"
      }
    ],
    "roadmap": "未来两周：减少主动联系频率，观察对方是否主动。",
    "walkaway_point": {
      "timeframe": "2周",
      "trigger": "对方再次出现超过3天已读不回，或在执行策略后依然无任何主动联系",
      "reason": "此时继续投入的成本已超出任何可能的回报"
    }
  },

  "key_findings": [
    {
      "title": "发现1标题",
      "quote": "原始消息引用",
      "analysis": "解读"
    }
  ],

  "patriarch_wisdom": {
    "situation_read": "说实话兄弟，我看完你们的聊天记录——[童锦程口吻的直接点评，1-2句话]",
    "advance_tactics": [
      {
        "title": "让她对你产生吸引",
        "logic": "我跟你说，[为什么有效的逻辑]——知道吧？",
        "action": "[具体话术或行动指引]"
      }
    ],
    "fatal_mistake": {
      "value": null,
      "evidence_level": "insufficient",
      "reason": "未发现明显的、系统性的自我价值损耗行为，不强行归结一条"
    },
    "closing_quote": "[一句最契合当前局面的童锦程式语录]"
  },

  "simp_description": "统计维度的单向投入行为描述（若存在严重不对等，此处必须直接指出）",
  "love_description": "统计维度的被爱信号描述",
  "verdict": "综合鉴定结论（2-3句话，幽默但有洞察力）"
}
```
