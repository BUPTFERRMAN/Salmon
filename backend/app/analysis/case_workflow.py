import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from app.analysis.llm import OpenAICompatibleClient
from app.core.document_parser import DocumentParser
from app.schemas import (
    AgentExchange,
    AgentProfile,
    AgentStep,
    AgentTurnResponse,
    CaseFinalResult,
    CaseParseResponse,
    CaseReasonResponse,
    CaseSynthesisResponse,
    CaseWorkflowResponse,
    EvidenceDetail,
    EvidenceItem,
    GraphEdge,
    GraphNode,
    OutputPanel,
    PipelineStep,
    ReconstructionStep,
    SuspectRank,
    UploadedDocument,
)

L10N = {
    "zh-CN": {
        "default_outcome": "\u8bf7\u91cd\u5efa\u8fd9\u8d77\u6848\u4ef6\u7684\u5f62\u6210\u94fe\u6761\u3002",
        "unknown_time": "\u65f6\u95f4\u672a\u660e",
        "summary": "\u6750\u6599\u6765\u81ea {source}\uff0c\u5f53\u524d\u4efb\u52a1\u662f\u56f4\u7ed5\u201c{outcome}\u201d\u91cd\u5efa\u66f4\u5b8c\u6574\u7684\u6210\u56e0\u94fe\u3002",
        "few_clues": "\u5f53\u524d\u6750\u6599\u4e2d\u7684\u663e\u5f0f\u5f02\u5e38\u4ecd\u7136\u504f\u5c11\uff0c\u5efa\u8bae\u8865\u5145\u539f\u59cb\u8bb0\u5f55\u3001\u7ed3\u6784\u56fe\u6216\u8bc1\u8a00\u3002",
        "no_hard_evidence": "\u5f53\u524d\u4ecd\u7f3a\u5c11\u80fd\u76f4\u63a5\u9501\u5b9a\u5176\u884c\u4e3a\u7684\u786c\u7269\u8bc1\u3002",
        "uncertainty_1": "\u5f53\u524d\u4e3b\u5047\u8bbe\u80fd\u591f\u89e3\u91ca\u5927\u591a\u6570\u7ebf\u7d22\uff0c\u4f46\u4ecd\u7f3a\u5c11\u76f4\u63a5\u628a\u884c\u4e3a\u3001\u88c5\u7f6e\u548c\u5acc\u7591\u5bf9\u8c61\u9501\u6b7b\u7684\u786c\u8bc1\u636e\u3002",
        "uncertainty_2": "\u5982\u679c\u80fd\u8865\u5145\u539f\u59cb\u76d1\u63a7\u3001\u95e8\u7981\u3001\u533b\u5b66\u9274\u5b9a\u6216\u66f4\u5b8c\u6574\u8bc1\u8bcd\uff0c\u5acc\u7591\u4eba\u6392\u5e8f\u4f1a\u660e\u663e\u66f4\u7a33\u5b9a\u3002",
        "verdict_strong": "\u201c\u5355\u7eaf\u610f\u5916\u201d\u7684\u89e3\u91ca\u5df2\u7ecf\u96be\u4ee5\u8986\u76d6\u73b0\u6709\u7ebf\u7d22\uff0c{suspect} \u76ee\u524d\u6700\u503c\u5f97\u4f18\u5148\u6838\u67e5\uff0c\u4f46\u4ecd\u4e0d\u80fd\u76f4\u63a5\u5b9a\u7f6a\u3002",
        "verdict_mid": "\u73b0\u6709\u6750\u6599\u5df2\u8ba9\u201c\u5355\u7ebf\u4e8b\u6545\u8bf4\u201d\u51fa\u73b0\u88c2\u7f1d\uff0c{suspect} \u9700\u8981\u4f5c\u4e3a\u91cd\u70b9\u5bf9\u8c61\u63a5\u53d7\u8fdb\u4e00\u6b65\u9a8c\u8bc1\u3002",
        "verdict_light": "\u73b0\u6709\u6750\u6599\u4ecd\u4e0d\u8db3\u4ee5\u4e0b\u5b9a\u8bba\uff0c\u4f46\u5df2\u7ecf\u51fa\u73b0\u503c\u5f97\u7ee7\u7eed\u6df1\u6316\u7684\u5f02\u5e38\u94fe\u6761\u3002",
        "explain_a": "\u56f4\u7ed5\u201c{outcome}\u201d\uff0c\u66f4\u5408\u7406\u7684\u89e3\u91ca\u4e0d\u662f\u5b64\u7acb\u4e8b\u6545\uff0c\u800c\u662f\u591a\u6761\u5f02\u5e38\u7ebf\u7d22\u9010\u6b65\u6536\u675f\u5230\u540c\u4e00\u4f5c\u6848\u673a\u5236\u3002",
        "explain_b": "\u5f53\u524d\u6700\u503c\u5f97\u4f18\u5148\u9a8c\u8bc1\u7684\u7ebf\u7d22\u5305\u62ec\uff1a{clues}\u3002",
        "explain_c": "\u4ece\u52a8\u673a\u3001\u624b\u6bb5\u3001\u673a\u4f1a\u4e0e\u7ebf\u7d22\u8986\u76d6\u5ea6\u770b\uff0c{suspects} \u66f4\u63a5\u8fd1\u8fd9\u6761\u673a\u5236\u94fe\u3002",
        "agent_evidence": "\u7b5b\u51fa\u786c\u8bc1\u636e\u548c\u6700\u5371\u9669\u7684\u77db\u76fe\u70b9\u3002",
        "agent_relationship": "\u91cd\u5efa\u4eba\u7269\u5173\u7cfb\u3001\u5229\u76ca\u7ed3\u6784\u4e0e\u9690\u6027\u7275\u8fde\u3002",
        "agent_suspicion": "\u57fa\u4e8e\u52a8\u673a\u3001\u624b\u6bb5\u3001\u673a\u4f1a\u7ed9\u51fa\u5acc\u7591\u4eba\u6392\u5e8f\u3002",
        "agent_reconstruction": "\u53cd\u5411\u62fc\u63a5\u6700\u53ef\u80fd\u7684\u4f5c\u6848\u94fe\u548c\u65f6\u95f4\u7ebf\u3002",
        "agent_judge": "\u6574\u5408\u591a\u6761\u89e3\u91ca\u5e76\u4fdd\u7559\u5173\u952e\u4e0d\u786e\u5b9a\u6027\u3002",
        "core_actor": "\u6838\u5fc3\u76f8\u5173\u65b9",
        "critical_anomaly": "\u5173\u952e\u5f02\u5e38",
        "dialogue_1": "\u6700\u9ad8\u98ce\u9669\u7ebf\u7d22\u662f\u201c{label}\u201d\uff0c\u9700\u8981\u56f4\u7ed5\u5b83\u89e3\u91ca\u6574\u6761\u8bc1\u636e\u94fe\u3002",
        "dialogue_2": "\u76ee\u524d\u6700\u503c\u5f97\u76ef\u4f4f\u7684\u662f {suspect}\uff0c\u56e0\u4e3a\u4ed6\u66f4\u8d34\u8fd1\u5173\u952e\u5173\u7cfb\u548c\u5229\u76ca\u94fe\u3002",
        "dialogue_3": "\u8bf7\u4f18\u5148\u9a8c\u8bc1 {suspect} \u7684\u52a8\u673a\u3001\u624b\u6bb5\u548c\u673a\u4f1a\u662f\u5426\u80fd\u540c\u65f6\u8986\u76d6\u591a\u6761\u7ebf\u7d22\u3002",
        "dialogue_4": "\u65f6\u95f4\u7ebf\u8d77\u70b9\u662f\u201c{event}\u201d\uff0c\u5b83\u50cf\u662f\u540e\u7eed\u5173\u952e\u4e8b\u4ef6\u7684\u94fa\u57ab\u3002",
        "dialogue_5": "\u6211\u4f1a\u5728\u7efc\u5408\u5224\u65ad\u4e2d\u4fdd\u7559\u4e3b\u5047\u8bbe\u4e0e\u4e0d\u786e\u5b9a\u6027\u3002",
        "role_generic": "\u5173\u952e\u76f8\u5173\u65b9",
        "relation_generic": "{name} \u4f4d\u4e8e\u6848\u4ef6\u5173\u952e\u5173\u7cfb\u94fe\u4e2d\uff0c\u89d2\u8272\u5224\u65ad\u4e3a {role}\u3002",
        "motive_generic": "{name} \u53ef\u80fd\u53d7\u5230\u5229\u76ca\u3001\u81ea\u4fdd\u3001\u63a7\u5236\u53d9\u4e8b\u6216\u5173\u7cfb\u51b2\u7a81\u7684\u9a71\u52a8\u3002",
        "means_generic": "{role} \u53ef\u80fd\u5177\u5907\u63a5\u8fd1\u73b0\u573a\u3001\u88c5\u7f6e\u3001\u4fe1\u606f\u6216\u5173\u952e\u901a\u9053\u7684\u80fd\u529b\u3002",
        "opportunity_generic": "\u6750\u6599\u4e2d\u81f3\u5c11\u6709 {count} \u5904\u8282\u70b9\u4e0e\u5176\u76f4\u63a5\u76f8\u5173\uff0c\u8bf4\u660e\u5176\u63a5\u8fd1\u5173\u952e\u65f6\u70b9\u3002",
        "agent_context": "\u5f53\u524d\u4ee3\u7406\u6b63\u5728 Salmon \u7684\u56de\u6eaf\u91cd\u5efa\u6d41\u7a0b\u4e2d\u5de5\u4f5c\u3002",
        "actor_note": "\u4e0e {name} \u76f8\u5173\u7684\u7247\u6bb5\u5171 {count} \u5904\u3002",
        "event_note": "\u8be5\u8282\u70b9\u6765\u81ea\u65f6\u95f4\u7ebf\u7247\u6bb5 {ref_id}\u3002",
        "clue_note": "\u8be5\u8282\u70b9\u5bf9\u5e94\u89c2\u5bdf\u70b9 {ref_id}\u3002",
        "edge_note": "\u8be5\u5173\u7cfb\u7531\u6750\u6599\u7247\u6bb5 {refs} \u652f\u6491\u3002",
    },
    "en": {
        "default_outcome": "Please reconstruct how this case was formed.",
        "unknown_time": "Unknown time",
        "summary": "The material comes from {source}, and the task is to reconstruct how '{outcome}' took shape.",
        "few_clues": "The explicit anomalies are still sparse; more raw records, layouts, or statements would help.",
        "no_hard_evidence": "Direct physical evidence is still missing.",
        "uncertainty_1": "The leading hypothesis explains most clues, but direct physical evidence still does not conclusively bind the act, mechanism, and suspect.",
        "uncertainty_2": "The ranking would become much more stable with raw surveillance, access logs, medical findings, or fuller witness statements.",
        "verdict_strong": "A pure-accident explanation no longer fits the clues well; {suspect} deserves the highest priority review, but this is not proof.",
        "verdict_mid": "The single-accident narrative is weakening, and {suspect} should be tested first.",
        "verdict_light": "The material is still incomplete, but it already reveals an anomaly chain worth deeper investigation.",
        "explain_a": "For '{outcome}', the stronger explanation is not an isolated accident but a shared mechanism that absorbs multiple anomalies.",
        "explain_b": "The highest-priority clues are: {clues}.",
        "explain_c": "Across motive, means, opportunity, and clue coverage, {suspects} sit closest to that mechanism.",
        "agent_evidence": "Filter the strongest evidence and contradictions.",
        "agent_relationship": "Map relationships, incentives, and hidden ties.",
        "agent_suspicion": "Rank suspects by motive, means, and opportunity.",
        "agent_reconstruction": "Reconstruct the most likely causal chain and timeline.",
        "agent_judge": "Synthesize the explanations while keeping uncertainty visible.",
        "core_actor": "Core stakeholder",
        "critical_anomaly": "Critical anomaly",
        "dialogue_1": "The highest-risk clue is '{label}', so the mechanism needs to explain it first.",
        "dialogue_2": "{suspect} sits closest to the strongest relationship and incentive chain.",
        "dialogue_3": "Please test whether {suspect} covers motive, means, opportunity, and clue overlap.",
        "dialogue_4": "The timeline begins with '{event}', which likely primes the later event.",
        "dialogue_5": "I will keep both the leading hypothesis and the uncertainty visible in the synthesis.",
        "role_generic": "Key stakeholder",
        "relation_generic": "{name} appears inside the central relationship chain as {role}.",
        "motive_generic": "{name} may be driven by gain, self-protection, narrative control, or relationship conflict.",
        "means_generic": "The {role} role may provide access to the scene, devices, information, or key pathways.",
        "opportunity_generic": "The material links this actor to at least {count} relevant points near critical moments.",
        "agent_context": "This agent is working inside Salmon's reconstruction flow.",
        "actor_note": "There are {count} fragments directly tied to {name}.",
        "event_note": "This node comes from timeline fragment {ref_id}.",
        "clue_note": "This node corresponds to observation point {ref_id}.",
        "edge_note": "This relation is supported by material fragments {refs}.",
    },
}

AGENTS = [
    {
        "agent_name": "Evidence Agent",
        "purpose_key": "agent_evidence",
        "codename": "Trace Lens",
        "role": {"zh-CN": "证据审计", "en": "Evidence Audit"},
        "disposition": {"zh-CN": "冷静、保守", "en": "Calm, conservative"},
        "accent": "#b44d28",
    },
    {
        "agent_name": "Relationship Agent",
        "purpose_key": "agent_relationship",
        "codename": "Link Weaver",
        "role": {"zh-CN": "关系建模", "en": "Relationship Modeling"},
        "disposition": {"zh-CN": "结构化、关系优先", "en": "Structured, link-first"},
        "accent": "#254d59",
    },
    {
        "agent_name": "Suspicion Agent",
        "purpose_key": "agent_suspicion",
        "codename": "Rank Signal",
        "role": {"zh-CN": "关键对象排序", "en": "Suspicion Ranking"},
        "disposition": {"zh-CN": "比较驱动、筛选优先", "en": "Comparative, ranking-first"},
        "accent": "#8b5e34",
    },
    {
        "agent_name": "Reconstruction Agent",
        "purpose_key": "agent_reconstruction",
        "codename": "Time Thread",
        "role": {"zh-CN": "因果重建", "en": "Causal Reconstruction"},
        "disposition": {"zh-CN": "时序驱动、链路敏感", "en": "Timeline-driven, chain-sensitive"},
        "accent": "#3e6b6f",
    },
    {
        "agent_name": "Judge Agent",
        "purpose_key": "agent_judge",
        "codename": "Final Frame",
        "role": {"zh-CN": "综合裁决", "en": "Final Synthesis"},
        "disposition": {"zh-CN": "平衡、审慎", "en": "Balanced, cautious"},
        "accent": "#c59c3d",
    },
]

ROLE_KEYWORDS = ["\u533b\u751f", "\u6559\u6388", "\u8b66\u5bdf", "\u7ee7\u7236", "\u6bcd\u4eb2", "\u59b9\u59b9", "\u59d0\u59d0", "\u4fdd\u5b89", "\u7ecf\u7406", "\u4e3b\u4efb", "\u7ef4\u4fee", "\u62a4\u58eb", "\u53f8\u673a", "\u8d22\u52a1"]
AGENT_COLLAB_ROUNDS = 2
MIN_AGENT_COLLAB_ROUNDS = 1
MAX_AGENT_COLLAB_ROUNDS = 6
AGENT_CORE_SEQUENCE = ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent"]
AGENT_FINAL_SEQUENCE = [*AGENT_CORE_SEQUENCE, "Judge Agent"]
AGENT_ROUND_PLANS = [
    list(AGENT_CORE_SEQUENCE),
    list(AGENT_FINAL_SEQUENCE),
]

