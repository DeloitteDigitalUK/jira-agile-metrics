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

    def initialize(self):
        """Initialize the calculator
        """

    def is_enabled(self):
        """Return True if this calculator should be run
        """
        return True

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

    # Initialise all
    for c in calculators:
        c.initialize()

    # Run all
    for c in calculators:
        if c.is_enabled():
            results[c.__class__] = c.run()

    # Write all files
    for c in calculators:
        if c.is_enabled():
            c.write()

    return results
