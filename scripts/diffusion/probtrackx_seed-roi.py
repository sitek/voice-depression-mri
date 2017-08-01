# Run probabilistic tractography via FSL FDT's ProbTrackX2
# Requires having run bedpostx (or TRACULA) already
# Also extracts an aparc seed mask
# KRS 2017.07.28

import os
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs

work_dir = os.path.abspath('/om/scratch/Tue/ksitek/tractography')
subject_list = ['voice999']

info = dict(dwi=[['subject_id', 'data']],
            aseg=[['subject_id', 'aparc+aseg+2mm']],
            thsamples=[['subject_id', 'merged_th1samples']],
            fsamples=[['subject_id', 'merged_f1samples']],
            phsamples=[['subject_id', 'merged_ph1samples']],
            target_masks=[['subject_id', ['nodif_brain_mask']]])

infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id']),
                     name="infosource")
infosource.iterables = ('subject_id', subject_list)

datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'],
                                               outfields=list(info.keys())),
                     name='datasource')
datasource.inputs.template = "%s/%s"
datasource.inputs.base_directory = os.path.abspath('/om/project/voice/processedData/tracula/')
datasource.inputs.field_template = dict(dwi='%s/dmri/%s.nii.gz',
                                        aseg='%s/dlabel/diff/%s.bbr.nii.gz',
                                        thsamples='%s/dmri.bedpostX/%s.nii.gz',
                                        fsamples='%s/dmri.bedpostX/%s.nii.gz',
                                        phsamples='%s/dmri.bedpostX/%s.nii.gz',
#                                        seed_file="%s.bedpostX/%s.nii.gz",
                                        target_masks="%s/dmri.bedpostX/%s.nii.gz")
datasource.inputs.template_args = info
datasource.inputs.sort_filelist = True

binarize = pe.Node(interface=fs.model.Binarize(),name='binarize')
binarize.inputs.match = [4035] # 4035 = wm-rh-insula

pbx2 = pe.Node(interface=fsl.ProbTrackX2(), name='probtrackx')
#pbx2.inputs.out_dir = os.path.abspath('/om/project/voice/processedData/probtrackx2')

pbx2.inputs.target2 = os.path.join('/om/project/voice/processedData/tracula/',
                                    'voice999/dmri.bedpostX/nodif_brain_mask.nii.gz')
pbx2.inputs.omatrix2 = True
pbx2.inputs.opd = True
pbx2.inputs.os2t = True
pbx2.inputs.s2tastext = True
pbx2.inputs.loop_check = True

pbx2.inputs.samples_base_name = os.path.join('/om/project/voice/processedData/tracula/',
                                    'voice999/dmri.bedpostX/merged')
pbx2.inputs.verbose = 1

datasink = pe.Node(interface=nio.DataSink(), name='datasink')
datasink.inputs.base_directory = os.path.abspath('/om/project/voice/processedData/probtrackx2')

tractography = pe.Workflow(name='tractography')
tractography.connect([
    (infosource, datasource, [('subject_id', 'subject_id')])])
tractography.connect([(binarize, pbx2, [('binary_file', 'seed')] )])
tractography.connect([(datasource, pbx2,
                      [('thsamples', 'thsamples'),
                       ('phsamples', 'phsamples'),
                       ('fsamples', 'fsamples'),
                       ('target_masks', 'mask')])])
tractography.connect([(datasource, binarize, [('aseg','in_file')] )])
tractography.connect([(infosource, datasink, [('subject_id', 'container')]),
                      (pbx2, datasink,
                      [('fdt_paths','probtrackx.@fdt_paths'),
                       ('log','probtrackx.@log'),
                       ('lookup_tractspace','probtrackx.@lookup_tractspace'),
                       ('matrix2_dot','probtrackx.@matrix2_dot'),
                       ('targets','probtrackx.@targets'),
                       ('way_total','probtrackx.@way_total') ]) ])

tractography.base_dir = work_dir
tractography.run('SLURM',
                 plugin_args={'sbatch_args': '--qos=gablab --time=18:00:00 -N1 -c2 --mem=40G'})
