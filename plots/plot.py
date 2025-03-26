# Author: Santiago Gil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path


parser = argparse.ArgumentParser(description="A script that accepts one mandatory and one optional argument.")
    
# Path (mandatory)
parser.add_argument("path", type=str, help="Mandatory path argument")

# Optional flag for saving the plot
parser.add_argument("--save", action="store_true", help="Flag to save resulting plot")

args = parser.parse_args()

filename = args.path

save_file = args.save

script_path = Path(__file__).resolve().parent

font = {'font.family' : 'monospace',
        'font.weight' : 'bold',
        'axes.titlesize'   : 14,
        'axes.labelsize'   : 12,
        'legend.fontsize' : 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
       }

plt.rcParams.update(font)

df_cosim = pd.read_csv(filename)

fig, axes = plt.subplots(3,2, figsize=(20,16))
plt.subplot(3,2,1)

x_axis_values = df_cosim["sim_time"].to_list()
supervisor_event_axis_values = df_cosim["supervisor_event"].to_list()
controller_heater_ctrl_axis_values = df_cosim["Controller.heater_ctrl"].to_list()

plt.step(x_axis_values,supervisor_event_axis_values)
plt.title("(1) Supervisor's triggered clock")
plt.yticks([1.0, 0.0],["True","False"])
plt.legend(['supervisor_event'])
plt.xlabel('simulation time [s]')
plt.ylabel('state')
plt.grid()
plt.tight_layout()

plt.subplot(3,2,2)
df_cosim.plot(x = "sim_time",y = ["Plant.Temperature","Plant.Temperature_heater"],
             figsize=(12,12),
             title = "(2) Plant temperatures",
             ax=axes[0,1],
)
plt.xlabel('simulation time [s]')
plt.ylabel('Temperature (°C)')
plt.legend(['Box temperature','Heater temperature'])
plt.grid()
plt.tight_layout()

plt.subplot(3,2,3)

plt.step(x_axis_values,controller_heater_ctrl_axis_values)
plt.title("(3) Heater control")
plt.yticks([1.0, 0.0],["True","False"])
plt.legend(['heater_ctrl'])
plt.xlabel('simulation time [s]')
plt.ylabel('state')
plt.grid()
plt.tight_layout()

plt.subplot(3,2,4)
df_cosim.plot(x = "sim_time",y = ["Supervisor.temperature_desired"],
             figsize=(12,12),
             title = "(4) Supervisor's desired temperature",
             ax=axes[1,1],
)
plt.xlabel('simulation time [s]')
plt.ylabel('Temperature (°C)')
plt.legend(['desired temperature'])
plt.grid()
plt.tight_layout()

plt.subplot(3,2,5)
df_cosim.plot(x = "sim_time",y = ["Supervisor.heating_time"],
             figsize=(12,12),
             title = "(4) Supervisor's heating time",
             ax=axes[2,0],
)
plt.xlabel('simulation time [s]')
plt.ylabel('time [s]')
plt.legend(['heating time'])
plt.grid()
plt.tight_layout()

plt.show()
if save_file:
    fig.savefig(script_path / 'plot.pdf', dpi=300)
    fig.savefig(script_path / 'plot.png', dpi=300)
    print("Plot saved in " + str(script_path))