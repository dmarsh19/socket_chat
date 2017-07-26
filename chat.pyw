#!/usr/bin/env python3
"""
-menu on ChatWindow. Add connection if not in config
-NewConnection user message if connection already exists
"""
import os
import time
import datetime
import socket
from uuid import uuid4
from threading import Thread
# performance using cElementTree in Python2 is worth the extra try:except
try: #python2
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET
try: # python3
    from queue import Queue
    from socketserver import ThreadingTCPServer, BaseRequestHandler
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog as tkfiledialog
    from tkinter import scrolledtext
except ImportError:
    from Queue import Queue
    from SocketServer import ThreadingTCPServer, BaseRequestHandler
    import Tkinter as tk
    import ttk
    import tkFileDialog as tkfiledialog
    import ScrolledText as scrolledtext


class ChatMain(ttk.Frame):
    """Starts the chat application, including:
    - List of hosts that can be messaged
    - read/write configuration
    - server to process incoming messages"""
    msg_queue = Queue()
    queue_listener_delay = 250 # ms
    def __init__(self, config_file_path="socketchat.xml", *args, **kwargs):
        ttk.Frame.__init__(self, name='chatmain', *args, **kwargs)
        self.grid() # The Frame fills tk.master. Following widgets are built within Frame.
        self.master.resizable(0, 0) # not resizeable
        self.master.title('Socket Chat')
        self.focus_force() # grab focus
        # create gui widgets
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(menu=filemenu, label='File')
        self.master.config(menu=menubar)
        self.tree = ttk.Treeview(self, show='tree', selectmode='browse')
        ysb = ttk.Scrollbar(self, command=self.tree.yview)
        self.tree['yscroll'] = ysb.set
        self.tree.grid()
        ysb.grid(row=0, column=1, sticky="ns")
        # initialize default config
        self.config = init_config()
        # load config file if exists, overwrite default config
        self.load_config(config_file_path)
        self.address = self.config.find('request_server').findtext('address')
        self.port = int(self.config.find('request_server').findtext('port'))
        # start listening for TCP connections
        request_server = ThreadingTCPServer((self.address, self.port), ChatRequestHandler)
        # can be called using self.server.queue from inside ChatRequestHandler class
        request_server.queue = self.msg_queue
        request_server_thread = Thread(target=request_server.serve_forever)
        # if main thread is closed, exit all other threads
        request_server_thread.daemon = True
        request_server.daemon_threads = True
        request_server_thread.start()
        # add menu commands after self.config exists
        filemenu.add_command(label='Load Configuration', command=self.load_config)
        filemenu.add_command(label='Add Connection', command=lambda: NewConnection(self.config))
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.close)
        # start listener for messages placed on queue
        self.queue_listener_ptr = self.after(self.queue_listener_delay, self._poll_queue)
        # callback for closing window
        self.master.protocol('WM_DELETE_WINDOW', self.close)
    # END __init__()

    def load_config(self, config_file_path=None):
        """Callable function, run from the menu, in order to assist user in selecting an xml file.
        Passes the file to perform the logic of loading/refreshing the connections.
        -config_file_path=None: 'Load Configuration' was called from ChatMain menu. Prompt user to
          select file. Try to load if selected. If cancel selection, do nothing."""
        if not config_file_path:
            filetypes = (("All types", "*.*"), ("eXtensible Markup Language file", "*.xml"))
            config_file_path = tkfiledialog.askopenfilename(parent=self, filetypes=filetypes,
                                                            title='Load Configuration',
                                                            defaultextension=".xml",
                                                            initialdir=os.path.abspath('.'))
        # if user cancels selecting a file, config_file_path still empty.
        # No more logic so we don't wipe out any existing connections.
        if config_file_path:
            try:
                _tree = ET.parse(config_file_path)
                if ET.iselement(_tree.getroot()): # valid xml element from file
                    self.config_file_path = config_file_path
                    self.config = _tree
            except (IOError, ET.ParseError): # non-existent file
                self.config_file_path = config_file_path

            # kill existing ChatWindow(s) if connections not in new config.
            # No longer guaranteed reference to their connection info.
            # use list of widget names, do not destroy directly from iter.
            for iid in [i for i in self.master.children]:
                if iid != 'chatmain' and iid not in [j.get('id') for j in self.config.iter('connection')]:
                    self.master.children[iid].destroy()
            # drop existing values in the tree if any
            # * - splat operator; i.e. 'unpacking argument lists'
            self.tree.delete(*self.tree.get_children())
            # load new data to tree
            [self.populate_connection(i) for i in self.config.iter('connection')]
    # END load_config()

    def populate_connection(self, conn_elem):
        """Add connections to ui tree. Add mapping of address to iid in lookup dict."""
        self.tree.insert('', 'end', iid=conn_elem.get('id'),
                         text=conn_elem.findtext('displayname'), tags='#entry')
        # bind the callback on every obj that has the #entry tag
        self.tree.tag_bind('#entry', '<<TreeviewSelect>>', self._click_connection)
    # END populate_connection()

    def _click_connection(self, *args, **kwargs):
        """callback on click of row in tree."""
        iid = self.tree.focus()
        if iid in self.master.children:
            # set focus to existing window
            self.master.children[iid].deiconify()
            self.master.children[iid].focus_set()
        else:
            conn_elem = self.config.find(".//connection[@id='{}']".format(iid))
            if conn_elem is not None:
                displayname = conn_elem.findtext('displayname')
                address = conn_elem.findtext('address')
                ChatWindow(iid, displayname, address, self.port)
    # END _click_connection()

    def _poll_queue(self):
        """Poll a queue.Queue() until returns True. Pass message from queue to
        ChatWindow based on addr.

        1. Try to retrieve connection id from config using addr.
            a. if not found, assign addr as id
        2. Check if ChatWindow with matching id is already open.
            a. if not open, use id to retrieve displayname from config.
                i. if no match in config, socket call for displayname.
            b. Spawn new ChatWindow."""
        while not self.msg_queue.empty():
            addr, msg = self.msg_queue.get_nowait()
            # Try to retrieve connection id from config using addr
            conn_elem = self.config.find(".//connection[address='{}']".format(addr))
            if conn_elem is not None:
                iid = conn_elem.get('id')
            else: # id not found, assign addr as id
                # tkinter uses 'dot' naming convention to signify ancestry of widgets.
                # thus, we can't leave the addr in the standard format.
                iid = addr.replace('.', '-')
            # Check if ChatWindow with matching id is already open
            try:
                chat_window = self.master.children[iid]
            except KeyError: # window not open, use id to retrieve displayname from config
                conn_elem = self.config.find(".//connection[@id='{}']".format(iid))
                if conn_elem is not None:
                    displayname = conn_elem.findtext('displayname')
                else: # no match in config, socket call for displayname
                    displayname = socket.getfqdn(addr).split('.')[0]
                # Spawn new ChatWindow
                chat_window = ChatWindow(iid, displayname, addr, self.port)
            chat_window.display_msg('{}:'.format(chat_window.displayname), ('displayname',))
            chat_window.display_msg(msg)
        self.queue_listener_ptr = self.after(self.queue_listener_delay, self._poll_queue)
    # END _poll_queue()

    def close(self):
        """Callback on window close to write config to file if there are connections."""
        if hasattr(self, 'config_file_path'):
            if self.config.findall('connection'):
                self.config.write(self.config_file_path, "UTF-8", True)
        self.master.destroy()
    # END close()
