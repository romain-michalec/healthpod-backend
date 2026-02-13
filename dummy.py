from multiprocessing.connection import Listener

host = "localhost"
"""Network interface to listen on.

Interface name (such as localhost) or IP address (such as 127.0.0.1). If
using an empty string, the server will listen for incoming connections
on all available network interfaces.
"""

port = 61000
"""TCP port to listen on."""


# Basic print-to-stdout server
address = (host, port)
with Listener(address) as listener:
    print(f"Listening for connections on {listener.address}")

    with listener.accept() as connection:  # Block until there is an incoming connection
        print(f"Connection accepted from {listener.last_accepted}")

        while True:
            msg = connection.recv()  # Block until there is something to receive
            print(f"Received: {msg}")

    print("Connection closed")
