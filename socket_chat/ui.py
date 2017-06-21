#!/usr/bin/env python3
"""
"""
import os
import time
import datetime
import socket
try:
    import ttk
except ImportError:
    from tkinter import ttk
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk
try:
    from tkinter import filedialog as tkfiledialog
except ImportError:
    import tkFileDialog as tkfiledialog
try:
    import Queue as queue
except ImportError:
    import queue

from socket_chat.connections import xml_iter_by_tag, xml_add_connection, fetch_conn_val_by_iid
from socket_chat.servers import socket_send_msg


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

def _spacer(parent, **kwargs):
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


class ChatMain(tk.Frame):
    """."""
    title = 'Socket Chat'
    queue_listener_delay = 250 # ms
    def __init__(self, connection_file='', msg_queue=None, *args, **kwargs):
        tk.Frame.__init__(self, name='chatmain', *args, **kwargs)
        self.pack(expand=tk.YES, fill=tk.BOTH)

        self.master.title(self.title)
        # set frame resize priorities necessary for AutoScrollbar
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        # create the menu
        self.menu = tk.Menu(self)
        self.filemenu = tk.Menu(self.menu, tearoff=0)
        self.filemenu.add_command(label='Load Connection File', command=self.load_connection_file)
        # in load_connection_file(), enable and add command once we have a valid connection file
        self.filemenu.add_command(label='New Connection', state=tk.DISABLED)
        self.menu.add_cascade(menu=self.filemenu, label='File')

        # create TreeView (TODO: would a simple Listbox be better?)
        self.tree = ttk.Treeview(self, columns='connections', show='', selectmode='browse')
        self.ysb = AutoScrollbar(self, command=self.tree.yview, orient=tk.VERTICAL)
        self.tree['yscroll'] = self.ysb.set

        # populate the connections
        if connection_file:
            self.load_connection_file(connection_file)

        if msg_queue:
            self.poll_queue(msg_queue)

        self.master.config(menu=self.menu)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.ysb.grid(row=0, column=1, sticky="ns")
    # END __init__()

    def load_connection_file(self, connection_file=''):
        """Callable function, run from the menu, in order to assist user in selecting an xml file.
        Passes the file to load_connection_file() to perform the logic of loading/refreshing the
        connections."""
        if connection_file == '':
            #self.filemenu.entryconfig(1, state=tk.DISABLED) #TODO: get index by command name?
            connection_file = tkfiledialog.askopenfilename(parent=self, title='Select Connection File',
                                                        filetypes=(("All types", "*.*"),
                                                                    ("eXtensible Markup Language file", "*.xml")),
                                                        defaultextension=".xml",
                                                        initialdir=os.path.abspath('.'))
            # if user cancels on selecting a file, escape this function so we don't
            # wipe out existing connections (if any)properties
            if not connection_file:
                return
        # bad file path
        elif not (connection_file or os.path.isfile(connection_file)):
            return

        self.connection_file = connection_file
        #TODO: get index by command name?
        self.filemenu.entryconfig(1, state=tk.NORMAL, command=lambda: NewConnection(self.connection_file))
        self.connections_by_address = {}
        self.connections_by_iid = {}
        # kill existing ChatWindow(s). No longer guaranteed a reference to their connection info.
        # get a set of the widget names. trying to destroy() while looping fails.
        for name in set(self.master.children):
            if name != 'chatmain':
                self.master.children[name].destroy()
        # drop existing values in the tree if any
        for child in self.tree.get_children():
            self.tree.delete(child)
        # load new data to tree
        try:
            #TODO: this map() call works in 2.7, not in 3
            #map(self._populate_connections, xml_iter_by_tag(self.connection_file, 'connection'))
            for conn_elem in xml_iter_by_tag(self.connection_file, 'connection'):
                self._populate_connections(conn_elem)
            # bind the callback on every obj that has the #entry tag
            self.tree.tag_bind('#entry', '<<TreeviewSelect>>', self._click_connection)
        except TypeError:
            pass # no elements in iterator (empty file or bad xml or not xml file)
    # END load_connection_file()

    def _populate_connections(self, conn_elem):
        """Add connections to ui tree. Create two lookup dicts to map address to iid and vice versa.
        Called from load_connection_file()."""
        self.tree.insert('', 'end', iid=conn_elem.get('id'),
                         values=conn_elem.find('displayname').text, tags='#entry')
        # store all connections in python object lookup table (performance)
        #TODO: better python data structure to store xml
        self.connections_by_address[conn_elem.find('address').text] = conn_elem.get('id')
        self.connections_by_iid[conn_elem.get('id')] = conn_elem.find('address').text
    # END _populate_connections()

    def _click_connection(self, *args, **kwargs):
        """callback on click of row in tree."""
        iid = self.tree.focus()
        if iid in self.master.children:
            # set focus to existing window
            self.master.children[iid].deiconify()
            self.master.children[iid].focus_set()
        else:
            #TODO: better python data structure to store xml and get rid of this
            hostname = fetch_conn_val_by_iid(self.connection_file, iid, 'hostname')
            address = fetch_conn_val_by_iid(self.connection_file, iid, 'address')
            ChatWindow(iid, hostname, address)
    # END _click_connection()

    def poll_queue(self, msg_queue=None):
        """Callable function to hook to a queue and begin polling."""
        if msg_queue and isinstance(msg_queue, queue.Queue):
            self.msg_queue = msg_queue
        # start listener for messages placed on queue
        self.queue_listener_ptr = self.after(self.queue_listener_delay, self._poll_queue)
    # END poll_queue()

    def _poll_queue(self):
        """Poll a queue until returns True. Pass message from queue to corresponding ChatWindow."""
        while not self.msg_queue.empty():
            addr, msg = self.msg_queue.get_nowait()
            self.master.children[self.connections_by_address[addr]].display_msg(msg)
            #TODO: prefix display name in ChatWindow()
        # self.display_msg('{0}: '.format(CLIENT_HOST), 'hostname')
        # self.display_msg(msg)
        # #self.display_msg('{0}: {1}'.format(CLIENT_HOST, msg))
        self.queue_listener_ptr = self.after(self.queue_listener_delay, self._poll_queue)
    # END _poll_queue()
