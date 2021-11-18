from info import info
import os
import click
from time import sleep


@click.command()
@click.option('-state')
@click.option('-num_tunes', type=int)
@click.option('-num_draws', type=int)
@click.option('-run_elec')
@click.option('-run_county')
def main(state, num_tunes, num_draws, run_elec, run_county):
    elecs = info[state]["elections"].keys()
    counties = info[state]["counties"]
    for county in counties:
        if run_county:
            if county != run_county:
                continue
        for elec in elecs:
            if run_elec:
                if elec != run_elec:
                    continue
            for groups in [["BVAP"], ["BVAP", "WVAP", "HVAP"]]:
                groups_arg = "-g " + " -g ".join(groups)
                county_arg = '' if county is None else f'-county "{county}"'
                county_id = '' if county is None else f'_{county.replace(" ", "")}'
                output_folder = f"outputs/{state+county_id}/diagnostics"
                os.makedirs(output_folder, exist_ok=True)
                run_id = f"{state+county_id}_{elec}_{'-'.join(groups)}"
                with open("job.sh", "w") as f:
                    f.writelines("#!/bin/bash\n")
                    f.writelines(f"#SBATCH --job-name={elec}\n")
                    f.writelines(f"#SBATCH --time=4-00:00:00\n")
                    f.writelines(f"#SBATCH --nodes=1\n")
                    f.writelines(f"#SBATCH --ntasks-per-node=4\n")
                    f.writelines(f"#SBATCH --mem=16000\n")
                    f.writelines(f"#SBATCH -o {output_folder}/{run_id}.txt\n")
                    f.writelines(f"#SBATCH -e {output_folder}/{run_id}.txt\n\n")

                    f.writelines(f"python ei.py -state {state} -elec {elec} {groups_arg} -num_tunes {num_tunes} -num_draws {num_draws} {county_arg}\n")
                    f.writelines(f"python viz.py -state {state} -elec {elec} {groups_arg} {county_arg}\n")
                    f.writelines(f"python summary.py -state {state} -elec {elec} {groups_arg} {county_arg}\n")

                os.system("sbatch -p largemem job.sh")
                sleep(30)
    return

if __name__=="__main__":
    main()
