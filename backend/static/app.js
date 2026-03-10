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

let graphInstance = null;

const stepLabels = {
  parse: { title: "材料解析", detail: "读取文件并抽出可分析文本。" },
  graph: { title: "关系图谱", detail: "先展示人物、事件与线索结构。" },
  reason: { title: "多智能体回溯", detail: "让多个角色交叉验证作案机制。" },
  result: { title: "综合裁决", detail: "输出案情解释、嫌疑人排序和重演时间线。" },
};

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
  els.pipelineRoot.className = "pipeline empty";
  els.pipelineRoot.textContent = "这里会按顺序展示解析、图谱、智能体和结果阶段。";
  els.documentRoot.className = "document empty";
  els.documentRoot.textContent = "还没有解析到文档。";
  els.graphCanvas.className = "graph-shell empty";
  els.graphCanvas.textContent = "图谱尚未生成。";
  els.graphInspector.className = "inspector empty";
  els.graphInspector.textContent = "点击节点或连线后，这里会显示详细信息。";
  els.agentRoot.className = "grid-two empty";
  els.agentRoot.textContent = "智能体卡片会逐步更新。";
  els.agentDialogue.className = "dialogue-feed empty";
  els.agentDialogue.textContent = "这里会动态展示智能体之间的交互过程。";
  els.resultRoot.className = "result-grid empty";
  els.resultRoot.textContent = "最终输出会显示在这里。";
}

function pipelineText(step) {
  const local = stepLabels[step.step_id] || {};
  return {
    title: local.title || step.title,
    detail: local.detail || step.detail,
  };
}

function renderPipeline(steps) {
  els.pipelineRoot.className = "pipeline";
  els.pipelineRoot.innerHTML = steps
    .map((step) => {
      const copy = pipelineText(step);
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
      <p><strong>目标：</strong>${expectedOutcome}</p>
      <p>${document.extracted_preview}</p>
    </article>
    <article class="result-card">
      <strong>高优先级线索</strong>
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
        <p>${payload.summary || "暂无摘要"}</p>
        <dl>
          <div><dt>node_id</dt><dd>${payload.node_id}</dd></div>
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
      <p>${payload.evidence || "暂无说明"}</p>
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
  els.graphInspector.textContent = "点击节点或连线后，这里会显示详细信息。";

  if (!nodes.length) {
    els.graphCanvas.classList.add("empty");
    els.graphCanvas.textContent = "没有足够节点可用于生成图谱。";
    return;
  }

  if (typeof ForceGraph3D !== "function") {
    els.graphCanvas.classList.add("empty");
    els.graphCanvas.textContent = "3D 图谱组件加载失败。";
    return;
  }

  const data = {
    nodes: nodes.map((node) => ({ ...node, color: nodeColor(node), val: Math.max(4, (node.suspicion_score || 10) / 10) })),
    links: edges.map((edge) => ({ ...edge })),
  };

  graphInstance = ForceGraph3D()(els.graphCanvas)
    .backgroundColor("rgba(255,255,255,0)")
    .nodeLabel((node) => `${node.label}<br/>${node.node_type}`)
    .nodeColor((node) => node.color)
    .nodeVal((node) => node.val)
    .linkColor(() => "rgba(29,26,24,0.18)")
    .linkWidth((link) => 1 + Number(link.strength || 0.5))
    .linkOpacity(0.65)
    .cooldownTicks(120)
    .graphData(data)
    .onNodeClick((node) => renderInspector("node", node))
    .onLinkClick((link) => renderInspector("link", link));

  setTimeout(() => {
    graphInstance.zoomToFit(600, 60);
  }, 500);
}

function renderAgentCards(agents) {
  els.agentRoot.className = "grid-two";
  els.agentRoot.innerHTML = agents
    .map(
      (agent) => `
        <article class="agent-card">
          <strong>${agent.agent_name}</strong>
          <div class="muted">${agent.purpose}</div>
          <p>置信度：${Math.round(agent.confidence * 100)}%</p>
          <ul>${agent.findings.map((item) => `<li>${item}</li>`).join("")}</ul>
        </article>
      `
    )
    .join("");
}

function renderPendingAgents() {
  const placeholders = ["Evidence Agent", "Relationship Agent", "Suspicion Agent", "Reconstruction Agent", "Judge Agent"];
  els.agentRoot.className = "grid-two";
  els.agentRoot.innerHTML = placeholders
    .map(
      (name) => `
        <article class="agent-card">
          <strong>${name}</strong>
          <div class="muted">等待推演结果...</div>
          <p>正在准备观点</p>
        </article>
      `
    )
    .join("");
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
    await new Promise((resolve) => setTimeout(resolve, 260));
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
      <p><strong>裁决摘要：</strong>${finalResult.verdict_summary}</p>
    </article>
    <article class="result-card">
      <h3>证据说明</h3>
      <ul>${finalResult.evidence_notes.map((item) => `<li>${item}</li>`).join("")}</ul>
      <h3>不确定性</h3>
      <ul>${finalResult.uncertainties.map((item) => `<li>${item}</li>`).join("")}</ul>
    </article>
    <article class="result-card">
      <h3>嫌疑人排序</h3>
      <div class="ranking-table">${rankingRows || "<p>暂无排序。</p>"}</div>
    </article>
    <article class="result-card">
      <h3>案情重演时间线</h3>
      <div class="timeline-list">${timelineRows || "<p>暂无时间线。</p>"}</div>
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
    : "当前没有 API Key，将自动走规则引擎。";
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
  els.configState.textContent = payload.enabled ? "模型配置已保存，后续会优先调用远程模型。" : "模型配置已保存，但当前处于关闭状态。";
}

async function loadSample() {
  const sample = await fetchJson("/api/case-sample");
  els.rawText.value = sample.seed_text;
  els.expectedOutcome.value = sample.expected_outcome;
  setStatus(`已加载样例：${sample.title}`);
}

async function runWorkflow() {
  resetWorkspace();
  setStatus("正在解析材料...");
  els.modelBadge.textContent = "parsing";

  const formData = new FormData();
  formData.append("expected_outcome", els.expectedOutcome.value.trim() || "请重建这起案件的形成链条。");
  formData.append("raw_text", els.rawText.value.trim());
  const file = els.fileInput.files[0];
  if (file) {
    formData.append("file", file);
  }

  try {
    const parseData = await fetchJson("/api/case-parse", { method: "POST", body: formData });
    renderPipeline(parseData.pipeline);
    renderDocument(parseData.document, parseData.evidence_items, parseData.expected_outcome);
    renderGraph(parseData.graph_nodes, parseData.graph_edges);
    renderPendingAgents();
    setStatus("图谱已生成，正在执行多智能体回溯...");
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
    renderAgentCards(reasonData.agents);
    renderResults(reasonData.final_result);
    setStatus("智能体回溯完成，正在展示交互过程...");
    await playDialogue(reasonData.agent_dialogue || []);
    setStatus("案情重演完成");
  } catch (error) {
    setStatus("运行失败");
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

document.getElementById("saveConfig").addEventListener("click", saveConfig);
document.getElementById("loadSample").addEventListener("click", loadSample);
document.getElementById("runWorkflow").addEventListener("click", runWorkflow);

bootstrap();
