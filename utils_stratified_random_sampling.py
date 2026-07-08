#!/usr/bin/env python
# coding: utf-8

## Modules
from osgeo import gdal
import numpy as np
import pandas as pd
from shapely.geometry import Point
import geopandas as gpd


gdal.UseExceptions()

def compute_pixel_counts(input_map, strata=None, output_csv=None):
    """
    Compute pixel counts (in hectares) for each stratum in a raster map,
    and include stratum weights (Wi). Optionally save as CSV using pandas.

    Parameters
    ----------
    input_map : str
        Path to raster file.
    strata : list, optional
        List of strata (class values) to compute pixel counts for.
        If None, all unique values in the raster will be used.
    output_csv : str, optional
        Path to save results as CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: ['Stratum', 'Area_ha', 'Wi']
    """

    # Open raster
    ds = gdal.Open(input_map)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {input_map}")

    arr = ds.GetRasterBand(1).ReadAsArray().astype('uint8')

    # Determine strata if not provided
    if strata is None:
        strata = np.unique(arr)

    # Pixel area in hectares
    gt = ds.GetGeoTransform()
    pixel_area_ha = (gt[1] * abs(gt[5])) / 10000  # convert m² to ha

    # Compute areas
    areas = []
    for s in strata:
        count = np.count_nonzero(arr == s)
        areas.append(count * pixel_area_ha)

    # Compute stratum weights
    total_area = sum(areas)
    weights = [area / total_area for area in areas]

    # Create pandas DataFrame
    df = pd.DataFrame({
        'Stratum': strata,
        'Area_ha': areas,
        'Wi': weights
    })

    # Save CSV if requested
    if output_csv:
        df.to_csv(output_csv, index=False)

    return df



def allocate_samples(pixel_counts, min_allocation, Ni, output_allocation_csv=None):
    """
    Allocate samples to strata proportionally to their pixel counts,
    ensuring at least `min_allocation` per stratum.

    pixel_counts : dict or pd.DataFrame
        If dict: {stratum: pixel_count}.
        If DataFrame: must have columns ['Stratum', 'Area_ha'].
    """
    import pandas as pd

    # Convert DataFrame to dict if needed
    if isinstance(pixel_counts, pd.DataFrame):
        if 'Area_ha' not in pixel_counts.columns or 'Stratum' not in pixel_counts.columns:
            raise ValueError("DataFrame must have columns ['Stratum', 'Area_ha']")
        pixel_counts = dict(zip(pixel_counts['Stratum'], pixel_counts['Area_ha']))

    # Step 1: compute stratum weights
    total_pixels = sum(pixel_counts.values())
    Wi = {k: v / total_pixels for k, v in pixel_counts.items()}

    # Step 2: allocate minimum to each stratum
    sample_allocation = {k: min_allocation for k in pixel_counts}

    # Step 3: compute remaining samples to distribute proportionally
    remaining = Ni - sum(sample_allocation.values())
    if remaining > 0:
        for k in Wi:
            sample_allocation[k] += int(remaining * Wi[k])

        # Step 4: fix rounding issues to ensure total sums to Ni
        allocated = sum(sample_allocation.values())
        diff = Ni - allocated
        if diff > 0:
            # add leftover samples to strata with largest weights
            for k, _ in sorted(Wi.items(), key=lambda x: -x[1]):
                if diff <= 0:
                    break
                sample_allocation[k] += 1
                diff -= 1

    # Optionally save allocation to CSV
    if output_allocation_csv:
        df = pd.DataFrame(list(sample_allocation.items()), columns=["Stratum", "Sample units"])
        df.to_csv(output_allocation_csv, index=False)

    return sample_allocation



