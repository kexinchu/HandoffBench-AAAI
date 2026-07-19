# HandoffBench AAAI-27 严格审稿审计

审计日期：2026-07-18。审计范围：`paper/main.tex`、`research/*.md`、当前代码、数据和
`outputs/`，以及本地保存的 *Handoff Debt*（arXiv:2606.02875v1）。本审计不把开发集、
协议失效运行或不完整 counterfactual 结果当作论文证据。

## 总裁决

**若以当前仓库状态投稿：预计 2/5（Reject；苛刻审稿人可能给 1/5）。** 问题重要、形式化
方向清楚、harness 工程质量正在变好，但当前稿件仍是两页 proposal：Results 明确空缺，
`references.bib` 没有文献条目，没有冻结 test split、人工标注可靠性、跨模型主实验、完整
factorial 或 confirmatory statistics。现有结果只足以证明“系统能运行并不断发现协议问题”，
不能证明科学主张。

**完成关键证据包后的上限：有条件 4/5。** 这要求论文的中心发现是“可测的 boundary-state
loss 及其因果后果”，且 provenance/checks 对匹配 Structured baseline 有独立机制效应；如果
最终只得到“JSON 比自由摘要好”，在 *Handoff Debt* 之后最多约 3/5。

## 已核验的资产与缺口

- `data/tasks/dev/pilot.json` 有 30 个任务，五域各 6 个，30 个独立 `template_family`；它明确
  是 development pilot，不是冻结 test。
- `data/tasks/dev/counterfactual_travel.json` 有 24 个任务，但只是 6 个 travel families 的四种
  variants，不能按 24 个独立样本统计。
- 没有可见的 train/test task manifests。`configs/factorial.yaml` 规划 60 个 test tasks、2 个
  models、2 seeds，但配置不是数据或实验结果。
- `outputs/` 中多个 smoke 目录已明确标为 `INVALID_PROTOCOL`；v2 是有 action-label leakage 的
  development diagnostic。v3 和 counterfactual interim 仍是单一 Qwen、极小且不完整样本，
  不能用于 confirmatory claims。counterfactual 汇总中各方法的 `n` 不相等（例如 EHC=5、
  Structured=5、Full History=7、Oracle=24），不是可接受的主方法配对比较。
- 当前 harness 已具备严格 schema、原子状态匹配、首次 receiver probe、原子 artifact、seed、
  usage 和 deterministic simulator 等良好基础；但没有完整冻结 split、双人 gold audit、主矩阵
  mixed/paired analysis 或一键生成论文表格的证据。
- `paper/main.pdf` 当前为 2 页。模板能够编译，但这不是接近投稿完成的七页论文。

## 相对 Handoff Debt 的可辩护创新

不能声称：首个 handoff benchmark、首个 deterministic takeover boundary、首个 raw trace vs
summary vs structured comparison、首个 bounded/auditable structured handoff，或首个测量 handoff
成本。*Handoff Debt* 已在 75 个 SWE-bench Verified source tasks、181 个 handoff points、3 个
successor models 和 2,172 runs 上占据这些主张，并报告 solved rate、events、tokens、bootstrap
intervals 和 McNemar tests。

仍可辩护、但必须由实验兑现的差异是：

1. **测量对象不同。** *Handoff Debt* 测 coding takeover 的可恢复性与 rediscovery cost；本工作
   可测 inter-role control boundary 上原子语义/认识状态是否被正确转移。
2. **监督信号不同。** HandoffBench 有隐藏的 boundary gold claims，包括 known/unknown/
   contradicted、scoped consent、policy decision 和 unresolved slots，并可报 category-level fidelity；
   对方的 handoff state 是 repository-level outcome class，不是语义接口 gold。
3. **错误归因不同。** 通过首次 receiver state probe、gold-state oracle 和相同 simulator，可区分
   extraction/representation loss 与 receiver utilization failure，并定义 oracle-conditional regression。
4. **安全语义不同。** 本工作可研究缺少授权、错误 scope、policy clearance 和不可逆 action gate；
   对方没有 transaction authority construct。
5. **机制识别潜力。** 信息匹配的 typing × provenance × checks factorial、corrupted capsule 和
   advisory-vs-enforced gate 能回答“为什么有效”，而不仅是比较四种 note formats。

安全定位句应是：

> Prior takeover work measures whether coding successors resume and how much rediscovery different
> context views induce. We instead expose a gold semantic state at an inter-role boundary, score its
> epistemic and authority-bearing claims, and test which transfer errors cause downstream regression
> or policy-invalid action.

