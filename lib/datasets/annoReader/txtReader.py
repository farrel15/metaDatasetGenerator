
# --------------------------------------------------------
# CBAL
# Written by Kent Gauen
# --------------------------------------------------------

import os,re
import os.path as osp
import PIL
import numpy as np
import scipy.sparse
from core.config import cfg
from easydict import EasyDict as edict
import xml.etree.ElementTree as ET


class txtReader(object):
    """Image database."""

    def __init__(self, annoPath, classes , datasetName, bboxOffset = 0,
                 useDiff = True, cleanRegex = None, convertToPerson = False,
                 onlyPerson = False):
        """
        __init__ function for annoReader [annotationReader]

        """
        self._annoPath = annoPath
        self._bboxOffset = bboxOffset
        self._datasetName = datasetName
        self.num_classes = len(classes)
        self.useDiff = useDiff
        self._classToIndex = self._create_classToIndex(classes)
        self._convertToPerson = convertToPerson
        self._onlyPerson = onlyPerson
        if cleanRegex is not None: self._cleanRegex = cleanRegex # used for INRIA
        else:
            self._cleanRegex = r"(?P<cls>[0-9]+) (?P<xmin>[0-9]*\.[0-9]+) (?P<ymin>[0-9]*\.[0-9]+) (?P<xmax>[0-9]*\.[0-9]+) (?P<ymax>[0-9]*\.[0-9]+)"
        
    def _create_classToIndex(self,classes):
        return dict(zip(classes, range(self.num_classes)))
        
    def load_annotation(self,index):
        """
        load annotations depending on how the annotation should be loaded

        """
        return self._load_txt_annotation(index)

    def _load_txt_annotation(self, index):
        """
        requires the following format @ 
        <PATH_TO_ANNOTATIONS>/*txt
        """

        filename = os.path.join(self._annoPath, index + '.txt')
        annos = []
        with open(filename,"r") as f:
            annos = f.readlines()

        num_objs = 0 
        if self._cleanRegex is not None:
            for idx,line in enumerate(annos):
                m = re.match(self._cleanRegex,line)
                if m is not None:
                    num_objs += 1
        else:
            num_objs = len(annos)
                    

        

        # reformat into the dictionary
        boxes = np.zeros((num_objs, 4), dtype=np.int16)
        gt_classes = np.zeros((num_objs), dtype=np.int32)
        overlaps = np.zeros((num_objs, self.num_classes), dtype=np.float32)
        # "Seg" area for pascal is just the box area
        seg_areas = np.zeros((num_objs), dtype=np.float32)
        ix = 0

        for line in annos:
            m = re.match(self._cleanRegex,line)
            if m is not None:
                mgd = m.groupdict()
                x1 = float(mgd['xmin'])
                y1 = float(mgd['ymin'])
                x2 = float(mgd['xmax'])
                y2 = float(mgd['ymax'])

                if "cls" in mgd.keys():
                    cls = mgd['cls']
                    if re.match(r"[0-9]+",cls) is None:
                        cls = self._classToIndex[cls]
                    else:
                        cls = int(cls)
                else:
                    cls = self._classToIndex["person"]
                
                # check if we need to convert annotation class to "person"
                if self._convertToPerson is not None:
                    if cls in self._convertToPerson:
                        cls = self._classToIndex["person"]
                
                if self._onlyPerson is True and\
                   cls is not "person": continue

                boxes[ix, :] = [x1, y1, x2, y2]
                gt_classes[ix] = cls
                overlaps[ix, cls] = 1.0
                seg_areas[ix] = (x2 - x1 + 1) * (y2 - y1 + 1)
                ix += 1

        overlaps = scipy.sparse.csr_matrix(overlaps)

        if cfg.OBJ_DET.BBOX_VERBOSE:
            bbox = {'boxes' : boxes,
                    'gt_classes': gt_classes,
                    'gt_overlaps' : overlaps,
                    'flipped' : False,
                    'seg_areas' : seg_areas,
                    'set':1}
        else:
            bbox = {'boxes' : boxes,
                    'gt_classes': gt_classes,
                    'flipped': False,
                    'set':1}
        return bbox

