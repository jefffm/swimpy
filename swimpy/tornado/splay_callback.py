import random

from tornado.ioloop import PeriodicCallback, IOLoop


class PeriodicCallbackWithSplay(PeriodicCallback):
    """
    This class overrides the tornado PeriodicCallback to allow configuring a percentage of "splay" to apply to each
    periodic task.

    Running periodic tasks with a certain amount of "wiggle room" for scheduled times is a general best practice for
    systems where many jobs can be scheduled at once.

    For example, if we configured 20 callbacks at 1 minute intervals, and each callback lasted only a few seconds,
    rather than attempting to schedule all 20 to run at exactly the same time, applying a 100% splay would randomly
    spread each callback to run any time within that minute.
    """

    # noinspection PyMissingConstructor
    def __init__(self, callback, callback_time, splay_pct=10, io_loop=None):
        """
        We override the __init__ without calling super so that we can intercept calls to self.callback_time with a
        property that dynamically applies the splay_pct. Using super() would set self.callback_time to the attribute
        directly.

        :param callback:
        :param callback_time:
        :param splay_pct: Percentage to shift the interval by. Defaults to 10% splay
        :param io_loop: IOLoop to schedule callback on. Defaults to the current thread instance
        """
        self.callback = callback
        if callback_time <= 0:
            raise ValueError("Periodic callback must have a positive callback_time")
        self.io_loop = io_loop or IOLoop.current()
        self._running = False
        self._timeout = None

        self._configured_callback_time = callback_time
        self.splay_pct = splay_pct

    @staticmethod
    def _calculate_splay(interval, splay_pct):
        """
        Calculate an interval based on a "splay percent"

        :param interval: integer, minutes to wait between callbacks
        :param splay_pct: integer or float, percentage to splay the interval by.

        For example, with an interval of 10 minutes and a splay of (up to) 20%, the callback will be scheduled sometime
        between every 8 and 12 minutes

        :return: Interval, nudged forward or backward by a percent
        """
        assert 0 <= splay_pct <= 100, 'Splay percent should be between 0 and 100. Got: {!r}'.format(splay_pct)

        # We want to center the splay on zero, such that 20% splay is +/- 10% of the interval
        splay_lower_bound = (splay_pct / 2.0) * -1
        splay_upper_bound = (splay_pct / 2.0)

        # Convert to decimal and select a splay between the lower and upper bounds of the splay
        splay = 0.1 * random.randint(splay_lower_bound, splay_upper_bound)

        # Apply the splay to get the interval
        return interval + (interval * splay)

    @property
    def callback_time(self):
        return self._calculate_splay(self._configured_callback_time, self.splay_pct)