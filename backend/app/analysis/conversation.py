import re
from dataclasses import dataclass
from typing import List, Optional

from app.schemas import (
    AnalysisOverview,
    ConversationAnalysisResponse,
    Hypothesis,
    MessageInsight,
    TurningPoint,
)

POSITIVE_WORDS = {"谢谢", "理解", "好", "愿意", "支持", "抱歉", "辛苦", "在意", "可以"}
NEGATIVE_WORDS = {"烦", "失望", "算了", "没必要", "生气", "累", "问题", "躲", "审问", "随你"}
ANXIOUS_WORDS = {"是不是", "有点", "以为", "担心", "怕", "不知道", "吗", "？", "?"}
DEFENSIVE_PATTERNS = ("我没有", "不是这个意思", "别想太多", "随你", "我只是", "你怎么又", "够累了")
PRESSURE_PATTERNS = ("必须", "现在就", "应该", "赶紧", "一直", "每次", "总是")
REPAIR_PATTERNS = ("抱歉", "不是想", "我在意", "理解", "我们可以")
QUESTION_MARKERS = ("？", "?", "吗")
MESSAGE_RE = re.compile(
    r"^\s*(?:\[(?P<timestamp>[^\]]+)\]\s*)?(?P<speaker>[^:：\n]{1,20})[:：]\s*(?P<content>.+?)\s*$"
)


@dataclass
class ParsedMessage:
    message_id: str
    speaker: str
    content: str
    timestamp: Optional[str]


def _parse_messages(text: str) -> List[ParsedMessage]:
    parsed: List[ParsedMessage] = []
    fallback_speaker = ["角色A", "角色B"]
    fallback_idx = 0

    for index, raw_line in enumerate([line for line in text.splitlines() if line.strip()], start=1):
        match = MESSAGE_RE.match(raw_line)
        if match:
            parsed.append(
                ParsedMessage(
                    message_id=f"msg_{index:02d}",
                    speaker=match.group("speaker").strip(),
                    content=match.group("content").strip(),
                    timestamp=match.group("timestamp"),
                )
            )
            continue

        speaker = fallback_speaker[fallback_idx % 2]
        fallback_idx += 1
        parsed.append(
            ParsedMessage(
                message_id=f"msg_{index:02d}",
                speaker=speaker,
                content=raw_line.strip(),
                timestamp=None,
            )
        )
    return parsed


def _emotion_for(content: str) -> str:
    score = 0
    if any(word in content for word in POSITIVE_WORDS):
        score += 1
    if any(word in content for word in NEGATIVE_WORDS):
        score -= 2
    if any(word in content for word in ANXIOUS_WORDS):
        score -= 1
    if any(pattern in content for pattern in DEFENSIVE_PATTERNS):
        score -= 1

    if score <= -3:
        return "防御/不耐烦"
    if score == -2:
        return "受伤/紧张"
    if score == -1:
        return "试探/不安"
    if score == 0:
        return "中性"
    return "修复/靠近"


def _intents_for(content: str) -> List[str]:
    intents: List[str] = []
    if any(marker in content for marker in QUESTION_MARKERS):
        intents.append("试探")
    if any(pattern in content for pattern in DEFENSIVE_PATTERNS):
        intents.append("防御")
    if any(pattern in content for pattern in PRESSURE_PATTERNS):
        intents.append("施压")
    if any(pattern in content for pattern in REPAIR_PATTERNS):
        intents.append("修复")
    if "答应" in content or "说一声" in content:
        intents.append("追责/确认")
    if "躲我" in content or "审问" in content:
        intents.append("关系定性")
    if not intents:
        intents.append("信息陈述")
    return intents[:3]


def _strategy_for(intents: List[str]) -> str:
    if "防御" in intents:
        return "保护自我位置"
    if "施压" in intents:
        return "推动对方表态"
    if "修复" in intents:
        return "尝试降温"
    if "试探" in intents:
        return "低风险探测关系状态"
    return "直接陈述"


def _impact_for(content: str, intents: List[str]) -> int:
    impact = 0
    if any(word in content for word in POSITIVE_WORDS):
        impact += 1
    if any(word in content for word in NEGATIVE_WORDS):
        impact -= 1
    if "防御" in intents:
        impact -= 1
    if "施压" in intents:
        impact -= 2
    if "修复" in intents:
        impact += 1
    return max(-3, min(2, impact))


