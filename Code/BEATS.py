"""
Created on Thu Mar  3 11:33:57 2016
GENERAL OVERVIEW 
------------------------------------------------------------------------------
Relevance overview
------------------------------------------------------------------------------
- One task of visual system to create normalized image
- This involves global search for min/max of inputs 
- Inputs are rescaled based on these values
- This exact method of normalization is not nuero-phys. plausible
- However, it could serve as inspiration for diffusion-like filling-in process
  to make the FACADE-like model by Gregory Francis more neuro-phys. plausible, 
  as well as, producing a more accurate output percept.
------------------------------------------------------------------------------
Meta-description of model
------------------------------------------------------------------------------
- Here exact normalization achieved by next-neighbour interactions
- Uses novel non-linear diffusuion systems (like filling-in) this is where
  Bigger EAts Smaller (BEATS), and regions of maximum brightness/darkness grow
  until a global min/max is reached.
- Reaction-diffusion system, Laplacian diffusion model a continuum of electrically
  couple cells (syncytium)
- Laplacian describes an electrical synapse (gap-junction) permitting
  hyperpolarizing and depolarizing somatic curents.
  
  Based on a smodified reaction-diffusion system (Laplacian diffusion)
  
------------------------------------------------------------------------------
Notes
------------------------------------------------------------------------------
- Majority of the code is dedicated to solving various ordinary differential 
  equations (ODE's), which model various synaptic interactions.
- The solving method chosen here is the Fourth-Order Runga-Kutta (RK4) method. 
  One of the most robust and accurate method for solving ODE's. Keil tends to 
  use the Euler method to solve it, as it's simpler but less accurate. 
"""

import numpy as np
import sympy as sp
import scipy.ndimage.filters as flt
#import square_wave
import matplotlib.pyplot as plt
from PIL import Image
from multiprocessing import Pool
    
def T(lamda,x): 
    """
    T Operator function
    ---------------------------------------------------------------------------
    lambda is a "steering" constant between 3 diffusion behaviour states, as a
    part of the diffusion operator. The consequences of steering being:
    
    -------------------------------------------------------
    |lamba |   state   | result on input x                |
    |------|-----------|----------------------------------|
    |==0   | linearity | Remains the same                 |
    |<0    | max       | Half-wave rectification          |
    |>0    | min       | Inverse half-wave rectification  |
    -------------------------------------------------------
    
    Parameters
    ------------    
    lambda : int    steering constant
    x :array-like   input stimulus arrau    
    
    """    
    if lamda == 0:  
        return x
    elif lamda > 0:
        maxval = np.zeros_like(x)
        return np.array([x, maxval]).max(axis=0)
    elif lamda < 0: 
        minval = np.zeros_like(x)
        return np.array([x, minval]).min(axis=0)
        

def Diffusion_operator(lamda,f,t):  
    """
    Diffusion Operator - 2D Spatially Discrete Non-Linear Diffusion
    ---------------------------------------------------------------------------
    This describes the synaptic states of diffusion processes and correspond to 
    It "models different types of electrical synapses (gap junctions).
    The linear version, K=0 , describes the exchange of both polarizing and 
    de-polarizing". Thus the rectification found in the T operator serves to 
    dictate whether polizing (half-wave rectification) or de-polizing (inverse
    half-wave rectification) flow states are allowed to occur.
    Parameters
    ----------
    D : int                      diffusion coefficient
    h : int                      step size
    t0 : int                     stimulus injection point
    stimulus : array-like        luminance distribution     
    
    Returns
    ----------
    f : array-like               output of diffusion equation
    
    
    ---------------------------------------------------------------------
    |lamba |   state                 | result on input x                |
    |------|-------------------------|----------------------------------|
    |==0   | linearity  (T[0])       | Operator becomes Laplacian       |
    |<0    | positive K(lamda)       | Half-wave rectification          |
    |>0    | negative K(lamda)       | Inverse half-wave rectification  |
    ---------------------------------------------------------------------
    
    """
    
    if lamda == 0:  # linearity
        return flt.laplace(f)
    else:           # non-linearity (neighbour interactions up/down/left/right)
        f_new = T(lamda,np.roll(f,1, axis=0)-f) \
        +T(lamda,np.roll(f,-1, axis=0)-f) \
        +T(lamda,np.roll(f, 1, axis=1)-f) \
        +T(lamda,np.roll(f,-1, axis=1)-f)
        return f_new


