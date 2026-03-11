const els = {
  providerName: document.getElementById("providerName"),
  baseUrl: document.getElementById("baseUrl"),
  modelName: document.getElementById("modelName"),
  apiKey: document.getElementById("apiKey"),
  modelEnabled: document.getElementById("modelEnabled"),
  configState: document.getElementById("configState"),
  expectedOutcome: document.getElementById("expectedOutcome"),
  rawText: document.getElementById("rawText"),
  fileInput: document.getElementById("fileInput"),
  statusText: document.getElementById("statusText"),
  modelBadge: document.getElementById("modelBadge"),
  designNotes: document.getElementById("designNotes"),
  pipelineRoot: document.getElementById("pipelineRoot"),
  documentRoot: document.getElementById("documentRoot"),
  graphCanvas: document.getElementById("graphCanvas"),
  graphInspector: document.getElementById("graphInspector"),
  agentRoot: document.getElementById("agentRoot"),
  agentDialogue: document.getElementById("agentDialogue"),
  resultRoot: document.getElementById("resultRoot"),
};

const STEP_LABELS = {
  parse: { title: "材料解析", detail: "抽取可分析文本、基础事实与结构化片段。" },
  graph: { title: "关系图谱", detail: "构建人物、事件、线索之间的可交互关系网络。" },
  reason: { title: "多智能体推演", detail: "按角色逐步执行分析代理，并动态回放交互。" },
  result: { title: "综合输出", detail: "生成案情解释、嫌疑人排序与证据化时间线。" },
};

const state = {
  graphInstance: null,
  graphData: { nodes: [], links: [] },
  selectedNodeId: null,
  selectedLinkKey: null,
  parseData: null,
  agentSteps: [],
  dialogueItems: [],
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "请求失败");
  }
  return response.json();
}

function setStatus(text) {
  els.statusText.textContent = text;
}

function resetWorkspace() {
  if (state.graphInstance && typeof state.graphInstance._destructor === "function") {
    state.graphInstance._destructor();
  }
  state.graphInstance = null;
  state.graphData = { nodes: [], links: [] };
  state.selectedNodeId = null;
  state.selectedLinkKey = null;
  state.parseData = null;
  state.agentSteps = [];
  state.dialogueItems = [];

  els.pipelineRoot.className = "pipeline empty";
  els.pipelineRoot.textContent = "任务启动后，这里会依次展示解析、图谱、代理与结果阶段。";
  els.documentRoot.className = "document empty";
  els.documentRoot.textContent = "尚未载入材料。";
  els.graphCanvas.className = "graph-shell empty";
  els.graphCanvas.textContent = "图谱尚未生成。";
  els.graphInspector.className = "inspector empty";
  els.graphInspector.textContent = "点击节点、关系、证据引用或关联节点后，这里会显示详细说明。";
  els.agentRoot.className = "grid-two empty";
  els.agentRoot.textContent = "智能体将在图谱准备完成后初始化。";
  els.agentDialogue.className = "dialogue-feed empty";
  els.agentDialogue.textContent = "代理交互日志会随着推理逐步出现。";
  els.resultRoot.className = "result-grid empty";
  els.resultRoot.textContent = "最终分析结果将在这里生成。";
}

function renderPipeline(steps) {
  els.pipelineRoot.className = "pipeline";
  els.pipelineRoot.innerHTML = steps
    .map((step) => {
      const copy = STEP_LABELS[step.step_id] || { title: step.title, detail: step.detail };
      return `
        <article class="pipeline-step ${step.status}">
          <strong>${copy.title}</strong>
          <div class="muted">${step.status}</div>
          <p>${copy.detail}</p>
        </article>
      `;
    })
    .join("");
}

function renderDocument(document, evidenceItems, expectedOutcome) {
  els.documentRoot.className = "document";
  els.documentRoot.innerHTML = `
    <article class="result-card">
      <strong>${document.source_name}</strong>
      <div class="pill-row">
        <span class="pill">类型: ${document.source_type}</span>
        <span class="pill">字符数: ${document.character_count}</span>
        <span class="pill">页数: ${document.page_count ?? "未统计"}</span>
      </div>
      <p><strong>分析目标:</strong> ${expectedOutcome}</p>
      <p>${document.extracted_preview}</p>
    </article>
    <article class="result-card">
      <strong>关键证据预览</strong>
      <ul>${evidenceItems.slice(0, 6).map((item) => `<li><strong>${item.label}</strong>（风险 ${item.risk_score}） ${item.detail}</li>`).join("")}</ul>
    </article>
  `;
}

