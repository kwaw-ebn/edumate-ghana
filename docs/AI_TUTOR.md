# EduMate Tutor frontend

## Available now

- Student sidebar and dashboard entry, plus **Ask EduMate Tutor** inside published lessons.
- Subject/lesson selection with class and objective context.
- Chat composer, keyboard submission, explanation/hint/practice/revision activities, practice feedback and retries.
- Original prepared explanations for the six original demonstration topics. Other published lessons use their own notes and objectives, with an explicit demo explanation.
- Teacher-authored ungraded practice questions when available, otherwise original topic examples.
- Browser read-aloud using installed English voices when supported. Voice input is not implemented.
- Per-account, per-lesson conversation history in sessionStorage, limited to 30 messages. Clear-chat action. History is not persisted to PostgreSQL.
- Responsive tablet/mobile layout, missing-lesson state, privacy reminders and an offline indicator.

Every tutor screen is labelled **Demo mode - GPT not connected**. Responses are deterministic and do not use a live AI model. There are no AI API requests, API keys or paid dependencies. Topic explanations are prepared demonstrations, not free-form answers. Tutor practice does not affect school grades. An open tutor screen can continue showing prepared content offline; downloaded offline learning remains a separate workspace.

## Future GPT integration

The single adapter is `frontend/app/tutor-demo.ts::requestTutorReply`. It currently returns the local demonstration response asynchronously. The React interface already handles an asynchronous response, errors and cancellation of stale responses after lesson switches.

When connecting an AI service:

1. Add a protected backend endpoint such as `POST /tutor/messages` (the existing Next rewrite exposes it as `/api/tutor/messages`). **This endpoint is not implemented yet.**
2. Accept a lesson ID, a bounded message, learning mode and bounded recent conversation. Authenticate the student, check current school/class access, and retrieve approved lesson context on the server. Do not trust client-provided school IDs or lesson content for access decisions.
3. Keep the API key exclusively in the backend environment. Never place it in browser code, a `NEXT_PUBLIC_*` variable or this repository.
4. Add school/student usage limits, request timeouts, safeguards appropriate to children, content grounding and a rule that guides students through graded work. The current demo's keyword checks are illustrative UI behavior, not a production safety system.
5. Validate and return a response shaped like `{text: string, practice?: {prompt: string, options: string[], correct: string, explanation: string}}`. Use the practice shape only for ungraded exercises; never expose answer keys for school assessments.
6. Replace the adapter with a same-origin authenticated fetch. Update the mode label only once live responses are implemented and verified. Handle refusal, rate limits, network failures and unsuitable responses explicitly.
7. Agree on guardian consent, privacy, retention and teacher oversight before sending real pupil conversations to a provider. Do not enable provider calls silently.

No API connection is needed to demonstrate the frontend now.

## Verification

Run `npm run build --prefix frontend`, then `python frontend/tests/tutor_check.py` with Python Playwright/Chromium installed. The browser test uses fictional mocked API records and checks lesson entry, demo labelling, hints, practice feedback/retries, revision, isolated lesson history, graded-work guidance, mobile width, clear chat and the absence of AI requests.