def draw_samples(map_path, sample_allocation, out_gpkg, seed=0, v=False):
    """
    Samples points from a categorical raster by stratum and saves results as a GeoPackage.

    map_path: path to categorical raster
    sample_allocation: dict {stratum_value: n_samples}
    out_gpkg: output GeoPackage path
    seed: random seed
    v: verbose
    """

    # Open raster
    ds = gdal.Open(map_path)
    band = ds.GetRasterBand(1)
    width = ds.RasterXSize
    height = ds.RasterYSize
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()

    samples = {"stratum_pred": [], "row": [], "col": [], "geometry": []}

    np.random.seed(seed)  # reproducibility

    # Loop over strata
    for stratum, n_samples in sample_allocation.items():
        if v:
            print(f"Stratum {stratum}, sampling {n_samples} points...")
        sampled = 0

        while sampled < n_samples:
            col = np.random.randint(0, width)
            row = np.random.randint(0, height)

            val = band.ReadAsArray(col, row, 1, 1)[0, 0]

            if val == stratum:
                # Convert pixel to coordinates (pixel center)
                x = gt[0] + (col + 0.5) * gt[1] + (row + 0.5) * gt[2]
                y = gt[3] + (col + 0.5) * gt[4] + (row + 0.5) * gt[5]

                samples["stratum_pred"].append(val)
                samples["row"].append(row)
                samples["col"].append(col)
                samples["geometry"].append(Point(x, y))

                sampled += 1

        if v:
            print(f"  Sampled {sampled}/{n_samples}")

    # Create GeoDataFrame and save as GPKG
    gdf = gpd.GeoDataFrame(samples, geometry="geometry", crs=proj)
    gdf.to_file(out_gpkg, driver="GPKG")

    if v:
        print(f"Saved {len(gdf)} samples to {out_gpkg}")

    return gdf

def extract_true_class_values(samples_gpkg, crop_map_true, out_gpkg,
                              nodata_class, v=False):
    """
    Extract raster values at points stored in a GeoPackage and save as a new GeoPackage.
    If sampled value equals raster NoData, assign nodata_class.

    samples_gpkg: path to GeoPackage with sampled points
    crop_map_true: path to raster from which to extract values
    out_gpkg: path to save the new GeoPackage
    nodata_class: value to assign when "true" value is NoData or out of bounds
    v: verbose
    """

    gdf = gpd.read_file(samples_gpkg)

    ds = gdal.Open(crop_map_true)
    band = ds.GetRasterBand(1)
    gt = ds.GetGeoTransform()
    nodata = band.GetNoDataValue()

    if v:
        print(f"Raster NoData value: {nodata}")

    true_values = []

    for idx, row in gdf.iterrows():
        x, y = row.geometry.x, row.geometry.y
        col = int((x - gt[0]) / gt[1])
        row_idx = int((y - gt[3]) / gt[5])  # gt[5] negative

        if 0 <= col < ds.RasterXSize and 0 <= row_idx < ds.RasterYSize:
            val = band.ReadAsArray(col, row_idx, 1, 1)[0, 0]

            if nodata is not None and val == nodata:
                true_values.append(nodata_class)
            else:
                true_values.append(val)
        else:
            true_values.append(nodata_class)
            if v:
                print(f"Point {idx} out of bounds, assigning {nodata_class}")

    gdf["true_class"] = true_values
    gdf.to_file(out_gpkg, driver="GPKG")

    if v:
        print(f"Saved {len(gdf)} points with true_class to {out_gpkg}")

    return gdf




def _build_confusion_proportions(pixel_counts, pred, true):
    """
    Shared building block for the stratified estimators below: cross-tabulates
    pred/true by stratum (map class) and converts sample counts into
    estimated area proportions p_hat_ij = Wi * nij/ni (Olofsson et al., 2014,
    Eq. 4), assuming the strata are the map classes.

    Parameters
    ----------
    pixel_counts : pd.DataFrame
        Has columns ['Stratum', 'Area_ha'] (and optionally 'Wi').
    pred, true : array-like
        Predicted (map) and reference stratum of each sample unit.

    Returns
    -------
    strata : list
        Stratum values, in the order used for all matrix rows/columns.
    cm : np.ndarray
        Sample count confusion matrix, cm[i, j] = # samples with map
        stratum i and reference class j.
    Wi : np.ndarray
        Mapped area proportion of each stratum, same order as `strata`.
    Pij : np.ndarray
        Estimated area-proportion error matrix, p_hat_ij.
    """
    from sklearn.metrics import confusion_matrix

    strata = list(pixel_counts['Stratum'])
    pixel_counts_dict = pixel_counts.set_index('Stratum')['Area_ha'].to_dict()
    total_pixels = sum(pixel_counts_dict.values())
    Wi = np.array([pixel_counts_dict[s] / total_pixels for s in strata])

    # Explicit labels so matrix rows/cols always align with `strata`'s order,
    # regardless of what values happen to appear in pred/true.
    cm = confusion_matrix(pred, true, labels=strata)
    numberOfClasses = len(strata)

    Pij = np.zeros((numberOfClasses, numberOfClasses))
    for i in range(numberOfClasses):
        ni = cm[i].sum()
        for j in range(numberOfClasses):
            Pij[i, j] = Wi[i] * cm[i, j] / ni if ni > 0 else 0

    return strata, cm, Wi, Pij


