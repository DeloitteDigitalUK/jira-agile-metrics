from ..calculator import Calculator
from ..utils import get_extension

from .cycletime import CycleTimeCalculator

class PercentilesCalculator(Calculator):
    """Build percentiles for `cycle_time` in cycle data as a DataFrame
    """

    def run(self):
        cycle_data = self.get_result(CycleTimeCalculator)
        return cycle_data['cycle_time'].dropna().quantile(self.settings['quantiles'])

    def write(self):
        output_file = self.settings['percentiles_data']
        if not output_file:
            return

        output_extension = get_extension(output_file)

        file_data = self.get_result()

        if output_extension == '.json':
            file_data.to_json(output_file, date_format='iso')
        elif output_extension == '.xlsx':
            file_data.to_frame(name='percentiles').to_excel(output_file, 'Percentiles', header=True)
        else:
            file_data.to_csv(output_file, header=True)
