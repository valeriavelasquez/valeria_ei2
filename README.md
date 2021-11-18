# EI workflow
This is a directory set up to make it easy to run `PyEI` and store the outputs in a helpful way.
## Installations
First, you should clone this repository and start working on your own branch, so that your outputs do not collide with anyone else's.
```sh
git clone https://github.com/gabeschoenbach/ei.git
cd ei
git checkout -b {YOUR_BRANCH_NAME}
```
TODO: determine the minimal installations necessary to make this project runnable.
## Pre-processing
The first — and most challenging — part of the EI pipeline is preparing an accurate dataset that can be fed into the `PyEI` machinery. This data can be in a tabular (CSV) format or stored in a shapefile. You should make a `shapes/` folder at the root of this directory and put your shapefile or CSV inside of it. For example, if you want to run EI on a Massachusetts 2020 VTD shapefile stored in a folder called `MA_vtd20`, you should put that folder in shapes so that `ei/shapes/MA_vtd20/` is a valid path.
### Preparing data
The minimal information needed on your input data is the following:
* Demographic columns: a total electorate column like `VAP` or `CVAP` and then a breakdown into racial groups, i.e. `WVAP`, `BVAP`, `HVAP`, `ASIANVAP`, `NHPIVAP`, `AMINVAP`, `2MOREVAP`, `OTHERVAP`. These columns should have counts for how many voters in each group reside in each geographical unit (row).
* Election columns: A column for the vote totals for a given candidate. For example, `BMAY21PAG` refers to the votes that Annissa Essaibi George won in Boston's 2021 Mayoral primary race.

Optional columns could include:
* A county column, helpful if you want to run EI on individual counties.

### Using `info.py`
Once you have prepared your input data, you should add its information to the `info.py` file. Every script in this directory relies on `info.py` to understand the data, so it's important to carefully fill it out when you add new data.
```sh
"MA_vtd20": {
    "shapefile_path": "shapes/MA_vtd20",
    "COUNTY_COL": "COUNTYFP20",
    "counties": [None],
    "elections": {
        "BMAY21P": {
            "POP_COL": "VAP",
            "candidates": {
                "BMAY21PAG": {
                    "name": "Annissa George",
                    "race": "W",
                    "won": True,
                },
                "BMAY21PAC": {
                    "name": "Andrea Campbell",
                    "race": "B",
                    "won": False,
                },
                "BMAY21PKJ": {
                    "name": "Kim Janey",
                    "race": "B",
                    "won": False,
                },
                "BMAY21PMW": {
                    "name": "Michelle Wu",
                    "race": "A",
                    "won": True,
                },
            },
        },
    },
},
```
The above blob contains information about the `MA_vtd20` file that contains just one election — the 2021 Boston Mayoral race — labeled `BMAY21P`. Inside, you specify the population basis you want to use for the election — since the `MA_vtd20` shapefile has `VAP`, `WVAP`, `BVAP`, ... columns, we specify `VAP`. For each candidate, we specify a well-formatted `name` that will be used in the plots, along with the candidate's `race` and whether they actually won the election (in this example, the top two candidates advance, which is why Wu and George both have `won=True`). Neither `race` nor `won` is currently used, but it's helpful to keep track of. `COUNTY_COL` and `counties` can be left as the empty string and `[None]`, respectively, if you aren't planning on running EI on individual counties.
## Running EI
The main EI script is `ei.py`. It accepts a `-state` argument that refers to the key in `info.py` that points to the data you're interested in (in our example, this would be `MA_vtd20`). The `-elec` argument determins which election EI will be run on, and you can specify as many `-g` arguments as groups you want to divide the electorate into. Optionally you can set a `-county` argument to run it on just one county. Lastly, you can specify a `-num_tunes` and `-num_draws` argument to set how long to run the MCMC process that happens under the hood of EI. The default is set to 10 for testing, but you should try 1000 for each to get good convergence.

For example, if we wanted to run EI on the 2021 Boston Mayoral primary on our Massachusetts shapefile, breaking the electorate into Black and non-Black voters, we would run:
```sh
python run_ei.py -state MA_vtd20 -elec BMAY21P -g BVAP -num_tunes 1000 -num_draws 1000
```
And if we wanted to run it while dividing the electorate into White, Black, Hispanic, and all other voters, we would run:
```sh
python run_ei.py -state MA_vtd20 -elec BMAY21P -g WVAP -g BVAP -g HVAP -num_tunes 1000 -num_draws 1000
```
This process will create (if not already there) an `outputs/MA_vtd20/` folder in which to store results. Standard output and error will be printed to the terminal, but an `outputs/MA_vtd20/ei/` subfolder will be created that stores the EI outputs as a `.pickle` file, along with a `.csv` file of the final input data in `outputs/MA_vtd20/final_inputs/`. Each of these files will be named according to the EI run that it corresponds, which will be of the form `{state}_{election}_{groups}`. As an example, the EI result from last Python call above would be saved as `outputs/MA_vtd20/ei/MA_vtd20_BMAY21P_WVAP-BVAP-HVAP.pickle`.

## Post-processing
You can summarize and visualize the outputs of a given EI run by calling the `summary.py` and `viz.py` scripts, respectively. On the above EI run, calling
```sh
python summary.py -state MA_vtd20 -elec BMAY21P -g WVAP -g BVAP -g HVAP
python viz.py -state MA_vtd20 -elec BMAY21P -g WVAP -g BVAP -g HVAP
```
would create `outputs/MA_vtd20/summaries/` and `outputs/MA_vtd20/plots/` respectively. The subfolders in those directories that include the phrase `turnout_adjusted` refer to summaries and plots that compute candidate preferences only out of voters inferred to have participated in the election — that is, voters that had not chosen to abstain or vote for an unlisted candidate.

## Cluster jobs
The `submit_jobs.py` script creates and runs (via `sbatch`) a `job.sh` file that calls `ei.py`, `viz.py`, and `summary.py` for every election in the `elections` section of your state in `info.py`. Hardcoded into the script (but easily editable) is the choice of demographic groups you want in the inference. As of 10/25/21, its set to `WVAP, BVAP, HVAP` (and will implicitly group all the rest of the population into `OVAP`, "Other"). To run this on the cluster, simply run
```sh
python submit_jobs.py -state MA_vtd20 -num_tunes 1000 -num_draws 1000
```
If you only want to run it on one election, you can specify so with an optional `-elec` argument.
