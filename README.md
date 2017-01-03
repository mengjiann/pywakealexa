# Notice

This is a modified version of Python Alexa Voice Service from https://github.com/nicholasjconn/python-alexa-voice-service. Unfortuanetly I've removed the Alarm for now until I am able to dig more into the code and test it more thoroughly.

Adjustments made allow you to call upon your device and wake up Alexa, with a wake word that you so happen to decide on. I've yet to find opportunity on polishing all modifications I've made thus so far. You will stumble upon bugs, and I kindly request any feedback.

# Features

- Runs on a Raspberry Pi 3 Model B (Have not had the chance to try earlier models, I probably won't.)
- Customizable wake word (Default is JARVIS)
- Playback functionality e.g. mute, stop, next, quiet (turn volume down), louder (turn volume up)
- Runs 24/7 so you can get help when you need it
- Many more to come

# Python Alexa Voice Service (pyWakeAlexa)

This project is a Python implementation of Amazon's Alexa Voice Service (AVS). The goal of this project is to create cross-platform example Alexa device that is completely compatible with the current AVS API (v20160207). This is a work in progress.

## Requirements
- [Python 2.7+](https://www.python.org/)
	- [cherrypy](http://www.cherrypy.org/)
    - [requests](http://docs.python-requests.org/en/master/)
    - [hyper](https://hyper.readthedocs.org/en/latest/) (developer branch)
	- [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/)
	- [alsaaudio]
    - [webrtcvad]
    - [pocketsphinx]
    - [vlc]
- [Microphone](http://a.co/eHZgfoT) and speaker
