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

    # NOTE
    #
    # Successive START/STOP commands can be sent during the same
    # session, for instance:
    #
    connection.send(START)
    print(f"Request sent again: {START}")
    print(connection.recv())  # Pull a single message from the socket
    connection.send(STOP)
    print(f"Request sent again: {STOP}")
    #
    # However, *beware* that this will re-use the same socket and that
    # the server might have put something from its queue in that socket
    # after the previous STOP command and before the new START command!
    #
    # The STOP command only stops the server from listening to the user,
    # not from continuing to process what was already recorded, and then
    # sending the recognized speech on the socket (regardless of whether
    # the client pulls data from that socket at that point). This
    # behavior is intentional, but it could be changed if it is
    # undesirable.
    #
    # Contrary to a new START command, a new connection to the server
    # gets a fresh socket.


print("Connection closed")
