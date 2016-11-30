import helper
import authorization
import alexa_device
import subprocess
import signal
import sys
import snowboy.snowboydecoder as snowboydecoder

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"


def play_mpc():
    alexa_device.alexa_audio_instance.player.play()
                        
def pause_mpc():
    alexa_device.alexa_audio_instance.player.pause()
   
def stop_mpc():
    alexa_device.alexa_audio_instance.player.stop()


if __name__ == "__main__":
    # Load configuration file (contains the authorization for the user and device information)
    config = helper.read_dict('config.dict')
    # Check for authorization, if none, initialize and ask user to go to a website for authorization.
    if 'refresh_token' not in config:
        print("Please go to http://localhost:5000")
        authorization.get_authorization()
        config = helper.read_dict('config.dict')

    # Create alexa device
    alexa_device = alexa_device.AlexaDevice(config)

    models = ['files/alexa.umdl', 'files/play.pmdl', 'files/pause.pmdl', 'files/stop.pmdl']
    detector = snowboydecoder.HotwordDetector(models, sensitivity=0.4)
    print('Listening... Press Ctrl+C to exit')
    alexa_device.alexa_audio_instance.play_audio(file='files/hello.mp3')

    detector.start(detected_callback=[alexa_device.user_initiate_audio, play_mpc, pause_mpc, stop_mpc],
                   sleep_time=0.03)
    detector.terminate()