#!/usr/bin/env python3
"""
Send is bound to Shift-Enter

-auto size window
-negotiate connection start between two hosts based on computer name only
-tls/ssl
"""
import time
import datetime
import socket
import multiprocessing
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk


PORT = 12141 # non-privileged
CLIENT_HOST = 'ATL-L-7YZMM12'#'ATL-L-F8YDM72'


class ChatApplication(object):
    """Tkinter class used to build a GUI window."""
    width = 550
    height = 500
    pipe_listener_delay = 250
    timestamp_fmt = '%a, %b %d, %Y %H:%M:%S'
    def __init__(self, root, pipe):
        self.root = root
        self.root.resizable(0, 0) # not resizeable
        self.root.title("Socket Chat")
        self.pipe = pipe
        self.current_local_msg = ""
        self.timestamp = time.strftime(self.timestamp_fmt)
        self.center_window() # set the window geometry to display in the center of the screen
        # create a frame encompassing the entire root widget. While all other widgets
        # could be created straight on root, this allows some further customization ability.
        self.master = tk.Frame(self.root, width=self.width, height=self.height)
        #####
        # populate display text window
        #  -self.master.display
        #  -self.master.display_scroll
        self.init_display()
        # text display tags - format how the texdt appears based on what generated the text
        self.master.display.tag_config('local', justify=tk.RIGHT)
        self.master.display.tag_config('error', foreground="red")
        self.master.display.tag_config('timestamp', justify=tk.CENTER, foreground="gray")
        self.master.display.tag_config('hostname', foreground="blue")
        # populate input text window and button
        #  -self.master.input
        #  -self.master.input_scroll
        self.init_input()
        self.master.send = tk.Button(self.master, text='Send', width=15, height=1,
                                     command=self.display_local_msg)
        #####
        # draw everything to screen
        # display
        # left and right padding
        self.spacer(self.master, row=0, column=0, rowspan=5, width=5)
        self.spacer(self.master, row=0, column=3, rowspan=5, width=5)
        # top padding
        self.spacer(self.master, row=0, column=1, columnspan=2, height=5)
        self.master.display.grid(sticky="we") # row=1, column=1 in init_display()
        self.master.display_scroll.grid(row=1, column=2, sticky="ns")
        # middle spacer
        self.spacer(self.master, row=2, column=1, columnspan=2, height=10)
        # input
        self.master.input.grid(sticky="we") # row=3, column=1 in init_input()
        self.master.input_scroll.grid(row=3, column=2, sticky="ns")
        self.spacer(self.master, row=4, column=1, columnspan=2, height=10)
        self.master.send.grid(row=5, column=1, sticky="e")
        #####
        # draw master last to display when all else has been drawn
        self.master.grid()
        #####
        # start listener for messages passed through pipe
        self.pipe_listener_ptr = self.root.after(self.pipe_listener_delay, self.listen_on_pipe)
        # on startup, write the initial timestamp
        self.display_msg('{0}\n'.format(self.timestamp), ('timestamp',))
    # END __init__()

    def spacer(self, parent, **kwargs):
        """A generic function to create spacers of all sizes.

           Required arguments: - parent widget
           Optional arguments: - (spacer)width (default: 1)
                               - (spacer)height (default: 1)
                               - row (default: 0)
                               - column (default: 0)
                               - columnspan (default: 1)
                               - rowspan (defaul: 1)
                               - backgroundcolor (default: OS default)
                               - relief: (default: FLAT)"""
        width = kwargs.pop("width", 1)
        height = kwargs.pop("height", 1)
        row = kwargs.pop("row", 0)
        column = kwargs.pop("column", 0)
        columnspan = kwargs.pop("columnspan", 1)
        rowspan = kwargs.pop("rowspan", 1)
        backgroundcolor = kwargs.pop("backgroundcolor", "")
        relief = kwargs.pop("relief", tk.FLAT)
        spacer = tk.Frame(parent, width=width, height=height,
                          background=backgroundcolor, relief=relief)
        spacer.grid(row=row, column=column, columnspan=columnspan, rowspan=rowspan)
    # END spacer()

    def center_window(self):
        """Center the root window on the screen."""
        # get screen width and height and calculate x,y for Tk() window
        x = (self.root.winfo_screenwidth() / 2) - (self.width / 2)
        y = (self.root.winfo_screenheight() / 2) - (self.height / 2)
        # set the dimensions of the window and where it is placed
        # TODO: {}.format
        self.root.geometry('%dx%d+%d+%d' % (self.width, self.height, x, y))
    # END center_window()

    def init_display(self):
        """Create the UI objects associated witht the chat display."""
        # create an outer Frame() object to control the Text() size based on pixels, not by font
        outer_frame = tk.Frame(self.master, width=520, height=270)
        outer_frame.grid(row=1, column=1)
        outer_frame.columnconfigure(0, weight=10)
        outer_frame.grid_propagate(False)
        self.master.display = tk.Text(outer_frame, state=tk.DISABLED, wrap=tk.WORD)
        # link the Scrollbar to Text
        self.master.display_scroll = tk.Scrollbar(self.master, command=self.master.display.yview)
        self.master.display['yscrollcommand'] = self.master.display_scroll.set
    # END init_display()

    def init_input(self):
        """Create the UI objects associated with the chat input window."""
        outer_frame = tk.Frame(self.master, width=520, height=160)
        outer_frame.grid(row=3, column=1)
        outer_frame.columnconfigure(0, weight=10)
        outer_frame.grid_propagate(False)
        self.master.input = tk.Text(outer_frame, wrap=tk.WORD)
        # link the Scrollbar to Text
        self.master.input_scroll = tk.Scrollbar(self.master, command=self.master.input.yview)
        self.master.input['yscrollcommand'] = self.master.input_scroll.set
    # END init_input()

    def display_local_msg(self):
        """Store the characters currently in the input window. Send them to be displayed
           on the input window. Clear the input window."""
        self.current_local_msg = self.master.input.get(1.0, tk.END)
        self.display_msg(self.current_local_msg, ('local',))
        self.master.input.delete(1.0, tk.END)
    # END display_local_msg()

    def display_msg(self, msg, text_tags=None):
        """Write msg to chat display window.

        text_tags should be a tuple:
        ex: ('local',)"""
        #TODO: strip hanging newlines?
        self.master.display.config(state=tk.NORMAL)
        report_timestamp = self.report_update_timestamp()
        if report_timestamp is not None:
            self.master.display.insert(tk.END, '{0}\n'.format(report_timestamp), ('timestamp',))

        if text_tags is None:
            self.master.display.insert(tk.END, msg)
        else:
            self.master.display.insert(tk.END, msg, text_tags)
        self.master.display.config(state=tk.DISABLED)
        self.master.display.yview(tk.END)
    # END display_msg()

    def report_update_timestamp(self):
        """If current timestamp is older than 5 minutes,
           update to new time and print to display window.
           Called from within display_msg()."""
        ret = None
        five_min_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
        if datetime.datetime.strptime(self.timestamp, self.timestamp_fmt) <= five_min_ago:
            # reset the timestamp before re-calling display_msg to avoid infinite loop
            ret = self.timestamp
            self.timestamp = time.strftime(self.timestamp_fmt)
            return ret
    # END report_update_timestamp()

    def listen_on_pipe(self):
        """Poll the supplied pipe until returns True. Grab message from pipe and write to
           display window."""
        # no timeout, return immediately, do not block
        ret = self.pipe.poll()
        if ret:
            msg = self.pipe.recv_bytes()
            self.display_msg('{0}: '.format(CLIENT_HOST), 'hostname')
            self.display_msg(msg)
            #self.display_msg('{0}: {1}'.format(CLIENT_HOST, msg))
        self.pipe_listener_ptr = self.root.after(self.pipe_listener_delay, self.listen_on_pipe)
    # END listen_on_pipe()
