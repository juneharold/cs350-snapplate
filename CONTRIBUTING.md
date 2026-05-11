# Team Contribution Rules

This file is for the four SnapPlate teammates working in this repository. It defines how we should use Git, write code, review each other, and decide when a task is done.

SnapPlate is currently specified as:

- Mobile client: Expo / React Native
- Backend: FastAPI REST API
- Auth / database / storage: Supabase
- External restaurant data: Kakao Local REST API
- Core features: account/profile, restaurant search, bookmarks, camera/photo upload, food diary, taste analysis, recommendations, settings

If we change the stack, update this file in the same pull request.

## Shared Expectations

- Keep `main` runnable.
- Do not commit directly to `main`.
- Keep each branch focused on one task.
- Keep changes small enough for teammates to review.
- Explain unclear decisions in the PR instead of hiding them in code.
- Do not add features outside the SRS unless the team agrees first.
- Do not commit secrets, local config files, build outputs, or unrelated edits.

## Working On A Task

When you start a task:

1. Pull the latest `main`.
2. Create a new branch for that task.
3. Implement only the task you picked.
4. Run the relevant checks or manually verify the changed workflow.
5. Open a pull request.
6. Ask at least one teammate for review.
7. Merge only after review and verification.

Useful commands:

```bash
git checkout main
git pull
git checkout -b feature/photo-upload
```

## Branch Names

Use this format:

```text
type/short-description
```

Allowed types:

```text
feature/photo-upload
feature/diary-list
fix/login-token-refresh
docs/api-setup
test/diary-api
refactor/recommendation-service
chore/update-dependencies
```

Use:

- `feature/` for new user-visible behavior
- `fix/` for bug fixes
- `docs/` for documentation
- `test/` for test-only work
- `refactor/` for behavior-preserving cleanup
- `chore/` for tooling, dependencies, or repo maintenance

## Pull Requests

Every PR should be small and reviewable.

- One PR should cover one task.
- If a PR changes more than about 400 lines, explain why.
- If a PR changes a mobile/backend API contract, update both sides in the same PR when possible.
- If the other side will be updated later, write that clearly in the PR.
- Squash merge PRs into `main` unless the team agrees otherwise.
- Delete the branch after merge.

Use this PR description:

```markdown
## What Changed
-

## Related Requirement
- REQ-...

## Verification
- [ ] Ran tests: `...`
- [ ] Manually checked: ...

## Notes
- N/A
```

If a section does not apply, write `N/A`.

## Reviews

Every PR needs at least one teammate review before merge.

Ask the teammate closest to the changed area:

- API, schema, auth, Supabase, or Kakao changes: backend reviewer
- Mobile UI, navigation, screen state, or permissions: frontend reviewer
- Taste analysis, recommendation logic, or ranking behavior: algorithm reviewer
- Documentation-only changes: any teammate

As a reviewer:

- Check correctness first.
- Check whether the implementation is simpler than the problem requires.
- Check whether the change matches the SRS and project vocabulary.
- Point out unrelated edits.
- Ask questions when intent is unclear.
- Do not request personal style changes unless they improve readability or consistency.

As the PR author:

- Respond to every review comment.
- Push follow-up commits to the same branch.
- Do not resolve comments without either making the change or explaining why not.

## Commit Messages

Use clear, direct commit messages.

Good:

```text
Add diary photo upload endpoint
Fix bookmark toggle state
Document Supabase setup
```

Bad:

```text
stuff
fix
changes
wip
```

We do not need a strict commit message format unless the team later adds one.

## Project Rules

### Requirements

- Connect PRs to SRS requirement IDs when possible.
- Example:

```text
Implements REQ-4.6-001 and REQ-4.6-002 for photo-based diary creation.
```

- Do not add version 1.0 out-of-scope features unless the team agrees first.
- The SRS currently excludes admin dashboards, payments, social sharing, chat, and web/tablet-specific clients.

### API Boundaries

