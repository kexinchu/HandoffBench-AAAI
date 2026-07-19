# HandoffBench：AAAI-27 审稿与实验设计作战书

> 版本：2026-07-18。定位：以苛刻 AAAI 主会审稿人和实验设计负责人视角给出可证伪、可执行的投稿门槛。本文件不是对录用的保证；“4/5”指在实验与写作达到下述门槛后，论文有合理机会获得 **weak accept / accept**，而不是承诺评分。

## 1. 一句话裁决

**当前：高风险、有条件 GO，但尚不具备投稿证据。** 问题真实、边界清晰、能形成公开 benchmark；但仅有 README 中的设想会被认为是“结构化 JSON 比摘要好”的工程常识，且 2026 年预印本 **Handoff Debt (arXiv:2606.02875)** 构成直接 novelty collision，当前预期降至 **2–3/5（reject / weak reject）**。不能靠改名或一句“concurrent work”解决；必须逐项核验其 task unit、handoff definition、metrics、baselines、method 与实验结论，并在 related-work 表中给出 claim-level 非重合证据。只有在以下四点同时成立时才应投 AAAI-27 主会：

1. **隔离出 handoff 的因果损失**：相同轨迹、相同接收模型、相同工具与预算下，只改变边界处传递机制，并有 single-agent/no-handoff oracle；
2. **Capsule 的收益不是 schema、额外 token 或 prompt engineering 的假象**：跨模型、跨领域、跨 stressor 显著，且 provenance/checks 消融提供机制证据；
3. **Benchmark 经得起数据集审查**：任务级 train/dev/test 隔离，gold state 双人标注与一致性报告，确定性 mocked tools、版本化 traces、可执行评测器和公开代码/数据。
4. **相对 Handoff Debt 有实质、可演示的新增知识**：HandoffBench 必须以 boundary-level gold state 和 transfer/consumption error 分解为核心，并由 typing × provenance × checks 因子实验支持；若对方已覆盖这些核心点且本工作没有新的 formalism、数据或机制发现，则直接 **NO-GO**。

若 2026-07-22 前不能完成主矩阵与独立复核，或核心效应不满足第 4 节门槛，则 **NO-GO 主会**：不要用更多 cherry-picked case studies 掩盖阴性结果，可改写为 benchmark/resource workshop 或诚实的负结果论文。

### 1.1 Handoff Debt 撞题后的 48 小时 novelty gate

在任何大规模付费实验前完成逐页审计并保存表格：`their claim/evidence → our overlap → defensible delta → required experiment`。以下任一情况成立即暂停 AAAI 主会路线：

- 对方已经发布 boundary gold state benchmark，且状态类别、严格成功/回归指标与本项目基本同构；
- 对方已把 typed transfer、provenance 和 precondition checks 作为方法并有公平 structured-payload 对照；
- 我方唯一差异只是多几个领域、换模型、换框架或改 JSON 字段名；
- 无法在摘要和 introduction 第一页用一句可核验的话说明“对方回答 X，我们回答 Y”，且 Y 对 AAAI 社区本身重要。

可继续 GO 的最低差异必须至少包含两项：**(i)** 原子 gold state + evidence provenance 的公开可执行评测；**(ii)** transfer error 与 receiver consumption/reasoning error 的因果分解；**(iii)** 2×2×2 因子实验识别 typing/provenance/checks 的主效应与交互；**(iv)** corruption/counterfactual test 直接测 checkability；**(v)** 对安全关键不可逆动作的独立结论。论文不得使用“first benchmark”措辞，除非完整检索后确实成立。

## 2. 审稿人会追问的研究主张

不要把所有指标都写成贡献。主文只承诺三个可检验主张：

- **C1（现象）**：控制上游证据和下游模型后，常见 handoff 表示会产生可测的、区别于一般 agent failure 的 handoff-induced regression。
- **C2（方法）**：Executable Handoff Capsule（EHC）相对 free summary 与同字段 structured payload，提高严格任务成功率并降低安全关键 state errors。
- **C3（效率）**：EHC 相对 full history 位于更优的 reliability–token Pareto frontier；若不能同时省 token 和保可靠性，则删除“更高效”主张。

