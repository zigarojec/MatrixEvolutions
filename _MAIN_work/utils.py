import numpy as np
import random
from copy import copy, deepcopy
from time import time, strftime
import collections

from globalVars import *


#general circuit class

class slimCircuit:
	"""
	We make the circuit object. 
	Just putting together BigCircuitMatrix and ValueVector to have them in one place. 
	This class cointains no method calls. It is only needed to store topology and values for faster parameter optimizing.
	"""
	def __init__(self, BigCircuitMatrix, ValueVector):
		self.BigCircuitMatrix = BigCircuitMatrix
		#self.fullRedundancyMatrix = fullRedundancyBigCircuitMatrix(BigCircuitMatrix)
		self.fullRedundancyMatrix = None
		self.ValueVector = ValueVector
		
class circuit:
	"""
	We make the circuit object. 
	Just putting together everything an individual represents. 
	"""
	def __init__(self, BigCircuitMatrix, ValueVector):
		self.BigCircuitMatrix = BigCircuitMatrix
		self.fullRedundancyMatrix = fullRedundancyBigCircuitMatrix(BigCircuitMatrix)
		#self.fullRedundancyMatrix = None
		self.ValueVector = ValueVector
		
		rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(self.BigCircuitMatrix)
		self.matrixDensity = float(len(rowsR))/float((BigMatrixSize*BigMatrixSize/2))	#(ones/(all/2))
		self.reduMtrxHash = hash(self.fullRedundancyMatrix.tostring())
		self.mtrxHash = hash(self.BigCircuitMatrix.tostring())
		self.valuHash = hash(self.ValueVector.tostring())
		self.fullHash = self.reduMtrxHash + self.valuHash
		#----added for MOEA
		self.dominatesThose = []
		self.isDominatedByThatMany = None
		self.rank = None
		#self.objectivesScore = np.array([np.inf, np.inf, np.inf])
		self.objectivesScore = []

		#self.scoreHash = hash(self.objectivesScore.tostring())
		self.crow_dist = None
		#----ALPS
		self.age = None
	@property
	def scoreHash(self):
		return hash(np.array(self.objectivesScore).tostring())

def createRandomBigCircuitMatrix(ValueVector):
	"""Creates a random BigCircuitMatrix, with random connection in each row.
	  Takes an individual as an argument from which it gets ValueMatrix."""
	ind1_MX = emptyBigMatrix()	
	OutConns_gene_1 = np.zeros([NofOutConns,BigMatrixSize-NofOutConns], dtype=bool)
	InterConns_gene_1 = np.zeros([BigMatrixSize-NofOutConns, BigMatrixSize-NofOutConns], dtype=bool)

	#Extract sexual material - OutConns - Individual_1
	for i in range(len(OutConns_gene_1)):
		OutConns_gene_1[i] = ind1_MX[0:BigMatrixSize-NofOutConns,BigMatrixSize-(i+1)]	

	#Extract sexual material - InterConns - Individual_1	
	for i in range(len(InterConns_gene_1)):
		InterConns_gene_1[i] = ind1_MX[i,:BigMatrixSize-NofOutConns]

	#--- addRANDOM NODES ---#
	#Pick EVERY amino. Put ONE random connection. 
	for i in range(0, len(InterConns_gene_1)-1):
		#j = random.randint((i+1),(len(InterConns_gene_1[i])-1))
		#InterConns_gene_1[i][j] = True
		#InterConns_gene_1[i][j] = bool(random.getrandbits(1))
		#Improvement 7.8.2015:
		j = random.randint(0,(len(InterConns_gene_1[i])-1))
		InterConns_gene_1[i][j] = True
		#Put true anywhere in a square matrix. Take only upper triangular part. This makes sure lower rows get less chance to be chosen (can be connected to previous). 
	InterConns_gene_1 = deepcopy(np.triu(InterConns_gene_1,0))
		
	used = [None]*len(OutConns_gene_1)
	for i in range(0, len(OutConns_gene_1)):
		done = False
		while not done:
			j = random.randint(0,(len(OutConns_gene_1[i])-1))
			if j in used:
				done = False
			else:
				done = True
				used[i] = j
		OutConns_gene_1[i][j] = True
	
	#--- END of addRANDOM NODES ---#
	
	#Rebuild a big connections matrix out of genes...
	child1_MX=emptyBigMatrix()	
	
	rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(OutConns_gene_1)
	for i in range(len(rowsR)):
		child1_MX[columnsR[i], BigMatrixSize-(rowsR[i]+1)] = True
		
	rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(InterConns_gene_1)		
	for i in range(len(rowsC)):
		child1_MX[rowsC[i], columnsC[i]] = True
	
	
	child1 = circuit(child1_MX, copy(ValueVector))
	return child1
      
