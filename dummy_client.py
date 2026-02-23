from multiprocessing.connection import Client


address = (host, port) = ("localhost", 61000)
"""Hostname/IP address and TCP port where the STT program listens."""


# Attempt to set up a connection to the speech-to-text program. Fail
# with ConnectionRefusedError if no speech-to-text program is running at
# the specified address.
print(f"Trying to connect to STT program at {address}")
with Client(address) as connection:
    print(f"Connected to {address}")

    # Tell STT program to start listening to the user
    connection.send("Start listening")
    print("Command sent to STT program: Start listening")

    while True:
        try:
            # The next line blocks until there is something to receive
            msg = connection.recv()

        except KeyboardInterrupt:
            # The user hit Ctrl+C
            break

        else:
            print(f"Received from STT program: {msg}")

    # Tell STT program to stop listening to the user
    connection.send("Stop listening")
    print("Command sent to STT program: Stop listening")

    # Multiple successive start/stop commands can be sent during the
    # same session:
    #connection.send("Start listening")
    #print("Command sent to STT program: Start listening")
    #
    #print(connection.recv())  # Pull a single message from the socket
    #
    #connection.send("Stop listening")
    #print("Command sent to STT program: Stop listening")


print("Connection closed")