RISK_WORDS = {
    "missing": 3,
    "cover-up": 4,
    "tamper": 4,
    "timeline gap": 3,
    "device": 2,
    "access": 2,
    "insurance": 2,
    "统一口径": 4,
    "封存": 3,
    "异常": 2,
    "缺失": 3,
    "篡改": 4,
    "监控盲区": 4,
    "时间差": 3,
    "通道": 2,
    "装置": 2,
    "保险": 2,
    "提前": 2,
}

STRUCTURE_HEADINGS = {
    "background",
    "background facts",
    "analysis target",
    "goal",
    "target",
    "task",
    "clue",
    "clues",
    "evidence",
    "material input",
    "materials",
    "result",
    "results",
    "answer",
    "analysis",
    "summary",
    "timeline",
    "回溯",
    "重演",
    "分析",
    "分析目标",
    "目标",
    "问题",
    "材料输入",
    "输入材料",
    "背景",
    "背景资料",
    "线索",
    "关键线索",
    "证据",
    "结果",
    "答案",
    "参考分析",
    "时间线",
}
NOISE_ENTITY_TERMS = {
    *STRUCTURE_HEADINGS,
    "main hypothesis",
    "alternative hypothesis",
    "main explanation",
    "核心相关方",
    "关键相关方",
    "关键对象",
    "关键异常",
    "重要线索",
    "分析解释",
    "目标回答",
    "证据与不确定性",
    "时间",
    "结果",
    "事实",
    "安排",
    "问题",
    "工作",
    "冲突",
    "事件",
    "舆情",
    "解释",
    "原因",
}
QUESTION_TOKENS_ZH = ("为什么", "为何", "谁", "如何", "怎么", "是否", "能否", "哪", "什么", "意味着")
QUESTION_TOKENS_EN = ("why", "who", "how", "whether", "what", "which")
SECTION_ALIASES = {
    "background": "background",
    "背景": "background",
    "背景资料": "background",
    "backgroundfacts": "background",
    "analysisgoal": "goal",
    "goal": "goal",
    "target": "goal",
    "task": "goal",
    "目标": "goal",
    "分析目标": "goal",
    "问题": "goal",
    "材料输入": "extra",
    "输入材料": "extra",
    "clue": "clues",
    "clues": "clues",
    "evidence": "clues",
    "线索": "clues",
    "关键线索": "clues",
    "证据": "clues",
    "result": "result",
    "results": "result",
    "answer": "result",
    "summary": "result",
    "analysis": "result",
    "结果": "result",
    "答案": "result",
    "分析": "result",
    "参考分析": "result",
    "timeline": "extra",
    "时间线": "extra",
}


def _normalize_collaboration_rounds(value: Optional[int]) -> int:
    try:
        rounds = int(value) if value is not None else AGENT_COLLAB_ROUNDS
    except (TypeError, ValueError):
        rounds = AGENT_COLLAB_ROUNDS
    return max(MIN_AGENT_COLLAB_ROUNDS, min(MAX_AGENT_COLLAB_ROUNDS, rounds))


def _build_agent_round_plans(rounds: Optional[int]) -> List[List[str]]:
    normalized_rounds = _normalize_collaboration_rounds(rounds)
    plans: List[List[str]] = []
    for round_index in range(normalized_rounds):
        plans.append(list(AGENT_FINAL_SEQUENCE if round_index == normalized_rounds - 1 else AGENT_CORE_SEQUENCE))
    return plans


def run_case_workflow(
    text: str,
    document: UploadedDocument,
    expected_outcome: Optional[str],
    collaboration_rounds: Optional[int] = None,
) -> CaseWorkflowResponse:
    parse_stage = parse_case_material(text, document, expected_outcome, collaboration_rounds=collaboration_rounds)
    reason_stage = reason_case_material(
        text=text,
        document=document,
        expected_outcome=expected_outcome,
        structured_case=parse_stage.structured_case,
        detected_language=parse_stage.detected_language,
        collaboration_rounds=parse_stage.collaboration_rounds,
    )
    return CaseWorkflowResponse(
        document=document,
        expected_outcome=reason_stage.expected_outcome,
        collaboration_rounds=reason_stage.collaboration_rounds,
        detected_language=reason_stage.detected_language,
        model_status=reason_stage.model_status,
        graph_nodes=parse_stage.graph_nodes,
        graph_edges=parse_stage.graph_edges,
        evidence_items=parse_stage.evidence_items,
        pipeline=reason_stage.pipeline,
        agent_profiles=reason_stage.agent_profiles,
        agents=reason_stage.agents,
        agent_dialogue=reason_stage.agent_dialogue,
        final_result=reason_stage.final_result,
    )


def parse_case_material(
    text: str,
    document: UploadedDocument,
    expected_outcome: Optional[str],
    collaboration_rounds: Optional[int] = None,
) -> CaseParseResponse:
    language = detect_language(text, expected_outcome)
    outcome = _outcome(expected_outcome, language)
    normalized_rounds = _normalize_collaboration_rounds(collaboration_rounds)
    structured = _build_structured_case(text, document, outcome, language, collaboration_rounds=normalized_rounds)
    structured["expected_outcome"] = outcome
    structured["collaboration_rounds"] = normalized_rounds
    graph_nodes, graph_edges = _build_graph(structured, document.source_name, language)
    structured["graph_context"] = {
        "nodes": [node.model_dump() for node in graph_nodes],
        "edges": [edge.model_dump() for edge in graph_edges],
    }
    return CaseParseResponse(
        document=document,
        expected_outcome=outcome,
        collaboration_rounds=normalized_rounds,
        detected_language=language,
        extracted_text=text,
        structured_case=structured,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        evidence_items=_build_evidence_items(structured, document.source_name),
        agent_profiles=_build_agent_profiles(structured, language),
        pipeline=_pipeline("pending", "pending"),
    )


def reason_case_material(
    text: str,
    document: UploadedDocument,
    expected_outcome: Optional[str],
    structured_case: Optional[Dict] = None,
    detected_language: Optional[str] = None,
    collaboration_rounds: Optional[int] = None,
) -> CaseReasonResponse:
    language = detected_language or detect_language(text, expected_outcome)
    outcome = _outcome(expected_outcome, language)
    normalized_rounds = _normalize_collaboration_rounds(collaboration_rounds or (structured_case or {}).get("collaboration_rounds"))
    structured = structured_case or _build_structured_case(text, document, outcome, language, collaboration_rounds=normalized_rounds)
    structured["expected_outcome"] = outcome
    structured["collaboration_rounds"] = normalized_rounds
    agent_steps: List[AgentStep] = []
    agent_dialogue: List[AgentExchange] = []
    statuses: List[str] = []
    round_plans = structured.get("agent_round_plans") or _build_agent_round_plans(normalized_rounds)
    for round_index, round_agents in enumerate(round_plans, start=1):
        for agent_name in round_agents:
            turn = run_agent_turn(
                structured_case=structured,
                expected_outcome=outcome,
                detected_language=language,
                document=document,
                agent_name=agent_name,
                prior_steps=agent_steps,
                prior_dialogue=agent_dialogue,
                round_index=round_index,
            )
            agent_steps.append(turn.agent_step)
            agent_dialogue.extend(turn.dialogue)
            statuses.append(turn.model_status)

    synthesis = synthesize_case(structured, outcome, language, document, agent_steps)
    model_status = "model_plus_rules" if any(status == "model_plus_rules" for status in [*statuses, synthesis.model_status]) else "rules_only"

    return CaseReasonResponse(
        expected_outcome=outcome,
        collaboration_rounds=normalized_rounds,
        detected_language=language,
        model_status=model_status,
        pipeline=_pipeline("completed", "completed"),
        agent_profiles=_build_agent_profiles(structured, language),
        agents=agent_steps,
        agent_dialogue=agent_dialogue,
        final_result=synthesis.final_result,
    )


def detect_language(text: str, outcome: Optional[str] = None) -> str:
    sample = f"{outcome or ''}\n{text[:2000]}"
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", sample))
    latin_words = len(re.findall(r"[A-Za-z]{2,}", sample))
    return "zh-CN" if chinese_chars >= max(12, latin_words) else "en"


def _outcome(expected_outcome: Optional[str], language: str) -> str:
    return (expected_outcome or L10N[language]["default_outcome"]).strip()


def _pipeline(reason_status: str, result_status: str) -> List[PipelineStep]:
    return [
        PipelineStep(step_id="parse", title="parse", detail="document parsed", status="completed"),
        PipelineStep(step_id="graph", title="graph", detail="graph ready", status="completed"),
        PipelineStep(step_id="reason", title="reason", detail="agents reasoning", status=reason_status),
        PipelineStep(step_id="result", title="result", detail="final synthesis", status=result_status),
    ]


def _build_structured_case(
    text: str,
    document: UploadedDocument,
    outcome: str,
    language: str,
    collaboration_rounds: Optional[int] = None,
) -> Dict:
    normalized_rounds = _normalize_collaboration_rounds(collaboration_rounds)
    round_plans = _build_agent_round_plans(normalized_rounds)
    llm_client = OpenAICompatibleClient()
    if llm_client.enabled:
        structured = _extract_with_llm(llm_client, text, outcome, document, language)
        if structured:
            structured = _sanitize_structured_case(structured, text, document, outcome, language)
            if _needs_rule_backfill(structured, text, outcome):
                rules = _sanitize_structured_case(_extract_with_rules(text, document, outcome, language), text, document, outcome, language)
                structured = _merge_structured_cases(structured, rules, text, outcome)
            structured["parse_model_status"] = "model_plus_rules"
            structured["collaboration_rounds"] = normalized_rounds
            structured["agent_round_plans"] = round_plans
            return structured
    structured = _extract_with_rules(text, document, outcome, language)
    structured = _sanitize_structured_case(structured, text, document, outcome, language)
    structured["parse_model_status"] = "rules_only"
    structured["collaboration_rounds"] = normalized_rounds
    structured["agent_round_plans"] = round_plans
    return structured


def run_agent_turn(
    structured_case: Dict,
    expected_outcome: str,
    detected_language: str,
    document: UploadedDocument,
    agent_name: str,
    prior_steps: List[AgentStep],
    prior_dialogue: Optional[List[AgentExchange]] = None,
    round_index: int = 1,
) -> AgentTurnResponse:
    spec = _agent_spec(agent_name)
    llm_client = OpenAICompatibleClient()
    prior_dialogue = prior_dialogue or []
    profile = _build_agent_profile_from_spec(spec, structured_case, detected_language)
    step = None
    model_status = "rules_only"

    if llm_client.enabled:
        step = _run_agent_turn_with_llm(
            llm_client,
            structured_case,
            expected_outcome,
            detected_language,
            document,
            spec,
            prior_steps,
            prior_dialogue,
            round_index,
        )
        if step:
            model_status = "model_plus_rules"

    if not step:
        step = _run_agent_turn_with_rules(structured_case, detected_language, spec, prior_steps, round_index)

    profile.current_focus = step.findings[0] if step.findings else profile.current_focus
    profile.persistent_state = f"{profile.persistent_state} / round {round_index}"
    profile.memory_notes = [*step.findings[:2], *profile.memory_notes][:5]

    return AgentTurnResponse(
        expected_outcome=expected_outcome,
        detected_language=detected_language,
        model_status=model_status,
        round_index=round_index,
        pipeline=_pipeline("in_progress", "pending"),
        agent_profile=profile,
        agent_step=step,
        dialogue=[_build_exchange(agent_name, _next_agent_name(agent_name), step, structured_case, detected_language, round_index)],
    )


def synthesize_case(
    structured_case: Dict,
    expected_outcome: str,
    detected_language: str,
    document: UploadedDocument,
    agent_steps: List[AgentStep],
) -> CaseSynthesisResponse:
    llm_client = OpenAICompatibleClient()
    final_result = None
    model_status = "rules_only"
    if llm_client.enabled:
        final_result = _run_final_synthesis_with_llm(llm_client, structured_case, expected_outcome, detected_language, document, agent_steps)
        if final_result:
            model_status = "model_plus_rules"
    if not final_result:
        final_result = _build_final_result(structured_case, agent_steps)
    return CaseSynthesisResponse(
        expected_outcome=expected_outcome,
        detected_language=detected_language,
        model_status=model_status,
        pipeline=_pipeline("completed", "completed"),
        final_result=final_result,
    )


def _extract_with_llm(
    llm_client: OpenAICompatibleClient,
    text: str,
    outcome: str,
    document: UploadedDocument,
    language: str,
) -> Optional[Dict]:
    system_prompt, user_prompt = _build_case_llm_prompts(text, outcome, document, language)
    payload = llm_client.complete_json(system_prompt, user_prompt)
    if not payload:
        return None
    required = [
        "background_summary",
        "actors",
        "events",
        "clues",
        "suspect_rankings",
        "reenactment_timeline",
        "evidence_notes",
        "verdict_summary",
        "final_explanation",
        "uncertainties",
        "goal_response",
    ]
    if any(key not in payload for key in required):
        return None
    return _normalize_llm_payload(payload)


def _build_case_llm_prompts(text: str, outcome: str, document: UploadedDocument, language: str) -> Tuple[str, str]:
    sections = _split_case_sections(text)
    segments = _material_segments(text)[:36]
    context_windows = _mirofish_style_chunks(text, chunk_size=1800, overlap=180)[:10]
    target_language = "Simplified Chinese" if language == "zh-CN" else "English"
    background_block = "\n".join(f"- {item}" for item in sections["background"]) or "- None explicitly provided."
    clue_block = "\n".join(f"- {item}" for item in sections["clues"]) or "- None explicitly provided."
    goal_block = "\n".join(f"- {item}" for item in sections["goal"]) or "- No explicit goal block."
    extra_block = "\n".join(f"- {item}" for item in sections["extra"]) or "- No extra sections."
    mode = _classify_prompt_mode(text, outcome)
    extra_constraints = _mode_specific_constraints(mode)
    ranking_label = _mode_ranking_label(mode)

    system_prompt = f"""
You are Salmon's reconstruction structuring agent.
Return one valid JSON object and nothing else.
All natural-language values in the JSON must be written in {target_language}.
Keep the JSON keys in English.
Treat background as context, clues as the main evidence layer, and never convert inference into fact.
Build a reusable structured graph that can support downstream multi-agent reasoning.
The current analysis mode is: {mode}.
When ranking candidates, use motive, means, opportunity, clue coverage, or the closest equivalent for this mode.
For compatibility, always write the ranked objects into suspect_rankings, even when they represent key actors, conflict drivers, or responsibility centers rather than literal suspects.
Preserve entity names faithfully. Do not invent tokenized fragments, half-names, or meaningless broken terms.
When the source text is noisy, first normalize it into coherent actors, events, clues, and evidence references before building the graph.
Never treat section titles such as 背景, 线索, 结果, 回溯, 分析, analysis, or summary as actors, clues, or graph nodes.
goal_response must answer the user's analysis goal directly, explicitly, and compactly. If the goal asks why / who / how / whether, answer those points in plain language before giving structure.

Output schema:
background_summary: string
actors: [{{name, role, relation, suspicion_score, motive, means, opportunity, evidence_refs}}]
events: [{{id, time_hint, description, actors, evidence_refs, inference_level}}]
clues: [{{id, label, detail, actors, event_ids, risk_level, evidence_refs}}]
suspect_rankings: [{{name, role, suspicion_score, motive, means, opportunity, supporting_evidence, concerns}}]  # {ranking_label}
reenactment_timeline: [{{order, phase, time_hint, event, evidence_refs, inference_level}}]
evidence_notes: [string]
verdict_summary: string
final_explanation: string
uncertainties: [string]
goal_response: string
""".strip()

    user_prompt = f"""
Analysis goal:
{outcome}

Document info:
- source_name: {document.source_name}
- source_type: {document.source_type}
- character_count: {document.character_count}

Background facts:
{background_block}

Explicit clues:
{clue_block}

Explicit goal notes:
{goal_block}

Other sections:
{extra_block}

Context windows:
{chr(10).join(f"Window {index + 1}: {chunk}" for index, chunk in enumerate(context_windows)) or "- None."}

Normalized segments:
{chr(10).join(f"- {segment}" for segment in segments) or "- None."}

Extra constraints:
{extra_constraints}
""".strip()
    return system_prompt, user_prompt
