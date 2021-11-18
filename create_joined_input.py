import sys
if ".." not in sys.path:
    sys.path.append("..")

from ei_meta import meta_data
import geopandas as gpd
import pandas as pd
import click

@click.command()
@click.option('-state', default="MA")
def join_data(state):
    elections = set(meta_data[state]["elections"].keys())
    shp_path = meta_data[state]["shapefile_path"]
    MATCH_KEY = meta_data[state]["MATCH_KEY"]
    output_file = f"../inputs/{state}/joined_data.csv"
    print(f"Joining {len(elections)} elections to the {shp_path} shapefile...")

    gdf = gpd.read_file(shp_path)
    demog_cols = list(filter(lambda x: "VAP" in x, gdf.columns))
    gdf = gdf[["NAME"] + demog_cols]
    for elec in elections:
        print(f" -- Joining {elec} to geodataframe...")

        candidate_dict = meta_data[state]["elections"][elec]["candidates"]
        renames = {c: f"{elec}_{candidate_dict[c]}" for c in candidate_dict.keys()}

        df = pd.read_csv(f"../inputs/{state}/QA_elections/{elec}.csv")
        df = df.rename(columns=renames)
        df = df[[MATCH_KEY] + list(renames.values())]

        gdf = gdf.merge(df, on=MATCH_KEY, how='outer')

    gdf.to_csv(output_file)
    return

if __name__=="__main__":
    join_data()