import csv

import numpy as np
import matplotlib.pyplot as plt


def plot_results(results):
    fig = plt.figure()
    fig.set_size_inches(20, 10)

    ax1 = fig.add_subplot(2, 1, 1)
    ax1.plot(results['V_dut'], results['Current'], 'b.', label='')
    ax1.set_xlabel('Vdut')
    ax1.set_ylabel('Current')

    ax2 = fig.add_subplot(2, 1, 2)
    ax2.plot(results['V_dut'], results['dI_dV'], 'b.', label='Measured')
    ax2.plot(results['V_dut'], results['dI_dV_calculated'], 'r.', label='Calculated')
    ax2.set_xlabel('Vdut')
    ax2.set_ylabel('dI_dV - measured')
    ax2.legend(loc=2, prop={"size": 8})

    plt.show()


def differntiate_iv(results):
    results['dI_dV_calculated'] = [0]
    for i in range(1, len(results['Current'])):
        di = results['Current'][i] - results['Current'][i - 1]
        dv = results['V_dut'][i] - results['V_dut'][i - 1]
        di_dv_calculated = di / dv
        results['dI_dV_calculated'].append(di_dv_calculated)
    return results


def load_data():
    results = {}
    with open('data.csv', 'r', newline='\n') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for line in reader:
            # Check for out-of-range values and skip line in case one is present
            skip = False
            for val in line.values():
                if float(val) > 1e10:
                    skip = True
            if skip:
                continue
            for key, val in line.items():
                if not key in results:
                    results[key] = []
                results[key].append(float(val))
    return results


if __name__ == '__main__':
    results = load_data()
    # print(results)
    results = differntiate_iv(results)
    plot_results(results)
