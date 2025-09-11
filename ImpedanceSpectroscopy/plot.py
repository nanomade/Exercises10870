import csv

import numpy as np
import matplotlib.pyplot as plt


def plot_results(results):
    real = []
    imaginary = []
    for val in results.values():
        real.append(val[0] * np.cos(val[1]))
        imaginary.append(val[0] * abs(np.sin(val[1])))

    fig = plt.figure()
    fig.set_size_inches(20, 10)

    axis = fig.add_subplot(1, 1, 1)
    axis.plot(real, imaginary, "bo", label="")

    axis.set_xlabel("Real")
    axis.set_ylabel("Imaginary")
    # axis.set_xlim(0, 50)
    axis.legend()
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
    print(results)
    plot_results(results)
