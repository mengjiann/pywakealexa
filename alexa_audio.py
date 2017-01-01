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
    def __init__(self, mic_device="default"):
        self.build_decoder()
        self.mic_device = mic_device

    def connect(self):
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self.mic_device)
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
        file_name = 'alexa'
        dict_file = '{}.dict'.format(file_name)
        lm_file = '{}.lm'.format(file_name)
        ps_config = pocketsphinx.Decoder.default_config()
        ps_config.set_string('-hmm', os.path.join(model_path, 'acoustic-model'))
        ps_config.set_string('-dict', os.path.join(model_path, dict_file))
        ps_config.set_string('-keyphrase', "JARVIS")
        ps_config.set_float('-kws_threshold', 1e-10)
        ps_config.set_string('-logfn', '/dev/null')
        
        self.decoder = pocketsphinx.Decoder(ps_config)
        self.decoder.start_utt()

    def get_audio(self, player_instance, throwaway_frames=None):
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self.mic_device)
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
        player_instance.media_player.pause()
        # if throwaway_frames is None: throwaway_frames = VAD_THROWAWAY_FRAMES
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
        player_instance.media_player.play()
        return audio

class Player(object):
    def __init__(self, callback_report, speaker_device=""):
        self.__callback_report = callback_report
        self.speaker_device = speaker_device

        self.player_instance = None
        self.media_player_instance = None
        self.player = None
        self.media_player = None
        self.paused = False

        self.event_manager = None

        self.queue = None
        self.processing_queue = False

        self.stream_id = None
        self.playerActivity = "IDLE"

        self.volume = None

        self.blocking = False
        self.required_progress_report = []
        
        self.queue = deque()
        
        self.current_item_lock = threading.Event()
        self.play_lock = threading.Event()
        self.play_lock.set()

        self.tmp_path = os.path.join(tempfile.mkdtemp(prefix='pywakealexa-runtime-'), '')
        self.player_instance = vlc.Instance('--alsa-audio-device={} --file-logging --logfile=/dev/null'.format(self.speaker_device))

    def setup(self, volume=50):
        instance = self.player_instance
        self.player = instance.media_player_new()
        self.media_player = instance.media_player_new()
        self.set_volume(volume)
        
        print('Volume set to {}'.format(volume))

    def __play(self, item):
        print 'Audio request: {}'.format(item['url'])
        if (item['audio_type'] == 'media'):
            instance = self.player_instance
            player = instance.media_player_new()
            self.media_player = player
        else:
            instance = self.player_instance
            player = self.player_instance.media_player_new()
            self.player = player
        
        media = instance.media_new(item['url'])
        media.get_mrl()
        player.set_media(media)
        if item['audio_type'] == 'media':
            if item['report']: self.required_progress_report.append([item['streamId'],item['report']])
            event_manager = media.event_manager()
            event_manager.event_attach(vlc.EventType.MediaStateChanged, self.state_callback, player, item['streamId'])
        player.set_time(item['offset'])
        if (item['audio_type'] == 'speech'):
            self.media_player.pause()
        player.play()
        while player.get_state() not in [vlc.State.Ended,vlc.State.Stopped,vlc.State.Error]:
            time.sleep(1)
        player.stop()
        if (item['audio_type'] == 'speech'):
            self.media_player.play()

    def queued_play(self, url, offset=0, audio_type='media', streamId=None, report={}, behavior=None):
        if type(url) == list: url = url[0]
        item = {
            'url': url,
            'offset': offset,
            'audio_type': audio_type,
            'streamId': streamId,
            'report': report,
            'trigger': False
        }

        if str(behavior) == 'REPLACE_ALL':
            self.stop()
        if str(behavior) == 'REPLACE_ENQUEUED':
            self.clear()
        if str(behavior) == 'ENQUEUE':
            while self.playerActivity == "PLAYING":
                time.sleep(1)

        self.queue.append(item)

        pqReady = threading.Event()
        pqThread = threading.Thread(target=self.process_queue, kwargs={'reportReady': pqReady})
        pqThread.start()

        pqReady.wait()

    def blocking_play(self, url, offset=0, audio_type='speech', streamId=None, trigger=False, behavior=None):
        item = {
            'url': url,
            'offset': offset,
            'audio_type': audio_type,
            'streamId': streamId,
            'trigger': trigger
        }
        
        if str(behavior) == 'REPLACE_ALL':
            self.stop()
        if str(behavior) == 'REPLACE_ENQUEUED':
            self.clear()
        if str(behavior) == 'ENQUEUE':
            while self.playerActivity == "PLAYING":
                time.sleep(1)

        self.__play(item)

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
        self.setup(self.volume)

    def pause(self):
        self.player.pause()
        self.media_player.pause()

    def clear(self):
        self.queue.clear()

    def get_volume(self):
        return self.volume
    
    def set_volume(self, volume):
        self.volume = volume
        self.player.audio_set_volume(volume)
        self.media_player.audio_set_volume(volume)
        
    def __interval_progress_report(self, player, streamId, offset):
        while player.get_state() not in [vlc.State.Ended,vlc.State.Stopped,vlc.State.Error]:
            time.sleep(int(offset/1000))
            self.__callback_report('PROGRESS_REPORT_INTERVAL', self.playerActivity, streamId)
        self.__callback_report('PROGRESS_REPORT_INTERVAL', self.playerActivity, streamId)
        
    def __delay_progress_report(self, player, streamId, offset):
        time.sleep(int(offset/1000))
        self.__callback_report('PROGRESS_REPORT_DELAY', self.playerActivity, streamId)

    def state_callback(self, event, player, streamId): # pylint: disable=unused-argument
        state = player.get_state()
        self.playerActivity = "IDLE" if state in [vlc.State.Stopped, vlc.State.Ended, vlc.State.Error] else "PLAYING"

        if state in [vlc.State.Playing, vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:
            report = {
                vlc.State.Playing: "STARTED",
                vlc.State.Stopped: "STOPPED",
                vlc.State.Paused: "PAUSED",
                vlc.State.Ended:  "FINISHED",
                vlc.State.Error: "ERROR",
            }
            rThread = threading.Thread(target=self.__callback_report, args=(report[state], self.playerActivity, streamId))
            rThread.start()
        if state in [vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:
            self.media_player = self.player_instance.media_player_new()
        
        if len(self.required_progress_report):
            check = [[i,report] for i,report in enumerate(self.required_progress_report) if report[0] == streamId]
            if check:
                _id = check[0][0]
                report = check[0][1][1]
                self.required_progress_report.pop(_id)
                _type = report['type']
                report_offset = report['offset']
                if _type == 'delay':
                    iThread = threading.Thread(target=self.__delay_progress_report, args=(player,streamId,report_offset))
                    iThread.start()
                    
                if _type == 'interval':
                    iThread = threading.Thread(target=self.__interval_progress_report, args=(player,streamId,report_offset))
                    iThread.start()
