#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pathlib
import numpy as np
import pandas as pd
import plotnine as gg


# In[2]:


results_dir = pathlib.Path("../../1.calculate-metrics/cell-health/results")
output_dir = pathlib.Path("figures")


# In[3]:


# Load cell health grit scores
cell_health_grit_file = pathlib.Path(f"{results_dir}/cell_health_grit.tsv")

cell_health_grit_df = (
    pd.read_csv(cell_health_grit_file, sep="\t")
    .query("barcode_control == 'cutting_control'")
    .query("cor_method == 'pearson'")
)

print(cell_health_grit_df.shape)
cell_health_grit_df.head()


# In[4]:


# Load mp value grit scores
cell_health_mpvalue_file = pathlib.Path(f"{results_dir}/cell_health_mpvalue.tsv")

cell_health_mpvalue_df = (
    pd.read_csv(cell_health_mpvalue_file, sep="\t")
    .query("barcode_control == 'cutting_control'")
)

cell_health_mpvalue_df = cell_health_mpvalue_df.assign(mp_value_neglog=-1 * np.log10(cell_health_mpvalue_df.mp_value))

mask = cell_health_mpvalue_df.mp_value_neglog == np.inf
cell_health_mpvalue_df.loc[mask, "mp_value_neglog"] = cell_health_mpvalue_df.loc[~mask, "mp_value_neglog"].max()

print(cell_health_mpvalue_df.shape)
cell_health_mpvalue_df.head()


# In[5]:


combined_df = (
    cell_health_grit_df.merge(
        cell_health_mpvalue_df,
        left_on=["perturbation", "cell_line", "barcode_control"],
        right_on=["Metadata_pert_name", "cell_line", "barcode_control"]
    )
)

print(combined_df.shape)
combined_df.head()


# In[6]:


cell_line_colors = {
  "A549": "#861613",
  "ES2": "#1CADA8",
  "HCC44": "#2A364D"
}

def col_func(s):
    return f"Permutations:\n{s}\n"

mp_value_comparison_gg = (
    gg.ggplot(combined_df.dropna(), gg.aes(x="grit", y="mp_value_neglog"))
    + gg.geom_point(gg.aes(fill="cell_line"), size=0.7, stroke=0.2, alpha=0.7)
    + gg.geom_vline(xintercept=0, linetype="dotted", color="red")
    + gg.scale_fill_manual(name="Cell Line", values=cell_line_colors)
    + gg.xlab("Grit")
    + gg.ylab("-log10(mp-Value)")
    + gg.facet_wrap("~num_permutations", ncol=4, labeller=gg.labeller(cols=col_func))
    + gg.theme_bw()
    + gg.theme(strip_background=gg.element_rect(color="black", height=0.15, fill="#fdfff4"))
)

output_file = pathlib.Path(f"{output_dir}/cell_health_grit_mpvalue_comparison.png")
mp_value_comparison_gg.save(output_file, dpi=500, height=3, width=6.5)

mp_value_comparison_gg

