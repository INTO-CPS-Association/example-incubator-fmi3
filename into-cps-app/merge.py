#time,eventMode,{controllerFmu}.controller.heater_ctrl,{plantFmu}.plant.T,{plantFmu}.plant.T_heater,{supervisorFmu}.supervisor.temperature_desired,{supervisorFmu}.supervisor.heating_time,{supervisorFmu}.supervisor.supervisor_clock,{controllerFmu}.controller.controller_clock

#sim_time,
# supervisor_event,
# controller_event,
# Plant.Temperature,
# Plant.Temperature_heater,
# Controller.heater_ctrl,
# Supervisor.temperature_desired,
# Supervisor.heating_time

import pandas as pd

df_p = pd.read_csv("../data/simulation_data.csv")
df_m=pd.read_csv("simulation/outputs.csv")
df_m.rename(columns={
    "time":"sim_time",
    "{controllerFmu}.controller.heater_ctrl":"Controller.heater_ctrl",
    "{plantFmu}.plant.T":"Plant.Temperature",
    "{plantFmu}.plant.T_heater":"Plant.Temperature_heater",
    "{supervisorFmu}.supervisor.temperature_desired":"Supervisor.temperature_desired",
    "{supervisorFmu}.supervisor.heating_time":"Supervisor.heating_time",
    "{supervisorFmu}.supervisor.supervisor_clock":"supervisor_event",
    "{controllerFmu}.controller.controller_clock":"controller_event",
}, inplace=True)

df = pd.merge(df_p, df_m, on="sim_time", suffixes=('', '_maestro'))

cols = sorted([c for c in df.columns if c != "sim_time" and c!='eventMode'])

# Put sim_time first
df = df[["sim_time",'eventMode'] + cols]

df.to_csv("outputs_merged.csv", index=False)



import pandas as pd
import matplotlib.pyplot as plt



# Convert boolean columns to integers
df = df.map(lambda x: int(x) if isinstance(x, bool) else x)

df = df[df.iloc[:, 0] <= 3000]
# First column as X
x = df.iloc[:, 0]

# All other columns as Ys
ys = df.iloc[:, 1:]

for col in ys.columns:
    plt.plot(x, ys[col],  label=col)

# Add labels and legend
plt.xlabel(df.columns[0])
plt.ylabel("Values")
plt.title("CSV Plot")
plt.legend()
plt.grid(True)
plt.tight_layout()

# Show the plot
plt.show()