def createRandomValueVector():
  """
  Function creates a random Value Vector based on parameters set in globalVars.py and buildingBlocksBank.py. 
  It takes into account the element type, quantity, and all the constraints from buildingBlocksBank.py. 
  """
  #TODO check parameter scale
  
  #exponentMin = paramBounds[params]['scale']*np.log10(paramBounds[params]['min'])
  
 
  randomValueVector = np.array([], dtype="float64")
  for element in buildBlocks:
    for duplicates in range(0,element['Quantity']):
      for params in element['ParamTypes']:
	randomValueVector = np.append(randomValueVector, random.uniform(paramBounds[params]['min'], paramBounds[params]['max']))
  return randomValueVector


def returnMaxValueVector():
  """Returns a Value Vector with parameters at maximum bounds."""
  MaxValueVector = np.array([], dtype="float64")
  for element in buildBlocks:
    for duplicates in range(0,element['Quantity']):
      for params in element['ParamTypes']:
	MaxValueVector = np.append(MaxValueVector, paramBounds[params]['max'])
  return MaxValueVector

def returnMinValueVector():
  """Returns a Value Vector with parameters at minimum bounds."""
  MinValueVector = np.array([], dtype="float64")
  for element in buildBlocks:
    for duplicates in range(0,element['Quantity']):
      for params in element['ParamTypes']:
	MinValueVector = np.append(MinValueVector, paramBounds[params]['min'])
  return MinValueVector


#test functions
def emptyBigMatrix():
	"""Returns an empty diagonal matrix of BigMatrixSize of type Boolean"""
	ones = np.ones(BigMatrixSize,dtype=bool)
	return np.diag(ones,0)	

def fullBigMatrix():
	"""Returns an upper ttriangular matrix full of ones."""
	ones = np.ones([BigMatrixSize, BigMatrixSize],dtype=bool)
	return np.triu(ones,0)
	
def sortedNonZeroIndices(BigCircuitMatrix):
	"""Returns a vector of [rowsR,columnsR,columnsC,rowsC]. 
		rowsR -- rows with non-zero elements sorted by row number (R)
		columnsR -- columns with non-zero elements sorted by row number (R)
		columnsC -- columns with non-zero elements sorted by column number (C)
		rowsC -- rows with non-zero elements sorted by column number (C)
		"""
	#Array of non-zero elements in a BigCircuitMatrix
	connections = np.nonzero(BigCircuitMatrix)
	#Sorted-on-rows version
	rowsR = np.transpose(connections[0])
	columnsR = np.transpose(connections[1])
	#Sorted-on-columns version
	if len(columnsR)>0:
	  columnsC,rowsC = (list (t) for t in zip(*sorted(zip(columnsR,rowsR))))
	  #just to see better in terminal: well yea
	  columnsC = np.transpose(columnsC)
	  rowsC = np.transpose(rowsC)
	  return rowsR,columnsR,columnsC,rowsC
	
	else:
	  print "sortedNonZeroIndices error. Matrix is empty. Cannot return sorted non zero indices."
	  columnsC = None
	  rowsC = None
	  return rowsR,columnsR,columnsC,rowsC 
	  
