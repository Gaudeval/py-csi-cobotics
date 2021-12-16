from mtfl import WeakUntil
from mtfl.sugar import env, alw, implies, until, timed_until

F = env
G = alw


def weak_until(phi, psi):
    return WeakUntil(phi, psi)