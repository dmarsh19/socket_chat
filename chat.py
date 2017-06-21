#!/usr/bin/env python3
"""
-bind 'Send' to Shift-Enter
-pop-up ChatWindow when a message comes in on server that doesn't have a ui window
-tls/ssl
-tests
-add_connection on menu
-menu for ChatWindow?
"""
import os
import threading
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from socket_chat.ui import ChatMain
from socket_chat.servers import ChatRequestServer, ChatRequestHandler

ADDRESS = '' # '': symbolic name meaning all available interfaces on localhost
PORT = 12141 # non-privileged


def main():
    """Logic neede to run the entire chat application (ui and servers) on click of script."""
    msg_queue = Queue()
    request_server = ChatRequestServer((ADDRESS, PORT), ChatRequestHandler)
    # can be called using self.server.queue from inside ChatRequestHandler
    request_server.queue = msg_queue
    request_server_thread = threading.Thread(target=request_server.serve_forever)
    # if main thread is closed, exit all other threads
    request_server_thread.daemon = True
    request_server.daemon_threads = True
    request_server_thread.start()

    #TODO: bad xml path gives unhelpful error - ui.py, line 101, _load_connection_file()
    # map(self._populate_connections, xml_iter_by_tag(self.connection_file, 'connection'))
    # TypeError: argument 2 to map() must support iteration
    #ChatMain().mainloop()
    ChatMain(os.path.abspath("connections.xml"), msg_queue=msg_queue).mainloop()
# END main()


if __name__ == '__main__':
    main()
# class ChatApplication(object):
#     def __init__(self, root, pipe):
#         self.center_window() # set the window geometry to display in the center of the screen
#     # END __init__()

#     def center_window(self):
#         """Center the root window on the screen."""
#         # get screen width and height and calculate x,y for Tk() window
#         x = (self.root.winfo_screenwidth() / 2) - (self.width / 2)
#         y = (self.root.winfo_screenheight() / 2) - (self.height / 2)
#         # set the dimensions of the window and where it is placed
#         # TODO: {}.format
#         self.root.geometry('%dx%d+%d+%d' % (self.width, self.height, x, y))
#     # END center_window()
# # END ChatApplication


# if __name__ == '__main__':
#     root = tk.Tk()
#     gui = ChatApplication(root, client_pipe)
#     # bind Shift+Enter to the input window to send.
#     #TODO: shift-return still adds a newline after the message is sent.
#     gui.master.input.bind("<Shift-Return>", send_and_display_msg)