def Dirac_delta_test(tester):
    """
    The stimuli is injected at t=0 with a dirac delta function. This function
    limits the injection to a unitary multiplication, rather than infinite.
    """
    if np.sum(sp.DiracDelta(tester)) == 0:
        return 0
    else:
        return 1

def Solve_diff_eq_RK4(stimulus,lamda,t0,h,D,t_N):
    """
    Finds a solution to the linear and spatially discrete diffusion equation:
    
                        df/dt = D*K(f) - s*delta(t-t0)  
                        
    using the 4th order Runge-Kutta method (ignoring leakage currents). The 
    stimulus is inject at t0 and then the defined lamda value permits certain
    diffusion behaviour to occur iteratively over this initial stimuli. The
    result is a diffusion of the maximum and minimum values across the stimuli
    to obtain a global value of luminance extremities through local interactions.   
    
    Parameters
    ---------------
    stimulus : array_like   input stimuli [x,y] "photo receptor activity elicited by
                            some real-world luminance distribution"
    lamda : int             a value between +/- inf
    t0 : int                point of stimulus "injection"
    h : int                 Runga-kutta step size
    N : int                 stimulus array size
    D : int                 diffusion coefficient weights rate of diffusion [0<D<1]
    
    Returns
    ----------------
    f : array_like          computed diffused array
    
    """
    f = np.zeros((t_N+1,stimulus.shape[0],stimulus.shape[1])) #[time, equal shape space dimension]
    t = np.zeros(t_N+1)
    
    if lamda ==0:
        """    Linearity  Global Activity Preserved   """
        for n in np.arange(0,t_N,h):
            k1 = D*flt.laplace(f[t[n],:,:]) + stimulus*Dirac_delta_test(t[n]-t0)
            k1 = k1.astype(np.float64)
            k2 = D*flt.laplace(f[t[n]+(h/2.),:,:]+(0.5*h*k1)) + stimulus*Dirac_delta_test((t[n]+(0.5*h))- t0)
            k2 = k2.astype(np.float64)
            k3 = D*flt.laplace(f[t[n]+(h/2.),:,:]+(0.5*h*k2)) + stimulus*Dirac_delta_test((t[n]+(0.5*h))-t0)
            k3 = k3.astype(np.float64)
            k4 = D*flt.laplace(f[t[n]+h,:,:]+(h*k3)) + stimulus*Dirac_delta_test((t[n]+h)-t0)
            k4 = k4.astype(np.float64)
            f[n+1,:,:] = f[n,:,:] + (h/6.) * (k1 + 2.*k2 + 2.*k3 + k4)
            t[n+1] = t[n] + h
        return f
    
    else:
        """    Non-Linearity   (max/min syncytium) Global Activity Not Preserved   """
        for n in np.arange(0,t_N):
            k1 = D*Diffusion_operator(lamda,f[t[n],:,:],t[n]) + stimulus*Dirac_delta_test(t[n]-t0)
            k1 = k1.astype(np.float64)
            k2 = D*Diffusion_operator(lamda,(f[t[n]+(h/2.),:,:]+(0.5*h*k1)),t[n]) + stimulus*Dirac_delta_test((t[n]+(0.5*h))- t0)
            k2 = k2.astype(np.float64)
            k3 = D*Diffusion_operator(lamda,(f[t[n]+(h/2.),:,:]+(0.5*h*k2)),t[n]) + stimulus*Dirac_delta_test((t[n]+(0.5*h))-t0)
            k3 = k3.astype(np.float64)
            k4 = D*Diffusion_operator(lamda,(f[t[n]+h,:,:]+(h*k3)),t[n]) + stimulus*Dirac_delta_test((t[n]+h)-t0)
            k4 = k4.astype(np.float64)
            f[n+1,:,:] = f[n,:,:] + (h/6.) * (k1 + 2.*k2 + 2.*k3 + k4)
            t[n+1] = t[n] + h   
        return f


def ONtype_norm(s,t0,h,D,t_N,a,b,R,dt=1):
    """
    Dynamic normalisation or lightness filling-in (luminance increments)
    ---------------------------------------------------------------------------
    Using the previously obtained global min values of the input stimuli
    a lightness diffusion process is used to obtain a normalized image of the 
    image.
    
    ISSUE : R (+1) regularisation parameter in steady state solution required
            to buffer NaN
    
    Returns
    --------
    c     - steady state solution
    c_out - dynamic solution
    """
    n1=a.shape[1]
    n2=a.shape[2]
    
    c = np.zeros((t_N,n1,n2))
    cd_out = np.zeros((t_N,n1,n2))

    for t in np.arange(1,t_N-1):
        c[t,:,:] =  (s-a[t,:,:])/(b[t,:,:]-a[t,:,:]+R)
    
        cd_out_1 = b[t,:,:]*(np.zeros((n1,n2))-cd_out[t-1,:,:])
        cd_out_2 = a[t,:,:]*(np.ones((n1,n2))-cd_out[t-1,:,:])
        cd_out[t,:,:] = dt*(cd_out_1 - cd_out_2 + s)    
    
    return c , cd_out
    

