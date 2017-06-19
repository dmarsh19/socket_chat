#!/usr/bin/env python3
"""
Send is bound to Shift-Enter

-auto size window
-negotiate connection start between two hosts based on computer name only
-tls/ssl
"""
import socket
import threading
import ttk
try:
    import SocketServer as socketserver
except ImportError:
    import socketserver
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk
try:
    import Queue as queue
except ImportError:
    import queue

from connections import *


class AutoScrollbar(tk.Scrollbar):
    """a scrollbar that hides itself if it's not needed.
       Only works if you use the grid geometry manager."""
    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        tk.Scrollbar.set(self, low, high)
    # END set()
# END AutoScrollbar


class ChatMain(tk.Frame):
    """."""
    address = '' # '': symbolic name for all available interfaces on localhost
    port = 12141 # non-privileged
    title = 'Socket Chat'
    queue = queue.Queue()
    def __init__(self, connection_file='', *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.pack(expand=tk.YES, fill=tk.BOTH)

        self.server = ChatSocketServer((self.address, self.port, self.queue), ChatRequestHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.master.title(self.title)
        # set frame resize priorities
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/ttk-Treeview.html
        self.tree = ttk.Treeview(self, columns='connections', show='', selectmode='browse')
        self.ysb = AutoScrollbar(self, command=self.tree.yview, orient=tk.VERTICAL)
        self.tree['yscroll'] = self.ysb.set

        # populate the connections
        if connection_file:
            self.load_connection_file(connection_file)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.ysb.grid(row=0, column=1, sticky="ns")
    # END __init__()

    def load_connection_file(self, connection_file=''):
        """."""
        if connection_file != '':
            self.connection_file = connection_file
        map(self._load_connection, parse_connection_file(self.connection_file, 'connection'))
        # bind the callback on every obj that has the #entry tag
        self.tree.tag_bind('#entry', '<<TreeviewSelect>>', self.click_connection)
    # END load_connection_file()

    def _load_connection(self, conn):
        """."""
        # add data to the tree
        self.tree.insert('', 'end', iid=conn[0], values=conn[1], tags='#entry')
    # END _load_connection()

    def click_connection(self, *args, **kwargs):
        """callback on click of row in tree."""
        iid = self.tree.focus()
        #print(iid)
        address = fetch_conn_val_by_iid(self.connection_file, iid, 'address')
        hostname = fetch_conn_val_by_iid(self.connection_file, iid, 'hostname')
        #print(socket.gethostbyaddr(address))
        #print(socket.gethostbyname_ex(hostname))

        if iid in self.master.children:
            # set focus to existing window
            self.master.children[iid].deiconify()
            self.master.children[iid].focus_set()
        else:
            ChatWindow(iid, hostname)
    # END click_connection()
# END ChatMain


class ChatWindow(tk.Toplevel):
    """Tkinter class used to build a GUI window."""
    width = 550
    height = 500
    def __init__(self, iid, hostname, *args, **kwargs):
        tk.Toplevel.__init__(self, name=iid, width=self.width, height=self.height, *args, **kwargs)
        self.iid = iid
        self.hostname = hostname
        self.title(self.hostname)
        self.resizable(0, 0) # not resizeable
        # populate display text window
        #  -self.master.display
        #  -self.master.display_scroll
        self.init_display()

        # populate input text window and button
        #  -self.master.input
        #  -self.master.input_scroll
        self.init_input()
        self.send = tk.Button(self, text='Send', width=15, height=1)
        #####
        # draw everything to screen
        # display
        # left and right padding
        self.spacer(self, row=0, column=0, rowspan=5, width=5)
        self.spacer(self, row=0, column=3, rowspan=5, width=5)
        # top padding
        self.spacer(self, row=0, column=1, columnspan=2, height=5)
        self.display.grid(sticky="we") # row=1, column=1 in init_display()
        self.display_sb.grid(row=1, column=2, sticky="ns")
        # middle spacer
        self.spacer(self, row=2, column=1, columnspan=2, height=10)
        # input
        self.input.grid(sticky="we") # row=3, column=1 in init_input()
        self.input_sb.grid(row=3, column=2, sticky="ns")
        self.spacer(self, row=4, column=1, columnspan=2, height=10)
        self.send.grid(row=5, column=1, sticky="e")
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

    def init_display(self):
        """Create the UI objects associated witht the chat display."""
        # create an outer Frame() object to control the Text() size based on pixels, not by font
        outer_frame = tk.Frame(self, width=520, height=270)
        outer_frame.grid(row=1, column=1)
        outer_frame.columnconfigure(0, weight=10)
        outer_frame.grid_propagate(False)
        self.display = tk.Text(outer_frame, state=tk.DISABLED, wrap=tk.WORD)
        # link the Scrollbar to Text
        self.display_sb = tk.Scrollbar(self, command=self.display.yview)
        self.display['yscrollcommand'] = self.display_sb.set
    # END init_display()

    def init_input(self):
        """Create the UI objects associated with the chat input window."""
        outer_frame = tk.Frame(self, width=520, height=160)
        outer_frame.grid(row=3, column=1)
        outer_frame.columnconfigure(0, weight=10)
        outer_frame.grid_propagate(False)
        self.input = tk.Text(outer_frame, wrap=tk.WORD)
        # link the Scrollbar to Text
        self.input_sb = tk.Scrollbar(self, command=self.input.yview)
        self.input['yscrollcommand'] = self.input_sb.set
    # END init_input()
# END ChatWindow


class ChatSocketServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class ChatRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        """When a connection is made on the open socket, accept and receive
           the message, appending to a single variable for its entirety
           (assumes data will always be str). Put tuple(addr, message) on the queue.
           Start listening for new connections again."""
        msg = ""
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            msg = msg + data
        self.queue.put_nowait((self.client_address, str(msg)))
        self.listen()
    # END serve()
# END ChatSocketServer


if __name__ == '__main__':
    ChatMain(r"C:\Workspace\Projects\SocketChat_project\connections.xml").mainloop()
