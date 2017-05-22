import subprocess
import time
import os
import tempfile
import threading
import webrtcvad
import vlc
from collections import deque
from multiprocessing import Queue
from sys import platform

__author__ = "NJC"
__license__ = "MIT"

vad = webrtcvad.Vad(2)

# constants
VAD_SAMPLERATE = 16000
VAD_FRAME_MS = 30
VAD_PERIOD = (VAD_SAMPLERATE / 1000) * VAD_FRAME_MS
VAD_SILENCE_TIMEOUT = 1000
VAD_THROWAWAY_FRAMES = 10

class Speech(object):
    def __init__(self, mic_device="default"):
        self.mic_device = mic_device
    
    def get_stream(self):
        if platform == "linux" or platform == "linux2":
            import alsaaudio
            stream = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self.mic_device)
            stream.setchannels(1)
            stream.setrate(VAD_SAMPLERATE)
            stream.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            stream.setperiodsize(VAD_PERIOD)
        elif platform == "darwin":
            import pyaudio
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1,
                rate=VAD_SAMPLERATE, input=True,
                frames_per_buffer=VAD_PERIOD) 
        return stream 
        
    def get_data(self, stream):
        if platform == "linux" or platform == "linux2":
            return stream.read()
        elif platform == "darwin":
            data = stream.read(VAD_PERIOD)
            return (len(data)/2, data)

    def get_audio(self, player_instance, throwaway_frames=VAD_THROWAWAY_FRAMES):
        audio = ""
        
        thresholdSilenceMet = False
        frames = 0
        numSilenceRuns = 0
        silenceRun = 0
        start = time.time()
        
        stream = self.get_stream()
        player_instance.media_player.pause()

        print '* listening'
        while ((thresholdSilenceMet is False) and ((time.time() - start) < throwaway_frames)):
            length, data = self.get_data(stream)
            if data:
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
        print '* getting response'

        player_instance.media_player.play()
        
        if thresholdSilenceMet:
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
        self.player_instance = vlc.Instance('--file-logging --logfile=/dev/null')

    def setup(self, volume=50):
        self.media_player = self.player_instance.media_player_new()
        self.set_volume(volume)

    def __play(self, item):
        print 'Audio request: {}'.format(item['url'])
        player = self.player_instance.media_player_new()
        if (item['audio_type'] == 'media'):
            self.media_player = player
        
        media = self.player_instance.media_new(item['url'])
        player.set_media(media)
        player.audio_set_volume(self.volume)
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
        
        if item['audio_type'] == 'media':
            event_manager.event_detach(vlc.EventType.MediaStateChanged)

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
        self.media_player.stop()
        self.setup(self.volume)

    def pause(self):
        self.media_player.pause()

    def clear(self):
        self.queue.clear()

    def get_volume(self):
        return self.volume
    
    def set_volume(self, volume):
        self.volume = volume
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
