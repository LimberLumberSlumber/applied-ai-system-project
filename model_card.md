# Model Card: ShowTime Planner

## System summary

ShowTime Planner extends my PawPal+ pet-care scheduler. It retrieves movie and TV data (bundled catalog, optionally TMDB), computes how many minutes a viewing needs for a chosen mode, fits that into the free windows left by the user's busy blocks, and reports a confidence score and related titles. It does not use a generative model to produce answers. The "AI" parts are retrieval, rule-based reasoning, scoring, and guardrails.

## Limitations and biases

- **Small, hand-built catalog.** The 21 bundled titles were chosen by me and the AI during the session and entered from memory. I later compared them with TMDB: most matched, Stranger Things was corrected, and episode counts for The Office and Parks and Recreation differ slightly from TMDB (likely merged double episodes). Dark and Avatar: The Last Airbender could not be compared because TMDB search returned different shows. Treat catalog numbers as approximate. Live TMDB data is more trustworthy but was spot-checked only a few times.
- **Popularity and language bias.** The catalog is mostly well-known English-language titles, with a few exceptions (Parasite, Spirited Away, Dark). Related-title suggestions are only drawn from the catalog, so they favor those titles and rarely suggest anything obscure.
- **Same-creator bias in suggestions.** Ranking rewards shared director, cast, and genre, so users get "more of the same" and little variety.
- **Average episode runtime.** Shows use one typical episode length. Real episodes vary, so season and series totals are estimates.
- **Planning is simple.** One day only, greedy placement, no time zones, no preference for evening viewing, and a movie may be split across windows.
- **Matching can be wrong.** Fuzzy matching and TMDB's top search hit can pick the wrong title. The system warns on non-exact matches and lowers confidence, but the user must confirm. The confidence value is a heuristic, not a calibrated probability.
- **Weak typo handling on the live path.** A typo that TMDB cannot resolve, and that the catalog does not contain, ends in an error.

## Potential misuse and prevention

This is a low-risk tool. The realistic risks are small:
- **Leaking the API key.** The key is read from an environment variable or a gitignored `.env`, never stored in code or the repo.
- **Overloading or misusing TMDB.** Requests have a timeout, one search per plan, and no scraping loop. TMDB data is not cached into the repo, and the required attribution is shown.
- **Over-trusting the output.** A wrong match could waste someone's evening, nothing worse. Mitigations are warnings, a visible source label, a confidence score, and a low-confidence notice. A human reads these before acting.
- **Bad input.** Invalid times, impossible seasons, and unknown titles are rejected with clear errors instead of silently producing a plan.

## What surprised me while testing reliability

- The first version of related titles ranked a movie above a same-kind show, because genre overlap alone was a tie. A tiny same-kind bonus fixed it. The tie was only visible by reading real output, not from the unit tests I had written.
- Live matches initially got a confidence of 1.0 whenever TMDB returned anything, which was overconfident. Scoring by name similarity made the number mean something.
- Retrieval helped in an unexpected way. A live title missing from the catalog (Oppenheimer) still produced catalog-based related suggestions because its director and genres matched.
- The offline path is more forgiving of typos than the live path, which is the opposite of what I expected.

## Evaluation results

From `python eval.py` (offline): 13 of 13 cases passed, average confidence on accepted plans 0.93. From pytest: 49 passed. Full outputs are in the README and in `assets/`. These cases were written by me against my own catalog, so they show consistency, not accuracy against the real world.

## Collaboration with AI

I used Claude Code (Sonnet) throughout: planning the project, proposing the architecture, writing the code and tests, running them, and drafting the documentation. I reviewed and approved the plan before any code was written, answered scoping questions, and supplied the TMDB key and the product idea.

- **Suggestion I accepted:** keep a bundled offline catalog as the base and treat the live API as an optional second source with a fallback. It made the project runnable and gradable without a key, and it made the tests independent of the network. I also accepted the suggestion to build the evaluation harness and the multi-source retrieval stretch features.
- **Suggestions I changed or scoped down:**
  - I asked for an IMDb API. The AI pointed out IMDb has no free public API, proposed TVmaze, and I redirected to TMDB, which covers movies and TV with one key. That version was adopted.
  - I asked for a recommendation carousel. It was scoped down to a row of three text cards ranked by shared director, cast, and genre. A real image carousel and alternative recommendation sources are left as later work.
  - The first confidence design gave live results a fixed 1.0. I changed it to scale with how closely the returned title name matches what the user typed.

## Future improvements

- Verify the catalog against a real source and grow it.
- Multi-day planning, preferred viewing times, and calendar import.
- Use TMDB recommendations and ratings in the related-title ranking, and add an image carousel.
- Better typo handling on the live path, for example retrying with a fuzzy-corrected query.
- Optional LLM step for friendlier explanations, kept behind the same guardrails.
