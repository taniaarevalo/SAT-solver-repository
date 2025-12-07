from pysat.formula import CNFPlus
from pysat.solvers import Minicard

def gen_solution(durations: list[int], c: int, T: int) -> None | list[tuple]:
    N = len(durations)          # number of chicken 
    idCounter = 1               # increment counter to get new ID

    # diccos to contain the ID for each variable
    dep = {}
    a = {}
    b = {}
    dur = {}
    side = {}
    DEP_t = {}
    ARR_t = {}
    ALL_t = {}

    # put a id number on each variable
    # we check for each time > each chicken > each direction:
    for t in range(T):
        side[t] = idCounter
        idCounter += 1

        DEP_t[t] = idCounter 
        idCounter += 1

        ARR_t[t] = idCounter 
        idCounter += 1

        ALL_t[t] = idCounter 
        idCounter += 1

        for p in range(N):
            
            for s in range(2): # 0: Aller, 1: Retour
                dep[(t, p, s)] = idCounter
                idCounter += 1

            a[(p, t)] = idCounter
            idCounter += 1

            b[(p, t)] = idCounter
            idCounter += 1

            for d in range(durations[p]): # durées possibles
                dur[(t, d)] = idCounter
                idCounter += 1
        
def find_duration(durations: list[int], c: int) -> int:
    pass