
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs

subject_list = ['voice999']

info = dict(dwi=[['subject_id', 'data']],
            aseg=[['subject_id', 'aparc+aseg+2mm']]
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
binarize.inputs.match = 4035 # wm-rh-insula

pbx2 = pe.Node(interface=fsl.ProbTrackX2(), name='probtrackx')
pbx2.inputs.out_dir = os.path.abspath('/om/project/voice/processedData/probtrackx2')
pbx2.inputs.omatrix2=True
pbx2.inputs.opd = True
pbx2.inputs.os2t = True
pbx2.inputs.loop_check = True

datasink = pe.Node(interface=nio.DataSink(), name='datasink')
datasink.inputs.base_directory = os.path.abspath('/om/scratch/Fri/ksitek/probtrackx')

tractography = pe.Workflow(name='tractography')
tractography.connect([
    (infosource, datasource, [('subject_id', 'subject_id')],),
    (datasource, binarize, [('aparc','in_file'),
                            ('thsamples', 'thsamples'),
                            ('phsamples', 'phsamples'),
                            ('fsamples', 'fsamples') ])])
tractography.connect([(binarize, probtrackx, [('binary_file', 'seed')]
tractography.connect([(datasource, probtrackx,
                      [('thsamples', 'thsamples'),
                       ('phsamples', 'phsamples'),
                       ('fsamples', 'fsamples'),
                       ('target_masks', 'mask'),
                       ('aseg','aseg') ])])
tractography.connect([(infosource, datasink, [('subject_id', 'container')]),
                      (probtrackx, datasink,
                      [('probtrackx.fdt_paths','probtrackx.@fdt_paths'),
                       ('probtrackx.log','probtrackx.@log'),
                       ('probtrackx.lookup_tractspace','probtrackx.@lookup_tractspace'),
                       ('probtrackx.matrix2_dot','probtrackx.@matrix2_dot'),
                       ('probtrackx.targets','probtrackx.@targets'),
                       ('probtrackx.way_total','probtrackx.@way_total') ) ])

tractography.run('SLURM',
                 plugin_args={'sbatch_args': '--qos=gablab --time=18:00:00 -N1 -c2 --mem=40G'})
