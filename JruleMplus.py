#!/usr/bin/env python

import sys, os, re
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


# Quick and dirty fix to display numbers in treeview str columns
# TODO: refactor treeview to have float columns
def jpaste(number, digits=3):
    """Utility function to write a floating point number to text"""
    return "%1.3f" % float(number)

# Regular expressions to validate user input in delta and alpha fields
valid_alpha = re.compile(r'^[ \t]*0*\.[0-9]+[ \t]*$')
valid_delta = re.compile(r'^[ \t]*[0-9]*\.[0-9]+[ \t]*$')


class JruleGTK:
    """Graphical user interface for the MplusOutput class using 
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
        self.alpha_entry = self.tree.get_widget("alpha_entry")
        self.delta_entry = self.tree.get_widget("delta_entry")
        self.treeview = TreeView(self)# see ItemList class below
        self.messager = Messager(self)
        self.combo_parameter = ComboBox('combo_parameter', self, ['BY', 'ON', 'WITH'])
        self.combo_group = ComboBox('combo_group', self, [])
        self.combo_decision = ComboBox('combo_decision', self, ['Misspecified', 'Not misspecified', 
            'Check EPC', 'Not enough information'])
        
        self.update_status() # show current file in status bar
        
        # connect widget signals to class functions
        self.window.connect("destroy", gtk.main_quit)

        dic = { "on_window_destroy" : gtk.main_quit,
                "on_quit_mi_activate" :gtk.main_quit,
                "on_about_mi_activate" : self.show_about,
                "on_filechooser_file_set" : self.set_file,
                "on_about_response" : self.about_response,
                "on_delta_entry_changed" : self.reload,
                "on_alpha_entry_changed" : self.reload,
        }
        self.tree.signal_autoconnect(dic) 
        self.window.show()

    def jpaste(self, number):
        """Utility function to write a floating point number to text.
           Currently not yet in use."""
        return eval("\%1." + self.digits + "f") % float(number)

    def set_file(self, filechooser):
        """Given the user's choice of file, save this data and reload the list."""
        self.filename = filechooser.get_filename()
        sys.stderr.write("File chosen is %s.\n" % self.filename)
        self.update_status()
        if not self.reload():
            self.messager.display_message('A problem occurred trying to read ' + 
                '%s as an Mplus output file.' % self.filename +
                ' Please make sure you have selected the right file.')
    
    def reload(self, *args):
        """Reload the list using the MplusOutput class. Might be used as a callback
           so has variable number of arguments."""
        try:
            self.output = MplusOutput(self.filename)
            self.estimates = self.output.get_estimates()
        except Exception, e:
            sys.stderr.write('Could not reload application: %s\n'%str(e))
            self.filename = ''# Undo filename setting
            #filechooser.set_filename(None) # How to do this
            return False
        # If all went well, put the items found into the treeview
        self.treeview.populate_tree()
        return True

    def update_status(self, context_id=0):
        """Displays a text in the status bar showing the file currently in use."""
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
        if signal < 0: aboutbox.hide()

    def get_delta(self):
        "Check user input and return chosen delta value"
        error = ''
        value = self.delta_entry.get_text()
        sys.stderr.write('Getting delta, value is %s.\n'%value)
        try:
            float(value)
        except ValueError, e:
            error = str(e)
        if not valid_delta.match(value):
            error = 'Value does not match validation criteria.'
        if error:
            self.error('Please enter a valid number (separated by a dot) '+\
                    'in the <b>delta</b> field.\n\nThe error is "%s"'%error)
            return 0.0
        else:
            return float(value)

    def get_alpha(self):
        "Check user input and return chosen alpha value"
        error = ''
        value = self.alpha_entry.get_text()
        sys.stderr.write('Getting alpha, value is %s.\n'%value)
        try:
            float(value)
        except ValueError, e:
            error = str(e)
        if not valid_alpha.match(value):
            error = 'Value does not match validation criteria.'
        if error:
            self.error('Please enter a valid number (separated by a dot) '+\
                    'in the <b>alpha</b> field.\n\nThe error is "%s"'%error)
            return 0.0
        else:
            return float(value)
    
    def error(self, err_string):
        self.messager.display_message(err_string)


