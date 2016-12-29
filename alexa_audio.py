import subprocess
import time
import os
import tempfile
import threading
import webrtcvad
import alsaaudio
import vlc
from collections import deque
from multiprocessing import Queue
from pocketsphinx import pocketsphinx


__author__ = "NJC"
__license__ = "MIT"

vad = webrtcvad.Vad(2)

# constants
VAD_SAMPLERATE = 16000
VAD_FRAME_MS = 30
VAD_PERIOD = (VAD_SAMPLERATE / 1000) * VAD_FRAME_MS
VAD_SILENCE_TIMEOUT = 1000
VAD_THROWAWAY_FRAMES = 10
MAX_RECORDING_LENGTH = 8
MAX_VOLUME = 100
MIN_VOLUME = 30

class Speech(object):
    def __init__(self, trigger_word):
        self.trigger_word = trigger_word
        self.build_decoder()

    def connect(self):

        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL)
        inp.setchannels(1)
        inp.setrate(16000)
        inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        inp.setperiodsize(1024)

        record_audio = False
        while not record_audio:
            time.sleep(.1)

            triggered = False
            while not triggered:
                _, buf = inp.read()
                self.decoder.process_raw(buf, False, False)
                triggered = self.decoder.hyp() is not None

            record_audio = True
    
        inp.close()

        self.decoder.end_utt()
        self.decoder.start_utt()

    def build_decoder(self):
        model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'files/sphinx')
        dict_file = '{}.dict'.format(self.trigger_word)
        ps_config = pocketsphinx.Decoder.default_config()
        ps_config.set_string('-hmm', os.path.join(model_path, 'acoustic-model'))
        ps_config.set_string('-dict', os.path.join(model_path, dict_file))
        ps_config.set_string('-keyphrase', self.trigger_word.upper())
        ps_config.set_float('-kws_threshold', 1e-20)
        ps_config.set_string('-logfn', '/dev/null')
        
        self.decoder = pocketsphinx.Decoder(ps_config)
        self.decoder.start_utt()

    def get_audio(self, throwaway_frames=None):
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL)
        inp.setchannels(1)
        inp.setrate(VAD_SAMPLERATE)
        inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        inp.setperiodsize(VAD_PERIOD)
        audio = ""
        
        thresholdSilenceMet = False
        frames = 0
        numSilenceRuns = 0
        silenceRun = 0
        start = time.time()

        while frames < throwaway_frames:
            length, data = inp.read()
            frames = frames + 1
            if length:
                audio += data

        while ((thresholdSilenceMet is False) and ((time.time() - start) < MAX_RECORDING_LENGTH)):
            length, data = inp.read()
            if length:
                audio += data
    
                if length == VAD_PERIOD:
                    isSpeech = vad.is_speech(data, VAD_SAMPLERATE)
    
                    if not isSpeech:
                        silenceRun = silenceRun + 1
                        # print "0"
                    else:
                        silenceRun = 0
                        numSilenceRuns = numSilenceRuns + 1
                        # print "1"

            if (numSilenceRuns != 0) and ((silenceRun * VAD_FRAME_MS) > VAD_SILENCE_TIMEOUT):
                thresholdSilenceMet = True

        inp.close()
        return audio

