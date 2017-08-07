# Run probabilistic tractography via FSL FDT's ProbTrackX2
# Requires having run bedpostx (or TRACULA) already
# Runs network connectivity (omatrix1) by creating diffusion-space aparc masks
# KRS 2017.08.04

import os
from glob import glob
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs

work_dir = os.path.abspath('/om/scratch/Fri/ksitek/tractography')
tracula_dir = os.path.abspath('/om/project/voice/processedData/tracula/')
out_dir = os.path.abspath('/om/project/voice/processedData/probtrackx2')
data_dir = os.path.abspath('/om/project/voice/processedData/openfmri')

# create the subject list
#subject_list = ['voice999']
subject_list = [os.path.basename(x) for x in sorted(glob(data_dir+'/voice*'))]

# define the FreeSurferColorLUT for  label name-grabbing:
fsLUT = os.path.join('/cm/shared/openmind/freesurfer/5.3.0/',
                     'FreeSurferColorLUT.txt')

info = dict(dwi=[['subject_id', 'data']],
            aseg=[['subject_id', 'aparc+aseg+2mm']],
            thsamples=[['subject_id', 'merged_th1samples']],
            fsamples=[['subject_id', 'merged_f1samples']],
            phsamples=[['subject_id', 'merged_ph1samples']],
            mask=[['subject_id', 'nodif_brain_mask']],
#            mask2=[['subject_id', 'nodif_brain_mask']],
#            target_masks=[['subject_id', 'nodif_brain_mask']]
            )

infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id']),
                     name="infosource")
infosource.iterables = ('subject_id', subject_list)

datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'],
                                               outfields=list(info.keys())),
                     name='datasource')
datasource.inputs.template = "%s/%s"
datasource.inputs.base_directory = tracula_dir
datasource.inputs.field_template = dict(dwi='%s/dmri/%s.nii.gz',
                                        aseg='%s/dlabel/diff/%s.bbr.nii.gz',
                                        thsamples='%s/dmri.bedpostX/%s.nii.gz',
                                        fsamples='%s/dmri.bedpostX/%s.nii.gz',
                                        phsamples='%s/dmri.bedpostX/%s.nii.gz',
                                        mask="%s/dmri.bedpostX/%s.nii.gz"#,
#                                        mask2="%s/dmri.bedpostX/%s.nii.gz",
#                                        target_masks="%s/dmri.bedpostX/%s.nii.gz"
                                        )
datasource.inputs.template_args = info
datasource.inputs.sort_filelist = True

# custom function that reads nifti with nibabel/nilearn & finds unique values,
# which it will then send to binarize to create per-ROI mask files
def aseg_value_grabber(aseg_file):
    import numpy as np
    import nibabel as nib

    aseg_img = nib.load(aseg_file)
    label_values = np.unique(aseg_img.get_data())

    return label_values

aseg_value_grabber = pe.Node(name='aseg_value_grabber',
               interface=util.Function(input_names=['aseg_file'],
                                  output_names=['label_values'],
                                  function=aseg_value_grabber))

def aseg_name_grabber(label_values, fslut_file):
    import numpy as np
    import pandas as pd

    fslut = pd.read_table(fslut_file, delim_whitespace=True,
                          skip_blank_lines=True, skiprows=[0, 1, 2, 3],
                          comment='#', header=None,
                          names=['Num','LabelName','R','G','B','A'])
    # only keep values between 1-999 and between 3000-4999
    label_values_filtered = label_values[((label_values<100) & (label_values>0)) | ((label_values<5000) & (label_values>=3000))]
    label_names = fslut.set_index('Num').loc[label_values_filtered, 'LabelName'].tolist()

    # this goes to a mapnode next, and mapnode wants a list of lists,
    # not an np.array
    #label_values_filtered = label_values_filtered.tolist()[0]
    label_values_filtered = [[x] for x in label_values_filtered]
    return label_values_filtered, label_names

aseg_name_grabber = pe.Node(name='aseg_name_grabber',
               interface=util.Function(input_names=['label_values', 'fslut_file'],
                                  output_names=['label_values_filtered','label_names'],
                                  function=aseg_name_grabber))
