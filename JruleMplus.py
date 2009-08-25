#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import sys, os, re
import copy
import distributions

import matplotlib   
matplotlib.use('GTK')
matplotlib.interactive(1)
from matplotlib.figure import Figure   
from matplotlib.axes import Subplot   
from matplotlib.lines import Line2D
from matplotlib.backends.backend_gtk import FigureCanvasGTK, NavigationToolbar  

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
valid_alpha = re.compile(r'^[ \t]*0*\.?[0-9]+[ \t]*$')
valid_power = valid_alpha
valid_delta = re.compile(r'^[ \t]*[0-9]*\.?[0-9]+[ \t]*$')



class JruleGTK:
    """Graphical user interface for the MplusOutput class using 
       GTK+ and Glade."""

    def __init__(self):
        # Session vars, TODO: get from ini file
        self.filename = '' # The file to be read
        self.last_directory = 'test/'

        self.critical = False # just a caching var, False triggers calculations
        self.plot = EmptyThing() # A hack to fool .reload()

        # Set the Glade file
        self.gladefile = "JruleMplus.glade"  
        self.tree = gtk.glade.XML(self.gladefile) 

        # Get various widgets necessary later
        self.window = self.tree.get_widget("main_window")
        self.aboutbox = self.tree.get_widget("about")
        self.statusbar = self.tree.get_widget("statusbar")
        self.alpha_entry = self.tree.get_widget("alpha_entry")
        self.power_entry = self.tree.get_widget("power_entry")
        self.delta_entry = self.tree.get_widget("delta_entry")
        self.filechooser = FileChooser(self) # see FileChooser class below
        self.treeview = TreeView(self) # see ItemList class below
        self.messager = Messager(self) 
        self.combo_parameter = ComboBox('combo_parameter', self, ['BY', 'ON', 'WITH'])
        self.combo_group = ComboBox('combo_group', self, []) # TODO: fill in
        self.combo_decision = ComboBox('combo_decision', self, ['Misspecified', 
            'Not misspecified', 'Check EPC', 'Not enough information'])
        
        self.update_status() # show current file in status bar
        
        self.treecolors = {'Inconclusive': '#dee3e3',
            'Misspecified': '#e38f8f',
            'Not misspecified': '#6be05f',
            'Misspecified (EPC >= delta)': '#e3b3b3',
            'Not misspecified (EPC < delta)' : '#a8e8a1',
        } # default colors to give the background of the treeview
        self.use_colors = True # Whether to color bg of treeview

        # connect widget signals to class functions
        self.window.connect("destroy", gtk.main_quit)

        dic = { "on_window_destroy" : gtk.main_quit,
                "on_quit_mi_activate" :gtk.main_quit,
                "on_about_mi_activate" : self.show_about,
                "on_filechooser_file_set" : self.set_file,
                "on_open_mi_activate" : self.set_file_from_menu,
                "on_about_response" : self.about_response,
                "on_delta_entry_changed" : self.reload, # on out of tab
                "on_save" : self.save_tree,
                "on_print" : self.print_tree,
        }
        self.tree.signal_autoconnect(dic) 
        self.window.show()
        self.reload() # fill the tree if there is a file
        self.plot = JPlot(self)

    def reset_filter(self):
        "Reset the application wide filter on parameters"
        self.filtered_parameters = range(len(self.parameters))
        self.already_filtered = []

    def get_parameters(self):
        "Get the parameters from the indices"
        return [self.parameters[ind] for ind in self.filtered_parameters]

    def filter_param(self, index):
        "Filter out parameter with <index>. Assumes reset filter has been called"
        if not index in self.already_filtered:
            self.already_filtered.append(index)
            self.filtered_parameters.remove(index)

    def jpaste(self, number):
        """Utility function to write a floating point number to text.
           Currently not yet in use."""
        return eval("\%1." + self.digits + "f") % float(number)

    def set_file_from_menu(self, menuitem):
        '''What happens if user selects Open from menu'''
        self.set_file(None, filename = self.filechooser.ask())

    def set_file(self, filechooser=None, filename=''):
        """Given the user's choice of file, save this data and reload the list."""
        if filechooser: self.filename = filechooser.get_filename()
        elif filename: self.filename = filename
        else: sys.stderr.write('[108] An error occurred trying to open the file.\n')
        sys.stderr.write("File chosen is %s.\n" % self.filename)
        self.update_status()
        if not self.reload():
            self.messager.display_message('A problem occurred trying to read ' + 
                '%s as an Mplus output file.' % self.filename +
                ' Please make sure you have selected the right file.')

    def reload(self, *args):
        """Reload the list using the MplusOutput class. Might be used as a callback
           so has variable number of arguments."""
        self.critical = False #recalc
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
        if self.plot: self.plot.reload()
        return True

    def update_status(self, context_id=0):
        """Displays a text in the status bar showing the file currently in use."""
        if self.filename:
            msg = "The current output file is '%s'."\
                 % self.filename
        else:
            msg = "Please click the file selection button on the left to"+\
                  " select an output file."
        self.statusbar.push(context_id, msg)

    def show_about(self, about_mi):
        'Show about box'
        self.aboutbox.run() 

    def about_response(self, aboutbox, signal):
        'Handle signals from about box'
        if signal < 0: aboutbox.hide()

    def get_field_value(self, which):
        '''The judgement rules can be changed by the user via fields in the 
           rules tab. This function retrieves a value from a particular field.
           The name of this field should be passed in `which`.'''
        which_dict = {'alpha': (self.alpha_entry, valid_alpha),
            'power': (self.power_entry, valid_power),
            'delta': (self.delta_entry, valid_delta),
        }
        if which not in which_dict.keys(): return 0.0 # unknown field
        error = ''
        value = which_dict[which][0].get_text()
        try:
            float(value)
        except ValueError, e:
            error = str(e)
        if not which_dict[which][1].match(value):
            error = 'Value does not match validation criteria.'
        if error:
