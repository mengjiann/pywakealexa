import helper
import authorization
import alexa_device
import sys
import signal
import time
import snowboydecoder


__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"

interrupted = False

def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted


def work(config):
    volume = 60
    
    # defualt if pulseaudio otherwise plughw:[CARDID]
    mic_device = 'default'
    speaker_device = 'plughw:1'

    if len(sys.argv) == 1:
        print("Error: need to specify model name")
        print("Usage: python demo.py your.model")
        sys.exit(-1)

    model = sys.argv[1]

    signal.signal(signal.SIGINT, signal_handler)


    print("Listening... Press Ctrl+C to exit")

    while True:
        try:
            # Init the snowboydetector
            detector = snowboydecoder.HotwordDetector(model, sensitivity=0.5)
            detector.start(detected_callback=snowboydecoder.play_audio_file,
               interrupt_check=interrupt_callback,
               sleep_time=0.05)
            detector.terminate()

            # Init the existing alexa_device.
            alexa = alexa_device.AlexaDevice(config)
            speech = alexa.set_speech_instance(mic_device)
            player = alexa.set_player_instance(alexa.playback_progress_report_request, speaker_device)
            player.setup(volume)
            alexa.user_initiate_audio()
            alexa.close()

        except (KeyboardInterrupt, EOFError, SystemExit):
            alexa.close()
            sys.exit()
            break

if __name__ == "__main__":
    config = helper.read_dict('config.dict')
    if 'refresh_token' not in config:
        print("Please go to http://localhost:5000")
        authorization.get_authorization()
        config = helper.read_dict('config.dict')

    work(config)
