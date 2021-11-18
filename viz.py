from info import info
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import pandas as pd
import click
import os
import pickle
from pyei.plot_utils import size_ticks
import seaborn as sns
import numpy as np
from copy import copy


PALETTE = "Dark2"  # set library-wide color palette
FONTSIZE = 20
TITLESIZE = 24
TICKSIZE = 15
FIGSIZE = (10, 5)
colors = sns.color_palette(PALETTE)
def plot_turnout_kdes(sampled_voting_prefs, group_names, candidate_names, plot_by="candidate", axes=None):
    """
    Plot a kernel density plot for prefs of voting groups for each candidate
    Parameters
    ----------
    sampled_voting_prefs : numpy array
        Shape: num_samples x r x c (where r = # of demographic groups, c= #
        of candidates or voting outcomes). Gives samples of support from each group
        for each candidate. NOTE: for a 2 x 2 case where we have just two candidates/outcomes
        and want only one plot, have c=1
    group_names : list of str
        Names of the demographic groups (length r)
    candidate_names : list of str
        Names of the candidates or voting outcomes (length c)
    plot_by : {"candidate", "group"}
        (Default='candidate')
        If 'candidate', make one plot per candidate, with each plot showing the kernel
        density estimates of voting preferences of all groups. If 'group', one plot
        per group, with each plot showing the kernel density estimates of voting
        preferences for all candidates.
    axes : list of Matplotlib axis object or None
        Default=None.
        If not None and plot_by is 'candidate', should have length c (number of candidates).
        If plot_by is 'group', should have length r (number of groups)
    Returns
    -------
    ax : Matplotlib axis object
    """

    _, num_groups, num_candidates = sampled_voting_prefs.shape
    if plot_by == "candidate":
        num_plots = num_candidates
        num_kdes_per_plot = num_groups
        titles = candidate_names
        if group_names == ["WVAP", "OVAP"]:
          group_names = ["WVAP", "POCVAP"]
        legend = group_names
        support = "for"
        if axes is None:
            _, axes = plt.subplots(num_candidates, figsize=FIGSIZE, sharex=True)
            plt.subplots_adjust(hspace=0.3*num_candidates)
    elif plot_by == "group":
        num_plots = num_groups
        num_kdes_per_plot = num_candidates - 1 # we DON'T want turnout in the group KDEs
        if group_names == ["WVAP", "OVAP"]:
          group_names = ["WVAP", "POCVAP"]
        titles = group_names
        sampled_voting_prefs = np.swapaxes(sampled_voting_prefs, 1, 2)
        legend = candidate_names
        support = "among"
        if axes is None:
            _, axes = plt.subplots(num_groups, figsize=FIGSIZE, sharex=True)
            plt.subplots_adjust(hspace=0.3*num_groups)
    else:
        raise ValueError("plot_by must be 'group' or 'candidate' (default: 'candidate')")

    middle_plot = int(np.floor(num_plots / 2))
    for plot_idx in range(num_plots):
        if num_plots > 1:
            ax = axes[plot_idx]
            axes[middle_plot].set_ylabel("Probability Density", fontsize=FONTSIZE)
        else:
            ax = axes
            axes.set_ylabel("Probability Density", fontsize=FONTSIZE)
        if plot_idx == num_plots - 1 and plot_by == "candidate":
            ax.set_title(titles[plot_idx], fontsize=TITLESIZE)
        else:
            ax.set_title(f"Support {support} " + titles[plot_idx], fontsize=TITLESIZE)
        ax.set_xlim((0, 1))
        size_ticks(ax, "x")

        for kde_idx in range(num_kdes_per_plot):
            sns.histplot(
                sampled_voting_prefs[:, kde_idx, plot_idx],
                kde=True,
                ax=ax,
                stat="density",
                element="step",
                label=legend[kde_idx],
                color=colors[kde_idx],
                linewidth=0,
            )
            ax.set_ylabel("")

    if num_plots > 1:
        axes[middle_plot].legend(bbox_to_anchor=(1, 1), loc="upper left", prop={"size": 12})
    else:
        ax.legend(prop={"size": 12})
    return ax

