#!/usr/bin/env python
"""Submit a job to the SLURM Workload Manager.

usage: subSLURM.py [-h] [-w [WALLTIME]] [-N NAME] [-n [NNODES]] [-t [NTASKS]]
                   [-e EXECUTABLE] [--no-mpi] [--set-mpi-library]
                   [-a JOBARRAY [JOBARRAY ...]] [-d] [-p TMP] [-s]
                   [-P PARTITION] [-Q QOS] [-A ACCOUNT] [--ITP]

optional arguments:
  -h, --help            show this help message and exit
  -w [WALLTIME], --walltime [WALLTIME]
                        maximum job runtime (in minutes) (default: 30)
  -N NAME, --name NAME  SLURM job name (default: SLURM_job)
  -n [NNODES], --nnodes [NNODES]
                        number of nodes to allocate (default: 1)
  -t [NTASKS], --ntasks [NTASKS]
                        number of tasks per node (default: 16)
  -e EXECUTABLE, --executable EXECUTABLE
                        executable for job submission (default:
                        solve_xml_mumps)
  --no-mpi              submit single-core job (default: False)
  --set-mpi-library     set I_MPI_PMI_LIBRARY environment variable (default:
                        False)
  -a JOBARRAY [JOBARRAY ...], --jobarray JOBARRAY [JOBARRAY ...]
                        submit job array to queue (default: None)
  -d, --dryrun          write submit file and exit (default: False)
  -p TMP, --tmp TMP     write output and error to TMP file instead to slurm-
                        SLURM-ID.out (default: None)
  -s, --silent          suppress output to stdout (default: False)
  -P PARTITION, --partition PARTITION
                        specify the partition (default: mem_0064)
  -Q QOS, --qos QOS     specify quality of service (QOS) (default:
                        normal_0064)
  -A ACCOUNT, --account ACCOUNT
                        specify user account (QOS) (default: p70072)
  --ITP, --itp          override the partition/qos/account settings and use
                        the institute nodes (default: False)
"""

import argparse
from argparse import ArgumentDefaultsHelpFormatter as help_formatter
import subprocess
import sys
import textwrap


# parse command-line arguments
parser = argparse.ArgumentParser(formatter_class=help_formatter)

parser.add_argument("-w", "--walltime", nargs="?", default=30, type=int,
                    help="maximum job runtime (in minutes)")
parser.add_argument("-N", "--name", default="SLURM_job", type=str,
                    help="SLURM job name")
parser.add_argument("-n", "--nnodes", nargs="?", default=1, type=int,
                    help="number of nodes to allocate")
parser.add_argument("-t", "--ntasks", nargs="?", default=16, type=int,
                    help="number of tasks per node")
parser.add_argument("-e", "--executable", default="solve_xml_mumps",
                    type=str, help="executable for job submission")
parser.add_argument("--no-mpi", action="store_true",
                    help="submit single-core job")
parser.add_argument("--set-mpi-library", action="store_true",
                    help="set I_MPI_PMI_LIBRARY environment variable")
parser.add_argument("-a", "--jobarray", nargs="+", type=str,
                    help="submit job array to queue")
parser.add_argument("-d", "--dryrun", action="store_true",
                    help="write submit file and exit")
parser.add_argument("-p", "--tmp", type=str,
                    help=("write output and error to TMP file instead to "
                          "slurm-SLURM-ID.out"))
parser.add_argument("-s", "--silent", action="store_true",
                    help="suppress output to stdout")
parser.add_argument("-P", "--partition", type=str, default="mem_0064",
                    help="specify the partition")
parser.add_argument("-Q", "--qos", type=str, default="normal_0064",
                    help="specify quality of service (QOS)")
parser.add_argument("-A", "--account", type=str, default="p70072",
                    help="specify user account")
parser.add_argument("--ITP", "--itp", action="store_true",
                    help=("override the partition/qos/account settings and "
                          "use the institute nodes"))