预注册主终点：**strict end-to-end task success**（所有目标满足、无禁用动作、无虚构 consent/commitment）。关键次终点：macro state F1、安全关键错误率、输入 token。其余均为诊断性指标，避免多重比较后“挑显著”。

## 3. 最小可发表证据包（MPEP）

### 3.1 Benchmark 与标注

- **至少 120 个唯一任务模板/实例族**，5 个领域各 24 个：travel repair、refund/exchange、procurement、appointment scheduling（明确非诊疗）、enterprise IT。不得把同一模板仅换名字/数值后跨 split。
- 每个任务含 2–3 个角色、固定 handoff boundary、可重放工具 trace、gold boundary state、允许/禁止动作、终局判定器；至少 40% 含不可逆或用户影响动作。
- state unit 必须原子化并带类型：goal、constraint、verified fact、open slot、tool evidence、policy status、consent、commitment、risk flag、precondition。每个 unit 有 evidence span/trace ID、criticality、允许的等价表达。
- 任务族按 **60/20/40 train/dev/test** 划分；prompt/schema 调试仅用 train/dev，test 冻结后一次性主评测。保留一个完全未见领域或至少 20 个 challenge tasks 作 OOD。
- 两位独立标注者复核全部 test gold；报告各类别 Cohen's kappa（离散标签）和 span/state F1；目标 kappa ≥ .80，分歧由第三人裁决。LLM 只能提议标注，不能充当唯一 gold 作者。
- 公开 JSON schema、任务生成来源、许可证、datasheet、评测脚本、失败 taxonomy、原始逐 run 输出、模型/日期/参数、prompt hashes；mocked API 必须确定性且带 action log。

### 3.2 必需对照

1. **No-handoff / single-agent oracle**：接收者直接看到完整既定轨迹，界定“任务本身难”与 handoff loss。
2. **Full history**：完整对话与工具 trace，不人为截断。
3. **Free summary**：固定 token budget 的自然语言交接。
4. **Structured payload**：与 EHC 相同 task-state 字段，但去掉 provenance 与 executable checks；这是最关键的公平对照。
5. **EHC**：typed state + provenance + checks。
6. 可选 shared scratchpad 只作外部效度，不得占用主文核心空间。

所有方法使用同一 upstream trace（离线 replay），同一 downstream system prompt、工具权限、采样参数和最大 token/tool-call 预算。EHC 若用额外生成/验证模型，必须将其调用、token、延迟与失败计入成本。

### 3.3 最低结果门槛

在冻结 test 上，EHC 必须同时满足：

- 相对 structured payload，strict success **绝对提升 ≥ 8 个百分点**，任务聚类的 95% CI 下界 > 0；
- 相对 free summary，安全关键错误（consent hallucination + commitment hallucination + precondition skip）**相对下降 ≥ 30%**，且绝对下降 ≥ 5 个百分点；
- 至少 **2/3 模型、4/5 领域、4/6 stressor** 方向一致；不能只靠一个弱模型或一个领域；
- 对 full history：strict success 的差值 95% CI 下界不低于预设非劣界 **−3pp**，同时中位输入 token 至少降低 **30%**；否则只可主张 reliability improvement，不可主张 Pareto 优势；
- no-handoff 与各 handoff 方法的差值给出 handoff-induced regression；若 full history 也大幅失败，必须区分接收者推理失败和 state-transfer failure。

上述阈值应在看 test 前锁定。若 EHC 对 structured payload < 5pp 且 CI 跨 0，方法贡献 **NO-GO**；可以保留 benchmark 论文，但必须证明新诊断结论，而非硬说方法有效。

## 4. 模型 × 方法 × 任务 × stressor 实验矩阵

### 4.1 主矩阵

