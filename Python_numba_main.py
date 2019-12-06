
#--------------------------------#
#         House-keeping          #
#--------------------------------#

from numba import jit, jitclass, njit, prange, int64, float64
import numpy
import math
import time
from scipy.stats import norm
from collections import OrderedDict
import sys

#--------------------------------#
#         Initialization         #
#--------------------------------#

# Number of workers

# Grid for x
nx            = 1500;
xmin          = 0.1;
xmax          = 4.0;

# Grid for e: parameters for Tauchen
ne            = 15;
ssigma_eps    = 0.02058;
llambda_eps   = 0.99;
m             = 1.5;

# Utility function
ssigma        = 2;
bbeta         = 0.97;
T             = 10;

# Prices
r             = 0.07;
w             = 5;

# Initialize the grid for X
xgrid = numpy.zeros(nx)

# Initialize the grid for E and the transition probability matrix
egrid = numpy.zeros(ne)
P     = numpy.zeros((ne, ne))




#--------------------------------#
#         Grid creation          #
#--------------------------------#

# Function to construct the grid for capital (x)
size = nx;
xstep = (xmax - xmin) /(size - 1);
it = 0;
for i in range(0,nx):
	xgrid[i] = xmin + it*xstep;
	it = it+1;


# Function to construct the grid for productivity (e) using Tauchen (1986)
size = ne;
ssigma_y = math.sqrt(math.pow(ssigma_eps, 2) / (1 - math.pow(llambda_eps,2)));
estep = 2*ssigma_y*m / (size-1);
it = 0;
for i in range(0,ne):
	egrid[i] = (-m*math.sqrt(math.pow(ssigma_eps, 2) / (1 - math.pow(llambda_eps,2))) + it*estep);
	it = it+1;


# Function to construct the transition probability matrix for productivity (P) using Tauchen (1986)
mm = egrid[1] - egrid[0];
for j in range(0,ne):
	for k in range(0,ne):
		if (k == 0):
			P[j, k] = norm.cdf((egrid[k] - llambda_eps*egrid[j] + (mm/2))/ssigma_eps);
		elif (k == ne-1):
			P[j, k] = 1 - norm.cdf((egrid[k] - llambda_eps*egrid[j] - (mm/2))/ssigma_eps);
		else:
			P[j, k] = norm.cdf((egrid[k] - llambda_eps*egrid[j] + (mm/2))/ssigma_eps) - norm.cdf((egrid[k] - llambda_eps*egrid[j] - (mm/2))/ssigma_eps);


# Exponential of the grid e
for i in range(0,ne):
	egrid[i] = math.exp(egrid[i]);



#--------------------------------#
#     Structure and function     #
#--------------------------------#

# Value function
VV = math.pow(-10.0, 5);

specs = OrderedDict()
specs['ind'] = int64
specs['ne'] = int64
specs['nx'] = int64
specs['T'] = int64
specs['age'] = int64
specs['P'] = float64[:,:]
specs['xgrid'] = float64[:]
specs['egrid'] = float64[:]
specs['ssigma'] = float64
specs['bbeta'] = float64
specs['w'] = float64
specs['r'] = float64
specs['V'] = float64[:,:,:]


# Data structure of state and exogenous variables
@jitclass(specs)
class modelState(object):
	def __init__(self,ind,ne,nx,T,age,P,xgrid,egrid,ssigma,bbeta,w,r,V):
		self.ind		= ind
		self.ne			= ne
		self.nx			= nx
		self.T			= T
		self.age		= age
		self.P			= P
		self.xgrid		= xgrid
		self.egrid		= egrid
		self.ssigma		= ssigma
		self.bbeta		= bbeta
		self.w			= w
		self.r			= r
		self.V			= V

# Function that returns value for a given state
# ind: a unique state that corresponds to a pair (ie,ix)
@njit
def value_func(states):

	ind = states.ind
	ne = states.ne
	nx = states.nx
	T = states.T
	age = states.age
	P = states.P
	xgrid = states.xgrid
	egrid = states.egrid
	ssigma = states.ssigma
	bbeta = states.bbeta
	w = states.w
	r = states.r
	V = states.V

	ix = int(math.floor(ind/ne));
	ie = int(math.floor(ind%ne));

	VV = math.pow(-10.0, 3)
	for ixp in range(0,nx):
		expected = 0.0;
		if(age < T-1):
			for iep in range(0,ne):
				expected = expected + P[ie, iep]*V[age+1, ixp, iep]

		cons  = (1 + r)*xgrid[ix] + egrid[ie]*w - xgrid[ixp];

		utility = math.pow(cons, (1-ssigma))/(1-ssigma) + bbeta*expected;

		if(cons <= 0):
			utility = math.pow(-10.0,5);
		
		if(utility >= VV):
			VV = utility;

		utility = 0.0;

	return[VV];



#--------------------------------#
#     Life-cycle computation     #
#--------------------------------#

print(" ")
print("Life cycle computation: ")
print(" ")

@njit(parallel=True)
def compute(age, V):

	for ind in prange(0,nx*ne):

		states = modelState(ind, ne, nx, T, age, P, xgrid, egrid, ssigma, bbeta, w, r, V)
		
		ix = int(math.floor(ind/ne));
		ie = int(math.floor(ind%ne));

		V[age, ix, ie] = value_func(states)[0];

	return(V)



start = time.time()
# Initialize value function V
V     = numpy.zeros((T, nx, ne))

for age in range(T-1, -1, -1):
	V = compute(age, V)

	finish = time.time() - start
	print("Age: ", age+1, ". Time: ", round(finish, 4), " seconds.")


finish = time.time() - start
print("TOTAL ELAPSED TIME: ", round(finish, 4), " seconds. \n")


#---------------------#
#     Some checks     #
#---------------------#

print(" - - - - - - - - - - - - - - - - - - - - - \n")
print("The first entries of the value function: \n")

for i in range(0,3):
	print(round(V[0, 0, i], 5))

print(" \n")

