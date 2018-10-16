from spikeinterface import SortingExtractor
from spikeinterface.tools import read_python

import numpy as np
import os
from os.path import join
import h5py

class SpykingCircusSortingExtractor(SortingExtractor):
    def __init__(self, spykingcircus_folder):
        SortingExtractor.__init__(self)
        files = os.listdir(spykingcircus_folder)
        if np.any('merged' in files):
            results = [f for f in os.listdir(spykingcircus_folder) if f.endswith('result-merged.hdf5')][0]
        else:
            results = [f for f in os.listdir(spykingcircus_folder) if f.endswith('result.hdf5')][0]
        f_results = h5py.File(join(spykingcircus_folder, results))
        self._spiketrains = []
        self._unit_ids = []
        for temp in f_results['spiketimes'].keys():
            self._spiketrains.append(f_results['spiketimes'][temp].value)
            self._unit_ids.append(int(temp.split('_')[-1]))


    def getUnitIds(self):
        return list(self._unit_ids)

    def getUnitSpikeTrain(self, unit_id, start_frame=None, end_frame=None):
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = np.Inf
        times = self._spiketrains[self.getUnitIds().index(unit_id)]
        inds = np.where((start_frame <= times) & (times < end_frame))
        return times[inds]

    @staticmethod
    def writeSorting(sorting, save_path):
        pass