from pysat.formula import CNFPlus, IDPool
from pysat.solvers import Minicard
from pysat.card import CardEnc


def id_dep(T, N, vpool):
    """Will return a dictionnary with all the id for dep. {(t, p, s): id}"""
    dep = {}
    for t in range(T):
        for p in range(N):
            for s in range(2):  # two ways only : 0 = "Aller", 1 = "Retour"
                dep[(t, p, s)] = vpool.id(("dep", t, p, s))
    return dep


def id_A(T, N, vpool):
    """Will return a dictionnary with all the id for A. {(t, p): id}"""
    A = {}
    for t in range(T):
        for p in range(N):
            A[(p, t)] = vpool.id(("A", p, t))
    return A


def id_B(T, N, vpool):
    """Will return a dictionnary with all the id for B. {(t, p): id}"""
    B = {}
    for t in range(T):
        for p in range(N):
            B[(p, t)] = vpool.id(("B", p, t))
    return B


def id_dur(T, durations, vpool):
    """Will return a dictionnary with all the id for dur. {(t, d): id}"""
    dur = {}
    for t in range(T):
        for d in durations:
            dur[(t, d)] = vpool.id(("dur", t, d))
    return dur


def id_side(T, vpool):
    """Will return a dictionnary with all the id for side. {t: id}"""
    side = {}
    for t in range(T):
        side[t] = vpool.id(("side", t))
    return side


def id_DEP(T, vpool):
    """Will return a dictionnary with all the id for DEP. {t: id}"""
    DEP = {}
    for t in range(T):
        DEP[t] = vpool.id(("DEP", t))
    return DEP


def id_ARR(T, vpool):
    """Will return a dictionnary with all the id for ARR. {t: id}"""
    ARR = {}
    for t in range(T):
        ARR[t] = vpool.id(("ARR", t))
    return ARR


def id_ALL(T, vpool):
    """Will return a dictionnary with all the id for ALL. {t: id}"""
    ALL = {}
    for t in range(T):
        ALL[t] = vpool.id(("ALL", t))
    return ALL


def gen_solution(durations: list[int], c: int, T: int) -> None | list[tuple]:
    N = len(durations)          # number of chicken 
    constraints = CNFPlus()         # we can start the CNF
    vpool = IDPool()            # to associate variable to a SAT number

    # dep(t, p, s)
    dep = id_dep(T, N, vpool)

    # A(p, t)
    A = id_A(T, N, vpool)

    # B(p, t)
    B = id_B(T, N, vpool)

    # dur(t, d)
    dur = id_dur(T, durations, vpool)

    # side(t)
    side = id_side(T, vpool)

    # DEP(t)
    DEP = id_DEP(T, vpool)

    # ARR(t)
    ARR = id_ARR(T, vpool)

    # ALL(t)
    ALL = id_ALL(T, vpool)

    # (¬DEP𝑡 ∨ dep𝑡,𝑝,𝑠) ∧ (dep𝑡,𝑝,𝑠 ∨ DEP𝑡) constraint
    for t in range(T):
        for p in range(N):
            for s in range(2):
                constraints.append([-DEP[t], dep[(t, p, s)]])
                constraints.append([dep[(t, p, s)], DEP[t]])
            
    # Cohérence entre départs et arrivée
    for t in range(T):
        for t2 in range(t):
            for d in durations:
                if t2+d == t:
                    constraints.append([-ARR[t], dur[t2, d]])
                    constraints.append([-dur[t2, d], ARR[t]])

    # Condition de complétion
    for t in range(T):
        for p in range(N):
            constraints.append([-ALL[t], B[(p, t)]])
            constraints.append([-B[(p, t)], ALL[t]])

    # Contraintes dur(t, d)
    for t in range(T):
        for i, d1 in enumerate(durations):
            for d2 in durations[i+1:]:
                constraints.append([-dur[(t, d1)], -dur[(t, d2)]])

    for t in range(T):
        for d in durations:
            for p in range(N):
                if durations[p] > d:
                    for s in range(2):
                        constraints.append([-dur[(t, d)], -dep[(t, p, s)]])
                elif durations[p] == d:
                    for s in range(2):
                        constraints.append([-dep[(t, p, s)], dur[(t, d)]])
    
    # capacité max de la barque, atmlst : ∑(𝑝) dep𝑡,𝑝,𝑠 <= 𝐶
    for t in range(T):
        for s in range(2):
            lits = []
            for p in range(N):
                lits.append(dep[(t, p, s)])
            barque = CardEnc.atmost(lits, bound = c,vpool = vpool, encoding = 1)
            constraints.extend(barque.clauses)

    # contrainte d'alternance et position de la barque side(t)
    for t in range(T):
        for p in range(N):
            constraints.append([-side[t], -dep[(t, p, 1)]])
            constraints.append([side[t], -dep[(t, p, 0)]])

    # mise à jour de la position de la barque
    for t in range(T):
            for d in durations:
                if t+d < T:
                    constraints.append([-dur[(t, d)], -side[t], side[t+d]])
                    constraints.append([-dur[(t, d)], side[t], -side[t+d]])

    # évolution des poules sur la berge A et B
    for t in range(T):
        for d in durations:
            if d + t < T:
                for p in range(N):
                    constraints.append([-dep[(t, p, 0)], -dur[(t, d)], B[(p, t+d)]])
                    constraints.append([-dep[(t, p, 1)], -dur[(t, d)], A[(p, t+d)]])
    for t in range(T):
        if t + 1 < T:
            for p in range(N):
                constraints.append([dep[(t, p, 0)], dep[(t, p, 1)], -A[(p, t)], A[(p, t+1)]])
                constraints.append([dep[(t, p, 0)], dep[(t, p, 1)], -B[(p, t)], B[(p, t+1)]])

    # interdiction de départs multiples pendant une traversée
    for t in range(T):
        for d in durations:
            for k in range(1, d):
                if t+k < T:
                    constraints.append([-dur[(t, d)], -DEP[(t+k)]])
    
    with Minicard(bootstrap_with=constraints) as solver:
        sat = solver.solve()
        if not sat:
            return None
        model = solver.get_model()
        true_vars = set(v for v in model if v > 0)

        solution = []
        for t in range(T):
            if DEP[t] in true_vars:
                chickens = []
                for p in range(N):
                    for s in range(2):
                        if dep[(t, p, s)] in true_vars:
                            chickens.append(p + 1)
                            break
                solution.append((t, chickens))

        return solution


def find_duration(durations: list[int], c: int) -> int:
    pass
