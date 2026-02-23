from multiprocessing.connection import Listener


address = (host, port) = ("localhost", 61000)
"""Network interface and TCP port to listen on.

The network interface can be a hostname (such as localhost), an IP
address (such as 127.0.0.1), or an emptry string (to bind the listening
socket to all the available interfaces).

Choose a port number in the private range and ideally outside the
operating system's range for ephemeral ports (in /proc/sys/net/ipv4/
ip_local_port_range).
"""


# This listener prints the messages sent from the other end of the
# connection to the standard output
with Listener(address) as listener:
    print(f"Listening for connections on {listener.address}")

    while True:
        try:
            # The next line blocks until there is an incoming connection
            with listener.accept() as connection:
                print(f"Connection accepted from {listener.last_accepted}")

                while True:
                    try:
                        # The next line blocks until there is something to receive
                        msg = connection.recv()

                    except EOFError:
                        # There is nothing left to receive and the other end was closed
                        break

                    else:
                        print(f"Received: {msg}")

            print("Connection closed")

        except KeyboardInterrupt:
            # The user hit Ctrl+C
            break


print("Stopped listening")
