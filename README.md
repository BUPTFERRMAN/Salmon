# BackTrace Demo

BackTrace 现在已经从“样例页”升级成了一个可运行的案情重演工作台。

它当前聚焦你最先要做的场景：

- 上传 `PDF / TXT / MD`
- 或直接粘贴案情文本
- 先解析文档
- 再构建人物 / 事件 / 线索关系图谱
- 再组织多个回溯代理
- 最后输出案情解释、嫌疑人排序、案情重演时间线和证据说明

## 当前实现了什么

### 1. 文档输入链路

- 支持文件上传
- 支持直接文本输入
- 支持 PDF 文本提取

说明：
当前 PDF 解析基于 `PyMuPDF`，适合文本型 PDF。
如果 PDF 是扫描件、图片件，或者字体嵌入异常，中文提取质量会下降，这一类后续需要补 OCR。

### 2. 模型接入页

前端页面已经支持填写：

- `Provider Name`
- `Base URL`
- `Model`
- `API Key`
- `是否启用模型`

接入方式采用 OpenAI 兼容接口。
当前默认已经按 DeepSeek 推理模型预设：

- `provider_name = DeepSeek`
- `base_url = https://api.deepseek.com`
- `model = deepseek-reasoner`

如果工作区根目录存在 `api.txt`，系统会自动读取其中的 API Key 并初始化本地模型配置。
这意味着后续你无论接 DeepSeek、OpenAI 兼容网关、Ollama 中转层，还是自建模型服务，都不用改前端协议。

### 3. 案情重演工作流

当前工作流是：

1. 材料解析
2. 大模型结构化分析（如果已接模型）
3. 关系图谱构建
4. 多代理回溯
5. 结果裁决

现在已经有 5 类代理输出：

- `Evidence Agent`
- `Relationship Agent`
- `Suspicion Agent`
- `Reconstruction Agent`
- `Judge Agent`

### 4. 最终输出

页面当前会展示：

- 文档摘要
- 过程追踪
- 图谱可视化
- 代理过程卡片
- 案情解释
- 嫌疑人排序
- 案情重演时间线
- 证据说明
- 不确定性提醒

## 为什么这版没有直接照搬 MiroFish

`MiroFish` 的长处在未来社会仿真，核心依赖是：

- Zep 图谱
- OASIS / CAMEL 大规模 agent 仿真
- 报告代理

BackTrace 当前阶段更重要的是先证明：

- 文档能不能被稳定解析
- 案件能不能被结构化
- 结论能不能保留竞争解释和证据边界

所以这版采用的是：

- MiroFish 的分层工作流思路
- BackTrace 自己的“逆向因果回溯”引擎

等案情重演案例跑稳之后，再决定是否把 Zep 图谱层和更强的多体仿真层接进来。

## 运行方式

```bash
cd backtrace-demo/backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8010
```

打开：

[http://127.0.0.1:8010](http://127.0.0.1:8010)

## API

已经可用的关键接口：

- `GET /api/model-config`
- `POST /api/model-config`
- `POST /api/case-workflow`
- `GET /api/case-sample`
- `GET /api/design`

## 当前边界

- 没接模型时，会走规则引擎兜底。
- 接了模型后，会先尝试用模型做结构化分析，再由本地流程组织图谱和代理结果。
- 当前还没有 OCR。
- 当前还没有持久化案件库。
- 当前还没有引用级 evidence span 高亮。

## 下一步最值得继续做的事

1. 用你真实准备开源的案情材料替换现在的样例。
2. 接入你准备本地调试使用的模型接口。
3. 给时间线和嫌疑人排序补上“原文证据定位”。
4. 第二阶段再考虑接入图数据库或 Zep 图谱层。