def compute_stratified_random_sampling_metrics(pixel_counts, pred, true, output_csv=None, v=False):
    """
    Compute stratified area estimates and uncertainty metrics.

    Parameters
    ----------
    pixel_counts : df
        Has columns Stratum and Area_ha
    pred : array-like
        Predicted class labels.
    true : array-like
        True/reference class labels.
    output_csv : str or None
        If provided, saves the results DataFrame to this CSV path.
    v: bool
        If true, verbose

    Returns
    -------
    df : pd.DataFrame
        DataFrame with per-class area estimates, SE, CI, and percentages.
    """
    import pandas as pd

    strata, cm, Wi, Pij = _build_confusion_proportions(pixel_counts, pred, true)
    numberOfClasses = len(strata)
    total_pixels = pixel_counts.set_index('Stratum')['Area_ha'].sum()

    # Compute areas (Olofsson et al., 2014, Eq. 8-9): sum of column k
    Areas = [sum(Pij[:, k]) * total_pixels for k in range(numberOfClasses)]

    # Compute standard errors for areas (Eq. 10)
    AreasSTDERR = []
    for k in range(numberOfClasses):
        AreasSTDERR.append(
            np.sqrt(sum(
                ((Wi[i] * Pij[i, k]) - (Pij[i, k] ** 2)) / (cm[i].sum() - 1) if cm[i].sum() > 1 else 0
                for i in range(numberOfClasses)
            ))
        )

    AreasSE_total = [total_pixels * AreasSTDERR[k] for k in range(numberOfClasses)]

    # Prepare DataFrame
    df = pd.DataFrame({
        'Area_ha': Areas,
        'SE_Ha': AreasSE_total,
        'CI_Ha': [se * 1.96 for se in AreasSE_total],
        'SE%': [se / area if area != 0 else np.nan for se, area in zip(AreasSE_total, Areas)],
        'CI%': [(se * 1.96) / area if area != 0 else np.nan for se, area in zip(AreasSE_total, Areas)]
    }, index=strata)
    df.index.name = "class"

    if output_csv:
        df.to_csv(output_csv)
        if v:
            print(f"Saved stratified sampling metrics to {output_csv}")

    if v:
        print(df)

    return df


def compute_accuracy_metrics(pixel_counts, pred, true, output_csv=None, v=False):
    """
    Compute sample-based map accuracy (overall, user's, and producer's) with
    standard errors and 95% confidence intervals, following Olofsson et al.
    (2014), Eqs. 1-3 (parameters) and Eqs. 5-7 (variances). Assumes the
    strata correspond to the map classes, as in
    `compute_stratified_random_sampling_metrics`.

    Parameters
    ----------
    pixel_counts : pd.DataFrame
        Has columns ['Stratum', 'Area_ha'].
    pred, true : array-like
        Predicted (map) and reference stratum of each sample unit.
    output_csv : str, optional
    v : bool

    Returns
    -------
    class_df : pd.DataFrame
        Per-class user's accuracy (Ui) and producer's accuracy (Pi), each
        with SE and 95% CI. Indexed by stratum.
    overall : dict
        {'O': overall accuracy, 'SE': ..., 'CI': ...}
    """
    strata, cm, Wi, Pij = _build_confusion_proportions(pixel_counts, pred, true)
    q = len(strata)
    ni = np.array([cm[i].sum() for i in range(q)])  # sample units per map class (rows)

    # User's accuracy (Eq. 2) and its variance (Eq. 6)
    Ui = np.array([Pij[i, i] / Wi[i] if Wi[i] > 0 else np.nan for i in range(q)])
    Ui_var = np.array([
        Ui[i] * (1 - Ui[i]) / (ni[i] - 1) if ni[i] > 1 else np.nan
        for i in range(q)
    ])

    # Marginal totals needed for producer's accuracy (Eq. 3, 7)
    p_dot_j = Pij.sum(axis=0)  # estimated area proportion of reference class j
    total_pixels = pixel_counts.set_index('Stratum')['Area_ha'].sum()
    N_i = Wi * total_pixels  # mapped pixel/area count per stratum i

    Pj = np.array([Pij[j, j] / p_dot_j[j] if p_dot_j[j] > 0 else np.nan for j in range(q)])

    Pj_var = np.full(q, np.nan)
    for j in range(q):
        if p_dot_j[j] <= 0:
            continue
        Nj_hat_j = sum(N_i[i] * cm[i, j] / ni[i] if ni[i] > 0 else 0 for i in range(q))
        if Nj_hat_j <= 0 or ni[j] <= 1:
            continue
        term1 = (N_i[j] ** 2) * ((1 - Pj[j]) ** 2) * Ui[j] * (1 - Ui[j]) / (ni[j] - 1)
        term2 = (Pj[j] ** 2) * sum(
            (N_i[i] ** 2) * (cm[i, j] / ni[i]) * (1 - cm[i, j] / ni[i]) / (ni[i] - 1)
            for i in range(q) if i != j and ni[i] > 1
        )
        Pj_var[j] = (term1 + term2) / (Nj_hat_j ** 2)

    # Overall accuracy (Eq. 1) and its variance (Eq. 5)
    O = Pij.trace()
    O_var = sum(
        (Wi[i] ** 2) * Ui[i] * (1 - Ui[i]) / (ni[i] - 1) if ni[i] > 1 else 0
        for i in range(q)
    )

    class_df = pd.DataFrame({
        'Ui': Ui,
        'Ui_SE': np.sqrt(Ui_var),
        'Ui_CI': 1.96 * np.sqrt(Ui_var),
        'Pi': Pj,
        'Pi_SE': np.sqrt(Pj_var),
        'Pi_CI': 1.96 * np.sqrt(Pj_var),
    }, index=strata)
    class_df.index.name = "class"

    overall = {'O': O, 'SE': np.sqrt(O_var), 'CI': 1.96 * np.sqrt(O_var)}

    if output_csv:
        class_df.to_csv(output_csv)
        if v:
            print(f"Saved accuracy metrics to {output_csv}")

    if v:
        print(class_df)
        print(f"Overall accuracy: {overall['O']:.3f} +/- {overall['CI']:.3f}")

    return class_df, overall