function nodeColor(node) {
  if (node.node_type === "actor") return "#b44d28";
  if (node.node_type === "event") return "#254d59";
  return "#c59c3d";
}

function linkKey(link) {
  const source = typeof link.source === "object" ? link.source.id : link.source;
  const target = typeof link.target === "object" ? link.target.id : link.target;
  return `${source}__${target}__${link.relation}`;
}

function normalizeGraph(nodes, edges) {
  const normalizedNodes = nodes.map((node) => ({
    ...node,
    id: node.node_id,
    color: nodeColor(node),
    val: Math.max(8, (Number(node.suspicion_score) || 18) / 7),
  }));
  const ids = new Set(normalizedNodes.map((node) => node.id));
  const normalizedLinks = edges
    .filter((edge) => ids.has(edge.source) && ids.has(edge.target))
    .map((edge) => ({ ...edge, key: linkKey(edge) }));
  return { nodes: normalizedNodes, links: normalizedLinks };
}

function neighborMap() {
  const map = new Map();
  for (const node of state.graphData.nodes) map.set(node.id, new Set());
  for (const link of state.graphData.links) {
    const source = typeof link.source === "object" ? link.source.id : link.source;
    const target = typeof link.target === "object" ? link.target.id : link.target;
    map.get(source)?.add(target);
    map.get(target)?.add(source);
  }
  return map;
}

function applyGraphHighlight() {
  if (!state.graphInstance) return;
  const neighbors = neighborMap();
  const selectedNodeId = state.selectedNodeId;
  const selectedLinkKey = state.selectedLinkKey;

  state.graphInstance
    .nodeColor((node) => {
      if (!selectedNodeId && !selectedLinkKey) return node.color;
      if (selectedNodeId) {
        if (node.id === selectedNodeId) return "#111111";
        if (neighbors.get(selectedNodeId)?.has(node.id)) return node.color;
        return "rgba(160, 160, 160, 0.25)";
      }
      if (selectedLinkKey) {
        const activeLink = state.graphData.links.find((item) => item.key === selectedLinkKey);
        const source = typeof activeLink?.source === "object" ? activeLink.source.id : activeLink?.source;
        const target = typeof activeLink?.target === "object" ? activeLink.target.id : activeLink?.target;
        if (node.id === source || node.id === target) return node.color;
        return "rgba(160, 160, 160, 0.25)";
      }
      return node.color;
    })
    .linkColor((link) => {
      if (!selectedNodeId && !selectedLinkKey) return "rgba(29,26,24,0.2)";
      const source = typeof link.source === "object" ? link.source.id : link.source;
      const target = typeof link.target === "object" ? link.target.id : link.target;
      if (selectedLinkKey && link.key === selectedLinkKey) return "#111111";
      if (selectedNodeId && (source === selectedNodeId || target === selectedNodeId)) return "rgba(37,77,89,0.8)";
      return "rgba(160,160,160,0.16)";
    })
    .linkWidth((link) => {
      if (selectedLinkKey && link.key === selectedLinkKey) return 5;
      const source = typeof link.source === "object" ? link.source.id : link.source;
      const target = typeof link.target === "object" ? link.target.id : link.target;
      if (selectedNodeId && (source === selectedNodeId || target === selectedNodeId)) return 3.2;
      return 1.5 + Number(link.strength || 0.5);
    })
    .nodeVal((node) => {
      if (selectedNodeId && node.id === selectedNodeId) return node.val * 1.4;
      return node.val;
    });
}

function renderEvidenceDetails(details = []) {
  if (!details.length) return "<p class=\"muted\">暂无细粒度证据引用。</p>";
  return `
    <div class="evidence-stack">
      ${details
        .map(
          (detail) => `
            <button class="evidence-chip" data-ref-id="${detail.ref_id}">
              <strong>${detail.ref_id}</strong>
              <span>${detail.note || detail.source}</span>
            </button>
            <p class="evidence-excerpt">${detail.excerpt}</p>
          `
        )
        .join("")}
    </div>
  `;
}

function renderRelatedNodes(nodeIds = []) {
  if (!nodeIds.length) return "<p class=\"muted\">暂无关联节点。</p>";
  return `
    <div class="chips">
      ${nodeIds.map((nodeId) => `<button class="pill link-pill" data-node-id="${nodeId}">${nodeId}</button>`).join("")}
    </div>
  `;
}

