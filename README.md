<!-- -*- coding: utf-8-unix -*- -->

# AI-assisted self-screening health station (backend)

This repository contains the backend of the AI-assisted self-screening health station for project RES 1625688 (NHS Tayside).

The station, or pod, or kiosk, assists patients in using wireless medical devices to collect a set of measurements as part of their regular monitoring for cardiovascular disease in primary care. The project is funded by [Tay Health Tech](https://tayhealthtech.org.uk/) and is a feasibility study.

## Description

The backend is written in Python. It must be run on a computer with sufficient computing power to perform automatic speech recognition. It consists of three components:

* A coordinator program (`main.py`) runs a finite state machine implementing the health check process. It interfaces with a large language model running in the cloud, which provides the conversational part of the interaction with the patient. It also interfaces with the [frontend](https://github.com/harilakshman-333/healthub-main).

* A speech-to-text program (`listen.py`) listens to the patient and sends the transcript of what they say to the coordinator program.

* A Bluetooth interface receives the measurements from the wireless medical devices and forwards them to the coordinator program. There is one Bluetooth interface program for each medical device.

## Dependencies

We are developing and testing on Ubuntu Linux 24.04 LTS with Python 3.12.

### System-wide dependencies

Use, for example, `apt list --installed python3-{dev,venv,pip,pip-whl}` to ensure that these packages are installed. If not, install them with `sudo apt install ...`.

The speech-to-text program uses SpeechRecognition, which requires PortAudio through its Python bindings PyAudio for [microphone input](https://github.com/Uberi/speech_recognition?tab=readme-ov-file#pyaudio-for-microphone-users). Install PortAudio with:

```shell
sudo apt install portaudio19-dev
```

On macOS, run `brew install portaudio` instead. On Microsoft Windows, do not install PortAudio manually; it is included in the PyAudio wheels (precompiled binaries).

### Virtual environment

Create a virtual environment using [`venv`](https://docs.python.org/library/venv.html) and activate it:

```shell
python3 -m venv [--prompt=<prompt>] --upgrade-deps </path/to/new/venv>
source </path/to/new/venv>/bin/activate
```

Then install the following dependencies:

```shell
python3 -m pip install langchain langchain-openai langgraph pydantic
python3 -m pip install "speechrecognition[audio,whisper-local]" sounddevice
```

For development only:

```shell
python3 -m pip install pillow
```

We also provide a `requirements.txt` file for repeatable installations, created with `python3 -m pip freeze > requirements.txt` at the time of writing:

```shell
python3 -m pip install -r requirements.txt
```

## Usage

In a first terminal, activate your virtual environment and start the coordinator program:

```shell
export OPENAI_API_KEY="key_goes_here"
python3 main.py
```

In a second terminal, activate your virtual environment and start the speech-to-text program. Use option `-h`, `--help` to show all available options. If no microphone is specified on the command line, the default microphone is used:

```shell
python3 listen.py
```

If you only want to test the communication between the speech-to-text program and a dummy receiver, you can run `dummy.py` instead of `main.py`.
