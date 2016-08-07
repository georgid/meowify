'''
Created on Aug 6, 2016

@author: joro
'''
import numpy
import os
import subprocess
import sys

import essentia.standard
import mir_eval

mix_factor_cats = 0.5
sampleRate = 44100.
frameSize = 512.

from essentia.standard import *
from essentia import Pool, array

parentDir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__) ), os.path.pardir)) 

pathEvaluation = os.path.join(parentDir, 'vocal-detection')
if pathEvaluation not in sys.path:
    sys.path.append(pathEvaluation)

sys.path.append(pathEvaluation)
from vocal import getTimeStamps



def get_mean_onsets(onsets_ts, audio_samples, cat_audio_samples, cat_pitch):
    
    audio_catbuss = [0.] * len(audio_samples)
 
    for ts_onset in onsets_ts:
        o = ts_onset[0]
        o_samples = long(o * sampleRate)
        o_frame = long(o_samples / frameSize)  
        o_pitch = ts_onset[2]
        
        ######## take average pitch from onset for pitch_window_size frames
       
     
        while True:
            if o_pitch > 1000: o_pitch /= 2
            else: break
        print "pitch_goal=", o_pitch
        
        # resample cat pithc  
        o_resample = 44100. * cat_pitch / o_pitch
     
        cat_audio_resampled = Resample(outputSampleRate=o_resample)(cat_audio_samples)
        
        
        #### go through cat samples
        for i in range(len(cat_audio_resampled)):
            if o_samples+i >= len(audio_samples): break
            audio_catbuss[o_samples+i] += cat_audio_resampled[i]
    return audio_catbuss


def extractPitch(audioFileURI, audio_samples,frame_size, hop_size ):
    from essentia.standard import PredominantPitchMelodia

    pitchTracker = PredominantPitchMelodia(frameSize = frame_size, hopSize = hop_size,  voicingTolerance = 1.4)

    pitch, pitchConf = pitchTracker(audio_samples)
    timestamps = getTimeStamps(audio_samples, pitch)

    est_freq_and_ts = zip(timestamps, pitch)

    # write to csv
    outFileURI = os.path.splitext(audioFileURI)[0] + '.csv'
    writeCsv(outFileURI, est_freq_and_ts)
    
    return pitch




def writeCsv(fileURI, list_, withListOfRows=1):
    from csv import writer
    fout = open(fileURI, 'wb')
    w = writer(fout)
    print 'writing to csv file {}...'.format(fileURI)
    for row in list_:
        if withListOfRows:
            w.writerow(row)
        else:
            tuple_note = [row.onsetTime, row.noteDuration]
            w.writerow(tuple_note)
    
    fout.close()
    


def get_cat_audio_pitch():
    
    spectrum = Spectrum()
    pitch = PitchYinFFT(frameSize=1024)
 
    pool = Pool()
    windowing = Windowing(type = 'hann')


    cat_audio = MonoLoader(filename='cat-01.wav', sampleRate=44100)()
    cat_audio_loudness = Loudness()(cat_audio)
 
    for frame in FrameGenerator(cat_audio, frameSize=1024, hopSize=512):
        spec = spectrum(windowing(frame))
        p, conf = pitch(spec)
        pool.add('cat_pitch', p)
 
 
    cat_pitch = numpy.mean(pool['cat_pitch'])
    cat_MIDI = mir_eval.multipitch.frequencies_to_midi([cat_pitch]) 
    return cat_audio, cat_MIDI[0]


def extractNoteOnsets(audioFileURI):
        '''
        with cante. 
        extract note onsets for whole audio
        '''
        import cante
        cante.transcribe(audioFileURI, acc=True, f0_file=True, recursive=False)
        


if __name__ == '__main__':
    audioFileURI = '/Users/joro/Documents/Phd/UPF/Python_AudioMusicProcessing/sms-tools-master/sounds/singing-female.wav'
    
    audioFileURI = 'Better_Together.wav'
#     audioFileURI = '/Users/joro/Downloads/audio_with_vocal.wav'
    audioFileURI = '/Users/joro/Downloads/yesterday.wav'
    mono_loader = essentia.standard.MonoLoader(filename = audioFileURI, sampleRate = 44100)
    audio_samples = mono_loader()
    
    audioFileURI_karaoke =  audioFileURI[:-4] +  '_karaoke.wav'
    mono_loader_karaoke = essentia.standard.MonoLoader(filename = audioFileURI_karaoke, sampleRate = 44100)
    audio_samples_karaoke = mono_loader_karaoke()
    
#     extractPitch(audioFileURI, audio_samples,frame_size=1024, hop_size=128 )
#     extractNoteOnsets(audioFileURI)

    onsets_URI = audioFileURI[:-4] + '.notes.csv'
    # read from URI
    
    from csv import reader
    onsets_ts = [] 
    with open(onsets_URI) as f:
            r = reader(f)
            for row in r:
                currTs = float( "{0:.2f}".format(float(row[0].strip())) )
                currDur = float( "{0:.2f}".format(float(row[1].strip())) )
                currMIDI = int(row[2].strip())
                onsets_ts.append((currTs, currDur, currMIDI))
    
    cat_audio_samples, cat_pitch = get_cat_audio_pitch()
    
    audio_catbuss = get_mean_onsets(onsets_ts, audio_samples, cat_audio_samples, cat_pitch)
    
    #### write
    for i in range(len(audio_samples_karaoke)):
        audio_samples_karaoke[i] += mix_factor_cats * audio_catbuss[i]
    
    output = audioFileURI[:-4] + '_cats.wav'
    MonoWriter(filename=output)(audio_samples_karaoke)
    