function renderInspector(kind, payload) {
  els.graphInspector.className = "inspector";
  if (kind === "node") {
    const attributes = Object.entries(payload.attributes || {})
      .map(([key, value]) => `<div><dt>${key}</dt><dd>${value}</dd></div>`)
      .join("");
    els.graphInspector.innerHTML = `
      <article class="inspector-card">
        <h3>${payload.label}</h3>
        <p class="muted">${payload.node_type}</p>
        <p>${payload.summary || "暂无摘要。"}</p>
        <dl>
          <div><dt>node_id</dt><dd>${payload.node_id || payload.id}</dd></div>
          <div><dt>evidence_refs</dt><dd>${(payload.evidence_refs || []).join(", ") || "无"}</dd></div>
          ${attributes}
        </dl>
        <h4>证据引用</h4>
        ${renderEvidenceDetails(payload.evidence_details || [])}
        <h4>关联节点</h4>
        ${renderRelatedNodes(payload.related_node_ids || [])}
      </article>
    `;
    return;
  }

  els.graphInspector.innerHTML = `
    <article class="inspector-card">
      <h3>${payload.relation}</h3>
      <p class="muted">${payload.source} -> ${payload.target}</p>
      <p>${payload.evidence || "暂无说明。"}</p>
      <dl>
        <div><dt>strength</dt><dd>${payload.strength}</dd></div>
        <div><dt>evidence_refs</dt><dd>${(payload.evidence_refs || []).join(", ") || "无"}</dd></div>
      </dl>
      <h4>证据引用</h4>
      ${renderEvidenceDetails(payload.evidence_details || [])}
    </article>
  `;
}

function selectNodeById(nodeId) {
  const node = state.graphData.nodes.find((item) => item.id === nodeId || item.node_id === nodeId);
  if (!node) return;
  state.selectedNodeId = node.id;
  state.selectedLinkKey = null;
  renderInspector("node", node);
  applyGraphHighlight();
}

function selectLink(link) {
  state.selectedNodeId = null;
  state.selectedLinkKey = link.key;
  renderInspector("link", link);
  applyGraphHighlight();
}

function renderGraph(nodes, edges) {
  els.graphCanvas.className = "graph-shell";
  els.graphCanvas.innerHTML = "";
  els.graphInspector.className = "inspector empty";
  els.graphInspector.textContent = "点击节点、关系、证据引用或关联节点后，这里会显示详细说明。";

  if (!nodes.length) {
    els.graphCanvas.classList.add("empty");
    els.graphCanvas.textContent = "当前材料尚未生成可视化图谱。";
    return;
  }

  if (typeof ForceGraph3D !== "function") {
    els.graphCanvas.classList.add("empty");
    els.graphCanvas.textContent = "3D 图谱组件加载失败。";
    return;
  }

  state.graphData = normalizeGraph(nodes, edges);
  const width = Math.max(480, els.graphCanvas.clientWidth - 24);
  const height = Math.max(500, els.graphCanvas.clientHeight - 24);

  state.graphInstance = ForceGraph3D()(els.graphCanvas)
    .width(width)
    .height(height)
    .nodeId("id")
    .linkSource("source")
    .linkTarget("target")
    .showNavInfo(false)
    .backgroundColor("rgba(255,255,255,0)")
    .nodeColor((node) => node.color)
    .nodeVal((node) => node.val)
    .nodeLabel((node) => `${node.label}<br/>${node.node_type}`)
    .linkColor(() => "rgba(29,26,24,0.2)")
    .linkWidth((link) => 1.5 + Number(link.strength || 0.5))
    .linkOpacity(0.72)
    .linkDirectionalParticles(1)
    .linkDirectionalParticleWidth(2)
    .d3AlphaDecay(0.02)
    .cooldownTicks(180)
    .graphData(state.graphData)
    .onNodeClick((node) => selectNodeById(node.id))
    .onLinkClick((link) => selectLink(link))
    .onEngineStop(() => state.graphInstance && state.graphInstance.zoomToFit(500, 60));
}

function ensureAgentCard(profile) {
  let card = els.agentRoot.querySelector(`[data-agent-name="${profile.agent_name}"]`);
  if (card) return card;
  card = document.createElement("article");
  card.className = "agent-card persona-card";
  card.dataset.agentName = profile.agent_name;
  card.style.setProperty("--agent-accent", profile.accent);
  card.innerHTML = `
    <div class="persona-head">
      <div class="persona-badge">${profile.codename.slice(0, 2).toUpperCase()}</div>
      <div>
        <strong>${profile.codename}</strong>
        <div class="muted">${profile.agent_name} / ${profile.role}</div>
      </div>
    </div>
    <p class="persona-summary">${profile.current_focus}</p>
    <div class="persona-state">${profile.disposition}</div>
    <p class="muted">${profile.persistent_state}</p>
    <ul class="memory-list">${(profile.memory_notes || []).map((item) => `<li>${item}</li>`).join("")}</ul>
    <div class="agent-findings muted">等待执行</div>
  `;
  els.agentRoot.appendChild(card);
  return card;
}

