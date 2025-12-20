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
    """Will return a dictionnary with all the id for A. {(p, t): id}"""
    A = {}
    for t in range(T + 1):
        for p in range(N):
            A[(p, t)] = vpool.id(("A", p, t))
    return A


def id_B(T, N, vpool):
    """Will return a dictionnary with all the id for B. {(p, t): id}"""
    B = {}
    for t in range(T + 1):
        for p in range(N):
            B[(p, t)] = vpool.id(("B", p, t))
    return B


def id_dur(T, D, vpool):
    """Will return a dictionnary with all the id for dur. {(t, d): id}"""
    dur = {}
    for t in range(T):  # dur is defined only for departure instants
        for d in D:
            dur[(t, d)] = vpool.id(("dur", t, d))
    return dur


def id_side(T, vpool):
    """Will return a dictionnary with all the id for side. {t: id}"""
    side = {}
    for t in range(T + 1):
        side[t] = vpool.id(("side", t))
    return side


def id_DEP(T, vpool):
    """Will return a dictionnary with all the id for DEP. {t: id}"""
    DEP = {}
    for t in range(T):  # departures only at times 0..T-1
        DEP[t] = vpool.id(("DEP", t))
    return DEP


def id_ARR(T, vpool):
    """Will return a dictionnary with all the id for ARR. {t: id}"""
    ARR = {}
    for t in range(T + 1):
        ARR[t] = vpool.id(("ARR", t))
    return ARR


def id_ALL(T, vpool):
    """Will return a dictionnary with all the id for ALL. {t: id}"""
    ALL = {}
    for t in range(T + 1):
        ALL[t] = vpool.id(("ALL", t))
    return ALL


def id_ARRP(T, N, vpool):
    """Will return a dictionary with all the id for ARRP. {(p, t): id} where t in [0..T]."""
    ARRP = {}
    for t in range(T + 1):
        for p in range(N):
            ARRP[(p, t)] = vpool.id(("ARRP", p, t))
    return ARRP


