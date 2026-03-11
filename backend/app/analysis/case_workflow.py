import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from app.analysis.llm import OpenAICompatibleClient
from app.schemas import (
    AgentExchange,
    AgentProfile,
    AgentStep,
    CaseFinalResult,
    CaseParseResponse,
    CaseReasonResponse,
    CaseWorkflowResponse,
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
        "role_generic": "\u5173\u952e\u76f8\u5173\u65b9",
        "relation_generic": "{name} \u4f4d\u4e8e\u6848\u4ef6\u5173\u952e\u5173\u7cfb\u94fe\u4e2d\uff0c\u89d2\u8272\u5224\u65ad\u4e3a {role}\u3002",
        "motive_generic": "{name} \u53ef\u80fd\u53d7\u5230\u5229\u76ca\u3001\u81ea\u4fdd\u3001\u63a7\u5236\u53d9\u4e8b\u6216\u5173\u7cfb\u51b2\u7a81\u7684\u9a71\u52a8\u3002",
        "means_generic": "{role} \u53ef\u80fd\u5177\u5907\u63a5\u8fd1\u73b0\u573a\u3001\u88c5\u7f6e\u3001\u4fe1\u606f\u6216\u5173\u952e\u901a\u9053\u7684\u80fd\u529b\u3002",
        "opportunity_generic": "\u6750\u6599\u4e2d\u81f3\u5c11\u6709 {count} \u5904\u8282\u70b9\u4e0e\u5176\u76f4\u63a5\u76f8\u5173\uff0c\u8bf4\u660e\u5176\u63a5\u8fd1\u5173\u952e\u65f6\u70b9\u3002",
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
        "role_generic": "Key stakeholder",
        "relation_generic": "{name} appears inside the central relationship chain as {role}.",
        "motive_generic": "{name} may be driven by gain, self-protection, narrative control, or relationship conflict.",
        "means_generic": "The {role} role may provide access to the scene, devices, information, or key pathways.",
        "opportunity_generic": "The material links this actor to at least {count} relevant points near critical moments.",
    },
}

AGENTS = [
    ("Evidence Agent", "agent_evidence"),
    ("Relationship Agent", "agent_relationship"),
    ("Suspicion Agent", "agent_suspicion"),
    ("Reconstruction Agent", "agent_reconstruction"),
    ("Judge Agent", "agent_judge"),
]

ZH_KEYWORDS = {
    "camera": ["\u76d1\u63a7", "\u76f2\u533a"],
    "record": ["\u7f3a\u5931", "\u5c01\u5b58", "\u7be1\u6539"],
    "mechanism": ["\u5bc6\u5ba4", "\u901a\u98ce\u53e3", "\u5047\u94c3\u7ef3", "\u53e3\u54e8", "\u6591\u70b9\u5e26\u5b50"],
}

ROLE_KEYWORDS = ["\u533b\u751f", "\u6559\u6388", "\u8b66\u5bdf", "\u7ee7\u7236", "\u6bcd\u4eb2", "\u59b9\u59b9", "\u59d0\u59d0", "\u4fdd\u5b89", "\u7ecf\u7406", "\u4e3b\u4efb", "\u7ef4\u4fee", "\u62a4\u58eb", "\u53f8\u673a", "\u8d22\u52a1"]

RISK_WORDS = {
    "missing": 3,
    "cover-up": 4,
    "tamper": 4,
    "locked room": 4,
    "ventilator": 3,
    "bell rope": 3,
    "whistle": 3,
    "insurance": 2,
    "\u7edf\u4e00\u53e3\u5f84": 4,
    "\u5c01\u5b58": 3,
    "\u5f02\u5e38": 2,
    "\u7f3a\u5931": 3,
    "\u7be1\u6539": 4,
    "\u76d1\u63a7\u76f2\u533a": 4,
    "\u5bc6\u5ba4": 4,
    "\u901a\u98ce\u53e3": 3,
    "\u5047\u94c3\u7ef3": 3,
    "\u53e3\u54e8": 3,
    "\u9057\u8a00": 2,
    "\u4fdd\u9669": 2,
    "\u63d0\u524d": 2,
}


def run_case_workflow(text: str, document: UploadedDocument, expected_outcome: Optional[str]) -> CaseWorkflowResponse:
    parse_stage = parse_case_material(text, document, expected_outcome)
    reason_stage = reason_case_material(text, document, expected_outcome)
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
    graph_nodes, graph_edges = _build_graph(structured)
    return CaseParseResponse(
        document=document,
        expected_outcome=_outcome(expected_outcome, language),
        detected_language=language,
        extracted_text=text,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        evidence_items=_build_evidence_items(structured, document.source_name),
        pipeline=_pipeline("pending"),
    )