def compute_pilot_variances(strata, pred, true, output_csv=None, v=False):
    """
    Estimate prior per-stratum standard deviations (S_h) from a deterministic
    pilot stratified sample, for use in Neyman sample-size and allocation
    planning (Cochran, 1977; Olofsson et al., 2014, Eq. 5.55):

        S_h = sqrt(U_h * (1 - U_h))

    where U_h is the stratum's user's accuracy (proportion of pilot sample
    units in stratum h whose reference class matches the map stratum)
    observed in the pilot sample. Note U_h = nii/ni is independent of the
    stratum's area weight, so it can be computed directly from sample counts.

    Parameters
    ----------
    strata : list
        Stratum values, in the same order as the map classes / pixel counts.
    pred, true : array-like
        Predicted (map) and reference stratum of each pilot sample unit.
    output_csv : str, optional
    v : bool

    Returns
    -------
    pd.DataFrame with columns ['Stratum', 'n_pilot', 'Ui_pilot', 'Sh']
    """
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(pred, true, labels=strata)

    rows = []
    for i, s in enumerate(strata):
        n_pilot = int(cm[i].sum())
        Ui = cm[i, i] / n_pilot if n_pilot > 0 else 0.0
        Sh = np.sqrt(Ui * (1 - Ui))
        rows.append({'Stratum': s, 'n_pilot': n_pilot, 'Ui_pilot': Ui, 'Sh': Sh})

    df = pd.DataFrame(rows)

    if output_csv:
        df.to_csv(output_csv, index=False)
    if v:
        print(df)

    return df


def _stratum_dict(df_or_dict, value_col):
    """Accept either a dict {Stratum: value} or a DataFrame with a 'Stratum' column."""
    if isinstance(df_or_dict, pd.DataFrame):
        return dict(zip(df_or_dict['Stratum'], df_or_dict[value_col]))
    return dict(df_or_dict)


# z-values for common confidence levels (two-sided). Avoids adding scipy as
# a hard dependency just for norm.ppf; falls back to scipy if an
# uncommon confidence level is requested and scipy happens to be available.
_Z_LOOKUP = {0.80: 1.2816, 0.85: 1.4395, 0.90: 1.6449, 0.95: 1.9600, 0.98: 2.3263, 0.99: 2.5758}


