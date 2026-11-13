# scripted-ceiling figures. Inputs: analysis/ceiling_by_tick.tsv, analysis/ceiling_widths.tsv (rerun
# `python analysis/ceiling_check.py --widths` first). Output: figures/ceiling_*.png.
suppressPackageStartupMessages({ library(readr); library(dplyr) })
here <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
source(file.path(here, "analysis", "theme_fourfold.R"))

# 1. score by tick ---------------------------------------------------------------------------------
bt <- read_tsv(file.path(here, "analysis", "ceiling_by_tick.tsv"), show_col_types = FALSE) |>
  filter(set == "main", role == "all", T <= 8)
stopifnot(nrow(bt) == 9)
# the limit: after tick T a cell cannot name an id more than T hops away (one hop per tick), so its map part is
# at most (cells within T hops) / 9; the other four parts are capped at 1. unknown at tick 0, so not drawn there.
cells <- expand.grid(r = 0:2, c = 0:2)
limit <- bind_rows(lapply(1:8, function(T) {
  ball <- sapply(seq_len(nrow(cells)), function(i) sum(abs(cells$r - cells$r[i]) + abs(cells$c - cells$c[i]) <= T))
  tibble(T = T, mean = mean((4 + ball / 9) / 5), line = "Limit for any cell")
}))
curve <- bind_rows(transmute(bt, T, mean, line = "Scripted cell (achieved)"), limit)
p1 <- ggplot(curve, aes(T, mean, colour = line, linetype = line)) +
  geom_line(linewidth = 0.8) + geom_point(size = 2.2) +
  scale_colour_manual(values = ff_ceiling_cols) +
  scale_linetype_manual(values = c("Scripted cell (achieved)" = "solid", "Limit for any cell" = "dashed")) +
  scale_x_continuous(breaks = 0:8) + scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2)) +
  labs(title = "A scripted cell scores a perfect quiz after tick 4, the earliest possible",
       subtitle = sprintf("Mean eval score of 9 cells, %d worlds (3x3, 128-bit ports)", bt$n[1] / 9),
       x = "quiz taken after tick", y = "eval score (0-1)") +
  theme_fourfold()
ff_save(p1, file.path(here, "figures", "ceiling_by_tick.png"))

# 2. first perfect tick by port width --------------------------------------------------------------
wd <- read_tsv(file.path(here, "analysis", "ceiling_widths.tsv"), show_col_types = FALSE)
stopifnot(nrow(wd) == 6, all(wd$late_worlds == 0))
orig <- "Length of the original 4-bit model run"
long <- bind_rows(
  transmute(wd, port_bits, tick = first_perfect_max, line = "Scripted cell (achieved)"),
  transmute(wd, port_bits, tick = floor, line = "Limit for any cell"),
  tibble(port_bits = 4, tick = 130, line = orig))   # original README: "they never found each other in 130 ticks"
p2 <- ggplot(long, aes(port_bits, tick, colour = line, shape = line)) +
  geom_line(data = filter(long, line != orig), linewidth = 0.8) +
  geom_point(size = 2.8, stroke = 1.2) +
  scale_colour_manual(values = ff_ceiling_cols) + scale_shape_manual(values = ff_ceiling_shapes) +
  scale_x_continuous(trans = "log2", breaks = wd$port_bits) +
  scale_y_continuous(trans = "log2", breaks = c(4, 8, 16, 32, 64, 128), limits = c(3.5, 140)) +
  labs(title = sprintf("Even at 4 bits per port a scripted cell is perfect by tick %d", wd$first_perfect_max[wd$port_bits == 4]),
       subtitle = sprintf("First tick after which all nine cells score 1.0, %d worlds per width (3x3). Both axes double per step.", wd$worlds[1]),
       x = "port width (bits)", y = "tick") +
  theme_fourfold() + guides(colour = guide_legend(ncol = 1), shape = guide_legend(ncol = 1))
ff_save(p2, file.path(here, "figures", "ceiling_widths.png"), h = 5.8)
