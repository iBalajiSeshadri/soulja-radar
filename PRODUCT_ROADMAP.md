# Product Roadmap — make soulja-radar a shareable multi-league tool

Goal: any Sleeper user pastes their LEAGUE ID (or draft ID) and the app works for
THEIR league — scoring, roster, managers, and behavioral intelligence — with no
Soulja-specific hardcodes. Deferred until AFTER the 2026-08-29 Soulja draft to
avoid destabilizing the draft-day path.

## DONE (committed, safe, backward-compatible)
- `sleeper_live.league_config(league_id)` — pulls scoring_settings + roster_positions,
  auto-detects superflex / IDP / teams / budget / roster slots. (commit a73f969)
- `sleeper_live.fit_league_behavior(league_id, clean_name)` — walks
  previous_league_id chain, pulls completed drafts (AUCTION + SNAKE), fits
  per-manager aggression / top3 / positional lean / nominate-early (auction) and
  early-round lean (snake), plus league position-depth + premium. Verified it
  reproduces the manual Soulja analysis with zero local files. (commit a73f969)
- `fantasy_engine.calculate_master_board(scoring, starters, superflex, include_idp)`
  — parameterized so the VORP board can rebuild for ANY league's scoring; defaults
  to Soulja config (backward compatible). (commit 95b65f6)

## REMAINING (the app wiring — do next, ideally behind an opt-in flag)
1. **Dynamic board rebuild on connect (Task 2 wire):** when a non-preset league
   connects, call `calculate_master_board(scoring=cfg['scoring'],
   starters=<derived from start_slots>, superflex=cfg['superflex'],
   include_idp=cfg['include_idp'])` and cache the resulting board per league_id
   (it scrapes FFToday+Sleeper, ~30-60s — show a spinner, cache hard).
2. **De-personalize managers (Task 4):** stop relying on `SOULJA_SOULJA_DEFAULTS`
   in the render path. Managers come from live league users; archetype title +
   counter-exploit GENERATED from fitted behavior (aggression bands + lean).
   Keep Soulja as an OPTIONAL preset fallback, not the default.
3. **Thread live data through the ~15 touchpoints (Task 5):** board load, wallets,
   rival tab chart+exploits, MC pricing (`build_rivals_for_sim` -> use live
   `by_handle` fit), nomination depth, Should-I-Bid/Draft. Replace the
   `auction_fit.json` file read with the in-memory live fit when connected.
4. **Snake behavioral surfacing:** show snake managers' early-round positional
   lean + reach tendency in the rival tab (auction shows $ behavior; snake shows
   draft-capital behavior).
5. **Verify on a REAL friend league** (one auction, one snake) headless before
   shipping. Keep Soulja's stable pre-built board path untouched.

## SAFETY NOTE
Do NOT run the live board rebuild on the Soulja draft-day path. Soulja uses the
committed pre-built `top_150_draft_board.csv` + `auction_fit.json`. The product
path should be additive/opt-in so the personal path stays frozen and reliable.
