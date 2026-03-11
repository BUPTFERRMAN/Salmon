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

const AGENT_PERSONAS = [
  {
    agent_name: "Evidence Agent",
    codename: "Trace Lens",
    badge: "EV",
    accent: "#b44d28",
    role: "证据审计",
    summary: "负责提取高风险线索、识别证据断点与异常模式。",
  },
  {
    agent_name: "Relationship Agent",
    codename: "Link Weaver",
    badge: "RL",
    accent: "#254d59",
    role: "关系建模",
    summary: "负责梳理人物关系、利益链条与隐性依附结构。",
  },
  {
    agent_name: "Suspicion Agent",
    codename: "Rank Signal",
    badge: "SP",
    accent: "#8b5e34",
    role: "嫌疑排序",
    summary: "基于动机、手段、机会与线索覆盖度输出排序。",
  },
  {
    agent_name: "Reconstruction Agent",
    codename: "Time Thread",
    badge: "RC",
    accent: "#3e6b6f",
    role: "因果拼接",
    summary: "负责回溯作案机制、重组事件链条与时间线。",
  },
  {
    agent_name: "Judge Agent",
    codename: "Final Frame",
    badge: "JG",
    accent: "#c59c3d",
    role: "综合裁决",
    summary: "负责整合多方观点，输出主解释与关键不确定性。",
  },
];

const STEP_LABELS = {
  parse: { title: "材料解析", detail: "抽取可分析文本、基础事实与结构化片段。" },
  graph: { title: "关系图谱", detail: "构建人物、事件与线索的可交互关系视图。" },
  reason: { title: "多智能体推演", detail: "执行角色分工、证据交叉验证与回溯推演。" },
  result: { title: "综合输出", detail: "生成案情解释、嫌疑人排序与证据化时间线。" },
};

let graphInstance = null;

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
  if (graphInstance && typeof graphInstance._destructor === "function") {
    graphInstance._destructor();
  }
  graphInstance = null;

  els.pipelineRoot.className = "pipeline empty";
  els.pipelineRoot.textContent = "任务启动后，这里会依次展示解析、图谱、智能体与结果阶段。";
  els.documentRoot.className = "document empty";
  els.documentRoot.textContent = "尚未载入材料。";
  els.graphCanvas.className = "graph-shell empty";
  els.graphCanvas.textContent = "图谱尚未生成。";
  els.graphInspector.className = "inspector empty";
  els.graphInspector.textContent = "点击节点或关系后，这里将显示详细属性与证据说明。";
  els.agentRoot.className = "grid-two empty";
  els.agentRoot.textContent = "智能体角色将在这里初始化。";
  els.agentDialogue.className = "dialogue-feed empty";
  els.agentDialogue.textContent = "智能体交互日志将在这里动态播放。";
  els.resultRoot.className = "result-grid empty";
  els.resultRoot.textContent = "最终分析结果将在这里生成。";
}

function localizeStep(step) {
  return STEP_LABELS[step.step_id] || { title: step.title, detail: step.detail };
}

