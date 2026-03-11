from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DemoCard(BaseModel):
    demo_id: str
    title: str
    mode: str
    description: str
    seed_text: str
    expected_outcome: str


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    expected_outcome: Optional[str] = None
    use_llm: bool = False


class MessageInsight(BaseModel):
    message_id: str
    speaker: str
    content: str
    timestamp: Optional[str] = None
    surface_meaning: str
    emotion: str
    intents: List[str]
    strategy: str
    relationship_impact: int
    evidence_level: str


class TurningPoint(BaseModel):
    event_id: str
    title: str
    reason: str
    severity: str


class TimelineEvent(BaseModel):
    event_id: str
    label: str
    detail: str
    time_hint: str
    actors: List[str]
    event_type: str
    pressure_score: int


class ActorCard(BaseModel):
    name: str
    role_guess: str
    state: str
    motives: List[str]


class Hypothesis(BaseModel):
    title: str
    summary: str
    path: List[str]
    supporting_evidence: List[str]
    counter_evidence: List[str]
    confidence: float


class AnalysisOverview(BaseModel):
    title: str
    summary: str
    key_judgement: str
    uncertainty: str


class ConversationAnalysisResponse(BaseModel):
    mode: str = "conversation"
    overview: AnalysisOverview
    messages: List[MessageInsight]
    turning_points: List[TurningPoint]
    main_hypothesis: Hypothesis
    alternative_hypothesis: Hypothesis
    missing_evidence: List[str]
    relationship_temperature: int
    conflict_risk: int


class CaseAnalysisResponse(BaseModel):
    mode: str = "case"
    overview: AnalysisOverview
    actors: List[ActorCard]
    timeline: List[TimelineEvent]
    hidden_factors: List[str]
    turning_points: List[TurningPoint]
    main_hypothesis: Hypothesis
    alternative_hypothesis: Hypothesis
    missing_evidence: List[str]
    case_temperature: int


class ModelConfig(BaseModel):
    provider_name: str = "OpenAI Compatible"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    enabled: bool = False
    request_timeout_seconds: Optional[float] = None


class ModelConfigView(BaseModel):
    provider_name: str = "OpenAI Compatible"
    base_url: str = ""
    model: str = ""
    enabled: bool = False
    has_api_key: bool = False
    api_key_hint: str = ""
    request_timeout_seconds: Optional[float] = None


class UploadedDocument(BaseModel):
    source_name: str
    source_type: str
    character_count: int
    page_count: Optional[int] = None
    extracted_preview: str


class EvidenceDetail(BaseModel):
    ref_id: str
    excerpt: str
    source: str
    note: str = ""


class GraphNode(BaseModel):
    node_id: str
    label: str
    node_type: str
    summary: str
    suspicion_score: float = 0.0
    evidence_refs: List[str] = Field(default_factory=list)
    evidence_details: List[EvidenceDetail] = Field(default_factory=list)
    related_node_ids: List[str] = Field(default_factory=list)
    attributes: Dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    evidence: str
    evidence_refs: List[str] = Field(default_factory=list)
    evidence_details: List[EvidenceDetail] = Field(default_factory=list)
    strength: float = 0.5


class EvidenceItem(BaseModel):
    evidence_id: str
    label: str
    detail: str
    source: str
    evidence_level: str
    risk_score: int


class AgentStep(BaseModel):
    agent_name: str
    purpose: str
    status: str
    findings: List[str]
    confidence: float
    round_index: int = 1
    focus_refs: List[str] = Field(default_factory=list)


class AgentProfile(BaseModel):
    agent_name: str
    codename: str
    role: str
    disposition: str
    current_focus: str
    persistent_state: str
    memory_notes: List[str]
    accent: str


class AgentExchange(BaseModel):
    step_id: str
    speaker: str
    audience: str
    message: str
    stage: str
    round_index: int = 1
    evidence_refs: List[str] = Field(default_factory=list)


class PipelineStep(BaseModel):
    step_id: str
    title: str
    detail: str
    status: str


class SuspectRank(BaseModel):
    name: str
    role: str
    suspicion_score: int
    motive: str
    means: str
    opportunity: str
    supporting_evidence: List[str]
    concerns: List[str]