# END ChatApplication


class ChatSocketServer(object):
    """Open a socket in server mode, waiting for connections."""
    def __init__(self, ip, port, pipe):
        """."""
        self.pipe = pipe
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((ip, port)) # '': symbolic name meaning all available interfaces on localhost
        self.listen()
    # END __init__()

    def listen(self):
        """When a connection on the open socket is made, start serving."""
        self.sock.listen(10)
        self.serve()
    # END listen()

    def serve(self):
        """When a connection is made on the open socket, accept and receive
           the message, appending to a single variable for its entirety
           (assumes data will always be str). Send the message through the pipe.
           Start listening for new connections again."""
        msg = ""
        conn, addr = self.sock.accept()
        while True:
            data = conn.recv(1024)
            if not data:
                break
            msg = msg + data
        self.pipe.send_bytes(str(msg))
        self.listen()
    # END serve()
# END ChatSocketServer


def socket_send_msg(host, port, msg=None):
    """Send a message through a socket to a host."""
    if msg:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.sendall(str(msg))
        sock.close()
# END socket_send_msg()


def close_all():
    """Callback bound to closing chat window. Stops separate server process and
       destroys gui windows.

    Bound to tk.Tk() (root) 'WM_DELETE_WINDOW' protocol."""
    server_proc.terminate()
    root.destroy()
# END close_all()


def send_and_display_msg(*args, **kwargs):
    """Overwrite the callback for gui input Send button. Displays the local message from the
       input window to the display window and sends the message through the socket.

       Because this function involves a server process that is separate from the gui, overwriting
       outside the gui class is better practice."""
    # display to chat window (gui is global; defined in if __name__)
    gui.display_local_msg()
    # send to socket. If no server on other end, notify unavailable.
    try:
        socket_send_msg(CLIENT_HOST, PORT, gui.current_local_msg)
    except socket.error:
        gui.display_msg('[user is unavailable]\n', ('error',))
# END send_and_display_msg()


if __name__ == '__main__':
    # False: client can only receive, server can only send
    client_pipe, server_pipe = multiprocessing.Pipe(False)
    server_proc = multiprocessing.Process(target=ChatSocketServer, args=('', PORT, server_pipe))
    server_proc.start()

    # create the gui, re-configure the send button callback to both
    #  send on the socket and display locally.
    root = tk.Tk()
    gui = ChatApplication(root, client_pipe)
    gui.master.send.configure(command=send_and_display_msg)
    # binds
    # redirect closing chat window to callback
    root.protocol("WM_DELETE_WINDOW", close_all)
    # bind Shift+Enter to the input window to send.
    #TODO: shift-return still adds a newline after the message is sent.
    gui.master.input.bind("<Shift-Return>", send_and_display_msg)
    # mainloop() blocks script until Tk() is completed or closed (destroyed)
    root.mainloop()
