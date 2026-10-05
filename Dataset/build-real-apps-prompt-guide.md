# Building Real Apps (Not Prototypes) with AI Coding Agents
### A Senior Developer's Prompting Playbook + SRS Template

Tools like Antigravity, Cursor, and similar agent-first IDEs are optimized to produce something that *looks* done fast — a nice UI, a working button, a screenshot worth showing you. Left alone, they will happily stop there. Getting a fully functional product out of them is a discipline problem, not a tool problem. This guide gives you the prompting habits and the requirements document that force the agent to build the whole thing — front end, back end, data, and edge cases — not just the shell.

---

## 1. The Core Mistake to Avoid

**Vague scope → shallow build.** If you say "build me a to-do app," the agent decides what "done" means, and it usually means: a page that renders, with buttons that don't yet do anything real.

**Fix:** Never describe an app by its *features* alone. Describe it by its **screens + data + behavior + edge cases**. If you don't specify what happens on click, on error, on empty state, on reload — the agent won't either.

---

## 2. Prompting Techniques That Force Real Functionality

### 2.1 Specify the destination of every action, not just the action
Bad: *"Add a login button."*
Good: *"Add a login form (email + password) that calls the auth API, stores the session token, redirects to /dashboard on success, and shows an inline error message on failure (wrong password, network error, empty fields)."*

### 2.2 Describe data flow explicitly
State: where does data come from (API, database, mock, local storage)? What shape is it? What happens when it's empty, loading, or fails to load?

> "The Dashboard page fetches `/api/orders` on mount, shows a loading skeleton while fetching, renders an empty state message if the array is empty, and displays a paginated table (10 rows/page) if data exists."

### 2.3 Ban placeholders explicitly
Add this line to almost every build prompt:

> "Do not use placeholder text, mock buttons, or 'TODO' stubs. Every button, link, and form must be fully wired to real logic or a real API call. If a backend doesn't exist yet, create a minimal working one (e.g., local JSON server, SQLite, or in-memory store) rather than faking the UI."

### 2.4 Ask for the task plan first, then review it
Before letting the agent code, ask it to output an implementation plan / task list. Read it. If a screen or flow you asked for isn't broken into concrete implementation tasks (e.g. "wire form submit to backend," "handle empty/error states"), say so before approving:

> "Your plan only lists UI tasks for the Settings page — add tasks for the save-to-backend logic and validation."

### 2.5 Build one flow completely before moving to the next
Instead of: *"Build the whole app: login, dashboard, settings, profile."*
Do: *"Build the login flow completely — UI, validation, API call, error handling, session persistence. Confirm it works end-to-end before we move to the dashboard."*

Depth-first beats breadth-first when working with agents. A fully wired login page is more valuable than four half-wired pages.

### 2.6 Force a self-check after generation
End every build prompt with a verification instruction:

> "After building, go through every button, link, and form in the app and confirm each one performs a real action (API call, state change, navigation, persistence). List any that are still stubs, and finish them before reporting completion."

### 2.7 Set a standing rule (if the tool supports rules/config files)
Most agentic IDEs (Antigravity, Cursor, Claude Code) support a persistent rules file (e.g. `GEMINI.md`, `.agents/rules/`, `CLAUDE.md`). Add a rule like:

> "Never leave a page, button, or feature as a visual-only placeholder. Every UI element must be connected to working logic, a real API, or a real data store. If unsure whether something is 'done', assume it needs backend logic and implement it."

This applies the constraint automatically across every task, not just the one you're currently prompting.

### 2.8 Use "acceptance criteria" language, not feature lists
Frame each feature as a testable outcome:

> "Feature is done when: a user can sign up, log out, log back in, and see their data persist across sessions. Not done if any of these fail."

This gives the agent (and you) a concrete bar instead of a vibe.

### 2.9 Ask it to demonstrate, not just claim
> "Show me a screen recording or walkthrough proving the signup → login → dashboard flow works end-to-end with real data, not mock data."

Agentic IDEs like Antigravity already generate walkthroughs/screenshots as artifacts — explicitly ask it to prove the *full* flow, not just the landing screen.

---

## 3. Software Requirements Specification (SRS) Template

Feed this structure to the agent (filled in for your app) as your very first prompt, or paste it as a project spec file. It forces the plan to include real logic from the start.

```markdown
# SRS: [App Name]

## 1. Purpose
What problem does this app solve? Who is the user?

## 2. Scope
What is in v1? What is explicitly NOT in v1 (to prevent scope creep or agent over-building)?

## 3. User Roles
- Role 1 (e.g. Guest): what can they do?
- Role 2 (e.g. Registered User): what can they do?
- Role 3 (e.g. Admin): what can they do?

## 4. Functional Requirements (per screen/feature)
For EACH screen, specify:
- **Screen name**
- **Purpose**
- **Inputs** (fields, buttons, filters)
- **Data source** (API endpoint / DB table / mock — be explicit)
- **Actions & outcomes** (what happens on each click/submit — success AND failure paths)
- **States to handle**: loading / empty / error / success
- **Navigation**: where does each action lead?

Example:
### 4.1 Login Screen
- Inputs: email, password, "remember me" checkbox
- Data source: POST /api/auth/login
- On success: store JWT in secure storage, redirect to /dashboard
- On failure: show inline error ("Invalid credentials" / "Network error")
- Empty fields: disable submit button, show validation message
- Loading state: disable form, show spinner on submit button

## 5. Non-Functional Requirements
- Performance (e.g. page load under X seconds)
- Security (auth method, data encryption, input sanitization)
- Responsiveness (mobile/desktop breakpoints)
- Browser/device support

## 6. Data Model
List entities and their fields, e.g.:
- User: id, name, email, password_hash, created_at
- Order: id, user_id, items[], total, status, created_at

## 7. API Endpoints (if applicable)
| Method | Endpoint | Purpose | Auth required? |
|--------|----------|---------|-----------------|
| POST | /api/auth/login | Log in user | No |
| GET | /api/orders | Fetch user orders | Yes |

## 8. Edge Cases & Error Handling
List explicitly — this is what agents skip most often:
- What if the network fails mid-request?
- What if a form is submitted twice?
- What if a user has zero data (empty state)?
- What if a session expires mid-use?

## 9. Definition of Done
This app is complete when:
- [ ] Every screen listed in Section 4 is implemented with real data flow, not placeholders
- [ ] Every button/link performs its stated action
- [ ] All error/empty/loading states are handled
- [ ] Data persists correctly across reloads/sessions
- [ ] Core user flows work end-to-end (list them)
```

---

## 4. Quick Reference: Prompt Checklist Before You Hit "Build"

- [ ] Did I name every screen, not just the app as a whole?
- [ ] Did I specify what data each screen needs and where it comes from?
- [ ] Did I specify success AND failure behavior for every action?
- [ ] Did I explicitly ban placeholders/stubs?
- [ ] Did I ask for the task plan before it starts coding?
- [ ] Did I ask for a self-check / walkthrough proving the full flow works?
- [ ] Am I building one flow at a time instead of the whole app at once?

---

*Use the SRS template above as a living doc — paste it into your first prompt for a new project, and update it as you refine scope. The more concrete Section 4 and Section 8 are, the less likely the agent is to stop at "looks done."*
