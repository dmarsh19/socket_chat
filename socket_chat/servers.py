#!/usr/bin/env python3
"""
"""
import socket
import threading
try:
    from SocketServer import ThreadingMixIn, TCPServer, BaseRequestHandler
except ImportError:
    from socketserver import ThreadingMixIn, TCPServer, BaseRequestHandler
try:
    from Queue import Queue
except ImportError:
    from queue import Queue


class ChatRequestServer(ThreadingMixIn, TCPServer):
    """Listen for connection requests. When one is made,
    spawn an instance of ChatRequestHandler in a new thread."""
    pass
# END ChatRequestServer


class ChatRequestHandler(BaseRequestHandler):
    def handle(self):
        """Receive a message from the socket connection, appending to a single variable for
        its entirety (assumes data will always be str). Put tuple(addr, message) on the queue.
           Start listening for new connections again."""
        msg = ""
        while True:
            data = self.request.recv(1024).decode()
            if not data:
                break
            msg = msg + data
        self.server.queue.put_nowait((self.client_address[0], str(msg)))
    # END handle()
# END ChatRequestHandler


def socket_send_msg(address, port, msg=None):
    """Send a message through a socket to a host."""
    if msg:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((address, port))
        sock.sendall(str(msg).encode())
        sock.close()
# END socket_send_msg()


if __name__ == '__main__':
    address = '127.0.0.1'
    port = 12141 # non-privileged
    msg_queue = Queue()
    request_server = ChatRequestServer((address, port), ChatRequestHandler)
    # can be called using self.server.queue from inside ChatRequestHandler
    request_server.queue = msg_queue
    request_server_thread = threading.Thread(target=request_server.serve_forever)
    # if main thread is closed, exit all other threads
    request_server_thread.daemon = True
    request_server.daemon_threads = True
    request_server_thread.start()

    # test message to queue
    socket_send_msg(address, port, 'Test')

    print(request_server.queue.get())