class Player(object):
    def __init__(self, callback_report):
        self.__callback_report = callback_report

        self.vlc_instance = None
        self.player = None
        self.media_vlc_instance = None
        self.media_player = None

        self.event_manager = None

        self.queue = None
        self.processing_queue = False

        self.stream_id = None
        self.is_playing = None

        self.volume = None

        self.blocking = False
        self.required_progress_report = []
        self.tmp_path = os.path.join(tempfile.mkdtemp(prefix='pywakealexa-runtime-'), '')
        
        self.instance = vlc.Instance('--alsa-audio-device=mono --file-logging --logfile=files/vlc-log.txt')

    def setup(self, volume=50):
        self.player = self.instance.media_player_new()
        self.media_player = self.instance.media_player_new()
        self.set_volume(volume)
        self.queue = deque()
        
        print('Volume set to {}'.format(volume))

    def _play(self, item):
        instance = self.instance
        media = instance.media_new(item['url'])
        player = self.instance.media_player_new()
        self.player = player
        media.get_mrl()
        player.set_media(media)
        self.set_volume(self.volume)

        player.set_time(item['offset'])  
        player.play()

        self.blocking = True
        while player.get_state() not in [vlc.State.Ended,vlc.State.Stopped,vlc.State.Error]:
            time.sleep(1)
        player.stop()
        self.blocking = False

    def __play(self, item):
        if item['report']: self.required_progress_report.append([item['streamId'],item['report']])

        instance = self.instance
        media = instance.media_new(item['url'])
        player = self.instance.media_player_new()
        self.media_player = player
        media.get_mrl()
        player.set_media(media)
        self.set_volume(self.volume)
        
        event_manager = media.event_manager()
        event_manager.event_attach(vlc.EventType.MediaStateChanged, self.state_callback, player, item['streamId'])

        while self.blocking: time.sleep(1)
        player.set_time(item['offset'])  
        player.play()
        while player.get_state() not in [vlc.State.Ended,vlc.State.Stopped,vlc.State.Error]:
            time.sleep(1)
        player.stop()

    def queued_play(self, url, offset=0, audio_type='media', streamId=None, report={}):
        item = {
            'url': url,
            'offset': offset,
            'audio_type': audio_type,
            'streamId': streamId,
            'report': report
        }

        self.queue.append(item)
        if not self.processing_queue:
            pqReady = threading.Event()
            pqThread = threading.Thread(target=self.process_queue, kwargs={'reportReady': pqReady})
            pqThread.start()
    
            pqReady.wait()

    def blocking_play(self, url, offset=0, audio_type='speech', streamId=None):
        item = {
            'url': url,
            'offset': offset,
            'audio_type': audio_type,
            'streamId': streamId
        }

        self._play(item)

    def process_queue(self, reportReady=None):
        self.processing_queue = True
        if reportReady:
            reportReady.set()

        while len(self.queue):
            item = self.queue.popleft()
            self.__play(item)

            if len(self.queue) > 0:
                time.sleep(0.5)
        self.processing_queue = False

    def stop(self):
        self.player.stop()
        self.media_player.stop()
        self.blocking = False
        self.processing_queue = False

    def clear(self):
        self.queue.clear()

    def get_volume(self):
        return self.volume
    
    def set_volume(self, volume):
        self.volume = volume
        self.player.audio_set_volume(volume)
        self.media_player.audio_set_volume(volume)
        
    def __interval_progress_report(self, player, streamId, offset):
        while player.get_state() != vlc.State.Ended:
            time.sleep(offset/1000)
            self.__callback_report('PROGRESS_REPORT_INTERVAL', "PLAYING", streamId)
        self.__callback_report('PROGRESS_REPORT_INTERVAL', "IDLE", streamId)

    def state_callback(self, event, player, streamId): # pylint: disable=unused-argument
        state = player.get_state()
        playerActivity = "IDLE" if state in [vlc.State.Stopped, vlc.State.Ended, vlc.State.Error] else "PLAYING"

        if state in [vlc.State.Playing, vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:
            report = {
                vlc.State.Playing: "STARTED",
                vlc.State.Stopped: "STOPPED",
                vlc.State.Ended:  "FINISHED",
                vlc.State.Error: "ERROR",
            }
            rThread = threading.Thread(target=self.__callback_report, args=(report[state], playerActivity, streamId))
            rThread.start()

        if len(self.required_progress_report):
            check = [[i,report] for i,report in enumerate(self.required_progress_report) if report[0] == streamId]
            if check:
                _id = check[0][0]
                report = check[0][1][1]
                self.required_progress_report.pop(_id)
                _type = report['type']
                report_offset = report['offset']
                if _type == 'delay':
                    time.sleep(report['offset']/1000)
                    self.__callback_report('PROGRESS_REPORT_DELAY', playerActivity, streamId)
                    
                if _type == 'interval':
                    
                    iThread = threading.Thread(target=self.__interval_progress_report, args=(player,streamId,report_offset))
                    iThread.start()