# END ChatMain


class ChatWindow(tk.Toplevel):
    """Tkinter UI chat window with a single client."""
    timestamp_fmt = '%a, %b %d, %Y %H:%M:%S'
    def __init__(self, iid, displayname, address, port, *args, **kwargs):
        tk.Toplevel.__init__(self, name=iid, *args, **kwargs)
        self.resizable(0, 0) # not resizeable
        self.focus_force()
        self.displayname = displayname
        self.title(self.displayname)
        self.address = address
        self.port = port
        self.current_local_msg = ""
        self.timestamp = time.strftime(self.timestamp_fmt)
        # populate widgets
        # ttk.Frame gets the default OS colors correct on MacOS
        background_frame = ttk.Frame(self)
        background_frame.grid()
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(menu=filemenu, label='File')
        #TODO: pass params to NewConnection
        #filemenu.add_command(label="Add Connection")#, command=lambda: NewConnection(self.config))
        filemenu.add_separator()
        filemenu.add_command(label="Close", command=self.destroy)
        self.config(menu=menubar)
        self.display = scrolledtext.ScrolledText(background_frame, height=18, borderwidth=2,
                                                 relief=tk.SUNKEN, state=tk.DISABLED, wrap=tk.WORD)
        self.input = scrolledtext.ScrolledText(background_frame, height=10, wrap=tk.WORD,
                                               borderwidth=2, relief=tk.SUNKEN)
        send_button = ttk.Button(background_frame, text='Send', width=15,
                                 command=self.send_and_display_msg)
        # text display tags - format how the text appears based on what generated the text
        self.display.tag_config('local', justify=tk.RIGHT)
        self.display.tag_config('error', foreground="red")
        self.display.tag_config('timestamp', justify=tk.CENTER, foreground="gray")
        self.display.tag_config('displayname', foreground="blue")
        # draw everything to screen
        self.display.grid()
        self.input.grid()
        send_button.grid(sticky="e")
        # on startup, write the initial timestamp
        self.display_msg(self.timestamp, ('timestamp',))
        # bind Enter to Send button and Shift-Enter to place newline
        self.bind('<Return>', self.send_and_display_msg)
        self.bind('<Shift-Return>', lambda e: "break")
    # END __init__()

    def _fetch_local_msg(self):
        """If there are characters in the input window, send them to the display window.
        Clear the input window. Return True if characters existed, else False."""
        ret = False
        self.current_local_msg = self.input.get(1.0, tk.END).strip('\n')
        if self.current_local_msg:
            ret = True
            self.display_msg(self.current_local_msg, ('local',))
            self.input.delete(1.0, tk.END)
        return ret
    # END _fetch_local_msg()

    def display_msg(self, msg, text_tags=None):
        """Write msg to chat display window.

        text_tags should be a tuple:
        ex: ('local',)"""
        self.display.config(state=tk.NORMAL)
        report_timestamp = self._report_update_timestamp()
        if report_timestamp is not None:
            self.display.insert(tk.END, '{}\n'.format(report_timestamp), ('timestamp',))
        if text_tags is None:
            self.display.insert(tk.END, '{}\n'.format(msg))
        else:
            self.display.insert(tk.END, '{}\n'.format(msg), text_tags)
        self.display.config(state=tk.DISABLED)
        self.display.yview(tk.END)
    # END display_msg()

    def send_and_display_msg(self, *args, **kwargs):
        """Displays the local message from the input window to the display window and
        sends the message through a socket."""
        if self._fetch_local_msg():
            # send to socket. If no server on other end, notify unavailable.
            if not socket_send_msg(self.address, self.port, self.current_local_msg):
                self.display_msg('[user is unavailable]', ('error',))
    # END send_and_display_msg()

    def _report_update_timestamp(self):
        """If current timestamp is older than 5 minutes, update to new time and
        print to display window. Called from within display_msg()."""
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
    def __init__(self, config_xml_tree, *args, **kwargs):
        tk.Toplevel.__init__(self, name='newconnection', *args, **kwargs)
        self.resizable(0, 0) # not resizeable
        self.title('Add Connection')
        self.focus_force()
        self.config = config_xml_tree
        self.hostname = tk.StringVar()
        self.displayname = tk.StringVar()
        self.address = tk.StringVar()
        # create the UI objects
        background_frame = ttk.Frame(self)
        background_frame.grid()
        ttk.Label(background_frame, text="hostname").grid()
        ttk.Entry(background_frame, textvariable=self.hostname, width=25).grid(row=0, column=1)
        ttk.Label(background_frame, text="displayname").grid()
        ttk.Entry(background_frame, textvariable=self.displayname, width=25).grid(row=1, column=1)
        ttk.Label(background_frame, text="address").grid()
        ttk.Entry(background_frame, textvariable=self.address, width=25).grid(row=2, column=1)
        button_frame = ttk.Frame(background_frame) # additional frame to center buttons
        self.lookup_button = ttk.Button(button_frame, text="address lookup", width=15,
                                        command=lambda: self.address.set(socket.gethostbyname(self.hostname.get())))
        self.lookup_button.state(['disabled'])
        self.add_button = ttk.Button(button_frame, text="Add", width=10, command=self._add)
        self.add_button.state(['disabled'])
        self.lookup_button.grid()
        self.add_button.grid(row=0, column=1)
        button_frame.grid(columnspan=2)
        # start the listener to check if fields are populated
        self._listener()
    # END __init__()

    def _listener(self):
        """check if the fields are populated before buttons are active."""
        if self.hostname.get():
            self.lookup_button.state(['!disabled'])
        else:
            self.lookup_button.state(['disabled'])
        if self.hostname.get() and self.displayname.get() and self.address.get():
            # bind Enter to Add button
            self.bind('<Return>', self._add)
            self.add_button.state(['!disabled'])
        else:
            self.unbind('<Return>')
            self.add_button.state(['disabled'])
        self.after(self.listener_delay, self._listener)
    # END _listener()

    def _add(self, *args, **kwargs):
        """callback for Add button."""
        # parse the xml to see if a connection with same address already exists
        conn_elem = self.config.find(".//connection[address='{}']".format(self.address.get()))
        if conn_elem is None: #TODO: notify user of existing connection
            new_conn_elem = create_elem_with_subs(self.config.getroot(), 'connection',
                                                  {'id': str(uuid4())},
                                                  {'hostname': self.hostname.get().upper(),
                                                   'displayname': self.displayname.get(),
                                                   'address': self.address.get()})
            self.master.children['chatmain'].populate_connection(new_conn_elem)
        self.destroy()
    # END _add()
