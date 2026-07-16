#!/bin/bash --login
#SBATCH -p multicore      # Single-node multicore job
#SBATCH -n 16             # Number of cores
#SBATCH -J mainJob        # Job name

# Submit jobs and capture Job IDs
job1=$(sbatch --parsable paraWssTimePlot.sh)
job2=$(sbatch --parsable paraTawssCyclePlot.sh)
job3=$(sbatch --parsable paraGeomWssStream.sh)
job4=$(sbatch --parsable paraOsi.sh)
job5=$(sbatch --parsable paraTawss.sh)
job6=$(sbatch --parsable paraOsiCyclePlot.sh)
job7=$(sbatch --parsable extract-multiple-wss-percentiles.sh)

# Submit a final job that waits for all the above jobs to complete
sbatch --dependency=afterok:$job1:$job2:$job3:$job4:$job5:$job6:$job7 <<EOF
#!/bin/bash
#SBATCH -p multicore
#SBATCH -n 16
#SBATCH -J postProcess

# Create log directory in postProcessing
mkdir -p postProcessing/log

# Move visualization and parameters folders and CSV files to postProcessing
mv visualizations postProcessing/
mv parameters postProcessing/
mv *.csv postProcessing/

# Move log and out files to postProcessing/log
mv *.log postProcessing/log/
mv *.out postProcessing/log/
mv *.output postProcessing/log/
EOF