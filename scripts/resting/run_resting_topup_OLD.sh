#!/bin/bash

bids_dir=/om/project/voice/bids/data/
out_dir=${bids_dir}derivatives/rs/
fs_dir=/om/project/voice/processedData/fsdata_session1/
script_dir=/om/user/ksitek/scripts/OpenfMRI/resting_bids/

target_file=/om/user/ksitek/STUT/scripts/reference_files/OASIS-30_Atropos_template_in_MNI152_2mm.nii.gz

for sub in sub-voice860; do
  python ${script_dir}rsfmri_vol_surface_preprocessing_nipy.py -d /mindhive/xnat/dicom_storage/voice/dicom/voice860/session001_visit001/dicom/TrioTim-35115-20150825-101921-015000/15000-6-1.dcm \
  -f ${bids_dir}${sub}/'ses-1'/func/${sub}'_ses-1_task-rest_run-01_bold.nii.gz' \
  -s $sub -o ${out_dir} -t $target_file \
  --topup_AP=${bids_dir}${sub}/ses-1/fmap/${sub}'_ses-1_acq-func_dir-AP_run-02_epi.nii.gz' \
  --topup_PA=${bids_dir}${sub}/ses-1/fmap/${sub}'_ses-1_acq-func_dir-PA_run-01_epi.nii.gz' \
  --subjects_dir=$fs_dir \
  -w /om/scratch/Mon/ksitek/rs_${sub} \
  -p 'SLURM' --plugin_args "dict(sbatch_args='--qos=gablab --time=23:00:00')"

done
