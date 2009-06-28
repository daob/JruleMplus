import re


class MplusOutput:
   """
      Parsing functions for output from Mplus 5
   """
   def __init__(self, filename):
      "Try to open the file and initialise some of the looping variables used by the parser"
      try:
         self.f = open(filename, 'r')
      except IOError:
         print "\nThe output file does not exist (check the file name):\"%s\"" % filename
      else:
         # lazy check that it is an Mplus output file:
         version = re.findall( 'Mplus VERSION ([0-9\.]+)', self.f.readline() )
         if ( not version ):
            raise ValueError, "\nThat file does not seem to be an Mplus output file.\n"
         if ( float(version[0]) < 5.0 ):
            print("\nWarning: reading STDYX estimates will only work with Mplus version 5 or higher.")
         
         self.class_num  = 1
         self.groups     = self.get_group_info()
         self.statements = {}
         
         self.estimates_string = re.compile('^[ ]*(\w+)[ ]*([-]*\d+\.\d+)[ ]+([-]*\d+\.\d+)')
         self.class_num_string = re.compile('^Latent Class (\d+)')
         self.group_string     = re.compile('^Group (\w+)$')
      
      
   def read_estimates(self, statement_string = '(\w+)[ ]*BY', estimate_type = 'stdyx'):
      """
         Read some kind of estimates (e.g. stdyx or normal), 
         and some kind of statement (e.g. BY, WITH, ...)
      """
      if (estimate_type == 'stdyx'):
         self.starting_string = re.compile("STDYX Standardization")
         self.stopping_string = re.compile("R-SQUARE")
      elif (estimate_type == 'regular'):
         self.starting_string = re.compile("^MODEL RESULTS")
         self.stopping_string = re.compile("^STANDARDIZED MODEL RESULTS")
         #self.stopping_string = re.compile("^LOGISTIC REGRESSION ODDS RATIO RESULTS")
      else :
         raise ValueError, "I don't know how to read that kind of output (yet)."
         
      in_block       = False
      in_statement   = False
      
      statement_string = re.compile(statement_string)
      statements = {}

      for line in self.f:
         if ( self.starting_string.findall(line) ):
            in_block = True
         if ( self.stopping_string.findall(line)  ):
            in_block = False
            
         if (in_block):
            class_tmp   = self.group_string.findall(line)
            if (class_tmp):
               self.class_num += 1
               #self.groups.append(class_tmp[0]) # now done in init

            about_variable = statement_string.findall(line)

            if (about_variable):
               in_statement = about_variable[0]
               if ( not statements.has_key(in_statement) ):
                  statements[in_statement] = {}
                             
            if (not about_variable and in_statement):
               est = self.estimates_string.findall(line)
               if (est):
                  est = est[0]
                  if (not statements[in_statement].has_key(est[0])):
                     statements[in_statement][est[0]] = []

                  statements[in_statement][est[0]].append(est[1:])
               else:
                  in_statement = False

         est         = []
         about_variable = []

      self.f.seek(0) # rewind the file so it can be read again
      return(statements)

   def get_group_info(self):
      start = re.compile("^Number of observations[\r\n]")
      group = re.compile("^[ ]+Group ([a-zA-Z_0-9-]+)[ ]+([0-9]+)[\r\n]")
      stop  = re.compile("^Number of dependent variables[ ]+([0-9]+)[\r\n]")

      in_block = False
      groups = []
      for line in self.f:
         if ( start.findall(line) ):
            in_block = True
         if ( stop.findall(line) ):
            self.f.seek(0) # rewind the file so it can be read again
            return(groups)
         if (in_block):
            g = group.findall(line)
            if(g):               
               groups.append(g[0][0])

      self.f.seek(0) # rewind the file so it can be read again   
      return(groups)
         
   def write_estimates(self, filename, estimate_type = 'regular'):
      f = open(filename, 'w')
      f.write("country\tround\tparameter\testimate\tse\n")

      estimate_types = {'Errors':'e', 'Variances':'V', 'Means':'E', 'Intercepts':'n'}
      results = self.get_estimates(estimate_type)

      for type, symbol in estimate_types.iteritems():
         res = results[type][results[type].keys()[0]]
         for param in res.keys():
            for country_num in range(0,len(res[param])):
               f.write(str(self.groups[country_num]) + "\t1\t" + symbol  + "(" + str(param) + ")\t")
               f.write('\t'.join(res[param][country_num]))
               f.write("\n")

      f.close()

   def get_estimates(self, estimate_type = 'stdyx'):      
      statement_types = { 
         "BY"     : '(\w+)[ ]*BY',
         "ON"     : '(\w+)[ ]*ON',
         "WITH"   : '(\w+)[ ]*WITH',
         "Means"  : '^[ ]*Means[ ]*[\n\r]',
         "Intercepts": '^ Intercepts[\n\r]',
         "Variances": '^ Variances[\n\r]',
         "Errors" : '^[ ]*Residual Variances[ ]*[\n\r]', 
         }
      for statement_type, statement_regex in statement_types.iteritems():
         ests = self.read_estimates(statement_string=statement_regex, estimate_type = estimate_type)
         if (len (ests) == 1): 
            # if the estimates are not nested with other variables, skip one level of nesting
            ests[ests.keys()[0]]
         self.statements[statement_type] = ests

      return (self.statements)

   def write_modindices(self, filename, delta=0.1, alpha=0.05, multigroup=True):
      try:
         modinds = self.get_modindices(delta, alpha, multigroup)
      except:   
         print("\nCould not read the modification indices.\n")
         return()
      
      f = open(filename, 'w')
      f.write("param\tcountry\tMI\tEPC\tStd_EPC\tStdYX_EPC\tNCP\tpower\n")
      for param in modinds.keys():
         for country in modinds[param].keys():
            l = "\t".join(str(m) for m in modinds[param][country])
            f.write('"'+param +'"'+ "\t")
            f.write('"'+country +'"'+ "\t")
            f.write(l + "\n")
      f.close()

   def get_modindices(self, delta=0.1, alpha = 0.05, multigroup=True):
      """
         Read the modification indices from the file,
         and calculate the power of the score test.
      """
      self.starting_string = re.compile("^MODEL MODIFICATION INDICES")
      self.stopping_string = re.compile('^TECHNICAL \d OUTPUT')

      in_block       = False
      scipy_ok       = True
      try:
         from scipy.stats.distributions import chi2 # chi-square distribution
         from scipy.stats.distributions import ncx2 # non-central chi-square
      except ImportError:
         scipy_ok = False
         print "\nWarning: You do not have the scipy library installed. "
         print "The power cannot be calculated.\n"
      if scipy_ok: critical = chi2.ppf(1.0-alpha, 1) # critical value for alpha level
      
      statement_string = re.compile('^[\[]*([\w ]+\w+)[ \]]+([-]*\d+\.\d+)[ ]+([-]*\d+\.\d+)[ ]+([-]*\d+\.\d+)[ ]+([-]*\d+\.\d+)')
      if multigroup:
          class_num_string = re.compile('^Group ([A-Z_-]+)[ ]*[\r\n]')
      else:
          class_num_string = re.compile('^CLASS (\d+)[ ]*[\r\n]')
      class_num = 1
      statements = dict()

      for line in self.f:
         if ( self.starting_string.findall(line) ):
            in_block = True
         if ( self.stopping_string.findall(line)  ):
            in_block = False
            
         if (in_block):
            class_tmp   = class_num_string.findall(line)
            if (class_tmp):
               class_num = str(class_tmp[0])

            about_variable = statement_string.findall(line)

            if (about_variable):
               in_statement = about_variable[0][0]
               in_statement = re.sub("[ ]+"," ", in_statement.strip())
               values = about_variable[0][1:]
               values = list(float(v) for v in values )
               
               if (values[0] != 999.0 and abs(values[3]) > 0.0001 and \
                    abs(values[1])> 1e-6):
                  ncp = ( values[0] / values[1]**2 ) * delta**2
                  values.append(ncp)
                  if scipy_ok: # calculate power
                     values.append(1 - float(ncx2.cdf(critical, 1.0, values[4])))
                  else:
                     values.append(999.0) # no scipy-->missing power value
               else:
                  values.extend([999.0,999.0]) # missing values

               if in_statement not in statements: 
                  statements[in_statement] = {class_num : values}
               else:
                  statements[in_statement][class_num] = values
                  
         about_variable = []

      self.f.seek(0) # rewind the file so it can be read again
      return(statements)         
