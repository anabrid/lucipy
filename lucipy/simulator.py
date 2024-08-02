import numpy as np
from scipy.integrate import solve_ivp

# only for debugging; very helpful to display big matrices in one line
np.set_printoptions(edgeitems=30, linewidth=1000, suppress=True)

def split(array, nrows, ncols):
    """
    Split a matrix into sub-matrices.
    Provides one new axis over the array (linearized).
    """
    r, h = array.shape
    return (array.reshape(h//nrows, nrows, -1, ncols)
                 .swapaxes(1, 2)
                 .reshape(-1, nrows, ncols))


class simulation:
    """
    A simulator for the LUCIDAC. Please :ref:`refer to the documentation <lucipy-sim>`
    for a theoretical and practical introduction.
    
    Important properties and limitations:
    
    * Currently only understands mblocks ``M1 = Mul`` and ``M0 = Int``
    * Unrolls Mul blocks at evaluation time, which is slow
    * Note that the system state is purely hold in I.
    * Note that k0 is implemented in a way that 1 time unit = 10_000 and
      k0 slow results are thus divided by 100 in time.
      Should probably be done in another way so the simulation time is seconds.
    """
    
    def __init__(self, circuit):
        UCI = circuit.to_dense_matrix()
        self.A, self.B, self.C, self.D = split(UCI, 8, 8)
        self.ics = circuit.ics
        
        # fast = 10_000, slow = 100
        self.int_factor = np.array(circuit.k0s) / 10_000
        
    def Mul_out(self, Iout):
        # Determine Min from Iout, the "loop unrolling" way
        
        Min0 = np.zeros((8,)) # initial guess
        constants = np.ones((4,)) # constant sources on Mblock
        
        # Compute the actual MMulBlock, computing 4 multipliers and giving out constants.
        mult_sign = -1 # in LUCIDACs, multipliers negate!
        Mout_from = lambda Min: np.concatenate((mult_sign*np.prod(Min.reshape(4,2),axis=1), constants))
        
        Mout = Mout_from(Min0)
        Min = Min0
        
        max_numbers_of_loops = 4 # = number of available multipliers (in system=on MMul)
        for loops in range(max_numbers_of_loops+1):
            Min_old = Min.copy()
            Min = self.A.dot(Mout) + self.B.dot(Iout)
            Mout = Mout_from(Min)
            #print(f"{loops=} {Min=} {Mout=}")

            # this check is fine since exact equality (not np.close) is required.
            # Note that NaN != NaN, therefore another check follows
            if np.all(Min_old == Min):
                break
            
            if np.any(np.isnan(Min)) or np.any(np.isnan(Mout)):
                raise ValueError(f"At {loops=}, occured NaN in {Min=}; {Mout=}")

        else:
            raise ValueError("The circuit contains algebraic loops")
        
        #print(f"{loops=} {Mout[0:2]=}")
        return Mout
    
    def nonzero(self):
        sys = np.array([[self.A,self.B],[self.C,self.D]])
        return np.sum(sys != 0, axis=(2,3))

    
    def rhs(self, t, state, clip=True):
        Iout = state
        
        #eps = 1e-2 * np.random.random()
        eps = 0.2
        if clip:
            Iout[Iout > +1.4] = +1.4 - eps
            Iout[Iout < -1.4] = -1.4 + eps

        Mout = self.Mul_out(Iout)
        Iin = self.C.dot(Mout) + self.D.dot(Iout)
        int_sign  = +1 # in LUCIDAC, integrators do not negate
        #print(f"{Iout[0:2]=} -> {Iin[0:2]=}")
        #print(t)
        return int_sign * Iin * self.int_factor
    
    def solve_ivp(self, t_final, clip=True, ics=None, **kwargs_for_solve_ivp):
        """
        Good-to-know options for solve_ivp:
    
        * dense_output=True -> allows for interpolating on res.sol(linspace(...))
        * method="LSODA" -> good for stiff problems
    
        """
        if np.all(ics == None):
            ics = self.ics
        elif len(ics) < len(self.ics):
            ics = list(ics) + [0]*(len(self.ics) - len(ics))
        
        data = solve_ivp(lambda t,state: self.rhs(t,state,clip), [0, t_final], ics, **kwargs_for_solve_ivp)
        
        #assert data.status == 0, "ODE solver failed"
        #assert data.t[-1] == t_final
        
        return data