function renderAgentProfiles(profiles = []) {
  els.agentRoot.className = "grid-two";
  els.agentRoot.innerHTML = "";
  profiles.forEach((profile) => ensureAgentCard(profile));
}

function setActiveAgent(agentName) {
  els.agentRoot.querySelectorAll(".persona-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.agentName === agentName);
  });
}

function renderAgentTurn(turn) {
  const card = ensureAgentCard(turn.agent_profile);
  card.querySelector(".agent-findings").innerHTML = `
    <div class="findings-title">最新产出</div>
    <ul>${turn.agent_step.findings.map((item) => `<li>${item}</li>`).join("")}</ul>
    <div class="muted">confidence: ${turn.agent_step.confidence.toFixed(2)}</div>
  `;
}

async function playDialogueItems(dialogue = []) {
  els.agentDialogue.className = "dialogue-feed";
  for (const item of dialogue) {
    const node = document.createElement("article");
    node.className = "dialogue-item";
    node.innerHTML = `
      <div class="dialogue-head">
        <span>${item.speaker}</span>
        <span>${item.audience}</span>
      </div>
      <p>${item.message}</p>
    `;
    els.agentDialogue.appendChild(node);
    els.agentDialogue.scrollTop = els.agentDialogue.scrollHeight;
    await sleep(220);
  }
}

function renderResults(finalResult) {
  const rankingRows = finalResult.suspect_rankings
    .map(
      (item, index) => `
        <article class="ranking-row">
          <div class="ranking-score">#${index + 1}</div>
          <strong>${item.name}</strong>
          <div class="muted">${item.role}</div>
          <p><strong>动机:</strong> ${item.motive}</p>
          <p><strong>手段:</strong> ${item.means}</p>
          <p><strong>机会:</strong> ${item.opportunity}</p>
          <ul>${item.supporting_evidence.map((evidence) => `<li>${evidence}</li>`).join("")}</ul>
        </article>
      `
    )
    .join("");

  const timelineRows = finalResult.reenactment_timeline
    .map(
      (item) => `
        <article class="timeline-row">
          <strong>${item.order}. ${item.phase}</strong>
          <div class="muted">${item.time_hint} / ${item.inference_level}</div>
          <p>${item.event}</p>
          <div class="chips">${item.evidence_refs.map((ref) => `<button class="pill link-pill" data-ref-id="${ref}">${ref}</button>`).join("")}</div>
        </article>
      `
    )
    .join("");

  els.resultRoot.className = "result-grid";
  els.resultRoot.innerHTML = `
    <article class="result-card">
      <h3>案情解释</h3>
      <p>${finalResult.case_explanation}</p>
      <p><strong>综合结论:</strong> ${finalResult.verdict_summary}</p>
    </article>
    <article class="result-card">
      <h3>证据说明</h3>
      <ul>${finalResult.evidence_notes.map((item) => `<li>${item}</li>`).join("")}</ul>
      <h3>不确定性</h3>
      <ul>${finalResult.uncertainties.map((item) => `<li>${item}</li>`).join("")}</ul>
    </article>
    <article class="result-card">
      <h3>嫌疑人排序</h3>
      <div class="ranking-table">${rankingRows || "<p>暂无嫌疑人排序。</p>"}</div>
    </article>
    <article class="result-card">
      <h3>案情重演时间线</h3>
      <div class="timeline-list">${timelineRows || "<p>暂无可用时间线。</p>"}</div>
    </article>
  `;
}

async function loadConfig() {
  const config = await fetchJson("/api/model-config");
  els.providerName.value = config.provider_name || "";
  els.baseUrl.value = config.base_url || "";
  els.modelName.value = config.model || "";
  els.modelEnabled.checked = Boolean(config.enabled);
  els.configState.textContent = config.has_api_key
    ? `已读取模型配置，Key: ${config.api_key_hint || "已保存"}`
    : "当前未保存 API Key，将自动回退到规则引擎。";
}

