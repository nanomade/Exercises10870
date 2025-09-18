import csv

import numpy as np
import matplotlib.pyplot as plt


def plot_results(results):
    frequency = []
    shift = []
    real = []
    imaginary = []
    for freq, val in results.items():
        frequency.append(freq)
        phase_shift = val[1]  # % np.pi
        print('{:.3f} '.format(phase_shift / np.pi), end='')
        # print(phase_shift, np.pi / 2)
        if phase_shift < 0:
            phase_shift += 2* np.pi
        if phase_shift > np.pi / 4:
            phase_shift = phase_shift - (np.pi / 2)
        print('{:.3f}'.format(phase_shift / np.pi))
        shift.append(phase_shift)
        real.append(val[0] * np.cos(phase_shift))
        imaginary.append(val[0] * np.sin(phase_shift))

    fig = plt.figure()
    fig.set_size_inches(20, 10)

    ax1 = fig.add_subplot(2, 1, 1)
    ax1.plot(real, imaginary, "bo", label="")
    ax1.set_xlabel("Real")
    ax1.set_ylabel("Imaginary")

    ax2 = fig.add_subplot(2, 1, 2)
    ax2.plot(frequency, shift, "bo", label="")
    ax2.set_xlabel('Angular frequency')
    ax2.set_ylabel('Phase shift / rad')

    plt.show()


def load_data():
    results = {}
    with open('results.csv', 'r', newline='\n') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            freq = float(row[0])
            results[freq] = (float(row[1]), float(row[2]))
    return results


if __name__ == '__main__':
    results = load_data()
    # print(results)
    plot_results(results)
