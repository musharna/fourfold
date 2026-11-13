# fourfold-lab house style (adapted from agent-zoo analysis/theme_zoo.R): every figure script sources this
# file; restyle here, never inline.
suppressPackageStartupMessages(library(ggplot2))

ff_ink <- "#1f2328"
ff_grid <- "#e6e8eb"
ff_muted <- "#57606a"

# one color per model family; conditions are shown by shape/fill, not color
ff_model_cols <- c(Sol = "#2f6f9f", Opus = "#c4622d", Sonnet = "#d4a21f", Qwen = "#6a4c93")

# scripted-ceiling figures: what the scripted cell achieved, the bound no cell can beat, a reference run length
ff_ceiling_cols <- c("Scripted cell (achieved)" = ff_ink, "Limit for any cell" = "#c4622d",
                     "Length of the original 4-bit model run" = "#2f6f9f")
ff_ceiling_shapes <- c("Scripted cell (achieved)" = 16, "Limit for any cell" = 4,
                       "Length of the original 4-bit model run" = 17)

theme_fourfold <- function(base_size = 12) {
  theme_minimal(base_size = base_size) %+replace%
    theme(
      text = element_text(colour = ff_ink),
      plot.title = element_text(face = "bold", size = rel(1.15), hjust = 0, margin = margin(b = 4)),
      plot.subtitle = element_text(colour = ff_muted, hjust = 0, margin = margin(b = 10)),
      plot.title.position = "plot",
      panel.grid.major = element_line(colour = ff_grid, linewidth = 0.4),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_blank(),
      strip.text = element_text(face = "bold", hjust = 0, margin = margin(b = 4)),
      legend.position = "top",
      legend.justification = "left",
      legend.title = element_blank(),
      axis.title = element_text(colour = ff_muted),
      plot.background = element_rect(fill = "white", colour = NA),
      plot.margin = margin(12, 14, 10, 12)
    )
}

ff_save <- function(p, path, w = 8, h = 5) {
  ggsave(path, p, width = w, height = h, dpi = 200, bg = "white")
  message("wrote ", path)
}