async function saveConfig() {
  const payload = {
    provider_name: els.providerName.value.trim() || "OpenAI Compatible",
    base_url: els.baseUrl.value.trim(),
    model: els.modelName.value.trim(),
    api_key: els.apiKey.value.trim(),
    enabled: els.modelEnabled.checked,
  };
  await fetchJson("/api/model-config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  els.apiKey.value = "";
  els.configState.textContent = payload.enabled ? "模型配置已保存，后续任务会优先调用外部模型。" : "模型配置已保存，当前处于关闭状态。";
}

async function loadSample() {
  const sample = await fetchJson("/api/case-sample");
  els.rawText.value = sample.seed_text;
  els.expectedOutcome.value = sample.expected_outcome;
  setStatus(`样例已载入: ${sample.title}`);
}

async function runWorkflow() {
  resetWorkspace();
  setStatus("正在解析材料");
  els.modelBadge.textContent = "parsing";

  const formData = new FormData();
  formData.append("expected_outcome", els.expectedOutcome.value.trim() || "请重建这份材料所指向的形成链条。");
  formData.append("raw_text", els.rawText.value.trim());
  const file = els.fileInput.files[0];
  if (file) formData.append("file", file);

  try {
    const parseData = await fetchJson("/api/case-parse", { method: "POST", body: formData });
    state.parseData = parseData;
    renderPipeline(parseData.pipeline);
    renderDocument(parseData.document, parseData.evidence_items, parseData.expected_outcome);
    renderGraph(parseData.graph_nodes, parseData.graph_edges);
    renderAgentProfiles(parseData.agent_profiles || []);

    setStatus("图谱已完成，正在逐步执行多智能体推演");
    els.modelBadge.textContent = "reasoning";

    for (const profile of parseData.agent_profiles || []) {
      setActiveAgent(profile.agent_name);
      setStatus(`正在执行 ${profile.agent_name}`);
      const turn = await fetchJson("/api/case-agent-turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          structured_case: parseData.structured_case,
          expected_outcome: parseData.expected_outcome,
          detected_language: parseData.detected_language,
          document: parseData.document,
          agent_name: profile.agent_name,
          prior_steps: state.agentSteps,
        }),
      });
      renderAgentTurn(turn);
      state.agentSteps.push(turn.agent_step);
      await playDialogueItems(turn.dialogue || []);
      await sleep(180);
    }

    renderPipeline([
      { step_id: "parse", status: "completed" },
      { step_id: "graph", status: "completed" },
      { step_id: "reason", status: "completed" },
      { step_id: "result", status: "pending" },
    ]);
    setActiveAgent("");
    setStatus("正在生成综合分析结果");

    const synthesis = await fetchJson("/api/case-synthesis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        structured_case: parseData.structured_case,
        expected_outcome: parseData.expected_outcome,
        detected_language: parseData.detected_language,
        document: parseData.document,
        agent_steps: state.agentSteps,
      }),
    });

    renderPipeline(synthesis.pipeline);
    renderResults(synthesis.final_result);
    els.modelBadge.textContent = synthesis.model_status;
    setStatus("分析完成");
  } catch (error) {
    setStatus("任务失败");
    els.pipelineRoot.className = "pipeline";
    els.pipelineRoot.innerHTML = `<article class="pipeline-step fallback"><strong>错误</strong><p>${String(error.message).slice(0, 500)}</p></article>`;
  }
}

async function bootstrap() {
  const design = await fetchJson("/api/design");
  els.designNotes.innerHTML = [...design.borrowed_from_mirofish, ...design.rewritten_for_backtrace]
    .map((item) => `<li>${item}</li>`)
    .join("");
  await loadConfig();
}

els.graphInspector.addEventListener("click", (event) => {
  const target = event.target.closest("[data-node-id], [data-ref-id]");
  if (!target) return;
  if (target.dataset.nodeId) {
    selectNodeById(target.dataset.nodeId);
    return;
  }
  if (target.dataset.refId) {
    const refId = target.dataset.refId;
    const node = state.graphData.nodes.find((item) => (item.evidence_refs || []).includes(refId));
    if (node) selectNodeById(node.id);
  }
});

els.resultRoot.addEventListener("click", (event) => {
  const target = event.target.closest("[data-ref-id]");
  if (!target) return;
  const refId = target.dataset.refId;
  const node = state.graphData.nodes.find((item) => (item.evidence_refs || []).includes(refId));
  if (node) selectNodeById(node.id);
});

document.getElementById("saveConfig").addEventListener("click", saveConfig);
document.getElementById("loadSample").addEventListener("click", loadSample);
document.getElementById("runWorkflow").addEventListener("click", runWorkflow);

bootstrap();
