import helper
import authorization
import alexa_device
import subprocess
import snowboy.snowboydecoder as snowboydecoder

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"



def user_input_loop(alexa_device):
    """ This thread initializes a voice recognition event based on Snowboy's Alexa wake word universal model. This function uses voice recognition for interacting with the user. The user can initiate a command by saying Alexa, or quit if desired.

        This is currently the "main" thread for the device.
    """

    models = ['files/alexa.umdl', 'files/play.pmdl', 'files/pause.pmdl', 'files/stop.pmdl']
    detector = snowboydecoder.HotwordDetector(models, sensitivity=0.5)
    print('Listening... Press Ctrl+C to exit')
    
    # main Snowboy detector loop
    detector.start(detected_callback=[alexa_device.user_initiate_audio, play_mpc, pause_mpc, stop_mpc],
                   sleep_time=0.03)
    detector.terminate()
 
def play_mpc():
    subprocess.call(['mpc', 'play'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                        
def pause_mpc():
    subprocess.call(['mpc', 'pause'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
   
def stop_mpc():
    subprocess.call(['mpc', 'clear'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


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

    user_input_loop(alexa_device)

    print("Done")
