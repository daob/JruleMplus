#!/usr/bin/env python

import sys, os
try:
    import pygtk
    pygtk.require("2.0")
except:
    pass
try:
    import gtk
    import gtk.glade
    from MplusOutput import MplusOutput
except:
    sys.exit(1)

def jpaste(number, digits=3):
    """Utility function to write a floating point number to text"""
    return "%1.3f" % float(number)


class JruleGTK:
    """Graphical user interface for the SQP compare function using 
       GTK+ and Glade."""

    def __init__(self):
        self.filename = '' # The file to be read

        #Set the Glade file
        self.gladefile = "JruleMplus.glade"  
        self.tree = gtk.glade.XML(self.gladefile) 

        # Get various widgets necessary later
        self.window = self.tree.get_widget("main_window")
        self.aboutbox = self.tree.get_widget("about")
        self.statusbar = self.tree.get_widget("statusbar")
        self.filechooser = self.tree.get_widget("filechooser")
        self.treeview = TreeView(self)# see ItemList class below
        self.messager = Messager(self)
        
        self.update_status() # show current file in status bar
        
        # connect widget signals to class functions
        self.window.connect("destroy", gtk.main_quit)

        dic = { "on_window_destroy" : gtk.main_quit,
                "on_quit_mi_activate" :gtk.main_quit,
                "on_about_mi_activate" : self.show_about,
                "on_filechooser_file_set" : self.set_file,
                "on_about_response" : self.about_response,
        }
        self.tree.signal_autoconnect(dic) 
        self.window.show()

    def jpaste(self, number):
        """Utility function to write a floating point number to text"""
        return eval("\%1." + self.digits + "f") % float(number)

    def set_file(self, filechooser):
        self.filename = filechooser.get_filename()
        sys.stderr.write("File chosen is %s.\n" % self.filename)
        self.update_status()
        self.reload()
    
    def reload(self):
        try:
            self.output = MplusOutput(self.filename)
            self.estimates = self.output.get_estimates()
        except:
            self.messager.display_message('A problem occurred trying to read ' + 
                '%s as an Mplus output file.' % self.filename +
                ' Please make sure you have selected the right file.')
            self.filename = ''# Undo filename setting
            #filechooser.set_filename(None) # How to do this
            return
        # If all went well, put the items found into the treeview
        self.treeview.populate_tree()

    def update_status(self, context_id=0):
        if self.filename:
            msg = "The current output file is '%s'. Click to select the items."\
                 % self.filename
        else:
            msg = "Please click the file selection button on the left to"+\
                  " select an output file."
        self.statusbar.push(context_id, msg)

    def show_about(self, about_mi):
        sys.stderr.write("Show about box\n")
        self.aboutbox.run() 

    def about_response(self, aboutbox, signal):
        sys.stderr.write("Received signal %d from about box\n" % signal)
        if signal < 0:
            aboutbox.hide()

    def compare(self):
        sys.stderr.write("Compare flare:\n")


class TreeView:
    """Class representing the list of parameters."""
    def __init__(self, application):
        self.treeview = application.tree.get_widget("treeview")
        self.application = application
        self.init_treeview()

    def append_columns(self, titles, type='text', column_id=0):
        """Helper function that appends new column to the treeview. 
           Takes tuple of titles and one type that must be equal for all.
           The column id is set automatically and needn't be explicitly used"""
        for title in titles:
            cell = gtk.CellRendererText()
            col = gtk.TreeViewColumn(title)
            col.pack_start(cell, True)
            col.set_sort_column_id(column_id)
            col.add_attribute(cell, 'text', column_id)
            self.treeview.append_column(col)
            column_id += 1 # default arguments are static!
        
    def init_treeview(self):
        sys.stderr.write("Initialising the item list (gtk.TreeView)\n")

        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.treestore = gtk.TreeStore(str,str,str,str,str,str,str)

        self.append_columns(('Parameter', 'Group', 'Decision', 
                            'MI', 'EPC', 'Power', 'NCP'))

        self.treemodelfilter = self.treestore.filter_new(root=None)
        self.treemodelsort = gtk.TreeModelSort(self.treemodelfilter)
        self.treeview.set_model(self.treemodelsort)

    def populate_tree(self):
        """Uses MplusOutput class linked to the parent application
           to get the results and decision rules for the file."""
#        self.treeview.get_model().clear()
        if self.application.output:
            mi_dict = self.application.output.get_modindices()
            for parameter, result in mi_dict.iteritems():
                for group, values in result.iteritems():
                    self.treestore.append( None, (parameter, str(group), '-', 
                        jpaste(values[0]), jpaste(values[1]), 
                        jpaste(values[-1]), jpaste(values[-2])) )


class Messager:
    def __init__(self, app):
        self.dialog = app.tree.get_widget('messagedialog')

    def display_message(self, message):
        self.dialog.set_markup(message)
        response = self.dialog.run()
        self.dialog.hide()

if __name__ == "__main__":
    app = JruleGTK()
    gtk.main()
