#!/usr/bin/env python
# coding: utf-8
"""
Script equivalent of
stratified_random_sampling_for_map_accuracy_and_area_estimation.ipynb: joint
sample-based map accuracy and area estimation via stratified random
sampling. A map alone (or a deterministic held-out accuracy score) gives no
defensible uncertainty on accuracy or area; probability sampling (Olofsson
et al., 2014) is the general solution to both.
"""

## Import modules and packages
import utils_stratified_random_sampling as srs
import os
from osgeo import gdal

gdal.UseExceptions()


def main():

    ## Paths and files
    demo_data_path = os.path.join(os.path.dirname(__file__), 'demo_data')
    crop_map_true = os.path.join(demo_data_path, 'CropMapTrue.tif')
    crop_map_pred = os.path.join(demo_data_path, 'CropMapPred.tif')

    # Ideally, here some visualization of the data

    #------------------------------------
    # Stratified random sampling
    #------------------------------------

    # Create output directory for stratified random sampling
    srs_outdir = demo_data_path.replace('demo_data', 'stratifiedRandomSampling_outputs')
    os.makedirs(srs_outdir, exist_ok=True)

    # Step 1. Compute pixel counts of predicted map
    strata = [0, 1]  # 0 = non-cropland, 1 = cropland
    output_csv = os.path.join(srs_outdir, 'pixelcounts_predicted_map.csv')
    pixel_counts_pred = srs.compute_pixel_counts(crop_map_pred, strata=strata, output_csv=output_csv)
    print("Pixel counts from predicted map:", pixel_counts_pred)

    # Step 2. Deterministic pilot sample (100 SU, proportional allocation) to
    # obtain prior per-stratum variances (Sh) for Neyman sample-size planning
    pilot_min_allocation = 0
    pilot_Ni = 100
    pilot_allocation_csv = os.path.join(srs_outdir, 'pilot_allocations.csv')
    pilot_allocation = srs.allocate_samples(
        pixel_counts_pred, min_allocation=pilot_min_allocation, Ni=pilot_Ni,
        output_allocation_csv=pilot_allocation_csv
    )
    print("Pilot sample allocation per stratum:", pilot_allocation)

    pilot_samples_pred_gpkg = os.path.join(srs_outdir, 'pilot_sample.gpkg')
    pilot_samples_pred = srs.draw_samples(crop_map_pred, pilot_allocation, pilot_samples_pred_gpkg, seed=0, v=True)

    pilot_samples_true_gpkg = os.path.join(srs_outdir, 'pilot_sample_annotated.gpkg')
    nodata_class = 0
    pilot_samples_true = srs.extract_true_class_values(
        pilot_samples_pred_gpkg, crop_map_true, pilot_samples_true_gpkg, nodata_class, v=True
    )

    pilot_pred, pilot_true = list(pilot_samples_true.stratum_pred), list(pilot_samples_true.true_class)
    Sh_csv = os.path.join(srs_outdir, 'pilot_stratum_variances.csv')
    Sh = srs.compute_pilot_variances(strata, pilot_pred, pilot_true, output_csv=Sh_csv, v=True)

    # Step 3. Total sample size (Neyman) for a target confidence level and
    # target coefficient of variation on the cropland area estimate
    confidence = 0.95  # 95% confidence interval
    cv_target = 0.04  # target 4% relative precision
    target_stratum = 1  # cropland
    n_tot = srs.compute_neyman_sample_size(
        pixel_counts_pred, Sh, cv_target=cv_target, confidence=confidence,
        target_stratum=target_stratum, v=True
    )

    # Step 4. Neyman allocation of the total sample size to strata
    neyman_allocation_csv = os.path.join(srs_outdir, 'neyman_allocations.csv')
    allocation = srs.allocate_neyman(pixel_counts_pred, Sh, n_tot, output_allocation_csv=neyman_allocation_csv, v=True)
    print("Neyman sample unit allocation per stratum:", allocation)

    # Step 5. Draw the main sample from the map using the Neyman allocation
    samples_pred_gpkg = os.path.join(srs_outdir, 'stratified_random_sample.gpkg')
    samples_pred = srs.draw_samples(crop_map_pred, allocation, samples_pred_gpkg, seed=0, v=True)
    print(samples_pred)
    # Here also display as a map visual

    # Step 6. Here some talk about how we would be using reference image interpretation, instead we draw from the True map
    samples_true_gpkg = os.path.join(srs_outdir, 'stratified_random_sample_annotated.gpkg')
    samples_true = srs.extract_true_class_values(samples_pred_gpkg, crop_map_true, samples_true_gpkg, nodata_class, v=True)
    print(samples_true)

    # Step 7. Compute sample-based area estimates and uncertainties
    pred, true = list(samples_true.stratum_pred), list(samples_true.true_class)
    metrics_csv_path = os.path.join(srs_outdir, 'stratified_random_sample_metrics.csv')
    metrics = srs.compute_stratified_random_sampling_metrics(pixel_counts_pred, pred, true, output_csv=metrics_csv_path)
    print(metrics)

    # Step 8. Compute map accuracy (overall, user's, producer's) with uncertainties
    accuracy_csv_path = os.path.join(srs_outdir, 'accuracy_metrics.csv')
    accuracy_metrics, overall_accuracy = srs.compute_accuracy_metrics(pixel_counts_pred, pred, true, output_csv=accuracy_csv_path, v=True)
    print(accuracy_metrics)
    print("Overall accuracy:", overall_accuracy)


if __name__ == "__main__":
    main()