aseg_name_grabber.inputs.fslut_file = fsLUT

# create a binary mask for a single region
#binarize = pe.Node(interface=fs.model.Binarize(),name='binarize')
#binarize.inputs.match = [4035] # 4035 = wm-rh-insula

# mapnode version of binarize that takes in aseg label values
binarize = pe.MapNode(interface=fs.model.Binarize(),
                      iterfield=['match'], name='binarize')
binarize.plugin_args = {'sbatch_args': '--qos=gablab --mem=40G --time=1:00:00',
                       'overwrite': True}

# custom node to take the binarize outputs and bring the workflow back together
# also should create a txt file with binarize output file paths
def make_target_mask_txt(target_mask_files):
    import numpy as np
    import os
    target_mask_txt = os.path.join(os.getcwd(), 'target_masks.txt')
    #np.savetxt(target_mask_txt, target_mask_files)
    file = open(target_mask_txt, 'w')
    file.writelines("%s\n" % item  for item in target_mask_files)
    file.close()

    #output the file name for probtrackx network mask input
    return target_mask_txt

make_target_mask_txt = pe.Node(name='make_target_mask_txt',
               interface=util.Function(input_names=['target_mask_files'],
                                  output_names=['target_mask_txt'],
                                  function=make_target_mask_txt))

# probtrackx2
pbx2 = pe.Node(interface=fsl.ProbTrackX2(), name='probtrackx')
#pbx2.inputs.omatrix2 = True
pbx2.inputs.omatrix1 = True
pbx2.inputs.opd = True
pbx2.inputs.os2t = True # needs --target_masks in order to run?
pbx2.inputs.s2tastext = True
pbx2.inputs.loop_check = True
pbx2.inputs.verbose = 1

datasink = pe.Node(interface=nio.DataSink(), name='datasink')
datasink.inputs.base_directory = out_dir

tractography = pe.Workflow(name='tractography')
tractography.connect([
    (infosource, datasource, [('subject_id', 'subject_id')])])
tractography.connect([(binarize, pbx2, [('binary_file', 'seed')] )])
tractography.connect([(datasource, pbx2,
                      [('thsamples', 'thsamples'),
                       ('phsamples', 'phsamples'),
                       ('fsamples', 'fsamples'),
                       ('mask', 'mask')#,
#                       ('mask2', 'target2')#,
#                       ('mask2', 'target1')#,
                       ])])
tractography.connect([(datasource, binarize, [('aseg','in_file')] )])

# new connections for aseg mapnode stuff:
tractography.connect([(datasource, aseg_value_grabber, [('aseg','aseg_file')] )])
tractography.connect([(aseg_value_grabber, aseg_name_grabber, [('label_values','label_values')] )])
tractography.connect([(aseg_name_grabber, binarize,
#                       [('label_values_filtered','match'), ('label_names', 'binary_file')] )])
                       [('label_values_filtered','match')] )])
#tractography.connect([(binarize, make_target_mask_txt, [('binary_file','target_mask_files')] )])
#tractography.connect([(make_target_mask_txt, pbx2, [('target_mask_txt','target_masks')] )])
tractography.connect([(binarize, pbx2, [('binary_file','target_masks')] )])

tractography.connect([(infosource, datasink, [('subject_id', 'container')]),
                      (pbx2, datasink,
                      [('fdt_paths','probtrackx.@fdt_paths'),
                       ('log','probtrackx.@log'),
                       ('lookup_tractspace','probtrackx.@lookup_tractspace'),
#                       ('matrix2_dot','probtrackx.@matrix2_dot'),
                       ('matrix1_dot','probtrackx.@matrix1_dot'),
                       ('targets','probtrackx.@targets'),
                       ('way_total','probtrackx.@way_total') ]) ])

tractography.base_dir = work_dir
tractography.run(plugin='SLURM',
                 plugin_args={'sbatch_args': '--time=24:00:00 -N1 -c2 --mem=40G',
                 'max_jobs':200})
