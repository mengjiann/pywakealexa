import helper
import authorization
import alexa_device
import sys
import signal
import time

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"

def cleanup(signal, frame):
    sys.exit(0)

def work(config):
    volume = 60
    
    # defualt if pulseaudio otherwise plughw:[CARDID]
    mic_device = 'default'
    speaker_device = 'plughw:1'

    for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM):
        signal.signal(sig, cleanup)

    alexa = alexa_device.AlexaDevice(config)
    speech = alexa.set_speech_instance(mic_device)
    player = alexa.set_player_instance(alexa.playback_progress_report_request, speaker_device)
    player.setup(volume)
    player.blocking_play('files/hello.mp3')

    while 1:
        try:
            speech.connect()
            alexa.user_initiate_audio()
        except (KeyboardInterrupt, EOFError, SystemExit):
            break
        time.sleep(0)

if __name__ == "__main__":
    config = helper.read_dict('config.dict')
    if 'refresh_token' not in config:
        print("Please go to http://localhost:5000")
        authorization.get_authorization()
        config = helper.read_dict('config.dict')

    work(config)
