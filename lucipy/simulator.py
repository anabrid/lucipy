import numpy as np
from scipy.integrate import solve_ivp

# only for debugging; very helpful to display big matrices in one line
np.set_printoptions(edgeitems=30, linewidth=1000)

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
    This adopts the convention with the column order
    
    M1 Mul
    M0 Int
    
    and subsequently
    
    (M^in) = [ A B ] (M^out)
    (I^in) = [ C D ] (I^out)
    
    or written out,
    
    M^in = A * M^out + B * I^out
    I^in = C * M^out + D * I^out
    
    could also denote A,B,C,D as MM, IM, MI, II in (from)(to) fashion.
    
    We need to unroll the M^in = f(I^out, M^out) to
    M^in = f(I^out) so we can then compute M^out from M^in and provide
    the actual system matrix for I^in = f(I^out).
    
    Note that the system state is purely hold in I.
    """
    
    def __init__(self, circuit):
        UCI = circuit.to_dense_matrix()
        self.A, self.B, self.C, self.D = split(UCI, 8, 8)
        self.ics = circuit.ics
        
    def Mul_out(self, Iout):
        # Determine Min from Iout, the "loop unrolling" way
        
        Min0 = np.zeros((8,)) # initial guess
        constants = np.ones((4,)) # constant sources on Mblock
        
        # Compute the MMul block effect, computing 4 multipliers and giving out constants.
        mult_sign = -1 # in LUCIDACs, multipliers negate!
        Mout_from = lambda Min: np.concatenate((mult_sign*np.prod(Min.reshape(4,2),axis=1), constants))
        
        Mout = Mout_from(Min0)
        Min = Min0

        for loops in range(5):
            Min_old = Min.copy()
            Min = self.A.dot(Mout) + self.B.dot(Iout)
            Mout = Mout_from(Min)
            if np.all(Min_old == Min):
                break
        else:
            raise ValueError("The circuit contains algebraic loops")
        
        return Mout
    
    def nonzero(self):
        sys = np.array([[self.A,self.B],[self.C,self.D]])
        return np.sum(sys != 0, axis=(2,3))

    
    def rhs(self, state):
        Iout = state
        Mout = self.Mul_out(Iout)
        Iin = self.C.dot(Mout) + self.D.dot(Iout)
        int_sign  = +1 # in LUCIDAC, integrators do not negate
        print(f"{Iout[0:2]=} -> {Iin[0:2]=}")
        return int_sign * Iin
    
    def solve_ivp(self, t_final, initial_state=None, dense_output=True):
        if np.all(initial_state == None):
            initial_state = self.ics
        
        data = solve_ivp(lambda t, state: self.rhs(state), [0, t_final], initial_state, dense_output=dense_output)
        
        assert data.status == 0, "ODE solver failed"
        assert data.t[-1] == t_final
        
        return data
