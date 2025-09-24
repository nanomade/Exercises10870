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
    for x_pertub in np.arange(0, 8 * np.pi, 0.05):
        y_pertub = np.sin(x_pertub) * 0.1
        y = x + y_pertub
        y_values.append(y)
x_values = range(0, len(y_values))
ax.plot(x_values, y_values)
ax.set_xlabel('Tid', fontsize=11)
ax.set_ylabel('Eksitation', fontsize=11)
# Remove axis ticks, this is conceptual drawing
plt.xticks([]) 
plt.yticks([])



ax_insert = zoomed_inset_axes(ax, 5, loc=2) # zoom = 6
ax_insert.plot(x_values, y_values)
ax_insert.set_xlim(0,1500)
ax_insert.set_ylim(-0.15,3.05)
# Remove axis ticks, this is conceptual drawing
plt.xticks([]) 
plt.yticks([])
# plt.show()
plt.savefig('dc_plus_ac_signal.svg')
