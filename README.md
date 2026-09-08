# ECMWF Ensemble Energy Weather Risk Monitor

I made this project to explore how ECMWF ensemble forecasts can be used in European energy analytics. My background is in scientific modelling, Python and large multidimensional datasets. I wanted to apply these skills to a practical weather problem and learn more about ensemble weather prediction.

The project gives a 10-day view of weather signals that can be relevant for energy markets. It focuses on three simple proxy regions: the Nordic area, Germany and France.

I use the data to answer four questions:

1. What do the forecasts show for 2 m temperature and 100 m wind speed?
2. How large is the ensemble spread, and how does it change with lead time?
3. How different is the current forecast from the previous 00 UTC run?
4. Which large-scale circulation scenarios are present over the North Atlantic and Europe at day 10?

This is a weather-analysis example. It is not a forecast of electricity prices, demand, hydropower or wind generation.

## Why use an ensemble forecast?

One weather forecast gives only one possible future. An ensemble contains many forecasts with slightly different starting conditions or model behaviour. Looking at all members gives more information about uncertainty.

In this project I use:

- the **ensemble mean** as the main forecast signal;
- the **ensemble standard deviation** as a measure of spread;
- **event probabilities** for selected rain and wind thresholds;
- a comparison with the previous model run to show how the forecast has changed;
- clustering of individual ensemble members to find different circulation scenarios.

A large spread means that the members disagree more. It does not directly tell us the forecast error. Forecast error can only be measured later against observations or reanalysis data.

## Example results

The example saved in this repository uses the ECMWF forecast initialised at 00 UTC on 7 September 2026.

### Temperature signal and forecast change

![Day-7 European temperature signal, uncertainty, and forecast change](figures/forecast_change_map.png)

The first map shows the day-7 ensemble-mean temperature. The second map shows the ensemble spread. The third map compares the same valid time in two forecast runs.

For this case, the newer run is warmer across much of northern and eastern Europe. The spread is also larger toward Scandinavia and eastern Europe. This tells us where the forecast is changing and where the members disagree. It does not show which run will be more accurate.

### Day-10 circulation scenarios

![Day-10 IFS ensemble circulation scenarios](figures/z500_scenario_clusters.png)

This figure groups the 51 IFS ensemble members into four scenarios using their 500 hPa geopotential-height patterns. The four groups contain 29.4%, 29.4%, 23.5% and 17.6% of the members.

Z500 describes the large-scale position of ridges and troughs in the middle atmosphere. Different patterns can lead to different temperature, wind and precipitation conditions over Europe. The percentages are the fractions of members in each group. They are not calibrated probabilities of recognised weather regimes.

### Other results

- [Regional 10-day temperature and 100 m wind outlook](figures/regional_energy_outlook.png)
- [Regional rain and wind event probabilities](figures/energy_event_probabilities.png)

For this example, the regional mean of the gridpoint probability for at least 5 mm of precipitation in 24 hours reaches 46.1% in the Nordic proxy region for the period ending 9 September. This does not mean that there is a 46.1% probability that the whole region receives more than 5 mm. It is an average of local gridpoint probabilities.

## Data used

The pipeline downloads public ECMWF forecast data directly with the official `ecmwf-opendata` Python client. No API key is required.

- **AIFS ENS**, every 6 hours to 240 hours: ensemble mean and standard deviation for 2 m temperature and 100 m wind speed.
- **AIFS ENS event probabilities**: at least 5 mm of precipitation in 24 hours and instantaneous 10 m wind speed of at least 10 m/s.
- **Previous AIFS ENS run**: ensemble means from the previous 00 UTC forecast, matched to the same valid times.
- **IFS ENS at day 10**: 50 perturbed members and one control member for Z500 circulation analysis.

I use AIFS ENS summary fields for the regional 10-day plots because they are compact to download. I use IFS ENS member fields for the circulation analysis because clustering requires each member separately.

## How the analysis works

The workflow has six main steps:

1. Find the latest complete 00 UTC forecast run.
2. Download the required GRIB2 fields into `data/raw/`.
3. Read and check the fields with `cfgrib` and `xarray`.
4. Calculate regional signals and forecast changes.
5. Cluster the day-10 Z500 ensemble patterns with PCA and k-means.
6. Save small CSV tables, metadata and figures for inspection.

The three regions are rectangular latitude-longitude boxes defined in [`config/regions.yml`](config/regions.yml). They are only simple proxies. They are not electricity bidding zones, river catchments, population-weighted demand regions or wind-farm masks.

