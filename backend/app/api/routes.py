from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.analysis.case_reconstruction import analyze_case
from app.analysis.case_workflow import parse_case_material, reason_case_material, run_agent_turn, run_case_workflow, synthesize_case
from app.analysis.conversation import analyze_conversation
from app.analysis.llm import load_model_config, model_config_view, save_model_config
from app.analysis.sample_data import CASE_SAMPLE, CONVERSATION_SAMPLE, DEMO_LIBRARY
from app.core.document_parser import DocumentParser
from app.schemas import AnalysisRequest, AgentTurnRequest, CaseReasonRequest, CaseSynthesisRequest, ModelConfig

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "Salmon"}


@router.get("/demos")
def list_demos() -> list[dict]:
    return [demo.model_dump() for demo in DEMO_LIBRARY]


@router.get("/design")
def design_notes() -> dict:
    return {
        "borrowed_from_mirofish": [
            "保留‘文档解析 -> 图谱构建 -> 智能体推演 -> 综合裁决’的分层流程。",
            "复用图谱先行的思路，让用户先看到人物、事件、线索和关系结构。",
            "参考工作台式双栏交互，把图谱、智能体过程和结果统一放在一个页面里。",
        ],
        "rewritten_for_backtrace": [
            "将面向未来的社会仿真改为面向过去的案件回溯与因果重建。",
            "将智能体职责改写为 Evidence / Relationship / Suspicion / Reconstruction / Judge。",
            "优先服务 PDF 或文本材料上传，面向案情重演，同时保留向更多回溯用例扩展的能力。",
        ],
    }


@router.get("/model-config")
def get_model_config() -> dict:
    return model_config_view(load_model_config()).model_dump()


@router.post("/model-config")
def update_model_config(payload: ModelConfig) -> dict:
    stored = save_model_config(payload)
    return model_config_view(stored).model_dump()


@router.get("/case-sample")
def case_sample() -> dict:
    return CASE_SAMPLE.model_dump()


@router.get("/conversation-sample")
def conversation_sample() -> dict:
    return CONVERSATION_SAMPLE.model_dump()


@router.post("/analyze/conversation")
def analyze_conversation_route(payload: AnalysisRequest) -> dict:
    return analyze_conversation(payload.text, payload.expected_outcome).model_dump()


@router.post("/analyze/case")
def analyze_case_route(payload: AnalysisRequest) -> dict:
    return analyze_case(payload.text, payload.expected_outcome).model_dump()


@router.post("/case-parse")
async def case_parse_route(
    expected_outcome: str = Form("请重建这份材料所指向的形成链条。"),
    raw_text: str = Form(""),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    if file is None and not raw_text.strip():
        raise HTTPException(status_code=400, detail="请上传 PDF/TXT/MD 文件，或直接输入案情文本。")

    try:
        if file is not None and file.filename:
            document, text = await DocumentParser.parse_upload(file)
        else:
            document, text = DocumentParser.parse_text(raw_text, source_name="direct-input.txt")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not text.strip():
        raise HTTPException(status_code=400, detail="文档解析后没有拿到有效文本。")

    return parse_case_material(text=text, document=document, expected_outcome=expected_outcome).model_dump()


@router.post("/case-reason")
def case_reason_route(payload: CaseReasonRequest) -> dict:
    if not payload.text.strip() and not payload.structured_case:
        raise HTTPException(status_code=400, detail="推演阶段缺少可分析文本或结构化上下文。")
    return reason_case_material(
        text=payload.text,
        document=payload.document,
        expected_outcome=payload.expected_outcome,
        structured_case=payload.structured_case,
    ).model_dump()


@router.post("/case-agent-turn")
def case_agent_turn_route(payload: AgentTurnRequest) -> dict:
    return run_agent_turn(
        structured_case=payload.structured_case,
        expected_outcome=payload.expected_outcome,
        detected_language=payload.detected_language,
        document=payload.document,
        agent_name=payload.agent_name,
        prior_steps=payload.prior_steps,
        prior_dialogue=payload.prior_dialogue,
        round_index=payload.round_index,
    ).model_dump()


@router.post("/case-synthesis")
def case_synthesis_route(payload: CaseSynthesisRequest) -> dict:
    return synthesize_case(
        structured_case=payload.structured_case,
        expected_outcome=payload.expected_outcome,
        detected_language=payload.detected_language,
        document=payload.document,
        agent_steps=payload.agent_steps,
    ).model_dump()


@router.post("/case-workflow")
async def case_workflow_route(
    expected_outcome: str = Form("请重建这份材料所指向的形成链条。"),
    raw_text: str = Form(""),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    if file is None and not raw_text.strip():
        raise HTTPException(status_code=400, detail="请上传 PDF/TXT/MD 文件，或直接输入案情文本。")

    try:
        if file is not None and file.filename:
            document, text = await DocumentParser.parse_upload(file)
        else:
            document, text = DocumentParser.parse_text(raw_text, source_name="direct-input.txt")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not text.strip():
        raise HTTPException(status_code=400, detail="文档解析后没有拿到有效文本。")

    return run_case_workflow(text=text, document=document, expected_outcome=expected_outcome).model_dump()