def OFFtype_norm(t_N,a,b,c,s,R,dt=1):
    """
    Inverse dynamic normalisation or darkness filling-in (luminance decrements)
    --------------------------------------------------------------------------
    Same as dynamic normalisation, but opposite.
    
    ISSUE : R (+1) regularisation parameter in steady state solution to buffer NaN  
            as recommended by Keil. 
    
    Returns
    --------
    d     - steady state solution
    d_out - dynamic solution
    """
    n1=a.shape[1]
    n2=a.shape[2] 
    
    d = np.zeros((t_N,n1,n2))
    d_out = np.zeros((t_N,n1,n2))
    for t in np.arange(0,t_N-1):
        d[t,:,:] = (b[t,:,:] - s) / (b[t,:,:] - a[t,:,:]+R)      
       
        d_out_1 = b[t,:,:]*(np.zeros((n1,n2))-d_out[t,:,:])
        d_out_2 = a[t,:,:]*(np.ones((n1,n2))-d_out[t,:,:])
        d_out[t,:,:] = dt*(d_out_1 - d_out_2 - s)
    return d, d_out
    

""" 
Here is the code to run
"""
# Parameters
D = 0.25  # Diffusion Coefficient [<0.75]
h = 1     # Runga-Kutta Step [h = 1]
t0 = 0    # Start time
t_N = 500 # Length of stimulation [up to 1000 or too much memory used]
R = 1     # Regularisation parameter [R = 1]

# Import jpg image or use square wave stimulus
filename = "whites_1" # Add your own or look in "contAdapt_francis/Documents/"
im = Image.open(("{0}{1}{2}".format("/home/will/Documents/Git_Repository/contAdapt_francis/Documents/",filename,".png"))).convert('L')
#C:\Users\Will\Documents\gitrepos\contAdapt_francis\Documents\rs.png

# Repository names
# /home/will/gitrepos/contAdaptTranslation/Documents/rs.ng
# /home/will/Documents/Git_Repository/contAdapt_francis/Documents

# Resizing image (smaller) increases speed (but reduces accuracy)
f_reduce = 5 # reduction factor
arr = np.array(im.resize((im.size[0]/f_reduce,im.size[1]/f_reduce), Image.ANTIALIAS))
#arr = np.array(im)

# Scale down from grey to binary scale
stimulus=arr/255.
N=stimulus.shape[0]

"""
To increase code speed, multiple processors are run simultaneously with different
diffusion states. The results are saved in the "results" array.
"""
def multi_run_wrapper(args):
   return Solve_diff_eq_RK4(*args)

# Three diffusion behaviour states
pool = Pool(4) # Open 4 processors available on this computer into Pools
state1=(stimulus,-1,t0,h,D,t_N)
state2=(stimulus,0,t0,h,D,t_N)
state3=(stimulus,1,t0,h,D,t_N)
results = pool.map(multi_run_wrapper,[state1,state2,state3])
pool.close()

# output results into arrays
a=results[0][0:t_N,:,:]  # minimum growth state of diffusion
b=results[2][0:t_N,:,:]  # maximum growth state of diffusion
ss=results[1][0:t_N,:,:] # steady-state diffusion

# Two diffusion layers converging to normalized image 
c, c_out = ONtype_norm(stimulus,t0,h,D,t_N,a,b,1) # Lightness filling-in
d, d_out = OFFtype_norm(t_N,a,b,c,stimulus,1)     # Darkness filling-in


""" Later components for full BEATS processing """
#maxval = np.zeros_like(c)
#
#
## Steady-state half-wave-rectify
#S_bright = np.array([c, maxval]).max(axis=0)
#S_dark   = np.array([d, maxval]).min(axis=0)
#
## Dynamic state half-wave-rectify
#S_bright_d = np.array([c_out, maxval]).max(axis=0)
#S_dark_d   = np.array([d_out, maxval]).min(axis=0)
#
## Perceptual activities
#P = (S_bright-S_dark)/(1+S_bright+S_dark) # Steady-state
#P_d = (S_bright_d-S_dark_d)/(1+S_bright_d+S_dark_d) # Dynamic
#
# Positive values only
#P  = np.array([P, maxval]).max(axis=0)
#P_d= np.array([P_d, maxval]).max(axis=0)



