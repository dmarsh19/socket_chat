"""
.
"""
import os
import uuid
import xml.etree.ElementTree as et


def fetch_xmlfile_root(xmlfile_path):
    """Return the root (top level Element) of an xml file. If failed, return None."""
    root = None
    if xmlfile_path and os.path.isfile(xmlfile_path):
        try:
            tree = et.parse(xmlfile_path)
            root = tree.getroot()
        except:
            pass
    return root
# END fetch_xmlfile_root()


def xml_iter_by_tag(xmlfile_path, tag):
    """Return an iterator of all elements in the xml file of a specified tag.

    Ex:
    <garage>
        <car>
            <model>Honda</model>
        </car>
        <car>
            <model>Toyota</model>
        </car>
    </garage>

    xml_iter_by_tag('garage.xml', 'car') => iter(<Element(car)>, <Element(car)>)
    """
    root = fetch_xmlfile_root(xmlfile_path)
    if root:
        return root.iter(tag)
# END xml_iter_by_tag()


def parse_connection_file(xmlfile_path, tag):
    """."""
    # [(connection.id, connection.displayname), (connection.id, connection.displayname), ...]
    return map(_parse_connection_elem, xml_iter_by_tag(xmlfile_path, tag))
# END parse_connections_xml()


def _parse_connection_elem(conn_elem):
    """From a 'connection' xml element, return a tuple(connection.id, connection.displayname)"""
    return (conn_elem.get('id'), conn_elem.find('displayname').text)
# END _parse_connection_elem()


def add_connection():
    """."""
    print(uuid.uuid4())
    pass
# END add_connection()


def fetch_conn_val_by_iid(connection_file, iid, tagname):
    """."""
    conn_val = None
    root = fetch_xmlfile_root(connection_file)
    conn_elem = root.find(".//connection[@id='{}']".format(iid))
    if conn_elem:
        conn_val = conn_elem.find(tagname).text
    return conn_val
# END fetch_conn_val_by_iid()


if __name__ == '__main__':
    pass
