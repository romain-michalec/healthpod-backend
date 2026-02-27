import argparse
from multiprocessing.connection import Connection, Listener
from queue import Queue
from threading import Event, Thread

# Import sounddevice to silence ALSA and JACK warnings:
# https://github.com/Uberi/speech_recognition/issues/182
import sounddevice
import speech_recognition as sr


ADDRESS = (HOST, PORT) = ("localhost", 61000)
"""Network interface and TCP port to listen on.

The network interface can be a hostname (such as localhost), an IP
address (such as 127.0.0.1), or an emptry string (to bind the listening
socket to all the available interfaces).

Choose a port number in the private range and ideally outside the
operating system's range for ephemeral ports (in /proc/sys/net/ipv4/
ip_local_port_range).
"""


START = "Start listening"
"""Client command to request the server start listening to the user."""


STOP = "Stop listening"
"""Client command to request the server stop listening to the user."""


HALLUCINATIONS = [
    # Empty string
    "",
    # Thank you phrases
    "Thank you for watching",
    "Thanks for watching",
    "Thank you for your attention",
    # Subscription/engagement prompts
    "Please subscribe",
    "Don't forget to like and subscribe",
    "Hit the bell icon",
    # Filler phrases
    "You",
    "Subtitles by the Amara.org community",
    # Korean broadcaster signature
    "MBC 뉴스",
]
"""Whisper hallucinations.

Sentences produced by the model when it is fed silence or very
low-energy audio.

More? See community dataset on Hugging Face:
https://huggingface.co/datasets/sachaarbonel/whisper-hallucinations
"""


