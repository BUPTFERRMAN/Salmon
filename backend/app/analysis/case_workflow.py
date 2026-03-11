import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from app.analysis.llm import OpenAICompatibleClient
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
        "disposition": {"zh-CN": "结构化、关联优先", "en": "Structured, link-first"},
        "accent": "#254d59",
    },
    {
        "agent_name": "Suspicion Agent",
        "purpose_key": "agent_suspicion",
        "codename": "Rank Signal",
        "role": {"zh-CN": "嫌疑排序", "en": "Suspicion Ranking"},
        "disposition": {"zh-CN": "比较驱动、筛选优先", "en": "Comparative, ranking-first"},
        "accent": "#8b5e34",
    },
    {
        "agent_name": "Reconstruction Agent",
        "purpose_key": "agent_reconstruction",
        "codename": "Time Thread",
        "role": {"zh-CN": "因果拼接", "en": "Causal Reconstruction"},
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
AGENT_ROUND_PLANS = [
    ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent"],
    ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent", "Judge Agent"],
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


def run_case_workflow(text: str, document: UploadedDocument, expected_outcome: Optional[str]) -> CaseWorkflowResponse:
    parse_stage = parse_case_material(text, document, expected_outcome)
    reason_stage = reason_case_material(
        text=text,
        document=document,
        expected_outcome=expected_outcome,
        structured_case=parse_stage.structured_case,
        detected_language=parse_stage.detected_language,
    )
    return CaseWorkflowResponse(
        document=document,
        expected_outcome=reason_stage.expected_outcome,
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


def parse_case_material(text: str, document: UploadedDocument, expected_outcome: Optional[str]) -> CaseParseResponse:
    language = detect_language(text, expected_outcome)
    structured = _extract_with_rules(text, document, _outcome(expected_outcome, language), language)
    graph_nodes, graph_edges = _build_graph(structured, document.source_name, language)
    return CaseParseResponse(
        document=document,
        expected_outcome=_outcome(expected_outcome, language),
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
) -> CaseReasonResponse:
    language = detected_language or detect_language(text, expected_outcome)
    outcome = _outcome(expected_outcome, language)
    structured = structured_case or _build_structured_case(text, document, outcome, language)
    agent_steps: List[AgentStep] = []
    agent_dialogue: List[AgentExchange] = []
    statuses: List[str] = []
    for round_index, round_agents in enumerate(AGENT_ROUND_PLANS, start=1):
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


def _build_structured_case(text: str, document: UploadedDocument, outcome: str, language: str) -> Dict:
    llm_client = OpenAICompatibleClient()
    if llm_client.enabled:
        structured = _extract_with_llm(llm_client, text, outcome, document, language)
        if structured:
            return structured
    return _extract_with_rules(text, document, outcome, language)


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
    ]
    if any(key not in payload for key in required):
        return None
    return _normalize_llm_payload(payload)


def _build_case_llm_prompts(text: str, outcome: str, document: UploadedDocument, language: str) -> Tuple[str, str]:
    sections = _split_case_sections(text)
    target_language = "Simplified Chinese" if language == "zh-CN" else "English"
    background_block = "\n".join(f"- {item}" for item in sections["background"]) or "- None explicitly provided."
    clue_block = "\n".join(f"- {item}" for item in sections["clues"]) or "- None explicitly provided."
    extra_block = "\n".join(f"- {item}" for item in sections["extra"]) or "- No extra sections."
    mode = _classify_prompt_mode(text, outcome)
    if mode == "case_reenactment":
        extra_constraints = """
- This request is a case reenactment task. Preserve suspect ranking, timeline reconstruction, and evidence coverage.
- Prefer one mechanism that explains multiple clues at once.
- If the material includes space, access, device, time-gap, or other structural anomalies, test whether they combine into one mechanism chain.
- Suspect ranking must clearly state which material supports motive, means, opportunity, and clue coverage.
""".strip()
    else:
        extra_constraints = """
- This request is a general backtracing task rather than a pure criminal case.
- Focus on causal structure, competing explanations, and hidden turning points.
- Reuse the same schema without forcing crime-specific assumptions.
""".strip()

    system_prompt = f"""
You are Salmon's reconstruction structuring agent.
Return one valid JSON object and nothing else.
All natural-language values in the JSON must be written in {target_language}.
Keep the JSON keys in English.
Treat background as context, clues as the main evidence layer, and never convert inference into fact.
Build a reusable structured graph that can support downstream multi-agent reasoning.
When ranking candidates, use motive, means, opportunity, and clue coverage when relevant.

Output schema:
background_summary: string
actors: [{{name, role, relation, suspicion_score, motive, means, opportunity, evidence_refs}}]
events: [{{id, time_hint, description, actors, evidence_refs, inference_level}}]
clues: [{{id, label, detail, actors, event_ids, risk_level, evidence_refs}}]
suspect_rankings: [{{name, role, suspicion_score, motive, means, opportunity, supporting_evidence, concerns}}]
reenactment_timeline: [{{order, phase, time_hint, event, evidence_refs, inference_level}}]
evidence_notes: [string]
verdict_summary: string
final_explanation: string
uncertainties: [string]
""".strip()

    user_prompt = f"""
Case goal:
{outcome}

Document info:
- source_name: {document.source_name}
- source_type: {document.source_type}
- character_count: {document.character_count}

Background facts:
{background_block}

Explicit clues:
{clue_block}

Other sections:
{extra_block}

Raw material:
{text[:18000]}

Extra constraints:
{extra_constraints}
""".strip()
    return system_prompt, user_prompt


def _split_case_sections(text: str) -> Dict[str, List[str]]:
    sections = {"background": [], "clues": [], "extra": []}
    current = "extra"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lower().replace(" ", "")
        if "background" in normalized or "\u80cc\u666f" in normalized:
            current = "background"
            continue
        if "clue" in normalized or "evidence" in normalized or "\u7ebf\u7d22" in normalized:
            current = "clues"
            continue
        if "result" in normalized or "answer" in normalized or "\u7ed3\u679c" in normalized or "\u7b54\u6848" in normalized:
            current = "extra"
            continue
        sections[current].append(line.lstrip("-* ").strip())
    return sections


def _classify_prompt_mode(text: str, outcome: str) -> str:
    sample = f"{outcome}\n{text[:4000]}".lower()
    case_keywords = [
        "案情",
        "案件",
        "嫌疑",
        "凶手",
        "证据",
        "线索",
        "案发",
        "案情重演",
        "suspect",
        "murder",
        "crime",
        "evidence",
        "reenact",
    ]
    hits = sum(1 for keyword in case_keywords if keyword in sample)
    return "case_reenactment" if hits >= 2 else "general_backtrace"


def _normalize_llm_payload(payload: Dict) -> Dict:
    def ensure_list(value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]

    def ensure_int(value, fallback=0):
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

    def ensure_float(value, fallback=0.0):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return fallback
        return fallback

    for actor in payload.get("actors", []):
        actor["evidence_refs"] = ensure_list(actor.get("evidence_refs"))
        actor["suspicion_score"] = ensure_float(actor.get("suspicion_score"), 0.0)
    for event in payload.get("events", []):
        event["actors"] = ensure_list(event.get("actors"))
        event["evidence_refs"] = ensure_list(event.get("evidence_refs"))
    for clue in payload.get("clues", []):
        clue["actors"] = ensure_list(clue.get("actors"))
        clue["event_ids"] = ensure_list(clue.get("event_ids"))
        clue["evidence_refs"] = ensure_list(clue.get("evidence_refs"))
        clue["risk_level"] = ensure_int(clue.get("risk_level"), 5)
    for suspect in payload.get("suspect_rankings", []):
        suspect["supporting_evidence"] = ensure_list(suspect.get("supporting_evidence"))
        suspect["concerns"] = ensure_list(suspect.get("concerns"))
        suspect["suspicion_score"] = ensure_int(suspect.get("suspicion_score"), 50)
    for step in payload.get("reenactment_timeline", []):
        step["evidence_refs"] = ensure_list(step.get("evidence_refs"))
        step["order"] = ensure_int(step.get("order"), 0)
    payload["evidence_notes"] = ensure_list(payload.get("evidence_notes"))
    payload["uncertainties"] = ensure_list(payload.get("uncertainties"))
    return payload


def _extract_with_rules(text: str, document: UploadedDocument, outcome: str, language: str) -> Dict:
    loc = L10N[language]
    lines = [line.strip(" \t-*") for line in text.splitlines() if line.strip()]
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

    actors = _build_actor_cards(actor_counter, actor_evidence_map, clues, language, document.source_name)
    suspect_rankings = _build_suspect_rankings(actors, events, language)
    timeline = _build_reenactment_timeline(events)

    return {
        "background_summary": loc["summary"].format(source=document.source_name, outcome=outcome),
        "actors": actors,
        "events": events,
        "clues": clues,
        "suspect_rankings": suspect_rankings,
        "reenactment_timeline": timeline,
        "evidence_notes": _build_evidence_notes(clues, language),
        "verdict_summary": _build_verdict(clues, suspect_rankings, language),
        "final_explanation": _build_explanation(outcome, clues, suspect_rankings, language),
        "uncertainties": [loc["uncertainty_1"], loc["uncertainty_2"]],
    }


def _build_actor_cards(
    actor_counter: Counter,
    actor_evidence_map: Dict[str, List[str]],
    clues: List[Dict],
    language: str,
    source_name: str,
) -> List[Dict]:
    loc = L10N[language]
    actor_names = [name for name, _ in actor_counter.most_common(8)] or [loc["core_actor"]]
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


def _build_suspect_rankings(actors: List[Dict], events: List[Dict], language: str) -> List[Dict]:
    loc = L10N[language]
    rankings = []
    for actor in sorted(actors, key=lambda item: item["suspicion_score"], reverse=True)[:5]:
        supporting = [event["description"] for event in events if event["id"] in actor["evidence_refs"]][:3]
        rankings.append(
            {
                "name": actor["name"],
                "role": actor["role"],
                "suspicion_score": int(actor["suspicion_score"]),
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

    for clue in structured.get("clues", [])[:10]:
        required_event_ids.update(clue.get("event_ids", []))

    for actor in structured.get("actors", [])[:8]:
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
        event_ids.add(event["id"])
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
                edges.append(
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
                related_nodes[event_id].add(clue["id"])
                related_nodes[clue["id"]].add(event_id)
                edges.append(
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
                related_nodes[actor_ids[actor_name]].add(clue["id"])
                related_nodes[clue["id"]].add(actor_ids[actor_name])
                edges.append(
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
    return CaseFinalResult(
        case_explanation=structured.get("final_explanation", ""),
        verdict_summary=structured.get("verdict_summary", ""),
        suspect_rankings=[
            SuspectRank(
                name=item["name"],
                role=item["role"],
                suspicion_score=int(item["suspicion_score"]),
                motive=item["motive"],
                means=item["means"],
                opportunity=item["opportunity"],
                supporting_evidence=item.get("supporting_evidence", []),
                concerns=item.get("concerns", []),
            )
            for item in structured.get("suspect_rankings", [])[:5]
        ],
        reenactment_timeline=[
            ReconstructionStep(
                order=int(item["order"]),
                phase=item["phase"],
                time_hint=item["time_hint"],
                event=item["event"],
                evidence_refs=item.get("evidence_refs", []),
                inference_level=item.get("inference_level", "mixed"),
            )
            for item in structured.get("reenactment_timeline", [])[:10]
        ],
        evidence_notes=[*structured.get("evidence_notes", []), *[f"{step.agent_name}: {' | '.join(step.findings[:2])}" for step in agent_steps[:3]]][:8],
        uncertainties=structured.get("uncertainties", []),
    )


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
    payload = llm_client.complete_json(system_prompt, user_prompt, timeout=45)
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
    system_prompt = f"""
You are one specialist analyst inside Salmon.
Return one valid JSON object and nothing else.
All natural-language values must be written in {target_language}.
Keep the JSON keys in English.
Stay evidence-constrained and reusable across future cases.
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
- round_index: {round_index} / {AGENT_COLLAB_ROUNDS}

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
    payload = llm_client.complete_json(system_prompt, user_prompt, timeout=45)
    if not payload:
        return None
    required = ["case_explanation", "verdict_summary", "suspect_rankings", "reenactment_timeline", "evidence_notes", "uncertainties"]
    if any(key not in payload for key in required):
        return None
    normalized = _normalize_llm_payload(
        {
            "actors": structured_case.get("actors", []),
            "events": structured_case.get("events", []),
            "clues": structured_case.get("clues", []),
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
    agent_block = "\n".join(f"- {step.agent_name}: {' | '.join(step.findings[:4])}" for step in agent_steps) or "- None."
    ranking_block = "\n".join(
        f"- {item.get('name')}: score={item.get('suspicion_score')} role={item.get('role')}"
        for item in structured_case.get("suspect_rankings", [])[:5]
    ) or "- None."
    timeline_block = "\n".join(
        f"- {item.get('order')}. {item.get('time_hint')} -> {item.get('event')} / refs={', '.join(item.get('evidence_refs', []))}"
        for item in structured_case.get("reenactment_timeline", [])[:10]
    ) or "- None."
    system_prompt = f"""
You are Salmon's final synthesis agent.
Return one valid JSON object and nothing else.
All natural-language values must be written in {target_language}.
Keep the JSON keys in English.
Stay evidence-constrained and preserve uncertainty.
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

Output schema reminder:
- case_explanation
- verdict_summary
- suspect_rankings
- reenactment_timeline
- evidence_notes
- uncertainties
""".strip()
    return system_prompt, user_prompt


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


def _extract_actors(detail: str) -> List[str]:
    actors = set(re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+){0,2}\b", detail))
    for token in re.findall(r"[\u4e00-\u9fff]{2,4}", detail):
        if any(keyword in token for keyword in ROLE_KEYWORDS):
            actors.add(token)
    return sorted(name for name in actors if name.lower() not in {"the", "and", "but"})[:4]


def _risk_score(detail: str) -> int:
    lowered = detail.lower()
    score = 1
    for word, weight in RISK_WORDS.items():
        if word in lowered or word in detail:
            score += weight
    return min(score, 10)


def _clue_label(detail: str, language: str) -> str:
    lowered = detail.lower()
    if any(word in detail or word in lowered for word in ("监控", "盲区", "录像", "camera", "surveillance", "footage")):
        return "\u76d1\u63a7\u5f02\u5e38" if language == "zh-CN" else "Surveillance anomaly"
    if any(word in detail or word in lowered for word in ("缺失", "封存", "篡改", "missing", "tamper", "record")):
        return "\u8bb0\u5f55\u5f02\u5e38" if language == "zh-CN" else "Record anomaly"
    if any(word in detail or word in lowered for word in ("装置", "通道", "设备", "机制", "device", "access", "mechanism")):
        return "\u673a\u5236\u7ebf\u7d22" if language == "zh-CN" else "Mechanism clue"
    if any(word in detail or word in lowered for word in ("保险", "财产", "债务", "insurance", "property", "debt")):
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


def _node_id(prefix: str, label: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", label).strip("-").lower()
    return f"{prefix}-{safe[:28] or 'node'}"