如果 provenance/checks 对同字段 Structured Payload 没有稳定增益或预期 stressor interaction，
“Executable Capsule”不构成足够的方法创新。此时应诚实改写为 benchmark/diagnostic paper。

## 达到 4/5 必须补齐的证据

### 数据与标注

- 至少 120 个**独立 task families**，五域均衡；更稳妥是 160–200，以检测约 8pp 的配对差异。
  数值/实体替换和同一 family 的 counterfactual variants 不算独立任务。
- 独立 train/dev/test family split；所有 prompt/schema 修复只能看 dev，test hash 在主运行前冻结。
- 至少 40% 任务包含 user-impacting/irreversible decision；但 consent-heavy 模板不能人为保证 EHC
  获胜。各方法必须面对相同公开 action contract。
- 两名人工标注者独立审阅全部 test gold，第三人裁决；报告 category agreement、boundary-state
  precision/recall/F1 或适用的 kappa，以及具体分母。作者/LLM 单人生成 gold 不够。
- 发布 datasheet、template lineage、licenses、task/split hashes、模型 snapshot、prompt/config hashes、
  raw runs 和 software revision。

### 主实验与对照

- 至少 2 个模型家族是底线，3 个更像 AAAI 主会证据；不能只有 Qwen。主方法为 Full History、
  Free Summary、同字段 Structured Payload、EHC、Gold Oracle。
- 增加真正的 no-handoff/single-agent control，或非常精确地说明为什么 Gold Oracle/Full History
  分别是什么 estimand；不能把 Full History 自动称为 single-agent oracle。
- 完成同信息、近似同 token 的 2×2×2 typing × provenance × checks 八格。当前只有设计文档和
  legacy 三方法，不足以估计主效应/交互。
- 分开报告 generated capsule 与 gold capsule；加入 corrupted/missing/contradicted claim challenge，
  证明 provenance/checkability 不是装饰性 metadata。
- 对 EHC gate 报 prevented violations、false blocks 和 utility loss；representation effect 与 enforced
  action policy effect必须分表，不能混为 EHC 增益。
- 至少加入一个 framework-realistic external-validity adaptation（例如真实 handoff API 的 history
  filter/typed payload），否则只可声称 controlled protocol，而非现代 frameworks 的普遍行为。

### 统计

- 所有主比较按 task/model/seed 完整配对；provider/parse failure 按预注册 missingness policy 处理，
  不得让不同方法出现不同 `n` 后直接比较均值。
- 主终点限于：EHC vs Structured strict success；EHC vs Free Summary critical episode error；EHC vs
  Full History 的预设 non-inferiority 与 token superiority。给 absolute effect、95% CI、原始分母。
- 二元结果用 task-family cluster bootstrap/paired test；连续 F1/tokens 用 family bootstrap。seed 不是
  独立 task。模型/域/stressor 的 mixed-effects 分析需说明 random intercept 与 interaction。
- 建议在 dev discordance 上做 power simulation，再冻结 N。仅 60 tasks × 2 models 很可能无法稳定
  证明 8pp；增加独立 families 比增加 seeds 更重要。
- 报 method × missing-consent/irreversible-action、provenance × conflict 的预注册 interaction，并对
  多重比较校正。阴性机制结果必须保留。
- 成本必须含 source generation、receiver 所有轮次、validator/checker、失败调用和 output tokens；
  当前汇总主要突出 input tokens，不足以支持“更低成本”。

## 当前草稿的 unsupported / overclaim

1. Abstract 说 gold state “including ... commitments, and action preconditions”，但 `data/README.md`
   明确 pilot 没有 commitment/risk gold，precondition 在 `ActionRule.when` 而非 primary gold。应改为
   “schema supports”，或等 test 数据确实覆盖后再写。
2. Abstract 称 evaluators “separate source extraction, transport, and receiver utilization errors”。当前
   有 receiver probe/oracle 基础，但没有完整 intervention matrix 与结果。应写“enable/provide probes
   for”，不能写成已被实证分解。
3. Introduction 称 benchmark holds target model/tools/budget fixed while only representation varies。
   EHC source prompt、public predicates、validation/checks 和调用成本可能不同；只有完成信息匹配
   factorial 与成本核算后才能使用“only”。
4. “minimal, task-sufficient gold state”中的 minimality/sufficiency 尚未验证。需要 claim deletion test
   或标注准则与 oracle action determinacy；否则改为“task-critical annotated state”。
5. “Task families, entity pools, and workflow automata are separated across splits”目前不成立：只有 dev
   数据，没有可审计 split manifests。