def _split_case_sections(text: str) -> Dict[str, List[str]]:
    sections = {"background": [], "clues": [], "goal": [], "extra": []}
    current = "extra"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _match_section_heading(line)
        if heading:
            current = heading
            continue
        cleaned = _clean_segment(line)
        if not cleaned:
            continue
        if _is_structural_heading(cleaned):
            continue
        sections[current].append(cleaned)
    return sections


def _classify_prompt_mode(text: str, outcome: str) -> str:
    sample = f"{outcome}\n{text[:5000]}".lower()
    keyword_groups = {
        "case_reenactment": [
            "\u6848\u60c5",
            "\u6848\u4ef6",
            "\u5acc\u7591",
            "\u5acc\u7591\u4eba",
            "\u51f6\u624b",
            "\u4f5c\u6848",
            "\u6848\u53d1",
            "\u8bc1\u636e",
            "\u4fa6\u67e5",
            "crime",
            "suspect",
            "forensic",
            "murder",
            "reenact",
            "evidence",
        ],
        "relationship_emotion": [
            "\u60c5\u4fa3",
            "\u611f\u60c5",
            "\u60c5\u7eea",
            "\u4e89\u5435",
            "\u5173\u7cfb",
            "\u6c9f\u901a",
            "\u804a\u5929\u8bb0\u5f55",
            "\u8bef\u89e3",
            "\u51b7\u6218",
            "emotion",
            "relationship",
            "conflict",
            "chat",
            "argument",
            "repair attempt",
        ],
        "public_opinion_attribution": [
            "\u8206\u60c5",
            "\u8206\u8bba",
            "\u516c\u5173",
            "\u4f20\u64ad",
            "\u54c1\u724c",
            "\u5371\u673a",
            "\u54c1\u724c\u5371\u673a",
            "\u5a92\u4f53",
            "\u70ed\u641c",
            "\u58f0\u91cf",
            "\u5e73\u53f0",
            "\u56de\u5e94",
            "\u822a\u7a7a",
            "\u89c6\u9891",
            "\u58f0\u660e",
            "public opinion",
            "reputation",
            "brand crisis",
            "social media",
            "narrative",
            "statement",
            "video",
            "airline",
        ],
    }
    scores = {mode: sum(1 for keyword in keywords if keyword in sample) for mode, keywords in keyword_groups.items()}
    best_mode = max(scores, key=scores.get)
    return best_mode if scores[best_mode] >= 2 else "general_backtrace"


def _mode_specific_constraints(mode: str) -> str:
    constraints = {
        "case_reenactment": """
- This request is a case reenactment task. Preserve suspect ranking, timeline reconstruction, and evidence coverage.
- Prefer one mechanism that explains multiple clues at once.
- If the material includes space, access, device, time-gap, or other structural anomalies, test whether they combine into one mechanism chain.
- Suspect ranking must clearly state which material supports motive, means, opportunity, and clue coverage.
""".strip(),
        "relationship_emotion": """
- This request is a relationship or emotional backtrace task.
- Track each side's emotion shifts, unmet needs, defensive moves, repair attempts, and escalation points.
- Use suspect_rankings to represent the key actors or conflict drivers rather than literal suspects.
- Reconstruct the timeline around trigger moments, misunderstanding loops, and failed repair windows.
""".strip(),
        "public_opinion_attribution": """
- This request is a public-opinion or narrative-attribution task.
- Focus on the chain from operational trigger to public narrative escalation, response failure, and perception shift.
- Use suspect_rankings to represent key actors, responsibility centers, or escalation drivers.
- Reconstruct the timeline around trigger event, amplification, official response, counter-reaction, and stabilization attempt.
""".strip(),
        "general_backtrace": """
- This request is a general backtracing task rather than a single predefined scenario.
- Focus on causal structure, competing explanations, hidden turning points, and evidentiary limits.
- Reuse the same schema without forcing crime-specific assumptions.
""".strip(),
    }
    return constraints.get(mode, constraints["general_backtrace"])


def _mode_ranking_label(mode: str) -> str:
    labels = {
        "case_reenactment": "关键对象及其驱动链",
        "relationship_emotion": "关键关系双方及驱动链",
        "public_opinion_attribution": "关键责任中心及驱动链",
        "general_backtrace": "关键对象及其驱动链",
    }
    return labels.get(mode, labels["general_backtrace"])


def _mode_agent_focus(mode: str, agent_name: str) -> str:
    focus_map = {
        "case_reenactment": {
            "Evidence Agent": "prioritize hard evidence, contradictions, and mechanism-sensitive clues.",
            "Relationship Agent": "map who is linked to whom, through what incentives or hidden ties.",
            "Suspicion Agent": "rank persons of interest by motive, means, opportunity, and clue coverage.",
            "Reconstruction Agent": "rebuild the most plausible mechanism chain and event order.",
            "Judge Agent": "compare main and alternative explanations while preserving uncertainty.",
        },
        "relationship_emotion": {
            "Evidence Agent": "identify emotionally loaded utterances, unmet needs, and explicit trigger sentences.",
            "Relationship Agent": "map attachment needs, misread intentions, power balance, and repeated patterns.",
            "Suspicion Agent": "rank the main conflict drivers, misunderstandings, or escalation sources.",
            "Reconstruction Agent": "rebuild the escalation path from expectation, to hurt, to defense, to withdrawal or repair.",
            "Judge Agent": "balance both sides' intentions, injuries, and plausible misreadings.",
        },
        "public_opinion_attribution": {
            "Evidence Agent": "identify high-leverage facts, public-facing evidence, and narrative turning points.",
            "Relationship Agent": "map the relationship between organization, audience, media, platform, and spokesperson.",
            "Suspicion Agent": "rank the main responsibility centers or escalation drivers.",
            "Reconstruction Agent": "rebuild the path from trigger event to amplification, backlash, response, and aftershock.",
            "Judge Agent": "compare responsibility narratives and keep visible what remains uncertain.",
        },
        "general_backtrace": {
            "Evidence Agent": "identify the strongest evidence and the most dangerous blind spots.",
            "Relationship Agent": "map the main stakeholders, dependencies, and hidden ties.",
            "Suspicion Agent": "rank the strongest drivers, actors, or explanations.",
            "Reconstruction Agent": "rebuild the causal chain and the most important turning points.",
            "Judge Agent": "synthesize the main and secondary explanations while preserving uncertainty.",
        },
    }
    return focus_map.get(mode, focus_map["general_backtrace"]).get(agent_name, "focus on the most evidence-supported interpretation.")


def _ensure_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _ensure_int(value, fallback=0):
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return {"low": 3, "medium": 6, "high": 9}.get(value.strip().lower(), fallback)
    return fallback


def _ensure_float(value, fallback=0.0):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return fallback
    return fallback


def _normalize_llm_payload(payload: Dict) -> Dict:
    normalized_actors = []
    for actor in payload.get("actors", []):
        if isinstance(actor, dict):
            normalized_actors.append(actor)
        elif str(actor).strip():
            normalized_actors.append({"name": str(actor).strip()})
    payload["actors"] = normalized_actors

    normalized_events = []
    for event in payload.get("events", []):
        if isinstance(event, dict):
            normalized_events.append(event)
        elif str(event).strip():
            normalized_events.append({"description": str(event).strip()})
    payload["events"] = normalized_events

    normalized_clues = []
    for clue in payload.get("clues", []):
        if isinstance(clue, dict):
            normalized_clues.append(clue)
        elif str(clue).strip():
            normalized_clues.append({"detail": str(clue).strip()})
    payload["clues"] = normalized_clues

    normalized_rankings = []
    for suspect in payload.get("suspect_rankings", []):
        if isinstance(suspect, dict):
            normalized_rankings.append(suspect)
        elif str(suspect).strip():
            normalized_rankings.append({"name": str(suspect).strip()})
    payload["suspect_rankings"] = normalized_rankings

    normalized_timeline = []
    for step in payload.get("reenactment_timeline", []):
        if isinstance(step, dict):
            normalized_timeline.append(step)
        elif str(step).strip():
            normalized_timeline.append({"event": str(step).strip()})
    payload["reenactment_timeline"] = normalized_timeline

    for actor in payload.get("actors", []):
        actor["evidence_refs"] = _ensure_list(actor.get("evidence_refs"))
        actor["suspicion_score"] = _ensure_float(actor.get("suspicion_score"), 0.0)
    for event in payload.get("events", []):
        event["actors"] = _ensure_list(event.get("actors"))
        event["evidence_refs"] = _ensure_list(event.get("evidence_refs"))
    for clue in payload.get("clues", []):
        clue["actors"] = _ensure_list(clue.get("actors"))
        clue["event_ids"] = _ensure_list(clue.get("event_ids"))
        clue["evidence_refs"] = _ensure_list(clue.get("evidence_refs"))
        clue["risk_level"] = _ensure_int(clue.get("risk_level"), 5)
    for suspect in payload.get("suspect_rankings", []):
        suspect["supporting_evidence"] = _ensure_list(suspect.get("supporting_evidence"))
        suspect["concerns"] = _ensure_list(suspect.get("concerns"))
        suspect["suspicion_score"] = _ensure_int(suspect.get("suspicion_score"), 50)
    for step in payload.get("reenactment_timeline", []):
        step["evidence_refs"] = _ensure_list(step.get("evidence_refs"))
        step["order"] = _ensure_int(step.get("order"), 0)
    payload["evidence_notes"] = _normalize_note_strings(payload.get("evidence_notes"))
    payload["uncertainties"] = _normalize_note_strings(payload.get("uncertainties"))
    payload["goal_response"] = str(payload.get("goal_response", "") or "")
    return payload


def _normalize_note_strings(value) -> List[str]:
    notes: List[str] = []
    for item in _ensure_list(value):
        if isinstance(item, str):
            cleaned = _clean_segment(item)
            if cleaned:
                notes.append(cleaned)
            continue
        if isinstance(item, dict):
            fragments: List[str] = []
            for key in ("summary", "detail", "note", "evidence", "supporting_evidence", "concerns", "findings"):
                raw = item.get(key)
                if isinstance(raw, list):
                    fragments.extend(_clean_segment(str(value)) for value in raw if _clean_segment(str(value)))
                elif raw:
                    fragments.append(_clean_segment(str(raw)))
            if fragments:
                notes.append("；".join(fragment for fragment in fragments if fragment))
            else:
                fallback = _clean_segment(str(item))
                if fallback:
                    notes.append(fallback)
            continue
        cleaned = _clean_segment(str(item))
        if cleaned:
            notes.append(cleaned)
    return notes[:12]


def _normalize_heading_token(value: str) -> str:
    normalized = re.sub(r"^\s*(?:[#>*-]+|\d+[.)、-]?|[一二三四五六七八九十]+[.)、-]?)\s*", "", value.strip(), flags=re.IGNORECASE)
    normalized = re.sub(r"[*_`]+", "", normalized)
    normalized = normalized.lower()
    normalized = re.sub(r"[\s:：#*_\-—–()（）\[\]【】/\\]+", "", normalized)
    return normalized


def _match_section_heading(line: str) -> Optional[str]:
    return SECTION_ALIASES.get(_normalize_heading_token(line))


def _looks_like_entity_noise(value: str) -> bool:
    if value.strip() in {"A", "B", "C", "D", "甲", "乙", "丙", "丁"}:
        return False
    normalized = _normalize_heading_token(value)
    if not normalized:
        return True
    if normalized in { _normalize_heading_token(item) for item in NOISE_ENTITY_TERMS }:
        return True
    if re.search(r"(?:^|[ #])(?:step|round)\b", value.lower()):
        return True
    return len(value.strip()) <= 1


def _is_structural_heading(line: str) -> bool:
    stripped = line.strip()
    normalized = _normalize_heading_token(stripped)
    if not normalized:
        return True
    if normalized in SECTION_ALIASES or normalized in {_normalize_heading_token(item) for item in STRUCTURE_HEADINGS}:
        return True
    return bool(
        len(stripped) <= 24
        and re.fullmatch(
            r"(?:第?[0-9一二三四五六七八九十]+[章节部分项篇、.)-]*)?(?:背景|背景资料|线索|关键线索|证据|结果|答案|分析|分析目标|参考分析|时间线|目标回答|分析解释|回溯|重演|summary|analysis|answer|result|timeline|background|clues?|evidence)",
            stripped,
            flags=re.IGNORECASE,
        )
    )


def _clean_segment(segment: str) -> str:
    cleaned = (segment or "").replace("\u3000", " ").strip()
    cleaned = re.sub(r"^\s*(?:[#>*-]+|\d+[.)、-]?|[一二三四五六七八九十]+[.)、-]?)\s*", "", cleaned)
    cleaned = re.sub(r"^(?:案例包|案例|场景|材料|任务|聊天记录|背景|线索|证据|结果|答案|提示)[：:]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -\t")
    return cleaned


def _split_long_segment(segment: str, max_length: int = 160) -> List[str]:
    if len(segment) <= max_length:
        return [segment]
    parts = re.split(r"(?<=[。！？；.!?;])\s+|(?<=\])\s+|(?<=\))\s+|(?<=[：:])\s+", segment)
    pieces: List[str] = []
    buffer = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        candidate = f"{buffer} {part}".strip() if buffer else part
        if len(candidate) <= max_length:
            buffer = candidate
            continue
        if buffer:
            pieces.append(buffer)
        buffer = part
    if buffer:
        pieces.append(buffer)
    return pieces or [segment]


def _segment_has_material_value(segment: str) -> bool:
    if len(segment) < 6:
        return False
    if _is_structural_heading(segment):
        return False
    if re.fullmatch(r"[\W_]+", segment):
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", segment))


def _mirofish_style_chunks(text: str, chunk_size: int = 1600, overlap: int = 160) -> List[str]:
    cleaned = DocumentParser.preprocess_text(text)
    if len(cleaned) <= chunk_size:
        return [cleaned] if cleaned else []

    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        if end < len(cleaned):
            window = cleaned[start:end]
            for separator in ("\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ", "; "):
                split_at = window.rfind(separator)
                if split_at > chunk_size * 0.45:
                    end = start + split_at + len(separator)
                    break
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _normalize_actor_names(values: List[str], context: str, source_text: str) -> List[str]:
    candidates: List[str] = []
    for raw in [*_ensure_list(values), *_extract_actors(context)]:
        name = _clean_segment(str(raw))
        if not name or _looks_like_entity_noise(name):
            continue
        if len(name) > 20:
            continue
        if name in context or source_text.count(name) >= 2 or any(keyword in name for keyword in ROLE_KEYWORDS):
            candidates.append(name)
    return list(dict.fromkeys(candidates))[:5]


