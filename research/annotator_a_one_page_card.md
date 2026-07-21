# Annotator A — 一页操作卡（Candidate v2）

**角色：** 独立盲标 · 使用代码 `annotator_a` · 禁止查看对方或模型结果
**范围：** assignment 中的全部 **200** 题 · 按你文件里的顺序做，不要重排

---

## 你只会收到

1. `annotator_a` 的 assignment 文件
2. 对应工作簿（空白 JSON 或按模板填的 CSV）
3. `candidate_packets_v2/` 无标签 packet
4. `annotation_template.csv`（若用 CSV）
5. `annotation_protocol.md` + `candidate_v2_annotation_execution_guide.md`
6. `data/README.md`（category 定义）

**不要索取 / 不要打开：** 对方材料、remediation 队列、金标/evaluator、模型输出、论文结果、源 Episode。

---

## 每题怎么做（固定顺序）

1. **核对** packet 文件名、内部 `task_id`、assignment 里的 `packet_sha256`、`trace_cut`。
2. **只读边界：** 认证 trace 读到 `trace_cut`；scripted 回复是“问了才会发生”，不是边界上已成立的事实。
3. **先写合法 next-action**（再写 claim）：
   - 尽量枚举 ≥3 个公开备选；用边界证据检查各自 `requires`；
   - 写出动作名 + 精确 JSON 参数的有序序列；
   - 标出第一个用户影响/不可逆动作，确认其参数都有可见依据。
4. **再写原子 claim：** 拆开复合事实；每条一个 `claim_key`；填 category / status / value / criticality / task_critical / 反事实 rationale。
5. **挂 provenance：** 至少一条 `(trace_id, source_type, field_path)`；矛盾则引用所有冲突事件。
6. **任务级决策：** `irreversible_args_inferable`、`catalog_leakage_flag`；歧义/拒标理由只写在 `notes`（勿写姓名联系方式）。

**拒标（不要猜）：** 两套序列同等合法、参数不可见、或公共语义不够 → 在 notes 说明并拒标；不要问作者“正确答案”。

---

## Category 速记（互斥，按第一条命中）

`goal` → `constraint` → `consent`（用户授权；unknown≠普通缺参）→ `policy_check`（组织审批/资格）→ `unresolved_slot` → `verified_fact`（工具等权威事实）

不要：把 tool 成功与否当 claim；不要用未来 scripted 回复把 unknown 填成 known；不要把动作合同里的 `requires` 再抄成 gold claim。

---

## 交回前自检

- 每题：1 条 task + ≥1 条 claim；claim key 唯一；每 claim ≥1 条 provenance
- JSON 合法（字符串加引号、布尔小写）；动作只用 public catalog
- CSV：UTF-8、原表头、行序稳定；只用 `annotator_a`，不写真名
- JSON 工作簿：每题 `response=complete`；claims / action_sequence 非空；顶层 `status=completed_unlocked`
- 无模型输出、无对方内容、无真实 PII

格式问题会被退回**你本人**改格式；协调员不会提示语义答案。

---

## 提交与锁定

1. 导出完成后计算文件 SHA-256，经协调员指定渠道提交。
2. 你只会收到**自己的**哈希回执；不会看到 Annotator B。
3. 锁定后勿覆盖原文件；若需改正 → 新版本文件 + 新哈希 + 书面原因。

有疑问只问**格式/流程**；不要讨论具体题的“应该选哪个动作”。
