import csv
import time
import datetime

import pyvisa

import numpy as np


class DataWriter:
    """
    This class provides a way to store two data-files with the same data. One
    file is named with a unique name that ensure that no data is lost. The
    other file is always called `data.csv`
    """

    def __init__(self):
        now = datetime.datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
        filename = 'data_' + now + '.csv'
        self.liveplot = open('data.csv', 'w', newline='\n')
        self.datafile = open(filename, 'w', newline='\n')
        self.livewriter = csv.writer(self.liveplot, delimiter=';')
        self.datawriter = csv.writer(self.datafile, delimiter=';')

    def write_line(self, **kwargs):
        self.livewriter.writerow(kwargs.values())
        self.datawriter.writerow(kwargs.values())
        self.liveplot.flush()
        self.datafile.flush()


class Agilent34401a:
    def __init__(self):
        rm = pyvisa.ResourceManager()
        # print(rm.list_resources())
        self.instr = rm.open_resource('ASRL1::INSTR')
        self.instr.timeout = 2000  # ms
        self.instr.write_termination = '\n'
        self.instr.read_termination = '\n'
        self.instr.baud_rate = 9600
        self.instr.data_bits = 8
        self.instr.stop_bits = pyvisa.constants.StopBits.two
        self.instr.parity = pyvisa.constants.Parity.none
        self.instr.write('*RST')
        time.sleep(0.5)
        print('SET SYSTEM REMOTE')
        self.instr.write(':SYSTEM:REMOTE')
        time.sleep(0.1)
        print('SET TRIGGER SOURCE')
        # cmd = 'SAMP:COUNT 1;:TRIG:SOUR EXT'
        cmd = 'SAMP:COUNT 1;:TRIG:SOUR IMM'
        self.instr.write(cmd)
        # cmd = 'SENSe:VOLTage:DC:NPLCycles?'
        # print(self.instr.query(cmd))

    def set_voltage_mode(self, dc=True):
        if dc:
            cmd = 'CONF:VOLT:DC 0, 1e-6'
        else:  # AC
            cmd = 'CONF:VOLT:AC 0, 1e-6'
        self.instr.write(cmd)

    def prepare_read(self):
        self.instr.write('READ?')

    def read_after_trigger(self):
        data = self.instr.read()
        value = float(data)
        return value