def _sanitize_structured_case(structured: Dict, text: str, document: UploadedDocument, outcome: str, language: str) -> Dict:
    loc = L10N[language]
    source_text = text or ""
    source_name = document.source_name

    events: List[Dict] = []
    event_ids = set()
    seen_events = set()
    for index, raw_event in enumerate(structured.get("events", []), start=1):
        description = _clean_segment(str(raw_event.get("description", "")))
        if not _segment_has_material_value(description):
            continue
        dedupe_key = re.sub(r"\s+", " ", description).lower()
        if dedupe_key in seen_events:
            continue
        event_id = str(raw_event.get("id") or f"evt_{index:02d}").strip() or f"evt_{index:02d}"
        evidence_refs = [str(item).strip() for item in _ensure_list(raw_event.get("evidence_refs")) if str(item).strip()]
        if event_id not in evidence_refs:
            evidence_refs = [event_id, *evidence_refs][:4]
        events.append(
            {
                "id": event_id,
                "time_hint": str(raw_event.get("time_hint") or loc["unknown_time"]).strip() or loc["unknown_time"],
                "description": description,
                "actors": _normalize_actor_names(raw_event.get("actors", []), description, source_text),
                "evidence_refs": evidence_refs,
                "evidence_details": raw_event.get("evidence_details")
                or [
                    {
                        "ref_id": event_id,
                        "excerpt": description[:220],
                        "source": source_name,
                        "note": loc["event_note"].format(ref_id=event_id),
                    }
                ],
                "inference_level": str(raw_event.get("inference_level") or "mixed"),
            }
        )
        seen_events.add(dedupe_key)
        event_ids.add(event_id)

    clues: List[Dict] = []
    seen_clues = set()
    for index, raw_clue in enumerate(structured.get("clues", []), start=1):
        detail = _clean_segment(str(raw_clue.get("detail", "")))
        if not _segment_has_material_value(detail):
            continue
        dedupe_key = re.sub(r"\s+", " ", detail).lower()
        if dedupe_key in seen_clues:
            continue
        clue_id = str(raw_clue.get("id") or f"clue_{index:02d}").strip() or f"clue_{index:02d}"
        event_refs = [str(item).strip() for item in _ensure_list(raw_clue.get("event_ids")) if str(item).strip() in event_ids]
        evidence_refs = [str(item).strip() for item in _ensure_list(raw_clue.get("evidence_refs")) if str(item).strip()]
        if clue_id not in evidence_refs:
            evidence_refs = [clue_id, *evidence_refs][:4]
        if event_refs:
            for ref in event_refs[:2]:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
        label = _clean_segment(str(raw_clue.get("label", ""))) or _clue_label(detail, language)
        if _looks_like_entity_noise(label):
            label = _clue_label(detail, language)
        clues.append(
            {
                "id": clue_id,
                "label": label,
                "detail": detail,
                "actors": _normalize_actor_names(raw_clue.get("actors", []), detail, source_text),
                "event_ids": event_refs,
                "risk_level": max(2, _ensure_int(raw_clue.get("risk_level"), _risk_score(detail))),
                "evidence_refs": evidence_refs[:5],
                "evidence_details": raw_clue.get("evidence_details")
                or [
                    {
                        "ref_id": event_refs[0] if event_refs else clue_id,
                        "excerpt": detail[:220],
                        "source": source_name,
                        "note": loc["clue_note"].format(ref_id=clue_id),
                    }
                ],
            }
        )
        seen_clues.add(dedupe_key)

    if not clues and events:
        for fallback_index, event in enumerate(sorted(events, key=lambda item: _risk_score(item["description"]), reverse=True)[:4], start=1):
            clue_id = f"clue_{fallback_index:02d}"
            clues.append(
                {
                    "id": clue_id,
                    "label": _clue_label(event["description"], language),
                    "detail": event["description"],
                    "actors": event.get("actors", []),
                    "event_ids": [event["id"]],
                    "risk_level": max(3, _risk_score(event["description"])),
                    "evidence_refs": [clue_id, event["id"]],
                    "evidence_details": event.get("evidence_details", []),
                }
            )

    actor_counter: Counter = Counter()
    actor_evidence_map: Dict[str, List[str]] = defaultdict(list)
    for event in events:
        for actor in event.get("actors", []):
            actor_counter[actor] += 1
            actor_evidence_map[actor].append(event["id"])
    for clue in clues:
        for actor in clue.get("actors", []):
            actor_counter[actor] += 1
            actor_evidence_map[actor].extend(ref for ref in clue.get("event_ids", []) if ref)

    existing_actors: List[Dict] = []
    seen_actor_names = set()
    for raw_actor in structured.get("actors", []):
        name = _clean_segment(str(raw_actor.get("name", "")))
        if not name or _looks_like_entity_noise(name) or name in seen_actor_names:
            continue
        if name not in source_text and actor_counter.get(name, 0) == 0 and source_text.count(name) < 2:
            continue
        mentions = list(dict.fromkeys([str(ref).strip() for ref in _ensure_list(raw_actor.get("evidence_refs")) if str(ref).strip()] + actor_evidence_map.get(name, [])))[:4]
        suspicious_hits = sum(1 for clue in clues if name in clue.get("actors", []))
        role = _clean_segment(str(raw_actor.get("role", ""))) or _guess_role(name, language)
        existing_actors.append(
            {
                "name": name,
                "role": role,
                "relation": _clean_segment(str(raw_actor.get("relation", ""))) or loc["relation_generic"].format(name=name, role=role),
                "suspicion_score": min(96.0, max(20.0, _ensure_float(raw_actor.get("suspicion_score"), 35 + suspicious_hits * 15 + len(mentions) * 5))),
                "motive": _clean_segment(str(raw_actor.get("motive", ""))) or loc["motive_generic"].format(name=name),
                "means": _clean_segment(str(raw_actor.get("means", ""))) or loc["means_generic"].format(role=role),
                "opportunity": _clean_segment(str(raw_actor.get("opportunity", ""))) or loc["opportunity_generic"].format(count=max(1, len(mentions))),
                "evidence_refs": mentions,
                "evidence_details": raw_actor.get("evidence_details")
                or [
                    {
                        "ref_id": ref_id,
                        "excerpt": loc["actor_note"].format(name=name, count=max(1, len(mentions))),
                        "source": source_name,
                        "note": loc["event_note"].format(ref_id=ref_id),
                    }
                    for ref_id in mentions
                ],
            }
        )
        seen_actor_names.add(name)

    actors = sorted(existing_actors or _build_actor_cards(actor_counter, actor_evidence_map, clues, language, source_name), key=lambda item: float(item.get("suspicion_score", 0.0)), reverse=True)[:8]
    valid_actor_names = {item["name"] for item in actors}
    mode = _classify_prompt_mode(text, outcome)

    suspect_rankings: List[Dict] = []
    for raw_rank in structured.get("suspect_rankings", []):
        name = _clean_segment(str(raw_rank.get("name", "")))
        if name not in valid_actor_names:
            continue
        actor = next((item for item in actors if item["name"] == name), None)
        if not actor:
            continue
        suspect_rankings.append(
            {
                "name": name,
                "role": actor["role"],
                "suspicion_score": max(1, _ensure_int(raw_rank.get("suspicion_score"), int(actor["suspicion_score"]))),
                "motive": _clean_segment(str(raw_rank.get("motive", ""))) or actor["motive"],
                "means": _clean_segment(str(raw_rank.get("means", ""))) or actor["means"],
                "opportunity": _clean_segment(str(raw_rank.get("opportunity", ""))) or actor["opportunity"],
                "supporting_evidence": [
                    _clean_segment(str(item))
                    for item in _ensure_list(raw_rank.get("supporting_evidence"))
                    if _clean_segment(str(item))
                ][:4],
                "concerns": [_clean_segment(str(item)) for item in _ensure_list(raw_rank.get("concerns")) if _clean_segment(str(item))][:4] or [loc["no_hard_evidence"]],
            }
        )
    if not suspect_rankings:
        suspect_rankings = _build_suspect_rankings(actors, events, language, mode)

    timeline: List[Dict] = []
    for raw_step in structured.get("reenactment_timeline", []):
        event = _clean_segment(str(raw_step.get("event", "")))
        if not _segment_has_material_value(event):
            continue
        evidence_refs = [str(item).strip() for item in _ensure_list(raw_step.get("evidence_refs")) if str(item).strip()]
        timeline.append(
            {
                "order": max(1, _ensure_int(raw_step.get("order"), len(timeline) + 1)),
                "phase": _clean_segment(str(raw_step.get("phase", ""))) or "build",
                "time_hint": _clean_segment(str(raw_step.get("time_hint", ""))) or loc["unknown_time"],
                "event": event,
                "evidence_refs": evidence_refs[:4],
                "inference_level": _clean_segment(str(raw_step.get("inference_level", ""))) or "mixed",
            }
        )
    if not timeline:
        timeline = _build_reenactment_timeline(events)
    else:
        timeline = sorted(timeline, key=lambda item: item["order"])[:10]
        for index, step in enumerate(timeline, start=1):
            step["order"] = index

    sections = _split_case_sections(text)
    background_lines = [*sections.get("background", []), *sections.get("extra", [])[:2]]
    background_summary = _clean_segment(str(structured.get("background_summary", "")))
    if not background_summary or _is_structural_heading(background_summary):
        background_summary = " ".join(background_lines[:2])[:260] if background_lines else loc["summary"].format(source=source_name, outcome=outcome)

    final_explanation = _clean_segment(str(structured.get("final_explanation", ""))) or _build_explanation(outcome, clues, suspect_rankings, language)
    verdict_summary = _clean_segment(str(structured.get("verdict_summary", ""))) or _build_verdict(clues, suspect_rankings, language)
    evidence_notes = [_clean_segment(str(item)) for item in _ensure_list(structured.get("evidence_notes")) if _clean_segment(str(item))][:6] or _build_evidence_notes(clues, language)
    uncertainties = [_clean_segment(str(item)) for item in _ensure_list(structured.get("uncertainties")) if _clean_segment(str(item))][:5] or [loc["uncertainty_1"], loc["uncertainty_2"]]
    transient_cache = _build_transient_cache(clues, events, outcome)
    goal_response = _clean_segment(str(structured.get("goal_response", "")))
    if not goal_response or len(goal_response) < 18 or goal_response == verdict_summary:
        goal_response = _compose_goal_response(
            outcome,
            clues,
            suspect_rankings,
            timeline,
            verdict_summary,
            language,
            mode=mode,
            transient_cache=transient_cache,
        )
    goal_response = _expand_evidence_aliases(goal_response, transient_cache.get("evidence_aliases", {}))

    return {
        **structured,
        "background_summary": background_summary,
        "actors": actors,
        "events": events[:12],
        "clues": clues[:10],
        "suspect_rankings": suspect_rankings[:5],
        "reenactment_timeline": timeline[:10],
        "evidence_notes": evidence_notes,
        "verdict_summary": verdict_summary,
        "final_explanation": final_explanation,
        "uncertainties": uncertainties,
        "goal_response": goal_response,
        "transient_cache": transient_cache,
    }


def _needs_rule_backfill(structured: Dict, text: str, outcome: str) -> bool:
    mode = _classify_prompt_mode(text, outcome)
    actors = [item.get("name", "") for item in structured.get("actors", []) if item.get("name")]
    if len(structured.get("events", [])) < 3 or len(structured.get("clues", [])) < 2:
        return True
    if len(actors) < 2:
        return True
    if mode == "relationship_emotion":
        if re.search(r"(?<![A-Za-z])A(?![A-Za-z])", text) and re.search(r"(?<![A-Za-z])B(?![A-Za-z])", text):
            if "A" not in actors or "B" not in actors:
                return True
    return False


def _merge_structured_cases(primary: Dict, fallback: Dict, text: str, outcome: str) -> Dict:
    mode = _classify_prompt_mode(text, outcome)

    def choose(primary_key: str) -> List[Dict]:
        primary_list = primary.get(primary_key, []) or []
        fallback_list = fallback.get(primary_key, []) or []
        return primary_list if len(primary_list) >= len(fallback_list) else fallback_list

    merged = {
        **fallback,
        **primary,
        "actors": choose("actors"),
        "events": choose("events"),
        "clues": choose("clues"),
        "suspect_rankings": choose("suspect_rankings"),
        "reenactment_timeline": choose("reenactment_timeline"),
        "evidence_notes": primary.get("evidence_notes") or fallback.get("evidence_notes", []),
        "uncertainties": primary.get("uncertainties") or fallback.get("uncertainties", []),
        "background_summary": primary.get("background_summary") or fallback.get("background_summary", ""),
        "verdict_summary": primary.get("verdict_summary") or fallback.get("verdict_summary", ""),
        "final_explanation": primary.get("final_explanation") or fallback.get("final_explanation", ""),
        "goal_response": primary.get("goal_response") or fallback.get("goal_response", ""),
    }
    if mode == "relationship_emotion":
        actor_names = {item.get("name") for item in merged["actors"]}
        if {"A", "B"} - actor_names:
            merged["actors"] = fallback.get("actors", merged["actors"])
            merged["suspect_rankings"] = fallback.get("suspect_rankings", merged["suspect_rankings"])
            merged["goal_response"] = fallback.get("goal_response", merged["goal_response"])
    if mode == "public_opinion_attribution":
        top_name = (merged.get("suspect_rankings") or [{}])[0].get("name", "")
        if any(keyword in top_name for keyword in ("乘客", "网友", "媒体")):
            merged["suspect_rankings"] = fallback.get("suspect_rankings", merged["suspect_rankings"])
            merged["goal_response"] = fallback.get("goal_response", merged["goal_response"])
    merged["transient_cache"] = primary.get("transient_cache") or fallback.get("transient_cache", {})
    return merged


def _extract_with_rules(text: str, document: UploadedDocument, outcome: str, language: str) -> Dict:
    loc = L10N[language]
    mode = _classify_prompt_mode(text, outcome)
    lines = _material_segments(text)
    events = []
    clues = []
    actor_counter: Counter = Counter()
    actor_evidence_map: Dict[str, List[str]] = defaultdict(list)

    for index, line in enumerate(lines, start=1):
        time_hint, detail = _split_line(line, loc["unknown_time"])
        actors = _extract_actors(detail)
        event_id = f"evt_{index:02d}"
        for actor in actors:
            actor_counter[actor] += 1
            actor_evidence_map[actor].append(event_id)
        events.append(
            {
                "id": event_id,
                "time_hint": time_hint,
                "description": detail,
                "actors": actors,
                "evidence_refs": [event_id],
                "evidence_details": [
                    {
                        "ref_id": event_id,
                        "excerpt": detail[:220],
                        "source": document.source_name,
                        "note": loc["event_note"].format(ref_id=event_id),
                    }
                ],
                "inference_level": "direct" if actors else "mixed",
            }
        )
        score = _risk_score(detail)
        if score >= 4:
            clues.append(
                {
                    "id": f"clue_{len(clues) + 1:02d}",
                    "label": _clue_label(detail, language),
                    "detail": detail,
                    "actors": actors,
                    "event_ids": [event_id],
                    "risk_level": score,
                    "evidence_refs": [event_id, f"clue_{len(clues) + 1:02d}"],
                    "evidence_details": [
                        {
                            "ref_id": event_id,
                            "excerpt": detail[:220],
                            "source": document.source_name,
                            "note": loc["clue_note"].format(ref_id=f"clue_{len(clues) + 1:02d}"),
                        }
                    ],
                }
            )

    if not clues and events:
        ranked_events = sorted(events, key=lambda item: _risk_score(item["description"]), reverse=True)
        for fallback_index, event in enumerate(ranked_events[:4], start=1):
            clues.append(
                {
                    "id": f"clue_{fallback_index:02d}",
                    "label": _clue_label(event["description"], language),
                    "detail": event["description"],
                    "actors": event.get("actors", []),
                    "event_ids": [event["id"]],
                    "risk_level": max(3, _risk_score(event["description"])),
                    "evidence_refs": [event["id"], f"clue_{fallback_index:02d}"],
                    "evidence_details": event.get("evidence_details", []),
                }
            )

    actors = _build_actor_cards(actor_counter, actor_evidence_map, clues, language, document.source_name)
    suspect_rankings = _build_suspect_rankings(actors, events, language, mode)
    timeline = _build_reenactment_timeline(events)

    sections = _split_case_sections(text)
    background_summary = " ".join(sections["background"][:2])[:260] if sections["background"] else loc["summary"].format(source=document.source_name, outcome=outcome)

    return {
        "background_summary": background_summary,
        "actors": actors,
        "events": events,
        "clues": clues,
        "suspect_rankings": suspect_rankings,
        "reenactment_timeline": timeline,
        "evidence_notes": _build_evidence_notes(clues, language),
        "verdict_summary": _build_verdict(clues, suspect_rankings, language),
        "final_explanation": _build_explanation(outcome, clues, suspect_rankings, language),
        "uncertainties": [loc["uncertainty_1"], loc["uncertainty_2"]],
        "goal_response": _compose_goal_response(outcome, clues, suspect_rankings, timeline, _build_verdict(clues, suspect_rankings, language), language, mode=mode),
    }


