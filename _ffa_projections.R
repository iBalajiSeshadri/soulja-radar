#!/usr/bin/env Rscript
# _ffa_projections.R — COMPARISON ONLY. Writes projections_ffa.csv, touches nothing live.
# Scrapes multiple sources via ffanalytics, scores by the Soulja Soulja league rules,
# and exports the ROBUST (outlier-resistant) multi-source projection per player.

suppressMessages(library(ffanalytics))
suppressMessages(library(dplyr))

# --- Soulja Soulja scoring (mirrors config.py SCORING_WEIGHTS) ---
sc <- scoring
sc$pass$pass_yds     <- 0.05
sc$pass$pass_tds     <- 4
sc$pass$pass_int     <- -2
sc$pass$pass_inc     <- -0.2      # incompletion tax
sc$pass$pass_300_yds <- 3        # ~bonus_pass_300 (our threshold is 4000 season; closest FFA knob)
sc$rush$all_pos      <- TRUE
sc$rush$rush_yds     <- 0.1
sc$rush$rush_att     <- 0.1
sc$rush$rush_tds     <- 6
sc$rush$rush_100_yds <- 4
sc$rec$all_pos       <- TRUE
sc$rec$rec           <- 0.4       # 0.4 PPR
sc$rec$rec_yds       <- 0.1
sc$rec$rec_tds       <- 6
sc$rec$rec_100_yds   <- 5
sc$misc$sacks        <- -1        # pass_sack -1 (QB)
# TE PREMIUM: our league adds bonus_rec_te (0.5/rec) for TEs. FFA scores rec uniformly by
# position group, so we can't set a TE-only rec rate here cleanly. Instead we export FFA at
# BASE 0.4 and re-apply the TE premium in the Python comparison using each TE's projected
# receptions (recovered from the raw scrape avg-stats), so the compare is apples-to-apples.

pos <- c("QB","RB","WR","TE")
message("Scraping 2026 projections (multi-source)...")
scr <- tryCatch(
  scrape_data(pos = pos, season = 2026, week = 0),
  error = function(e) { message("scrape error: ", conditionMessage(e)); NULL }
)
if (is.null(scr)) quit(status = 1)

proj <- projections_table(scr, scoring_rules = sc)
# attach player names/teams/positions
proj <- tryCatch(add_player_info(proj), error=function(e){ message("add_player_info failed: ", conditionMessage(e)); proj })

# projections_table returns standard/weighted/robust per player via avg_type column.
# Keep the ROBUST average (outlier-resistant = the FFA-recommended choice).
out <- proj %>%
  filter(avg_type == "robust") %>%
  select(any_of(c("id","first_name","last_name","player_name","team","position","pos","points","floor","ceiling","sd_pts")))

# build readable name if needed
if (!("player_name" %in% names(out)) && all(c("first_name","last_name") %in% names(out))) {
  out$player_name <- trimws(paste(out$first_name, out$last_name))
}
write.csv(out, "projections_ffa.csv", row.names = FALSE)
message(sprintf("Wrote projections_ffa.csv: %d rows (robust avg).", nrow(out)))