def make_turnout_adjusted_samples(samples):
    """
    Assumes the last `candidate` is the `None` (or `Abstain`) column.
    Returns a new samples array where the candidates support levels are normalized to the total estimated
    voting population of each demographic, and the last column is the estimated turnout.
    """
    new_samples = copy(samples)
    _, num_groups, num_candidates = samples.shape
    num_named_candidates = num_candidates - 1
    for i in range(num_groups):
        for j in range(num_named_candidates):
            new_samples[:,i,j] = samples[:,i,j] / sum(samples[:,i,k] for k in range(num_named_candidates))
        new_samples[:,i,-1] = 1 - samples[:,i,-1]
    return new_samples

def best_fit_mb(xs, ys):
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))
    b = np.mean(ys) - m*np.mean(xs)
    return m, b

def plot_ER(state, election, groups):
    df = pd.read_csv(f"outputs/{state}/final_inputs/{state}_{election}_{'-'.join(groups)}.csv", index_col=0)
    candidates = list(info[state]["elections"][election]["candidates"].keys())

    group = groups[0]
    candidate = candidates[0]
    group_pct = df[f"{group}_pct"]
    candidate_pct = df[f"{candidate}_pct"]
    candidate_last_name = info[state]["elections"][election]["candidates"][candidate]["name"].split(" ")[-1]

    m, b = best_fit_mb(group_pct, candidate_pct)
    unweighted_xs = np.arange(0, 1, 0.01)
    unweighted_ys = [m*x + b for x in unweighted_xs]

    x = np.reshape(group_pct.values, (len(df), 1))
    y = np.reshape(candidate_pct.values, (len(df), 1))
    line = LinearRegression().fit(x, y, (df[candidates].sum(axis=1)))
    weighted_xs = np.reshape(unweighted_xs, (len(unweighted_xs), 1))
    weighted_ys = line.predict(weighted_xs)

    _, ax = plt.subplots(figsize=(8,8))
    ax.scatter(group_pct,
            candidate_pct,
    #            c=df[candidates].sum(axis=1),
    #            cmap='jet',
            )
    ax.plot(unweighted_xs,
            unweighted_ys,
            color="black",
            label="unweighted",
            lw=2,
        )
    ax.plot(weighted_xs,
            weighted_ys,
            color="red",
            label="weighted",
            lw=2,
        )
    ax.set_xlabel(f"{group} Share", fontsize=24)
    ax.set_ylabel(f"{candidate_last_name} Share", fontsize=24)
    ax.legend()
    #     ax.set_xlim(0,1)
    #     ax.set_ylim(0,1)

    os.makedirs(f"outputs/{state}/plots/ER", exist_ok=True)
    plt.savefig(f"outputs/{state}/plots/ER/{state}_{election}_scatter.png", dpi=600, bbox_inches='tight')
    plt.show()
    plt.close()
    return

@click.command()
@click.option('-state')
@click.option('-elec')
@click.option('-g', multiple=True)
@click.option('-county')
def main(state, elec, g, county=None):
    print(f"\nMaking viz for {elec} on {g}...")
    # candidate_cols = list(info[state]["elections"][elec]["candidates"].keys())
    county_id = '' if county is None else f'_{county.replace(" ", "")}'
    run_id = f"{state+county_id}_{elec}_{'-'.join(g)}"

    ei = pickle.load(open(f"outputs/{state+county_id}/ei/{run_id}.pickle", "rb"))
    turnout_samples = make_turnout_adjusted_samples(ei.sampled_voting_prefs)
    turnout_candidate_names = ei.candidate_names
    turnout_candidate_names[-1] = "Turnout"

    output_folder = f"outputs/{state+county_id}/plots"
    os.makedirs(output_folder, exist_ok=True)

    plot_ER(state, elec, g)
    for kde_type in ["candidate", "group"]:
        os.makedirs(f"{output_folder}/turnout_adjusted_kdes_{kde_type}", exist_ok=True)
        plot_turnout_kdes(turnout_samples, ei.demographic_group_names, turnout_candidate_names, plot_by=kde_type)
        plt.savefig(f"{output_folder}/turnout_adjusted_kdes_{kde_type}/{run_id}_kdes_{kde_type}.png", dpi=200, bbox_inches='tight')
        plt.close()
    return

if __name__=="__main__":
    main()