| 轴 | 主实验水平 | 设计目的 |
|---|---|---|
| 接收模型 | 3 个不同供应商/开放性的强、中、较小模型（冻结具体版本） | 排除单模型 prompt 偶然性 |
| 交接方法 | Full History、Free Summary、Structured Payload、EHC | 4 个主方法；no-handoff 作为 oracle |
| 领域 | 5 域 × 24 tasks = 120 tasks | 每域均衡，任务是推断单位 |
| 重复 | 每个模型–方法–任务 3 个独立 seeds | 估计随机性；temperature=0 仍建议重复 API 非确定性 |
| 核心规模 | 3 × 4 × 120 × 3 = **4,320 downstream runs** | 配对比较；另加 oracle 1,080 runs |

不要对 120 tasks 再做 6 stressor 的完全笛卡尔积。每个 base task 预先分配一个 clean 版本与两个平衡的 stress variants，形成配对 challenge set；主矩阵使用 clean/自然混合，stressor 分析使用约 **60 个 base tasks × 7 条件 × 4 方法 × 2 个代表模型 × 2 seeds = 6,720 runs**。预算不足时，stressor 分析只保留 40 tasks、2 模型、1 seed，但不可削减主矩阵的模型或方法公平对照。

### 4.2 六类 stressor 与可证伪预测

| Stressor | 操作化 | 主要易损状态 | 预测 |
|---|---|---|---|
| Long distractor context | handoff 前插入 4k/12k 无关但同域文本 | constraints/evidence | full history 和 summary 退化，EHC 稳定 |
| User revision | 用户明确撤销早期日期/预算/选择 | goal/commitment | stale commitment 上升；provenance 有益 |
| Conflicting evidence | 用户陈述与后续工具结果冲突 | verified facts | evidence mutation/错误优先级上升 |
| Missing consent | action-ready 但缺明确授权 | consent/precondition | safety-critical 差异最大 |
| Multi-step evidence | 结论需连接两个工具结果 | evidence/policy | 单纯字段 schema 可能不足 |
| Irreversible action | refund/book/reset 等带确认门 | checks/risk flags | executable checks 应提供独特收益 |

每个 stressor 有 paired clean control，难度除目标扰动外保持一致。将 stressor × method interaction 作为机制检验，而不是只报每组柱状图。

## 5. 指标与统计分析计划

### 5.1 指标定义

- **State recall/precision/F1**：以 gold atomic units 为分母/匹配单元，先确定规则化与语义匹配协议；关键 state 加权结果只能作补充，主结果用 macro-F1。
- **Strict success**：确定性 predicate 全部通过且没有 forbidden action。另报 partial success，但不能替代主终点。
- **Handoff-induced regression**：对同一 task/model/seed，oracle 成功而 handoff 失败的比例；同时报告 reverse flips。
- **Safety-critical error**：每 task 是否出现 consent/commitment hallucination 或 precondition skip；不能以每 token 为分母稀释。
- **Efficiency**：输入/输出 token、handoff 生成调用、工具调用数、端到端延迟（若可稳定测）、按运行日期记录的实际成本。跨供应商价格会变化，主文优先 token/调用量。

### 5.2 推断

- 二元 strict success：主比较用 **paired cluster bootstrap**（按 task family 重采样，10,000 次）给出绝对差和 95% CI；稳健性分析用 mixed-effects logistic regression：method、model、domain、stressor 及 method×stressor 为固定效应，task family 为随机截距。
- 同一 task 的方法两两比较可附 McNemar exact test；不能把 seed 当独立任务做普通卡方检验。
- state F1/token：按 task 聚类 bootstrap；长尾 token 同时报 median、IQR 与几何均值。
- 主假设仅三项：EHC vs structured 的 strict success；EHC vs free summary 的 critical error；EHC vs full history 的 success non-inferiority + token superiority。前两项 Holm 校正；非劣检验单侧 alpha=.025。
- 报 effect size、CI 和原始分母，不以 `p<.05` 代替实质意义。按模型/域/stressor 的分析预标为 secondary，控制 FDR 或明确 exploratory。

### 5.3 功效与顺序门控

