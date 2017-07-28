#!/bin/bash

bids_dir=/om/project/voice/bids/data/
out_dir=${bids_dir}derivatives/rs/
fs_dir=/om/project/voice/processedData/fsdata_session1/
script_dir=/om/user/ksitek/scripts/OpenfMRI/resting_bids/

target_file=/om/user/ksitek/STUT/scripts/reference_files/OASIS-30_Atropos_template_in_MNI152_2mm.nii.gz

python ${script_dir}fmri_ants_bids.py -d $bids_dir -t rest -m 103 \
  --sd=$fs_dir --target=$target_file \
  -w /om/scratch/Mon/ksitek/rs_${sub} \
  -p 'SLURM' \
  --plugin_args "dict(sbatch_args='--qos=gablab --time=23:00:00')" \
  -ss 1 -rs
