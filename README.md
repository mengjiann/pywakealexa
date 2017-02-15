<<<<<<< HEAD
# Notice

This is a modified version of Python Alexa Voice Service from https://github.com/nicholasjconn/python-alexa-voice-service. Unfortuanetly I've removed the Alarm for now until I am able to dig more into the code and test it more thoroughly.

Adjustments made allow you to call upon your device and wake up Alexa, with a wake word that you so happen to decide on. I've yet to find opportunity on polishing all modifications I've made thus so far. You will stumble upon bugs, and I kindly request any feedback.

## Features

- Runs on a Raspberry Pi 3 Model B (Have not had the chance to try earlier models, I probably won't.)
- Customizable wake word (Default is JARVIS)
- Playback functionality e.g. mute, stop, next, quiet (turn volume down), louder (turn volume up)
- Runs 24/7 so you can get help when you need it
- Many more to come

## Python Alexa Voice Service (pyWakeAlexa)

<<<<<<< HEAD
This project is a Python implementation of Amazon's Alexa Voice Service (AVS). The goal of this project is to create cross-platform example Alexa device that is completely compatible with the current AVS API (v20160207). This is a work in progress.

## Requirements

- [Python 2.7+](https://www.python.org/)
	- [cherrypy](http://www.cherrypy.org/)
    - [requests](http://docs.python-requests.org/en/master/)
    - [hyper](https://hyper.readthedocs.org/en/latest/) (developer branch)
	- pyalsaaudio
    - webrtcvad
    - pocketsphinx
    - vlc

- [Microphone](http://a.co/eHZgfoT) and speaker
=======
1. [Register for an Amazon Developer Account](https://github.com/alexa/alexa-avs-raspberry-pi#61---register-your-product-and-create-a-security-profile).
2. Run `git clone https://github.com/respeaker/Alexa.git && cd Alexa`
3. Rename `example_creds.py` to `creds.py` and fill `ProductID`, `Security_Profile_Description`, `Security_Profile_ID`, `Client_ID` and `Client_Secret` with your Alexa device information.
4. Run `sudo pip install cherrypy requests pyaudio webrtcvad pocketsphinx respeaker` to get required python packages.
5. You might also need these depdencies if you got errors at the above step: `sudo apt-get install python-dev portaudio19-dev swig libpulse-dev`. Then re-run step 4.
6. Run `python auth_web.py` and open [http://localhost:3000](http://localhost:3000)

    It will redirect you to Amazon to sign in.
    Make sure you have whitelisted the the above URL (with http:// not https:// in your app profile)

7. Run `python alexa.py` to interact with Alexa.


### On ReSpeaker
Alexa will be installed at the lasest firmware of ReSpeaker. If the command `alexa` is available, skip step 1.

1. Download alexa ipk and install it.

  ```
  cd /tmp
  wget https://github.com/respeaker/get_started_with_respeaker/raw/master/files/alexa_2017-01-18_ramips_24kec.ipk
  opkg install alexa_2017-01-18_ramips_24kec.ipk
  ```

2. Run `alexa` or `/etc/init.d/alexa start` to start Alexa Voice Service

3. At the first time, you need to authorize the application.

  Connect ReSpeaker's Access Point, go to [http://192.168.100.1:3000]([http://192.168.100.1:3000) and tt will redirect you to Amazon to sign up or login in.

4. Run `python alexa.py` to interact with Alexa.

>Note: if you get error `IOError: [Errno -9998] Invalid number of channels`, It's likely that `mopidy-hallo` or `alexa` is running and using the audio input channel.
>You can stop `mopidy` by running `/etc/init.d/mopidy stop`. `/etc/init.d/mopidy disable` will disable it to auto-run.
>`/etc/init.d/alexa start` will run `alexa` on background. 


### Credits
+ [AlexaPi](https://github.com/sammachin/AlexaPi).
>>>>>>> origin/master
