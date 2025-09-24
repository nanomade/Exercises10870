import matplotlib
import matplotlib.pyplot as plt

from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset

import numpy as np
matplotlib.rc('text',usetex=True) # Magic fix for the font warnings

fig = plt.figure()
fig.subplots_adjust(left=0.15)
fig.subplots_adjust(bottom=0.15)
fig.subplots_adjust(right=0.9)

# ratio = 0.617
ratio = 0.4
fig_width = 12 / 2.54 # width in cm converted to inches
fig_height = fig_width*ratio
fig.set_size_inches(fig_width, fig_height)


ax = fig.add_subplot(1,1,1)

y_values = []
for x in range(0, 40):
    for x_pertub in range(0, 20):
        y_pertub = 0.6
        y = x + y_pertub
        y_values.append(y)
    for x_pertub in range(0, 20):
        y_pertub = -0.6
        y = x + y_pertub
        y_values.append(y)
x_values = range(0, len(y_values))
ax.plot(x_values, y_values, 'b-')
ax.plot([0, max(x_values)], [min(y_values), max(y_values)], 'r-')

ax.set_xlabel('Tid', fontsize=11)
ax.set_ylabel('Eksitation', fontsize=11)
# Remove axis ticks, this is conceptual drawing
plt.xticks([]) 
plt.yticks([])

# plt.show()
plt.savefig('dc_plus_delta_signal.svg')
