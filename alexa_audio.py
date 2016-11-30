
import vlc
import subprocess
import speech_recognition
import time

__author__ = "NJC"
__license__ = "MIT"


class AlexaAudio:
    """ This object handles all audio playback and recording required by the Alexa enabled device. Audio playback
        and recording both use the PyAudio package.

    """
    def __init__(self):
        """ AlexaAudio initialization function.
        """

        self.audio_playing = False

    def close(self):
        """ Called when the AlexaAudio object is no longer needed. This closes the PyAudio instance.
        """
        # Terminate the pyaudio instance
        self.instance.close()

    def get_audio(self, timeout=None):
        """ Get audio from the microphone. The SpeechRecognition package is used to automatically stop listening
            when the user stops speaking. A timeout can also be specified. If the timeout is reached, the function
            returns None.

            This function can also be used for debugging purposes to read an example audio file.

        :param timeout: timeout in seconds, when to give up if the user did not speak.
        :return: the raw binary audio string (PCM)
        """
        # Create a speech recognizer
        r = speech_recognition.Recognizer()
        r.energy_threshold = 4000
        with speech_recognition.Microphone() as source:
            r.adjust_for_ambient_noise(source)
            if timeout is None:
                self.play_audio('files/alexayes.mp3')
                audio = r.listen(source)
            else:
                try:
                    self.play_audio('files/dong.wav')
                    audio = r.listen(source, timeout=timeout)
                except speech_recognition.WaitTimeoutError:
                    return None
        # Convert audio to raw_data (PCM)
        raw_audio = audio.get_raw_data()

        # Rather than recording, read a pre-recorded example (for testing)
        # with open('files/example_get_time.pcm', 'rb') as f:
        #     raw_audio = f.read()
        return raw_audio

    def play_audio(self, file=None, raw_audio=None):
        """ Play an MP3 file. Alexa uses the MP3 format for all audio responses. PyAudio does not support this, so
            the MP3 file must first be converted to a wave file before playing.

            This function assumes ffmpeg is located in the current working directory (ffmpeg/bin/ffmpeg).

        :param raw_audio: the raw audio as a binary string
        """

        while self.audio_playing:
            time.sleep(1)

        if raw_audio:
            file = "files/response.mp3"
            with open(file, 'wb') as f:
                f.write(raw_audio)

        vlc_inst = vlc.Instance()
        media = vlc_inst.media_new(file)
        self.player = vlc_inst.media_player_new()
        self.player.set_media(media)
        mm = media.event_manager()
        mm.event_attach(vlc.EventType.MediaStateChanged, self.state_callback, self.player)
        self.player.play()

    def state_callback(self, event, media_player):
        state = media_player.get_state()
        if state == 3:      # Playing
            self.audio_playing = True
            print('PLAYING')
        elif state == 5:  # Stopped
            self.audio_playing = False
            print('STOPPED')
        elif state == 6:  # Ended
            self.audio_playing = False
            print('ENDED')
        elif state == 7:
            self.audio_playing = False
            print('ERROR')
