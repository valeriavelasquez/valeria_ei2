from pyei.r_by_c import RowByColumnEI
from info import info
import geopandas as gpd
import pandas as pd
import numpy as np
import math
import click
import os
import pickle
import warnings
warnings.filterwarnings('ignore')
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

def create_processed_df(state, elec, g, county):
    print(f" -- Processing {elec}")
    df = gpd.read_file(info[state]["shapefile_path"])
    if county is not None:
        if county == "Eastern":
            counties = ["Worcester", "Somerset", "Wicomico", "Dorchester", "Talbot", "Caroline", "Queen Anne's", "Kent", "Cecil"]
            df = df[df.COUNTY.isin(counties)]
        else:
            df = df[df.COUNTY == county]
    county_id = '' if county is None else f'_{county.replace(" ", "")}'
    
    COUNTY_COL = info[state]["COUNTY_COL"]
    election_dict = info[state]["elections"][elec]
    candidate_dict = election_dict["candidates"]
    candidate_cols = list(candidate_dict.keys())
    candidate_names = [candidate_dict[col]["name"] for col in candidate_cols]
    TOT_ELECTORATE = election_dict["POP_COL"]
    groups = list(g)

    run_id = f"{state+county_id}_{elec}_{'-'.join(groups)}"

    df = df[[COUNTY_COL, TOT_ELECTORATE] + groups + candidate_cols]
    numeric_cols = [TOT_ELECTORATE] + groups + candidate_cols
    df = df.dropna()
    # print(df.iloc[200:230])
    # print(df[numeric_cols].head())
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
    df = df.dropna()
    # print(df[numeric_cols].iloc[200:230])
    df[numeric_cols] = df[numeric_cols].astype(int)
    df["OVAP"] = df[TOT_ELECTORATE] - df[groups].sum(axis=1)
    groups += ["OVAP"]
    orig_length = len(df)
    df = df[df[TOT_ELECTORATE] > 0]
    print(f"After dropping NA and 0-{TOT_ELECTORATE}, len df {orig_length} -> {len(df)}")

    # Scale population to match votes, if needed
    df["TOT_VOTES"] = df[candidate_cols].sum(axis=1)
    df["factor"] = 1
    scaled_precincts = 0
    original_TOTPOP = df[TOT_ELECTORATE].sum()
    for i in range(len(df)):
        totpop = df[TOT_ELECTORATE].iloc[i]
        votes = df["TOT_VOTES"].iloc[i]
        if votes > totpop:
            scaled_precincts += 1
            df["factor"].iloc[i] = votes / totpop
        for group in groups:
            df[group].iloc[i] = np.ceil(df[group].iloc[i] * df["factor"].iloc[i])
        df[TOT_ELECTORATE].iloc[i] = sum(df[group].iloc[i] for group in groups)
    scaled_TOTPOP = df[TOT_ELECTORATE].sum()
    print(f"    -- Scaled {scaled_precincts} precincts, for an increase of {scaled_TOTPOP - original_TOTPOP} {TOT_ELECTORATE}")

    # Add in group % columns
    for group in groups:
            df[f"{group}_pct"] = df[group] / df[TOT_ELECTORATE]

    # Add in None candidate and % columns
    candidate_cols += [f"{elec}None"]
    candidate_names += ["None"]
    df[f"{elec}None"] = df[TOT_ELECTORATE] - df["TOT_VOTES"]
    df["TOT_VOTES"] = df[candidate_cols].sum(axis=1)
    for candidate in candidate_cols:
        df[f"{candidate}_pct"] = df[candidate] / df[TOT_ELECTORATE]

    # Assert things sum to 1
    assert df["TOT_VOTES"].sum() == df[TOT_ELECTORATE].sum()
    assert (df[groups].sum(axis=1) == df[TOT_ELECTORATE]).all()
    assert sum([df[f"{group}_pct"] for group in groups]).apply(lambda x: math.isclose(x, 1)).all()
    assert sum([df[f"{candidate}_pct"] for candidate in candidate_cols]).apply(lambda x: math.isclose(x, 1)).all()

    precinct_pops = np.array(df[TOT_ELECTORATE])
    votes_fractions = np.array(df[[f"{candidate}_pct" for candidate in candidate_cols]]).T
    group_fractions = np.array(df[[f"{group}_pct" for group in groups]]).T

    output_folder = f"outputs/{state+county_id}/final_inputs"
    os.makedirs(output_folder, exist_ok=True)
    df.to_csv(f"{output_folder}/{run_id}.csv")

    return  group_fractions, votes_fractions, precinct_pops, groups, candidate_names, run_id

def run_ei(state, elec, g, num_tunes, num_draws, county):
    group_fractions, votes_fractions, precinct_pops, groups, candidate_names, run_id = create_processed_df(state, elec, g, county)
    print(f"Running {groups} x {candidate_names} EI on {elec}")
    ei = RowByColumnEI(model_name='multinomial-dirichlet')
    ei.fit(group_fractions,
           votes_fractions,
           precinct_pops,
           groups,
           candidate_names,
           tune=num_tunes,
           draws=num_draws)

    county_id = '' if county is None else f'_{county.replace(" ", "")}'
    output_folder = f"outputs/{state+county_id}/ei"
    os.makedirs(output_folder, exist_ok=True)
    pickle.dump(ei, open(f"{output_folder}/{run_id}.pickle", "wb"))
    return

@click.command()
@click.option('-state', default="MD_eday")
@click.option('-elec', default="PRES12")
@click.option('-g', multiple=True)
@click.option('-num_tunes', default=10, type=int)
@click.option('-num_draws', default=10, type=int)
@click.option('-county')
def main(state, elec, g, num_tunes, num_draws, county):
    run_ei(state, elec, g, num_tunes, num_draws, county)

if __name__=="__main__":
    main()
