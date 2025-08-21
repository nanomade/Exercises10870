import csv
import time
import pathlib
import datetime
import threading

import pyvisa
import nidaqmx

CURRENT_LIMIT = 5


class PowerSupply:
    def __init__(self, port='COM1'):
        rm = pyvisa.ResourceManager()
        self.comm = rm.open_resource('COM1')
        self.comm.baud_rate = 2400
        self.comm.stop_bits = pyvisa.constants.StopBits.one
        self.comm.write_termination = '\r'
        self.max_voltage = 2
        self.voltage_setpoint = None  # Will be set to in next line
        self.set_voltage(0)

    def status(self):
        # Apparantly this does not work, perhaps the cable
        # is not crossed?
        status_raw = self.comm.query('L')
        print(status_raw)

    def set_max_voltage(self, voltage):
        """
        Software limit on the highest allowed
        voltage - prevents accidentially setting a
        too high voltage during testing.
        """
        if voltage > 20:
            self.max_voltage = 20
        else:
            self.max_voltage = voltage

    def set_voltage(self, voltage):
        """
        Set the wanted output voltage setpoint. If higher
        than current max_voltage, the max value will used
        Voltages lower than zero will be treated as zero.
        """
        if voltage <= self.max_voltage:
            actual_voltage = voltage
        elif voltage < 0:
            actual_voltage = 0
        else:
            actual_voltage = self.max_voltage

        self.voltage_setpoint = actual_voltage
        cmd = 'SV {:.2f}'.format(actual_voltage)
        self.comm.write(cmd)

    def set_current_limit(self, current):
        """
        Set the current limit of the device
        """
        if current < 10:
            actual_current = current
        else:
            actual_current = 9.99  # Max for the device
        if current < 0:
            actual_current = 0.01

        cmd = 'SI {:.2f}'.format(actual_current)
        self.comm.write(cmd)


class TemperatureReader(threading.Thread):
    """
    Class to read temperature from DAQ-card inside the PC. The nidaq drivers
    are fairly magic and not a focus of this excercise - do not spend too much
    time to understand this - just know that the class will provide a steady
    supply of temperature readings.
    """

    def __init__(self):
        super().__init__()
        self.temperature = 999
        self.running = True
        self.error = 0

    def stop(self):
        self.running = False

    def run(self):
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_thrmcpl_chan(
                "SCC1Mod1/ai0",
                name_to_assign_to_channel="",
                min_val=0.0,
                max_val=500.0,
                units=nidaqmx.constants.TemperatureUnits.DEG_C,
                thermocouple_type=nidaqmx.constants.ThermocoupleType.K,
                cjc_source=nidaqmx.constants.CJCSource.BUILT_IN,
            )
            while self.running:
                time.sleep(0.25)
                try:
                    data = task.read(1, 10)
                    self.temperature = data[0]
                    self.error = 0
                except nidaqmx.errors.DaqReadError as e:
                    self.error += 1
                    if self.error > 10:
                        print(e)
                        print('Temperature read error: {}'.format(self.error))
                if self.error > 20:
                    self.running = False
                    self.temperature = 999


class DataWriter:
    """
    This class provides a way to store two data-files with the same data. One
    file is named with a unique name that ensure that no data is lost. The
    other file is always called `pid_plot.csv` and will be used by the plotting
    programm.
    """

    def __init__(self):
        now = datetime.datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
        filename = 'data_' + now + '.csv'
        self.liveplot = open('pid_plot.csv', 'w', newline='\n')
        self.datafile = open(filename, 'w', newline='\n')
        self.livewriter = csv.writer(self.liveplot, delimiter=';')
        self.datawriter = csv.writer(self.datafile, delimiter=';')

    def write_line(self, **kwargs):
        self.livewriter.writerow(kwargs.values())
        self.datawriter.writerow(kwargs.values())
        self.liveplot.flush()
        self.datafile.flush()


class Regulator:
    """
    Abstract regulator class.
    This calss cannot run by itself since _update_ps_output is not
    impletented. It provides most of the machinery to read setpoint,
    save data, handling of the power supply etc.
    To use the class - inherit it and override _update_ps_output.
    """

    def __init__(self, max_voltage=8):
        self.datawriter = DataWriter()
        self.t_start = time.time()
        self.ps = PowerSupply()
        self.ps.set_max_voltage(max_voltage)
        self.ps.set_current_limit(CURRENT_LIMIT)
        self.setpoint = 0
        self.parameters = {'max_voltage': max_voltage}
        self.running = True

    def set_setpoint(self, setpoint):
        self.setpoint = setpoint

    def _record_data_point(self, temperature):
        dt = time.time() - self.t_start
        voltage_setpoint = self.ps.voltage_setpoint
        self.datawriter.write_line(
            time=dt,
            temperature=temperature,
            voltage_setpoint=voltage_setpoint,
            temperature_setpoint=self.setpoint,
            params=self.parameters,
        )

    def _update_ps_output(self, error):
        raise NotImplementedError

    def _update_setpoint(self):
        setpoint_file = pathlib.Path('setpoint.txt')
        try:
            with setpoint_file.open() as f:
                setpoint_raw = f.read()
        except FileNotFoundError:
            print('Setpoint file not found')
            setpoint_raw = '0'

        try:
            setpoint = float(setpoint_raw)
        except ValueError:
            print('Unable to parse saetpoint as float')
            setpoint = 0
        return setpoint

    def update(self, temperature):
        setpoint = self._update_setpoint()
        if setpoint > 0:
            self.setpoint = setpoint
        else:
            self.running = False
            return

        temp_error = temperature - self.setpoint
        self._update_ps_output(temp_error)
        self._record_data_point(temperature)


class BangBangRegulator(Regulator):
    """
    Example of how to use the Regulator base class.
    This class implements a simple bang-bang protocol.
    """

    def __init__(self, max_voltage=8):
        super().__init__(max_voltage=max_voltage)
        self.bang_bang_voltage = max_voltage
        self.set_setpoint(10)

    def _update_ps_output(self, error):
        msg = 'error={:.1f}C. S={:.1f}C'
        print(msg.format(error, self.setpoint))
        if error < 0:
            wanted_voltage = self.bang_bang_voltage
        else:
            wanted_voltage = 0
        self.ps.set_voltage(wanted_voltage)
        self.parameters = {
            'max_voltage': self.ps.max_voltage,
            'p': 0,
            'i': 0,
            'd': 0,
        }


def run_regulator():
    regulator = BangBangRegulator(max_voltage=10)

    # These do not exist until you make them :)
    # regulator = PRegulator(max_voltage=10)
    # regulator = PIRegulator(max_voltage=10)
    # regulator = PIDRegulator( max_voltage=10)

    tr = TemperatureReader()
    tr.start()
    time.sleep(1)

    while regulator.running:
        time.sleep(0.25)
        temperature = tr.temperature
        regulator.update(temperature)

    ps.set_voltage(0)
    tr.stop()


if __name__ == '__main__':
    run_regulator()
