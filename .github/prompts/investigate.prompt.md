---
description: "Diagnose a bug or unexpected behaviour using the Explore subagent. Provide a description of the issue."
argument-hint: "Describe the issue or bug to investigate"
agent: "agent"
---

Use the **Explore subagent** to investigate the following issue. Do not read files directly in this session.

**Issue:** $input

Instructions for the Explore subagent:
- Find the relevant code paths involved in the issue
- Identify the root cause or the most likely candidates
- Note the specific files and line ranges that are relevant
- Keep the response focused: root cause hypothesis, relevant files, and suggested fix direction only

Once the subagent returns its findings, present a concise diagnosis and propose the next step before touching any code.