def _z_from_confidence(confidence):
    if confidence in _Z_LOOKUP:
        return _Z_LOOKUP[confidence]
    try:
        from scipy.stats import norm
        return float(norm.ppf(1 - (1 - confidence) / 2))
    except ImportError:
        raise ValueError(
            f"confidence={confidence} is not one of the supported standard levels "
            f"{sorted(_Z_LOOKUP)} and scipy is not installed to compute an exact "
            "z-value. Use one of the standard confidence levels, or install scipy."
        )


def compute_neyman_sample_size(pixel_counts, Sh, cv_target, confidence, target_stratum, v=False):
    """
    Determine the total stratified-random-sample size needed to achieve a
    target relative precision at a given confidence level, using the Neyman
    sample-size formula (Cochran, 1977; Song et al., 2017, Eq. 2):

        n_tot = z^2 * (sum_h Wh*Sh)^2 / E^2

    where E = cv_target * p_target is the desired confidence-interval
    half-width, expressed as a fraction (cv_target) of p_target (the mapped
    proportion of `target_stratum`). Note that because E already scales with
    z (E = z * SE), the *actual* coefficient of variation of the resulting
    estimator, SE(p_hat)/p_target, works out to cv_target / z: tightening
    the confidence level (larger z) for the same cv_target requires a larger
    sample size.

    Parameters
    ----------
    pixel_counts : pd.DataFrame
        Has columns ['Stratum', 'Area_ha', 'Wi'].
    Sh : pd.DataFrame or dict
        Prior per-stratum standard deviations, e.g. from
        `compute_pilot_variances` (columns ['Stratum', 'Sh']).
    cv_target : float
        Target relative precision (e.g. 0.04 for 4%). Required, user-set.
    confidence : float
        Confidence level (e.g. 0.95). Required, user-set.
    target_stratum : hashable
        Which stratum's mapped proportion (Wi) to use as p_target (typically
        the class of interest, e.g. cropland).
    v : bool

    Returns
    -------
    int
        Total required sample size, n_tot (rounded up).
    """
    Wi = _stratum_dict(pixel_counts, 'Wi')
    Sh_d = _stratum_dict(Sh, 'Sh')
    strata = list(Wi.keys())

    sum_WhSh = sum(Wi[s] * Sh_d[s] for s in strata)
    z = _z_from_confidence(confidence)
    p_target = Wi[target_stratum]
    E = cv_target * p_target

    n_tot = int(np.ceil((z * sum_WhSh / E) ** 2))

    if v:
        print(f"z={z}, sum(Wh*Sh)={sum_WhSh:.4f}, p_target={p_target:.4f}, E={E:.4f}")
        print(f"Required total sample size: n_tot={n_tot}")

    return n_tot


def allocate_neyman(pixel_counts, Sh, n_tot, output_allocation_csv=None, v=False):
    """
    Allocate n_tot sample units to strata via Neyman allocation (Cochran,
    1977; Song et al., 2017, Eq. 3):

        n_h = n_tot * Wh*Sh / sum_h(Wh*Sh)

    Parameters
    ----------
    pixel_counts : pd.DataFrame
        Has columns ['Stratum', 'Wi'].
    Sh : pd.DataFrame or dict
        Prior per-stratum standard deviations, e.g. from
        `compute_pilot_variances`.
    n_tot : int
        Total sample size to allocate, e.g. from `compute_neyman_sample_size`.
    output_allocation_csv : str, optional
    v : bool

    Returns
    -------
    dict {stratum: n_h}
    """
    Wi = _stratum_dict(pixel_counts, 'Wi')
    Sh_d = _stratum_dict(Sh, 'Sh')
    strata = list(Wi.keys())

    sum_WhSh = sum(Wi[s] * Sh_d[s] for s in strata)
    weights = {s: Wi[s] * Sh_d[s] for s in strata}
    allocation = {s: int(round(n_tot * weights[s] / sum_WhSh)) for s in strata}

    # Fix rounding so the allocation sums exactly to n_tot: adjust the
    # strata with the largest Neyman weight first.
    diff = n_tot - sum(allocation.values())
    order = sorted(strata, key=lambda s: -weights[s])
    i = 0
    while diff != 0 and order:
        s = order[i % len(order)]
        step = 1 if diff > 0 else -1
        allocation[s] += step
        diff -= step
        i += 1

    if output_allocation_csv:
        pd.DataFrame(list(allocation.items()), columns=["Stratum", "Sample units"]).to_csv(
            output_allocation_csv, index=False
        )

    if v:
        print(allocation)

    return allocation


