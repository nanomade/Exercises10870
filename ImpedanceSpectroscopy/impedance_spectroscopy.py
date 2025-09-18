import csv
import math
import time
import pyvisa
import nidaqmx
import numpy as np
import scipy as sp

import matplotlib.pyplot as plt


sample_rate = 5e5
min_val = -1
max_val = 1
# samples = 100000
terminal_config = nidaqmx.constants.TerminalConfiguration.DIFF

FIT_PARAMS = {
    # 'method': 'lm',
    "method": "trf",
    "jac": "3-point",
    "ftol": 1e-14,
    "xtol": 1e-14,
    "gtol": 1e-14,
    "loss": "soft_l1",
    "max_nfev": 20000,
    # 'max_nfev': 1000,
}


def read_data(freq):
    samples = 2 * np.pi * 3 * math.floor((sample_rate / freq))
    x_data = np.arange(1.0 / sample_rate, samples / sample_rate, 1.0 / sample_rate)
    # Due to rounding, x_data can miss a point, make sure they have
    # same length:
    samples = len(x_data)

    with nidaqmx.Task() as task:
        # 9V label
        task.ai_channels.add_ai_voltage_chan(
            "Dev1/ai3",
            terminal_config=terminal_config,
            min_val=min_val,
            max_val=max_val,
        )
        # H label
        task.ai_channels.add_ai_voltage_chan(
            "Dev1/ai2",
            terminal_config=terminal_config,
            min_val=min_val,
            max_val=max_val,
        )

        task.timing.cfg_samp_clk_timing(
            rate=sample_rate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samples * 2,
        )
        data = task.read(number_of_samples_per_channel=(samples))
    return x_data, data


def plot_data(x, y1, y2=None, label1='y1', label2='y2'):
    fig = plt.figure()
    fig.set_size_inches(20, 10)

    axis = fig.add_subplot(1, 1, 1)
    axis.plot(x * 1e3, y1, "b-", label=label1)
    if y2 is not None:
        axis.plot(x * 1e3, y2, "r-", label=label2)

    axis.set_xlabel("Time / ms")
    axis.set_ylabel("Voltage / V")
    # axis.set_xlim(0, 5)

    axis.legend()
    plt.show()


def find_main_frequency(data):
    # Numpy magic to extract main tone
    # In principle we do not need this, since we set the frequency in the experiment
    mean_value = sum(data) / len(data)
    fft_data = abs(np.fft.fft(np.array(data) - mean_value))
    freqs = np.fft.fftfreq(len(data))
    peak_coefficient = np.argmax(np.abs(fft_data))
    peak_freq = freqs[peak_coefficient]
    peak_freq_calibrated = abs(peak_freq * sample_rate)
    main_omega = peak_freq_calibrated * 2 * np.pi
    return main_omega


def sine_fit_func(p, x, freq):
    # value =  p[0] * np.sin(p[2] * 2 * math.pi * x + p[1])
    # value =  p[0] * np.sin(p[2] * 2 * math.pi * x + p[1])
    # value = amplitude * np.sin(freq * 2 * math.pi * x + phase)
    value = p[0] * np.sin(freq * x + p[1])
    return value


def sine_error_func(p, x, y, freq):
    error = sine_fit_func(p, x, freq) - y
    return error


def find_data_amp_and_phase(x_data, data):
    freq = find_main_frequency(data)
    # print('Detected frequency: {}Hz'.format(freq))
    amp_guess = (max(data) - min(data)) / 2
    print('Amplitude estimate: {:.1f}mV'.format(amp_guess * 1000))

    if len(x_data) > 1500:
        fit_length = 1500
    else:
        fit_length = len(x_data)

    error_min = 99999999999
    phase_guesses = np.arange(0, 6, 0.05)

    for phase_guess in phase_guesses:
        p0 = [amp_guess, phase_guess]
        error = 0
        for i in range(0, fit_length):
            sine_fit = sine_fit_func(p0, x_data[i], freq)
            error += (data[i] - sine_fit) ** 2

        if error < error_min:
            error_min = error
            phase = phase_guess
    # print('Phase guess: ', phase)
    p0 = [amp_guess, phase]

    plot_initial_guess = True
    if plot_initial_guess:
        plot_data(x_data, data, sine_fit_func(p0, x_data, freq), 'raw', 'initial guess')

    fit = sp.optimize.least_squares(
        sine_error_func,
        p0,
        args=(x_data, data, freq),
        # bounds=bounds,
        **FIT_PARAMS
    )

    # If you want to plot the fitted data, uncomment here
    plot_fitted = True
    if plot_fitted:
        plot_data(
            x_data, data, sine_fit_func(fit.x, x_data, freq), 'raw', 'fitted data'
        )
    # print(fit)
    amplitude = fit.x[0]
    phase = fit.x[1]
    return amplitude, phase, fit


def set_frequency(freq):
    rotational_frequency = freq / (2 * math.pi)
    rm = pyvisa.ResourceManager()
    for visaRsrcAddr in rm.list_resources():
        if "USB0" in visaRsrcAddr:
            break
    awg = rm.open_resource(visaRsrcAddr)
    awg.write("FREQ {}".format(rotational_frequency))
    time.sleep(0.1)


def test_a_frequency(freq):
    set_frequency(freq)
    x_data, data = read_data(freq)
    current = data[0]
    voltage = data[1]

    i_amp, i_phase, fit_i = find_data_amp_and_phase(x_data, current)
    v_amp, v_phase, fit_v = find_data_amp_and_phase(x_data, voltage)

    phase_shift = i_phase - v_phase
    # NOTICE!!! 1000ohm is assumed as shunt!!!!!
    impedance = 1000 * v_amp / i_amp

    msg = "I: {:.2f}mA.  V: {:.2f}V. |Z|: {:.2f}ohm"
    print(msg.format(1000 * i_amp / 1000, v_amp, 1000 * v_amp / i_amp))
    msg = "PhaseI: {:.2f}.  PhaseU: {:.2f}. Phase-shift: {:.2f}"
    print(msg.format(i_phase, v_phase, phase_shift))

    # plot_data(x_data, current, voltage, 'Current', 'Voltage')
    plot_data(
        x_data,
        sine_fit_func(fit_i.x, x_data, freq),
        sine_fit_func(fit_v.x, x_data, freq),
        'Current',
        'Voltage',
    )

    return impedance, phase_shift


def perform_a_sweep():
    results = {}
    for freq in np.logspace(2, 4, num=30):
        print("Testing: {}".format(freq))
        impedance, phase_shift = test_a_frequency(freq)
        results[freq] = (impedance, phase_shift)

    filename = 'results.csv'
    datafile = open(filename, 'w', newline='\n')
    datawriter = csv.writer(datafile, delimiter=';')
    for freq, values in results.items():
        datawriter.writerow([freq, values[0], values[1]])
    datafile.flush()


if __name__ == "__main__":
    # test_a_frequency(4000)
    perform_a_sweep()