class DCMeasurement:
    """
    Implements several modes of Differential Conductance Measurements
    """

    def __init__(self, dmm, r_shunt):
        self.writer = DataWriter()

        self.writer.write_line(
            time='Time',
            v_total='V_total',
            v_shunt='V_shunt',
            current='Current',
            v_dut='V_dut',
            di_dv='dI_dV',
        )

        self.t_start = time.time()
        self.r_shunt = r_shunt
        self.dmm = dmm
        rm = pyvisa.ResourceManager()
        for visaRsrcAddr in rm.list_resources():
            print(visaRsrcAddr)
            if "USB0" in visaRsrcAddr:
                break
        self.awg = rm.open_resource(visaRsrcAddr)
        # self._init_channel(1)
        self._init_channel(2)
        time.sleep(2)  # Allow instruments to settle

    def _auto_range(self, channel, state):
        if state:
            cmd = 'SOURCE{}:VOLTAGE:RANGE:AUTO ON'.format(channel)
        else:
            cmd = 'SOURCE{}:VOLTAGE:RANGE:AUTO OFF'.format(channel)
        self.awg.write(cmd)

    def _init_channel(self, channel, dc=True):
        if not channel in [1, 2]:
            raise Exception('Invalid channel!')
        # Set the voltatage range high enough that
        # auto-range will go to high

        print(self.awg.query('*IDN?'))

        time.sleep(0.5)
        self._auto_range(channel, True)
        if dc:
            cmd = 'SOURCE{}:FUNCTION DC'.format(channel)
            self.awg.write(cmd)
            cmd = 'SOURCE{}:APPLY:DC DEF, DEF, 1'.format(channel)
            self.awg.write(cmd)
            self._auto_range(channel, False)
            self.set_dc_voltage(0, channel=channel)
        else:  # This is an AC-measurement
            cmd = 'SOURCE{}:FUNCTION SINUSOID'.format(channel)
            self.awg.write(cmd)
            cmd = 'SOURCE{}:VOLTAGE 1'.format(channel)
            self.awg.write(cmd)
            cmd = 'SOURCE{}:FREQUENCY 253.154'.format(channel)
            self.awg.write(cmd)
            time.sleep(5)
            self.set_dc_voltage(1)
            # self._auto_range(channel, False)
            self.set_dc_voltage(0, channel=channel)
            self.set_ac_voltage(0.1)

    def trig_external(self):
        """
        Misusing channel 2 to as external trigger, since I did not
        spend sufficient time on reading the SCPI-docs....
        """
        self.set_dc_voltage(3, channel=2)
        time.sleep(1e-3)
        self.set_dc_voltage(0, channel=2)

    def set_dc_voltage(self, voltage, channel=1):
        if not channel in [1, 2]:
            raise Exception('Invalid channel!')
        cmd = 'SOURCE{}:VOLTAGE:OFFSET {:.6f}'.format(channel, voltage)
        self.awg.write(cmd)

    def set_ac_voltage(self, voltage, channel=1):
        if not channel in [1, 2]:
            raise Exception('Invalid channel!')
        cmd = 'SOURCE{}:VOLTAGE {:.6f}'.format(channel, voltage)
        self.awg.write(cmd)

    def read_at_voltage(self, voltage):
        """
        Used by the two dc-measurements,
        similar but not identical code exists in the AC-mode code.
        """
        self.set_dc_voltage(voltage)
        time.sleep(0.002)
        self.dmm.prepare_read()
        self.trig_external()
        v_shunt = self.dmm.read_after_trigger()
        current = v_shunt / self.r_shunt
        v_dut = voltage - v_shunt
        return current, v_dut, v_shunt

    def iv_curve(self, v_from, v_to, v_step):
        """
        Simulated current-step iv-curve. Total voltage is in
        each step increased by v_step + previous v_shunt in an
        attempt to make v_dut spacing approximately constant
        """
        self._init_channel(1, dc=True)
        time.sleep(0.5)

        voltage = v_from
        v_dut = 0
        if v_to < v_from:
            print('Error v_from must by lower than v_to!')
            return

        v_shunt = 0
        while voltage < v_to:
            # Add previous v_shunt in an attempt to achive
            # constant v_dut step size
            v_actual = voltage + v_shunt
            current, v_dut, v_shunt = self.read_at_voltage(v_actual)

            msg = 'Vdut: {:.3f}V, I: {:.3f}mA'
            print(msg.format(v_dut, current * 1e3))
            voltage = voltage + v_step

            self.writer.write_line(
                time=time.time() - self.t_start,
                v_total=voltage,
                v_shunt=v_shunt,
                current=current,
                v_dut=v_dut,
                di_dv=0,
            )
        self.set_dc_voltage(0)

    def ac_sweep(self, v_from, v_to, v_step, amplitude):
        self._init_channel(1, dc=False)
        self.set_ac_voltage(amplitude)
        self.dmm.set_voltage_mode(dc=False)
        time.sleep(0.5)

        voltage = v_from
        v_dut = 0
        if v_to < v_from:
            print('Error v_from must by lower than v_to!')
            return

        v_shunt = 0
        while voltage < v_to:
            # Add previous v_shunt in an attempt to achive
            # constant v_dut step size
            v_actual = voltage + v_shunt
            self.set_dc_voltage(v_actual)
            time.sleep(0.1)

            self.dmm.set_voltage_mode(dc=True)
            time.sleep(0.5)
            self.dmm.prepare_read()
            self.trig_external()
            v_shunt = self.dmm.read_after_trigger()
            current = v_shunt / self.r_shunt
            v_dut = voltage - v_shunt

            self.dmm.set_voltage_mode(dc=False)
            time.sleep(0.75)
            self.dmm.prepare_read()
            self.trig_external()
            d_shunt = self.dmm.read_after_trigger()
            di = d_shunt / self.r_shunt
            di_dv = di / amplitude

            msg = 'Vdut: {:.3f}V, I: {:.3f}mA, di/dv: {:.3f}mA'
            print(msg.format(v_dut, current * 1e3, di_dv * 1e3))
            voltage = voltage + v_step + v_shunt

            self.writer.write_line(
                time=time.time() - self.t_start,
                v_total=voltage,
                v_shunt=v_shunt,
                current=current,
                v_dut=v_dut,
                di_dv=di_dv,
            )
        self.set_dc_voltage(0)

    def delta_sweep(self, v_from, v_to, v_step, v_delta):
        self._init_channel(1, dc=True)
        time.sleep(0.5)
        voltage = v_from

        while voltage < v_to:
            v_plus = voltage + v_delta
            v_minus = voltage - v_delta
            i1, v_dut1, v_shunt1 = self.read_at_voltage(v_plus)
            i2, v_dut2, v_shunt2 = self.read_at_voltage(v_minus)
            i3, v_dut3, v_shunt3 = self.read_at_voltage(v_plus)

            v_shunt = (v_shunt3 + v_shunt2) * 0.5
            current = (i3 + i2) * 0.5
            voltage = voltage + v_step + v_shunt
            di = 0.5 * (0.5 * (i1 - i2) + 0.5 * (i3 - i2)) / v_delta

            msg = 'I: {:.3f}mA, di: {:.3f}uA'
            print(msg.format(current * 1e3, di * 1e6))
        self.set_dc_voltage(0)


if __name__ == '__main__':
    DMM = Agilent34401a()
    DG = DCMeasurement(dmm=DMM, r_shunt=999.8)

    # DG.iv_curve(1, 2.4, 0.005)
    DG.ac_sweep(1.4, 2.3, 0.01, 0.01)
    # DG.delta_sweep(v_from=1, v_to=5, v_step=0.01, v_delta=0.05)
