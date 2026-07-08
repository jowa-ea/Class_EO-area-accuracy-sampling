# Stratified Random Sampling for Map Accuracy and Area Estimation

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jowa-ea/Class_EO-area-accuracy-sampling/blob/main/stratified_random_sampling_for_map_accuracy_and_area_estimation.ipynb)

Class materials adapted from the [*Earth Observation Driven Crop Area
Estimation*](https://github.com/jowa-ea/EO4AreaEstimatesTogo.git) workshop by Josef Wagner ([University of
Strasbourg](https://www.unistra.fr/fr), [NASA Harvest](https://www.nasaharvest.org/)),
originally developed under the [FAO EOSTAT](https://www.fao.org/in-action/eostat/en)
Togo initiative in partnership with the [Togo Data Lab](https://datalab.gouv.tg/)
and the [DPSSE](https://planifeducation.gouv.tg/dpsse/).

## Context

Generating land use / land cover (LULC) maps is becoming increasingly
straightforward with end-to-end systems such as the [OLMO Earth
platform](https://olmoearth.allenai.org/) or [Google Earth
Engine](https://earthengine.google.com/). But every map produced this way
still contains classification errors. Traditionally, those errors are
assessed by holding out a deterministic subset of the training/reference
data (e.g. a train/test split) and reporting an accuracy score on it. That
score tells us something about the map, but because the held-out subset is
not a probability sample of the region of interest, we have no principled
way to know how trustworthy the accuracy estimate itself is.

The same problem shows up when a map is used to derive an area estimate —
of cropland, of forest, of change, or any other class — by simply counting
pixels. Pixel counting on an imperfect map may, by luck, land close to the
true area, but without a probability sample there is no way to attach a
defensible uncertainty to that number.

[McRoberts, 2011](https://doi.org/10.1016/j.rse.2010.10.013) makes this
point forcefully in a paper titled *"Satellite image-based maps: Scientific
inference or pretty pictures?"*: a map should not be used without a proper
assessment of uncertainties, and without such an assessment, a map is just
a pretty picture. This matters most where it is least optional: official
crop statistics are routinely required to meet a specified precision — for
example, the USDA's June Area Survey (JAS) targets a coefficient of
variation (CV) of around 2% for the national wheat area estimate, and
Ukraine's State Statistics Service (SSSU) targets a 5% CV for wheat.

[Olofsson et al., 2014](https://www.sciencedirect.com/science/article/abs/pii/S0034425714000704)
established the standard pipeline that resolves both problems at once:
**probability sampling is the general solution**. With a well-designed
sample, we can estimate both map accuracy (rather than a deterministic,
held-out accuracy score) and class area, each with a defensible confidence
interval — for any map, anywhere. This version of the workshop focuses on
**stratified random sampling** to do exactly that, and adds:

- Sample size and Neyman allocation planning for a target confidence level
  and coefficient of variation, informed by a deterministic pilot sample.
- Map accuracy assessment (overall, user's, and producer's accuracy with
  uncertainties), following Olofsson et al. (2014).

The two-stage sampling design covered in the original workshop is not
included here.

## Running in Colab

Click the badge above to open the notebook directly in Google Colab. The
first two setup cells install GDAL and the geospatial Python stack, then
clone this repository (including `git-lfs` for the demo rasters) into the
Colab runtime — no local setup required.

This repository is currently **private**, so Colab will prompt you to
authorize access to your GitHub account the first time you open the badge
link; only accounts with read access to this repo can open or clone it. To
share this notebook with students, either add them as collaborators on the
repo, or make the repo public (Settings → General → Danger Zone → Change
visibility) so anyone with the link can open it without authorization.

## Content

1. `stratified_random_sampling_for_map_accuracy_and_area_estimation.ipynb` —
   Jupyter notebook for the hands-on session.
2. `demo_data/` — example cropland maps for the Plateaux region of Togo.
3. `utils_stratified_random_sampling.py`, `utils_plotting.py` — helper
   scripts required to run the notebook.
4. `main.py` — script equivalent of the notebook, with fewer comments and no
   visualizations.

## Sources

Where not specified otherwise, all content was created by Josef Wagner. Feel
free to reuse, share, and modify this workshop content.

- Full cropland maps for Togo: [Kerner et al., 2019](https://arxiv.org/abs/2006.16866)
- Design-based inference for accuracy assessment and area estimation: [McRoberts, 2011](https://doi.org/10.1016/j.rse.2010.10.013), [Olofsson et al., 2014](https://www.sciencedirect.com/science/article/abs/pii/S0034425714000704)
- Neyman allocation and sample size planning: [Song et al., 2017](https://doi.org/10.1016/j.rse.2017.01.008)