Grid cells cover a smaller physical area at high latitude. I therefore use cosine-latitude weights when calculating regional means. For the PCA, I use the square root of the cosine-latitude weight so that the Euclidean distance between flattened fields is closer to an area-weighted spatial distance.

The shaded bands in the regional plots show the regional average of the local ensemble standard deviation. They are not confidence intervals, and they are not the ensemble spread of a regional average.

### Circulation clustering

For the day-10 scenarios, the code:

1. selects 30-80 degrees north and 80 degrees west-40 degrees east;
2. subtracts the current ensemble mean from every member;
3. applies square-root cosine-latitude weighting;
4. reduces the fields to ten principal components;
5. applies k-means with four clusters and a fixed random seed;
6. saves the cluster size and a representative member.

The ten PCA components retain 82.4% of the weighted variance in this example. These clusters should not be called NAO, blocking or other standard weather regimes. A regime analysis would need climatological anomalies, a clear regime definition and validation on independent data.

## Project structure

- `src/energy_weather_risk/`: download, processing, clustering and plotting code.
- `config/regions.yml`: definitions of the three regional boxes.
- `data/processed/`: tables produced by the example run.
- `figures/`: four figures from the example run.
- `tests/`: tests for the most important processing steps.
- `.github/workflows/tests.yml`: automated tests on GitHub.

Raw GRIB files are not stored in Git because they are large and can be downloaded again. The default run downloads about 250 MB, although the size can change between forecast cycles.

## Run directly on GitHub

You can regenerate the results without installing Python on your computer:

1. Edit `config/regions.yml` on GitHub and commit the change.
2. Open the **Actions** tab in the repository.
3. Select **regenerate forecast products** from the workflow list.
4. Select **Run workflow**.
5. Leave the forecast date empty to use the latest complete run, or enter a date as `YYYY-MM-DD`.
6. Choose the forecast hour and data source, then start the run.

The workflow installs the project, downloads about 250 MB of ECMWF data, recreates the tables and figures, and runs the tests. It then commits changed files from `data/processed/` and `figures/` back to the selected branch. It also stores the results as a downloadable GitHub artifact for 30 days.

The raw GRIB files are not committed. If you select a new forecast date, remember that the example text in this README may need to be updated because the numerical conclusions will be different.

## Run the project

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
energy-weather-risk
```

The command selects the latest complete 00 UTC run with the required AIFS and IFS day-10 fields. To reproduce the example in this repository:

```bash
energy-weather-risk --date 2026-09-07 --hour 0 --source ecmwf
```

The client also supports public cloud mirrors. For example:

```bash
energy-weather-risk --source google
```

Downloaded files are first written as temporary files and then renamed after a successful download. Existing non-empty files are reused when the pipeline is run again. Cartopy downloads Natural Earth coastlines and borders the first time it is used.

## Run the tests

```bash
pytest -q
```

The tests check configuration validation, latitude-aware area weighting, exact valid-time selection and accounting of all ensemble members during clustering.

## Limitations and possible next steps

This is a small portfolio project based on one forecast case, so the results must be interpreted carefully.

- Comparing two model runs measures forecast change, not forecast quality.
- One forecast case is not enough to evaluate performance.
- Rectangular regional boxes are too simple for operational energy analysis.
- Wind speed is not wind power. A generation model also needs turbine curves, hub height, air density, turbine availability and wind-farm locations.
- Temperature is not electricity demand. A demand model needs population, calendar effects and calibration for each market.
- Four clusters were chosen for exploration. Their stability and forecast value have not been tested.

My first next step would be proper forecast verification. This would require a longer archive of ensemble forecasts or reforecasts together with ERA5 or observations. Useful measures would include CRPS, Brier scores, reliability diagrams, rank histograms and spread-error relationships. The ECMWF Open Data rolling archive contains only the latest runs, so it is not enough for this validation by itself.

## Data licence

ECMWF forecast data are used under the [ECMWF Open Data licence and terms](https://www.ecmwf.int/en/forecasts/datasets/open-data). The open subset requires CC BY 4.0 attribution. Retrieval uses the official [`ecmwf-opendata` client](https://github.com/ecmwf/ecmwf-opendata). Natural Earth boundary data are public domain.

The source code in this repository is released under the MIT License. This code licence does not change the licences of the forecast or map data.