def fullRedundancyBigCircuitMatrix(BigCircuitMatrix):
	"""Returns a boolean upper triangular matrix with all redundant elements (element connections)."""
	##REVISE###
	BCMx = copy(BigCircuitMatrix)
	
	rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(BCMx)	#get indices of non zero elements
	allDone = 0
	count = 0
	
	while allDone == 0:
		count+=1
		allDone = 1
		#print "Perform cross check (look-up-and-right-and-put-diagonal) for every square..."
		"""
		for i in range(BigMatrixSize):
			up = np.where(columnsC == i)
			right = np.where(rowsR == i)
			for j in up[0]:
				for k in right[0]:
					if(not BCMx[rowsC[j]][columnsR[k]]):
						BCMx[rowsC[j]][columnsR[k]] = True
						allDone = 0
						#print "	BCMx (look-up-and-right-and-put-diagonal) repairment made [row, column] [",rowsC[j],",",columnsR[k],"]"
						
			rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(BCMx)	#to refresh changes
		"""
		for i in range(BigMatrixSize):
			up = np.where(columnsC == i)
			right = np.where(rowsR == i)
			l = 0
			for j in rowsC[up]:
				for k in columnsR[right][l:]:
					if(not BCMx[j][k]):
						BCMx[j][k] = True
						allDone = 0
						#print "	BCMx (look-up-and-right-and-put-diagonal) repairment made [row, column] [",rowsC[j],",",columnsR[k],"]"
						
			rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(BCMx)	#to refresh changes		
		#print "Perform left check bottom-up (look-up-and-put-left) for each in a row..."
		for i in range(BigMatrixSize-1, -1,-1):
			up = np.where(columnsC == i)
			l = 0
			for j in rowsC[up]:
				for k in rowsC[up][l:]:
					if(not BCMx[j][k]):
						BCMx[j][k] = True
						allDone = 0
						#print "	BCMx (look-up-and-put-left) repairment made [row, column] [",j,",",k,"]"			
				l = l+1
			rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(BCMx)	#to refresh changes
			
		#print "Perform right check up-bottom (look-right-and-put-down) for each in a column..."
		for i in range(BigMatrixSize):	
			right = np.where(rowsR == i)
			l = 0
			for j in columnsR[right]:
				for k in columnsR[right][l:]:
					if(not BCMx[j][k]):
						BCMx[j][k] = True
						allDone = 0
						#print "	BCMx (look-right-and-put-down) repairment made [row, column] [",j,",",k,"]"			
				l = l+1				
			rowsR,columnsR,columnsC,rowsC = sortedNonZeroIndices(BCMx)	#to refresh changes
		
	#print "fullRedundancyBigCircuitMatrix counter:\t ", count
	return BCMx

def checkNofOnes(matrix):
  """Similar as checkOutConnsConnected, only matrix can be of any size."""
  conns = np.array(matrix, dtype = int)
  suma = np.sum(conns)
  return suma
 
def checkConnsConnected(BigCircuitMatrix):
  """Checks whether any ouf outer and inner connections in a circuit are connected to each other.
  Function returns a tuple: max number of connected nodes to a single outer node and number of innernodes that are NOT connected anywhere."""
  #---Outer connections
  BCMx = deepcopy(BigCircuitMatrix)
  OutConns = BCMx[:,BigMatrixSize-NofOutConns:BigMatrixSize]
  OutConns = np.array(OutConns, dtype = int)
  
  suma = 0
  for i in range(0, NofOutConns):
    suma = suma + OutConns[:,i]
  
  #---Inner connections
  InnerConns = BCMx[:(BigMatrixSize-NofOutConns),:(BigMatrixSize-NofOutConns)]
  rowSum = np.sum(InnerConns, axis=1)
  colSum = np.sum(InnerConns, axis=0)
  
  a = rowSum + colSum - 2
  nonConnected = len(a) - np.count_nonzero(a)

  #--TEST-Count self-connected elements
  selfConnected = 0
  for i in range(0, Nof2poles, 2):
    selfConnected = selfConnected+InnerConns[i,i+1]
    
  #--TEST- OPAMP LINEAR REGION -Check whether an element is inserted between + and - nodes of opamp
  #TODO
  #Bad idea. Instead, mesaure THD. DONE.
  
  
  return max(suma), nonConnected, selfConnected