- The mobile app should call the backend REST API for SnapPlate data operations.
- Backend responses should use JSON.
- Photo uploads should use `multipart/form-data`.
- Authenticated API requests should include the auth token in request headers.
- Kakao Local REST API calls should live behind backend code, not directly inside UI components.
- External API keys must be read from environment variables, not hardcoded.
- If an endpoint shape changes, update the caller, tests, and documentation in the same PR when possible.

### Data And Security

- Do not commit `.env` files.
- Add or update `.env.example` when adding a required environment variable.
- Never commit Supabase service-role keys, Kakao API keys, private tokens, or production credentials.
- User-owned data must stay user-scoped.
- Do not expose another user's diary entries, images, bookmarks, or profile data.
- If database schema changes are introduced, include the migration or setup instructions in the same PR.

### Error Handling

- Do not hide unexpected failures with silent fallbacks.
- If the product needs graceful behavior, make it explicit in code and UI.

Acceptable examples:

- Show an upload failure message and keep the original photo available.
- Show cached restaurant results with a visible stale/loading state.
- Queue diary sync after network recovery and indicate that sync is pending.

Unacceptable examples:

- Catching an exception and returning empty data without explanation.
- Ignoring a failed API response and pretending the save succeeded.
- Falling back to mock data in development without making that obvious.

## Coding Conventions

### General

- Keep changes surgical and directly tied to the task.
- Prefer simple code over abstractions that are only used once.
- Match the style of nearby code.
- Put imports at the top of the file.
- Remove unused imports, variables, functions, files, and comments created by your change.
- Do not leave commented-out code in committed changes.
- Do not reformat unrelated files.
- Do not rename files, routes, API fields, or database columns unless the task requires it.
- Use product vocabulary consistently: `diaryEntry`, `restaurant`, `bookmark`, `photo`, `tasteProfile`, `recommendation`.

### Frontend: Expo / React Native

- New frontend code should use TypeScript unless the team decides otherwise.
- Keep UI components focused on rendering and interaction.
- Put API calls in a dedicated client/service layer, not directly inside deeply nested UI components.
- Do not store auth tokens manually unless the chosen auth library requires it.
- Keep loading, empty, error, and success states explicit for screens that fetch or mutate data.
- Request camera, location, photo library, and notification permissions at the point of use.
- Do not hardcode device-specific layout sizes when React Native layout can handle it.

### Backend: FastAPI / Python

- Follow PEP 8.
- All imports must be at the top of the file.
- Prefer typed request and response models.
- Keep route handlers thin.
- Put database access, external API calls, and recommendation logic in separate functions or service modules when they become non-trivial.
- Validate request inputs at the API boundary.
- Return clear HTTP status codes:
  - `400` for invalid input
  - `401` for missing or invalid authentication
  - `403` for authenticated users accessing data they do not own
  - `404` for missing resources
  - `500` only for unexpected server errors
- Do not log secrets, auth tokens, raw credentials, or private user data.

## Tests And Manual Verification

- Add or update tests for bug fixes and non-trivial logic.
- Backend logic should have tests for success cases, invalid input, and unauthorized access when relevant.
- Frontend logic should have tests for non-trivial state transitions when test infrastructure exists.
- If no automated test exists for the changed area yet, document manual verification in the PR.

Manual verification examples:

```text
Created a diary entry with one photo on iOS simulator.
Confirmed invalid login shows an error and does not navigate.
Confirmed restaurant search shows cached results when Kakao request fails.
```

## Documentation

Update `README.md` when a change affects:

- Setup instructions
- Run commands
- Test commands
- Environment variables
- Database setup or migrations
- External service setup, such as Supabase or Kakao
- Project architecture

Use code comments sparingly. Add comments only when they explain why something is done, not what obvious code already says.

## Definition Of Done

A task is done when:

- The requested behavior is implemented.
- The code is small, readable, and scoped to the task.
- Relevant tests pass, or manual verification is documented.
- API, schema, environment, or setup changes are documented.
- The PR has at least one review.
- The branch is merged into `main`.