目标是检测 paired absolute improvement 8–10pp。若方法间 discordant pair 约 20–25%，McNemar 正态近似在双侧 alpha=.05、80% power 下约需 **157–245 个独立任务**；120 tasks 对 10pp 左右效应尚可但对 8pp 可能不足。由于 task-family 聚类和模型异质性，不能宣称 120 一定充分：

1. 用 30 个 dev tasks 估计 discordance，不看 frozen test；
2. 在数据收集前用模拟 mixed model 做 power curve（N=80/120/160/200，ICC=.05/.10/.20）；
3. 若对 8pp 的功效 < .80，把 test 扩至 **160–200 个独立 task families**，而不是增加 seeds；seeds 提升运行稳定性，但不能替代任务多样性；
4. 禁止依据 test p-value 随时加样本。样本量一旦锁定，只允许按预注册的无结果信息规则补齐失败 API runs。

### 5.4 成本计划

先做 2×4×30×2=480-run pilot，记录每方法真实输入/输出 token，再估算：

`总成本 = Σ(输入token×当日输入单价 + 输出token×当日输出单价 + capsule生成/验证调用 + 重试)`。

主矩阵 5,400 runs（含 oracle），另预留 10% 重试容量。建议设三级闸门：

- **Gate A（schema）**：20 tasks 上 gold evaluator 单元测试 ≥ 95%，否则不调用付费模型；
- **Gate B（signal）**：dev pilot 中 EHC 相对 structured 至少 +5pp 或 critical errors 明显下降，否则先改机制/任务，不扩大；
- **Gate C（scale）**：冻结 prompt、模型版本、数据 hash、预算后一次跑 test。

必须缓存 immutable upstream traces；对所有方法复用。任何 provider refusal/rate-limit 作为缺失原因记录，不静默重跑到成功。预算不足的削减顺序：先减 exploratory seeds/stressor tasks，再减 shared memory；绝不删除 structured payload、oracle 或跨模型验证。

## 6. 必做消融与反事实控制

按重要性排序：

1. **预注册 2×2×2 因子消融（必须，不可用三个零散 ablation 代替）**：Typing {free-form, typed} × Provenance {absent, trace-linked} × Checks {absent, executable}，共 8 cells；所有 cells 使用同一原子信息源、近似等 token、同一生成模型和下游预算。用 mixed-effects model 报三个主效应、两两交互及 typing×provenance×checks 三阶交互，task family 为随机截距；特别检验 provenance×conflicting-evidence 与 checks×irreversible-action/missing-consent。若 free-form 中嵌 provenance/checks 的实现不自然，仍需给出明确序列化规范，不能因此跳过 cell。
2. **EHC − provenance**：作为因子结果的直观切片，字段保留但去掉 trace IDs；证明来源绑定的贡献。
3. **EHC − executable checks**：作为因子结果切片，checks 变成普通文本或删除；证明 precondition enforcement 的贡献。
4. **EHC − typing**：作为因子结果切片，free text 与 typed cell 信息和 token 等量，检验结构本身。
5. **Equal-token full history/summary**：排除 EHC 只是获得更优 token budget。
6. **Gold capsule upper bound** 与 **model-generated capsule**：把 capsule construction error 与 consumption error 分开；这是定位失败归因的关键。
7. **Corrupted capsule challenge**：受控删除/篡改一个 state unit，测 receiver/checker 是否检测到；展示“executable/checkable”而不只是紧凑摘要。
8. **Receiver-only validation** vs source-only generation vs 双端验证：确定收益来自何处以及真实额外成本。
9. **字段组消融**：consent/preconditions、evidence/provenance、open slots；仅在主效应成立后做，避免组合爆炸。

完整 2×2×2 至少在 2 个模型、60 个平衡 tasks 上运行（8×2×60×2 seeds = 1,920 runs）；对 contrasts 使用同任务配对 CI 与 Holm/FDR 校正。若 provenance、checks 无主效应且在预期 stressor 上也无交互，则不能把 provenance-aware/executable 作为方法创新；在 Handoff Debt 撞题背景下，这将触发 **主会 NO-GO**，而不只是降级措辞。

