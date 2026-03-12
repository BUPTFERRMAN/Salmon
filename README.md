# Salmon

<p align="center">
  <img src="backend/static/logo.png" alt="Salmon Logo" width="180" />
</p>

**不是预测未来，而是重建过去。**

Salmon 是一个面向案件回放、历史回溯与因果链分析的多智能体重建工作空间。  
它把零散材料转成结构化证据，再通过多智能体反向推理，重建“结果如何形成”的过程。

## 为什么是 Salmon

- `Reverse-first`：从结果逆推成因，而不是从目标正推未来。
- `Evidence-constrained`：每条解释路径都绑定证据节点与反证信息。
- `Multi-hypothesis`：默认给出竞争性解释，而不是单一路径。
- `Replay-oriented`：输出可复盘、可质疑、可重演的形成链。

## 分阶段回溯流程

1. `Document Parsing`  
   解析 PDF / TXT / MD，提取人物、事件、时间与关键线索。
2. `Graph Construction`  
   构建人物-事件-线索关系图和候选因果链。
3. `Multi-Agent Reverse Reasoning`  
   多角色 Agent 围绕证据、动机、疑点和路径展开协作与交叉校验。
4. `Final Synthesis`  
   输出主路径、备选路径、关键证据、不确定性与缺证点。

## 技术亮点

### 1) Reverse-First Multi-Agent Architecture
以“回溯重建”为中心，而非“未来规划”为中心。

### 2) Evidence-Constrained Reconstruction
解释必须有证据锚点，并结合反证信息评估可信度。

### 3) Graph-Native Reasoning
将文本转化为图结构，便于发现隐性耦合、角色变化和关键前置条件。

### 4) Multi-Hypothesis, Not Single Answer
并行生成多条解释路径，展示各自强弱与置信度。

### 5) From Fragments to Replay
从碎片到重演，重建事件的完整演化过程。

## 当前能力

- 解析文本型 PDF / TXT / Markdown 材料。
- 构建可交互的人物-事件-线索图谱。
- 支持五类专长代理协作：
  - `Evidence Agent`
  - `Relationship Agent`
  - `Suspicion Agent`
  - `Reconstruction Agent`
  - `Judge Agent`
- 输出按用户目标动态组织（非固定模板）：
  - 因果路径与关键转折点
  - 竞争性解释及证据/反证
  - 不确定性与置信度标注
  - 你指定格式的报告结构（如重演叙述、角色分析、时间线、缺口清单）

## 示例场景

### 示例 1：智能侦探 - 案情回溯

- [视频演示：点击跳转到 Bilibili](https://www.bilibili.com/video/BV1iJckzYEnF/?spm_id_from=333.1387.homepage.video_card.click&vd_source=089e5b874bf4827db5f814a7206ee42e)
- [案情结果：《巴斯克维尔的猎犬》.txt](examples/example-1-case-backtrace/案情结果：《巴斯克维尔的猎犬》.txt)
- [案情结果：《斑点带子案》.txt](examples/example-1-case-backtrace/案情结果：《斑点带子案》.txt)
- [案情问题.txt](examples/example-1-case-backtrace/案情问题.txt)
- [案情线索：《巴斯克维尔的猎犬》.txt](examples/example-1-case-backtrace/案情线索：《巴斯克维尔的猎犬》.txt)
- [案情线索：《斑点带子案》.txt](examples/example-1-case-backtrace/案情线索：《斑点带子案》.txt)

### 示例 2：聊天助手 - 恋爱分析

- [视频演示：点击跳转到 Bilibili](https://www.bilibili.com/video/BV1wxcrz6Eg1/)
- [情侣聊天.txt](examples/example-2-love-chat/情侣聊天.txt)
- [情侣聊天问题.txt](examples/example-2-love-chat/情侣聊天问题.txt)

### 示例 3：反思者 - 舆情归因

- [航空案例舆情线索.txt](examples/example-3-public-opinion/航空案例舆情线索.txt)

## 模型接入

后端采用 OpenAI 兼容 API 模式。默认本地配置为 DeepSeek：

- `provider_name = DeepSeek`
- `base_url = https://api.deepseek.com`
- `model = deepseek-reasoner`

若工作区根目录存在 `api.txt`，Salmon 会自动读取 API Key。

## 运行方式

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

打开 [http://127.0.0.1:8010](http://127.0.0.1:8010)

## API

- `GET /api/model-config`
- `POST /api/model-config`
- `POST /api/case-parse`
- `POST /api/case-reason`
- `POST /api/case-workflow`

## 备注

- 当前 PDF 解析器针对文本型 PDF，未包含扫描件 OCR。
- 当前 Agent 层为角色化分析工作流，并非完整社会仿真系统。
- 图谱视图支持交互式节点与关系检查。