def removeDuplicatesFromArrayByAttribute(individuals, attribute):
  """Takes an array of individuals. It returns a copy of that array with unique individuals by some attribute. 
  Usually the attribute would be a hash or some oher unique indentifier. 
  The "attribute" parameter has to be in string type.
  """
  tempPool_hashes = []

  for i in individuals:
    tempPool_hashes.append(getattr(i, attribute))

  dups = collections.defaultdict(list)
  for i, item in enumerate(tempPool_hashes):
    dups[item].append(i)
  
  uniqateI = []
  for i in set(tempPool_hashes):
    uniqateI.append(dups[i][0])#take just first one ...
    #if len(dups[i])>1:
    #  for j in range(1,2):
	  #uniqateI.append(dups[i][j])#take another ... or so.
  
  uniqueIndividuals = []
  for i in uniqateI:
    uniqueIndividuals.append(individuals[i])
  
  return copy(uniqueIndividuals)#deepcopy


def minmaxMeas(sig, scl, start, stop):#obsolete?
  """"""
  startI = int(pyo.IatXval(scl,start, slope='any'))
  stopI = int(pyo.IatXval(scl,stop, slope='any'))
  
  
  partOfSig = copy(sig[startI:stopI])
  maxOfPart = max(partOfSig)
  minOfPart = min(partOfSig)
  
  delta = abs(maxOfPart - minOfPart)
  deltaMeanRef = (abs(1 - np.mean(partOfSig)))/1
  
  gradientSum = sum(abs(np.gradient(partOfSig)))
  
  return maxOfPart, minOfPart, delta, deltaMeanRef, gradientSum

  
