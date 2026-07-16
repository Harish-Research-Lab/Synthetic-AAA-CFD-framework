#!/bin/bash --login
#SBATCH -p multicore     # Single-node multicore job
#SBATCH -n 8             # (or --ntasks=8) number of cores - can be 2-40.

# Ensure the paraview modulefile is loaded
module  purge
module load paraview/5.9.1

# Set permissions for the script
chmod +x paraWssTimePlot.py

# Run pvbatch - you do not control this with the paraview GUI
mpiexec pvbatch --system-mpi paraWssTimePlot.py