#!/bin/bash

fsdir=/om/project/voice/processedData/fsdata_session1/

subject=voice998
outdir=/om/project/voice/processedData/probtrack/$subject/labels_a2009s
mkdir $outdir -p

mri_annotation2label --subject $subject --annotation aparc.a2009s --hemi lh --outdir $outdir --sd $fsdir