#            self.error('Please enter a valid number (separated by a dot) '+\
#                    'in the <b>%s</b> field.\n\nThe error is "%s"'%\
#                    (which, error))
            return 0.0
        else:
            return float(value)

    def get_critical(self):
        "Return critical value of 1df chi square test from field or cached value"
        if not self.critical: # not cached
            self.critical = distributions.qchisq(1, self.get_field_value('alpha'))
        return self.critical

    def error(self, err_string):
        'Just a shorthand for:'
        self.messager.display_message(err_string)

    def save_tree(self, obj):
        "Save the treeview as HTML file"
        outfile = file('outfile.html', 'w')
        outfile.write(self.treeview.get_html())
        outfile.close()
        sys.stderr.write('saved to file ' + filename + '.\n')

    def print_tree(self, obj):
        "Print the treeview as HTML file"
        sys.stderr.write('Print\n')
        html = self.treeview.get_html()
        # print the html under win32


class JPlot:
    """Misspecification plot"""
    def __init__(self, app):
        #setup matplotlib stuff on first notebook page (empty graph)
        self.app = app
        # Plot defaults:
        self.imp_col = '#dd2244'
        self.nim_col = '#5533dd'
        # Create figure
        self.figure = Figure(figsize=(6,4), dpi=72)
        self.axis = self.figure.add_subplot(111)
        self.axis.set_xlabel('Modification index')
        self.axis.set_ylabel('Power')
        self.axis.set_title('Misspecifications')
        try:
            # omit missing observations
            parameters = [par for par in self.app.get_parameters() if \
                        par.mi <99.0 and par.power < 1.0 and par.epc < 99.0]
            self.mis = [par.mi for par in parameters]
            self.names = [par.name for par in parameters]
            self.powers = [par.power for par in parameters]
            self.ids = ["%s in group %s" % (par.name, par.group) for par in parameters]

            self.axis.scatter( self.mis, self.powers,
                c = [par.epc > self.app.get_field_value('delta') \
                    and self.imp_col or self.nim_col for par in parameters],
                linewidth=0, picker=30.0, vmin=self.imp_col,
                vmax = self.nim_col,
            )
            self.axis.autoscale_view(True) #tight

            self.axis.axvline(self.app.get_critical(),
                 color='#444444', linestyle='dashed')
            self.axis.axhline( y=float(self.app.get_field_value('power')),
                 color='#444444', linestyle='dashed')
        except AttributeError:
            pass
        self.draw()

    def pick_handler(self, event):
        '''What happens if the user clicks a point in the plot'''
        index = event.ind[0]
        label = self.ids[index]
        sys.stderr.write('ind is %s'% index)
        sys.stderr.write('mousover %s\n' % label)
        x, y = self.mis[index], self.powers[index]
        self.axis.text(x, y, label)
        self.draw()

    def draw(self):
        'Draw or re-draw the plot, possibly showing some labels'
        try: self.graphview.remove(self.canvas)
        except: pass
        self.canvas = FigureCanvasGTK(self.figure)
        self.canvas.mpl_connect('pick_event', self.pick_handler)
        self.canvas.show()
        self.graphview = self.app.tree.get_widget("vbox_plot")
        self.graphview.pack_start(self.canvas, True, True)

    def reload(self):
        'Completely redo the whole plot.'
        self.graphview.remove(self.canvas)
        self.__init__(self.app)


