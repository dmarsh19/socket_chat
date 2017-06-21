"""
"""
import os
import uuid
import xml.etree.ElementTree as et


def fetch_xmlfile_tree(xmlfile_path):
    """Return the ElementTree of an xml file. If failed, return None."""
    tree = None
    if xmlfile_path and os.path.isfile(xmlfile_path):
        try:
            tree = et.parse(xmlfile_path)
        except:
            pass
    return tree
# END fetch_xmlfile_tree()


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

    xml_iter_by_tag('garage.xml', 'car') => iter((<Element(car)>, <Element(car)>))
    """
    elem_iter = None
    tree = fetch_xmlfile_tree(xmlfile_path)
    if tree:
        elem_iter = tree.iter(tag)
    return elem_iter
# END xml_iter_by_tag()


def xml_add_connection(xmlfile_path, sub_elem_dict):
    """."""
    tree = fetch_xmlfile_tree(xmlfile_path)
    if tree:
        conn_elem = et.SubElement(tree.getroot(), 'connection', {'id': str(uuid.uuid4())})
        for sub in sub_elem_dict:
            sub_elem = et.SubElement(conn_elem, sub)
            sub_elem.text = sub_elem_dict[sub]
        tree.write(xmlfile_path, "utf-8", True)
# END xml_add_connection()


def fetch_conn_val_by_iid(connection_file, iid, tagname):
    """."""
    conn_val = None
    tree = fetch_xmlfile_tree(connection_file)
    if tree:
        conn_elem = tree.find(".//connection[@id='{}']".format(iid))
        if conn_elem:
            conn_val = conn_elem.find(tagname).text
    return conn_val
# END fetch_conn_val_by_iid()


if __name__ == '__main__':
    pass
