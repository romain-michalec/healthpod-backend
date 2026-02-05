from multiprocessing.connection import Listener

print("Starting up dummy controller")
address = ('localhost', 6000)     # family is deduced to be 'AF_INET'
listener = Listener(address, authkey=b'secret password')
print("Listening for connections...")

conn = listener.accept()
print('Connection accepted from', listener.last_accepted)

while True:
    print("Listening for messages...")
    msg = conn.recv()
    print("Received:", msg)
    if 'close connection' in msg.strip().lower():
        print("Closing connection")
        conn.close()
        print("Connection closed")
        break

print("Shuting down dummy controller")
listener.close()
print("No longer listening for connections")
