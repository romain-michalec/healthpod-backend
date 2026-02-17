import argparse
from multiprocessing.connection import Client, Connection
from queue import Queue
from threading import Thread

# Import sounddevice to silence ALSA and JACK warnings:
# https://github.com/Uberi/speech_recognition/issues/182
import sounddevice
import speech_recognition as sr


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
        "-t",
        "--test-microphone",
        action="store_true",
        help="test microphone and exit",
    )
    parser.add_argument(
        "-m",
        "--microphone",
        metavar="M",
        type=int,
        help=(
            "use the specified microphone (if unspecified, the default "
            "microphone is used)"
        ),
    )
    parser.add_argument(
        "-e",
        "--energy-threshold",
        metavar="N",
        type=int,
        help=(
            "initial energy threshold for sounds (between 0 and 4000; "
            "if unspecified, automatic calibration is performed)"
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


def test_microphone(device_index: None | int = None) -> None:
    pass


def listen(
    recognizer: sr.Recognizer,
    audio_queue: Queue,
    microphone: sr.Microphone,
    energy_threshold: None | int = None,
) -> None:
    """Capture microphone input.

    This function must be run in a thread. It enqueues the captured
    audio data in a message queue for consumption by the recognize()
    function in a different thread.
    """
    with microphone as source:
        # Set the initial energy threshold...
        if energy_threshold:
            # ...either by using the value specified by the user...
            recognizer.energy_threshold = energy_threshold
        else:
            # ...or by listening for 1 second (by default) to calibrate
            # the energy threshold for ambient noise levels
            print("Adjusting for ambient noise... Please be quiet")
            recognizer.adjust_for_ambient_noise(source)
        print(f"Initial energy threshold: {recognizer.energy_threshold}")

        # Repeatedly listen for phrases until the user hits Ctrl+C and
        # put the resulting audio on the audio processing job queue
        print("Listening... Say something!")
        try:
            while True:
                audio_queue.put(recognizer.listen(source))
        except KeyboardInterrupt:
            pass

    print("Stopped listening")

    # Block until all current audio processing jobs are done (empty queue)
    audio_queue.join()

    # Tell the other thread that no other audio processing job is coming
    audio_queue.put(None)


def recognize(
    recognizer: sr.Recognizer, audio_queue: Queue, connection: Connection
) -> None:
    """Run speech recognition.

    This function must be run in a thread. It dequeues from a message
    queue holding audio data captured by the listen() function in a
    different thread.
    """
    hallucinations = [
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

    while True:
        # Retrieve an audio processing job from the queue
        audio = audio_queue.get()

        # Stop all audio processing if the other thread is done
        if audio is None:
            audio_queue.task_done()
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
            utterance = recognizer.recognize_whisper(  # type: ignore
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
            print(f"Whisper thinks you said: {utterance}")

            # Reject hallucinations
            if utterance in hallucinations:
                continue

            # Send to the coordinator
            try:
                connection.send(utterance)
            except ValueError as error:
                print(f"Could not send utterance to the coordinator: {error}")
            else:
                print(f"Sent to the coordinator: {utterance}")

        finally:
            # Mark the audio processing job as completed in the queue
            audio_queue.task_done()


def main():
    """Run the speech-to-text interface (this program)."""
    # Parse command-line arguments
    args = parse_args()

    if args.list_microphones:
        list_microphones()
        return

    if args.test_microphone:
        test_microphone(args.microphone)
        return

    # Hostname/IP address and TCP port where the coordinator listens
    address = (host, port) = ("localhost", 61000)

    # Attempt to set up a connection to the coordinator. Fails with
    # ConnectionRefusedError if no coordinator is running at the specified
    # address.
    print(f"Trying to connect to coordinator at {address}")
    with Client(address) as connection:
        print(f"Connected to {address}")

        microphone = sr.Microphone(args.microphone)
        recognizer = sr.Recognizer()

        # Audio processing job queue (FIFO) used for communication
        # between the listener thread and the recognizer thread
        audio_queue = Queue()

        # Start a new thread to recognize audio...
        worker = Thread(target=recognize, args=(recognizer, audio_queue, connection))
        worker.start()

        # ...while this thread focuses on listening
        listen(recognizer, audio_queue, microphone, args.energy_threshold)

    print("Connection closed")


if __name__ == "__main__":
    main()
