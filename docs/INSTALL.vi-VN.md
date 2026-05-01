# Cài đặt

Coding Assistant Agent là gói **Copilot-first**: bạn có thể thả vào một dự án dùng GitHub Copilot hoặc cài cấu hình toàn cục cho mọi dự án.

## Yêu cầu

- GitHub Copilot đã bật trong IDE (VS Code, JetBrains, Neovim).
- Python 3.10+ (chỉ cần cho validator và eval harness, agent runtime không cần).
- `git` (để clone và đồng bộ `HANDOFF-PROTOCOL.md` với `software-engineering-agent`).

## Chế độ cài đặt

### Mode A — Theo từng dự án (khuyến nghị)

Copy thư mục `.github/` vào root dự án. Copilot sẽ tự nhận agent + skills.

```bash
git clone https://github.com/Tiepbm/coding-assistant-agent.git /tmp/coding-assistant-agent
cp -r /tmp/coding-assistant-agent/.github your-project/.github
```

Nếu dự án đã có `.github/`, hãy merge:

```bash
cp -rn /tmp/coding-assistant-agent/.github/skills/ your-project/.github/skills/
cp -rn /tmp/coding-assistant-agent/.github/agents/ your-project/.github/agents/
cp /tmp/coding-assistant-agent/.github/copilot-instructions.md your-project/.github/copilot-instructions.md
```

### Mode B — Toàn cục (mọi dự án)

Copy `agents/` và `skills/` vào cấu hình Copilot user-level (path tùy IDE).

```bash
cp -r coding-assistant-agent/agents/ ~/.config/copilot/agents/
cp -r coding-assistant-agent/skills/ ~/.config/copilot/skills/
cp coding-assistant-agent/HANDOFF-PROTOCOL.md ~/.config/copilot/HANDOFF-PROTOCOL.md
```

### Mode C — Cài cặp với `software-engineering-agent` (CE7)

Để có trải nghiệm **principal + senior+** đầy đủ:

```bash
mkdir -p ~/copilot-agents && cd ~/copilot-agents
git clone https://github.com/Tiepbm/software-engineering-agent.git
git clone https://github.com/Tiepbm/coding-assistant-agent.git

# Kiểm tra HANDOFF-PROTOCOL.md đồng bộ
diff -q software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md
```

Nếu khác nhau, đồng bộ từ CE7 (chủ canonical):

```bash
cp software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md
```

## Kiểm tra cài đặt

Chạy validator cấu trúc:

```bash
cd coding-assistant-agent
python3 scripts/validate_packs.py
```

Output mong đợi:

```
PASS: coding-assistant pack layout is valid
- packs: 10
- references: 49
- agent: coding-assistant.agent.md (with Clarify-First, Self-Review, Mini-Bar, Auto-Attach, HANDOFF link)
- HANDOFF-PROTOCOL.md present
```

## Thử task đầu tiên

Mở IDE trong dự án có Copilot. Hỏi:

> Implement an idempotent payment-capture endpoint in Spring Boot 3, header `Idempotency-Key`, p99 < 300ms, behind feature flag `payments.idempotent_v2` rolled out 1%->10%->50%->100%.

Hành vi mong đợi:

1. Agent KHÔNG hỏi clarify (brief đã đầy đủ).
2. Agent emit kế hoạch 8 bước.
3. Agent viết test trước, implement sau, rồi chạy Self-Review Checklist.
4. Response kết thúc bằng **Production Readiness Mini-Bar** (5 dòng: idempotency, observability, tenant authz, rollback, runbook line).

Nếu thiếu thì cài đặt chưa hoàn chỉnh hoặc agent file không được Copilot nhận. Chạy lại validator và kiểm tra log Copilot.

## Nâng cấp

```bash
cd coding-assistant-agent && git pull
# Copy lại mirror nếu dùng Mode A hoặc B
```

Sau mỗi lần nâng cấp, cũng pull `software-engineering-agent` và sync lại `HANDOFF-PROTOCOL.md`.

## Gỡ cài

```bash
rm -rf your-project/.github/skills/{backend,frontend,mobile,database,api-design,observability,testing,debugging,devops,quality}-pack
rm -f your-project/.github/agents/coding-assistant.agent.md
```