def reason_case_material(text: str, document: UploadedDocument, expected_outcome: Optional[str]) -> CaseReasonResponse:
    language = detect_language(text, expected_outcome)
    outcome = _outcome(expected_outcome, language)
    llm_client = OpenAICompatibleClient()
    structured = None
    model_status = "rules_only"

    if llm_client.enabled:
        structured = _extract_with_llm(llm_client, text, outcome, document, language)
        if structured:
            model_status = "model_plus_rules"

    if not structured:
        structured = _extract_with_rules(text, document, outcome, language)

    return CaseReasonResponse(
        expected_outcome=outcome,
        detected_language=language,
        model_status=model_status,
        pipeline=_pipeline("completed" if model_status == "model_plus_rules" else "fallback"),
        agent_profiles=_build_agent_profiles(structured, language),
        agents=_build_agent_steps(structured, language),
        agent_dialogue=_build_agent_dialogue(structured, language),
        final_result=_build_final_result(structured),
    )


def detect_language(text: str, outcome: Optional[str] = None) -> str:
    sample = f"{outcome or ''}\n{text[:2000]}"
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", sample))
    latin_words = len(re.findall(r"[A-Za-z]{2,}", sample))
    return "zh-CN" if chinese_chars >= max(12, latin_words) else "en"


def _outcome(expected_outcome: Optional[str], language: str) -> str:
    return (expected_outcome or L10N[language]["default_outcome"]).strip()