parser.add_argument("--dev", action="store_true",
                    help=("use the development QOS (for runtimes < 10')"))

params = vars(parser.parse_args())


# override partition, qos and account if ITP is specified
if params.get("ITP"):
    itp_params = {'qos': 'p70623_0256',
                  'partition': 'mem_0256',
                  'account': 'p70623'}
    params.update(itp_params)

# development queue
if params.get("dev"):
    dev_params = {'qos': 'devel_0128'}
    params.update(dev_params)

# print options
if not params.get("silent"):
    print("""
        Options:

            Job name:               {name}
            Maximum job runtime:    {walltime} minutes
            Number of nodes:        {nnodes}
            Executable file:        {executable}
            Job array directories:  {jobarray}
            Output files:           {tmp}
            Partition:              {partition}
            Quality of Service:     {qos}
            Account:                {account}

    """.format(**params))

# process parameters
joblist = params.get("jobarray")
if joblist:
    NJOBS = len(joblist)
    DIRS = " ".join(joblist)

    JOBARRAY_SETTINGS = """
        #SBATCH --array 1-{0}

        JOB_DIRS=({1})
        INDEX=$((${{SLURM_ARRAY_TASK_ID}} - 1))
        cd ${{JOB_DIRS[${{INDEX}}]}}
    """.format(NJOBS, DIRS)
else:
    JOBARRAY_SETTINGS = ""

if params.get("tmp"):
    TMP_FILE = """
        #SBATCH --output={tmp}
        #SBATCH --error={tmp}
    """.format(**params)
else:
    TMP_FILE = ""

# assemble SLURM options
SLURM_OPTIONS = """
        #!/bin/bash

        #SBATCH --job-name={name}
        #SBATCH --time=00:{walltime}:00
        #SBATCH --nodes {nnodes}
        #SBATCH --ntasks-per-node={ntasks}
        #SBATCH --partition={partition}
        #SBATCH --qos={qos}
        #SBATCH --account={account}
""".format(**params)
SLURM_OPTIONS = SLURM_OPTIONS[1:]

if params.get("no_mpi"):
    MPI = ""
else:
    MPI = "mpirun -np $SLURM_NTASKS"

if params.get("set_mpi_library"):
    MPI_LIBRARY = "export I_MPI_PMI_LIBRARY=/cm/shared/apps/slurm/current/lib/libpmi.so"
else:
    MPI_LIBRARY = ""

EXECUTABLE = """
        unset I_MPI_PIN_PROCESSOR_LIST
        {MPI_LIBRARY}
        time {MPI} {executable}
""".format(MPI=MPI, MPI_LIBRARY=MPI_LIBRARY, **params)

if joblist and not params.get('tmp'):
    EXECUTABLE = """
        OUTPUT=$SLURM_SUBMIT_DIR/slurm-${{SLURM_ARRAY_JOB_ID}}_${{SLURM_ARRAY_TASK_ID}}.out
        ln -s $OUTPUT .
        {EXECUTABLE}
        unlink $(basename $OUTPUT)
        gzip $OUTPUT
        mv $OUTPUT.gz .
    """.format(EXECUTABLE=EXECUTABLE)

SLURM_INPUT = SLURM_OPTIONS + JOBARRAY_SETTINGS + TMP_FILE + EXECUTABLE

# remove leading whitespace
SLURM_INPUT = textwrap.dedent(SLURM_INPUT)

# print SLURM input file
with open("SLURM_INPUT.sh", "w") as f:
    f.write(SLURM_INPUT)
    if not params.get("silent"):
        print("\nSLURM settings:\n" + SLURM_INPUT)

if params.get("dryrun"):
    sys.exit()

# open a pipe to the sbatch command
sbatch = subprocess.Popen(["sbatch"], stdin=subprocess.PIPE)

# send SLURM_INPUT to sbatch
sbatch.communicate(SLURM_INPUT.encode('utf-8'))
