from info import info
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import click
import os
import pickle
from viz import make_turnout_adjusted_samples

def make_points_table(samples, state, elec, g, last_candidate="None"):
    candidate_cols = list(info[state]["elections"][elec]["candidates"].keys()) + [f"{elec}{last_candidate}"]
    group_names = list(g) + ["OVAP"]
    df = pd.DataFrame(index=group_names,
                      columns=candidate_cols)
    for i, cand in enumerate(candidate_cols):
        for j, group in enumerate(group_names):
            point = np.mean(samples[:,j,i])
            lower = np.percentile(samples[:,j,i], 2.5)
            upper = np.percentile(samples[:,j,i], 97.5)
            df[cand].loc[group] = f"{round(point, 4)} ({round(lower, 4)}-{round(upper, 4)})"
    return df


@click.command()
@click.option('-state')
@click.option('-elec')
@click.option('-g', multiple=True)
@click.option('-county')
def main(state, elec, g, county=None):
    print(f"Making summary for {elec} on {g}")
    county_id = '' if county is None else f'_{county.replace(" ", "")}'
    run_id = f"{state+county_id}_{elec}_{'-'.join(g)}"

    ei = pickle.load(open(f"outputs/{state+county_id}/ei/{run_id}.pickle", "rb"))

    output_folder = f"outputs/{state+county_id}/summaries"
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(f"{output_folder}/raw_summaries", exist_ok=True)
    os.makedirs(f"{output_folder}/turnout_adjusted_summaries", exist_ok=True)

    samples = ei.sampled_voting_prefs
    turnout_samples = make_turnout_adjusted_samples(samples)
    df = make_points_table(samples, state, elec, g)
    turnout_df = make_points_table(turnout_samples, state, elec, g, last_candidate="Turnout")

    df.to_csv(f"{output_folder}/raw_summaries/{run_id}.csv", index_label="race")
    turnout_df.to_csv(f"{output_folder}/turnout_adjusted_summaries/{run_id}.csv", index_label="race")
    return

if __name__=="__main__":
    main()