def gen_solution(durations: list[int], c: int, T: int): 
    #-> None | list[tuple]
    N = len(durations)  # number of chickens
    maxT = max(durations) if durations else 0
    D = list(range(1, maxT + 1))  # duration domain

    constraints = CNFPlus()
    vpool = IDPool()

    # dep(t, p, s) where t in [0..T-1], p in [0..N-1], s in {0=Aller,1=Retour}
    dep = id_dep(T, N, vpool)

    # A(p, t), B(p, t) where t in [0..T]
    A = id_A(T, N, vpool)
    B = id_B(T, N, vpool)

    # dur(t, d) where t in [0..T-1] and d in D
    dur = id_dur(T, D, vpool)

    # side(t) where t in [0..T]
    side = id_side(T, vpool)

    # DEP(t) where t in [0..T-1]
    DEP = id_DEP(T, vpool)

    # ARR(t), ALL(t) where t in [0..T]
    ARR = id_ARR(T, vpool)
    ALL = id_ALL(T, vpool)
    ARRP = id_ARRP(T, N, vpool)

    # --- Basic location exclusivity: each chicken is on exactly one bank at each instant
    for t in range(T + 1):
        for p in range(N):
            constraints.append([A[(p, t)], B[(p, t)]])
            constraints.append([-A[(p, t)], -B[(p, t)]])

    # --- Initial state
    for p in range(N):
        constraints.append([A[(p, 0)]])
        constraints.append([-B[(p, 0)]])
    constraints.append([side[0]])  # boat starts on bank A

    # --- DEP(t) <-> OR_{p,s} dep(t,p,s)
    for t in range(T):
        dep_lits = [dep[(t, p, s)] for p in range(N) for s in range(2)]
        # DEP -> OR dep
        constraints.append([-DEP[t]] + dep_lits)
        # dep -> DEP
        for lit in dep_lits:
            constraints.append([-lit, DEP[t]])

    # --- Exactly one direction possible depending on boat side, and dep requires chicken on that side
    # side(t)=True means boat on A: Retour forbidden. side(t)=False means boat on B: Aller forbidden.
    for t in range(T):
        for p in range(N):
            # side(t) -> not Retour
            constraints.append([-side[t], -dep[(t, p, 1)]])
            # not side(t) -> not Aller   (equivalently: side(t) OR not Aller)
            constraints.append([side[t], -dep[(t, p, 0)]])

            # If a chicken departs, it must be on the departure bank at time t
            constraints.append([-dep[(t, p, 0)], A[(p, t)]])  # Aller
            constraints.append([-dep[(t, p, 1)], B[(p, t)]])  # Retour

    # --- Capacity: at most c chickens depart at time t (direction is already enforced by side)
    for t in range(T):
        lits = [dep[(t, p, 0)] for p in range(N)] + [dep[(t, p, 1)] for p in range(N)]
        barque = CardEnc.atmost(lits, bound=c, vpool=vpool, encoding=1)
        constraints.extend(barque.clauses)

    # --- Link dur and DEP: DEP(t) <-> OR_d dur(t,d)
    for t in range(T):
        dur_lits = [dur[(t, d)] for d in D]
        constraints.append([-DEP[t]] + dur_lits)  # DEP -> some duration chosen
        for dl in dur_lits:
            constraints.append([-dl, DEP[t]])

        # At most one duration per departure time
        for i, d1 in enumerate(D):
            for d2 in D[i + 1:]:
                constraints.append([-dur[(t, d1)], -dur[(t, d2)]])

    # --- Max-duration semantics:
    # 1) If dur(t,d) then no departing chicken has time > d
    # 2) If dur(t,d) then at least one departing chicken has time exactly d
    # 3) If a chicken with time tp departs, then chosen duration is >= tp
    for t in range(T):
        for d in D:
            # (2) dur(t,d) -> OR_{p:Tp=d, s} dep(t,p,s)
            equal_ps = [dep[(t, p, s)] for p in range(N) if durations[p] == d for s in range(2)]
            if equal_ps:
                constraints.append([-dur[(t, d)]] + equal_ps)
            else:
                # If no chicken has duration d, then dur(t,d) is impossible
                constraints.append([-dur[(t, d)]])

            for p in range(N):
                tp = durations[p]
                if tp > d:
                    # (1) dur(t,d) -> not dep(t,p,s)
                    constraints.append([-dur[(t, d)], -dep[(t, p, 0)]])
                    constraints.append([-dur[(t, d)], -dep[(t, p, 1)]])

        for p in range(N):
            tp = durations[p]
            # (3) dep(t,p,s) -> OR_{d>=tp} dur(t,d)
            ge_durs = [dur[(t, d)] for d in D if d >= tp]
            constraints.append([-dep[(t, p, 0)]] + ge_durs)
            constraints.append([-dep[(t, p, 1)]] + ge_durs)

    # --- ARR(t) <-> OR_{t',d: t'+d=t} dur(t',d)
    for t in range(T + 1):
        arrivals = []
        for t0 in range(T):
            for d in D:
                if t0 + d == t:
                    arrivals.append(dur[(t0, d)])
        if arrivals:
            constraints.append([-ARR[t]] + arrivals)
            for al in arrivals:
                constraints.append([-al, ARR[t]])
        else:
            constraints.append([-ARR[t]])

    # --- ARRP(p,t): chicken p arrives (changes bank) exactly at instant t
    # We build conjunction literals X = dep(t0,p,s) AND dur(t0,d) for all (t0,d) with t0+d=t,
    # then encode ARRP(p,t) <-> OR X.
    for t_arr in range(T + 1):
        for p in range(N):
            terms = []
            for t0 in range(T):
                for d in D:
                    if t0 + d == t_arr:
                        for s in range(2):
                            x = vpool.id(("arrterm", t0, p, s, d))
                            # x -> dep and x -> dur
                            constraints.append([-x, dep[(t0, p, s)]])
                            constraints.append([-x, dur[(t0, d)]])
                            # dep & dur -> x
                            constraints.append([-dep[(t0, p, s)], -dur[(t0, d)], x])
                            terms.append(x)
            if terms:
                # ARRP -> OR terms
                constraints.append([-ARRP[(p, t_arr)]] + terms)
                # each term -> ARRP
                for x in terms:
                    constraints.append([-x, ARRP[(p, t_arr)]])
            else:
                constraints.append([-ARRP[(p, t_arr)]])

    # --- Boat side update:
    # If a trip of duration d starts at t, then side flips at t+d.
    for t in range(T):
        for d in D:
            if t + d <= T:
                # If side[t] is True (boat on A) then after crossing it must be False (boat on B), and vice versa.
                constraints.append([-dur[(t, d)], -side[t], -side[t + d]])
                constraints.append([-dur[(t, d)], side[t], side[t + d]])

    # If no arrival at t+1, boat side stays the same (inertia)
    for t in range(T):
        constraints.append([ARR[t + 1], -side[t], side[t + 1]])
        constraints.append([ARR[t + 1], side[t], -side[t + 1]])

    # --- Chicken movement update:
    # Arrival constraints
    for t in range(T):
        for d in D:
            if t + d <= T:
                for p in range(N):
                    # If p departs at t and duration is d, then at arrival it is on the other bank
                    constraints.append([-dep[(t, p, 0)], -dur[(t, d)], B[(p, t + d)]])
                    constraints.append([-dep[(t, p, 1)], -dur[(t, d)], A[(p, t + d)]])

                    # During the crossing, the chicken stays on its departure bank
                    for k in range(1, d):
                        if t + k <= T:
                            constraints.append([-dep[(t, p, 0)], -dur[(t, d)], A[(p, t + k)]])
                            constraints.append([-dep[(t, p, 1)], -dur[(t, d)], B[(p, t + k)]])

    # Inertia: a chicken keeps its bank from t to t+1 unless it arrives (changes bank) at t+1
    for t in range(T):
        for p in range(N):
            constraints.append([ARRP[(p, t + 1)], -A[(p, t)], A[(p, t + 1)]])
            constraints.append([ARRP[(p, t + 1)], -B[(p, t)], B[(p, t + 1)]])

    # --- No departures while a trip is ongoing
    for t in range(T):
        for d in D:
            for k in range(1, d):
                if t + k < T:
                    constraints.append([-dur[(t, d)], -DEP[t + k]])

    # --- ALL(t) definition and objective: exists t <= T such that all chickens are on B
    for t in range(T + 1):
        # ALL(t) -> B(p,t)
        for p in range(N):
            constraints.append([-ALL[t], B[(p, t)]])
        # (AND_p B(p,t)) -> ALL(t)  encoded as one clause
        constraints.append([-B[(p, t)] for p in range(N)] + [ALL[t]])

    # Objective: OR_t ALL(t)
    constraints.append([ALL[t] for t in range(T + 1)])

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
                    if dep[(t, p, 0)] in true_vars or dep[(t, p, 1)] in true_vars:
                        chickens.append(p + 1)
                solution.append((t, chickens))

        return solution


def find_duration(durations: list[int], c: int) -> int:
    """Return the minimal T such that gen_solution(durations, c, T) is satisfiable."""
    if not durations:
        return 0

    maxT = max(durations)

    # Exponential search for an upper bound
    lo = 0
    hi = maxT
    while gen_solution(durations, c, hi) is None:
        hi *= 2

    # Binary search on [lo, hi]
    while lo < hi:
        mid = (lo + hi) // 2
        if gen_solution(durations, c, mid) is None:
            lo = mid + 1
        else:
            hi = mid

    return lo
