const els = {
  providerName: document.getElementById("providerName"),
  baseUrl: document.getElementById("baseUrl"),
  modelName: document.getElementById("modelName"),
  apiKey: document.getElementById("apiKey"),
  modelEnabled: document.getElementById("modelEnabled"),
  configState: document.getElementById("configState"),
  expectedOutcome: document.getElementById("expectedOutcome"),
  collaborationRounds: document.getElementById("collaborationRounds"),
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
  apiHealthBadge: document.getElementById("apiHealthBadge"),
  errorConsole: document.getElementById("errorConsole"),
};

const COPY = {
  pipeline: {
    parse: { title: "文档解析", detail: "抽取原始文本、结构化片段和候选证据。" },
    graph: { title: "关系图谱", detail: "构建人物、事件、线索及其证据关系。" },
    reason: { title: "多智能体协作", detail: "按轮次执行代理推演，并持续展示交互过程。" },
    result: { title: "综合输出", detail: "围绕分析目标生成可追溯的结果面板。" },
  },
  empty: {
    pipeline: "任务启动后，这里会持续展示解析、图谱、代理协作和综合输出阶段。",
    document: "尚未载入材料。",
    graph: "图谱尚未生成。",
    agents: "图谱准备完成后，这里会初始化多智能体角色。",
    dialogue: "多轮代理日志会随推理逐步出现。",
    results: "最终分析结果将在这里生成。",
  },
  graph: {
    defaultInspectorTitle: "图谱检查器",
    defaultInspectorBody: "点击节点、关系、证据引用或关联节点后，这里会显示详细属性、证据摘录与高亮联动。点击图谱空白处可恢复全图视图。",
    noEvidence: "暂无更细粒度的证据引用。",
    noRelatedNodes: "暂无关联节点。",
    noHitNodes: "没有直接命中的节点。",
    noHitLinks: "没有直接命中的关系。",
  },
};

const state = {
  graphInstance: null,
  graphData: { nodes: [], links: [] },
  graphSignature: "",
  sessionId: null,
  pollToken: 0,
  pollTimer: null,
  parseData: null,
  agentSteps: [],
  dialogueItems: [],
  renderedRounds: new Set(),
  finalRendered: false,
  selectedNodeId: null,
  selectedLinkKey: null,
  selectedEvidenceRef: null,
  theme: "sky",
  apiHealth: "unknown",
  lastHealthCheckAt: 0,
  runtimeMessages: [],
};

const THEME_ORDER = ["sky", "warm", "dark"];
const THEME_LABELS = {
  sky: "蓝白",
  warm: "暖色",
  dark: "夜间",
};

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeHtmlWithBreaks(value) {
  return escapeHtml(value).replace(/\n/g, "<br />");
}

async function fetchJson(url, options = {}) {
  const { meta = {}, ...fetchOptions } = options;
  if (!meta.skipHealthCheck && url !== "/api/health") {
    const reachable = await checkApiHealth({ force: meta.forceHealthCheck, silent: true });
    if (!reachable) {
      const message = "API 服务不可达，请检查后端是否启动或网络是否连通。";
      appendRuntimeMessage("error", "API 连通性检查失败", message);
      throw new Error(message);
    }
  }
  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (error) {
    const message = `请求 ${url} 失败：${String(error.message || error)}`;
    appendRuntimeMessage("error", "请求失败", message);
    throw error;
  }
  if (!response.ok) {
    const message = await response.text();
    appendRuntimeMessage("error", "接口返回错误", `${url} -> ${String(message || response.statusText).slice(0, 500)}`);
    throw new Error(message || "请求失败");
  }
  return response.json();
}

function setStatus(text) {
  els.statusText.textContent = text;
}

function appendRuntimeMessage(level, title, detail = "") {
  const entry = {
    level: level || "info",
    title: title || "运行提示",
    detail: String(detail || ""),
    timestamp: new Date(),
  };
  state.runtimeMessages = [entry, ...state.runtimeMessages].slice(0, 24);
  renderRuntimeConsole();
}

