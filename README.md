# Notice

This is a modified version of PyWakeAlexa from https://github.com/mikeyy/pywakealexa

Instead of using pocketsphinx to detect and process the hotword, Snowboy, a hotword detection engine is used. More info can be found on: https://snowboy.kitt.ai/. Currently it uses Alexa as the wake word. However, you can customize the wake word but training yours on the Snowboy site (please visit the website for more guide).

## Features

- Tested and run on Raspberry Pi 2
- Customizable wake word (Default is Alexa)
- Runs 24/7 so you can get help when you need it
- Still exploring the feature on the original repository.

## Python Alexa Voice Service

This project is a Python implementation of Amazon's Alexa Voice Service (AVS). The main goal of this is to use AVS to perform home automation

## Getting start

1. Follow the directions from Amazon on how to get your Client ID, Client Secret, and ProductID (parts of Chapter 3 and Chapter 6).
2. Rename config_example.dict to config.dict. Then open the file and update the Client ID, Client Secret, and ProductID values to your own values.
3. Run the main.py script.
``
python main.py ./resources/alexa.umdl
``
4. You might need to run the following command to kill the hang command.
``
pkill -f python
``

## Requirements

- [Python 2.7+](https://www.python.org/)
	- [cherrypy](http://www.cherrypy.org/)
    - [requests](http://docs.python-requests.org/en/master/)
    - [hyper](https://hyper.readthedocs.org/en/latest/) (developer branch)
    - webrtcvad
    - vlc

- [Microphone](http://a.co/eHZgfoT) and speaker
