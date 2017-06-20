#!/usr/bin/env python3
"""
-tls/ssl
"""
import os
import time
import datetime
import ttk
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk
try:
    import tkfiledialog
except ImportError:
    import tkFileDialog as tkfiledialog
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
    title = 'Socket Chat'
    queue_listener_delay = 250
    def __init__(self, connection_file='', msg_queue=None, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.pack(expand=tk.YES, fill=tk.BOTH)

        self.master.title(self.title)
        # set frame resize priorities
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        # create the menu
        self.menu = tk.Menu(self)
        self.filemenu = tk.Menu(self.menu, tearoff=0)
        self.filemenu.add_command(label='Load Connection File', command=self.load_connection_file)
        self.menu.add_cascade(menu=self.filemenu, label='File')

        # create TreeView (TODO: would a simple Listbox be better?)
        self.tree = ttk.Treeview(self, columns='connections', show='', selectmode='browse')
        self.ysb = AutoScrollbar(self, command=self.tree.yview, orient=tk.VERTICAL)
        self.tree['yscroll'] = self.ysb.set

        # populate the connections
        if connection_file:
            self._load_connection_file(connection_file)

        if msg_queue and isinstance(msg_queue, queue.Queue()):
            self.queue = msg_queue

        self.master.config(menu=self.menu)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.ysb.grid(row=0, column=1, sticky="ns")
        # start listener for messages placed on queue
        self.queue_listener_ptr = self.master.after(self.queue_listener_delay, self._poll_queue)
    # END __init__()

    def load_connection_file(self):
        """Callable function, run from the menu, in order to assist user in selecting an xml file.
        Passes the file to _load_connection_file() to perform the logic of loading/refreshing the
        connections."""
        connection_file = tkfiledialog.askopenfilename(parent=self, title='Select Connection File',
                                                       defaultextension='.xml',
                                                       initialdir=os.path.abspath('.'))
        self._load_connection_file(connection_file)
    # END load_connection_file()

    def _load_connection_file(self, connection_file=''):
        """Called during __init__ and load_connection_file()."""
        #TODO: kill any existing ChatWindow. No longer guaranteed a ref to their connection info
        if connection_file != '':
            self.connection_file = connection_file
        # drop existing values in the tree if any
        if self.tree.get_children():
            [self.tree.delete(child) for child in self.tree.get_children()]
        # load new data to tree
        map(self._populate_tree, parse_connection_file(self.connection_file, 'connection'))
        # bind the callback on every obj that has the #entry tag
        self.tree.tag_bind('#entry', '<<TreeviewSelect>>', self._click_connection)
        #TODO: store all connections in python object lookup table (performance)
    # END _load_connection_file()

    def _populate_tree(self, conn):
        """Add data to the tree. Called from _load_connection_file()."""
        self.tree.insert('', 'end', iid=conn[0], values=conn[1], tags='#entry')
    # END _populate_tree()

    def _click_connection(self, *args, **kwargs):
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
    # END _click_connection()

    def _poll_queue(self):
        """Poll a queue until returns True. Pass message from queue to corresponding ChatWindow."""
        if hasattr(self, 'queue'):
            while not self.queue.empty():
                addr, msg = self.queue.get_nowait()
                #TODO: use lookup table to map addr to iid and push msg along
            # self.display_msg('{0}: '.format(CLIENT_HOST), 'hostname')
            # self.display_msg(msg)
            # #self.display_msg('{0}: {1}'.format(CLIENT_HOST, msg))
        self.queue_listener_ptr = self.master.after(self.queue_listener_delay, self._poll_queue)
    # END _poll_queue()
# END ChatMain


class ChatWindow(tk.Toplevel):
    """Tkinter class used to build a GUI window."""
    timestamp_fmt = '%a, %b %d, %Y %H:%M:%S'
    def __init__(self, iid, hostname, *args, **kwargs):
        tk.Toplevel.__init__(self, name=iid, *args, **kwargs)
        self.iid = iid
        self.hostname = hostname
        self.title(self.hostname)
        self.resizable(0, 0) # not resizeable
        self.current_local_msg = ""
        self.timestamp = time.strftime(self.timestamp_fmt)
        # populate display & input text window and Send button
        self.display = tk.Text(self, width=70, height=18, state=tk.DISABLED, wrap=tk.WORD)
        # link the Scrollbar to Text
        self.display_sb = AutoScrollbar(self, command=self.display.yview)
        self.display['yscrollcommand'] = self.display_sb.set
        self.input = tk.Text(self, width=70, height=10, wrap=tk.WORD)
        # link the Scrollbar to Text
        self.input_sb = AutoScrollbar(self, command=self.input.yview)
        self.input['yscrollcommand'] = self.input_sb.set
        self.send = tk.Button(self, text='Send', width=15, height=1,
                              command=self._display_local_msg)
        #####
        # text display tags - format how the text appears based on what generated the text
        self.display.tag_config('local', justify=tk.RIGHT)
        self.display.tag_config('error', foreground="red")
        self.display.tag_config('timestamp', justify=tk.CENTER, foreground="gray")
        self.display.tag_config('hostname', foreground="blue")
        #####
        # draw everything to screen
        # display
        # left and right padding
        self._spacer(self, row=0, column=0, rowspan=5, width=5)
        self._spacer(self, row=0, column=3, rowspan=5, width=5)
        # top padding
        self._spacer(self, row=0, column=1, columnspan=2, height=5)
        self.display.grid(row=1, column=1)
        self.display_sb.grid(row=1, column=2, sticky="ns")
        # middle spacer
        self._spacer(self, row=2, column=1, columnspan=2, height=10)
        # input
        self.input.grid(row=3, column=1)
        self.input_sb.grid(row=3, column=2, sticky="ns")
        self._spacer(self, row=4, column=1, columnspan=2, height=10)
        self.send.grid(row=5, column=1, sticky="e")
        self._spacer(self, row=6, column=1, columnspan=2, height=10)
        # on startup, write the initial timestamp
        self._display_msg('{0}\n'.format(self.timestamp), ('timestamp',))
    # END __init__()

    def _spacer(self, parent, **kwargs):
        """A convenience function to simplify creating spacers on UI objects.

           Required arguments: - parent widget
           Optional: - width, height, row, column, columnspan, rowspan, backgroundcolor, relief
           """
        row = kwargs.pop("row", 0)
        column = kwargs.pop("column", 0)
        columnspan = kwargs.pop("columnspan", 1)
        rowspan = kwargs.pop("rowspan", 1)
        spacer = tk.Frame(parent, kwargs)
        spacer.grid(row=row, column=column, columnspan=columnspan, rowspan=rowspan)
    # END _spacer()

    def _display_local_msg(self):
        """Store the characters currently in the input window. Send them to be displayed
           on the input window. Clear the input window."""
        self.current_local_msg = self.input.get(1.0, tk.END)
        self._display_msg(self.current_local_msg, ('local',))
        self.input.delete(1.0, tk.END)
    # END _display_local_msg()

    def _display_msg(self, msg, text_tags=None):
        """Write msg to chat display window.

        text_tags should be a tuple:
        ex: ('local',)"""
        #TODO: strip hanging newlines?
        self.display.config(state=tk.NORMAL)
        report_timestamp = self._report_update_timestamp()
        if report_timestamp is not None:
            self.display.insert(tk.END, '{0}\n'.format(report_timestamp), ('timestamp',))

        if text_tags is None:
            self.display.insert(tk.END, msg)
        else:
            self.display.insert(tk.END, msg, text_tags)
        self.display.config(state=tk.DISABLED)
        self.display.yview(tk.END)
    # END _display_msg()

    def _report_update_timestamp(self):
        """If current timestamp is older than 5 minutes,
           update to new time and print to display window.
           Called from within _display_msg()."""
        ret = None
        five_min_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
        if datetime.datetime.strptime(self.timestamp, self.timestamp_fmt) <= five_min_ago:
            ret = self.timestamp
            self.timestamp = time.strftime(self.timestamp_fmt)
        return ret
    # END _report_update_timestamp()
# END ChatWindow


if __name__ == '__main__':
    ChatMain(os.path.abspath("../connections.xml")).mainloop()