""" Plotting of outputs """
""" Diffusion state plotter (change in state) either a,b,c or c_out"""
# plotter1=ss
plotter2=c
plotter3=c_out

plot_r=np.arange(1,t_N,5) # state time plotter array

# Plot intensity limits
vmaxv=0.1#np.max([plotter2,plotter3])
vminv=-0.05#np.min([plotter2,plotter3])

f, axarr = plt.subplots(2, 6)
#axarr[0, 0].imshow(plotter1[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
#axarr[0, 1].imshow(plotter1[plot_r[1],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
#axarr[0, 2].imshow(plotter1[plot_r[2],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
#axarr[0, 3].imshow(plotter1[plot_r[3],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
#axarr[0, 4].imshow(plotter1[plot_r[4],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
#axarr[0, 5].imshow(plotter1[plot_r[5],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
# edit for "Change in lightness evolution" -plotter2[plot_r[0],:,:]
axarr[0, 0].imshow(plotter2[plot_r[0],:,:]-plotter2[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[0, 1].imshow(plotter2[plot_r[1],:,:]-plotter2[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[0, 2].imshow(plotter2[plot_r[2],:,:]-plotter2[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[0, 3].imshow(plotter2[plot_r[3],:,:]-plotter2[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[0, 4].imshow(plotter2[plot_r[4],:,:]-plotter2[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[0, 5].imshow(plotter2[plot_r[5],:,:]-plotter2[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[1, 0].imshow(plotter3[plot_r[0],:,:]-plotter3[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[1, 1].imshow(plotter3[plot_r[1],:,:]-plotter3[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[1, 2].imshow(plotter3[plot_r[2],:,:]-plotter3[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[1, 3].imshow(plotter3[plot_r[3],:,:]-plotter3[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[1, 4].imshow(plotter3[plot_r[4],:,:]-plotter3[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)
axarr[1, 5].imshow(plotter3[plot_r[5],:,:]-plotter3[plot_r[0],:,:], cmap='gray',vmax=vmaxv,vmin=vminv)


""" SCALE CHANGE OF NORMALIZATION OVER TIME """
plot2max=np.zeros((t_N))
plot2mean=np.zeros((t_N))
for i in np.arange(0,t_N-1):
    plot2max[i]=np.max(plotter2[i,:,:])
    plot2mean[i]=np.mean(plotter2[i,:,:])

plt.figure(2)
plt.plot(plot2max)#[0:-1])
plt.plot(plot2mean)#[0:-1])
plt.xlabel('time')
plt.ylabel('intensity value')

""" Luminance edge profiler [ Choose x axis values for cross-sections]"""
first=0
second=33
third=0
t = 400 # State of process e.g. t = 400
gray = stimulus[30,20]
plt.figure(filename)#,figsize=[4,13])

plt.subplot(1,4,1)
stim1=stimulus[first,:]
stim2=stimulus[second,:]
stim3=stimulus[third,:]
plt.plot(stim1,'r')
plt.plot(stim2,'b')
plt.plot(stim3,'g')
plt.title('Input stimulus')
plt.ylim([0,0.7])

plt.subplot(1,4,2)
# plotter2 profile
first_line=plotter3[t,first,:]
second_line=plotter3[t,second,:]
third_line=plotter3[t,third,:]
plt.plot(first_line,'r')
plt.plot(second_line,'b')
plt.plot(third_line,'g')
plt.title('Steady-state solution')
plt.ylim([0,0.7])

plt.subplot(1,4,3)
first_line=plotter3[t,first,:]
second_line=plotter3[t,second,:]
third_line=plotter3[t,third,:]
plt.plot(first_line,'r')
plt.plot(second_line,'b')
plt.plot(third_line,'g')
plt.title('Dynamic solution')
plt.ylim([0,0.7])

plt.subplot(1,4,4)
plt.imshow(plotter2[t,:,:],cmap='gray', vmin=0,vmax=1)
plt.plot(np.arange(0,P.shape[2],1),np.ones(P.shape[2])*first,'r')
plt.plot(np.arange(0,P.shape[2],1),np.ones(P.shape[2])*second,'b')
plt.plot(np.arange(0,P.shape[2],1),np.ones(P.shape[2])*third,'g')
plt.xlim([0,P.shape[2]])
plt.ylim([0,P.shape[1]])
plt.title('Output Dynamic solution')
