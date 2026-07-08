# Stratified Random Sampling for Map Accuracy and Area Estimation

Class materials adapted from the [*Earth Observation Driven Crop Area
Estimation*](https://github.com/jowa-ea/EO4AreaEstimatesTogo.git) workshop by Josef Wagner ([University of
Strasbourg](https://www.unistra.fr/fr), [NASA Harvest](https://www.nasaharvest.org/)),
originally developed under the [FAO EOSTAT](https://www.fao.org/in-action/eostat/en)
Togo initiative in partnership with the [Togo Data Lab](https://datalab.gouv.tg/)
and the [DPSSE](https://planifeducation.gouv.tg/dpsse/).

This version focuses on **stratified random sampling** for area estimation
and map accuracy assessment, and adds:

- Sample size and Neyman allocation planning for a target confidence level
  and coefficient of variation, informed by a deterministic pilot sample.
- Map accuracy assessment (overall, user's, and producer's accuracy with
  uncertainties), following [Olofsson et al., 2014](https://www.sciencedirect.com/science/article/abs/pii/S0034425714000704).

The two-stage sampling design covered in the original workshop is not
included here.

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
- Stratified random sampling and accuracy assessment: [Olofsson et al., 2014](https://www.sciencedirect.com/science/article/abs/pii/S0034425714000704)
- Neyman allocation and sample size planning: [Song et al., 2017](https://doi.org/10.1016/j.rse.2017.01.008)
