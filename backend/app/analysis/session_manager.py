import threading
import uuid
from copy import deepcopy
from typing import Dict, Optional

from app.analysis.case_workflow import parse_case_material, run_agent_turn, synthesize_case
from app.schemas import AgentStep, CaseSessionResponse, PipelineStep, UploadedDocument


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, CaseSessionResponse] = {}

    def create_session(
        self,
        text: str,
        document: UploadedDocument,
        expected_outcome: str,
        collaboration_rounds: int = 2,
    ) -> CaseSessionResponse:
        session_id = uuid.uuid4().hex
        snapshot = CaseSessionResponse(
            session_id=session_id,
            status="queued",
            status_text="材料已接收，正在准备结构化解析。",
            expected_outcome=expected_outcome,
            collaboration_rounds=collaboration_rounds,
            document=document,
            extracted_text=text,
            pipeline=_pipeline("pending", "pending", "pending", "pending"),
        )
        with self._lock:
            self._sessions[session_id] = snapshot
        thread = threading.Thread(
            target=self._run_session,
            args=(session_id, text, document, expected_outcome, collaboration_rounds),
            daemon=True,
        )
        thread.start()
        return snapshot

    def get_session(self, session_id: str) -> Optional[CaseSessionResponse]:
        with self._lock:
            snapshot = self._sessions.get(session_id)
            return deepcopy(snapshot) if snapshot else None

    def _update(self, session_id: str, **changes) -> None:
        with self._lock:
            snapshot = self._sessions[session_id]
            for key, value in changes.items():
                setattr(snapshot, key, value)

    def _run_session(
        self,
        session_id: str,
        text: str,
        document: UploadedDocument,
        expected_outcome: str,
        collaboration_rounds: int,
    ) -> None:
        try:
            self._update(
                session_id,
                status="parsing",
                status_text="正在解析材料并构建关系图谱。",
                pipeline=_pipeline("in_progress", "pending", "pending", "pending"),
            )
            parse_data = parse_case_material(
                text=text,
                document=document,
                expected_outcome=expected_outcome,
                collaboration_rounds=collaboration_rounds,
            )
            self._update(
                session_id,
                status="parsed",
                status_text="图谱已生成，正在初始化多智能体。",
                expected_outcome=parse_data.expected_outcome,
                collaboration_rounds=parse_data.collaboration_rounds,
                detected_language=parse_data.detected_language,
                model_status=parse_data.structured_case.get("parse_model_status", "rules_only"),
                pipeline=_pipeline("completed", "completed", "pending", "pending"),
                graph_nodes=parse_data.graph_nodes,
                graph_edges=parse_data.graph_edges,
                evidence_items=parse_data.evidence_items,
                agent_profiles=parse_data.agent_profiles,
            )

            agent_steps: list[AgentStep] = []
            dialogue_items = []
            latest_model_status = parse_data.structured_case.get("parse_model_status", "rules_only")
            round_plans = parse_data.structured_case.get("agent_round_plans") or [
                ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent"],
                ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent", "Judge Agent"],
            ]

            for round_index, round_agents in enumerate(round_plans, start=1):
                self._update(
                    session_id,
                    status="reasoning",
                    status_text=f"第 {round_index} 轮多智能体协作进行中。",
                    pipeline=_pipeline("completed", "completed", "in_progress", "pending"),
                )
                for agent_name in round_agents:
                    turn = run_agent_turn(
                        structured_case=parse_data.structured_case,
                        expected_outcome=parse_data.expected_outcome,
                        detected_language=parse_data.detected_language,
                        document=parse_data.document,
                        agent_name=agent_name,
                        prior_steps=agent_steps,
                        prior_dialogue=dialogue_items,
                        round_index=round_index,
                    )
                    agent_steps.append(turn.agent_step)
                    dialogue_items.extend(turn.dialogue)
                    latest_model_status = (
                        "model_plus_rules"
                        if turn.model_status == "model_plus_rules" or latest_model_status == "model_plus_rules"
                        else "rules_only"
                    )
                    self._update(
                        session_id,
                        model_status=latest_model_status,
                        agents=deepcopy(agent_steps),
                        agent_dialogue=deepcopy(dialogue_items),
                    )

            self._update(
                session_id,
                status="synthesizing",
                status_text="正在综合代理结论并生成目标导向输出。",
                pipeline=_pipeline("completed", "completed", "completed", "in_progress"),
            )
            synthesis = synthesize_case(
                structured_case=parse_data.structured_case,
                expected_outcome=parse_data.expected_outcome,
                detected_language=parse_data.detected_language,
                document=parse_data.document,
                agent_steps=agent_steps,
            )
            latest_model_status = (
                "model_plus_rules"
                if synthesis.model_status == "model_plus_rules" or latest_model_status == "model_plus_rules"
                else "rules_only"
            )
            self._update(
                session_id,
                status="completed",
                status_text="分析完成。",
                model_status=latest_model_status,
                pipeline=_pipeline("completed", "completed", "completed", "completed"),
                final_result=synthesis.final_result,
            )
        except Exception as exc:  # pragma: no cover
            self._update(
                session_id,
                status="failed",
                status_text="任务执行失败。",
                error=str(exc),
                pipeline=_pipeline("completed", "completed", "fallback", "fallback"),
            )


def _pipeline(parse_status: str, graph_status: str, reason_status: str, result_status: str) -> list[PipelineStep]:
    return [
        PipelineStep(step_id="parse", title="parse", detail="document parsed", status=parse_status),
        PipelineStep(step_id="graph", title="graph", detail="graph ready", status=graph_status),
        PipelineStep(step_id="reason", title="reason", detail="agents reasoning", status=reason_status),
        PipelineStep(step_id="result", title="result", detail="final synthesis", status=result_status),
    ]


session_manager = SessionManager()