6. “Each contains two or three roles”需要数据统计证明；当前核心对象主要是 source/target boundary，
   不要用设计意图冒充数据属性。
7. “Critical errors include hallucinated ... commitments”与 pilot ontology 不一致；当前可主报 consent、
   policy/precondition/action errors，commitment 只能在有 authenticated evidence 的扩展集报告。
8. EHC “evaluates declared preconditions before user-impacting actions”混合 representation 与 enforcement。
   主 factorial checks 是 advisory，enforced gate 是二级 intervention；正文必须明确区分。
9. “matched factorial study”目前只是计划，尚无八格实现结果。改为 future tense 或完成后再保留。
10. Related Work 是一个无引用的占位段。`references.bib` 为空是直接 desk-quality failure；正文必须
    逐一引用 *Handoff Debt*、tau-bench/tau2、ToolSandbox、STATE-Bench、MultiAgentBench、DeLM、
    框架官方 handoff semantics 等已核验 primary sources。
11. Results 空缺当然不能投稿；任何 dev/smoke 数字都不得偷偷改称 benchmark results。
12. “higher auditability”“executable”“provenance-aware”必须各有操作化指标：provenance validity、check
    accuracy/corruption detection、prevented/false-block actions，而不是凭 schema 命名成立。

## 格式与呈现问题

- 当前使用 AAAI-27 submission style、letterpaper、匿名作者，编译日志显示 2 页，未见当前致命编译
  warning；但完整稿必须守 7 页正文、其后仅 references、总长上限及 checklist 的最终 author-kit规则。
- 当前没有任何 citation，bibliography 为空；这是内容和格式双重未完成。
- 两页稿几乎没有图、表、算法、dataset statistics 或 result denominators。最终主文至少需要：任务/
  state 分布表、方法对照表、主结果含 CI 表、一个 failure/decomposition 图、一个 cost/ablation 表。
- 不要把十种 state fields 全部宣传为 pilot coverage；表中应明确 schema-supported 与 dataset-observed
  categories，以及 primary metric 排除项。
- 标题可保留，但 “State Is the Interface” 的形式化含义必须在第一页定义，而非口号。

## 建议的七页结构与具体修改

1. **P1 Introduction。** 用一个同轨迹、不同 handoff view 导致不同 action 的可复现例子；紧接着定义
   boundary state fidelity。三项贡献必须是 benchmark、diagnostic estimand、机制实验，而不是“JSON
   schema”。首段末显式区分 *Handoff Debt*。
2. **P2 Formalization + closest work。** 定义 trace、boundary gold、view、首次 receiver probe、strict
   success、oracle-conditional regression；用 5–6 行 collision table 对比 Handoff Debt/tau2/
   STATE-Bench/MultiAgentBench。删除无法验证的 priority claim。
3. **P3 Benchmark。** 报 domain/family/split/state-category/critical-action 数量、任务生成与独立标注、
   deterministic evaluator、leakage audit。明确 primary gold ontology 与非 primary metadata。
4. **P4 Methods and controls。** 同一张图展示 Full/Free/Structured/EHC/Oracle；EHC 分为 typed claims、
   trace binding、advisory checks，另框标出 optional enforcement，防止因果混淆。给 token/call accounting。
5. **P5 Main results。** 完整配对分母；strict success、macro state F1、critical episode error、HIR 和
   input/output tokens，全部带 family-clustered CI。先报 EHC vs Structured，不要先挑 EHC vs Free。
6. **P6 Mechanism and robustness。** 八格 factorial 主效应/交互、gold-vs-generated、corruption test、
   advisory-vs-enforced、按 ontology category 的 error decomposition；至少展示一个阴性结果。
7. **P7 Limitations/Responsible Research/Conclusion。** 限定到 synthetic text/tool workflows；讨论 gold
   non-uniqueness、template dependence、模型漂移、mocked irreversible actions 和无真实 PII。结论只
   重述有 CI 支撑的发现。

## 提交门槛

在以下全部完成前应维持 **NO-GO**：冻结且未调参的 test；至少两模型完整配对主矩阵；Structured
关键对照；Gold Oracle；完整 2×2×2 或诚实降级方法主张；family-level CI；双人 gold audit；所有
invalid/dev artifacts 与论文表隔离；引用和七页正文完整；论文中的每个数字可回溯到 raw run。

最关键的 go/no-go 结果不是 EHC 是否胜 Free Summary，而是：**在相同原子信息、预算和 receiver
条件下，provenance/checks 是否让 EHC 稳定胜过 Structured Payload，并且这种差异是否集中出现于
理论预测的 conflict/authority/precondition stressors。**
