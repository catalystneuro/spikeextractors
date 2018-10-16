from spikeinterface import RecordingExtractor
from spikeinterface import SortingExtractor

from mountainlab_pytools import mlproc as mlp
from mountainlab_pytools import mdaio
import os, json
import numpy as np

class MdaRecordingExtractor(RecordingExtractor):
    def __init__(self, dataset_directory, *, download=True):
        RecordingExtractor.__init__(self)
        self._dataset_directory=dataset_directory
        timeseries0=dataset_directory+'/raw.mda'
        self._dataset_params=read_dataset_params(dataset_directory)
        self._samplerate=self._dataset_params['samplerate']*1.0
        if is_kbucket_url(timeseries0):
            download_needed=is_url(mlp.locateFile(timeseries0))
        else:
            download_needed=is_url(timeseries0)
        if download and download_needed:
            print('Downloading file: '+timeseries0)
            self._timeseries_path=mlp.realizeFile(timeseries0)
            print('Done.')
        else:
            self._timeseries_path=mlp.locateFile(timeseries0)
        geom0=dataset_directory+'/geom.csv'
        self._geom_fname=mlp.realizeFile(geom0)
        self._geom=np.genfromtxt(self._geom_fname, delimiter=',')
        X=mdaio.DiskReadMda(self._timeseries_path)
        if self._geom.shape[0] != X.N1():
            raise Exception('Incompatible dimensions between geom.csv and timeseries file {} <> {}'.format(self._geom.shape[0],X.N1()))
        self._num_channels=X.N1()
        self._num_timepoints=X.N2()
        for m in range(self._num_channels):
            self.setChannelProperty(m,'location',self._geom[m,:])

    def getNumChannels(self):
        return self._num_channels

    def getNumFrames(self):
        return self._num_timepoints

    def getSamplingFrequency(self):
        return self._samplerate

    def getTraces(self, start_frame=None, end_frame=None, channel_ids=None):
        if start_frame is None:
            start_frame=0
        if end_frame is None:
            end_frame=self.getNumFrames()
        if channel_ids is None:
            channel_ids=range(self.getNumChannels())
        X=mdaio.DiskReadMda(self._timeseries_path)
        recordings=X.readChunk(i1=0,i2=start_frame,N1=X.N1(),N2=end_frame-start_frame)
        recordings=recordings[channel_ids,:]
        return recordings

    @staticmethod
    def writeRecording(recording,save_path):
        M=recording.getNumChannels()
        N=recording.getNumFrames()
        channel_ids=range(M)
        raw=recording.getTraces()
        location0=recording.getChannelProperty(0,'location')
        nd=len(location0)
        geom=np.zeros((M,nd))
        for ii in range(len(channel_ids)):
            location_ii=recording.getChannelProperty(channel_ids[ii],'location')
            geom[ii,:]=list(location_ii)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        mdaio.writemda32(raw,save_path+'/raw.mda')
        params=dict(
            samplerate=recording.getSamplingFrequency(),
            spike_sign=-1
        )
        with open(save_path+'/params.json','w') as f:
            json.dump(params,f)
        np.savetxt(save_path+'/geom.csv', geom, delimiter=',')

class MdaSortingExtractor(SortingExtractor):
    def __init__(self, firings_file):
        SortingExtractor.__init__(self)
        if is_kbucket_url(firings_file):
            download_needed=is_url(mlp.locateFile(firings_file))
        else:
            download_needed=is_url(firings_file)
        if download_needed:
            print('Downloading file: '+firings_file)
            self._firings_path=mlp.realizeFile(firings_file)
            print('Done.')
        else:
            self._firings_path=mlp.realizeFile(firings_file)
        self._firings=mdaio.readmda(self._firings_path)
        self._times=self._firings[1,:]
        self._labels=self._firings[2,:]
        self._unit_ids=np.unique(self._labels).astype(int)

    def getUnitIds(self):
        return self._unit_ids

    def getUnitSpikeTrain(self, unit_id, start_frame=None, end_frame=None):
        if start_frame is None:
            start_frame=0
        if end_frame is None:
            end_frame=np.Inf
        inds=np.where((self._labels==unit_id)&(start_frame<=self._times)&(self._times<end_frame))
        return np.rint(self._times[inds]).astype(int)

    @staticmethod
    def writeSorting(sorting,save_path):
        unit_ids=sorting.getUnitIds()
        K=np.max(unit_ids)
        times_list=[]
        labels_list=[]
        for i in range(len(unit_ids)):
            unit=unit_ids[i]
            times=sorting.getUnitSpikeTrain(unit_id=unit)
            times_list.append(times)
            labels_list.append(np.ones(times.shape)*unit)
        all_times=np.concatenate(times_list)
        all_labels=np.concatenate(labels_list)
        sort_inds=np.argsort(all_times)
        all_times=all_times[sort_inds]
        all_labels=all_labels[sort_inds]
        L=len(all_times)
        firings=np.zeros((3,L))
        firings[1,:]=all_times
        firings[2,:]=all_labels
        mdaio.writemda64(firings,save_path)

def is_kbucket_url(path):
    return path.startswith('kbucket://') or path.startswith('sha1://')

def is_url(path):
    return path.startswith('http://') or path.startswith('https://') or path.startswith('kbucket://') or path.startswith('sha1://')

def read_dataset_params(dsdir):
    params_fname=mlp.realizeFile(dsdir+'/params.json')
    if not os.path.exists(params_fname):
        raise Exception('Dataset parameter file does not exist: '+params_fname)
    with open(params_fname) as f:
        return json.load(f)