function renderPipeline(steps) {
  els.pipelineRoot.className = "pipeline";
  els.pipelineRoot.innerHTML = steps
    .map((step) => {
      const copy = localizeStep(step);
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
        <span class="pill">类型：${document.source_type}</span>
        <span class="pill">字符数：${document.character_count}</span>
        <span class="pill">页数：${document.page_count ?? "未统计"}</span>
      </div>
      <p><strong>分析目标：</strong>${expectedOutcome}</p>
      <p>${document.extracted_preview}</p>
    </article>
    <article class="result-card">
      <strong>关键线索预览</strong>
      <ul>
        ${evidenceItems
          .slice(0, 5)
          .map((item) => `<li>${item.label}（风险 ${item.risk_score}）: ${item.detail}</li>`)
          .join("")}
      </ul>
    </article>
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
      </dl>
    </article>
  `;
}

function nodeColor(node) {
  if (node.node_type === "actor") return "#b44d28";
  if (node.node_type === "event") return "#254d59";
  return "#c59c3d";
}

function renderGraph(nodes, edges) {
  els.graphCanvas.className = "graph-shell";
  els.graphCanvas.innerHTML = "";
  els.graphInspector.className = "inspector empty";
  els.graphInspector.textContent = "点击节点或关系后，这里将显示详细属性与证据说明。";

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

  if (graphInstance && typeof graphInstance._destructor === "function") {
    graphInstance._destructor();
  }

  const width = Math.max(420, els.graphCanvas.clientWidth - 24);
  const height = Math.max(440, els.graphCanvas.clientHeight - 24);

  const data = {
    nodes: nodes.map((node) => ({
      ...node,
      id: node.node_id,
      color: nodeColor(node),
      val: Math.max(6, (Number(node.suspicion_score) || 20) / 8),
    })),
    links: edges.map((edge) => ({ ...edge })),
  };

  graphInstance = ForceGraph3D()(els.graphCanvas)
    .width(width)
    .height(height)
    .backgroundColor("rgba(255,255,255,0)")
    .nodeId("id")
    .linkSource("source")
    .linkTarget("target")
    .showNavInfo(false)
    .nodeLabel((node) => `${node.label}<br/>${node.node_type}`)
    .nodeColor((node) => node.color)
    .nodeVal((node) => node.val)
    .nodeOpacity(0.92)
    .linkColor(() => "rgba(29,26,24,0.22)")
    .linkWidth((link) => 1.5 + Number(link.strength || 0.5))
    .linkOpacity(0.72)
    .linkDirectionalParticles(1)
    .linkDirectionalParticleWidth(1.8)
    .cooldownTicks(160)
    .graphData(data)
    .onNodeClick((node) => renderInspector("node", node))
    .onLinkClick((link) => renderInspector("link", link))
    .onEngineStop(() => {
      if (graphInstance) {
        graphInstance.zoomToFit(400, 70);
      }
    });
}

function renderAgentPersonas(mode = "idle", agents = []) {
  const findingsByName = new Map(agents.map((agent) => [agent.agent_name, agent]));
  els.agentRoot.className = "grid-two";
  els.agentRoot.innerHTML = AGENT_PERSONAS.map((persona) => {
    const result = findingsByName.get(persona.agent_name);
    const statusLabel = mode === "pending" ? "待机完成，等待推演" : result ? "已完成本轮分析" : "角色初始化";
    const list = result
      ? `<ul>${result.findings.map((item) => `<li>${item}</li>`).join("")}</ul>`
      : `<p class="muted">${persona.summary}</p>`;
    return `
      <article class="agent-card persona-card ${result ? "active" : ""}" style="--agent-accent:${persona.accent}">
        <div class="persona-head">
          <div class="persona-badge">${persona.badge}</div>
          <div>
            <strong>${persona.codename}</strong>
            <div class="muted">${persona.agent_name} / ${persona.role}</div>
          </div>
        </div>
        <p class="persona-summary">${persona.summary}</p>
        <div class="persona-state">${statusLabel}</div>
        ${list}
      </article>
    `;
  }).join("");
}

async function playDialogue(dialogue) {
  els.agentDialogue.className = "dialogue-feed";
  els.agentDialogue.innerHTML = "";
  for (const item of dialogue) {
    const wrapper = document.createElement("article");
    wrapper.className = "dialogue-item";
    wrapper.innerHTML = `
      <div class="dialogue-head">
        <span>${item.speaker}</span>
        <span>${item.audience}</span>
      </div>
      <p>${item.message}</p>
    `;
    els.agentDialogue.appendChild(wrapper);
    await new Promise((resolve) => setTimeout(resolve, 280));
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
          <p><strong>动机：</strong>${item.motive}</p>
          <p><strong>手段：</strong>${item.means}</p>
          <p><strong>机会：</strong>${item.opportunity}</p>
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
          <div class="chips">${item.evidence_refs.map((ref) => `<span class="pill">${ref}</span>`).join("")}</div>
        </article>
      `
    )
    .join("");

  els.resultRoot.className = "result-grid";
  els.resultRoot.innerHTML = `
    <article class="result-card">
      <h3>案情解释</h3>
      <p>${finalResult.case_explanation}</p>
      <p><strong>综合结论：</strong>${finalResult.verdict_summary}</p>
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
  els.configState.textContent = payload.enabled
    ? "模型配置已保存，后续任务将优先调用外部模型。"
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
  renderAgentPersonas("pending");
  setStatus("材料解析中");
  els.modelBadge.textContent = "parsing";

  const formData = new FormData();
  formData.append("expected_outcome", els.expectedOutcome.value.trim() || "请重建这起案件的形成链条。");
  formData.append("raw_text", els.rawText.value.trim());
  const file = els.fileInput.files[0];
  if (file) {
    formData.append("file", file);
  }

  try {
    const parseData = await fetchJson("/api/case-parse", {
      method: "POST",
      body: formData,
    });

    renderPipeline(parseData.pipeline);
    renderDocument(parseData.document, parseData.evidence_items, parseData.expected_outcome);
    renderGraph(parseData.graph_nodes, parseData.graph_edges);
    renderAgentPersonas("pending");
    setStatus("关系图谱已完成，正在执行多智能体推演");
    els.modelBadge.textContent = "reasoning";

    const reasonData = await fetchJson("/api/case-reason", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: parseData.extracted_text,
        document: parseData.document,
        expected_outcome: parseData.expected_outcome,
      }),
    });

    els.modelBadge.textContent = reasonData.model_status;
    renderPipeline(reasonData.pipeline);
    renderAgentPersonas("done", reasonData.agents);
    renderResults(reasonData.final_result);
    setStatus("多智能体交互回放中");
    await playDialogue(reasonData.agent_dialogue || []);
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
  renderAgentPersonas("idle");
}

document.getElementById("saveConfig").addEventListener("click", saveConfig);
document.getElementById("loadSample").addEventListener("click", loadSample);
document.getElementById("runWorkflow").addEventListener("click", runWorkflow);

bootstrap();