# END ChatMain


class ChatWindow(tk.Toplevel):
    """Tkinter UI chat window with a single client."""
    timestamp_fmt = '%a, %b %d, %Y %H:%M:%S'
    def __init__(self, iid, hostname, address, *args, **kwargs):
        tk.Toplevel.__init__(self, name=iid, *args, **kwargs)
        self.iid = iid
        self.hostname = hostname
        self.address = address
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
                              command=self.send_and_display_msg)
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
        _spacer(self, row=0, column=0, rowspan=5, width=5)
        _spacer(self, row=0, column=3, rowspan=5, width=5)
        # top padding
        _spacer(self, row=0, column=1, columnspan=2, height=5)
        self.display.grid(row=1, column=1)
        self.display_sb.grid(row=1, column=2, sticky="ns")
        # middle spacer
        _spacer(self, row=2, column=1, columnspan=2, height=10)
        # input
        self.input.grid(row=3, column=1)
        self.input_sb.grid(row=3, column=2, sticky="ns")
        _spacer(self, row=4, column=1, columnspan=2, height=10)
        self.send.grid(row=5, column=1, sticky="e")
        _spacer(self, row=6, column=1, columnspan=2, height=10)
        # on startup, write the initial timestamp
        self.display_msg('{0}\n'.format(self.timestamp), ('timestamp',))
    # END __init__()

    def _display_local_msg(self):
        """Store the characters currently in the input window. Send them to be displayed
           on the input window. Clear the input window."""
        self.current_local_msg = self.input.get(1.0, tk.END)
        self.display_msg(self.current_local_msg, ('local',))
        self.input.delete(1.0, tk.END)
    # END _display_local_msg()

    def display_msg(self, msg, text_tags=None):
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
    # END display_msg()

    def send_and_display_msg(self, *args, **kwargs):
        """Displays the local message from the input window to the display window and
        sends the message through a socket."""
        self._display_local_msg()
        # send to socket. If no server on other end, notify unavailable.
        try:
            #TODO: hardcoded port
            socket_send_msg(self.address, 12141, self.current_local_msg)
        except socket.error:
            self.display_msg('[user is unavailable]\n', ('error',))
