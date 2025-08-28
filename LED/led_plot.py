import csv
import json
import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider


class Plotter:
    def __init__(self):
        self._clear_data()
        self.running = True
        self.max_time = 0
        self.iv_plot_min_voltage = 1

    def _clear_data(self):
        self.data = {
            'time': [],
            'v_tot': [],
            'current': [],
            'v_led': [],
        }
        return

    def on_close(self, event):
        self.running = False

    def update_sweep(self):
        self.read_data()
        max_time = self.data['time'][-1]
        if max_time > self.max_time:
            self.max_time = max_time
        else:
            plt.pause(0.01)
            # return 0.1

        try:
            max_current = max(self.data['current'])
            max_voltage = max(self.data['v_led'])
        except ValueError:
            max_current = 1
            max_voltage = 1

        self.fig.canvas.flush_events()
        self.time_voltage_plot[0].set_xdata([self.data['time']])
        self.time_voltage_plot[0].set_ydata([self.data['v_led']])
        self.time_current_plot[0].set_xdata([self.data['time']])
        self.time_current_plot[0].set_ydata([self.data['current']])

        self.ax1.set_xlim(0, self.data['time'][-1])
        self.ax1_2.set_xlim(0, self.data['time'][-1])
        self.ax1.set_ylim(0, max_voltage)
        self.ax1_2.set_ylim(0, max_current)

        self.iv_plot[0].set_xdata([self.data['v_led']])
        self.iv_plot[0].set_ydata([self.data['current']])
        self.ax2.set_xlim(self.iv_plot_min_voltage, max_voltage)
        self.ax2.set_ylim(1e-4, max_current)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.01)
        return 0.5

    def plot_sweep(self):
        plt.ion()
        self.fig = plt.figure()

        # Temperature plot
        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax1.set_xlabel('Time / s')
        self.ax1.set_ylabel('Current / mA')
        self.ax1_2 = self.ax1.twinx()
        self.time_voltage_plot = self.ax1.plot(
            self.data['time'],
            self.data['v_led'],
            'k.',
            label='Voltage',
        )
        self.ax1.set_ylabel('Voltage / V')

        self.time_current_plot = self.ax1_2.plot(
            self.data['time'], self.data['current'], 'b.', label='Current'
        )
        self.ax1_2.set_ylabel('Current / mA')

        lines = self.time_current_plot + self.time_voltage_plot
        labels = [l.get_label() for l in lines]
        self.ax1.legend(lines, labels, loc=0)
        # self.ax1.legend(loc=2, prop={"size": 8})

        # IV plot
        self.ax2 = self.fig.add_subplot(2, 1, 2)
        self.iv_plot = self.ax2.plot(self.data['v_led'], self.data['current'], 'k.-')
        self.ax2.set_xlabel('Voltage / V')
        self.ax2.set_ylabel('Current / mA.')

        self.ax_slider = self.fig.add_axes([0.1, 0.05, 0.85, 0.025])
        self.iv_slider = Slider(
            ax=self.ax_slider,
            label='Scale',
            valmin=0.1,
            valmax=4,
            valinit=1,
        )

        def update_iv_ax(val):
            self.iv_plot_min_voltage = self.iv_slider.val
        self.iv_slider.on_changed(update_iv_ax)

        self.fig.canvas.mpl_connect('close_event', self.on_close)
        return

    def read_data(self):
        self._clear_data()
        with open('led_plot.csv', 'r', newline='\n') as csvfile:
            # reader = csv.reader(csvfile, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
            reader = csv.reader(csvfile, delimiter=';')
            fields = ['time', 'v_tot', 'v_led', 'current']
            for row in reader:
                n = 0
                for field in fields:
                    self.data[field].append(float(row[n]))
                    n += 1


if __name__ == '__main__':
    plot = Plotter()

    plot.read_data()
    plot.plot_sweep()
    wait = 0.5
    while plot.running:
        time.sleep(wait)
        try:
            wait = plot.update_sweep()
        except:
            print('klaf')
            pass