def _pipeline(reason_status: str) -> List[PipelineStep]:
    return [
        PipelineStep(step_id="parse", title="parse", detail="document parsed", status="completed"),
        PipelineStep(step_id="graph", title="graph", detail="graph ready", status="completed"),
        PipelineStep(step_id="reason", title="reason", detail="agents reasoning", status=reason_status),
        PipelineStep(step_id="result", title="result", detail="final synthesis", status="completed" if reason_status != "pending" else "pending"),
    ]


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

    system_prompt = f"""
You are BackTrace's case-reenactment structuring agent.
Return one valid JSON object and nothing else.
All natural-language values in the JSON must be written in {target_language}.
Keep the JSON keys in English.
Treat background as context, clues as the main evidence layer, and never convert inference into fact.
Prefer one mechanism that explains multiple clues at once.
If the case resembles a locked-room or impossible-crime pattern, explain the mechanism that closes the gap.
Suspect ranking must be based on motive, means, opportunity, and clue coverage.

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
- If multiple clues can be explained by one shared mechanism, make that mechanism explicit.
- If there is a dying message, strange sound, fake device, fixed furniture, vent, passage, or other structural anomaly, test whether they form one integrated device chain.
- Suspect ranking must clearly state which material supports motive, means, opportunity, and clue coverage.
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
                    "evidence_refs": [event_id],
                }
            )

    actors = _build_actor_cards(actor_counter, actor_evidence_map, clues, language)
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


def _build_actor_cards(actor_counter: Counter, actor_evidence_map: Dict[str, List[str]], clues: List[Dict], language: str) -> List[Dict]:
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


def _build_graph(structured: Dict) -> Tuple[List[GraphNode], List[GraphEdge]]:
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    actor_ids: Dict[str, str] = {}
    required_event_ids = set()

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
                attributes={"time_hint": event["time_hint"], "inference_level": event["inference_level"]},
            )
        )
        for actor_name in event.get("actors", []):
            if actor_name in actor_ids:
                edges.append(
                    GraphEdge(
                        source=actor_ids[actor_name],
                        target=event["id"],
                        relation="involved_in",
                        evidence=event["description"],
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
                attributes={"risk_level": str(clue["risk_level"]), "detail": clue["detail"]},
            )
        )
        for event_id in clue.get("event_ids", []):
            if event_id in event_ids:
                edges.append(GraphEdge(source=event_id, target=clue["id"], relation="produces_clue", evidence=clue["detail"], strength=0.87))
        for actor_name in clue.get("actors", []):
            if actor_name in actor_ids:
                edges.append(GraphEdge(source=actor_ids[actor_name], target=clue["id"], relation="linked_to", evidence=clue["detail"], strength=0.74))

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
    loc = L10N[language]
    bundles = [
        structured.get("evidence_notes", [])[:4],
        [f"{actor['name']}: {actor['relation']}" for actor in structured.get("actors", [])[:4]],
        [f"{rank['name']} #{index + 1} / {rank['suspicion_score']}" for index, rank in enumerate(structured.get("suspect_rankings", [])[:4])],
        [f"{step['time_hint']} - {step['event']}" for step in structured.get("reenactment_timeline", [])[:4]],
        [structured.get("verdict_summary", ""), *structured.get("uncertainties", [])[:2]],
    ]
    return [
        AgentStep(agent_name=name, purpose=loc[key], status="completed", findings=bundles[index], confidence=0.72 + index * 0.04)
        for index, (name, key) in enumerate(AGENTS)
    ]


def _build_agent_profiles(structured: Dict, language: str) -> List[AgentProfile]:
    loc = L10N[language]
    top_clue = structured.get("clues", [{}])[0]
    top_suspect = structured.get("suspect_rankings", [{}])[0]
    top_event = structured.get("reenactment_timeline", [{}])[0]
    presets = [
        ("Evidence Agent", "Trace Lens", "证据审计" if language == "zh-CN" else "Evidence Audit", "冷静、保守" if language == "zh-CN" else "Calm, conservative", top_clue.get("detail", loc["few_clues"]), [*structured.get("evidence_notes", [])[:2]], "#b44d28"),
        ("Relationship Agent", "Link Weaver", "关系建模" if language == "zh-CN" else "Relationship Modeling", "结构化、关联优先" if language == "zh-CN" else "Structured, link-first", top_suspect.get("name", loc["core_actor"]), [actor.get("relation", "") for actor in structured.get("actors", [])[:2]], "#254d59"),
        ("Suspicion Agent", "Rank Signal", "嫌疑排序" if language == "zh-CN" else "Suspicion Ranking", "偏重比较与筛选" if language == "zh-CN" else "Comparative and ranking-oriented", top_suspect.get("motive", top_suspect.get("name", loc["core_actor"])), [item.get("name", "") for item in structured.get("suspect_rankings", [])[:3]], "#8b5e34"),
        ("Reconstruction Agent", "Time Thread", "因果拼接" if language == "zh-CN" else "Causal Reconstruction", "时序驱动" if language == "zh-CN" else "Timeline-driven", top_event.get("event", loc["few_clues"]), [item.get("event", "") for item in structured.get("reenactment_timeline", [])[:2]], "#3e6b6f"),
        ("Judge Agent", "Final Frame", "综合裁决" if language == "zh-CN" else "Final Synthesis", "平衡、谨慎" if language == "zh-CN" else "Balanced, cautious", structured.get("verdict_summary", ""), structured.get("uncertainties", [])[:2], "#c59c3d"),
    ]
    return [
        AgentProfile(
            agent_name=name,
            codename=codename,
            role=role,
            disposition=disposition,
            current_focus=current_focus,
            persistent_state=("已收束到当前案件上下文" if language == "zh-CN" else "Bound to the current case context"),
            memory_notes=[note for note in memory_notes if note],
            accent=accent,
        )
        for name, codename, role, disposition, current_focus, memory_notes, accent in presets
    ]


def _build_agent_dialogue(structured: Dict, language: str) -> List[AgentExchange]:
    loc = L10N[language]
    top_clue = structured.get("clues", [{}])[0]
    top_suspect = structured.get("suspect_rankings", [{}])[0]
    top_timeline = structured.get("reenactment_timeline", [{}])[0]
    lines = [
        ("Evidence Agent", "Relationship Agent", loc["dialogue_1"].format(label=top_clue.get("label", loc["critical_anomaly"]))),
        ("Relationship Agent", "Suspicion Agent", loc["dialogue_2"].format(suspect=top_suspect.get("name", loc["core_actor"]))),
        ("Suspicion Agent", "Reconstruction Agent", loc["dialogue_3"].format(suspect=top_suspect.get("name", loc["core_actor"]))),
        ("Reconstruction Agent", "Judge Agent", loc["dialogue_4"].format(event=top_timeline.get("event", "early anomaly"))),
        ("Judge Agent", "All Agents", structured.get("verdict_summary", "")),
    ]
    return [
        AgentExchange(step_id=f"exchange_{index + 1:02d}", speaker=speaker, audience=audience, message=message, stage="completed")
        for index, (speaker, audience, message) in enumerate(lines)
    ]


def _build_final_result(structured: Dict) -> CaseFinalResult:
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
        evidence_notes=structured.get("evidence_notes", []),
        uncertainties=structured.get("uncertainties", []),
    )


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
    if any(word in detail for word in ZH_KEYWORDS["camera"]) or "camera" in lowered:
        return "\u76d1\u63a7\u5f02\u5e38" if language == "zh-CN" else "Surveillance anomaly"
    if any(word in detail for word in ZH_KEYWORDS["record"]) or "missing" in lowered:
        return "\u8bb0\u5f55\u5f02\u5e38" if language == "zh-CN" else "Record anomaly"
    if any(word in detail for word in ZH_KEYWORDS["mechanism"]) or any(
        word in lowered for word in ("locked room", "ventilator", "bell rope", "whistle", "speckled band")
    ):
        return "\u4f5c\u6848\u673a\u5236\u7ebf\u7d22" if language == "zh-CN" else "Mechanism clue"
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
