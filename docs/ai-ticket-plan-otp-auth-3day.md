# SecureShip 3-Day Execution Plan (AI-Ready Ticket Format)

## Usage Instructions

- Each ticket is self-contained and implementation-ready.
- Execute tickets in listed order unless dependencies are satisfied another way.
- For each ticket, produce: design notes, code changes, tests, and a completion report.
- Do not expand scope beyond the stated boundaries.

## Global Constraints

- Prototype scope only: no app-level identity.
- Session listing remains global for this prototype.
- Authorization is enforced per chat session.
- OTP is generated only after explicit user action via Authenticate CTA.
- No plaintext OTP in persistent logs or transcript.

## Definition of Done (Applies to Every Ticket)

- Code compiles and project tests pass for impacted areas.
- New behavior is covered by automated tests.
- OpenAPI and generated client artifacts are updated when API contracts change.
- No regressions in existing chat streaming and session history behavior.

---

## Ticket SS-101

Title: Normalize Session State Model and Session API Contract

Objective:
Align backend state semantics with auth lifecycle and align session API payload shape with frontend usage.

Scope:
- Replace active/deleted assumptions in auth flow paths.
- Standardize lifecycle states:
  - anonymous
  - collecting_identity
  - code_sent
  - awaiting_code
  - verified
  - escalated_to_human
- Ensure session payload includes title and message_count where expected.

Primary Files:
- backend/app/schemas/sessions.py
- backend/app/repositories/chat_sessions.py
- backend/app/routers/sessions.py

Out of Scope:
- Full archival policy redesign.

Acceptance Criteria:
- Session create/list/get return consistent lifecycle state values.
- Response shape is frontend-compatible.
- Legacy active/deleted assumptions are removed from active auth flow.

Dependencies:
- None

---

## Ticket SS-102

Title: Implement In-Memory Auth Session Store

Objective:
Create per-chat-session runtime auth state with deterministic expiration behavior.

Scope:
- Add AuthSessionStore interface.
- Add in-memory implementation keyed by chat session id.
- Implement operations:
  - get
  - upsert
  - mark_auth_required
  - mark_verified
  - record_otp_attempt
  - reset_identity_flow
  - expire_if_needed
  - delete

Primary Files:
- backend/app/services/auth_session.py (new)
- backend/app/dependencies.py
- backend/app/core/config.py

Out of Scope:
- Redis implementation.

Acceptance Criteria:
- Store returns valid, expired, or missing deterministically.
- TTL and cooldown values are config-driven.
- Dependency wiring allows test overrides.

Dependencies:
- SS-101

---

## Ticket SS-103

Title: Implement Identity Verification Service

Objective:
Match provided identity to a customer record using normalized fields.

Scope:
- Normalize first name, last name, and phone number.
- Add service returning match or no-match with safe error payload.

Primary Files:
- backend/app/services/identity_verification.py (new)
- backend/app/repositories/shipments.py (if customer lookup helpers are needed)

Out of Scope:
- Fuzzy matching.

Acceptance Criteria:
- Known fixtures resolve exactly one customer.
- No-match path remains gated without data leakage.

Dependencies:
- SS-101

---

## Ticket SS-104

Title: Implement OTP and SMS Services

Objective:
Create secure OTP lifecycle services for generation, delivery, and validation.

Scope:
- OTP generation (6-digit).
- OTP hash storage.
- TTL, max attempts, resend cooldown checks.
- Console SMS provider for prototype.

Primary Files:
- backend/app/services/otp.py (new)
- backend/app/services/sms.py (new)
- backend/app/core/config.py

Out of Scope:
- Production SMS provider integration.

Acceptance Criteria:
- Plain OTP is never persisted in DB transcript or durable logs.
- Errors are typed: invalid_code, expired_code, too_many_attempts, resend_cooldown.

Dependencies:
- SS-102

---

## Ticket SS-105

Title: Add Explicit Start Verification Endpoint

Objective:
Generate and send OTP only after user clicks Authenticate.

Scope:
- Add POST /api/auth/start-verification.
- Validate session and identity prerequisites.
- Generate/send OTP via services.
- Return payload to open OTP modal on success.

Primary Files:
- backend/app/routers/auth_verification.py (new or existing router module)
- backend/app/schemas/sessions.py (or dedicated auth schema module)
- backend/app/dependencies.py

Out of Scope:
- Auto-sending OTP from chat stream.

Acceptance Criteria:
- Success response includes started=true and show_code_modal=true.
- Prerequisite failures return typed error codes.
- Cooldown is enforced.

Dependencies:
- SS-102
- SS-103
- SS-104

---

## Ticket SS-106

Title: Add Verify Code Endpoint

Objective:
Verify OTP and bind verified customer to session.

Scope:
- Add POST /api/verify-code.
- Validate request/session.
- Verify OTP.
- On success: set state to verified and bind customer_id.
- Refresh auth session expiration on success.

Primary Files:
- backend/app/routers/verify_code.py (new or existing router module)
- backend/app/repositories/chat_sessions.py
- backend/app/schemas/sessions.py (or dedicated auth schema module)

Out of Scope:
- Multi-factor expansion.

