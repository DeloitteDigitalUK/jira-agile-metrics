import json

from .cli import (
    to_quantiles,
    override_options
)

def test_to_quantiles():
    assert to_quantiles("0.1,0.5,0.6") == [0.1, 0.5, 0.6]
    assert to_quantiles("0.1, 0.5, 0.6") == [0.1, 0.5, 0.6]
    assert to_quantiles(".1, 0.5,.6") == [0.1, 0.5, 0.6]
    assert to_quantiles("") == []
    assert to_quantiles("1,2,3") == [1.0, 2.0, 3.0]

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