function renderRuntimeConsole() {
  if (!els.errorConsole) return;
  if (!state.runtimeMessages.length) {
    els.errorConsole.className = "error-console empty";
    els.errorConsole.textContent = "尚无运行反馈。页面加载后会先检查一次服务连通性。";
    return;
  }
  els.errorConsole.className = "error-console";
  els.errorConsole.innerHTML = state.runtimeMessages
    .map((item) => {
      const stamp = item.timestamp instanceof Date ? item.timestamp.toLocaleTimeString("zh-CN", { hour12: false }) : "";
      return `
        <article class="error-item ${escapeHtml(item.level)}">
          <div class="error-head">
            <strong>${escapeHtml(item.title)}</strong>
            <span class="muted">${escapeHtml(stamp)}</span>
          </div>
          ${item.detail ? `<p class="rich-text">${escapeHtmlWithBreaks(item.detail)}</p>` : ""}
        </article>
      `;
    })
    .join("");
}

function setApiHealthBadge(status, label) {
  if (!els.apiHealthBadge) return;
  els.apiHealthBadge.dataset.health = status;
  els.apiHealthBadge.textContent = label;
}

async function checkApiHealth({ force = false, silent = false } = {}) {
  const now = Date.now();
  if (!force && now - state.lastHealthCheckAt < 15000 && state.apiHealth === "online") {
    return true;
  }
  state.lastHealthCheckAt = now;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch("/api/health", { signal: controller.signal });
    if (!response.ok) throw new Error(response.statusText || "health check failed");
    const payload = await response.json();
    state.apiHealth = "online";
    setApiHealthBadge("online", payload.status === "ok" ? "API 正常" : "API 已响应");
    if (!silent) {
      appendRuntimeMessage("info", "API 连通性", "后端服务已连接，可继续运行分析。");
    }
    return true;
  } catch (error) {
    state.apiHealth = "offline";
    setApiHealthBadge("offline", "API 不可达");
    if (!silent) {
      appendRuntimeMessage("error", "API 连通性", `无法访问 /api/health：${String(error.message || error)}`);
    }
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

function clearPolling() {
  if (state.pollTimer) {
    window.clearTimeout(state.pollTimer);
    state.pollTimer = null;
  }
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

function hasGraphSelection() {
  return Boolean(state.selectedNodeId || state.selectedLinkKey || state.selectedEvidenceRef);
}

function restoreGraphSelection() {
  if (state.selectedNodeId) {
    const node = state.graphData.nodes.find((item) => item.id === state.selectedNodeId || item.node_id === state.selectedNodeId);
    if (node) {
      renderInspector("node", node);
      applyGraphHighlight();
      return true;
    }
  }
  if (state.selectedLinkKey) {
    const link = state.graphData.links.find((item) => item.key === state.selectedLinkKey);
    if (link) {
      renderInspector("link", link);
      applyGraphHighlight();
      return true;
    }
  }
  if (state.selectedEvidenceRef) {
    renderEvidenceInspector(state.selectedEvidenceRef);
    applyGraphHighlight();
    return true;
  }
  clearGraphSelection();
  return false;
}

function clearGraphSelection() {
  state.selectedNodeId = null;
  state.selectedLinkKey = null;
  state.selectedEvidenceRef = null;
  renderGraphInspectorDefault();
  applyGraphHighlight();
}

function resetWorkspace() {
  clearPolling();
  if (state.graphInstance && typeof state.graphInstance._destructor === "function") {
    state.graphInstance._destructor();
  }
  state.graphInstance = null;
  state.graphData = { nodes: [], links: [] };
  state.graphSignature = "";
  state.sessionId = null;
  state.pollToken += 1;
  state.parseData = null;
  state.agentSteps = [];
  state.dialogueItems = [];
  state.renderedRounds = new Set();
  state.finalRendered = false;
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
  els.modelBadge.textContent = "idle";
}

function renderPipeline(steps = []) {
  if (!steps.length) {
    els.pipelineRoot.className = "pipeline empty";
    els.pipelineRoot.textContent = COPY.empty.pipeline;
    return;
  }
  els.pipelineRoot.className = "pipeline";
  els.pipelineRoot.innerHTML = steps
    .map((step) => {
      const copy = COPY.pipeline[step.step_id] || { title: step.title || step.step_id, detail: step.detail || "" };
      return `
        <article class="pipeline-step ${escapeHtml(step.status)}" data-status="${escapeHtml(step.status)}">
          <strong>${escapeHtml(copy.title)}</strong>
          <div class="muted">${escapeHtml(step.status)}</div>
          <p>${escapeHtml(copy.detail)}</p>
        </article>
      `;
    })
    .join("");
}

function renderDocument(document, evidenceItems = [], expectedOutcome = "", fullText = "") {
  const preview = document?.extracted_preview || "暂无摘要";
  const materialText = fullText || preview;
  els.documentRoot.className = "document";
  els.documentRoot.innerHTML = `
    <article class="result-card document-card">
      <div class="card-head">
        <strong>${escapeHtml(document?.source_name || "未命名材料")}</strong>
        <div class="pill-row">
          <span class="pill">类型 ${escapeHtml(document?.source_type || "text")}</span>
          <span class="pill">字符数 ${escapeHtml(document?.character_count || 0)}</span>
          <span class="pill">页数 ${escapeHtml(document?.page_count ?? "未统计")}</span>
        </div>
      </div>
      <div class="scroll-pane">
        <p><strong>分析目标：</strong>${escapeHtml(expectedOutcome || "未填写")}</p>
        <p><strong>上传内容摘要：</strong></p>
        <p class="rich-text">${escapeHtmlWithBreaks(preview)}</p>
      </div>
    </article>
    <article class="result-card document-card">
      <div class="card-head">
        <strong>完整材料</strong>
        <span class="muted">滚动查看全文</span>
      </div>
      <pre class="scroll-pane material-text">${escapeHtml(materialText)}</pre>
    </article>
    <article class="result-card document-card">
      <div class="card-head">
        <strong>关键证据预览</strong>
        <span class="muted">点击后联动图谱高亮</span>
      </div>
      <div class="scroll-pane evidence-list">
        ${
          evidenceItems.length
            ? evidenceItems
                .slice(0, 18)
                .map(
                  (item) => `
                    <div>
                      <button class="evidence-chip" data-ref-id="${escapeHtml(item.evidence_id)}">
                        <strong>${escapeHtml(item.label)}</strong>
                        <span>${escapeHtml(item.evidence_id)} / 风险 ${escapeHtml(item.risk_score)}</span>
                      </button>
                      <p class="evidence-excerpt">${escapeHtml(item.detail)}</p>
                    </div>
                  `,
                )
                .join("")
            : '<p class="muted">等待结构化分析完成后展示证据预览。</p>'
        }
      </div>
    </article>
  `;
}

function nodeColor(node) {
  const palette = graphPalette();
  if (node.node_type === "actor") return palette.actor;
  if (node.node_type === "event") return palette.event;
  return palette.clue;
}

function graphPalette() {
  if (state.theme === "dark") {
    return {
      actor: "#ffb792",
      event: "#79d7ff",
      clue: "#ffe18c",
      defaultLink: "rgba(143, 211, 255, 0.52)",
      mutedLink: "rgba(143, 191, 235, 0.14)",
      mutedNode: "rgba(120, 149, 180, 0.22)",
      activeLink: "rgba(255, 232, 169, 0.96)",
      focusNode: "#f4fbff",
    };
  }
  if (state.theme === "warm") {
    return {
      actor: "#b44d28",
      event: "#254d59",
      clue: "#c59c3d",
      defaultLink: "rgba(29,26,24,0.2)",
      mutedLink: "rgba(160,160,160,0.16)",
      mutedNode: "rgba(160,160,160,0.22)",
      activeLink: "rgba(37,77,89,0.82)",
      focusNode: "#111111",
    };
  }
  return {
    actor: "#367fbe",
    event: "#205d92",
    clue: "#88bfe8",
    defaultLink: "rgba(54,127,190,0.24)",
    mutedLink: "rgba(160,160,160,0.16)",
    mutedNode: "rgba(160,160,160,0.22)",
    activeLink: "rgba(36,104,166,0.9)",
    focusNode: "#102b47",
  };
}

function linkKey(link) {
  const source = typeof link.source === "object" ? link.source.id : link.source;
  const target = typeof link.target === "object" ? link.target.id : link.target;
  return `${source}__${target}__${link.relation}`;
}

function normalizeGraph(nodes, edges) {
  const normalizedNodes = (nodes || []).map((node) => ({
    ...node,
    id: node.node_id,
    color: nodeColor(node),
    val: Math.max(12, (Number(node.suspicion_score) || 24) / 5.2),
  }));
  const ids = new Set(normalizedNodes.map((node) => node.id));
  const normalizedLinks = (edges || [])
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
  const palette = graphPalette();
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
        return evidenceNodeIds.has(node.id) ? node.color : palette.mutedNode;
      }
      if (selectedNodeId) {
        if (node.id === selectedNodeId) return palette.focusNode;
        return neighbors.get(selectedNodeId)?.has(node.id) ? node.color : palette.mutedNode;
      }
      if (selectedLinkKey) {
        const activeLink = state.graphData.links.find((item) => item.key === selectedLinkKey);
        const source = typeof activeLink?.source === "object" ? activeLink.source.id : activeLink?.source;
        const target = typeof activeLink?.target === "object" ? activeLink.target.id : activeLink?.target;
        return node.id === source || node.id === target ? node.color : palette.mutedNode;
      }
      return node.color;
    })
    .linkColor((link) => {
      if (selectedEvidenceRef) {
        return linkMatchesEvidence(link, selectedEvidenceRef) ? palette.activeLink : palette.mutedLink;
      }
      if (selectedNodeId) {
        const source = typeof link.source === "object" ? link.source.id : link.source;
        const target = typeof link.target === "object" ? link.target.id : link.target;
        return source === selectedNodeId || target === selectedNodeId ? palette.activeLink : palette.mutedLink;
      }
      if (selectedLinkKey) {
        return link.key === selectedLinkKey ? palette.activeLink : palette.mutedLink;
      }
      return palette.defaultLink;
    })
    .linkWidth((link) => {
      if (selectedEvidenceRef) {
        return linkMatchesEvidence(link, selectedEvidenceRef) ? 6.4 : 1.6;
      }
      if (selectedLinkKey) {
        return link.key === selectedLinkKey ? 7 : 2.2 + Number(link.strength || 0.5) * 1.1;
      }
      if (selectedNodeId) {
        const source = typeof link.source === "object" ? link.source.id : link.source;
        const target = typeof link.target === "object" ? link.target.id : link.target;
        return source === selectedNodeId || target === selectedNodeId ? 4.8 : 1.8;
      }
      return 2.2 + Number(link.strength || 0.5) * 1.1;
    })
    .nodeVal((node) => {
      if (selectedEvidenceRef) {
        return evidenceNodeIds.has(node.id) ? node.val * 1.42 : Math.max(8, node.val * 0.86);
      }
      if (selectedNodeId && node.id === selectedNodeId) return node.val * 1.55;
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
            <div>
              <button class="evidence-chip" data-ref-id="${escapeHtml(detail.ref_id)}">
                <strong>${escapeHtml(detail.ref_id)}</strong>
                <span>${escapeHtml(detail.note || detail.source)}</span>
              </button>
              <p class="evidence-excerpt">${escapeHtml(detail.excerpt)}</p>
            </div>
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
      <p class="muted">已同步高亮相关节点和关系。点击图谱空白处可恢复默认视图。</p>
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
function renderGraph(nodes = [], edges = []) {
  const normalized = normalizeGraph(nodes, edges);
  const signature = JSON.stringify({
    nodes: normalized.nodes.map((node) => node.id),
    links: normalized.links.map((link) => link.key),
  });
  state.graphData = normalized;

  if (!normalized.nodes.length) {
    els.graphCanvas.className = "graph-shell empty";
    els.graphCanvas.textContent = COPY.empty.graph;
    clearGraphSelection();
    renderGraphInspectorDefault();
    return;
  }

  if (signature === state.graphSignature && state.graphInstance) {
    if (!restoreGraphSelection()) {
      renderGraphInspectorDefault();
      applyGraphHighlight();
    }
    return;
  }

  state.graphSignature = signature;
  els.graphCanvas.className = "graph-shell";
  els.graphCanvas.innerHTML = "";

  if (typeof ForceGraph3D !== "function") {
    els.graphCanvas.className = "graph-shell empty";
    els.graphCanvas.textContent = "3D 图谱组件加载失败。";
    renderGraphInspectorDefault();
    return;
  }

  if (state.graphInstance && typeof state.graphInstance._destructor === "function") {
    state.graphInstance._destructor();
  }

  const width = Math.max(480, els.graphCanvas.clientWidth - 24);
  const height = Math.max(560, els.graphCanvas.clientHeight - 24);
  const palette = graphPalette();
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
    .linkColor(() => palette.defaultLink)
    .linkWidth((link) => 2.2 + Number(link.strength || 0.5) * 1.1)
    .linkOpacity(0.72)
    .linkDirectionalParticles(1)
    .linkDirectionalParticleWidth(2.8)
    .d3AlphaDecay(0.02)
    .cooldownTicks(180)
    .graphData(state.graphData)
    .onNodeClick((node) => selectNodeById(node.id))
    .onLinkClick((link) => selectLink(link))
    .onBackgroundClick(() => clearGraphSelection())
    .onEngineStop(() => state.graphInstance && state.graphInstance.zoomToFit(500, 60));

  if (!restoreGraphSelection()) {
    renderGraphInspectorDefault();
    applyGraphHighlight();
  }
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
      <div class="persona-badge">${escapeHtml((profile.codename || profile.agent_name).slice(0, 2).toUpperCase())}</div>
      <div>
        <strong>${escapeHtml(profile.codename)}</strong>
        <div class="muted">${escapeHtml(profile.agent_name)} / ${escapeHtml(profile.role)}</div>
      </div>
    </div>
    <div class="persona-body">
      <p class="persona-summary">${escapeHtml(profile.current_focus || "")}</p>
      <div class="persona-state">${escapeHtml(profile.disposition || "")}</div>
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
  if (!profiles.length) return;
  if (els.agentRoot.classList.contains("empty")) {
    els.agentRoot.className = "grid-two";
    els.agentRoot.innerHTML = "";
  }
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
    <ul>${(turn.agent_step.findings || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <div class="chips">${(turn.agent_step.focus_refs || [])
      .map((ref) => `<button class="pill link-pill" data-ref-id="${escapeHtml(ref)}">${escapeHtml(ref)}</button>`)
      .join("")}</div>
    <div class="muted">confidence: ${escapeHtml(Number(turn.agent_step.confidence || 0).toFixed(2))}</div>
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
  els.agentDialogue.scrollTop = els.agentDialogue.scrollHeight;
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
    await sleep(140);
  }
}

function getFallbackPanels(finalResult) {
  return [
    {
      panel_id: "goal_response",
      title: "目标回答",
      panel_type: "goal",
      summary: "点对点回应当前分析目标。",
      body: finalResult.goal_response || finalResult.verdict_summary || finalResult.case_explanation,
      items: [],
      evidence_refs: [],
    },
    {
      panel_id: "analysis",
      title: "分析解释",
      panel_type: "analysis",
      summary: "主解释与综合判断。",
      body: finalResult.case_explanation,
      items: [finalResult.verdict_summary],
      evidence_refs: [],
    },
    {
      panel_id: "ranking",
      title: "关键对象排序",
      panel_type: "ranking",
      summary: "关键对象及其驱动链。",
      body: finalResult.verdict_summary,
      items: (finalResult.suspect_rankings || []).map((item, index) => `${index + 1}. ${item.name} | ${item.role} | ${item.motive}`),
      evidence_refs: [],
    },
    {
      panel_id: "timeline",
      title: "回溯时间线",
      panel_type: "timeline",
      summary: "按证据重建形成过程。",
      body: "",
      items: (finalResult.reenactment_timeline || []).map((item) => `${item.order}. ${item.time_hint} | ${item.event}`),
      evidence_refs: [],
    },
    {
      panel_id: "evidence",
      title: "证据与不确定性",
      panel_type: "evidence",
      summary: "支持点与未决问题。",
      body: "",
      items: [...(finalResult.evidence_notes || []), ...(finalResult.uncertainties || [])],
      evidence_refs: [],
    },
  ];
}

function renderResults(finalResult) {
  const panels = (finalResult.output_panels && finalResult.output_panels.length ? finalResult.output_panels : getFallbackPanels(finalResult)).slice(0, 6);
  els.resultRoot.className = "result-grid";
  els.resultRoot.innerHTML = panels
    .map(
      (panel) => `
        <article class="result-card result-scroll-card" data-panel-id="${escapeHtml(panel.panel_id)}">
          <div class="card-head">
            <h3>${escapeHtml(panel.title)}</h3>
            <span class="muted">${escapeHtml(panel.summary || panel.panel_type || "")}</span>
          </div>
          <div class="scroll-pane">
            ${panel.body ? `<p class="rich-text">${escapeHtmlWithBreaks(panel.body)}</p>` : ""}
            ${(panel.items || []).length ? `<ul>${panel.items.map((item) => `<li class="rich-text">${escapeHtmlWithBreaks(item)}</li>`).join("")}</ul>` : '<p class="muted">暂无补充内容。</p>'}
          </div>
        </article>
      `,
    )
    .join("");
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
  appendRuntimeMessage("info", "模型配置", payload.enabled ? "模型配置已保存并启用。" : "模型配置已保存，当前使用规则链路。");
}

async function loadSample() {
  const sample = await fetchJson("/api/case-sample");
  els.rawText.value = sample.seed_text;
  els.expectedOutcome.value = sample.expected_outcome;
  setStatus(`样例已载入：${sample.title}`);
  appendRuntimeMessage("info", "样例加载", `已加载样例：${sample.title}`);
}

function buildInitialSnapshotResponse(snapshot) {
  renderPipeline(snapshot.pipeline || []);
  renderDocument(snapshot.document, snapshot.evidence_items || [], snapshot.expected_outcome, snapshot.extracted_text || "");
  if (els.collaborationRounds && Number.isFinite(Number(snapshot.collaboration_rounds))) {
    els.collaborationRounds.value = String(snapshot.collaboration_rounds);
  }
  els.modelBadge.textContent = snapshot.model_status || "preparing";
  setStatus(snapshot.status_text || "任务已创建。");
}

function mergeSnapshot(snapshot) {
  state.parseData = snapshot;
  renderPipeline(snapshot.pipeline || []);
  renderDocument(snapshot.document, snapshot.evidence_items || [], snapshot.expected_outcome, snapshot.extracted_text || "");
  if (els.collaborationRounds && Number.isFinite(Number(snapshot.collaboration_rounds))) {
    els.collaborationRounds.value = String(snapshot.collaboration_rounds);
  }
  els.modelBadge.textContent = snapshot.model_status || "running";
  setStatus(snapshot.status_text || snapshot.status || "处理中");

  if ((snapshot.graph_nodes || []).length) {
    renderGraph(snapshot.graph_nodes, snapshot.graph_edges || []);
  }
  if ((snapshot.agent_profiles || []).length) {
    renderAgentProfiles(snapshot.agent_profiles);
  }

  const newSteps = (snapshot.agents || []).slice(state.agentSteps.length);
  for (const step of newSteps) {
    if (!state.renderedRounds.has(step.round_index)) {
      appendSystemDialogue(`第 ${step.round_index} 轮协作开始`, step.round_index);
      state.renderedRounds.add(step.round_index);
    }
    renderAgentTurn({
      agent_profile: (snapshot.agent_profiles || []).find((item) => item.agent_name === step.agent_name) || {},
      agent_step: step,
      round_index: step.round_index,
    });
    state.agentSteps.push(step);
    setActiveAgent(step.agent_name);
  }

  const newDialogue = (snapshot.agent_dialogue || []).slice(state.dialogueItems.length);
  if (newDialogue.length) {
    state.dialogueItems.push(...newDialogue);
    playDialogueItems(newDialogue);
  }

  if (snapshot.final_result && !state.finalRendered) {
    renderResults(snapshot.final_result);
    state.finalRendered = true;
    setActiveAgent("");
  }
}

async function pollSession(sessionId, token, consecutiveFailures = 0) {
  if (token !== state.pollToken || sessionId !== state.sessionId) return;
  try {
    const snapshot = await fetchJson(`/api/case-session/${sessionId}`, { meta: { skipHealthCheck: true } });
    mergeSnapshot(snapshot);
    if (["completed", "failed"].includes(snapshot.status)) {
      if (snapshot.status === "failed") {
        els.pipelineRoot.className = "pipeline";
        els.pipelineRoot.innerHTML += `<article class="pipeline-step fallback"><strong>错误</strong><p>${escapeHtml(snapshot.error || "任务执行失败")}</p></article>`;
        appendRuntimeMessage("error", "会话执行失败", snapshot.error || "任务执行失败");
      } else {
        appendRuntimeMessage("info", "分析完成", snapshot.status_text || "分析流程已结束。");
      }
      return;
    }
    state.pollTimer = window.setTimeout(() => pollSession(sessionId, token, 0), 1100);
  } catch (error) {
    const nextFailures = consecutiveFailures + 1;
    setStatus(`正在等待服务继续返回结果（第 ${nextFailures} 次重试）`);
    if (nextFailures === 1 || nextFailures % 4 === 0) {
      appendRuntimeMessage("warn", "轮询重试", `会话 ${sessionId} 第 ${nextFailures} 次轮询失败：${String(error.message || error)}`);
    }
    state.pollTimer = window.setTimeout(() => pollSession(sessionId, token, nextFailures), Math.min(3000, 1000 + nextFailures * 300));
  }
}

async function runWorkflow() {
  resetWorkspace();
  setStatus("正在创建分析会话");
  els.modelBadge.textContent = "preparing";
  appendRuntimeMessage("info", "任务启动", "正在提交分析材料并创建会话。");

  const formData = new FormData();
  formData.append("expected_outcome", els.expectedOutcome.value.trim() || "请重建这份材料所指向的形成链条。");
  formData.append("collaboration_rounds", String(Math.max(1, Math.min(6, Number(els.collaborationRounds?.value || 2) || 2))));
  formData.append("raw_text", els.rawText.value.trim());
  const file = els.fileInput.files[0];
  if (file) formData.append("file", file);

  try {
    const snapshot = await fetchJson("/api/case-session/start", { method: "POST", body: formData });
    state.sessionId = snapshot.session_id;
    buildInitialSnapshotResponse(snapshot);
    appendRuntimeMessage("info", "会话创建成功", `session_id=${snapshot.session_id}，协作轮数=${snapshot.collaboration_rounds ?? els.collaborationRounds?.value ?? 2}`);
    const token = state.pollToken + 1;
    state.pollToken = token;
    pollSession(snapshot.session_id, token, 0);
  } catch (error) {
    setStatus("任务启动失败");
    els.pipelineRoot.className = "pipeline";
    els.pipelineRoot.innerHTML = `<article class="pipeline-step fallback"><strong>错误</strong><p>${escapeHtml(String(error.message).slice(0, 500))}</p></article>`;
    appendRuntimeMessage("error", "任务启动失败", String(error.message || error).slice(0, 1000));
  }
}
async function bootstrap() {
  mountThemeToggle();
  renderRuntimeConsole();
  await checkApiHealth({ force: true });
  try {
    const design = await fetchJson("/api/design");
    els.designNotes.innerHTML = [...design.borrowed_from_mirofish, ...design.rewritten_for_backtrace]
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    await loadConfig();
  } catch (error) {
    appendRuntimeMessage("error", "页面初始化失败", String(error.message || error).slice(0, 1000));
  }
}

function applyTheme(theme, persist = true) {
  state.theme = THEME_ORDER.includes(theme) ? theme : "sky";
  document.documentElement.dataset.theme = state.theme;
  document.querySelectorAll("[data-theme-option]").forEach((button) => {
    button.classList.toggle("active", button.dataset.themeOption === state.theme);
  });
  if (state.graphData.nodes.length) {
    state.graphData.nodes.forEach((node) => {
      node.color = nodeColor(node);
    });
    if (state.graphInstance) {
      state.graphInstance.graphData(state.graphData);
      if (!restoreGraphSelection()) {
        applyGraphHighlight();
      }
    }
  }
  if (persist) {
    window.localStorage.setItem("salmon-theme", state.theme);
  }
}

function mountThemeToggle() {
  const host = document.querySelector(".brand-line");
  if (!host || document.getElementById("themeSwitch")) return;
  const wrap = document.createElement("div");
  wrap.id = "themeSwitch";
  wrap.className = "theme-switch";
  wrap.innerHTML = THEME_ORDER.map((theme) => `<button type="button" class="ghost small theme-option" data-theme-option="${escapeHtml(theme)}">${escapeHtml(THEME_LABELS[theme])}</button>`).join("");
  wrap.querySelectorAll("[data-theme-option]").forEach((button) => {
    button.addEventListener("click", () => applyTheme(button.dataset.themeOption || "sky"));
  });
  host.appendChild(wrap);
  applyTheme(window.localStorage.getItem("salmon-theme") || "sky", false);
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
