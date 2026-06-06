# Team 6 Final Client Meeting Plan

## Purpose

This is the third and final client-developer sync before the final presentation. Since the first two meetings already covered product concept, UI direction, backend/algorithm direction, and open design concerns, this meeting should focus on final acceptance and presentation alignment.

Success criteria:

1. Close the unresolved action items from the May 8 and May 21 client meetings.
2. Confirm the final demo mode and presentation framing.
3. Get explicit approval for any SRS items treated as future work.
4. Leave with only small implementation or slide updates.

## Prior Client Meetings Reviewed

Source: Notion `CS350` page.

### May 8 Client-Dev Meeting

Already covered:

- Core product: personal food diary from meal photos, not a social-sharing app.
- Target users: people who take meal photos but do not turn them into useful records.
- UX goal: keep recording simple and non-disruptive during meals.
- Proposed backend: Python/FastAPI.
- Proposed frontend: mobile app, originally React Native, supporting iOS and Android.
- Kakao Map API as map/restaurant source.
- Recommendation feature is additional to the core diary flow.
- Recommendation should use diary text/embeddings, not only ratings.
- Recommendation should be based on accumulated user history, not one diary entry.
- Early recommendation threshold discussed as more than 5 diary entries.

Unresolved from May 8:

- Team needed to provide more detail about recommendation algorithm implementation.
- Team needed to clarify how inconsistent user preferences across entries are handled.

### May 21 Client-Dev Meeting

Already covered:

- UI flow: onboarding, passwordless login, profile setup, main page, drafts, restaurant search/filter, restaurant detail, capture/upload, photo preview, diary, taste analysis.
- Drafts are important because users may take photos now and write details later.
- Taste analysis screen includes category preferences, favorite dishes, six taste dimensions, and food type preferences.
- Taste analysis threshold was assumed as 10 meals.
- Algorithm direction: diary entries, Kakao restaurant data, and context data feed taste analysis/recommendations.
- Recommendation signals: content, collaborative, and context.
- Collaborative signal uses similar users and category rating vectors.
- Context signal includes distance, time, and filters.
- Fake/mock data testing was expected for algorithm validation.
- Final presentation/deployment format was still unclear: actual distribution vs local demo.
- Tech stack changes are acceptable if documented with justification.

Unresolved from May 21:

- Decide final distribution/local deployment approach for presentation.
- Document tech stack changes with justification.
- Share algorithm implementation details.
- Test taste analysis/recommendation with fake/mock data.

## Do Not Spend Meeting Time Repeating

Avoid reopening these unless Team 6 objects:

- The basic food diary concept.
- Whether this is social/sharing oriented. It is not.
- Why Kakao is used.
- Whether recommendations should use diary context. They should.
- Whether taste analysis has a dedicated screen. It does.
- The broad UI flow from onboarding to capture to diary.
- The existence of content/collaborative/context recommendation signals.

## Current Implementation Snapshot

- Frontend: Next.js mobile-style web app.
- Backend: FastAPI REST API.
- Data layer: Postgres and MinIO.
- Algorithm: Python package integrated through backend calls.
- Core demo path exists: auth -> restaurant explore/search -> bookmark -> capture/upload -> draft -> finalize -> diary -> taste profile/recommendations.
- Frontend can run with MSW mocks or real backend.
- Algorithm package includes tests and logic for entry profiling, taste report generation, hybrid recommendation scoring, diversity, novelty, exposure handling, and explanation text.

## Proposed Agenda

1. Confirm this is the final sync and that we will focus on closure.
2. Briefly summarize what changed since the May 21 meeting.
3. Demo the implemented core flow.
4. Walk through unresolved prior action items.
5. Resolve final demo and presentation framing.
6. Record remaining tasks and sign-off.

## Demo Path

Use this order if demonstrating live:

1. Sign in with magic link.
2. Use location or fallback location.
3. Explore nearby restaurants.
4. Search/filter restaurants.
5. Bookmark a restaurant.
6. Capture or upload food photos.
7. Preview photos and create a draft.
8. Finalize the draft into a diary entry.
9. View diary list and diary detail.
10. View taste profile.
11. View recommendation feed.

Recommended demo setup:

- Primary: seeded real backend data.
- Backup: MSW mock data.
- Avoid relying only on live Kakao data during the presentation.

## Final Questions to Ask

### 1. Did We Close the Recommendation Algorithm Action Item?

Question: Does the current algorithm explanation satisfy the May 8/May 21 request for more recommendation detail?

Show or summarize:

- Entry profiling from text, image labels/references, metadata, rating, time, and location.
- User profile aggregation with long-term and short-term preferences.
- Restaurant profiling from Kakao metadata.
- Recommendation scoring with content, collaborative, context, quality, novelty, and diversity signals.
- Explanation text returned without exposing raw scores.
- Tests using deterministic and synthetic data.

Decision to record:

- Algorithm detail is sufficient for final presentation.
- Or Team 6 wants one more diagram/table added to slides.

### 2. How Should We Explain Inconsistent Preferences?

Question: Does our long-term/short-term profile approach answer the earlier concern that users may focus on different things across entries?

Proposed answer:

