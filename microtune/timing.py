import enum
from numbers import Number
from typing import Callable
import time


__all__ = [
    "Clock",
    "master_clock",
]


class ClockState(enum.Enum):

    READY    = 0
    RUNNING  = 1
    STOPPED  = 2



class Clock:

    """
    Resettable clock with sub-millisecond precision useful for providing
    accurate timestamps relative to clock initialization/start time.
    
    Parameters
    ----------
    
    start: bool (optional)
      Whether to start clock when initialized. Default is `False`.
    fn: callable (optional)
      Function that returns a timestamp when called. Default is `time.perf_counter`.

    """

    __slots__ = (
        "_state",    # ClockState
        "_t_start",  # Optional[Number]
        "_t_stop",   # Optional[Number]
        "_fn",       # Callable[[], Number]
    )

    def __init__(self,
                 start: bool = False,
                 fn: Callable[[], Number] = time.perf_counter,
                 ):


        self._fn = fn
        self.reset(start=start)


    @property
    def state(self) -> ClockState:
        return self._state

    @property
    def ready(self) -> bool:
        return self._state == ClockState.READY

    @property
    def running(self) -> bool:
        return self._state == ClockState.RUNNING

    @property
    def stopped(self) -> bool:
        return self._state == ClockState.STOPPED


    def reset(self, start: bool = False) -> None:

        self._state = ClockState.READY
        self._t_start = None
        self._t_stop = None
        if start:
            return self.start()


    def start(self) -> Number:

        if self._state != ClockState.READY:
            raise RuntimeError(f"cannot start clock in state: {self._state}")

        self._t_start = self._fn()
        self._state = ClockState.RUNNING
        return 0


    def stop(self) -> Number:

        if self._state != ClockState.RUNNING:
            raise RuntimeError(f"cannot stop clock in state: {self._state}")

        self._t_stop = self._fn()
        self._state = ClockState.STOPPED
        return self._t_stop - self._t_start


    def __call__(self) -> Number:
        if self._state != ClockState.RUNNING:
            raise RuntimeError(f"cannot get time for clock in state {self._state}")
        return self._fn() - self._t_start


master_clock = Clock(start=True)
