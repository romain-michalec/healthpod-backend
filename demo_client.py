from multiprocessing.connection import Client
from sys import exit


ADDRESS = (HOST, PORT) = ("localhost", 61000)
"""Hostname/IP address and TCP port where the STT server listens."""


START = "Start STT"
"""Client command to request the server start listening to the user."""


STOP = "Stop STT"
"""Client command to request the server stop listening to the user."""


# Attempt to set up a connection to the speech-to-text server. Fail
# with ConnectionRefusedError if no speech-to-text server is running at
# the specified address.
print(f"Trying to connect to STT server at {ADDRESS}")
with Client(ADDRESS) as connection:
    print(f"Connected to {ADDRESS}")

    # Tell STT server to start listening to the user
    connection.send(START)
    print(f"Request sent: {START}")

    while True:
        try:
            # The next line blocks until there is something to receive
            msg = connection.recv()

        except EOFError:
            # There is nothing left to receive and the other end was closed
            print("Connection closed by the server")
            exit(1)

        except KeyboardInterrupt:
            # The user hit Ctrl+C
            break

        else:
            print(f"Received from server: {msg}")

    # Tell STT server to stop listening to the user
    connection.send(STOP)
    print(f"Request sent: {STOP}")

    # Successive START/STOP commands can be sent on the same connection,
    # for instance here is a second START/STOP session, used to pull a
    # single message from the socket:
    connection.send(START)
    print(f"Request sent: {START}")
    print(f"Received from server: {connection.recv()}")
    connection.send(STOP)
    print(f"Request sent: {STOP}")

print("Connection closed")