- Long-term profile captures stable preferences.
- Short-term profile captures recent shifts.
- Entry weighting uses recency, signal richness, and confidence.
- The recommendation system combines taste, context, quality, novelty, and diversity rather than assuming every diary has the same meaning.

Decision to record:

- This explanation is acceptable.
- Or Team 6 wants a simpler user-facing explanation.

### 3. What Threshold Should We Present?

Question: What minimum-entry threshold should we claim in the final demo?

Prior notes:

- May 8 discussed recommendations after more than 5 entries.
- May 21 assumed taste analysis after 10 meals.

Current implementation:

- Taste profile threshold: 10 entries.
- Recommendation threshold: 3 entries.

Recommendation:

- Present taste analysis threshold as 10.
- Align recommendation threshold with Team 6's expectation before final, or explicitly say recommendation is available earlier as a lightweight feed.

Decision to record:

- Taste threshold
- Recommendation threshold
- Whether code or slides need to change

### 4. Is the Platform Change Acceptable If Documented?

Question: Since earlier meetings expected a mobile app/React Native-style client, is a Next.js mobile-style prototype acceptable if we document the stack change?

Prior note:

- May 21 explicitly said tech stack can be modified if documented with justification.

Proposed justification:

- Same mobile-first UX flow.
- Faster course-demo iteration.
- Browser camera/gallery support covers the demo capture flow.
- Backend and algorithm contracts remain framework-independent.

Decision to record:

- Accepted with slide/documentation note.
- Or one specific native behavior must be simulated before final.

### 5. What Is the Final Presentation Deployment Mode?

Question: Should the final presentation use local demo, deployed demo, or recorded backup?

Prior note:

- May 21 left distribution vs local deployment unclear.
- Team is not targeting commercial distribution; course requirements matter most.

Recommendation:

- Local real-backend demo with seeded data.
- Recorded backup video or screenshots.
- MSW backup if backend/Kakao has issues.

Decision to record:

- Primary presentation mode
- Backup mode
- Whether deployment is required

### 6. Which UI Promises Must Be Demonstrated?

Question: From the May 21 UI flow, which screens must appear in the final demo?

Candidate must-show screens:

- Onboarding/login
- Main page with drafts and restaurant recommendations
- Search/filter
- Restaurant detail
- Capture/upload and preview
- Draft finish screen
- Diary list/detail
- Taste analysis
- Recommendation feed

Decision to record:

- Must-show screens
- Optional screens
- Screens safe to mention only briefly

### 7. What Should We Say About Notifications?

Question: Is it acceptable to present meal-completion reminders as an MVP/polling or future-work item?

Why ask:

- May 21 UI flow discussed notification prompts after leaving restaurant.
- Current MVP docs explicitly allow polling instead of push notifications.

Decision to record:

- Must implement/present notification behavior.
- Or present as future work/MVP limitation.

### 8. Should Rating or Note Be Required?

Question: Which diary finalization rule should the final demo follow?

Prior notes:

- May 8 described star rating as optional.
- The SRS says rating is required and comment is optional.

Current implementation:

- Note/comment is required.
- Rating is optional.

Decision to record:

- Keep current behavior because it matches the early UX discussion.
- Or change to match the SRS exactly.

### 9. Which Deferred SRS Items Are Acceptable?

Question: Which of these can be documented as future work?

Candidate future-work items:

- Native app packaging.
- Push notifications.
- Full offline sync.
- Cursor-based infinite scroll.
- Async taste-analysis job queue.
- Account deletion recovery UI.
- Production HTTPS/deployment hardening.
- Advanced search backend beyond current MVP search.

Decision to record:

- Accepted future-work items
- Any item that blocks final acceptance

### 10. What Should the Final Presentation Emphasize?

Question: What three points should we emphasize most?

Suggested emphasis:

- End-to-end diary workflow from photo to saved entry.
- Taste analysis from accumulated diary history.
- Personalized recommendations with explanation text.
- Algorithm testing/evaluation using synthetic data.
- Privacy/security basics: owner-only data, signed image URLs, no score exposure.

Decision to record:

- Top three presentation priorities
- Any topic to avoid overclaiming

## Decision Log

Fill this during the meeting.

| Topic | Decision | Owner | Deadline |
| --- | --- | --- | --- |
| Recommendation detail sufficient? |  |  |  |
| Inconsistent preference explanation |  |  |  |
| Taste/recommendation thresholds |  |  |  |
| Next.js/mobile-web framing |  |  |  |
| Final demo/deployment mode |  |  |  |
| Must-show UI screens |  |  |  |
| Notification/reminder handling |  |  |  |
| Rating/note requirement |  |  |  |
| Accepted future-work items |  |  |  |
| Final presentation emphasis |  |  |  |

## Follow-Up Message Template

Send this after the meeting.

```text
We completed the final Team 6 client-developer sync before the final presentation.

Closed prior action items:
- Recommendation algorithm detail: ...
- Inconsistent preference handling: ...
- Mock/fake data validation: ...

Final demo mode:
- Primary: ...
- Backup: ...

Final presentation framing:
- ...

Implementation changes before final:
- ...

Items documented as future work:
- ...
```

