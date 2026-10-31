<div align="center">

# XYOCK

**A focused AI workspace for learning, writing, and building code.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open-7AE5B3?style=for-the-badge&logo=github)](https://xyock.github.io/lock/)
[![Repository](https://img.shields.io/badge/GitHub-xyock%2Flock-181717?style=for-the-badge&logo=github)](https://github.com/xyock/lock)

An AI-powered chat interface that combines code assistance, conversational context, saved preferences, and a lightweight learning experience in one place.

</div>

---

## Overview

XYOCK is a browser-based AI assistant designed to help with programming tasks, explain technical concepts, and maintain useful context across conversations. The interface is intentionally lightweight and uses a dark, distraction-free design.

The application is backed by a Supabase Edge Function, which forwards requests to an AI model gateway. This keeps provider credentials out of the browser.

## Features

- **AI chat** — Ask questions, explore ideas, and get help with programming.
- **Code assistance** — Request code in supported languages and work with code-focused responses.
- **Conversation context** — Recent messages can be included with a new request so follow-up questions make sense.
- **Remember preferences** — Explicit preference requests can be saved in browser storage and included in later AI prompts. A new preference replaces the previous saved preference.
- **Secret Chat mode** — A password gate opens a separate chat session that is excluded from the app's normal conversation-history saving flow.
- **Conversation history** — Start new chats and revisit saved conversations when signed in and supported by the configured backend.
- **AI learning terms** — Explore built-in AI terminology and related explanations.
- **GitHub tools** — Access repository-oriented workflows exposed by the application.
- **Model selection** — Choose from the model options configured in the application.

## Live application

**[Launch XYOCK](https://xyock.github.io/lock/)**

The site is deployed with GitHub Pages. The frontend is served as a static web application; AI requests are handled by the configured backend function.

## Architecture

```text
Browser
  |
  |  Chat messages and optional attachments
  v
XYOCK frontend (xyock.html)
  |
  |  HTTPS request
  v
Supabase Edge Function: xyock-ai
  |
  |  Server-side request
  v
Kilo AI Gateway
  |
  v
Configured language model
```

### Main components

| Component | Responsibility |
| --- | --- |
| GitHub Pages | Hosts the static frontend |
| `xyock.html` | Chat interface, client-side features, and request handling |
| Supabase Auth / Database | Authentication and persistent application data, where configured |
| Supabase Edge Function (`xyock-ai`) | Receives AI requests and calls the model gateway |
| Kilo AI Gateway | Routes requests to the selected model |

The default model and available alternatives are configured in the frontend. The deployed Edge Function is responsible for communicating with the model gateway.

## Technology

- HTML, CSS, and JavaScript
- [Supabase](https://supabase.com/) — backend services and Edge Functions
- [Kilo AI](https://kilo.ai/) — model gateway
- [GitHub Pages](https://pages.github.com/) — static hosting

## Development and deployment

### Frontend

1. Clone the repository:

   ```bash
   git clone https://github.com/xyock/lock.git
   cd lock
   ```

2. Open `xyock.html` in a browser for local UI work, or serve the repository with a local static web server.
3. Configure the frontend's Supabase project settings to point to your own project before deploying your own instance.
4. Publish the frontend using GitHub Pages or another static hosting provider.

### Backend

The AI endpoint is expected to be deployed as a Supabase Edge Function named `xyock-ai`.

For a separate deployment:

1. Create a Supabase project.
2. Deploy the `xyock-ai` Edge Function.
3. Configure the model-gateway endpoint and API credential as server-side secrets in Supabase.
4. Configure the frontend to use your Supabase project URL and the deployed function endpoint.
5. Confirm that authentication, database policies, and function access rules match your deployment.

**Never put a private model-gateway API key or Supabase service-role key in frontend JavaScript.** Use server-side secrets and appropriate Row Level Security policies.

> This repository's frontend references a Supabase project. The Edge Function source and deployment configuration should be reviewed separately before creating an independent deployment.

## Privacy and security notes

- **Remembered preferences** are stored in the current browser's `localStorage`. They are not cloud-synced, do not automatically transfer to another browser or device, and can be lost if browser site data is cleared.
- **Secret Chat is not end-to-end encrypted.** Its password gate is a client-side access step, not cryptographic protection. Do not enter passwords, financial details, or other highly sensitive information. Requests sent to the AI backend may be processed by the configured model provider.
- **Conversation history** depends on the configured authentication and database policies.
- Treat AI-generated code and explanations as suggestions; review and test them before use.

## Project status

XYOCK is an actively evolving project. Some integrations and account workflows may be experimental or depend on the maintainer's backend configuration. Availability can change as the project develops.

## Contributing

Bug reports, feature suggestions, and pull requests are welcome.

When reporting an issue, include:
- What you expected to happen
- What actually happened
- Steps to reproduce the issue
- Browser and operating-system details, when relevant

## License

No license is currently specified in this repository. Unless a license is added, the default copyright rules apply and reuse is not automatically permitted.

---

<div align="center">

**XYOCK** · Build, learn, and create with AI.

</div>