def printer(results, stw0, generationNum, **kwargs):
  """
  Prints the summary of current results to the main terminal.
  Calculates time from the start of the program. 
  
  TODO: This method is to be replaced with python logger facility! It is really lame to print only to screen but not to file in the same way.
  """
  
  #Calculate time
  stw1 = time()		
  dtime = stw1-stw0
  m, s = divmod(dtime, 60)
  h, m = divmod(m, 60) 
  
  currentBestScore = results[0]
  
  if kwargs['problem']=='scoreCirc_HighPass':
    print "\n:::GENERATION %4.d - BEST ONE::: %s ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - ripple:", results[1]['ripple']['nominal'], "dB"
      print "\t - damping:", results[1]['damping_L']['nominal'], "dB"
      print "\t - gain:", results[1]['gain']['nominal'], "dB"
      print "\t - bw:", results[1]['bw_start']['nominal'], "Hz"
    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - "   
      
  
  if kwargs['problem']=='scoreCirc_PassiveBandPass':
    print "\n:::GENERATION %4.d - BEST ONE::: %s ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - ripple:", results[1]['ripple']['nominal'], "dB"
      print "\t - damping:", results[1]['damping_L']['nominal'], results[1]['damping_H']['nominal'], "dB"
      print "\t - gain:", results[1]['gain']['nominal'], "dB"
      print "\t - bw:", results[1]['bw_start']['nominal'], results[1]['bw_stop']['nominal'], "Hz"
    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - "   
  

  if kwargs['problem']=='scoreCirc_PassiveFilter_2':
    print "\n:::GENERATION %4.d - BEST ONE::: %f ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - ripple:", results[1]['ripple']['nominal'], "dB"
      print "\t - damping:", results[1]['damping']['nominal'], "dB"
      print "\t - gain:", results[1]['gain']['nominal'], "dB"
      print "\t - bw:", results[1]['bw']['nominal'], "Hz"
      print "\t - Max slope:", results[1]['dumpingSlope']['nominal'], "dB" 
    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - " 



  if kwargs['problem']=='scoreCirc_ActiveFilter_3' or kwargs['problem']=='scoreCirc_ActiveFilter_2':
    print "\n:::GENERATION %4.d - BEST ONE::: %s ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - ripple:", results[1]['ripple']['nominal'], "dB"
      print "\t - damping:", results[1]['damping']['nominal'], "dB"
      print "\t - gain:", results[1]['gain']['nominal'], "dB"
      print "\t - bw:", results[1]['bw']['nominal'], "Hz"
      print "\t - THD_Lf:", results[1]['THD_Lf']['nominal'], "%"
      print "\t - THD_Hf:", results[1]['THD_Hf']['nominal'], "%"
      #print "\t - Rin:", results[1]['rin_meas']['nominal'], "Ohm"
      print "\t - Gain diff 0-end:", results[1]['is_LP']['nominal'], "V/V"
      print "\t - Max slope @freq:", results[1]['maxDampingSlope']['nominal'], "dB@Hz" 
      print "\t - Max input imped:", results[1]['inimped']['nominal'], "Ohm"
      print "\t - Max output imped:", results[1]['outimped']['nominal'], "Ohm"      
    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - " 
 
 
  if kwargs['problem']=='scoreCirc_PassiveFilter':
    print "\n:::GENERATION %4.d - BEST ONE::: %f ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - ripple:", results[1]['ripple']['nominal'], "dB"
      print "\t - damping:", results[1]['damping']['nominal'], "dB"
      print "\t - gain:", results[1]['gain']['nominal'], "dB"
      #print "\t - THD:", Winnerresults[1]['THD']['nominal'], "%"  
    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - "
  
  if kwargs['problem']=='scoreCirc_VoltageReference':
    print "\n:::GENERATION %4.d - BEST ONE::: %f ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - vdd_sweep:", np.median(results[1]['vout_vdd']['nominal']), "V"
      print "\t - rload_sweep:", np.median(results[1]['vout_rload']['nominal']), "V"
      print "\t - temp_sweep:", np.median(results[1]['vout_temp']['nominal']), "V"
      print "\t - power@100Ohm:", results[1]['power']['nominal'], "W"   
    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - "
    
  if kwargs['problem']=='scoreCirc_CmosVoltageReference_2':
    print "\n:::GENERATION %4.d - BEST ONE::: %s ::YEAH!:: Time: %sh %sm %.2fs" %(generationNum,currentBestScore, int(h), int(m), s)
    try:
      print "\t - vdd_sweep at 3 loads:", 
      print np.median(results[1]['vout_vdd_res1']['nominal']),
      print np.median(results[1]['vout_vdd_res2']['nominal']),
      print np.median(results[1]['vout_vdd_res3']['nominal']), "V"
      
      print "\t - vdd_sweep at 3 temps:", 
      print np.median(results[1]['vout_vdd_temp1']['nominal']),
      print np.median(results[1]['vout_vdd_temp2']['nominal']),
      print np.median(results[1]['vout_vdd_temp3']['nominal']), "V"

      print "\t - power@10MOhm:", results[1]['power']['nominal'], "W"
      print "\t - PSRR@100Hz:", results[1]['psrr']['nominal'], "dB" 
      print "\t - Vout@2.5Vvdd:", results[1]['VatLowVdd']['nominal'], "V" 
      print "\t - VoutTsense@11Vvdd:", results[1]['tempSens']['nominal'], "V/oC"

    except:
      print "No results to show."
    print "\t- - - - - - - - - - - - - - - - - - - - - - - - - - "