class TreeView:
    """Class representing the list of parameters."""

    def __init__(self, application):
        sys.stderr.write("Initialising the item list (gtk.TreeView)\n")
        self.treeview = application.tree.get_widget("treeview")
        self.application = application
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.treestore = gtk.TreeStore(str,str,str,str,str,str,str,str)
        self.column_names = ('Parameter',  'Decision',  
                            'Group', 'MI', 'EPC', 'Power', 'NCP')
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
            
            if title is 'Decision':
                cell.set_property('foreground-set', True)
                cell.set_property('background-set', True)
                col.set_attributes(cell, background=7, text=1)

            self.treeview.append_column(col)
            column_id += 1 # default arguments are static!
        
    def reload(self, visible_func=None):
        """Initialize or reload the treeview given a filter function"""
        self.treemodelfilter = self.treestore.filter_new(root=None)
        if visible_func:
            self.treemodelfilter.set_visible_func(visible_func, data=None)
        self.treemodelsort = gtk.TreeModelSort(self.treemodelfilter)
        self.treeview.set_model(self.treemodelsort)
        self.application.plot.reload() # also redraw the plot

    def populate_tree(self):
        """Uses MplusOutput class linked to the parent application
           to get the results and decision rules for the file."""
        self.treestore.clear()
        if self.application.output:
            mi_dict = self.application.output.get_modindices(\
                        self.application.get_field_value('delta'), 
                        self.application.get_field_value('alpha') )
            self.application.parameters = []
            for parameter_name, result in mi_dict.iteritems():
                for group, values in result.iteritems():
                    parameter = Parameter(parameter_name, group, values, 
                        self.application)
                    self.application.parameters.append(parameter)
                    parameter.append_to_tree(self.treestore)
        self.application.reset_filter() # reset parameter filter

    def filter(self, by, filter_text, filter_re):
        """Filters the parameter list by regular expression for one of the fields"""
        sys.stderr.write('Filtering.. by=%s; text=%s\n'%(by,filter_text))
        self.application.reset_filter() # reset parameter filter
        colnum = [name.lower() for name in self.column_names].index(by.lower())
        def visible_func(model, iter, user_data):
            if not (filter_text and model.get_value(iter, colnum)): return True
            found = filter_re.search(str(model.get_value(iter, colnum)))
            if found: return True
            else:   # let the app know this param should be filtered out
                self.application.filter_param(self.treestore.get_path(iter)[0])
                return False

        self.reload(visible_func)
   
    def get_html(self):
        """Return the current content of the view as HTML for export/print
            So far this is just a simple hard-coded template. Maybe integrate
            a light-weight template engine?"""
        html = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'    
        html += '\n<html><head><title>JRule for Mplus output</title>\n' + \
                '<meta http-equiv="Content-Type"'+ \
                ' content="text/html; charset=UTF-8">\n</head>\n<body>\n'
        html += '<table><thead>'
        html += '\n<tr><th>' + '</th><th>'.join(self.column_names) + \
                '</th></tr></thead><tbody>'
        data = self.get_view_as_list()
        html += '\n'.join(['<tr><td>' + '</td><td>'.join(row) + '</td></tr>' \
                            for row in data])
        html += '</tbody></table>\n'
        html += '</body></html>'
        return html

    def get_view_as_list(self):    
        "Return the current content of the view as a list of lists"
        def get_html_from_row(model, path, iter, data=[]):
            "called on each row to return it as html or whatever"
            data.append( [ model.get_value(iter, colnum) for colnum in \
                range(model.get_n_columns()-1)] ) # -1 excludes the color column
        data = []
        self.treemodelsort.foreach(get_html_from_row, data)
        return data


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
        #TODO: self.set_text(widget)  # change text based on menu selection
        text = widget.child.get_text()
        try:
           filter_re = re.compile(text, re.IGNORECASE)
        except: 
            return
        self.app.treeview.filter(by = self.filters_by, 
            filter_text = text, filter_re = filter_re)

    def set_text(self, widget):
        "Set the text of the ComboEntry to the combo menu selection"
        raise NotImplementedError # There should be a HowDoesThisWork error

