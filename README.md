<!-- -*- coding: utf-8-unix -*- -->

# AI-assisted self-screening station (backend)

This is the backend of the AI-assisted self-screening station of project RES 1625688 (NHS Tayside). The station, or pod, assists a patient in using wireless medical devices to collect a set of measurements as part of their regular monitoring for cardiovasculary disease in primary care. The project is funded by [Tay Health Tech](https://tayhealthtech.org.uk/) and is a feasibility study.

## Description

The backend is written in Python and is run by a computer that is sufficiently powerful to run automatic speech recognition. It consists of three parts:

* A coordinator program (`main.py`) runs the state machine implementing the health check process. It interfaces with a large language model running in the cloud that provides the conversational part of the interaction with the patient. It also interfaces with the [frontend](https://github.com/harilakshman-333/healthub-main).

* A speech-to-text program (`listen.py`) turns the patient's voice into text and sends that text to the coordinator.

* A Bluetooth interface receives the data from the wireless medical devices and forwards it to the coordinator. There is one interface program for each medical device.

## Dependencies

We are developing and testing using Python 3.12. In a virtual environment, run:

```shell
python3 -m pip install langchain langchain-openai langgraph
python3 -m pip "SpeechRecognition[audio,whisper-local]" colorama
```

Note that [SpeechRecognition uses PyAudio for microphone input](https://github.com/Uberi/speech_recognition?tab=readme-ov-file#pyaudio-for-microphone-users), and PyAudio in turns requires the PortAudio library's development package:

```shell
apt install portaudio19-dev
```

## Usage

In a first terminal, activate your virtual environment and start the coordinator program.

```shell
python3 main.py
```

In a second terminal, activate your virtual environment and start the speech-to-text program:

```shell
python3 listen.py
```

The speech-to-text program will likely fail because the microphone ID is hardcoded. Inspect the list of discovered microphones and adjust the variable `mic_id` at the start of `listen.py`. Once it runs successfully, follow the instructions it prints in the terminal.

If you just want to try out the communication between the coordinator and the speech-to-text program, you can run `dummy.py` instead of `main.py`.
