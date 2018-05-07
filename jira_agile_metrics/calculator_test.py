from .calculator import (
    Calculator,
    run_calculators
)

def test_run_calculator():
    
    written = []

    class Enabled(Calculator):

        def run(self):
            return "Enabled"
        
        def write(self):
            written.append("Enabled")
    
    class Disabled(Calculator):

        def run(self):
            return "Disabled"
        
        def write(self):
            pass

    class GetPreviousResult(Calculator):

        def run(self):
            return self.get_result(Enabled) + " " + self.settings['foo']
        
        def write(self):
            written.append(self.get_result())
    
    calculators = [Enabled, Disabled, GetPreviousResult]
    query_manager = object()
    settings = {'foo': 'bar'}

    results = run_calculators(calculators, query_manager, settings)

    assert results == {
        Enabled: "Enabled",
        Disabled: "Disabled",
        GetPreviousResult: "Enabled bar"
    }

    assert written == ["Enabled", "Enabled bar"]