def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments of this program."""
    parser = argparse.ArgumentParser(
        description="Speech-to-text interface for the self-screening health station"
    )
    parser.add_argument(
        "-l",
        "--list-microphones",
        action="store_true",
        help="list all available microphones and exit",
    )
    parser.add_argument(
        "-m",
        "--microphone",
        metavar="M",
        type=int,
        help=(
            "use the specified microphone (if unspecified, the default microphone is "
            "used)"
        ),
    )
    parser.add_argument(
        "-t",
        "--energy-threshold",
        metavar="N",
        type=int,
        help=(
            "energy threshold for sounds (between 0 and 4000 - if unspecified, "
            "automatic calibration is performed before listening and the threshold is "
            "further adjusted automatically while listening)"
        ),
    )
    args = parser.parse_args()

    # Ensure that the specified microphone exists
    if (
        args.microphone is not None
        and not 0 <= args.microphone <= get_microphone_count() - 1
    ):
        raise IndexError("Device index out of range")

    # Ensure that the specified energy threshold is valid
    if args.energy_threshold is not None and not 0 <= args.energy_threshold <= 4000:
        raise ValueError("Energy threshold out of 0-4000")

    return args


def get_microphone_count() -> int:
    """Return the number of available microphones."""
    return len(sr.Microphone.list_microphone_names())


def list_microphones() -> None:
    """List all available microphones."""
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"{index}: {name}")


class STT:
    """Multi-threaded speech-to-text pipeline.

    Input from a microphone. Output to a socket. Usage:

    stt = STT(<microphone config>)
    stt.start(<connection object>)
    stt.stop()
    """

    microphone: sr.Microphone
    recognizer: sr.Recognizer
    workers: dict[str, Thread]
    queues: dict[str, Queue]
    stop_cmd: Event
    running: bool

    def __init__(self, microphone_id: int | None, energy_threshold: int | None) -> None:
        """Prep microphone and threads."""
        self.microphone = sr.Microphone(microphone_id)
        self.recognizer = sr.Recognizer()

        # Set the initial energy threshold
        if energy_threshold is not None:
            # Either by using the value specified by the user
            self.recognizer.energy_threshold = energy_threshold
            self.recognizer.dynamic_energy_threshold = False  # Default: True
        else:
            # Or by listening for 1 second (by default) to calibrate the
            # energy threshold for ambient noise levels
            print("Adjusting for ambient noise... Please be quiet")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
        print(f"Initial energy threshold: {self.recognizer.energy_threshold}")

        # Structures for holding threads and inter-thread communications
        self.workers = dict()
        self.queues = dict()

        # Threading event used by the main thread to stop the listener
        # thread (the other threads are stopped in a cascade)
        self.stop_cmd = Event()

        # Keep track of whether the threads are running
        self.running = False

    def start(self, connection: Connection) -> None:
        """Start worker threads.

        No-op if already started.
        """
        if self.running:
            return

        # Threads for listening to the user, recognizing their speech,
        # and sending the recognized speech to the client
        self.workers["listener"] = Thread(target=self.listen)
        self.workers["recognizer"] = Thread(target=self.recognize)
        self.workers["sender"] = Thread(target=self.send, args=(connection,))

        # Task queues (FIFO) for passing audio processing jobs from the
        # listener thread to the recognizer thread and text sending jobs
        # from the recognizer thread to the sender thread
        self.queues["audio"] = Queue()
        self.queues["text"] = Queue()

        self.workers["listener"].start()
        self.workers["recognizer"].start()
        self.workers["sender"].start()

        self.running = True

    def stop(self) -> None:
        """Stop worker threads.

        Blocks until all worker threads are stopped. No-op if already
        stopped.
        """
        if not self.running:
            return

        # Stop listener thread
        self.stop_cmd.set()

        # Wait for both worker threads to be over
        self.workers["listener"].join()
        self.workers["recognizer"].join()
        self.workers["sender"].join()

        # Reset the threading event
        self.stop_cmd.clear()

        self.running = False

    def listen(self) -> None:
        """Capture microphone input.

        This function must be run in a thread. It enqueues the captured
        audio data in a message queue for consumption by the recognize()
        function in a different thread.
        """
        # Repeatedly listen for phrases until the thread receives the
        # stop event. Put the resulting audio on the audio processing
        # job queue. Note that the stop event won't cut off the user
        # mid-sentence.
        with self.microphone as source:
            print("Listening... Say something!")
            while not self.stop_cmd.is_set():
                self.queues["audio"].put(self.recognizer.listen(source))

        print("Stopped listening")

        # Tell the recognizer thread that no other audio job is coming
        self.queues["audio"].put(None)

        # Block until all audio processing jobs are done (empty queue)
        self.queues["audio"].join()

    def recognize(self) -> None:
        """Run speech recognition.

        This function must be run in a thread. It dequeues audio data
        from a message queue fed by the listen() function in a different
        thread.
        """
        while True:
            # Retrieve an audio processing job from the queue
            audio = self.queues["audio"].get()

            # Stop all audio processing if the other thread is done
            if audio is None:
                self.queues["audio"].task_done()
                break

            # Perform speech recognition using Whisper
            #
            # Pick "model" from the output of "import whisper;
            # print(whisper.available_models())". Default is "base". See also
            # https://github.com/openai/whisper#available-models-and-languages.
            #
            # Pick "language" from the full language list at
            # https://github.com/openai/whisper/blob/main/whisper/tokenizer.py.
            # If not set, Whisper will automatically detect the language.
            try:
                utterance = self.recognizer.recognize_whisper(  # type: ignore[attr-defined]
                    audio, model="base.en", language="english"
                )

            except sr.UnknownValueError:
                # Speech was unintelligible
                print("Whisper could not understand audio")

            except sr.RequestError as error:
                # Whisper was unreachable or unresponsive - is it missing,
                # corrupt, or otherwise incompatible?
                print(f"Could not request results from Whisper: {error}")

            else:
                # Remove leading whitespace inserted by Whisper
                utterance = utterance.lstrip()
                print(f"Recognized: {utterance}")

                # Reject hallucinations
                if utterance in HALLUCINATIONS:
                    continue

                # Put the recognized speech on the sending queue
                self.queues["text"].put(utterance)

            finally:
                # Mark the audio processing job as completed in the queue
                self.queues["audio"].task_done()

        print("Stopped recognizing speech")

        # Tell the sender thread that no more recognized speech is coming
        self.queues["text"].put(None)

        # Block until all sending jobs are done (empty queue)
        self.queues["text"].join()

    def send(self, connection: Connection) -> None:
        """Send recognized speech to connected client.

        This function must be run in a thread. It dequeues text data
        from a message queue fed by the recognize() function in a
        different thread.
        """
        while True:
            # Retrieve recognized speech from the queue
            utterance = self.queues["text"].get()

            # Stop all sending if the other thread is done
            if utterance is None:
                self.queues["text"].task_done()
                break

            # Send recognized speech over the connection
            try:
                connection.send(utterance)
            except ValueError as error:
                print(f"Could not send utterance to client: {error}")
            else:
                print(f"Sent to client: {utterance}")
            finally:
                self.queues["text"].task_done()

        print("Stopped sending recognized speech to client")


def main():
    """Run speech-to-text server."""
    # Parse command-line arguments
    args = parse_args()

    if args.list_microphones:
        list_microphones()
        return

    # Listen for incoming connections
    with Listener(ADDRESS) as listener:
        print(f"Listening for connections on {listener.address}")

        while True:
            stt = STT(args.microphone, args.energy_threshold)

            try:
                # The next line blocks until there is an incoming connection
                with listener.accept() as connection:
                    print(f"Connection accepted from {listener.last_accepted}")

                    while True:
                        try:
                            # The next line blocks until there is something to receive
                            request = connection.recv()

                        except EOFError:
                            # There is nothing left to receive and the other end was closed
                            stt.stop()
                            break

                        else:
                            print(f"Request received: {request}")

                            if request == START:
                                stt.start(connection)
                            elif request == STOP:
                                stt.stop()
                            else:
                                pass

                print("Connection closed")

            except KeyboardInterrupt:
                # The user hit Ctrl+C
                stt.stop()
                break

    print("Stopped listening for connections")


if __name__ == "__main__":
    main()