class ReconstructionStep(BaseModel):
    order: int
    phase: str
    time_hint: str
    event: str
    evidence_refs: List[str]
    inference_level: str


class OutputPanel(BaseModel):
    panel_id: str
    title: str
    panel_type: str
    summary: str
    body: str
    items: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class CaseFinalResult(BaseModel):
    case_explanation: str
    verdict_summary: str
    suspect_rankings: List[SuspectRank]
    reenactment_timeline: List[ReconstructionStep]
    evidence_notes: List[str]
    uncertainties: List[str]
    goal_response: str = ""
    output_panels: List[OutputPanel] = Field(default_factory=list)


class CaseParseResponse(BaseModel):
    mode: str = "case_parse"
    document: UploadedDocument
    expected_outcome: str
    collaboration_rounds: int = 2
    detected_language: str
    extracted_text: str
    structured_case: Dict[str, Any] = Field(default_factory=dict)
    graph_nodes: List[GraphNode]
    graph_edges: List[GraphEdge]
    evidence_items: List[EvidenceItem]
    agent_profiles: List[AgentProfile] = Field(default_factory=list)
    pipeline: List[PipelineStep]


class CaseReasonRequest(BaseModel):
    text: str = Field(..., min_length=1)
    document: UploadedDocument
    expected_outcome: Optional[str] = None
    structured_case: Dict[str, Any] = Field(default_factory=dict)


class AgentTurnRequest(BaseModel):
    structured_case: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str
    detected_language: str
    document: UploadedDocument
    agent_name: str
    round_index: int = 1
    prior_steps: List[AgentStep] = Field(default_factory=list)
    prior_dialogue: List[AgentExchange] = Field(default_factory=list)


class AgentTurnResponse(BaseModel):
    mode: str = "case_agent_turn"
    expected_outcome: str
    detected_language: str
    model_status: str
    round_index: int
    pipeline: List[PipelineStep]
    agent_profile: AgentProfile
    agent_step: AgentStep
    dialogue: List[AgentExchange]


class CaseSynthesisRequest(BaseModel):
    structured_case: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str
    detected_language: str
    document: UploadedDocument
    agent_steps: List[AgentStep] = Field(default_factory=list)


class CaseSynthesisResponse(BaseModel):
    mode: str = "case_synthesis"
    expected_outcome: str
    detected_language: str
    model_status: str
    pipeline: List[PipelineStep]
    final_result: CaseFinalResult


class CaseReasonResponse(BaseModel):
    mode: str = "case_reasoning"
    expected_outcome: str
    collaboration_rounds: int = 2
    detected_language: str
    model_status: str
    pipeline: List[PipelineStep]
    agent_profiles: List[AgentProfile]
    agents: List[AgentStep]
    agent_dialogue: List[AgentExchange]
    final_result: CaseFinalResult


class CaseWorkflowResponse(BaseModel):
    mode: str = "case_reenactment"
    document: UploadedDocument
    expected_outcome: str
    collaboration_rounds: int = 2
    detected_language: str
    model_status: str
    graph_nodes: List[GraphNode]
    graph_edges: List[GraphEdge]
    evidence_items: List[EvidenceItem]
    pipeline: List[PipelineStep]
    agent_profiles: List[AgentProfile]
    agents: List[AgentStep]
    agent_dialogue: List[AgentExchange]
    final_result: CaseFinalResult


class CaseSessionResponse(BaseModel):
    mode: str = "case_session"
    session_id: str
    status: str
    status_text: str
    expected_outcome: str
    collaboration_rounds: int = 2
    document: UploadedDocument
    extracted_text: str
    detected_language: Optional[str] = None
    model_status: str = "preparing"
    pipeline: List[PipelineStep] = Field(default_factory=list)
    graph_nodes: List[GraphNode] = Field(default_factory=list)
    graph_edges: List[GraphEdge] = Field(default_factory=list)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    agent_profiles: List[AgentProfile] = Field(default_factory=list)
    agents: List[AgentStep] = Field(default_factory=list)
    agent_dialogue: List[AgentExchange] = Field(default_factory=list)
    final_result: Optional[CaseFinalResult] = None
    error: Optional[str] = None
