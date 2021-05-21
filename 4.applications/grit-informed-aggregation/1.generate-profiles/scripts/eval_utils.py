import os
import glob
import pandas as pd
import numpy as np
import random

from pycytominer.cyto_utils import infer_cp_features

def get_featuredata(df):
    """Return dataframe of output features that we expect to be cell painting features"""
    return df[infer_cp_features(df, metadata=False)]


def get_metadata(df):
    """Return dataframe of just metadata columns"""
    return df[infer_cp_features(df, metadata=True)]


def percent_score(null_dist, corr_dist, how):
    """
    Calculates the Percent strong or percent recall scores
    
    Arguments:
    null_dist - Null distribution
    corr_dist - Correlation distribution
    how - ["left", "right" or "both"] for using the 5th percentile, 95th percentile or both thresholds
    
    Return: 
    Proportion of correlation distribution beyond the threshold
    """
    if how == 'right':
        perc_95 = np.nanpercentile(null_dist, 95)
        above_threshold = corr_dist > perc_95
        return np.mean(above_threshold.astype(float)), perc_95
    if how == 'left':
        perc_5 = np.nanpercentile(null_dist, 5)
        below_threshold = corr_dist < perc_5
        return np.mean(below_threshold.astype(float)), perc_5
    if how == 'both':
        perc_95 = np.nanpercentile(null_dist, 95)
        above_threshold = corr_dist > perc_95
        perc_5 = np.nanpercentile(null_dist, 5)
        below_threshold = corr_dist < perc_5
        return np.mean(above_threshold.astype(float)) + np.mean(below_threshold.astype(float)), perc_95, perc_5

    
def corr_between_replicates(df, 
                            group_by_feature):
    """
    Calculate correlation between replicates
    
    Arguments:
    df - pd.DataFrame
    group_by_feature - Feature name to group the data frame by
    
    Return:
    List-like of correlation values
    """
    replicate_corr_df = pd.DataFrame()
    replicate_grouped = df.groupby(group_by_feature)
    for name, group in replicate_grouped:
        group_features = get_featuredata(group) 
        corr = np.corrcoef(group_features) 
        if len(group_features) == 1:  # If there is only one replicate on a plate
            replicate_corr = np.nan
        else:
            np.fill_diagonal(corr, np.nan)
            replicate_corr = np.nanmedian(corr)  # median replicate correlation
        replicate_corr_df = (replicate_corr_df.append({group_by_feature: name,
                                                      'correlation': replicate_corr},ignore_index=True)
                            )
    return replicate_corr_df


def corr_between_non_replicates(df, 
                               n_samples, n_replicates, 
                               metadata_compound_name):
    """
    Calculate null distribution between random "replicates".
    
    Arguments:
    df - pandas.DataFrame
    n_samples - int
    n_replicates - int
    metadata_compound_name - Compound name feature
    
    Return:
    List-like of correlation values, with a  length of `n_samples`
    """
    df.reset_index(drop=True, inplace=True)
    null_corr = []
    while len(null_corr) < n_samples:
        compounds = random.choices([_ for _ in range(len(df))], k=n_replicates)
        sample = df.loc[compounds].copy()
        if len(sample[metadata_compound_name].unique()) == n_replicates:
            sample_features = get_featuredata(sample)
            corr = np.corrcoef(sample_features)
            np.fill_diagonal(corr, np.nan)
            null_corr.append(np.nanmedian(corr))  # median replicate correlation
    return null_corr


def corr_between_perturbation_pairs(df, 
                                    metadata_common, 
                                    metadata_perturbation):
    """
    Calculate correlation between perturbation pairs
    
    Arguments:
    df - pd.DataFrame
    metadata_common - feature that identifies perturbation pairs
    metadata_perturbation - perturbation name feature
    
    Return:
    List-like of correlation values
    """
    replicate_corr = []
    
    profile_df = (
        get_metadata(df)
        .assign(profiles=list(df[infer_cp_features(df, metadata=False)].values))
    )
    
    replicate_grouped = (
        profile_df.groupby([metadata_common, metadata_perturbation]).profiles
            .apply(list)
            .reset_index()
    )
    
    common_grouped = (
        replicate_grouped.groupby([metadata_common]).profiles
            .apply(list)
            .reset_index()
    )
    
    for i in range(len(common_grouped)):
        if len(common_grouped.iloc[i].profiles) > 1:
            compound1_profiles = common_grouped.iloc[i].profiles[0]
            compound2_profiles = common_grouped.iloc[i].profiles[1]
            
            corr = np.corrcoef(compound1_profiles, compound2_profiles)
            corr = corr[0:len(common_grouped.iloc[i].profiles[0]), len(common_grouped.iloc[i].profiles[0]):]
            replicate_corr.append(np.nanmedian(corr))
    return replicate_corr


def corr_between_perturbation_non_pairs(df, 
                                        n_samples, 
                                        metadata_common, 
                                        metadata_perturbation):
    """
    Calculate null distribution generated by computing correlation between random pairs of perturbations.
    
    Arguments:
    df - pandas.DataFrame
    n_samples  int
    metadata_common - feature that identifies perturbation pairs
    metadata_perturbation - perturbation name feature
    
    Return: 
    List-like of correlation values, with a  length of `n_samples`
    """
    df.reset_index(drop=True, inplace=True)
    null_corr = []
    
    profile_df = (
        get_metadata(df)
        .assign(profiles=list(df[infer_cp_features(df, metadata=False)].values))
    )
    
    replicate_grouped = (
        profile_df.groupby([metadata_common, metadata_perturbation]).profiles
            .apply(list)
            .reset_index()
    )
    
    while len(null_corr) < n_samples:
        compounds = random.choices([_ for _ in range(len(replicate_grouped))], k=2)
        compound1_moa = replicate_grouped.iloc[compounds[0]][metadata_common]
        compound2_moa = replicate_grouped.iloc[compounds[1]][metadata_common]
        if compound1_moa != compound2_moa:
            compound1_profiles = replicate_grouped.iloc[compounds[0]].profiles
            compound2_profiles = replicate_grouped.iloc[compounds[1]].profiles
            corr = np.corrcoef(compound1_profiles, compound2_profiles)
            corr = corr[0:len(replicate_grouped.iloc[0].profiles), len(replicate_grouped.iloc[0].profiles):]
            null_corr.append(np.nanmedian(corr))  # median replicate correlation
    return null_corr