# END NewConnection


class ChatRequestHandler(BaseRequestHandler):
    """Called from ThreadingTCPServer.

    Requires assigning a queue.Queue() to self.queue after instantiation."""
    def handle(self):
        """Receive a message from a socket connection and put tuple(addr, message) on a queue."""
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
    """Send a message through a socket to a host. If failed, return False."""
    ret = True # assume success
    if msg:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((address, port))
            sock.sendall(str(msg).encode())
            sock.close()
        except socket.error:
            ret = False
    return ret
# END socket_send_msg()


def init_config():
    """Write a default xml configuration tree to memory."""
    tree = ET.ElementTree(ET.Element('socketchat'))
    create_elem_with_subs(tree.getroot(), 'request_server',
                          grandchild_elem_dict={'address': "", 'port': "12141"})
    return tree
# END init_config()


def create_elem_with_subs(parent_elem, child_tag, attrib_dict={}, grandchild_elem_dict={}):
    """Extends the functionality of Element or SubElement to also create additional sub elements
    from a dictionary."""
    child_elem = ET.SubElement(parent_elem, child_tag, attrib_dict)
    for i in grandchild_elem_dict:
        grandchild_elem = ET.SubElement(child_elem, i)
        grandchild_elem.text = grandchild_elem_dict[i]
    return child_elem
# END create_elem_with_subs()


if __name__ == '__main__':
    ChatMain().mainloop()