def _build_actor_cards(
    actor_counter: Counter,
    actor_evidence_map: Dict[str, List[str]],
    clues: List[Dict],
    language: str,
    source_name: str,
) -> List[Dict]:
    loc = L10N[language]
    actor_names = [name for name, _ in actor_counter.most_common(8) if not _looks_like_entity_noise(name)]
    actors = []
    for name in actor_names:
        mentions = actor_evidence_map[name]
        suspicious_hits = sum(1 for clue in clues if name in clue.get("actors", []))
        suspicion_score = min(96, 35 + suspicious_hits * 15 + len(mentions) * 5)
        role = _guess_role(name, language)
        actors.append(
            {
                "name": name,
                "role": role,
                "relation": loc["relation_generic"].format(name=name, role=role),
                "suspicion_score": suspicion_score,
                "motive": loc["motive_generic"].format(name=name),
                "means": loc["means_generic"].format(role=role),
                "opportunity": loc["opportunity_generic"].format(count=len(mentions)),
                "evidence_refs": mentions[:4],
                "evidence_details": [
                    {
                        "ref_id": ref_id,
                        "excerpt": loc["actor_note"].format(name=name, count=len(mentions)),
                        "source": source_name,
                        "note": loc["event_note"].format(ref_id=ref_id),
                    }
                    for ref_id in mentions[:4]
                ],
            }
        )
    return actors


def _build_suspect_rankings(actors: List[Dict], events: List[Dict], language: str, mode: str = "general_backtrace") -> List[Dict]:
    loc = L10N[language]
    rankings = []
    def ranking_score(actor: Dict) -> float:
        score = float(actor.get("suspicion_score", 0))
        name = actor.get("name", "")
        role = actor.get("role", "")
        if mode == "relationship_emotion":
            if name in {"A", "B", "甲", "乙"}:
                score += 18
            if any(keyword in name for keyword in ("医院", "父亲", "老板", "同事")):
                score -= 12
        elif mode == "public_opinion_attribution":
            if any(keyword in name for keyword in ("联合航空", "航空", "航司", "公司", "United", "Airlines", "Express", "Munoz", "管理")):
                score += 18
            if any(keyword in role for keyword in ("Management", "管理")):
                score += 10
            if any(keyword in name for keyword in ("乘客", "网友", "媒体")):
                score -= 10
        return score

    for actor in sorted(actors, key=ranking_score, reverse=True)[:5]:
        supporting = [event["description"] for event in events if event["id"] in actor["evidence_refs"]][:3]
        rankings.append(
            {
                "name": actor["name"],
                "role": actor["role"],
                "suspicion_score": int(ranking_score(actor)),
                "motive": actor["motive"],
                "means": actor["means"],
                "opportunity": actor["opportunity"],
                "supporting_evidence": supporting,
                "concerns": [loc["no_hard_evidence"]],
            }
        )
    return rankings


def _build_reenactment_timeline(events: List[Dict]) -> List[Dict]:
    phases = ["setup", "build", "critical", "cover", "after"]
    return [
        {
            "order": index + 1,
            "phase": phases[min(index, len(phases) - 1)],
            "time_hint": event["time_hint"],
            "event": event["description"],
            "evidence_refs": event["evidence_refs"],
            "inference_level": event["inference_level"],
        }
        for index, event in enumerate(events[:10])
    ]


