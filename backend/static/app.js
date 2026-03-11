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

const COPY = {
  pipeline: {
    parse: { title: "材料解析", detail: "抽取原始文本、结构化片段与初步证据引用。" },
    graph: { title: "关系图谱", detail: "构建人物、事件、线索及其关联关系。" },
    reason: { title: "多智能体协作", detail: "按轮次执行代理推演，逐步展示交叉校验过程。" },
    result: { title: "综合输出", detail: "整合代理结论，形成最终解释、排序与回溯时间线。" },
  },
  collaborationPlan: [
    {
      roundIndex: 1,
      label: "Round 1 · 初步建模",
      agents: ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent"],
    },
    {
      roundIndex: 2,
      label: "Round 2 · 交叉校验",
      agents: ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent", "Judge Agent"],
    },
  ],
  empty: {
    pipeline: "任务启动后，这里会依次展示解析、图谱、代理协作与综合输出。",
    document: "尚未载入材料。",
    graph: "图谱尚未生成。",
    agents: "图谱构建完成后将初始化代理角色。",
    dialogue: "多轮代理日志会逐步出现在这里。",
    results: "最终分析结果将在这里生成。",
  },
  graph: {
    defaultInspectorTitle: "图谱检查器",
    defaultInspectorBody: "点击节点、关系或证据引用后，这里会展示结构属性、证据摘录和关联对象。点击图谱空白处可恢复到初始高亮状态。",
    noEvidence: "暂无细粒度证据引用。",
    noRelatedNodes: "暂无关联节点。",
    noHitNodes: "没有直接命中的节点。",
    noHitLinks: "没有直接命中的关系。",
  },
};

