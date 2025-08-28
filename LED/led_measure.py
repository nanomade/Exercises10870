import csv
import time
import datetime

import pyvisa
import nidaqmx


class PowerSupply:
    """
    Same driver as for the PID-exercise - copied here to not have to worry
    about import errors during the exercise.
    """

    def __init__(self, port='COM1'):
        rm = pyvisa.ResourceManager()
        self.comm = rm.open_resource('COM1')
        self.comm.baud_rate = 2400
        self.comm.stop_bits = pyvisa.constants.StopBits.one
        self.comm.write_termination = '\r'
        self.max_voltage = 5
        self.voltage_setpoint = None  # Will be set to in next line
        self.set_voltage(0)

    def status(self):
        # Apparantly this does not work, perhaps the cable
        # not crossed?
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
        Voltages lower than zero will be trated as zero.
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
        elif current < 0:
            actual_current = 0.01
        else:
            actual_current = 9.99  # Max for the device
        cmd = 'SI {:.2f}'.format(actual_current)
        self.comm.write(cmd)


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
        self.liveplot = open('led_plot.csv', 'w', newline='\n')
        self.datafile = open(filename, 'w', newline='\n')
        self.livewriter = csv.writer(self.liveplot, delimiter=';')
        self.datawriter = csv.writer(self.datafile, delimiter=';')

    def write_line(self, **kwargs):
        self.livewriter.writerow(kwargs.values())
        self.datawriter.writerow(kwargs.values())
        self.liveplot.flush()
        self.datafile.flush()


class DataReader:
    def __init__(self):
        self.shunt = 100  # ohm
        self.sample_rate = 1000
        self.samples = 250

    def _read_channel_voltage(self, channel):
        """
        This is just a look-up table of the configuration of the break-out box
        for the DAQ-card.
        Returns a voltage reading of either the LED or the shunt.
        """
        if channel == 'v_led':
            dev = 'Dev1/ai6'
            config = nidaqmx.constants.TerminalConfiguration.NRSE
        if channel == 'v_shunt':
            dev = 'Dev1/ai3'
            config = nidaqmx.constants.TerminalConfiguration.DIFF

        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                dev,
                terminal_config=config,
                min_val=0,
                max_val=10,
            )
            task.timing.cfg_samp_clk_timing(
                rate=self.sample_rate,
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=self.samples,
            )
            data = task.read(number_of_samples_per_channel=(self.samples))
        value = sum(data) / self.samples
        return value

    def read_current(self):
        """
        Read the current (in mA!) through the LED by measuring the voltage
        drop over the shunt.
        """
        voltage = self._read_channel_voltage('v_shunt')
        current = 1000 * voltage / self.shunt
        return current

    def read_voltage(self):
        """
        Read the LED voltage
        """
        voltage = self._read_channel_voltage('v_led')
        return voltage


class LEDSweeper:
    def __init__(self):
        self.ps = PowerSupply()
        self.ps.set_voltage(0)
        self.reader = DataReader()
        self.writer = DataWriter()
        time.sleep(0.2)
        # Measure the offset at zero - this is typically
        # not very large and could be omitted
        self.i_0 = self.reader.read_current()
        self.t_start = time.time()

    def sweep(self, max_current=10):
        """
        Sweep from 0mA to a given max_current (in mA).
        Notice that the power supply is not good at regulating current,
        sweep is performed by sweeping voltage until desired current is
        reached.
        """
        current = 0
        voltage = 1  # No usable data below 1V
        while current < max_current:
            voltage += 0.01
            self.ps.set_voltage(voltage)
            time.sleep(0.1)
            dt = time.time() - self.t_start
            current = self.reader.read_current() - self.i_0
            led_voltage = self.reader.read_voltage()
            msg = 'PS: {:.3f}V, I={:.3f}mA, V_LED={:.3f}V'
            print(msg.format(voltage, current, led_voltage))
            self.writer.write_line(
                time=dt,
                voltage_setpoint=voltage,
                v_led=led_voltage,
                current=current,
            )
        self.ps.set_voltage(0)


if __name__ == '__main__':
    sweep = LEDSweeper()
    sweep.sweep(1)
