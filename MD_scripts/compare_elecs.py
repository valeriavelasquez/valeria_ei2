### NOTE: paths will not work as written since this has been moved to `ei/MD_scripts/`!
###       should be an easy fix though, if wanted

from info import info
import pandas as pd
import os
pd.options.display.max_columns = 1000
pd.options.display.max_rows = 10000

elections_dict = info["MD_eday"]["elections"]
candidates = ["SEN16PD_DE", "GOV14D", "GOV14PD_AB", "GOV18D", "GOV18PD_BJ"]
geographies = ["Statewide", "Prince George's", "Charles", "BaltimoreCity", "BaltimoreCounty", "Eastern"]
output_folder = "outputs/summary_comparisons"
os.makedirs(output_folder, exist_ok=True)

split = True

if split:
    vote_types = ["eday_WVAP", "full_WVAP", "eday_BVAP", "full_BVAP", \
                "eday_HVAP", "full_HVAP", "eday_OVAP", "full_OVAP"]
    suffix = "WVAP-BVAP-HVAP"
else:
    vote_types = ["eday_WVAP", "full_WVAP", "eday_POCVAP", "full_POCVAP"]
    suffix = "WVAP"

for candidate in candidates:
    elec = candidate.split("_")[0] if "_" in candidate else candidate[:-1]
    candidate_name = elections_dict[elec]["candidates"][candidate]["name"].split(" ")[-1]

    candidate_df = pd.DataFrame(columns=geographies, index=vote_types)
    turnout_df = pd.DataFrame(columns=geographies, index=vote_types)
    for vote_type in vote_types:
        vote = vote_type.split("_")[0]
        group = vote_type.split("_")[1]
        group_col = "OVAP" if group == "POCVAP" else group
        for geography in geographies:
            if geography == "Statewide":
                folder = f"outputs/MD_{vote}"
                file = f"MD_{vote}_{elec}_{suffix}.csv"
            else:
                folder = f"outputs/MD_{vote}_{geography.replace(' ', '')}"
                file = f"MD_{vote}_{geography.replace(' ', '')}_{elec}_{suffix}.csv"
            try:
                summary = pd.read_csv(f"{folder}/summaries/turnout_adjusted_summaries/{file}").set_index("race")
                candidate_df[geography].loc[vote_type] = summary[candidate].loc[group_col]
                turnout_df[geography].loc[vote_type] = summary[f"{elec}Turnout"].loc[group_col]
            except:
                continue

    candidate_df.to_csv(f"{output_folder}/{elec}_{candidate_name}_support_{suffix}.csv")
    turnout_df.to_csv(f"{output_folder}/{elec}_turnout_{suffix}.csv")