Acceptance Criteria:
- Success transitions state to verified.
- Failure returns typed errors with remaining attempts where applicable.
- Challenge is invalidated appropriately after success.

Dependencies:
- SS-102
- SS-104
- SS-105

---

## Ticket SS-107

Title: Enforce Auth Gating in Chat Router and SSE Contracts

Objective:
Apply auth session checks on every chat request while preserving current session bootstrap behavior.

Scope:
- Keep existing behavior: null session id creates DB chat session.
- For resolved session id:
  - expired auth session -> unbind DB customer and re-gate
  - valid auth session -> proceed
  - missing auth session -> emit auth-required flow
- Add/emit SSE event contracts:
  - session
  - auth_state
  - auth_required (message + Authenticate CTA)
  - show_code_modal (only after start-verification success)

Primary Files:
- backend/app/routers/chat.py
- backend/app/services/chat.py
- backend/app/repositories/chat_sessions.py

Out of Scope:
- Frontend rendering.

Acceptance Criteria:
- Expired auth path always unbinds and re-gates.
- Missing auth path emits auth_required contract.
- No auto-OTP generation in chat flow.

Dependencies:
- SS-102
- SS-103
- SS-105

---

## Ticket SS-108

Title: Redesign Tool Contracts with Authorization Context

Objective:
Prevent model/user-provided identity from being used as authorization input.

Scope:
- Remove get_shipment_by_user(user_id)-style contract.
- Add customer-scoped tool contracts without identity params.
- Require auth_context in tool execution.
- Scope repository lookups to verified customer id.

Primary Files:
- backend/app/llm/tools.py
- backend/app/services/chat.py
- backend/app/repositories/shipments.py

Out of Scope:
- New business tools unrelated to shipment access control.

Acceptance Criteria:
- Unverified context returns auth_required consistently.
- Verified context only returns scoped customer data.
- Cross-customer access via crafted arguments is impossible.

Dependencies:
- SS-101
- SS-107

---

## Ticket SS-109

Title: Frontend Authenticate CTA and OTP Modal Flow

Objective:
Implement UX: auth-required message with Authenticate button, then OTP modal after successful start-verification.

Scope:
- Extend stream event handling for auth_required/auth_state/show_code_modal.
- Render auth-required chat message with Authenticate CTA.
- Call start-verification endpoint on button click.
- Open OTP modal only on successful start-verification response.
- Submit OTP to verify-code endpoint and handle outcomes.

Primary Files:
- frontend/src/api/chatStream.ts
- frontend/src/features/chat/useChatStream.ts
- frontend/src/features/chat/useChatSessions.ts
- frontend/src/pages/ChatPage.tsx
- frontend/src/components/OtpVerificationModal.tsx (new)
- frontend/src/components/AuthRequiredMessage.tsx (new or inline)

Out of Scope:
- Visual redesign beyond required UX behavior.

Acceptance Criteria:
- Authenticate button is shown when auth_required event is received.
- OTP modal opens only after start-verification succeeds.
- Verify success unlocks only the active session.

Dependencies:
- SS-105
- SS-106
- SS-107

---

## Ticket SS-110

Title: API Types Regeneration and Contract Sync

Objective:
Keep generated frontend API client synchronized with backend contract changes.

Scope:
- Regenerate OpenAPI artifacts.
- Regenerate frontend generated client and schemas.
- Validate type compatibility in chat/session features.

Primary Files:
- frontend/src/api/generated/*
- frontend/src/api/openapi.json
- backend schema/router modules that affect OpenAPI

Out of Scope:
- Manual edits inside generated files.

Acceptance Criteria:
- Generated client includes start-verification and verify-code contracts.
- Build passes with no contract drift errors.

Dependencies:
- SS-101
- SS-105
- SS-106

---

## Ticket SS-111

Title: Test Coverage, Regression, and Hardening

Objective:
Lock behavior with tests and validate no regressions across chat, auth, and tools.

Scope:
- Backend tests:
  - chat tools auth enforcement
  - start-verification and verify-code flows
  - expiration and unbind behavior
- Frontend tests:
  - auth-required CTA rendering
  - Authenticate click and modal open behavior
  - per-session verification isolation
- Add masked logging checks.

Primary Files:
- backend/tests/test_chat_tools.py
- backend/tests/test_sessions_api.py
- backend/tests/test_auth_flow.py (new)
- frontend test files for stream/page/components

Out of Scope:
- End-to-end infra test environment setup beyond current repo baseline.

Acceptance Criteria:
- All impacted tests pass.
- No plaintext OTP leaks in logs/transcripts.
- Existing chat streaming and history behavior remains functional.

Dependencies:
- SS-108
- SS-109
- SS-110

---

## Suggested Execution Order

1. SS-101
2. SS-102
3. SS-103
4. SS-104
5. SS-105
6. SS-106
7. SS-107
8. SS-108
9. SS-109
10. SS-110
11. SS-111

## Final Validation Checklist

- All endpoints return stable, typed error codes.
- OTP never sends automatically on identity match.
- Authenticate CTA is the only trigger for OTP generation.
- Expired or missing auth session always re-gates protected access.
- Session bootstrap from null session id remains supported in chat endpoint.