class TreeView:
    """Class representing the list of parameters."""

    def __init__(self, application):
        sys.stderr.write("Initialising the item list (gtk.TreeView)\n")
        self.treeview = application.tree.get_widget("treeview")
        self.application = application
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.treestore = gtk.TreeStore(str,str,str,str,str,str,str)
        self.column_names = ('Parameter',  'Decision', 'Group',
                            'MI', 'EPC', 'Power', 'NCP')
        self.append_columns(self.column_names)
        self.reload()

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
        
    def reload(self, visible_func=None):
        """Initialize or reload the treeview given a filter function"""
        self.treemodelfilter = self.treestore.filter_new(root=None)
        if visible_func:
            self.treemodelfilter.set_visible_func(visible_func, data=None)
        self.treemodelsort = gtk.TreeModelSort(self.treemodelfilter)
        self.treeview.set_model(self.treemodelsort)

    def populate_tree(self):
        """Uses MplusOutput class linked to the parent application
           to get the results and decision rules for the file."""
        self.treestore.clear()
        if self.application.output:
            mi_dict = self.application.output.get_modindices(\
                        self.application.get_delta(), 
                        self.application.get_alpha() )
            for parameter, result in mi_dict.iteritems():
                for group, values in result.iteritems():
                    self.treestore.append( None, (parameter, '-', str(group),
                        jpaste(values[0]), jpaste(values[1]), 
                        jpaste(values[-1]), jpaste(values[-2])) )
        #TODO: calculate judgement rules
    
    def filter(self, by, filter_text):
        """Filters the parameter list by regular expression for one of the fields"""
        sys.stderr.write('Filtering.. by=%s; text=%s\n'%(by,filter_text))
        def visible_func(model, iter, user_data):
            if not filter_text: return True #Don't even bother
            colnum = [name.lower() for name in self.column_names].index(by.lower())
            sys.stderr.write("The value is "+model.get_value(iter, colnum)+"\n")
            found = re.search(filter_text, str(model.get_value(iter, colnum)),
                    re.IGNORECASE)
            return found and True or False  # strange: does not work w/o True/F
                   
        self.reload(visible_func)

class ComboBox:
    """A class for the three combobox filters."""
    def __init__(self, widget_name, app, choices=()):
        self.app = app
        self.widget_name = widget_name
        self.filters_by = widget_name.replace('combo_', '')
        self.widget = self.app.tree.get_widget(widget_name)
        self.model = gtk.ListStore(str)
        for choice in choices:
            self.model.append((choice,))
        self.widget.set_model(self.model)
        cell = gtk.CellRendererText()
        self.widget.pack_start(cell)
        self.widget.add_attribute(cell, 'text' ,0)
        self.widget.set_active(0)   

        self.widget.connect('changed', self.changed)

    def changed(self, widget):
        "Callback for change of combo menu or typing text"
        self.set_text(widget)  # change text based on menu selection
        self.app.treeview.filter(by = self.filters_by, 
            filter_text = widget.child.get_text())

    def set_text(self, widget):
        "Set the text of the ComboEntry to the combo menu selection"
        model = widget.get_model()
        index = widget.get_active()
        if index:
            widget.child.set_text(model[index][0])


class Messager:
    "Convenience class to display error and info dialogs"
    def __init__(self, app):
        self.dialog = app.tree.get_widget('messagedialog')

    def display_message(self, message):
        self.dialog.set_markup(message)
        response = self.dialog.run()
        self.dialog.hide()

if __name__ == "__main__":
    app = JruleGTK()
    gtk.main()