## 7. Threats to validity（论文必须主动承认并缓解）

- **构念效度**：gold state 并非唯一正确内部表示；用 atomic observable predicates、等价表达规则、盲人工审计与确定性终局判定器缓解。
- **handoff 与推理混淆**：下游可能收到状态却未使用。以 gold-capsule upper bound、oracle、显式 state extraction probe 分解 transfer/consumption failure。
- **模板泄漏与伪样本量**：数值改写不是独立任务；按 template family split、按 family bootstrap/随机效应。
- **合成生态效度**：mocked APIs 和合成对话不等于真实生产。至少让领域专家审阅任务，加入 20–30 个经匿名化/许可的现实 trace-inspired cases（如无法取得真实 trace，清楚限制主张）。
- **LLM judge 偏差**：安全和成功主指标尽可能程序化；语义匹配由盲人工子集校准，报告 judge–human agreement，不使用被评模型自评。
- **模型与 API 漂移**：记录精确 model snapshot、日期、参数与响应 hash；不同日批次随机化方法顺序。
- **公平性**：EHC 可能用更多 calls、工具权限或专用 prompt；完整计费并做 equal-budget 对照。
- **污染**：新 benchmark 仍可能被模型见过生成模板或领域惯例；保留提交前才生成并冻结的 challenge set，发布生成过程与 hashes。
- **安全/伦理**：医疗域只做预约，不给医疗建议；无真实 PII；不可逆动作在 sandbox/mock API 中执行；datasheet 说明风险与许可。
- **外推边界**：结论只覆盖语言型、工具调用、2–3 agent 的 controlled handoff，不外推到开放世界长期自治、多模态或人机团队。

## 8. 预演审稿意见与评分

### 当前 README 版本：预期 2–3/5（reject / weak reject）

**优点**：问题及时且真实；边界比“泛 agent memory”清楚；可复现 benchmark 有社区价值；安全关键 state 很有意义。

**致命问题**：Handoff Debt 直接撞题使 novelty 未成立；新颖性可能只是工程 schema；没有数据与显著性；“handoff-induced”未被 oracle 隔离；synthetic tasks 容易过拟合 schema；指标多而主假设不清；EHC 可能只是更多 token/更强 prompt；与 full history 的公平成本比较未定义。

### 升到 4/5（weak accept）的硬要求

- 完成 MPEP，并公开可执行 benchmark/harness；
- 用逐 claim collision table 证明相对 Handoff Debt 的新增研究问题与证据，不以“并发工作”替代定位；
- EHC vs **同字段 structured payload** 达到预注册、跨模型的实质提升；
- typing × provenance × checks 的 2×2×2 因子结果显示至少一个与理论一致、跨模型稳定的独特机制效应/交互；
- gold capsule 与 generated capsule 分解清楚地解释失败机制；
- 至少一个令人意外、可推广的科学发现，例如：full history 在 revision/conflict 下并非上界，或 provenance 只在冲突证据/不可逆动作中起效；
- 主文 7 页内含关键矩阵、置信区间、成本和负结果，不把核心证据放 supplement；
- 相关工作精确区分 routing、memory、state tracking、multi-agent benchmark 和 workflow protocols，避免宣称“首个”除非系统检索足够支持。

### 升到 5/5（accept）的具体要求

在 4/5 基础上至少再满足三项：

- 160–200 个独立 task families 或等价高功效设计，外加 held-out domain/challenge set；
- 3 个模型家族和真实框架适配（至少两种主流 handoff API）复现实验趋势；
- EHC 对 full history 达到预设非劣且 token 降 ≥30%，形成清晰 Pareto frontier；
- 机制证据强：provenance/checks 消融与相应 stressor 有显著 interaction，corruption detection 展示可检查性；
- benchmark 至少有独立 annotator/domain reviewer，gold agreement 高，artifact 一键复现；
- 论文提供一个比“JSON 好用”更持久的形式化视角：handoff state、sufficiency、fidelity、regression 的定义，以及 transfer error 与 receiver reasoning error 的可操作分解。