def _build_graph(structured: Dict, source_name: str, language: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
    loc = L10N[language]
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    actor_ids: Dict[str, str] = {}
    required_event_ids = set()
    related_nodes: Dict[str, set] = defaultdict(set)
    edge_keys = set()
    clue_to_events: Dict[str, List[str]] = {}
    clue_to_actors: Dict[str, List[str]] = {}
    event_to_actors: Dict[str, List[str]] = {}

    def add_edge(edge: GraphEdge) -> None:
        key = (edge.source, edge.target, edge.relation, tuple(edge.evidence_refs))
        if key in edge_keys:
            return
        edge_keys.add(key)
        related_nodes[edge.source].add(edge.target)
        related_nodes[edge.target].add(edge.source)
        edges.append(edge)

    for clue in structured.get("clues", [])[:10]:
        required_event_ids.update(clue.get("event_ids", []))

    for actor in structured.get("actors", [])[:8]:
        if _looks_like_entity_noise(actor["name"]):
            continue
        node_id = _node_id("actor", actor["name"])
        actor_ids[actor["name"]] = node_id
        nodes.append(
            GraphNode(
                node_id=node_id,
                label=actor["name"],
                node_type="actor",
                summary=actor["relation"],
                suspicion_score=float(actor["suspicion_score"]),
                evidence_refs=actor.get("evidence_refs", []),
                evidence_details=[EvidenceDetail.model_validate(item) for item in actor.get("evidence_details", [])],
                attributes={
                    "role": actor["role"],
                    "motive": actor["motive"],
                    "means": actor["means"],
                    "opportunity": actor["opportunity"],
                },
            )
        )

    event_items = structured.get("events", [])
    selected_events = []
    for event in event_items:
        if len(selected_events) < 12 or event["id"] in required_event_ids:
            selected_events.append(event)

    event_ids = set()
    for event in selected_events:
        if not _segment_has_material_value(event["description"]):
            continue
        event_ids.add(event["id"])
        event_to_actors[event["id"]] = [actor_name for actor_name in event.get("actors", []) if actor_name in actor_ids]
        nodes.append(
            GraphNode(
                node_id=event["id"],
                label=event["description"][:28],
                node_type="event",
                summary=event["time_hint"],
                suspicion_score=0.0,
                evidence_refs=event.get("evidence_refs", []),
                evidence_details=[EvidenceDetail.model_validate(item) for item in event.get("evidence_details", [])],
                attributes={"time_hint": event["time_hint"], "inference_level": event["inference_level"]},
            )
        )
        for actor_name in event.get("actors", []):
            if actor_name in actor_ids:
                related_nodes[actor_ids[actor_name]].add(event["id"])
                related_nodes[event["id"]].add(actor_ids[actor_name])
                add_edge(
                    GraphEdge(
                        source=actor_ids[actor_name],
                        target=event["id"],
                        relation="involved_in",
                        evidence=event["description"],
                        evidence_refs=event.get("evidence_refs", []),
                        evidence_details=[
                            EvidenceDetail(
                                ref_id=ref_id,
                                excerpt=event["description"][:220],
                                source=source_name,
                                note=loc["edge_note"].format(refs=", ".join(event.get("evidence_refs", []))),
                            )
                            for ref_id in event.get("evidence_refs", [])
                        ],
                        strength=0.82,
                    )
                )

    for clue in structured.get("clues", [])[:10]:
        if not _segment_has_material_value(clue["detail"]):
            continue
        clue_to_events[clue["id"]] = [event_id for event_id in clue.get("event_ids", []) if event_id in event_ids]
        clue_to_actors[clue["id"]] = [actor_name for actor_name in clue.get("actors", []) if actor_name in actor_ids]
        nodes.append(
            GraphNode(
                node_id=clue["id"],
                label=clue["label"],
                node_type="clue",
                summary=clue["detail"],
                suspicion_score=float(clue["risk_level"] * 10),
                evidence_refs=clue.get("evidence_refs", []),
                evidence_details=[EvidenceDetail.model_validate(item) for item in clue.get("evidence_details", [])],
                attributes={"risk_level": str(clue["risk_level"]), "detail": clue["detail"]},
            )
        )
        for event_id in clue.get("event_ids", []):
            if event_id in event_ids:
                add_edge(
                    GraphEdge(
                        source=event_id,
                        target=clue["id"],
                        relation="produces_clue",
                        evidence=clue["detail"],
                        evidence_refs=clue.get("evidence_refs", []),
                        evidence_details=[EvidenceDetail.model_validate(item) for item in clue.get("evidence_details", [])],
                        strength=0.87,
                    )
                )
        for actor_name in clue.get("actors", []):
            if actor_name in actor_ids:
                add_edge(
                    GraphEdge(
                        source=actor_ids[actor_name],
                        target=clue["id"],
                        relation="linked_to",
                        evidence=clue["detail"],
                        evidence_refs=clue.get("evidence_refs", []),
                        evidence_details=[EvidenceDetail.model_validate(item) for item in clue.get("evidence_details", [])],
                        strength=0.74,
                    )
                )

    selected_event_ids = [event["id"] for event in selected_events if event.get("id") in event_ids]
    for index in range(len(selected_event_ids) - 1):
        source_id = selected_event_ids[index]
        target_id = selected_event_ids[index + 1]
        source_event = next((item for item in selected_events if item.get("id") == source_id), None)
        target_event = next((item for item in selected_events if item.get("id") == target_id), None)
        if not source_event or not target_event:
            continue
        bridge_refs = [
            *[str(value) for value in _ensure_list(source_event.get("evidence_refs")) if str(value).strip()][:1],
            *[str(value) for value in _ensure_list(target_event.get("evidence_refs")) if str(value).strip()][:1],
        ]
        add_edge(
            GraphEdge(
                source=source_id,
                target=target_id,
                relation="precedes",
                evidence=f"{source_event.get('time_hint', '')} -> {target_event.get('time_hint', '')}",
                evidence_refs=bridge_refs[:2],
                evidence_details=[
                    EvidenceDetail(
                        ref_id=ref_id,
                        excerpt=f"{source_event.get('description', '')[:100]} -> {target_event.get('description', '')[:100]}",
                        source=source_name,
                        note="相邻事件按时间顺序连接。",
                    )
                    for ref_id in bridge_refs[:2]
                ],
                strength=0.56,
            )
        )

    actor_pair_map: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
    for event_id, actors in event_to_actors.items():
        refs = [event_id]
        for left_index in range(len(actors)):
            for right_index in range(left_index + 1, len(actors)):
                pair = tuple(sorted((actors[left_index], actors[right_index])))
                bucket = actor_pair_map.setdefault(pair, {"refs": [], "events": []})
                bucket["refs"].extend(refs)
                bucket["events"].append(event_id)

    for (left_actor, right_actor), payload in actor_pair_map.items():
        left_id = actor_ids.get(left_actor)
        right_id = actor_ids.get(right_actor)
        if not left_id or not right_id:
            continue
        refs = list(dict.fromkeys(payload["refs"]))[:3]
        add_edge(
            GraphEdge(
                source=left_id,
                target=right_id,
                relation="co_occurs_with",
                evidence=f"{left_actor} 与 {right_actor} 在多个事件中共同出现。",
                evidence_refs=refs,
                evidence_details=[
                    EvidenceDetail(
                        ref_id=ref_id,
                        excerpt=f"{left_actor} / {right_actor} 共同关联到事件 {ref_id}",
                        source=source_name,
                        note="由共享事件生成的人物关系边。",
                    )
                    for ref_id in refs
                ],
                strength=0.64,
            )
        )

    clue_ids = [clue["id"] for clue in structured.get("clues", [])[:10] if clue.get("id") in clue_to_events]
    for left_index in range(len(clue_ids)):
        for right_index in range(left_index + 1, len(clue_ids)):
            left_id = clue_ids[left_index]
            right_id = clue_ids[right_index]
            shared_events = sorted(set(clue_to_events.get(left_id, [])) & set(clue_to_events.get(right_id, [])))
            shared_actors = sorted(set(clue_to_actors.get(left_id, [])) & set(clue_to_actors.get(right_id, [])))
            if not shared_events and not shared_actors:
                continue
            refs = [*shared_events[:2], *[actor_ids[name] for name in shared_actors[:1] if name in actor_ids]]
            add_edge(
                GraphEdge(
                    source=left_id,
                    target=right_id,
                    relation="corroborates",
                    evidence=" / ".join([*(shared_events[:2]), *shared_actors[:2]]) or "线索之间存在共享上下文。",
                    evidence_refs=refs[:3],
                    evidence_details=[
                        EvidenceDetail(
                            ref_id=ref_id,
                            excerpt=f"{left_id} 与 {right_id} 共享事件或人物上下文。",
                            source=source_name,
                            note="由共享人物或事件生成的线索关联边。",
                        )
                        for ref_id in refs[:3]
                    ],
                    strength=0.6,
                )
            )

    for node in nodes:
        node.related_node_ids = sorted(related_nodes.get(node.node_id, set()))

    return nodes, edges


def _build_evidence_items(structured: Dict, source_name: str) -> List[EvidenceItem]:
    clues = structured.get("clues", [])
    if clues:
        return [
            EvidenceItem(
                evidence_id=clue["id"],
                label=clue["label"],
                detail=clue["detail"],
                source=source_name,
                evidence_level="direct" if clue.get("event_ids") else "inferred",
                risk_score=int(clue["risk_level"]),
            )
            for clue in clues[:10]
        ]
    return [
        EvidenceItem(
            evidence_id=event["id"],
            label=event["description"][:32],
            detail=event["description"],
            source=source_name,
            evidence_level=event["inference_level"],
            risk_score=_risk_score(event["description"]),
        )
        for event in structured.get("events", [])[:6]
    ]


def _build_agent_steps(structured: Dict, language: str) -> List[AgentStep]:
    return [_run_agent_turn_with_rules(structured, language, spec, [], 1) for spec in AGENTS]


def _build_agent_profiles(structured: Dict, language: str) -> List[AgentProfile]:
    return [_build_agent_profile_from_spec(spec, structured, language) for spec in AGENTS]


def _build_agent_dialogue(structured: Dict, language: str) -> List[AgentExchange]:
    steps = _build_agent_steps(structured, language)
    return [
        _build_exchange(step.agent_name, _next_agent_name(step.agent_name), step, structured, language, step.round_index)
        for step in steps
    ]


def _build_final_result(structured: Dict, agent_steps: Optional[List[AgentStep]] = None) -> CaseFinalResult:
    agent_steps = agent_steps or []
    actor_map = {item.get("name"): item for item in structured.get("actors", []) if item.get("name")}
    transient_cache = structured.get("transient_cache", {}) or {}
    normalized_rankings: List[SuspectRank] = []
    for item in structured.get("suspect_rankings", [])[:5]:
        name = _clean_segment(str(item.get("name", "")))
        if not name:
            continue
        actor = actor_map.get(name, {})
        role = _clean_segment(str(item.get("role", ""))) or _clean_segment(str(actor.get("role", ""))) or "Key actor"
        motive = _clean_segment(str(item.get("motive", ""))) or _clean_segment(str(actor.get("motive", ""))) or "Need more evidence."
        means = _clean_segment(str(item.get("means", ""))) or _clean_segment(str(actor.get("means", ""))) or "Need more evidence."
        opportunity = _clean_segment(str(item.get("opportunity", ""))) or _clean_segment(str(actor.get("opportunity", ""))) or "Need more evidence."
        normalized_rankings.append(
            SuspectRank(
                name=name,
                role=role,
                suspicion_score=max(1, _ensure_int(item.get("suspicion_score"), _ensure_int(actor.get("suspicion_score"), 50))),
                motive=motive,
                means=means,
                opportunity=opportunity,
                supporting_evidence=[str(value) for value in _ensure_list(item.get("supporting_evidence")) if str(value).strip()][:4],
                concerns=[str(value) for value in _ensure_list(item.get("concerns")) if str(value).strip()][:4],
            )
        )
    normalized_timeline = [
        {
            "order": max(1, _ensure_int(item.get("order"), index + 1)),
            "phase": str(item.get("phase", "build")),
            "time_hint": str(item.get("time_hint", "")),
            "event": str(item.get("event", "")),
            "evidence_refs": [str(value) for value in _ensure_list(item.get("evidence_refs")) if str(value).strip()][:4],
            "inference_level": str(item.get("inference_level", "mixed")),
        }
        for index, item in enumerate(structured.get("reenactment_timeline", [])[:10])
        if str(item.get("event", "")).strip()
    ]
    stable_goal_response = _stabilize_goal_response(
        structured,
        str(structured.get("goal_response", "")),
        structured.get("suspect_rankings", []),
        normalized_timeline,
        detect_language(
            f"{structured.get('expected_outcome', '')}\n{structured.get('final_explanation', '')}",
            structured.get("expected_outcome", ""),
        ),
    )
    result = CaseFinalResult(
        case_explanation=structured.get("final_explanation", ""),
        verdict_summary=structured.get("verdict_summary", ""),
        suspect_rankings=normalized_rankings,
        reenactment_timeline=[
            ReconstructionStep(
                order=item["order"],
                phase=item["phase"],
                time_hint=item["time_hint"],
                event=item["event"],
                evidence_refs=item["evidence_refs"],
                inference_level=item["inference_level"],
            )
            for item in normalized_timeline
        ],
        evidence_notes=_normalize_note_strings([*structured.get("evidence_notes", []), *[f"{step.agent_name}: {' | '.join(step.findings[:2])}" for step in agent_steps[:3]]])[:8],
        uncertainties=_normalize_note_strings(structured.get("uncertainties", [])),
        goal_response=_expand_evidence_aliases(stable_goal_response, transient_cache.get("evidence_aliases", {})),
    )
    result.output_panels = _build_output_panels_localized(structured, result, agent_steps)
    if not result.goal_response:
        result.goal_response = result.output_panels[0].body if result.output_panels else result.case_explanation
    return result


def _build_output_panels(structured: Dict, final_result: CaseFinalResult, agent_steps: List[AgentStep]) -> List[OutputPanel]:
    expected_outcome = structured.get("expected_outcome", "")
    mode = _classify_prompt_mode("\n".join(_normalize_note_strings(structured.get("evidence_notes", []))), expected_outcome)
    ranking_lines = [
        f"{index + 1}. {item.name} | {item.role} | {item.motive}"
        for index, item in enumerate(final_result.suspect_rankings[:5])
    ]
    timeline_lines = [
        f"{step.order}. {step.time_hint} | {step.phase} | {step.event}"
        for step in final_result.reenactment_timeline[:8]
    ]
    evidence_refs = [ref for step in final_result.reenactment_timeline[:6] for ref in step.evidence_refs[:2]]
    agent_lines = [f"{step.agent_name} R{step.round_index}: {' | '.join(step.findings[:2])}" for step in agent_steps[:8]]

    panels = [
        OutputPanel(
            panel_id="goal_response",
            title="目标回答",
            panel_type="goal",
            summary="点对点回应当前分析目标。",
            body=final_result.goal_response or f"{final_result.case_explanation}\n\n{final_result.verdict_summary}",
            items=[expected_outcome] if expected_outcome else [],
            evidence_refs=evidence_refs[:6],
        ),
        OutputPanel(
            panel_id="analysis",
            title="分析解释",
            panel_type="analysis",
            summary="主解释与综合判断。",
            body=final_result.case_explanation,
            items=[final_result.verdict_summary],
            evidence_refs=evidence_refs[:6],
        ),
        OutputPanel(
            panel_id="ranking",
            title=_mode_ranking_label(mode),
            panel_type="ranking",
            summary="关键对象及其驱动链。",
            body=final_result.verdict_summary,
            items=ranking_lines,
            evidence_refs=evidence_refs[:6],
        ),
        OutputPanel(
            panel_id="timeline",
            title="回溯时间线",
            panel_type="timeline",
            summary="按证据重建形成过程。",
            body="时间线可用于回看关键转折与证据覆盖。",
            items=timeline_lines,
            evidence_refs=evidence_refs[:8],
        ),
        OutputPanel(
            panel_id="evidence",
            title="证据与不确定性",
            panel_type="evidence",
            summary="保留支持点与未决问题。",
            body="需要同时关注支持证据与仍待补强的环节。",
            items=[*final_result.evidence_notes[:5], *final_result.uncertainties[:4]],
            evidence_refs=evidence_refs[:8],
        ),
        OutputPanel(
            panel_id="agents",
            title=_mode_specific_panel_title(mode),
            panel_type="mode",
            summary="汇总多智能体协作后的模式化观察。",
            body=_mode_specific_panel_body(mode, final_result),
            items=agent_lines[:8],
            evidence_refs=evidence_refs[:8],
        ),
    ]
    return panels[:6]


def _mode_specific_panel_title(mode: str) -> str:
    return {
        "case_reenactment": "机制与疑点",
        "relationship_emotion": "鎯呯华涓庡叧绯婚摼",
        "public_opinion_attribution": "浼犳挱涓庡綊鍥犻摼",
    }.get(mode, "鎵╁睍瑙傚療")


def _mode_specific_panel_body(mode: str, final_result: CaseFinalResult) -> str:
    if mode == "relationship_emotion":
        return "聚焦情绪波动、互动策略和关系温度变化，帮助解释局面是如何逐步形成的。"
    if mode == "public_opinion_attribution":
        return "聚焦议题扩散、关键节点和责任归因，帮助识别情绪升级与叙事转向。"
    if mode == "case_reenactment":
        return "聚焦作案机制、证据闭环和替代解释，帮助重建最可能的形成过程。"
    return final_result.verdict_summary or final_result.case_explanation


def _build_agent_profile_from_spec(spec: Dict, structured: Dict, language: str) -> AgentProfile:
    loc = L10N[language]
    top_clue = (structured.get("clues") or [{}])[0]
    top_suspect = (structured.get("suspect_rankings") or [{}])[0]
    top_event = (structured.get("reenactment_timeline") or [{}])[0]
    focus_map = {
        "Evidence Agent": top_clue.get("detail", loc["few_clues"]),
        "Relationship Agent": top_suspect.get("name", loc["core_actor"]),
        "Suspicion Agent": top_suspect.get("motive", top_suspect.get("name", loc["core_actor"])),
        "Reconstruction Agent": top_event.get("event", loc["few_clues"]),
        "Judge Agent": structured.get("verdict_summary", loc["few_clues"]),
    }
    memory_map = {
        "Evidence Agent": structured.get("evidence_notes", [])[:2],
        "Relationship Agent": [actor.get("relation", "") for actor in structured.get("actors", [])[:2]],
        "Suspicion Agent": [item.get("name", "") for item in structured.get("suspect_rankings", [])[:3]],
        "Reconstruction Agent": [item.get("event", "") for item in structured.get("reenactment_timeline", [])[:2]],
        "Judge Agent": structured.get("uncertainties", [])[:2],
    }
    return AgentProfile(
        agent_name=spec["agent_name"],
        codename=spec["codename"],
        role=spec["role"][language],
        disposition=spec["disposition"][language],
        current_focus=focus_map.get(spec["agent_name"], loc["few_clues"]),
        persistent_state=loc["agent_context"],
        memory_notes=[note for note in memory_map.get(spec["agent_name"], []) if note],
        accent=spec["accent"],
    )


def _run_agent_turn_with_rules(
    structured: Dict,
    language: str,
    spec: Dict,
    prior_steps: List[AgentStep],
    round_index: int,
) -> AgentStep:
    loc = L10N[language]
    bundle_map = {
        "Evidence Agent": structured.get("evidence_notes", [])[:4],
        "Relationship Agent": [f"{actor['name']}: {actor['relation']}" for actor in structured.get("actors", [])[:4]],
        "Suspicion Agent": [f"{rank['name']} #{index + 1} / {rank['suspicion_score']}" for index, rank in enumerate(structured.get("suspect_rankings", [])[:4])],
        "Reconstruction Agent": [f"{step['time_hint']} - {step['event']}" for step in structured.get("reenactment_timeline", [])[:4]],
        "Judge Agent": [structured.get("verdict_summary", ""), *structured.get("uncertainties", [])[:2]],
    }
    findings = bundle_map.get(spec["agent_name"], [])[:4]
    if prior_steps:
        findings = [*findings, f"Round {round_index} context: {', '.join(step.agent_name for step in prior_steps[-4:])}"][:5]
    actor_ref_map = {actor.get("name"): actor.get("evidence_refs", []) for actor in structured.get("actors", [])}
    focus_map = {
        "Evidence Agent": [item.get("id", "") for item in structured.get("clues", [])[:3]],
        "Relationship Agent": [ref for actor in structured.get("actors", [])[:3] for ref in actor.get("evidence_refs", [])[:2]],
        "Suspicion Agent": [ref for item in structured.get("suspect_rankings", [])[:3] for ref in actor_ref_map.get(item.get("name"), [])[:2]],
        "Reconstruction Agent": [ref for item in structured.get("reenactment_timeline", [])[:3] for ref in item.get("evidence_refs", [])[:2]],
        "Judge Agent": [item.get("id", "") for item in structured.get("clues", [])[:2]],
    }
    return AgentStep(
        agent_name=spec["agent_name"],
        purpose=loc[spec["purpose_key"]],
        status="completed",
        findings=findings,
        confidence=min(0.72 + len(prior_steps) * 0.04, 0.94),
        round_index=round_index,
        focus_refs=[str(item) for item in focus_map.get(spec["agent_name"], []) if str(item)],
    )


def _run_agent_turn_with_llm(
    llm_client: OpenAICompatibleClient,
    structured_case: Dict,
    expected_outcome: str,
    detected_language: str,
    document: UploadedDocument,
    spec: Dict,
    prior_steps: List[AgentStep],
    prior_dialogue: List[AgentExchange],
    round_index: int,
) -> Optional[AgentStep]:
    system_prompt, user_prompt = _build_agent_turn_prompts(
        structured_case, expected_outcome, detected_language, document, spec, prior_steps, prior_dialogue, round_index
    )
    payload = llm_client.complete_json(system_prompt, user_prompt)
    if not payload or not isinstance(payload.get("findings"), list):
        return None
    try:
        confidence = float(payload.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    return AgentStep(
        agent_name=spec["agent_name"],
        purpose=L10N[detected_language][spec["purpose_key"]],
        status="completed",
        findings=[str(item).strip() for item in payload.get("findings", []) if str(item).strip()][:5],
        confidence=max(0.0, min(confidence, 0.99)),
        round_index=round_index,
        focus_refs=[str(item).strip() for item in payload.get("focus_refs", []) if str(item).strip()][:5],
    )


def _build_agent_turn_prompts(
    structured_case: Dict,
    expected_outcome: str,
    detected_language: str,
    document: UploadedDocument,
    spec: Dict,
    prior_steps: List[AgentStep],
    prior_dialogue: List[AgentExchange],
    round_index: int,
) -> Tuple[str, str]:
    target_language = "Simplified Chinese" if detected_language == "zh-CN" else "English"
    total_rounds = _normalize_collaboration_rounds(structured_case.get("collaboration_rounds"))
    mode = _classify_prompt_mode(
        "\n".join([structured_case.get("background_summary", ""), *structured_case.get("evidence_notes", [])]),
        expected_outcome,
    )
    prior_summary = "\n".join(f"- {step.agent_name}: {' | '.join(step.findings[:3])}" for step in prior_steps) or "- None yet."
    dialogue_summary = "\n".join(
        f"- round {item.round_index} {item.speaker} -> {item.audience}: {item.message}"
        for item in prior_dialogue[-8:]
    ) or "- None yet."
    actor_block = "\n".join(
        f"- {item.get('name')}: role={item.get('role')}; refs={', '.join(item.get('evidence_refs', []))}"
        for item in structured_case.get("actors", [])[:8]
    ) or "- None."
    clue_block = "\n".join(
        f"- {item.get('id')}: {item.get('label')} / refs={', '.join(item.get('evidence_refs', []))}"
        for item in structured_case.get("clues", [])[:10]
    ) or "- None."
    timeline_block = "\n".join(
        f"- {item.get('order')}. {item.get('time_hint')} -> {item.get('event')} / refs={', '.join(item.get('evidence_refs', []))}"
        for item in structured_case.get("reenactment_timeline", [])[:8]
    ) or "- None."
    graph_context = _build_agent_graph_context(structured_case, spec["agent_name"])
    system_prompt = f"""
You are one specialist analyst inside Salmon.
Return one valid JSON object and nothing else.
All natural-language values must be written in {target_language}.
Keep the JSON keys in English.
Stay evidence-constrained and reusable across future cases.
The current analysis mode is: {mode}.
You are participating in a multi-round collaboration, so react to earlier specialist findings instead of repeating them.

Output schema:
findings: [string]
confidence: number
focus_refs: [string]
""".strip()
    user_prompt = f"""
Task:
{expected_outcome}

Document:
- source_name: {document.source_name}
- source_type: {document.source_type}

Current specialist:
- agent_name: {spec['agent_name']}
- role: {spec['role'][detected_language]}
- purpose: {L10N[detected_language][spec['purpose_key']]}
- round_index: {round_index} / {total_rounds}
- mode_focus: {_mode_agent_focus(mode, spec['agent_name'])}

Actors:
{actor_block}

Clues:
{clue_block}

Timeline:
{timeline_block}

Prior agent outputs:
{prior_summary}

Prior dialogue:
{dialogue_summary}

Relevant graph / retrieval context:
{graph_context}

Constraints:
- Produce 3 to 5 findings.
- Mention relevant reference ids directly inside the findings when possible.
- In later rounds, challenge, refine, or extend previous findings instead of restating them.
- focus_refs should contain the ids most central to this turn.
- Keep the style reusable; do not assume facts outside the material.
""".strip()
    return system_prompt, user_prompt
def _run_final_synthesis_with_llm(
    llm_client: OpenAICompatibleClient,
    structured_case: Dict,
    expected_outcome: str,
    detected_language: str,
    document: UploadedDocument,
    agent_steps: List[AgentStep],
) -> Optional[CaseFinalResult]:
    system_prompt, user_prompt = _build_final_synthesis_prompts(
        structured_case, expected_outcome, detected_language, document, agent_steps
    )
    payload = llm_client.complete_json(system_prompt, user_prompt)
    if not payload:
        return None
    required = ["case_explanation", "verdict_summary", "suspect_rankings", "reenactment_timeline", "evidence_notes", "uncertainties", "goal_response"]
    if any(key not in payload for key in required):
        return None
    normalized = _normalize_llm_payload(
        {
            "actors": structured_case.get("actors", []),
            "events": structured_case.get("events", []),
            "clues": structured_case.get("clues", []),
            "expected_outcome": expected_outcome,
            **payload,
        }
    )
    return _build_final_result(normalized, agent_steps)


def _build_final_synthesis_prompts(
    structured_case: Dict,
    expected_outcome: str,
    detected_language: str,
    document: UploadedDocument,
    agent_steps: List[AgentStep],
) -> Tuple[str, str]:
    target_language = "Simplified Chinese" if detected_language == "zh-CN" else "English"
    mode = _classify_prompt_mode(
        "\n".join([structured_case.get("background_summary", ""), *structured_case.get("evidence_notes", [])]),
        expected_outcome,
    )
    agent_block = "\n".join(f"- {step.agent_name}: {' | '.join(step.findings[:4])}" for step in agent_steps) or "- None."
    ranking_block = "\n".join(
        f"- {item.get('name')}: score={item.get('suspicion_score')} role={item.get('role')}"
        for item in structured_case.get("suspect_rankings", [])[:5]
    ) or "- None."
    timeline_block = "\n".join(
        f"- {item.get('order')}. {item.get('time_hint')} -> {item.get('event')} / refs={', '.join(item.get('evidence_refs', []))}"
        for item in structured_case.get("reenactment_timeline", [])[:10]
    ) or "- None."
    graph_context = _build_agent_graph_context(structured_case, "Judge Agent")
    system_prompt = f"""
You are Salmon's final synthesis agent.
Return one valid JSON object and nothing else.
All natural-language values must be written in {target_language}.
Keep the JSON keys in English.
Stay evidence-constrained and preserve uncertainty.
The current analysis mode is: {mode}.
Keep suspect_rankings compatible with the existing schema even when they represent key actors or responsibility centers.
goal_response must answer the user's analysis goal directly before the reader inspects the other panels.
If the task contains multiple sub-questions, answer them one by one with numbered items that mirror the user's wording.
When you cite evidence aliases such as E1, C1, T1, EVT_01, or CLUE_01, immediately expand them with the original clue or event content in parentheses.
""".strip()
    user_prompt = f"""
Task:
{expected_outcome}

Document:
- source_name: {document.source_name}
- source_type: {document.source_type}

Candidate ranking:
{ranking_block}

Working timeline:
{timeline_block}

Agent outputs:
{agent_block}

Relevant graph / retrieval context:
{graph_context}

Mode guidance:
{_mode_specific_constraints(mode)}

Output schema reminder:
- case_explanation
- verdict_summary
- suspect_rankings
- reenactment_timeline
- evidence_notes
- uncertainties
- goal_response
""".strip()
    return system_prompt, user_prompt


def _build_agent_graph_context(structured_case: Dict, agent_name: str) -> str:
    graph_context = structured_case.get("graph_context", {})
    nodes = graph_context.get("nodes", [])
    edges = graph_context.get("edges", [])

    if not nodes:
        return "- No graph context available."

    if agent_name == "Evidence Agent":
        selected_nodes = [node for node in nodes if node.get("node_type") == "clue"][:5]
        selected_edges = [edge for edge in edges if "supported_by" in edge.get("relation", "")][:5]
    elif agent_name == "Relationship Agent":
        selected_nodes = [node for node in nodes if node.get("node_type") == "actor"][:6]
        selected_edges = [edge for edge in edges if edge.get("relation") in {"involved_in", "connected_to"}][:6]
    elif agent_name == "Suspicion Agent":
        selected_nodes = sorted(nodes, key=lambda item: float(item.get("suspicion_score", 0.0)), reverse=True)[:5]
        selected_edges = [edge for edge in edges if edge.get("relation") in {"involved_in", "supported_by"}][:6]
    elif agent_name == "Reconstruction Agent":
        selected_nodes = [node for node in nodes if node.get("node_type") == "event"][:8]
        selected_edges = [edge for edge in edges if edge.get("relation") in {"precedes", "connected_to", "supported_by"}][:8]
    else:
        selected_nodes = nodes[:8]
        selected_edges = edges[:8]

    node_lines = [
        f"- node {node.get('node_id')}: {node.get('label')} | {node.get('node_type')} | refs={', '.join(node.get('evidence_refs', []))}"
        for node in selected_nodes
    ]
    edge_lines = [
        f"- edge {edge.get('source')} -> {edge.get('target')} | {edge.get('relation')} | refs={', '.join(edge.get('evidence_refs', []))}"
        for edge in selected_edges
    ]
    return "\n".join([*node_lines, *edge_lines]) or "- No focused graph context available."
def _build_exchange(agent_name: str, audience: str, step: AgentStep, structured: Dict, language: str, round_index: int) -> AgentExchange:
    loc = L10N[language]
    top_clue = (structured.get("clues") or [{}])[0]
    top_suspect = (structured.get("suspect_rankings") or [{}])[0]
    top_timeline = (structured.get("reenactment_timeline") or [{}])[0]
    fallback = {
        "Evidence Agent": loc["dialogue_1"].format(label=top_clue.get("label", loc["critical_anomaly"])),
        "Relationship Agent": loc["dialogue_2"].format(suspect=top_suspect.get("name", loc["core_actor"])),
        "Suspicion Agent": loc["dialogue_3"].format(suspect=top_suspect.get("name", loc["core_actor"])),
        "Reconstruction Agent": loc["dialogue_4"].format(event=top_timeline.get("event", "early anomaly")),
        "Judge Agent": loc["dialogue_5"],
    }
    return AgentExchange(
        step_id=f"exchange_r{round_index}_{re.sub(r'[^a-z0-9]+', '_', agent_name.lower()).strip('_')}",
        speaker=agent_name,
        audience=audience,
        message=step.findings[0] if step.findings else fallback.get(agent_name, loc["few_clues"]),
        stage="completed",
        round_index=round_index,
        evidence_refs=step.focus_refs[:4],
    )


def _agent_spec(agent_name: str) -> Dict:
    for spec in AGENTS:
        if spec["agent_name"] == agent_name:
            return spec
    return AGENTS[0]


def _next_agent_name(agent_name: str) -> str:
    names = [item["agent_name"] for item in AGENTS]
    try:
        index = names.index(agent_name)
    except ValueError:
        return "All Agents"
    return names[index + 1] if index + 1 < len(names) else "All Agents"


def _split_line(line: str, unknown_time: str) -> Tuple[str, str]:
    for separator in ("|", "\uff1a", ":"):
        if separator in line:
            left, right = line.split(separator, 1)
            if separator == "|" or any(char.isdigit() for char in left):
                return left.strip(), right.strip()
    return unknown_time, line.strip()


def _material_segments(text: str) -> List[str]:
    sectioned = _split_case_sections(text)
    raw_segments = [*sectioned["background"], *sectioned["clues"], *sectioned["extra"], *DocumentParser.segment_text(text)]
    cleaned: List[str] = []
    seen = set()
    for raw_segment in raw_segments:
        segment = _clean_segment(raw_segment)
        for piece in _split_long_segment(segment):
            piece = _clean_segment(piece)
            if not _segment_has_material_value(piece):
                continue
            dedupe_key = re.sub(r"\s+", " ", piece).lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            cleaned.append(piece)
    return cleaned[:48]


def _extract_actors(detail: str) -> List[str]:
    actors: List[str] = []
    english_candidates = re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+){0,2}\b", detail)
    for candidate in english_candidates:
        if candidate.lower() in {"the", "and", "but"} or _looks_like_entity_noise(candidate):
            continue
        actors.append(candidate.strip())
    for candidate in re.findall(r"(?<![A-Za-z])([A-Z])(?=\s*[：:和与、，。！？\s])", detail):
        actors.append(candidate.strip())

    chinese_patterns = [
        r"[\u4e00-\u9fff]{2,4}(?:先生|女士|夫人|同学|医生|教授|警官|经理|主任|护士|继父|继母|男友|女友|丈夫|妻子)",
        r"[\u4e00-\u9fff]{2,8}(?:医生|教授|警察|警官|保安|经理|主任|维修|护士|司机|财务|乘务长|机长|发言人)",
        r"(?:机组|航司|公司|品牌|警方|医院|学校|平台|媒体|网友|乘客|员工|家属)",
    ]
    for pattern in chinese_patterns:
        for token in re.findall(pattern, detail):
            token = _clean_segment(token)
            if token and not _looks_like_entity_noise(token):
                actors.append(token)
    contextual_name_patterns = [
        r"([\u4e00-\u9fff]{2,3})(?=说|称|表示|觉得|认为|要求|陪|回复|联系|告诉|进入|离开|来到|安排|通知|指出|报警|解释|拒绝|同意|反对)",
        r"(?:和|与|对|向)([\u4e00-\u9fff]{2,3})(?=[，。！？：:\s])",
    ]
    for pattern in contextual_name_patterns:
        for token in re.findall(pattern, detail):
            token = _clean_segment(token)
            if token and _looks_like_name(token):
                actors.append(token)

    return list(dict.fromkeys(actors))[:5]


def _looks_like_name(token: str) -> bool:
    common_surnames = {
        "赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "褚", "卫",
        "蒋", "沈", "韩", "杨", "朱", "秦", "尤", "许", "何", "吕", "施", "张",
        "孔", "曹", "严", "华", "金", "魏", "陶", "姜", "戚", "谢", "邹", "喻",
        "柏", "水", "窦", "章", "云", "苏", "潘", "葛", "奚", "范", "彭", "郎",
        "鲁", "韦", "昌", "马", "苗", "凤", "花", "方", "俞", "任", "袁", "柳",
        "酆", "鲍", "史", "唐", "费", "廉", "岑", "薛", "雷", "贺", "倪", "汤",
        "滕", "殷", "罗", "毕", "郝", "邬", "安", "常", "乐", "于", "时", "傅",
        "皮", "卞", "齐", "康", "伍", "余", "元", "卜", "顾", "孟", "平", "黄",
    }
    if len(token) not in {2, 3}:
        return False
    if token[0] not in common_surnames:
        return False
    return not any(keyword in token for keyword in ROLE_KEYWORDS)


def _risk_score(detail: str) -> int:
    lowered = detail.lower()
    score = 1
    for word, weight in RISK_WORDS.items():
        if word in lowered or word in detail:
            score += weight
    return min(score, 10)


def _clue_label(detail: str, language: str) -> str:
    lowered = detail.lower()
    if any(word in detail or word in lowered for word in ("鐩戞帶", "鐩插尯", "褰曞儚", "camera", "surveillance", "footage")):
        return "\u76d1\u63a7\u5f02\u5e38" if language == "zh-CN" else "Surveillance anomaly"
    if any(word in detail or word in lowered for word in ("缂哄け", "灏佸瓨", "绡℃敼", "missing", "tamper", "record")):
        return "\u8bb0\u5f55\u5f02\u5e38" if language == "zh-CN" else "Record anomaly"
    if any(word in detail or word in lowered for word in ("瑁呯疆", "閫氶亾", "璁惧", "鏈哄埗", "device", "access", "mechanism")):
        return "\u673a\u5236\u7ebf\u7d22" if language == "zh-CN" else "Mechanism clue"
    if any(word in detail or word in lowered for word in ("淇濋櫓", "璐骇", "鍊哄姟", "insurance", "property", "debt")):
        return "\u5229\u76ca\u7ebf\u7d22" if language == "zh-CN" else "Incentive clue"
    return L10N[language]["critical_anomaly"]


def _guess_role(name: str, language: str) -> str:
    lowered = name.lower()
    pairs = [
        ("doctor", "\u533b\u751f", "Doctor"),
        ("dr", "\u533b\u751f", "Doctor"),
        ("\u7ee7\u7236", "\u7ee7\u7236/\u76d1\u62a4\u4eba", "Stepfather/guardian"),
        ("\u4fdd\u5b89", "\u73b0\u573a\u5b89\u4fdd", "Security"),
        ("\u7ef4\u4fee", "\u6280\u672f\u7ef4\u62a4", "Maintenance"),
        ("\u8b66\u5bdf", "\u6267\u6cd5\u89d2\u8272", "Law enforcement"),
        ("\u6559\u6388", "\u4e13\u4e1a\u4eba\u58eb", "Professional"),
        ("\u7ecf\u7406", "\u7ba1\u7406\u5c42", "Management"),
    ]
    for key, zh_value, en_value in pairs:
        if key in lowered or key in name:
            return zh_value if language == "zh-CN" else en_value
    return L10N[language]["role_generic"]


def _build_evidence_notes(clues: List[Dict], language: str) -> List[str]:
    if clues:
        return [f"{clue['id']} {clue['label']}: {clue['detail']}" for clue in clues[:5]]
    return [L10N[language]["few_clues"]]


def _build_verdict(clues: List[Dict], suspect_rankings: List[Dict], language: str) -> str:
    loc = L10N[language]
    score = sum(clue.get("risk_level", 0) for clue in clues[:4])
    suspect = suspect_rankings[0]["name"] if suspect_rankings else loc["core_actor"]
    if score >= 22:
        return loc["verdict_strong"].format(suspect=suspect)
    if score >= 12:
        return loc["verdict_mid"].format(suspect=suspect)
    return loc["verdict_light"]


def _build_explanation(outcome: str, clues: List[Dict], suspect_rankings: List[Dict], language: str) -> str:
    loc = L10N[language]
    clue_sep = "\uff1b" if language == "zh-CN" else "; "
    suspect_sep = "\u3001" if language == "zh-CN" else ", "
    clue_text = clue_sep.join(clue["detail"] for clue in clues[:3]) or "n/a"
    suspect_text = suspect_sep.join(rank["name"] for rank in suspect_rankings[:3]) or loc["core_actor"]
    return " ".join(
        [
            loc["explain_a"].format(outcome=outcome),
            loc["explain_b"].format(clues=clue_text),
            loc["explain_c"].format(suspects=suspect_text),
        ]
    )


def _build_transient_cache(clues: List[Dict], events: List[Dict], outcome: str) -> Dict[str, Dict]:
    return {
        "goal_items": _extract_goal_items(outcome),
        "evidence_aliases": _build_evidence_aliases(clues, events),
    }


def _build_evidence_aliases(clues: List[Dict], events: List[Dict]) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for index, clue in enumerate(clues[:10], start=1):
        detail = _clean_segment(str(clue.get("detail", "")))
        if not detail:
            continue
        aliases[f"E{index}"] = detail
        aliases[f"C{index}"] = detail
        clue_id = str(clue.get("id", "")).upper()
        if clue_id:
            aliases[clue_id] = detail
    for index, event in enumerate(events[:10], start=1):
        detail = _clean_segment(str(event.get("description", "")))
        if not detail:
            continue
        aliases[f"T{index}"] = detail
        event_id = str(event.get("id", "")).upper()
        if event_id:
            aliases[event_id] = detail
    return aliases


def _expand_evidence_aliases(text: str, alias_map: Dict[str, str]) -> str:
    if not text or not alias_map:
        return text

    def replace(match: re.Match) -> str:
        alias = match.group(0)
        normalized = alias.upper()
        detail = alias_map.get(normalized)
        if not detail:
            return alias
        return f"{alias}（{detail}）"

    pattern = re.compile(r"\b(?:E\d+|C\d+|T\d+|EVT_\d+|CLUE_\d+)\b", flags=re.IGNORECASE)
    return pattern.sub(replace, text)


def _extract_goal_items(outcome: str) -> List[str]:
    cleaned = (outcome or "").strip()
    if not cleaned:
        return []

    split_pattern = re.compile(r"(?:^|[\n；;])\s*(?:[-*]|\d+[.)、）]|[一二三四五六七八九十]+[、.)）])\s*")
    markers = list(split_pattern.finditer(cleaned))
    if len(markers) >= 2 or (markers and markers[0].start() == 0):
        items: List[str] = []
        for index, match in enumerate(markers):
            start = match.end()
            end = markers[index + 1].start() if index + 1 < len(markers) else len(cleaned)
            item = cleaned[start:end].strip("；; \n")
            item = re.sub(r"^\*+|\*+$", "", item).strip()
            if item:
                items.append(item)
        if items:
            return _dedupe_goal_items(items)

    question_parts = re.split(r"(?<=[\?\uFF1F])\s*", cleaned)
    question_items = [part.strip("；;。!！ \n") for part in question_parts if part.strip("；;。!！ \n")]
    if len(question_items) >= 2:
        return _dedupe_goal_items(question_items)

    clause_parts = re.split(
        r"[；;]\s*|(?:\n+)|(?:\s+(?=(?:另外|并且|以及|同时|再看|再判断|还要|还需|whether|also|and)\b))",
        cleaned,
        flags=re.IGNORECASE,
    )
    clause_items = [_clean_goal_item(item) for item in clause_parts]
    clause_items = [item for item in clause_items if item]
    if len(clause_items) >= 2:
        return _dedupe_goal_items(clause_items)

    return [cleaned]


def _clean_goal_item(item: str) -> str:
    cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)、）]|[一二三四五六七八九十]+[、.)）])\s*", "", (item or "").strip())
    return cleaned.strip("；;。!！ \n")


