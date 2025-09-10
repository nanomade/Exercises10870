import pickle

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

    # axis.legend()
    plt.show()


if __name__ == '__main__':

    results = pickle.load(open("results.p", "rb"))
    print(results)
    plot_results(results)
