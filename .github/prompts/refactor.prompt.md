---
description: "Structured refactoring workflow: Explore subagent scopes the change, plan is proposed for approval, then implementation begins. Provide a description of the refactoring goal."
argument-hint: "Describe what to refactor and why"
agent: "agent"
---

Perform this refactoring in three explicit phases. Do not skip ahead.

**Refactoring goal:** $input

---

## Phase 1 — Explore (subagent)

Use the **Explore subagent** to map the scope. Ask it to:
- Find all files and symbols directly involved in the change
- Identify callers, consumers, and anything that would break
- Note existing patterns (naming, structure) to match in the refactored code
- Flag any non-obvious side effects or coupling

Return the subagent's findings verbatim before continuing.

---

## Phase 2 — Plan

Based on the Explore findings, produce a concise implementation plan:
- List every file that will change and what changes in each
- Call out any rename, interface change, or contract change explicitly
- Flag risks

**Stop here and wait for explicit approval before writing any code.**

---

## Phase 3 — Implement

After approval, implement the plan. Apply changes file by file. After all edits, run the relevant tests.

* backend tests:
```
uv run python -m unittest
```

Report any failures before declaring done.
