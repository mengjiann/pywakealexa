
import helper
import time
import threading
import traceback
import tunein

import requests
import json
import alexa_audio
import alexa_communication

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"


class AlexaDevice:
    """ This object is the AlexaDevice. It uses the AlexaCommunication and AlexaAudio object. The goal is to provide a
        highly abstract yet simple interface for Amazon's Alexa Voice Service (AVS).

    """
    def __init__(self, alexa_config):
        """ Initialize the AlexaDevice using the config dictionary. The config dictionary must containing the
            Client_ID, Client_Secret, and refresh_token.

        :param alexa_config: config dictionary specific to the device
        """
        self.config = alexa_config
        self.alexa = None
        self.muted = False
        self.previous_volume = 0
        self.player_instance = None
        self.tunein_parser = tunein.TuneIn(5000)
        self.player_activity = {"playerActivity": "IDLE", "streamId": ""}

        self.device_stop_event = threading.Event()
        self.device_thread = threading.Thread(target=self.device_thread_function)
        self.device_thread.start()

    def set_player_instance(self, playback_progress_report_request, speaker_device):
        self.player_instance = alexa_audio.Player(playback_progress_report_request, speaker_device)
        return self.player_instance

    def set_speech_instance(self, mic_device):
        self.speech_instance = alexa_audio.Speech(mic_device)
        return self.speech_instance

    def device_thread_function(self):
        # Start connection and save
        self.alexa = alexa_communication.AlexaConnection(self.config, context_handle=self.get_context,
                                                         process_response_handle=self.process_response)

        # Connection loop
        while not self.device_stop_event.is_set():
            # Do any device related things here
            time.sleep(0.1)
            pass

        # When complete (stop event is same as user_input_thread
        # Close the alexa connection and set stop event
        self.alexa.close()
        self.device_stop_event.set()
        print("Closing Thread")
        # TODO If anything went wrong, and stop event is not set, start new thread automatically

    def user_initiate_audio(self):
        self.player_instance.blocking_play("files/alexayes.mp3")
        raw_audio = self.speech_instance.get_audio(self.player_instance)
        if raw_audio is None:
            return

        stream_id = self.alexa.start_recognize_event(raw_audio)
        self.alexa.get_and_process_response(stream_id)

    def get_context(self):
        if self.player_instance:
            context_audio = {
                "header": {
                    "namespace": "AudioPlayer",
                    "name": "playbackState"
                },
                "payload": {
                    "streamId": self.player_activity['streamId'],
                    "offsetInMilliseconds": "0",
                    "playerActivity": self.player_activity['playerActivity']
                }
            }
            context_speaker = {
                "header": {
                    "namespace": "Speaker",
                    "name": "VolumeState"
                },
                "payload": {
                    "volume": self.player_instance.get_volume(),
                    "muted": True if self.player_instance.get_volume() == 0 else False
                }
            }
            return [context_audio, context_speaker]

    def process_response(self, message):
        for i, content in enumerate(message['content']):
            content = message['content'][i]
            try:
                attachment = message['attachment'][i]
            except IndexError:
                attachment = None

            header = content['directive']['header']
            # Get the namespace from the header and call the correct process directive function
            namespace = header['namespace']
            if namespace == 'SpeechSynthesizer':
                self.process_directive_speech_synthesizer(content, attachment)
            elif namespace == 'SpeechRecognizer':
                self.process_directive_speech_recognizer(content, attachment)
            elif namespace == 'Alerts':
                self.process_directive_alerts(content, attachment)
            elif namespace == 'AudioPlayer':
                self.process_directive_audio_player(content, attachment)
            elif namespace == 'Speaker':
                self.process_directive_speaker(content, attachment)
            else:
                print "Namespace not recognized (%s)." % namespace

    def process_directive_speaker(self, content, attachment):
        header = content['directive']['header']
        payload = content['directive']['payload']

        name = header['name']
        request_id = False
        if 'dialogRequestId' in header: request_id = 'dialogRequestId'
        volume = self.player_instance.get_volume()
        if not self.previous_volume or volume > 0:
            self.previous_volume = volume
        if name in ['SetVolume', 'AdjustVolume']:
            adjust_volume = payload['volume']
            print 'Player State: Volume adjust {}'.format(adjust_volume)
            volume = self.player_instance.get_volume() + adjust_volume
            self.player_instance.set_volume(volume)
        elif name in ['Mute', 'SetMute']:
            if payload['mute']:
                if not self.muted:
                    self.muted = True
                    volume = 0
                    print 'Player State: Mute'
                    self.player_instance.set_volume(volume)
                else:
                    self.muted = False
                    self.player_instance.set_volume(self.previous_volume)
            else:
                self.player_instance.set_volume(self.previous_volume)
        else:
            print "Name not recognized (%s)." % name

        self.alexa.send_event_volume_changed(volume)

    def process_directive_audio_player(self, content, attachment):
        header = content['directive']['header']
        payload = content['directive']['payload']

        report = False
        name = header['name']
        if name == 'ClearQueue':
            if payload['clearBehavior'] == 'CLEAR_ALL':
                self.player_instance.stop()
            self.player_instance.clear()
            stream_id = self.alexa.send_event_queue_cleared()
            self.alexa.get_and_process_response(stream_id)
        elif name == 'Play':
            audio_id = payload['audioItem']['audioItemId']
            offset = payload['audioItem']['stream']['offsetInMilliseconds']
            behavior = payload['playBehavior']
            if 'progressReport' in payload['audioItem']['stream']:
                r = payload['audioItem']['stream']['progressReport']
                if 'progressReportDelayInMilliseconds' in payload['audioItem']['stream']['progressReport']:
                    report = {'type': 'delay', 'offset': r['progressReportDelayInMilliseconds']}
                elif 'progressReportIntervalInMilliseconds' in payload['audioItem']['stream']['progressReport']:
                    report = {'type': 'interval', 'offset': r['progressReportIntervalInMilliseconds']-offset}
            if attachment is None:
                audio_url = payload['audioItem']['stream']['url']
                if audio_url.startswith("cid:"):
                    audio_url = "file://" + tmp_path + audio_url.lstrip("cid:") + ".mp3"
                if audio_url.find('radiotime.com') != -1:
                    audio_url = self.tunein_playlist(audio_url)
                self.player_instance.queued_play(audio_url, streamId=audio_id, offset=offset, report=report, behavior=behavior)
            else:
                audio_response = attachment
                audio_file = self.player_instance.tmp_path + "audio.mp3"
                with open(audio_file, 'wb') as f:
                    f.write(audio_response)
                print audio_file
                self.player_instance.blocking_play(audio_file, streamId=audio_id, offset=offset, behavior=behavior)
        elif name == 'Stop':
            self.player_instance.stop()
        else:
            print "Name not recognized (%s)." % name

    def tunein_playlist(self, url):
        req = requests.get(url)
        lines = req.content.split('\n')

        nurl = self.tunein_parser.parse_stream_url(lines[0])
        if (len(nurl) != 0):
            return nurl[0]

        return ""

    def process_directive_speech_synthesizer(self, content, attachment):
        header = content['directive']['header']
        payload = content['directive']['payload']

        name = header['name']
        if name == 'Speak':
            token = payload['token']
            if attachment:
                audio_response = attachment
                audio_file = self.player_instance.tmp_path + "response.mp3"
                with open(audio_file, 'wb') as f:
                    f.write(audio_response)
                stream_id = self.alexa.send_event_speech_started(token)
                self.alexa.get_and_process_response(stream_id)
                self.player_instance.blocking_play(audio_file, streamId=token, trigger=True)
                stream_id = self.alexa.send_event_speech_finished(token)
                self.alexa.get_and_process_response(stream_id)
        else:
            print "Name not recognized (%s)." % name

    def process_directive_speech_recognizer(self, content, attachment):
        header = content['directive']['header']
        payload = content['directive']['payload']

        name = header['name']
        if name == 'ExpectSpeech':
            dialog_request_id = header['dialogRequestId']
            timeout = payload['timeoutInMilliseconds']/1000

            file = "files/beep.wav"
            self.player_instance.blocking_play(file, streamId=dialog_request_id)
            raw_audio = self.speech_instance.get_audio(self.player_instance, throwaway_frames=timeout)
            if raw_audio is None:
                print("Speech timeout.")
                stream_id = self.alexa.send_event_expect_speech_timed_out()
                self.alexa.get_and_process_response(stream_id)
                return
            stream_id = self.alexa.start_recognize_event(raw_audio, dialog_request_id=dialog_request_id)
            self.alexa.get_and_process_response(stream_id)
        elif name == 'StopCapture':
            pass
        else:
            print "Name not recognized (%s)." % name

    def send_event_playback_finished(self, streamId):
        header = {"namespace": "AudioPlayer",
            "name": 'PlaybackNearlyFinished',
        }
        stream_id = self.alexa.send_event_audio(header, streamId)
        self.alexa.get_and_process_response(stream_id)

    def playback_progress_report_request(self, requestType, playerActivity, streamId):
        reports = []
        if requestType.upper() == "FINISHED":
            reports = ["PlaybackNearlyFinished", "PlaybackFinished"]
        elif requestType.upper() == "STOPPED":
            reports = ["PlaybackStopped"]
        elif requestType.upper() == "PAUSED":
            reports = ["PlaybackPaused"]
        elif requestType.upper() == "ERROR":
            reports = ["PlaybackFailed"]
            #stream_id = self.alexa.send_event_playback_failed(streamId)
            #return self.alexa.get_and_process_response(stream_id)
        elif requestType.upper() == "STARTED":
            reports = ["PlaybackStarted"]
        elif requestType.upper() == "PROGRESS_REPORT_DELAY":
            reports = ["ProgressReportDelayElapsed"]

        if reports and streamId:
            self.player_activity = {'playerActivity': playerActivity, 'streamId': streamId}
            for report in reports:
                header = {"namespace": "AudioPlayer",
                    "name": report,
                }
                stream_id = self.alexa.send_event_audio(header, streamId)
                self.alexa.get_and_process_response(stream_id)

    def close(self):
        self.device_stop_event.set()
        self.player_instance.stop()

    def wait_until_close(self):
        self.device_thread.join()
