# Playbook Cải Tiến Theo Eval

Khi pipeline eval (`docs/pipeline-guide.md`) cho thấy regression hoặc điểm thấp, theo playbook này để chạy chu trình cải tiến.

## Khi nào chạy playbook

- Coding suite < 90% pass-rate.
- Bất kỳ critical task nào (security/data-loss) fail.
- Handoff suite < 80%.
- Anti-pattern suite < 95%.
- Bản model mới làm giảm điểm.

## Chu trình 5 bước

### 1. Đọc báo cáo, tìm hotspot

Mở `runs/<sha>/aggregate.md`. Xác định:

- Top 3 case điểm thấp nhất.
- Pack có tỷ lệ fail cao nhất.
- Dimension có tỷ lệ fail cao nhất (Routing? Inclusion? Security depth?).

### 2. Reproduce local

Với mỗi case điểm thấp nhất, chạy prompt thủ công qua agent. So sánh:

- Output của agent so với `must_include` / `must_not_include`.
- Agent có gọi đúng `expected_pack` và `expected_references` không.
- Self-Review Checklist + Production Readiness Mini-Bar có xuất hiện không.

### 3. Chẩn đoán: pack vs prompt vs rubric

| Triệu chứng | Chẩn đoán | Sửa ở |
|---|---|---|
| Agent gọi sai pack | Routing description mơ hồ | `agents/coding-assistant.agent.md` Skill Routing OR pack `When to Use` |
| Đúng pack nhưng thiếu reference | Pack Reference Map mơ hồ | `skills/<pack>/SKILL.md` Pack Reference Map row |
| Code thiếu `must_include` | Reference content mỏng/cũ | `skills/<pack>/references/<ref>.md` |
| Code chứa `must_not_include` | Anti-pattern chưa nêu trong `When NOT to Use` | Update cả pack `When NOT to Use` LẪN `anti-pattern-benchmark.jsonl` |
| Bỏ qua Self-Review | Workflow rule chưa đủ chặt | `agents/coding-assistant.agent.md` Self-Review Checklist |
| Không escalate sang CE7 | Thiếu signal escalation | `agents/coding-assistant.agent.md` Expert Escalation + thêm case vào `handoff-benchmark.jsonl` |

### 4. Áp dụng fix nhỏ nhất khả thi

- Ưu tiên sửa pack/reference hơn sửa agent (low-risk surface).
- Ưu tiên thêm row vào benchmark hơn nới lỏng rubric.
- Ưu tiên cho agent hỏi thêm 1 clarify hơn để nó đoán.

### 5. Re-run + ghi nhận

```bash
python3 scripts/validate_packs.py
python3 evals/validate-references.py
python3 evals/run_eval.py ...
```

Append 1 dòng vào `memory/learned-patterns.md` mô tả bug + fix + benchmark case ID. Đây là corpus cho regression review tiếp theo.

## Anti-improvement (không được làm)

- Hạ `fail-under` để CI xanh.
- Xóa critical task thay vì fix.
- Thêm `must_include` để match câu trả lời sai-nhưng-pass.
- Cho agent bỏ qua Self-Review vì "performance".

## Review hàng quý

Mỗi quý (hoặc sau model bump lớn):

1. Đọc lại `memory/learned-patterns.md` và `memory/routing-corrections.jsonl`.
2. Xác định pattern fix lặp lại.
3. Promote thành agent rule / pack guidance.
4. Retire anti-pattern case nào đã clean 3+ run liên tiếp (thay bằng case khó hơn).
