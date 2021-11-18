import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
from info import info
import os
pd.options.display.max_columns = 1000
pd.options.display.max_rows = 10000

def get_turnout():
    """
    Grab 2018 and 2020 Turnout numbers by precinct; cut and paste the PG County 2020 numbers into the 2018 data
    and return that. Will be used to determine precinct-level turnout as a share of the county turnout.
    """
    df = pd.read_excel("tabular/GG18 Voter TurnOut By Precinct By Party Revised.xlsx", header=4)
    df = df[df["District"] != "---"]
    df["MATCH"] = df["County"] + " " + df["District"].apply(lambda x: x[1:]) + "-" + df["Precinct"]
    cols = ["County", "MATCH", "Total Voted Dem", "Total Voted Rep",  "Total Voted Ind", "Active Registered Ind"]
    df = df[cols]

    df20 = pd.read_excel("tabular/PG20 Turnout By Precinct by Party Revised.xlsx", header=3)
    df20 = df20[df20["Precinct"] != "---- ---"]
    df20["MATCH"] = df20["County"] + " " + df20["Precinct"].apply(lambda x: x.replace(' ', '')[1:])
    cols = ["County", "MATCH", "Total Voted Dem", "Total Voted Rep",  "Total Voted Ind", "Active Registered Ind"]
    df20 = df20[cols]

    swapped_PG_df = pd.concat([df[df.County != "Prince George's"], df20[df20.County == "Prince George's"]])

    counties = set(swapped_PG_df.County)
    for county in counties:
        if county != "Prince George's":
            assert df[df.County == county].MATCH.nunique() == swapped_PG_df[swapped_PG_df.County == county].MATCH.nunique()
        else:
            assert df20[df20.County == county].MATCH.nunique() == swapped_PG_df[swapped_PG_df.County == county].MATCH.nunique()
    df[["Total Voted Dem", "Total Voted Rep"]] = df[["Total Voted Dem", "Total Voted Rep"]].astype(int)
    return swapped_PG_df

def get_shapefile():
    """
    Using the 1809-precinct shapefile with 11 generals and 5 primaries (E-Day vote only), 
    create the same MATCH column as our turnout data and return the winnowed geodataframe.
    """
    gdf = gpd.read_file("shapes/MD_precinct_primaries")
    gdf["County"] = gdf.NAME.apply(lambda x: x.split(" Precinct ")[0])
    gdf["Precinct"] = gdf.NAME.apply(lambda x: x.split(" Precinct ")[-1])
    gdf["MATCH"] = gdf.County + " " + gdf.Precinct

    elec_cols_function = lambda x: ("GOV" in x or "SEN" in x or "COMP" in x or "PRES" in x or "AG" in x) and ("SSEN" not in x and "SEND" not in x)
    elec_cols = list(filter(elec_cols_function, gdf.columns))
    vap_cols_function = lambda x: "VAP" in x
    vap_cols = list(filter(vap_cols_function, gdf.columns))
    cols = ["County","MATCH"] + vap_cols + elec_cols
    gdf = gdf[cols]
    gdf[elec_cols + vap_cols] = gdf[elec_cols + vap_cols].astype(int)
    
    return gdf

def get_extra_votes():
    """
    Get the absentee + early votes by county for all candidates we're interested in.
    We have to crop the column names to 10 chars since our shapefile will only have 10-char fields (dumb)
    """
    primaries = pd.read_csv("tabular/MD_abs_by_county_primaries.csv")
    generals = pd.read_csv("tabular/MD_abs_by_county_generals.csv")
    df = primaries.merge(generals, on='NAME')
    df = df.set_index("NAME")
    renames = {col:col[:10] for col in df.columns}
    df = df.rename(columns=renames)
    return df


def get_full_votes(elec_df, turnout_df, extras_df, candidate):
    """
    Given the `elec_df` with E-Day votes for each `candidate`, and `turnout_df` with turnout by party,
    allocate the county-wide extra votes (early + absentee) to each precinct in each county.
    This weights precincts by share of county-wide turnout (by party), as opposed to doing it by, say, VAP.
    """
    party = "Dem" if candidate.split("_")[0][-1] == "D" else "Rep"
    # tracking = {county: 0 for county in set(elec_df.County)}
    if candidate in extras_df.columns:
        elec_df[f"{candidate}_full"] = 0
        for i in range(len(elec_df)):
            county = elec_df.County.iloc[i]
            precinct = elec_df.MATCH.iloc[i]
            precincts_in_county = set(elec_df[elec_df.County == county].MATCH)

            if county == "St. Mary's":
                county = county.replace("St. Mary's", "Saint Mary’s")
                precinct = precinct.replace("St. Mary's", "Saint Mary's")
                precincts_in_county = set([s.replace("St. Mary's", "Saint Mary's") for s in precincts_in_county])
            elif county == "Queen Anne's":
                county = county.replace(county, "Queen Anne’s")
                precinct = precinct.replace(county, "Queen Anne’s")
                precincts_in_county = set([s.replace(county, "Queen Anne’s") for s in precincts_in_county])
            elif county == "Prince George's":
                county = county.replace(county, "Prince George’s")
                precinct = precinct.replace(county, "Prince George’s")
                precincts_in_county = set([s.replace(county, "Prince George’s") for s in precincts_in_county])

            county_votes = extras_df[candidate].loc[county] 
            county_turnout = turnout_df[turnout_df.MATCH.isin(precincts_in_county)][f"Total Voted {party}"].sum()
            try:
                precinct_turnout_df = turnout_df[turnout_df.MATCH == precinct]
                assert len(precinct_turnout_df) == 1
            except:
                # assert county == "Frederick"
                if candidate == "PRES12D":
                    print(f"No additional votes added in {precinct}")
                elec_df[f"{candidate}_full"].iloc[i] = elec_df[candidate].iloc[i]
                continue
            precinct_turnout = precinct_turnout_df[f"Total Voted {party}"].iloc[0]
            extra_votes = (precinct_turnout / county_turnout) * county_votes
            elec_df[f"{candidate}_full"].iloc[i] = elec_df[candidate].iloc[i] + extra_votes
    else:
        print(f"No extra vote data for {candidate}")

    return

def disaggregate(state):
    """
    Disaggregate the extra (early + absentee) votes, which we have at the county-level,
    down to precincts for every candidate.
    """
    turnout_df = get_turnout()
    elec_df = get_shapefile()
    extras_df = get_extra_votes()

    for elec in info[state]["elections"].keys():
        candidates = list(info[state]["elections"][elec]["candidates"].keys())
        for candidate in candidates:
            get_full_votes(elec_df, turnout_df, extras_df, candidate)

    return elec_df



if __name__=="__main__":
    disaggregated = disaggregate("MD")
    disaggregated.to_csv("tabular/MD_precincts_turnout_aggregated_abs.csv")