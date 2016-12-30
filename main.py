import helper
import authorization
import alexa_device
import alexa_audio
import sys
import time

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"


def work(config):
    volume = 50

    alexa = alexa_device.AlexaDevice(config)
    speech = alexa.set_speech_instance()
    player = alexa.set_player_instance(alexa.playback_progress_report_request)
    player.setup(volume)
    player.blocking_play('files/hello.mp3')
    while True:
        try:
            speech.connect()
            alexa.user_initiate_audio()
        except (KeyboardInterrupt, EOFError, SystemExit):
            break

if __name__ == "__main__":
    config = helper.read_dict('config.dict')
    if 'refresh_token' not in config:
        print("Please go to http://localhost:5000")
        authorization.get_authorization()
        config = helper.read_dict('config.dict')
    
    player = None
    work(config)