# END send_and_display_msg()

    def _report_update_timestamp(self):
        """If current timestamp is older than 5 minutes,
           update to new time and print to display window.
           Called from within display_msg()."""
        ret = None
        five_min_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
        if datetime.datetime.strptime(self.timestamp, self.timestamp_fmt) <= five_min_ago:
            self.timestamp = time.strftime(self.timestamp_fmt)
            ret = self.timestamp
        return ret
    # END _report_update_timestamp()
# END ChatWindow


class NewConnection(tk.Toplevel):
    """Tkinter UI popup to add connection to xml."""
    listener_delay = 250 # ms
    def __init__(self, connection_file, *args, **kwargs):
        tk.Toplevel.__init__(self, name='newconnection', *args, **kwargs)
        self.title('New Connection')
        self.resizable(0, 0) # not resizeable
        self.connection_file = connection_file
        self.hostname = tk.StringVar()
        self.displayname = tk.StringVar()
        self.address = tk.StringVar()
        # grab focus and bind Enter to submit button
        self.focus_force()
        # create the UI objects
        tk.Label(self, text="hostname").grid(row=0)
        tk.Entry(self, bd=2, textvariable=self.hostname, width=25).grid(row=0, column=1)
        tk.Label(self, text="displayname").grid(row=1)
        tk.Entry(self, bd=2, textvariable=self.displayname, width=25).grid(row=1, column=1)
        tk.Label(self, text="address").grid(row=2)
        tk.Entry(self, bd=2, textvariable=self.address, width=25).grid(row=2, column=1)
        button_frame = tk.Frame(self) # additional frame to center buttons
        self.lookup_button = tk.Button(button_frame, text="address lookup", width=13, state=tk.DISABLED,
                                       command=lambda: self.address.set(socket.gethostbyname(self.hostname.get())))
        self.add_button = tk.Button(button_frame, text="Add", width=10, state=tk.DISABLED,
                                    command=self._add)
        self.lookup_button.grid(row=0)
        _spacer(button_frame, width=5, row=0, column=1)
        self.add_button.grid(row=0, column=2)
        button_frame.grid(row=3, columnspan=2)
        # start the listener to check if fields are populated
        self.listener()
    # END __init__()

    def listener(self):
        """check if the fields are populated before buttons are active."""
        if self.hostname.get():
            self.lookup_button.config(state=tk.NORMAL)
        else:
            self.lookup_button.config(state=tk.DISABLED)
        if self.hostname.get() and self.displayname.get() and self.address.get():
            self.bind('<Return>', self._add)
            self.add_button.config(state=tk.NORMAL)
        self.after(self.listener_delay, self.listener)
    # END listener()

    def _add(self, *args, **kwargs):
        """callback for Add button."""
        # parse the xml to see if a connection with same hostname and/or address already exists
        try:
            for conn_elem in xml_iter_by_tag(self.connection_file, 'connection'):
                print(conn_elem.find('address').text)
                if (conn_elem.find('address').text == self.address.get() or
                        conn_elem.find('hostname').text == self.hostname.get().upper()):
                    self.destroy() #TODO: notify user of existing connection
                    return
        except TypeError:
            pass
        xml_add_connection(self.connection_file, {'hostname': self.hostname.get().upper(),
                                                  'displayname': self.displayname.get(),
                                                  'address': self.address.get()})
        #TODO: accessing a private class method outside of the class
        self.master.children['chatmain'].load_connection_file(self.connection_file)
        self.destroy()
    # END _add()
# END NewConnection


if __name__ == '__main__':
    ChatMain(os.path.abspath("../connections.xml")).mainloop()
