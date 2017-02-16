import helper
import authorization
import alexa_device
import sys
import signal
import time

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"

def work(config):
    volume = 60
    wake_word = True
    
    # defualt if pulseaudio otherwise plughw:[CARDID]
    mic_device = 'default'
    speaker_device = 'plughw:1'

    alexa = alexa_device.AlexaDevice(config)
    speech = alexa.set_speech_instance(mic_device)
    player = alexa.set_player_instance(alexa.playback_progress_report_request, speaker_device)
    player.setup(volume)
    player.blocking_play('files/hello.mp3')

    while 1:
        try:
            if not wake_word:
                text = raw_input("Press enter anytime to start recording (or 'q' to quit).")
                if text == 'q':
                    alexa.close()
                    sys.exit()
                    break
            else:
                speech.connect()
        except (KeyboardInterrupt, EOFError, SystemExit):
            alexa.close()
            sys.exit()
            break
        alexa.user_initiate_audio()

if __name__ == "__main__":
    config = helper.read_dict('config.dict')
    if 'refresh_token' not in config:
        print("Please go to http://localhost:5000")
        authorization.get_authorization()
        config = helper.read_dict('config.dict')

    work(config)
