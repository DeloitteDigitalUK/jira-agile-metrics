import json

from .cli import (
    override_options
)

def test_override_options():

    class FauxArgs:
        def __init__(self, opts):
            self.__dict__.update(opts)
            for k, v in opts.items():
                setattr(self, k, v)

    options = {'one': 1, 'two': 2}
    override_options(options, FauxArgs({}))
    assert json.dumps(options) == json.dumps({'one': 1, 'two': 2})
    
    options = {'one': 1, 'two': 2}
    override_options(options, FauxArgs({'one': 11}))
    assert json.dumps(options) == json.dumps({'one': 11, 'two': 2})

    options = {'one': 1, 'two': 2}
    override_options(options, FauxArgs({'three': 3}))
    assert json.dumps(options) == json.dumps({'one': 1, 'two': 2})
