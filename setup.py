from distutils.core import setup
import py2exe
import glob
import matplotlib

data_files = ['JruleMplus.glade',
              (r'img', ['img/decision.png']),
              (r'img', ['img/decision-icon.png']),
              (r'tests',['tests/NEWOUT.OUT']),
              (r'tests', ['tests/MTMM_ROUND_1.OUT']),  ]

mpl_data = matplotlib.get_py2exe_datafiles()
data_files.extend(mpl_data)
data_files.append('boost_python-vc90-mt-1_39.dll',
    'boost_python-vc90-mt-1_39.dll.manifest', 'distributions.pyd',
    'distributions.pyd.manifest', 'msvcm90.dll', 'msvcp90.dll', 'msvcr90.dll')

setup(
    name = 'JruleMplus',
    description = 'Judgement Rule Aid for Mplus',
    version = 'beta',

    windows = [
                  {
                      'script': 'JruleMplus.py',
                      'icon_resources': [(1, "img/decision-icon.ico")],
                  }
              ],

    options = {
                  'py2exe': {
                      'packages':'encodings',
                      'includes': 'cairo, pango, pangocairo, atk, gobject, \
			matplotlib.backends.backend_gtk, distributions',
		      'excludes': [ '_tkagg'],
		      "dll_excludes": [ "MSVCR90D.dll","MSVCR90P.dll","MSVCP90D.dll"],
		
                  }
              },

    data_files=data_files
)

