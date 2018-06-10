import logging

logger = logging.getLogger(__name__)

class Calculator(object):
    """Base class for calculators.
    """

    def __init__(self, query_manager, settings, results):
        """Initialise with a `QueryManager`, a dict of `settings`,
        and a reference to the dict of `results`, which will be
        used to store intermeidary results.
        """

        self.query_manager = query_manager
        self.settings = settings
        self._results = results

    def get_result(self, calculator=None, default=None):
        """Get the results calculated by a previous calculator
        of type `calculator` (a class). Defaults to `self.__class__`
        """

        return self._results.get(calculator or self.__class__, default)

    # Lifecycle methods -- implement as appropriate

    def run(self):
        """Run the calculator and return its results.
        These will be automatically saved
        """

    def write(self):
        """Write any output files to the filesystem in the given
        target directory.
        """

def run_calculators(calculators, query_manager, settings):
    """Run all calculators passed in, in the order listed.
    Returns the aggregated results.
    """

    results = {}
    calculators = [C(query_manager, settings, results) for C in calculators]
    failed = set()

    # Run all calculators first
    for c in calculators:
        logger.info("%s running...", c.__class__.__name__)
        try:
            results[c.__class__] = c.run()
        except Exception as e:
            failed.add(c)
            logger.exception("%s failed with a fatal error. Subsequent calculators may also fail as a result.", c.__class__.__name__)
        else:
            logger.info("%s completed\n", c.__class__.__name__)

    # Write all files as a second pass
    for c in calculators:
        logger.info("Writing file for %s...", c.__class__.__name__)
        try:
            c.write()
        except Exception as e:
            logger.exception("%s failed with a fatal error. Subsequent calculators may also fail as a result.", c.__class__.__name__)
        else:
            logger.info("%s completed\n", c.__class__.__name__)

    return results