class Messager:
    "Convenience class to display error and info dialogs"
    def __init__(self, app):
        self.dialog = app.tree.get_widget('messagedialog')

    def display_message(self, message):
        self.dialog.set_markup(message)
        response = self.dialog.run()
        self.dialog.hide()

class Parameter:
    """Class to hold information about the possibly misspecified parameter
       and provide logic to calculate deltas and decisions. Subclass to get
       different kinds of parameters (WITH, BY, etc.)"""

    def __init__(self, name, group, values, app):
        # TODO: Recode 999.0 to missing
        self.name = name
        self.group = group
        self.mi = values[0]
        self.epc = values[1]
        self.std_epc = values[3]
        self.power = values[-1]
        self.ncp = values[-2]
        self.app = app
    
    def append_to_tree(self, treestore):
        """Show this parameter in a TreeStore"""
        # TODO: Give a different bg-color to different decisions
        # TODO: Give a different color to text describing groups
        decision = self.get_decision()
        treestore.append( None, (self.name, decision, str(self.group),
            jpaste(self.mi), jpaste(self.epc), 
            jpaste(self.power), jpaste(self.ncp), 
            self.app.treecolors[decision]) )

    def get_decision(self):
        "Decide whether the parameter is misspecified or not"
        #TODO: allow choice of bonferroni correction to alpha 
        #       (none, simple or complex)
        significant = self.mi > self.app.get_critical()
        high_power = self.power > self.app.get_field_value('power')
        
        if significant and not high_power:
            decision = 'Misspecified'
        elif not significant and not high_power:
            decision = 'Inconclusive'
        elif not significant and high_power:
            decision = 'Not misspecified'
        elif significant and high_power:
            if self.epc >= self.app.get_field_value('delta'):
                decision = 'Misspecified (EPC >= delta)'
            else:
                decision = 'Not misspecified (EPC < delta)'

        return decision


class FileChooser:
    '''Handles opening files, using the GTK filechooser widget and dialog'''
    def __init__(self, app, default_dir = 'tests/'):
        '''Set application, default directory and filters'''
        self.app = app
        self.default_dir = default_dir # so program can remember last session
        self.widget =  app.tree.get_widget("filechooser")

        self.filters = [] # will all be added as filters
        filter = gtk.FileFilter()
        filter.set_name("Output files")
        filter.add_pattern("*.out") # the official/default Mplus output extension
        filter.add_pattern("*.txt") # I guess some people save from Notepad..
        self.filters.append(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.filters.append(filter)

    def ask(self):
        '''Ask user for a file and return the filename chosen'''
        dialog = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,
                         buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        for filter in self.filters: dialog.add_filter(filter)
        dialog.set_current_folder(self.default_dir)
        response = dialog.run()
        if response == gtk.RESPONSE_OK: filename = dialog.get_filename()
        elif response == gtk.RESPONSE_CANCEL: filename = ''
        dialog.destroy()
        return filename


class EmptyThing:
    def __init__(self): pass
    def reload(self): pass
          

if __name__ == "__main__":
    try: sys.stderr = file('logfile.txt', 'w')
    except: pass
    app = JruleGTK()
    gtk.main()
    sys.stderr.close()
