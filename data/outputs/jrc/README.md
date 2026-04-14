# JRC Global Surface Water — Monthly Water Fraction

**Source:** JRC Global Surface Water (GSW), European Commission Joint Research Centre
**Dataset:** JRC/GSW1_4/MonthlyHistory (via Google Earth Engine)
**Resolution:** 30m Landsat imagery
**Coverage:** 1984–present, monthly
**Reference:** Pekel et al. (2016), Nature 540, 418–422. doi:10.1038/nature20584

**Download script:** `scripts/download/download_jrc_surface_water.py`

---

## What the data contains

For each of the 10 rivers, the script extracts the fraction of 30m pixels
classified as water within a **2 km radius buffer** around the exact river
mouth gauge location. Each monthly record contains:

| Column | Description |
|---|---|
| `river` | River name |
| `year` / `month` | Time period |
| `water_fraction` | Fraction of valid pixels classified as water (0.0–1.0) |
| `water_pixels` | Number of 30m pixels classified as water |
| `total_pixels` | Total valid (non-cloud) pixels in the buffer |

Null values indicate months with no usable Landsat imagery (cloud cover).

---

## Assessment of usefulness

### Main limitations

**High null rate (~40–50% of months).** Burundi's tropical climate means
heavy cloud cover during the wet season — precisely when flooding occurs.
This is the worst possible gap pattern for a flood indicator.

**Near-zero water fraction for most rivers.** These are small, narrow rivers
whose floodplains are too confined to register meaningfully in 30m imagery.
A river channel only a few pixels wide, draining a steep valley that clears
quickly after rain, will rarely appear as inundated in a monthly Landsat
composite.

### Per-river assessment

| River | Mean fraction | Max fraction | Verdict |
|---|---|---|---|
| Buzimba | ~0.000 | 0.0001 | Not useful — too narrow |
| Jiji | ~0.000 | 0.0000 | Not useful — too narrow |
| Kaburantwa | ~0.000 | 0.0002 | Not useful — too narrow |
| Mpanda | ~0.000 | 0.0000 | Not useful — too narrow |
| Mulembwe | 0.157 | 1.000 | Unreliable — buffer overlaps lake shore |
| Mutimbuzi | ~0.000 | 0.0042 | Not useful — too narrow |
| Nyakagunda | ~0.000 | 0.0000 | Not useful — too narrow |
| Nyamagana | ~0.000 | 0.0004 | Not useful — too narrow |
| Nyengwe | ~0.000 | 0.0001 | Not useful — too narrow |
| Rusizi | 0.025 | 0.204 | Some signal — larger delta |

**Rusizi** is the only river with a meaningful signal. It is a larger river
with a broader delta where floodwater can spread wide enough to register in
satellite imagery.

**Mulembwe** shows artificially high values because its 2 km buffer
overlaps the Lake Tanganyika shoreline, so the lake itself is being measured
rather than river flooding.

### Potential uses

Despite the limitations, the data may still be useful for:

- **Rusizi flood indicator** — water fraction spikes during flood events and
  can supplement or validate gauge readings
- **Long-term trend analysis** — has the permanent water extent around river
  mouths changed since 1984? (deforestation, land use change)
- **Model feature** — even weak signals can add marginal predictive value
  when combined with precipitation and river level data in a machine learning
  model
- **Cloud-free validation** — for months where data exists and values are
  non-zero, it provides independent confirmation of wet conditions

### Better alternatives for flood detection on these rivers

| Alternative | Why better |
|---|---|
| IGEBU river gauge data (master dataset) | Direct in-situ measurement at river mouth |
| ERA5 precipitation + runoff | Full temporal coverage, no cloud gaps |
| DAHITI lake level | Captures lake response to river inflow |
| SAR imagery (Sentinel-1) | Penetrates clouds — much better for tropical flood mapping |
