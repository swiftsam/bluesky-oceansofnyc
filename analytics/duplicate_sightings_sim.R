library(dplyr)
library(purrr)
library(ggplot2)

kTotalOceans = 2062

observation <- function(observation_index,
                        total_oceans = kTotalOceans, 
                        sighting_count = kTotalOceans * 5) {
  tibble(
    obs_id = observation_index,
    sighting_id = 1:sighting_count,
    sighted = sample(total_oceans, sighting_count,replace = TRUE),
    unique_sightings = cumsum(!duplicated(sighted)),
    sighting_pct = unique_sightings / total_oceans,
    sighting_ratio = sighting_id / total_oceans
  )
}

sims <- list_rbind(map(1:1000, observation))

# Ratio cumulative unique sightings
sims |>
  sample_n(1000) |>
  ggplot(aes(x = sighting_ratio, y = sighting_pct)) +
  geom_smooth() +
  scale_x_continuous(labels = scales::percent) +
  scale_y_continuous(labels = scales::percent) +
  theme_bw() 

# Nominal cumulative unique sightings
sims |>
  sample_n(1000) |>
  ggplot(aes(x = sighting_id)) +
  geom_hline(yintercept = kTotalOceans, color = "red") +
  geom_vline(xintercept = 48, linetype = "dashed") +
  #geom_abline(slope = 1, intercept = 0) +
  geom_smooth(aes(y = unique_sightings)) +
  labs(
    x = "Number of Sightings", 
    y = "Unique Sightings", 
    title = "How many sightings will it take to find them all?",
    subtitle = "The last 500 are gonna be tough") + 
  theme_bw()

## Identify the first duplicate sighting in each simulation
first_dupes <- sims |>
  filter(unique_sightings < sighting_id) |>
  group_by(obs_id) |>
  summarise(first_dupe = min(sighting_id)) |>
  arrange(first_dupe) |>
  mutate(cumulative_prob = row_number() / n() )
  
# Cumulative probability of seeing a dupe
first_dupes |>
  filter(first_dupe < 100) |>
  ggplot(aes(first_dupe, cumulative_prob)) +
  geom_smooth() +
  geom_vline(xintercept = 48, linetype = "dashed") +
  scale_x_continuous(breaks = seq(0,100,5)) + 
  scale_y_continuous(labels = scales::percent, breaks = seq(0,1,.1)) +
  labs(x = "Sighting Count", 
       y = "Probabiliyt of first dupe", 
       title = "When should we expect to find our first dupe?",
      subtitle = "we should start to be be surprised if we don't get a dupe in the next 15 or so") + 
  theme_bw()