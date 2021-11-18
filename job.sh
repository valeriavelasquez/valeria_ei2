#!/bin/bash
#SBATCH --job-name=GOV16
#SBATCH --time=4-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --mem=16000
#SBATCH -o outputs/NC/diagnostics/NC_GOV16_BVAP-WVAP-HVAP.txt
#SBATCH -e outputs/NC/diagnostics/NC_GOV16_BVAP-WVAP-HVAP.txt

python ei.py -state NC -elec GOV16 -g BVAP -g WVAP -g HVAP -num_tunes 1000 -num_draws 1000 
python viz.py -state NC -elec GOV16 -g BVAP -g WVAP -g HVAP 
python summary.py -state NC -elec GOV16 -g BVAP -g WVAP -g HVAP 