const state = {
  graphInstance: null,
  graphData: { nodes: [], links: [] },
  parseData: null,
  agentSteps: [],
  dialogueItems: [],
  selectedNodeId: null,
  selectedLinkKey: null,
  selectedEvidenceRef: null,
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
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

function renderGraphInspectorDefault() {
  els.graphInspector.className = "inspector";
  els.graphInspector.innerHTML = `
    <article class="inspector-card">
      <h3>${COPY.graph.defaultInspectorTitle}</h3>
      <p>${COPY.graph.defaultInspectorBody}</p>
      <div class="chips">
        <span class="pill">节点 ${state.graphData.nodes.length}</span>
        <span class="pill">关系 ${state.graphData.links.length}</span>
      </div>
    </article>
  `;
}

function clearGraphSelection() {
  state.selectedNodeId = null;
  state.selectedLinkKey = null;
  state.selectedEvidenceRef = null;
  renderGraphInspectorDefault();
  applyGraphHighlight();
}

function resetWorkspace() {
  if (state.graphInstance && typeof state.graphInstance._destructor === "function") {
    state.graphInstance._destructor();
  }
  state.graphInstance = null;
  state.graphData = { nodes: [], links: [] };
  state.parseData = null;
  state.agentSteps = [];
  state.dialogueItems = [];
  state.selectedNodeId = null;
  state.selectedLinkKey = null;
  state.selectedEvidenceRef = null;

  els.pipelineRoot.className = "pipeline empty";
  els.pipelineRoot.textContent = COPY.empty.pipeline;
  els.documentRoot.className = "document empty";
  els.documentRoot.textContent = COPY.empty.document;
  els.graphCanvas.className = "graph-shell empty";
  els.graphCanvas.textContent = COPY.empty.graph;
  els.graphInspector.className = "inspector empty";
  els.graphInspector.textContent = COPY.graph.defaultInspectorBody;
  els.agentRoot.className = "grid-two empty";
  els.agentRoot.textContent = COPY.empty.agents;
  els.agentDialogue.className = "dialogue-feed empty";
  els.agentDialogue.textContent = COPY.empty.dialogue;
  els.resultRoot.className = "result-grid empty";
  els.resultRoot.textContent = COPY.empty.results;
}

function renderPipeline(steps) {
  els.pipelineRoot.className = "pipeline";
  els.pipelineRoot.innerHTML = steps
    .map((step) => {
      const copy = COPY.pipeline[step.step_id] || { title: step.title || step.step_id, detail: step.detail || "" };
      return `
        <article class="pipeline-step ${step.status}">
          <strong>${escapeHtml(copy.title)}</strong>
          <div class="muted">${escapeHtml(step.status)}</div>
          <p>${escapeHtml(copy.detail)}</p>
        </article>
      `;
    })
    .join("");
}

function updatePipeline(reasonStatus, resultStatus) {
  renderPipeline([
    { step_id: "parse", status: "completed" },
    { step_id: "graph", status: "completed" },
    { step_id: "reason", status: reasonStatus },
    { step_id: "result", status: resultStatus },
  ]);
}

function renderDocument(document, evidenceItems, expectedOutcome, fullText) {
  const materialText = escapeHtml(fullText || document.extracted_preview || "");
  els.documentRoot.className = "document";
  els.documentRoot.innerHTML = `
    <article class="result-card document-card">
      <div class="card-head">
        <strong>${escapeHtml(document.source_name)}</strong>
        <div class="pill-row">
          <span class="pill">类型：${escapeHtml(document.source_type)}</span>
          <span class="pill">字符数：${escapeHtml(document.character_count)}</span>
          <span class="pill">页数：${escapeHtml(document.page_count ?? "未统计")}</span>
        </div>
      </div>
      <div class="scroll-pane">
        <p><strong>分析目标：</strong>${escapeHtml(expectedOutcome)}</p>
        <p><strong>上传内容摘要：</strong></p>
        <p>${escapeHtml(document.extracted_preview || "暂无摘要")}</p>
      </div>
    </article>
    <article class="result-card document-card document-wide">
      <div class="card-head">
        <strong>完整材料</strong>
        <span class="muted">滚动查看全文</span>
      </div>
      <pre class="scroll-pane material-text">${materialText}</pre>
    </article>
    <article class="result-card document-card">
      <div class="card-head">
        <strong>关键证据预览</strong>
        <span class="muted">点击后联动图谱高亮</span>
      </div>
      <div class="scroll-pane evidence-list">
        ${evidenceItems
          .slice(0, 18)
          .map(
            (item) => `
              <button class="evidence-chip" data-ref-id="${escapeHtml(item.evidence_id)}">
                <strong>${escapeHtml(item.label)}</strong>
                <span>${escapeHtml(item.evidence_id)} / 风险 ${escapeHtml(item.risk_score)}</span>
              </button>
              <p class="evidence-excerpt">${escapeHtml(item.detail)}</p>
            `,
          )
          .join("")}
      </div>
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

function refsOf(item) {
  const refs = new Set(item.evidence_refs || []);
  for (const detail of item.evidence_details || []) {
    if (detail.ref_id) refs.add(detail.ref_id);
  }
  return refs;
}

function nodeMatchesEvidence(node, refId) {
  return refsOf(node).has(refId);
}

function linkMatchesEvidence(link, refId) {
  return refsOf(link).has(refId);
}

function collectEvidenceContext(refId) {
  const nodes = state.graphData.nodes.filter((node) => nodeMatchesEvidence(node, refId));
  const links = state.graphData.links.filter((link) => linkMatchesEvidence(link, refId));
  return { nodes, links };
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
  const { selectedNodeId, selectedLinkKey, selectedEvidenceRef } = state;
  const evidenceContext = selectedEvidenceRef ? collectEvidenceContext(selectedEvidenceRef) : { nodes: [], links: [] };
  const evidenceNodeIds = new Set(evidenceContext.nodes.map((node) => node.id));

  for (const link of evidenceContext.links) {
    const source = typeof link.source === "object" ? link.source.id : link.source;
    const target = typeof link.target === "object" ? link.target.id : link.target;
    evidenceNodeIds.add(source);
    evidenceNodeIds.add(target);
  }

  state.graphInstance
    .nodeColor((node) => {
      if (selectedEvidenceRef) {
        if (evidenceNodeIds.has(node.id)) return node.color;
        return "rgba(160, 160, 160, 0.18)";
      }
      if (selectedNodeId) {
        if (node.id === selectedNodeId) return "#111111";
        if (neighbors.get(selectedNodeId)?.has(node.id)) return node.color;
        return "rgba(160, 160, 160, 0.22)";
      }
      if (selectedLinkKey) {
        const activeLink = state.graphData.links.find((item) => item.key === selectedLinkKey);
        const source = typeof activeLink?.source === "object" ? activeLink.source.id : activeLink?.source;
        const target = typeof activeLink?.target === "object" ? activeLink.target.id : activeLink?.target;
        if (node.id === source || node.id === target) return node.color;
        return "rgba(160, 160, 160, 0.22)";
      }
      return node.color;
    })
    .linkColor((link) => {
      if (selectedEvidenceRef) {
        return linkMatchesEvidence(link, selectedEvidenceRef) ? "rgba(17,17,17,0.92)" : "rgba(160,160,160,0.12)";
      }
      if (selectedNodeId) {
        const source = typeof link.source === "object" ? link.source.id : link.source;
        const target = typeof link.target === "object" ? link.target.id : link.target;
        return source === selectedNodeId || target === selectedNodeId ? "rgba(37,77,89,0.82)" : "rgba(160,160,160,0.16)";
      }
      if (selectedLinkKey) {
        return link.key === selectedLinkKey ? "rgba(17,17,17,0.92)" : "rgba(160,160,160,0.16)";
      }
      return "rgba(29,26,24,0.2)";
    })
    .linkWidth((link) => {
      if (selectedEvidenceRef) {
        return linkMatchesEvidence(link, selectedEvidenceRef) ? 4.5 : 1;
      }
      if (selectedLinkKey) {
        return link.key === selectedLinkKey ? 5 : 1.5 + Number(link.strength || 0.5);
      }
      if (selectedNodeId) {
        const source = typeof link.source === "object" ? link.source.id : link.source;
        const target = typeof link.target === "object" ? link.target.id : link.target;
        return source === selectedNodeId || target === selectedNodeId ? 3.2 : 1.2;
      }
      return 1.5 + Number(link.strength || 0.5);
    })
    .nodeVal((node) => {
      if (selectedEvidenceRef) {
        return evidenceNodeIds.has(node.id) ? node.val * 1.35 : Math.max(5, node.val * 0.8);
      }
      if (selectedNodeId && node.id === selectedNodeId) return node.val * 1.45;
      return node.val;
    });
}

function renderEvidenceDetails(details = []) {
  if (!details.length) return `<p class="muted">${COPY.graph.noEvidence}</p>`;
  return `
    <div class="evidence-stack">
      ${details
        .map(
          (detail) => `
            <button class="evidence-chip" data-ref-id="${escapeHtml(detail.ref_id)}">
              <strong>${escapeHtml(detail.ref_id)}</strong>
              <span>${escapeHtml(detail.note || detail.source)}</span>
            </button>
            <p class="evidence-excerpt">${escapeHtml(detail.excerpt)}</p>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderRelatedNodes(nodeIds = []) {
  if (!nodeIds.length) return `<p class="muted">${COPY.graph.noRelatedNodes}</p>`;
  return `<div class="chips">${nodeIds
    .map((nodeId) => `<button class="pill link-pill" data-node-id="${escapeHtml(nodeId)}">${escapeHtml(nodeId)}</button>`)
    .join("")}</div>`;
}

function renderEvidenceInspector(refId) {
  const context = collectEvidenceContext(refId);
  els.graphInspector.className = "inspector";
  els.graphInspector.innerHTML = `
    <article class="inspector-card">
      <h3>证据 ${escapeHtml(refId)}</h3>
      <p class="muted">已同步高亮相关节点与边。点击图谱空白处可恢复默认视图。</p>
      <div class="chips">
        <span class="pill">节点 ${context.nodes.length}</span>
        <span class="pill">关系 ${context.links.length}</span>
      </div>
      <h4>相关节点</h4>
      ${
        context.nodes.length
          ? context.nodes
              .map(
                (node) => `
                  <button class="evidence-chip" data-node-id="${escapeHtml(node.id)}">
                    <strong>${escapeHtml(node.label)}</strong>
                    <span>${escapeHtml(node.node_type)} / ${escapeHtml(node.id)}</span>
                  </button>
                `,
              )
              .join("")
          : `<p class="muted">${COPY.graph.noHitNodes}</p>`
      }
      <h4>相关关系</h4>
      ${
        context.links.length
          ? context.links
              .map(
                (link) => `
                  <article class="inspector-link-row">
                    <strong>${escapeHtml(link.relation)}</strong>
                    <span class="muted">${escapeHtml(typeof link.source === "object" ? link.source.id : link.source)} -> ${escapeHtml(typeof link.target === "object" ? link.target.id : link.target)}</span>
                    <p>${escapeHtml(link.evidence || "")}</p>
                  </article>
                `,
              )
              .join("")
          : `<p class="muted">${COPY.graph.noHitLinks}</p>`
      }
    </article>
  `;
}

function renderInspector(kind, payload) {
  els.graphInspector.className = "inspector";
  if (kind === "node") {
    const attributes = Object.entries(payload.attributes || {})
      .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`)
      .join("");
    els.graphInspector.innerHTML = `
      <article class="inspector-card">
        <h3>${escapeHtml(payload.label)}</h3>
        <p class="muted">${escapeHtml(payload.node_type)}</p>
        <p>${escapeHtml(payload.summary || "暂无摘要。")}</p>
        <dl>
          <div><dt>node_id</dt><dd>${escapeHtml(payload.node_id || payload.id)}</dd></div>
          <div><dt>evidence_refs</dt><dd>${escapeHtml((payload.evidence_refs || []).join(", ") || "无")}</dd></div>
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
      <h3>${escapeHtml(payload.relation)}</h3>
      <p class="muted">${escapeHtml(typeof payload.source === "object" ? payload.source.id : payload.source)} -> ${escapeHtml(typeof payload.target === "object" ? payload.target.id : payload.target)}</p>
      <p>${escapeHtml(payload.evidence || "暂无说明。")}</p>
      <dl>
        <div><dt>strength</dt><dd>${escapeHtml(payload.strength)}</dd></div>
        <div><dt>evidence_refs</dt><dd>${escapeHtml((payload.evidence_refs || []).join(", ") || "无")}</dd></div>
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
  state.selectedEvidenceRef = null;
  renderInspector("node", node);
  applyGraphHighlight();
}

function selectLink(link) {
  state.selectedNodeId = null;
  state.selectedLinkKey = link.key;
  state.selectedEvidenceRef = null;
  renderInspector("link", link);
  applyGraphHighlight();
}

function selectEvidenceRef(refId) {
  state.selectedNodeId = null;
  state.selectedLinkKey = null;
  state.selectedEvidenceRef = refId;
  renderEvidenceInspector(refId);
  applyGraphHighlight();
}

function renderGraph(nodes, edges) {
  els.graphCanvas.className = "graph-shell";
  els.graphCanvas.innerHTML = "";

  if (!nodes.length) {
    els.graphCanvas.classList.add("empty");
    els.graphCanvas.textContent = "当前材料尚未生成可视化图谱。";
    els.graphInspector.className = "inspector empty";
    els.graphInspector.textContent = COPY.graph.defaultInspectorBody;
    return;
  }

  if (typeof ForceGraph3D !== "function") {
    els.graphCanvas.classList.add("empty");
    els.graphCanvas.textContent = "3D 图谱组件加载失败。";
    els.graphInspector.className = "inspector empty";
    els.graphInspector.textContent = COPY.graph.defaultInspectorBody;
    return;
  }

  state.graphData = normalizeGraph(nodes, edges);
  const width = Math.max(480, els.graphCanvas.clientWidth - 24);
  const height = Math.max(560, els.graphCanvas.clientHeight - 24);

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
    .nodeLabel((node) => `${escapeHtml(node.label)}<br />${escapeHtml(node.node_type)}`)
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
    .onBackgroundClick(() => clearGraphSelection())
    .onEngineStop(() => state.graphInstance && state.graphInstance.zoomToFit(500, 60));

  renderGraphInspectorDefault();
  applyGraphHighlight();
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
      <div class="persona-badge">${escapeHtml(profile.codename.slice(0, 2).toUpperCase())}</div>
      <div>
        <strong>${escapeHtml(profile.codename)}</strong>
        <div class="muted">${escapeHtml(profile.agent_name)} / ${escapeHtml(profile.role)}</div>
      </div>
    </div>
    <div class="persona-body">
      <p class="persona-summary">${escapeHtml(profile.current_focus)}</p>
      <div class="persona-state">${escapeHtml(profile.disposition)}</div>
      <p class="muted">${escapeHtml(profile.persistent_state)}</p>
      <div class="memory-scroll">
        <ul class="memory-list">${(profile.memory_notes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div class="agent-rounds"></div>
    </div>
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
  const roundsRoot = card.querySelector(".agent-rounds");
  const block = document.createElement("section");
  block.className = "agent-round-block";
  block.innerHTML = `
    <div class="findings-title">Round ${escapeHtml(turn.round_index)}</div>
    <ul>${turn.agent_step.findings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <div class="chips">${(turn.agent_step.focus_refs || [])
      .map((ref) => `<button class="pill link-pill" data-ref-id="${escapeHtml(ref)}">${escapeHtml(ref)}</button>`)
      .join("")}</div>
    <div class="muted">confidence: ${escapeHtml(turn.agent_step.confidence.toFixed(2))}</div>
  `;
  roundsRoot.appendChild(block);
  roundsRoot.scrollTop = roundsRoot.scrollHeight;
}

function appendSystemDialogue(label, roundIndex) {
  els.agentDialogue.className = "dialogue-feed";
  const node = document.createElement("article");
  node.className = "dialogue-item dialogue-system";
  node.innerHTML = `
    <div class="dialogue-head">
      <span>System</span>
      <span>Round ${escapeHtml(roundIndex)}</span>
    </div>
    <p>${escapeHtml(label)}</p>
  `;
  els.agentDialogue.appendChild(node);
}

async function playDialogueItems(dialogue = []) {
  els.agentDialogue.className = "dialogue-feed";
  for (const item of dialogue) {
    const node = document.createElement("article");
    node.className = "dialogue-item";
    node.innerHTML = `
      <div class="dialogue-head">
        <span>${escapeHtml(item.speaker)}</span>
        <span>Round ${escapeHtml(item.round_index)} / ${escapeHtml(item.audience)}</span>
      </div>
      <p>${escapeHtml(item.message)}</p>
      <div class="chips">${(item.evidence_refs || [])
        .map((ref) => `<button class="pill link-pill" data-ref-id="${escapeHtml(ref)}">${escapeHtml(ref)}</button>`)
        .join("")}</div>
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
          <strong>${escapeHtml(item.name)}</strong>
          <div class="muted">${escapeHtml(item.role)}</div>
          <p><strong>动机或驱动：</strong>${escapeHtml(item.motive)}</p>
          <p><strong>手段或路径：</strong>${escapeHtml(item.means)}</p>
          <p><strong>机会或触发点：</strong>${escapeHtml(item.opportunity)}</p>
          <ul>${(item.supporting_evidence || []).map((evidence) => `<li>${escapeHtml(evidence)}</li>`).join("")}</ul>
        </article>
      `,
    )
    .join("");

  const timelineRows = finalResult.reenactment_timeline
    .map(
      (item) => `
        <article class="timeline-row">
          <strong>${escapeHtml(item.order)}. ${escapeHtml(item.phase)}</strong>
          <div class="muted">${escapeHtml(item.time_hint)} / ${escapeHtml(item.inference_level)}</div>
          <p>${escapeHtml(item.event)}</p>
          <div class="chips">${(item.evidence_refs || [])
            .map((ref) => `<button class="pill link-pill" data-ref-id="${escapeHtml(ref)}">${escapeHtml(ref)}</button>`)
            .join("")}</div>
        </article>
      `,
    )
    .join("");

  els.resultRoot.className = "result-grid";
  els.resultRoot.innerHTML = `
    <article class="result-card result-scroll-card">
      <div class="card-head"><h3>分析解释</h3><span class="muted">主解释与综合判断</span></div>
      <div class="scroll-pane">
        <p>${escapeHtml(finalResult.case_explanation)}</p>
        <p><strong>综合结论：</strong>${escapeHtml(finalResult.verdict_summary)}</p>
      </div>
    </article>
    <article class="result-card result-scroll-card">
      <div class="card-head"><h3>证据与不确定性</h3><span class="muted">滚动查看</span></div>
      <div class="scroll-pane">
        <ul>${(finalResult.evidence_notes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        <h3>未决问题</h3>
        <ul>${(finalResult.uncertainties || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
    </article>
    <article class="result-card result-scroll-card">
      <div class="card-head"><h3>关键对象排序</h3><span class="muted">支持滚动</span></div>
      <div class="scroll-pane ranking-table">${rankingRows || "<p>暂无可用排序。</p>"}</div>
    </article>
    <article class="result-card result-scroll-card">
      <div class="card-head"><h3>回溯时间线</h3><span class="muted">带证据引用</span></div>
      <div class="scroll-pane timeline-list">${timelineRows || "<p>暂无可用时间线。</p>"}</div>
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
  els.configState.textContent = payload.enabled
    ? "模型配置已保存，后续任务会优先调用外部模型。"
    : "模型配置已保存，当前处于关闭状态。";
}

async function loadSample() {
  const sample = await fetchJson("/api/case-sample");
  els.rawText.value = sample.seed_text;
  els.expectedOutcome.value = sample.expected_outcome;
  setStatus(`样例已载入：${sample.title}`);
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
    renderDocument(parseData.document, parseData.evidence_items, parseData.expected_outcome, parseData.extracted_text);
    renderGraph(parseData.graph_nodes, parseData.graph_edges);
    renderAgentProfiles(parseData.agent_profiles || []);

    els.modelBadge.textContent = "reasoning";
    updatePipeline("in_progress", "pending");

    for (const roundPlan of COPY.collaborationPlan) {
      appendSystemDialogue(roundPlan.label, roundPlan.roundIndex);
      setStatus(`${roundPlan.label} 进行中`);
      for (const agentName of roundPlan.agents) {
        const profile = (parseData.agent_profiles || []).find((item) => item.agent_name === agentName);
        if (!profile) continue;
        setActiveAgent(agentName);
        setStatus(`Round ${roundPlan.roundIndex}: ${agentName}`);
        const turn = await fetchJson("/api/case-agent-turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            structured_case: parseData.structured_case,
            expected_outcome: parseData.expected_outcome,
            detected_language: parseData.detected_language,
            document: parseData.document,
            agent_name: agentName,
            round_index: roundPlan.roundIndex,
            prior_steps: state.agentSteps,
            prior_dialogue: state.dialogueItems,
          }),
        });
        renderAgentTurn(turn);
        state.agentSteps.push(turn.agent_step);
        state.dialogueItems.push(...(turn.dialogue || []));
        await playDialogueItems(turn.dialogue || []);
        await sleep(150);
      }
    }

    setActiveAgent("");
    updatePipeline("completed", "in_progress");
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
    els.pipelineRoot.innerHTML = `<article class="pipeline-step fallback"><strong>错误</strong><p>${escapeHtml(String(error.message).slice(0, 500))}</p></article>`;
  }
}

async function bootstrap() {
  const design = await fetchJson("/api/design");
  els.designNotes.innerHTML = [...design.borrowed_from_mirofish, ...design.rewritten_for_backtrace]
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  await loadConfig();
}

function handleRefClick(event) {
  const nodeTarget = event.target.closest("[data-node-id]");
  if (nodeTarget) {
    selectNodeById(nodeTarget.dataset.nodeId);
    return;
  }
  const refTarget = event.target.closest("[data-ref-id]");
  if (refTarget) {
    selectEvidenceRef(refTarget.dataset.refId);
  }
}

window.addEventListener("resize", () => {
  if (!state.graphInstance) return;
  const width = Math.max(480, els.graphCanvas.clientWidth - 24);
  const height = Math.max(560, els.graphCanvas.clientHeight - 24);
  state.graphInstance.width(width).height(height);
});

els.graphInspector.addEventListener("click", handleRefClick);
els.documentRoot.addEventListener("click", handleRefClick);
els.resultRoot.addEventListener("click", handleRefClick);
els.agentRoot.addEventListener("click", handleRefClick);
els.agentDialogue.addEventListener("click", handleRefClick);

document.getElementById("saveConfig").addEventListener("click", saveConfig);
document.getElementById("loadSample").addEventListener("click", loadSample);
document.getElementById("runWorkflow").addEventListener("click", runWorkflow);

resetWorkspace();
bootstrap();
