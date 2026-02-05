#!/usr/bin/env python3

from multiprocessing.connection import Client
from queue import Queue
from threading import Thread
from time import sleep

import speech_recognition as sr

from log import Log

mic_id = 9


class Listen:
    def __init__(self):
        self.id = "listen"
        self.logger = Log(self.id)
        self.logger.startup_msg()

        self.logger.log("Loading Whisper model...")
        self.r = sr.Recognizer()

        # List all available microphones
        self.logger.log("Available microphones:")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            self.logger.log(f"  {index}: {name}")

        # Adjust for ambient noise and test microphone
        with sr.Microphone(device_index=mic_id) as source:
            self.logger.log("Adjusting for ambient noise... (be quiet)")
            self.r.adjust_for_ambient_noise(source, duration=2)
            self.logger.log(f"Energy threshold: {self.r.energy_threshold}")

            self.logger.log("Say something!")
            try:
                audio = self.r.listen(source, timeout=None, phrase_time_limit=5)
                self.logger.log("Got audio!")
            except Exception as e:
                self.logger.log_warn(f"Error: {e}")

        # Queue to hold audio for processing
        self.audio_queue = Queue()

        self.logger.log_great("Ready.")

    def listen(self):
        listen_thread = Thread(target=self.listen_worker)
        listen_thread.daemon = True
        listen_thread.start()

    def listen_worker(self):
        recognize_thread = Thread(target=self.recognize_worker)
        recognize_thread.daemon = True
        recognize_thread.start()
        with sr.Microphone(device_index=mic_id) as source:
            self.logger.log("Adjusting for ambient noise...")
            self.r.adjust_for_ambient_noise(source, duration=1)
            try:
                while True:
                    self.logger.log("Listening...")
                    timed_out = False
                    try:
                        audio = self.r.listen(source, phrase_time_limit=10)
                    except sr.WaitTimeoutError:
                        timed_out = True
                        self.logger.log_warn("Listen timeout.")
                    if not timed_out:
                        self.audio_queue.put(audio)
            except KeyboardInterrupt:
                pass

        self.audio_queue.join()
        self.audio_queue.put(None)
        recognize_thread.join()

    def recognize_worker(self):
        self.logger.log("Started worker thread.")

        # Set up a connection to a running controller
        self.logger.log("Connecting to controller...")
        address = ('localhost', 6000)
        connection = Client(address, authkey=b'secret password')
        self.logger.log("Connection open")

        while True:
            audio = self.audio_queue.get()
            if audio is None:
                break

            utterance = self.r.recognize_whisper(
                audio, language="English", model="base"
            )

            # Print to the console
            log = "Utterance:" + utterance
            self.logger.log(log)

            # Send to the controller
            connection.send(utterance)
            self.logger.log("Utterance sent to controller")

            self.logger.log("Terminated worker thread.")
            self.audio_queue.task_done()

        # Close connection to the controller
        self.logger.log("Closing connection")
        l.connection.close()
        self.logger.log("Connection closed")

if __name__ == "__main__":
    l = Listen()
    l.listen()
    while True:
        sleep(1)