def analyze_conversation(text: str, expected_outcome: Optional[str] = None) -> ConversationAnalysisResponse:
    messages = _parse_messages(text)
    insights: List[MessageInsight] = []
    turning_points: List[TurningPoint] = []

    relationship_temperature = 62
    conflict_risk = 18
    previous_temperature = relationship_temperature

    counts = {"试探": 0, "防御": 0, "施压": 0, "修复": 0, "关系定性": 0}

    for item in messages:
        intents = _intents_for(item.content)
        emotion = _emotion_for(item.content)
        strategy = _strategy_for(intents)
        impact = _impact_for(item.content, intents)

        for intent in intents:
            if intent in counts:
                counts[intent] += 1

        relationship_temperature = max(0, min(100, relationship_temperature + impact * 6))
        conflict_risk = max(0, min(100, conflict_risk + max(0, -impact) * 8))

        insight = MessageInsight(
            message_id=item.message_id,
            speaker=item.speaker,
            content=item.content,
            timestamp=item.timestamp,
            surface_meaning=item.content,
            emotion=emotion,
            intents=intents,
            strategy=strategy,
            relationship_impact=impact,
            evidence_level="direct",
        )
        insights.append(insight)

        drop = previous_temperature - relationship_temperature
        if impact <= -2 or drop >= 10 or ("关系定性" in intents and "防御" in intents):
            turning_points.append(
                TurningPoint(
                    event_id=item.message_id,
                    title=f"{item.speaker}让对话性质发生变化",
                    reason=f"这句话带有{','.join(intents)}倾向，关系温度单轮变化 {drop if drop > 0 else abs(impact) * 6} 点。",
                    severity="high" if impact <= -2 else "medium",
                )
            )
        previous_temperature = relationship_temperature

    if not turning_points and insights:
        last = insights[-1]
        turning_points.append(
            TurningPoint(
                event_id=last.message_id,
                title="对话走向冷处理",
                reason="结尾没有完成修复，留下了开放冲突。",
                severity="medium",
            )
        )

    if counts["试探"] >= 2 and counts["防御"] >= 2:
        path = ["试探落空", "不安累积", "解释不被接住", "防御性表达上升", "关系降温"]
        summary = "主因更像是试探没有被稳定接住，随后双方把“解释问题”升级成了“态度判断”。"
    elif counts["施压"] >= 2:
        path = ["需求不匹配", "追责上升", "施压触发抗拒", "沟通中断"]
        summary = "核心问题更像是需求长期不匹配，本段对话只是把冲突显性化。"
    else:
        path = ["轻微误会", "未及时澄清", "负面解读累积", "互动热度下降"]
        summary = "关系变冷主要由未澄清的小误会累计，而不是单次爆发。"

    positive_messages = [m for m in insights if m.relationship_impact > 0]
    negative_messages = [m for m in insights if m.relationship_impact < 0]

    main_hypothesis = Hypothesis(
        title="主解释路径",
        summary=summary,
        path=path,
        supporting_evidence=[
            f"{m.message_id} {m.speaker}: {m.content}" for m in negative_messages[:4]
        ],
        counter_evidence=[
            f"{m.message_id} {m.speaker}: {m.content}" for m in positive_messages[:2]
        ] or ["样本中仍有在意与修复表述，说明并非彻底破裂。"],
        confidence=0.74 if counts["试探"] and counts["防御"] else 0.66,
    )

    alternative_hypothesis = Hypothesis(
        title="备选解释路径",
        summary="也可能不是误会主导，而是双方对互动频率和回应义务的期待本来就不同，这次只是集中暴露。",
        path=["期待不一致", "忙碌被理解成回避", "追问被理解成压力", "沉默替代表达"],
        supporting_evidence=[
            f"{m.message_id} 出现对‘一直回消息/答应的事’的期待差异。"
            for m in insights
            if "一直回消息" in m.content or "答应" in m.content
        ][:3]
        or ["样本中多次出现对回应频率和责任边界的争执。"],
        counter_evidence=[
            "对话里仍有“我在意”“不是想逼你”这样的修复尝试，说明双方并非完全价值冲突。"
        ],
        confidence=0.58,
    )

    outcome = expected_outcome or "为什么关系降温"
    overview = AnalysisOverview(
        title=outcome,
        summary="系统没有把这段对话当成单句情绪识别，而是按‘事件 -> 意图 -> 关系温度 -> 转折点’回溯形成链。",
        key_judgement=summary,
        uncertainty="缺少这段聊天前后的上下文，无法判断当前语气是偶发波动还是稳定模式。",
    )

    return ConversationAnalysisResponse(
        overview=overview,
        messages=insights,
        turning_points=turning_points[:4],
        main_hypothesis=main_hypothesis,
        alternative_hypothesis=alternative_hypothesis,
        missing_evidence=[
            "补充前一周的聊天记录，确认这种语气是否是长期模式。",
            "补充线下事件背景，判断‘忙碌’是真实压力还是回避策略。",
            "补充双方约定过的关键事项，确认追问是否基于先前承诺。",
        ],
        relationship_temperature=relationship_temperature,
        conflict_risk=conflict_risk,
    )
