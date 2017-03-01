"""
Send is bound to Shift-Enter

-auto size window
-negotiate connection start between two hosts based on computer name only
-change color and side where messages come through
-add timestamp
-tls/ssl
"""
import socket
import Tkinter as Tk
import multiprocessing

SERVER_HOST = '' # Symbolic name meaning all available interfaces on localhost
SERVER_PORT = 12141 # Arbitrary non-privileged port
CLIENT_HOST = 'ATL-L-F8YDM72'#'ATL-L-7YZMM12'
CLIENT_PORT = 12142


class ChatApplication(object):
    listener_delay = 250
    """Tkinter class used to build a GUI window."""
    def __init__(self, root, pipe):
        self.root = root
        self.width = 550
        self.height = 500
        self.root.resizable(0, 0) # not resizeable
        self.root.title("Socket Chat")
##        self.root.iconbitmap(default='img/AGLRSymbol.ico')
        self.center_window() # set the window geometry to display in the center of the screen
        # create a frame encompassing the entire root widget. While all other widgets
        # could be created straight on root, this allows some further customization ability.
        self.master = Tk.Frame(self.root,
                               width=self.width,
                               height=self.height)
        #####
        # create frames within master for task groups(if needed)
        #####
        # populate display text window
        #  -self.master.display
        #  -self.master.display_scroll
        self.init_display()
        # populate input text window and button
        #  -self.master.input
        #  -self.master.input_scroll
        #  -self.master.send
        self.init_input()
        #####
        # draw everything to screen
        # display
        # left and right padding
        self.spacer(self.master, row=0, column=0, rowspan=5, width=5)
        self.spacer(self.master, row=0, column=3, rowspan=5, width=5)
        # top padding
        self.spacer(self.master, row=0, column=1, columnspan=2, height=5)
        self.master.display.grid(row=1, column=1)
        self.master.display_scroll.grid(row=1, column=2, sticky="ns")
        # middle spacer
        self.spacer(self.master, row=2, column=1, columnspan=2, height=10)
        # input
        self.master.input.grid(row=3, column=1)
        self.master.input_scroll.grid(row=3, column=2, sticky="ns")
        self.spacer(self.master, row=4, column=1, columnspan=2, height=10)
        self.master.send.grid(row=5, column=1, sticky="e")
        #####
        # draw master last to display when all else has been drawn.
        self.master.grid()

        self.pipe = pipe
        self.pipe_listener = self.root.after(self.listener_delay, self.listen_pipe)
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
        relief = kwargs.pop("relief", Tk.FLAT)
        spacer = Tk.Frame(parent,
                          width=width,
                          height=height,
                          background=backgroundcolor,
                          relief=relief)
        spacer.grid(row=row, column=column,
                    columnspan=columnspan,
                    rowspan=rowspan)
    # END spacer()

    def center_window(self):
        """Center the root window on the screen."""
        # get screen width and height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # calculate x,y for Tk window
        x = (screen_width / 2) - (self.width / 2)
        y = (screen_height / 2) - (self.height / 2)

        # set the dimensions of the screen
        # and where it is placed
        # TODO: {}.format
        self.root.geometry('%dx%d+%d+%d' % (self.width, self.height, x, y))
    # END center_window()

    def init_display(self):
        """."""
        self.master.display = Tk.Text(self.master, state=Tk.DISABLED, width=65, height=17)
        # link the Scrollbar to Text
        self.master.display_scroll = Tk.Scrollbar(self.master,
                                                  command=self.master.display.yview)
        self.master.display['yscrollcommand'] = self.master.display_scroll.set
    # END init_display()

    def init_input(self):
        """Create the UI objects associated with the chat display window."""
        self.master.input = Tk.Text(self.master, width=65, height=10)
        # link the Scrollbar to Text
        self.master.input_scroll = Tk.Scrollbar(self.master,
                                               command=self.master.input.yview)
        self.master.input['yscrollcommand'] = self.master.input_scroll.set
        self.master.send = Tk.Button(self.master,
                                     text='Send',
                                     width=15,
                                     height=1,
                                     command=self.display_local_msg)
    # END init_input()

    def display_local_msg(self):
        """."""
        self.msg = self.master.input.get(1.0, Tk.END)
        self.display_msg(self.msg)
        self.master.input.delete(1.0, Tk.END)
    # END display_local_msg()

    def display_msg(self, msg):
        """."""
        self.master.display.config(state=Tk.NORMAL)
        self.master.display.insert(Tk.END, msg)
        self.master.display.config(state=Tk.DISABLED)
    # END display_msg()

    def listen_pipe(self):
        # no timeout, return immediately, do not block
        ret = self.pipe.poll()
        if ret:
            msg = self.pipe.recv_bytes()
            self.display_msg(msg)
        self.pipe_listener = self.root.after(self.listener_delay, self.listen_pipe)
    # END listen_pipe()
# END ChatApplication()


class ChatSocketServer(object):
    """."""
    def __init__(self, pipe):
        """."""
        self.pipe = pipe
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((SERVER_HOST, SERVER_PORT))
        self.listen()
    # END __init__()

    def listen(self):
        self.sock.listen(1)
        self.serve()
    # END listen()

    def serve(self):
        """."""
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
# END ChatSocketServer()


def socket_client(data=None):
    """."""
    if data:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((CLIENT_HOST, CLIENT_PORT))
        sock.sendall(data)
        sock.close()
# END socket_client()


def start_socket_server(pipe):
    """."""
    s = ChatSocketServer(pipe)
# END start_socket_server()


def close_all():
    """."""
    server_proc.terminate()
    root.destroy()


def send_and_display_msg(*args, **kwargs):
    """."""
    # display to chat screen (is gui global?)
    gui.display_local_msg()
    # send to socket. If no server on other end, notify unavailable.
    try:
        socket_client(gui.msg)
    except socket.error:
        gui.display_msg('[user is unavailable]\n')
# END send_and_display_msg()


if __name__ == '__main__':
    # False: client can only receive, server can only send
    client_pipe, server_pipe = multiprocessing.Pipe(False)
    server_proc = multiprocessing.Process(target=start_socket_server, args=(server_pipe,))
    server_proc.start()
    
    # create the gui, re-configure the send button callback to both
    #  send on the socket and display locally.
    root = Tk.Tk()
    gui = ChatApplication(root, client_pipe)
    gui.master.send.configure(command=send_and_display_msg)
    # binds
    root.protocol("WM_DELETE_WINDOW", close_all)
    gui.master.input.bind("<Return>", send_and_display_msg)
    # mainloop() blocks script until Tk is completed or closed (destroyed)
    root.mainloop()
