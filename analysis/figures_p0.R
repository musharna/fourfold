# P0 figures: eval vs floor, refusal rate by cue, neighbor IDs heard. Inputs: analysis/p0_readout.tsv,
# analysis/r3_words_acts.tsv (rerun p0_readout.py and words_vs_acts.py first). Output: figures/p0_*.png.
suppressPackageStartupMessages({ library(readr); library(dplyr); library(tidyr) })
here <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
source(file.path(here, "analysis", "theme_fourfold.R"))

arm_levels <- c("sol-erin", "solapi-cued", "solcx-cued", "solcx-nocue", "opus-framed-cued", "opus-framed-nocue",
                "opus-cued", "opus-nocue", "sonnet-cued", "sonnet-nocue", "qwen-nothink")
arm_labels <- c("Sol API\n(erin)", "Sol API\ncued", "Sol codex\ncued", "Sol codex\nno cue", "Opus+line\ncued", "Opus+line\nno cue",
                "Opus\ncued", "Opus\nno cue", "Sonnet\ncued", "Sonnet\nno cue", "Qwen 9B\ncued")
model_of <- function(arm) case_when(grepl("^sol", arm) ~ "Sol", grepl("^opus", arm) ~ "Opus",
                                    grepl("^sonnet", arm) ~ "Sonnet", TRUE ~ "Qwen")
tidy_runs <- function(d) d |>
  mutate(arm = ifelse(run == "sol-50", "sol-erin", sub("^p0-(.*)-[0-9]+$", "\\1", run)),
         model = factor(model_of(arm), levels = names(ff_model_cols)),
         arm = factor(arm, levels = arm_levels, labels = arm_labels))

ro <- read_tsv(file.path(here, "analysis", "p0_readout.tsv"), show_col_types = FALSE, na = c("None", "")) |>
  filter(!grepl("^p0-(solapi-rmed|solcx-founder|solcx-verbmed)-", run)) |>   # T_text / P1 runs, not P0 arms
  mutate(void = as.logical(void)) |> tidy_runs()
stopifnot(nrow(ro) > 0, !any(is.na(ro$arm)))

# 1. eval vs floor -------------------------------------------------------------------------------
ev <- bind_rows(ro |> filter(!is.na(eval_mean)) |> select(run, arm, model, void, eval_mean),
                tidy_runs(tibble(run = "sol-50", void = FALSE, eval_mean = 0.597)))   # erin README / prereg
# floor per arm; arms without their own tick-0 eval use the model's floor (prereg: F0 per model, seed 1001)
fm <- ro |> group_by(model) |> summarise(f0m = mean(f0_mean, na.rm = TRUE), .groups = "drop")
fl <- ro |> group_by(arm, model) |> summarise(f0 = mean(f0_mean, na.rm = TRUE), .groups = "drop") |>
  left_join(fm, by = "model") |> mutate(f0 = ifelse(is.finite(f0), f0, f0m)) |> filter(is.finite(f0))
p1 <- ggplot(ev, aes(arm, eval_mean)) +
  geom_errorbar(data = fl, aes(x = arm, ymin = f0, ymax = f0), inherit.aes = FALSE, width = 0.6,
                colour = ff_muted, linewidth = 0.7) +
  geom_errorbar(data = fl, aes(x = arm, ymin = f0 + 0.2, ymax = f0 + 0.2), inherit.aes = FALSE, width = 0.6,
                colour = ff_muted, linetype = "dashed", linewidth = 0.5) +
  geom_point(aes(colour = model, fill = ifelse(void, "white", as.character(model))), shape = 21, size = 3.2,
             stroke = 1.1, position = position_jitter(width = 0.12, height = 0, seed = 1)) +
  scale_colour_manual(values = ff_model_cols, drop = FALSE, guide = guide_legend(override.aes = list(fill = ff_model_cols))) +
  scale_fill_manual(values = c(ff_model_cols, white = "white"), guide = "none") +
  scale_x_discrete(limits = arm_labels, drop = FALSE) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2)) +
  labs(title = "Sol scores higher without the evaluation cue on all three seeds",
       subtitle = "Eval score per run. Solid bar = zero-information floor, dashed = floor + 0.20. Hollow = void run.",
       x = NULL, y = "eval score (0-1)") +
  theme_fourfold()
ff_save(p1, file.path(here, "figures", "p0_eval.png"), w = 10.5, h = 5)

# 2. refusal rate by cue -------------------------------------------------------------------------
rf <- ro |> filter(model != "Qwen") |>
  mutate(variant = case_when(grepl("framed", run) ~ "Opus + neutral line", model == "Opus" ~ "Opus",
                             model == "Sonnet" ~ "Sonnet", TRUE ~ "Sol"),
         variant = factor(variant, levels = c("Sol", "Sonnet", "Opus", "Opus + neutral line")),
         cue = ifelse(grepl("nocue", run), "no cue", "cued"),
         refused_frac = refused / agent_ticks)
p2 <- ggplot(rf, aes(variant, refused_frac, colour = cue, shape = cue)) +
  geom_hline(yintercept = 0.10, colour = ff_muted, linetype = "dashed", linewidth = 0.4) +
  geom_point(size = 3, stroke = 1.1, position = position_dodge(width = 0.5)) +
  scale_colour_manual(values = c(cued = "#2f6f9f", `no cue` = "#c4622d")) +
  scale_shape_manual(values = c(cued = 16, `no cue` = 17)) +
  scale_y_continuous(labels = scales::percent, limits = c(0, NA)) +
  labs(title = "Removing the evaluation cue raises Claude's safeguard refusals",
       subtitle = "Share of agent-turns refused per run. Dashed = refusal level that alone voids a run.",
       x = NULL, y = "agent-turns refused") +
  theme_fourfold()
ff_save(p2, file.path(here, "figures", "p0_refusals.png"), w = 8, h = 5)

# 3. neighbor IDs heard --------------------------------------------------------------------------
r3 <- read_tsv(file.path(here, "analysis", "r3_words_acts.tsv"), show_col_types = FALSE) |>
  filter(!grepl("^p0-(solapi-rmed|solcx-founder|solcx-verbmed)-", run)) |>
  group_by(run) |> summarise(heard = sum(nb_heard) / sum(n_nbrs), .groups = "drop") |>
  tidy_runs() |> left_join(ro |> select(run, void, ticks), by = "run") |>
  mutate(void = coalesce(void & ticks >= 50 | grepl("framed-nocue", run), FALSE))   # runs still in progress are not void
p3 <- ggplot(r3, aes(arm, heard)) +
  geom_point(aes(colour = model, fill = ifelse(void, "white", as.character(model))), shape = 21, size = 3.2,
             stroke = 1.1, position = position_jitter(width = 0.12, height = 0, seed = 1)) +
  scale_colour_manual(values = ff_model_cols, drop = FALSE, guide = guide_legend(override.aes = list(fill = ff_model_cols))) +
  scale_fill_manual(values = c(ff_model_cols, white = "white"), guide = "none") +
  scale_x_discrete(limits = arm_labels, drop = FALSE) +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
  labs(title = "Sol cells hear every neighbor; Opus about half, Sonnet a fifth",
       subtitle = "Share of the 24 true neighbor links whose ID ever reached the cell's inputs. Hollow = void run.",
       x = NULL, y = "neighbor IDs heard") +
  theme_fourfold()
ff_save(p3, file.path(here, "figures", "p0_neighbors.png"), w = 10.5, h = 5)