def _dedupe_goal_items(items: List[str]) -> List[str]:
    deduped: List[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _clean_goal_item(item)
        normalized = re.sub(r"\s+", "", cleaned).lower()
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(cleaned)
    return deduped


def _goal_response_needs_rebuild(goal_response: str, goal_items: List[str]) -> bool:
    cleaned = (goal_response or "").strip()
    if not cleaned:
        return True
    if len(goal_items) <= 1:
        return len(cleaned) < 18
    numbered_hits = re.findall(r"(?m)^\s*\d+[.)、]\s+", cleaned)
    return len(numbered_hits) < len(goal_items)


def _emotion_answer_text(names: List[str], clues: List[Dict], language: str) -> str:
    if language != "zh-CN":
        return "The emotional trajectory shows unmet expectations on one side and defensive pressure on the other."
    left = names[0] if names else "一方"
    right = names[1] if len(names) > 1 else "另一方"
    clue_text = "；".join(clue.get("detail", "") for clue in clues[:2] if clue.get("detail"))
    return (
        f"{left} 更像是从解释现实压力逐步转向防御和撤退，{right} 更像是从期待、试探逐步转向失望和受伤。"
        f"{f'直接触发点主要落在：{clue_text}。' if clue_text else ''}"
    )


def _answer_goal_item(
    item: str,
    clues: List[Dict],
    suspect_rankings: List[Dict],
    timeline: List[Dict],
    verdict_summary: str,
    language: str,
    mode: str,
) -> str:
    clue_text = "；".join(clue.get("detail", "") for clue in clues[:2] if clue.get("detail"))
    lead_names = [entry.get("name", "") for entry in suspect_rankings[:3] if entry.get("name")]
    lead = lead_names[0] if lead_names else (L10N[language]["core_actor"] if language in L10N else "core actor")
    lead_role = suspect_rankings[0].get("role", "") if suspect_rankings else ""
    timeline_text = " -> ".join(step.get("event", "") for step in timeline[:3] if step.get("event"))
    lowered = item.lower()

    if language == "zh-CN":
        if any(keyword in item for keyword in ("情绪", "情感", "关系受伤", "误解")):
            return _emotion_answer_text(lead_names[:2], clues, language)
        if any(keyword in item for keyword in ("是否", "是不是", "能否", "有没有", "可否")):
            return f"当前更接近“是，但仍需补强证据细节”的判断。就现有线索看，{verdict_summary}"
        if any(keyword in item for keyword in ("为什么", "为何", "原因", "升级")):
            return f"核心原因不是单点偶发，而是 {clue_text or '多条关键线索'} 共同叠加并放大，最终形成了现在的结果。"
        if any(keyword in item for keyword in ("谁", "责任", "嫌疑", "排序", "关键对象")):
            return f"当前最应优先关注的是 {lead}{f'（{lead_role}）' if lead_role else ''}，其后是 {'、'.join(lead_names[1:3]) if len(lead_names) > 1 else '其他高相关对象'}。"
        if any(keyword in item for keyword in ("证据", "线索", "支持", "反证")):
            return f"当前最关键的支持线索包括：{clue_text or '现有高风险线索'}。反向看，仍需补强能直接闭合机制链的硬证据。"
        if any(keyword in item for keyword in ("时间线", "回溯", "重演", "分阶段")):
            return f"当前最优的回溯主线是：{timeline_text or '从前置异常进入关键事件，再到结果显化'}。"
        if mode == "public_opinion_attribution":
            return f"从归因上看，当前更接近“运营与回应失误共同放大舆情”的解释，{verdict_summary}"
        return f"围绕这个问题，当前更可信的回答是：{verdict_summary}"

    if any(keyword in lowered for keyword in ("why", "reason", "escalat")):
        return f"The strongest answer is that {clue_text or 'multiple signals combined into one mechanism'} rather than a single isolated cause."
    if any(keyword in lowered for keyword in ("whether", "is it", "can it", "could it")):
        return f"The stronger reading is yes in tendency, but the case still needs firmer evidence details. {verdict_summary}"
    if any(keyword in lowered for keyword in ("who", "responsib", "rank")):
        return f"The top priority is {lead}{f' ({lead_role})' if lead_role else ''}."
    if any(keyword in lowered for keyword in ("evidence", "clue", "support")):
        return f"The strongest supporting clues are: {clue_text or 'the currently extracted high-risk clues'}."
    if any(keyword in lowered for keyword in ("timeline", "replay", "reconstruct")):
        return f"The most likely timeline is: {timeline_text or 'setup -> trigger -> result'}."
    return verdict_summary


def _compose_goal_response(
    outcome: str,
    clues: List[Dict],
    suspect_rankings: List[Dict],
    timeline: List[Dict],
    verdict_summary: str,
    language: str,
    mode: Optional[str] = None,
    transient_cache: Optional[Dict] = None,
) -> str:
    transient_cache = transient_cache or _build_transient_cache(clues, [{"description": step.get("event", ""), "id": f"T{index + 1}"} for index, step in enumerate(timeline)], outcome)
    mode = mode or _classify_prompt_mode(outcome, outcome)
    goal_items = transient_cache.get("goal_items") or _extract_goal_items(outcome)
    alias_map = transient_cache.get("evidence_aliases", {})

    if len(goal_items) <= 1:
        base = _answer_goal_item(goal_items[0] if goal_items else outcome, clues, suspect_rankings, timeline, verdict_summary, language, mode)
        if language == "zh-CN":
            return _expand_evidence_aliases(f"针对“{outcome}”，当前更可信的回答是：{base}", alias_map)
        return _expand_evidence_aliases(f"For '{outcome}', the strongest current answer is: {base}", alias_map)

    lines = []
    for index, item in enumerate(goal_items, start=1):
        answer = _answer_goal_item(item, clues, suspect_rankings, timeline, verdict_summary, language, mode)
        if language == "zh-CN":
            lines.append(f"{index}. 问题：{item}\n回答：{answer}")
        else:
            lines.append(f"{index}. Question: {item}\nAnswer: {answer}")
    return _expand_evidence_aliases("\n".join(lines), alias_map)


def _stabilize_goal_response(
    structured: Dict,
    goal_response: str,
    suspect_rankings: List[Dict],
    timeline: List[Dict],
    language: str,
) -> str:
    transient_cache = structured.get("transient_cache", {}) or {}
    goal_items = transient_cache.get("goal_items") or _extract_goal_items(structured.get("expected_outcome", ""))
    expanded = _expand_evidence_aliases(goal_response or "", transient_cache.get("evidence_aliases", {}))
    if not _goal_response_needs_rebuild(expanded, goal_items):
        return expanded
    return _compose_goal_response(
        structured.get("expected_outcome", ""),
        structured.get("clues", []),
        suspect_rankings,
        timeline,
        structured.get("verdict_summary", ""),
        language,
        mode=_classify_prompt_mode(structured.get("expected_outcome", ""), structured.get("expected_outcome", "")),
        transient_cache=transient_cache,
    )


def _build_output_panels_localized(structured: Dict, final_result: CaseFinalResult, agent_steps: List[AgentStep]) -> List[OutputPanel]:
    expected_outcome = structured.get("expected_outcome", "")
    mode = _classify_prompt_mode("\n".join(_normalize_note_strings(structured.get("evidence_notes", []))), expected_outcome)
    ranking_lines = [
        f"{index + 1}. {item.name} | {item.role} | {item.motive}"
        for index, item in enumerate(final_result.suspect_rankings[:5])
    ]
    timeline_lines = [
        f"{step.order}. {step.time_hint} | {step.phase} | {step.event}"
        for step in final_result.reenactment_timeline[:8]
    ]
    evidence_refs = [ref for step in final_result.reenactment_timeline[:6] for ref in step.evidence_refs[:2]]
    agent_lines = [f"{step.agent_name} R{step.round_index}: {' | '.join(step.findings[:2])}" for step in agent_steps[:8]]
    panels = [
        OutputPanel(panel_id="goal_response", title="目标回答", panel_type="goal", summary="点对点回应当前分析目标。", body=final_result.goal_response or f"{final_result.case_explanation}\n\n{final_result.verdict_summary}", items=[expected_outcome] if expected_outcome else [], evidence_refs=evidence_refs[:6]),
        OutputPanel(panel_id="analysis", title="分析解释", panel_type="analysis", summary="主解释与综合判断。", body=final_result.case_explanation, items=[final_result.verdict_summary], evidence_refs=evidence_refs[:6]),
        OutputPanel(panel_id="ranking", title=_mode_ranking_label(mode), panel_type="ranking", summary="关键对象及其驱动链。", body=final_result.verdict_summary, items=ranking_lines, evidence_refs=evidence_refs[:6]),
        OutputPanel(panel_id="timeline", title="回溯时间线", panel_type="timeline", summary="按证据重建形成过程。", body="时间线可用于回看关键转折与证据覆盖。", items=timeline_lines, evidence_refs=evidence_refs[:8]),
        OutputPanel(panel_id="evidence", title="证据与不确定性", panel_type="evidence", summary="保留支持点与未决问题。", body="需要同时关注支持证据与仍待补强的环节。", items=[*final_result.evidence_notes[:5], *final_result.uncertainties[:4]], evidence_refs=evidence_refs[:8]),
        OutputPanel(panel_id="agents", title=_mode_specific_panel_title_clean(mode), panel_type="mode", summary="汇总多智能体协作后的模式化观察。", body=_mode_specific_panel_body_clean(mode, final_result), items=agent_lines[:8], evidence_refs=evidence_refs[:8]),
    ]
    return panels[:6]


def _mode_specific_panel_title_clean(mode: str) -> str:
    return {
        "case_reenactment": "机制与疑点",
        "relationship_emotion": "情绪与关系模式",
        "public_opinion_attribution": "舆情与归因模式",
    }.get(mode, "模式化观察")


def _mode_specific_panel_body_clean(mode: str, final_result: CaseFinalResult) -> str:
    if mode == "relationship_emotion":
        return "聚焦情绪波动、互动策略和关系温度变化，帮助解释局面是如何一步步形成的。"
    if mode == "public_opinion_attribution":
        return "聚焦议题扩散、关键节点和责任归因，帮助识别情绪升级与叙事转向。"
    if mode == "case_reenactment":
        return "聚焦作案机制、证据闭环和替代解释，帮助重建最可能的形成过程。"
    return final_result.verdict_summary or final_result.case_explanation


def _build_goal_response(
    outcome: str,
    clues: List[Dict],
    suspect_rankings: List[Dict],
    timeline: List[Dict],
    verdict_summary: str,
    language: str,
    mode: Optional[str] = None,
) -> str:
    loc = L10N[language]
    lead = suspect_rankings[0]["name"] if suspect_rankings else loc["core_actor"]
    lead_role = suspect_rankings[0]["role"] if suspect_rankings else loc["role_generic"]
    clue_text = "；".join(clue["detail"] for clue in clues[:2]) if language == "zh-CN" else "; ".join(clue["detail"] for clue in clues[:2])
    first_event = timeline[0]["event"] if timeline else ""
    mode = mode or _classify_prompt_mode(f"{outcome}\n{clue_text}\n{first_event}", outcome)
    asks_why = any(token in outcome for token in QUESTION_TOKENS_ZH) if language == "zh-CN" else any(token in outcome.lower() for token in QUESTION_TOKENS_EN)

    if language == "zh-CN":
        if mode == "relationship_emotion":
            pair = " 和 ".join(item["name"] for item in suspect_rankings[:2]) if len(suspect_rankings) >= 2 else lead
            return (
                f"针对“{outcome}”，当前更可信的回答是：问题并不是单次争执本身，而是由未被说清的期待、"
                f"{clue_text or '持续累积的情绪压力'}和沟通失配逐步放大。"
                f"应优先复盘 {pair} 的情绪变化和误读链，而不是只盯住某一句话。"
            )
        if mode == "public_opinion_attribution":
            return (
                f"针对“{outcome}”，当前更可信的回答是：舆情升级不是单点爆发，而是由"
                f"{clue_text or '多个异常线索'}叠加后，放大成对外叙事失控。"
                f"现阶段应优先要求 {lead}（{lead_role}）对关键触发点、响应迟滞和解释口径负责。"
            )
        if asks_why:
            return (
                f"针对“{outcome}”，当前更可信的回答是：事件之所以发展成现在这样，核心不是单一偶发因素，"
                f"而是 {clue_text or '多条关键线索'} 共同指向同一条形成链。"
                f"现阶段最应优先核查的是 {lead}（{lead_role}）与关键节点之间的关联，{verdict_summary}"
            )
        return (
            f"针对“{outcome}”，当前可直接给出的回答是：应先围绕 {lead}（{lead_role}）和"
            f"{clue_text or '当前最高风险线索'} 重建形成过程。"
            f"{first_event and f'起点大致可以追溯到“{first_event}”。'} {verdict_summary}"
        ).strip()
    if mode == "relationship_emotion":
        return (
            f"For '{outcome}', the stronger answer is that this was not caused by one quarrel alone, "
            f"but by unmet expectations, emotional load, and a repeated communication mismatch. "
            f"{lead} is the highest-priority conflict driver to review first."
        )
    if mode == "public_opinion_attribution":
        return (
            f"For '{outcome}', the stronger answer is that the escalation came from multiple trigger signals combining into a narrative failure. "
            f"{lead} ({lead_role}) is the top priority responsibility center to explain the trigger, response delay, and message gap."
        )
    return (
        f"For '{outcome}', the strongest current answer is that the outcome grew from a shared chain rather than a single isolated cause. "
        f"{lead} ({lead_role}) should be tested first against the highest-priority clues, and {verdict_summary}"
    )


def _node_id(prefix: str, label: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", label).strip("-").lower()
    return f"{prefix}-{safe[:28] or 'node'}"