若结果仅表明 EHC 胜 free summary、但不胜 structured payload，最高大概率仍是 3；若只在一个廉价小模型或 consent-heavy 人工任务上有效，也仍是 3。

## 9. 七页主文的证据布局

1. **P1 Intro**：失败案例、handoff 不是 routing、三项贡献与主结果数字。
2. **P2 Formalization/Related Work**：boundary state、sufficiency/fidelity/regression；极紧凑定位表。
3. **P3 Benchmark**：任务生成、gold schema、split、标注、判定器与伦理。
4. **P4 EHC + baselines**：算法/数据结构、provenance/check execution、公平预算。
5. **P5 Main experiments**：主矩阵、统计、strict success/state F1/critical errors。
6. **P6 Stress/ablation/cost**：interaction、gold-vs-generated、Pareto、失败案例。
7. **P7 limitations/conclusion**：外推边界、负结果、release。

参考文献最多只能占第 8–9 页；reproducibility checklist 和补充材料按官方说明另处理，但评审不必阅读 supplement，因此所有决定性结果必须在 7 页正文。

## 10. AAAI-27 官方格式、政策与时间核对

截至 2026-07-18，官方要求如下：

- AAAI-27 在 Montréal 线下举行（2027-02-16 至 02-23）；摘要截止 **2026-07-21 11:59pm UTC-12**，全文截止 **2026-07-28 11:59pm UTC-12**，补充材料/代码截止 **2026-07-31**。[AAAI-27 官方主页](https://aaai.org/conference/aaai/aaai-27/)
- 主会投稿限 **7 页 main content，总长最多 9 页；第 7 页之后只能放 references**。有 reproducibility checklist；补充材料非必读，关键证据必须在正文。[AAAI-27 Main Technical Track CFP](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
- 评审标准明确包括 significance/novelty、理论或实证 soundness、AAAI relevance、clarity、responsible research 与 reproducibility；官方更偏好开辟新问题/方向且对 AI 广泛有意义的工作，而非狭窄增量。[同一官方 CFP](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
- 作者可审慎使用生成式 AI 准备稿件，但作者对全部内容负责；不存在的引用、抄袭、近重复并行投稿和针对评审系统的 prompt injection 均可能受处罚。[同一官方 CFP](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
- 使用官方页面链接的 **AAAI-27 Author Kit**；不要沿用第三方或旧版模板。投稿前自动检查 US Letter、双栏、字体嵌入、匿名信息、页数、参考文献边界和 PDF 可读性。Author Kit 页面当前由官方 CFP 直接链接，最终以下载包内说明为准。

## 11. 最后 go/no-go checklist

提交前必须全部为“是”：

- [ ] frozen test 在 prompt/schema 锁定后才运行；
- [ ] oracle、full history、free summary、同字段 structured、EHC 五个条件齐全；
- [ ] 至少 3 模型、5 领域，任务族级统计与 CI；
- [ ] EHC 对 structured 达到预注册实质效应，不靠 cherry-pick；
- [ ] Handoff Debt 已逐页/逐 claim 审计，至少两项 substantive delta 有实验支撑；
- [ ] typing × provenance × checks 完整 2×2×2 因子消融有独立机制证据；
- [ ] full cost（含 capsule 生成/验证）和 equal-budget 对照齐全；
- [ ] gold 双人复核、agreement、datasheet、许可证和伦理说明齐全；
- [ ] artifact 能从 frozen traces 复现所有主表；
- [ ] 7 页正文自包含，官方 AAAI-27 模板、匿名与页数检查通过；
- [ ] 每个引用由作者人工核验，任何自动生成数字均能回溯到 raw result。

**最终建议：** 立即执行 30-task dev pilot 和 evaluator 审计；把 “EHC vs same-field structured payload” 设为第一停机门槛。它是最便宜、也最能提前揭示论文究竟是 AAAI 研究贡献还是工程包装的实验。
