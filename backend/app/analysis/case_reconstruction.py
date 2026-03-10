import re
from collections import Counter
from typing import List, Optional

from app.schemas import (
    ActorCard,
    AnalysisOverview,
    CaseAnalysisResponse,
    Hypothesis,
    TimelineEvent,
    TurningPoint,
)

SUSPICIOUS_WORDS = ("缺失", "覆盖", "空窗", "提前", "统一口径", "矛盾", "封存", "未提交", "争执")
PRESSURE_HINTS = {
    "信息不对称": ("缺失", "覆盖", "空窗", "未提交"),
    "利益约束": ("高价值", "保险", "损失预估", "样品区"),
    "组织压强": ("统一口径", "总监", "要求", "封存"),
    "证词波动": ("矛盾", "争执", "有人说"),
}


def _extract_lines(text: str) -> List[str]:
    return [line.strip(" -\t") for line in text.splitlines() if line.strip()]


def _time_hint(line: str) -> str:
    match = re.match(r"^([^|]+)\|", line)
    return match.group(1).strip() if match else "时间未明"


def _detail(line: str) -> str:
    if "|" in line:
        return line.split("|", 1)[1].strip()
    return line


def _event_type(detail: str) -> str:
    if "起火" in detail or "事故" in detail:
        return "incident"
    if "报告" in detail or "称" in detail:
        return "statement"
    if "要求" in detail or "统一口径" in detail:
        return "decision"
    if "监控" in detail or "日志" in detail:
        return "evidence"
    return "context"


def _pressure_score(detail: str) -> int:
    score = 1
    for word in SUSPICIOUS_WORDS:
        if word in detail:
            score += 2
    if "起火" in detail:
        score += 2
    return min(score, 10)


def _extract_actors(details: List[str]) -> List[str]:
    pool: List[str] = []
    for detail in details:
        pool.extend(re.findall(r"[\u4e00-\u9fff]{2,4}", detail))
    stopwords = {
        "仓库", "火灾", "监控", "画面", "日志", "要求", "内部", "会议", "损失",
        "报告", "联系", "样品", "值班", "维修", "员工", "正式", "偶发", "短路",
    }
    counts = Counter(token for token in pool if token not in stopwords)
    names = [name for name, _ in counts.most_common(6)]
    return names or ["安保", "财务", "维修方"]


def analyze_case(text: str, expected_outcome: Optional[str] = None) -> CaseAnalysisResponse:
    lines = _extract_lines(text)
    details = [_detail(line) for line in lines]
    actors = _extract_actors(details)

    timeline: List[TimelineEvent] = []
    turning_points: List[TurningPoint] = []

    for index, raw_line in enumerate(lines, start=1):
        detail = _detail(raw_line)
        pressure_score = _pressure_score(detail)
        time_hint = _time_hint(raw_line)
        related_actors = [actor for actor in actors if actor in detail][:3]

        timeline.append(
            TimelineEvent(
                event_id=f"evt_{index:02d}",
                label=detail[:28] + ("..." if len(detail) > 28 else ""),
                detail=detail,
                time_hint=time_hint,
                actors=related_actors or ["未标明角色"],
                event_type=_event_type(detail),
                pressure_score=pressure_score,
            )
        )

        if pressure_score >= 5:
            turning_points.append(
                TurningPoint(
                    event_id=f"evt_{index:02d}",
                    title="叙事可信度被削弱",
                    reason=f"该事件出现了高风险线索：{detail}",
                    severity="high" if pressure_score >= 7 else "medium",
                )
            )

    hidden_factors: List[str] = []
    for factor, words in PRESSURE_HINTS.items():
        if any(word in text for word in words):
            hidden_factors.append(factor)
    if not hidden_factors:
        hidden_factors.append("信息缺口")

    actor_cards = [
        ActorCard(
            name=actor,
            role_guess="关键节点相关方",
            state="处在信息压力或责任压力中",
            motives=["自保", "控制外部叙事", "降低追责风险"],
        )
        for actor in actors[:4]
    ]

    main_hypothesis = Hypothesis(
        title="主解释路径",
        summary="‘纯意外’叙事被削弱，不是因为已经证明存在故意纵火，而是因为多个关键证据点在事故前后都出现了异常中断、口径收束和时间顺序不自然。",
        path=[
            "基础事故发生",
            "关键记录出现缺口",
            "高价值区域先被关注而非先查原因",
            "证词和物证开始相互打架",
            "组织层面推动单一路径解释",
        ],
        supporting_evidence=[
            f"{event.event_id} {event.detail}" for event in timeline if event.pressure_score >= 5
        ][:5],
        counter_evidence=[
            "维修承包商提供了线路老化解释，说明事故性原因并非完全不存在。",
            "现有材料还没有直接证据证明有人在起火前实施破坏。",
        ],
        confidence=0.71,
    )

    alternative_hypothesis = Hypothesis(
        title="备选解释路径",
        summary="另一种更保守的解释是：事故原因为短路，但事故后的应急和责任管理非常混乱，结果制造出了像‘人为掩盖’的外观。",
        path=[
            "真实事故触发",
            "应急流程失序",
            "记录保存不规范",
            "管理层过早统一表述",
            "外部观察者据此怀疑掩盖",
        ],
        supporting_evidence=[
            "材料里出现了线路老化、记录缺失、员工口径不一致，混乱管理可以解释其中一部分异常。",
        ],
        counter_evidence=[
            "保险预估早于正式报告、监控空窗与门磁覆盖叠加，单靠‘混乱’解释会显得过轻。",
        ],
        confidence=0.54,
    )

    case_temperature = min(100, 35 + sum(event.pressure_score for event in timeline))

    overview = AnalysisOverview(
        title=expected_outcome or "案情重演",
        summary="系统把碎片材料按时间序、证据等级和隐藏压力重新编织，目标不是宣布真相，而是重建更可信的形成链。",
        key_judgement=main_hypothesis.summary,
        uncertainty="当前材料更像是‘异常堆叠’，仍缺直接物证来判断异常是掩盖、渎职还是偶然混乱。",
    )

    return CaseAnalysisResponse(
        overview=overview,
        actors=actor_cards,
        timeline=timeline,
        hidden_factors=hidden_factors,
        turning_points=turning_points[:4],
        main_hypothesis=main_hypothesis,
        alternative_hypothesis=alternative_hypothesis,
        missing_evidence=[
            "补充原始监控和门禁日志的只读备份，确认空窗和覆盖是否为人为操作。",
            "补充消防、保险、承包商三方的原始时间戳，核对谁最先知道损失规模。",
            "补充事故前一周的维修单与人员出入记录，确认是否存在提前预兆。",
        ],
        case_temperature=case_temperature,
    )
