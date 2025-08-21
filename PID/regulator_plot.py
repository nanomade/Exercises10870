import csv
import json
import time

import numpy as np
import matplotlib.pyplot as plt


class Plotter:
    def __init__(self):
        self._clear_data()
        self.running = True
        self.max_time = 0

    def _clear_data(self):
        self.data = {
            'time': [],
            'temperature': [],
            'voltage': [],
            'setpoint': [],
            'extra_data': {},
        }
        return

    def on_close(self, event):
        self.running = False

    def update_spectrum(self):
        self.read_data()
        max_time = self.data['time'][-1]
        if max_time > self.max_time:
            self.max_time = max_time
        else:
            plt.pause(0.01)
            # return 0.1

        try:
            max_temperature = max(self.data['temperature'])
            max_voltage = max(self.data['voltage'])
        except ValueError:
            max_temperature = 1
            max_voltage = 1

        self.fig.canvas.flush_events()
        self.temperature_plot.set_xdata([self.data['time']])
        self.temperature_plot.set_ydata([self.data['temperature']])
        self.setpoint_plot.set_xdata([self.data['time']])
        self.setpoint_plot.set_ydata([self.data['setpoint']])

        self.ax1.set_xlim(0, self.data['time'][-1])
        self.ax1.set_ylim(0, max_temperature)

        self.voltage_plot.set_xdata([self.data['time']])
        self.voltage_plot.set_ydata([self.data['voltage']])
        self.ax2.set_xlim(0, self.data['time'][-1])
        self.ax2.set_ylim(0, max_voltage)

        self.p_plot.set_xdata([self.data['time']])
        self.p_plot.set_ydata([self.data['extra_data']['p']])
        self.i_plot.set_xdata([self.data['time']])
        self.i_plot.set_ydata([self.data['extra_data']['i']])
        self.d_plot.set_xdata([self.data['time']])
        self.d_plot.set_ydata([self.data['extra_data']['d']])

        if len(self.data['time']) > 20:
            n = -20
        else:
            n = -1

        max_y_scale = max(
            max(self.data['extra_data']['max_voltage'][n:]),
            max(self.data['extra_data']['p'][n:]),
            max(self.data['extra_data']['i'][n:]),
            max(self.data['extra_data']['d'][n:]),
        )
        min_y_scale = min(
            min(self.data['extra_data']['max_voltage'][n:]),
            min(self.data['extra_data']['p'][n:]),
            min(self.data['extra_data']['i'][n:]),
            min(self.data['extra_data']['d'][n:]),
        )
        print(max_y_scale, min_y_scale)
        self.ax3.set_xlim(0, self.data['time'][-1])
        self.ax3.set_ylim(min_y_scale, max_y_scale)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.01)
        return 0.5

    def plot_spectrum(self):
        plt.ion()
        self.fig = plt.figure()

        # Temperature plot
        self.ax1 = self.fig.add_subplot(3, 1, 1)
        (self.temperature_plot,) = self.ax1.plot(
            self.data['time'], self.data['temperature'], 'b.', label='Temperature'
        )
        (self.setpoint_plot,) = self.ax1.plot(
            self.data['time'], self.data['setpoint'], 'r-', label='Setpoint'
        )
        self.ax1.set_xlabel('Time / s')
        self.ax1.set_ylabel('Temperature / C')
        self.ax1.legend(loc=2, prop={"size": 8})
        self.ax1_2 = self.ax1.twinx()
        # self.res_plot, = self.ax1_2.plot(
        #     self.data['time'],
        #     np.array(self.data['temperature']) - np.array(self.data['setpoint']),
        #     'k.', label='Residual'
        # )

        # Voltage plot
        self.ax2 = self.fig.add_subplot(3, 1, 2)
        (self.voltage_plot,) = self.ax2.plot(
            self.data['time'], self.data['voltage'], 'k.-'
        )
        self.ax2.set_xlabel('Time / s')
        self.ax2.set_ylabel('Voltage / V.')

        # Extra plot
        self.ax3 = self.fig.add_subplot(3, 1, 3)
        (self.p_plot,) = self.ax3.plot([0], [0], 'r.', label='P')
        (self.i_plot,) = self.ax3.plot([0], [0], 'b.', label='I')
        (self.d_plot,) = self.ax3.plot([0], [0], 'k.', label='D')
        (self.max_plot,) = self.ax3.plot([0], [0], 'g.', label='Max voltage')
        self.ax3.set_xlabel('Time / s')
        self.ax3.set_ylabel('Magnitude')
        self.ax3.legend(loc=2, prop={"size": 8})

        self.fig.canvas.mpl_connect('close_event', self.on_close)
        return

    def read_data(self):
        self._clear_data()
        with open('pid_plot.csv', 'r', newline='\n') as csvfile:
            # reader = csv.reader(csvfile, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
            reader = csv.reader(csvfile, delimiter=';')
            fields = ['time', 'temperature', 'voltage', 'setpoint']
            for row in reader:
                n = 0
                for field in fields:
                    self.data[field].append(float(row[n]))
                    n += 1
                extra_data = json.loads(row[n].replace('\'', '"'))
                for key, value in extra_data.items():
                    if key not in self.data['extra_data']:
                        self.data['extra_data'][key] = []
                    self.data['extra_data'][key].append(value)


if __name__ == '__main__':
    plot = Plotter()

    plot.read_data()
    plot.plot_spectrum()
    # plot.running = False
    wait = 0.5
    while plot.running:
        time.sleep(wait)
        try:
            wait = plot.update_spectrum()
        except:
            print('klaf')
            pass
