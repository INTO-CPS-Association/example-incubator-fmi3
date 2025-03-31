# Author: Santiago Gil
from fmpy import read_model_description, extract
from fmpy.fmi3 import FMU3Slave,fmi3OK, fmi3ValueReference, fmi3Binary, fmi3Error
import shutil
import logging
import time
import threading
import pandas as pd


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

# Co-simulation parameters
end_simulation_time = 5000.0
start_simulation_time = 0.0
sim_time = start_simulation_time # Holds the current time of the simulation
step_size = 0.5
simulation_program_delay = True # Set to True for real-time simulation

class ThreadedTimer:
    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run)
        
    def _run(self):
        while not self.stop_event.is_set():
            self.function(*self.args, **self.kwargs)
            if simulation_program_delay:
                time.sleep(self.interval)
        
    def start(self):
        self.thread.start()
        
    def stop(self):
        self.stop_event.set()
        self.thread.join()

columns = [
    "sim_time", 
    "supervisor_event", 
    "Plant.Temperature", 
    "Plant.Temperature_heater", 
    "Controller.heater_ctrl", 
    "Supervisor.temperature_desired", 
    "Supervisor.heating_time"
]

df = pd.DataFrame(columns=columns) # Empty dataframe to store data

plant_fmu_filename = "plant.fmu"
controller_fmu_filename = "controller.fmu"
supervisor_fmu_filename = "supervisor.fmu"
unzipdir_plant = extract(plant_fmu_filename)
unzipdir_controller = extract(controller_fmu_filename)
unzipdir_supervisor = extract(supervisor_fmu_filename)
# read the model description
model_description_plant = read_model_description(unzipdir_plant)
model_description_controller = read_model_description(unzipdir_controller)
model_description_supervisor = read_model_description(unzipdir_supervisor)

# collect the value references
vrs_plant = {}
vrs_controller = {}
vrs_supervisor = {}
for variable in model_description_plant.modelVariables:
    vrs_plant[variable.name] = variable.valueReference
for variable in model_description_controller.modelVariables:
    vrs_controller[variable.name] = variable.valueReference
for variable in model_description_supervisor.modelVariables:
    vrs_supervisor[variable.name] = variable.valueReference



plant_fmu = FMU3Slave(guid=model_description_plant.guid,
                unzipDirectory=unzipdir_plant,
                modelIdentifier=model_description_plant.coSimulation.modelIdentifier,
                instanceName='plant')
controller_fmu = FMU3Slave(guid=model_description_controller.guid,
                unzipDirectory=unzipdir_controller,
                modelIdentifier=model_description_controller.coSimulation.modelIdentifier,
                instanceName='controller')
supervisor_fmu = FMU3Slave(guid=model_description_supervisor.guid,
                unzipDirectory=unzipdir_supervisor,
                modelIdentifier=model_description_supervisor.coSimulation.modelIdentifier,
                instanceName='supervisor')

# Connections for input/output ports
timed_connections = {
		"plant.T": [
			"controller.box_air_temperature",
            "supervisor.T"
		],
		"plant.T_heater": [
			"supervisor.T_heater"
		]
	}

clocked_connections = {
		"controller.heater_ctrl": [
			"plant.in_heater_on"
		],
		"supervisor.heating_time": [
			"controller.heating_time"
		],
		"supervisor.temperature_desired": [
			"controller.temperature_desired"
		],
        "supervisor.supervisor_clock": [
			"controller.supervisor_clock"
		]
	}

all_connections = {**timed_connections,**clocked_connections}

# Outputs for logging
T = 0.0
T_heater = 0.0
heater_ctrl = False
temperature_desired = 0.0
heating_time = 0.0


# Instantiate
plant_fmu.instantiate(visible=False,
                    loggingOn=False,
                    eventModeUsed=False,
                    earlyReturnAllowed=False,
                    logMessage=None,
                    intermediateUpdate=None)
controller_fmu.instantiate(visible=False,
                    loggingOn=False,
                    eventModeUsed=False,
                    earlyReturnAllowed=True,
                    logMessage=None,
                    intermediateUpdate=None)
supervisor_fmu.instantiate(visible=False,
                    loggingOn=False,
                    eventModeUsed=False,
                    earlyReturnAllowed=True,
                    logMessage=None,
                    intermediateUpdate=None)

# Initialization mode
plant_fmu.enterInitializationMode()
controller_fmu.enterInitializationMode()
supervisor_fmu.enterInitializationMode()

# Set parameters if needed
## Standard functionality
supervisor_fmu.setFloat32([vrs_supervisor["desired_temperature_parameter"]],[35.0])
supervisor_fmu.setFloat32([vrs_supervisor["temperature_desired"]],[35.0])
controller_fmu.setFloat32([vrs_controller["temperature_desired"]],[35.0])
supervisor_fmu.setFloat32([vrs_supervisor["heating_time"]],[20.0])
controller_fmu.setFloat32([vrs_controller["heating_time"]],[20.0])
supervisor_fmu.setFloat32([vrs_supervisor["lower_bound"]],[5.0])
controller_fmu.setFloat32([vrs_controller["lower_bound"]],[5.0])
supervisor_fmu.setUInt32([vrs_supervisor["setpoint_achievements_parameter"]],[1])
supervisor_fmu.setUInt32([vrs_supervisor["wait_til_supervising_timer"]],[100])
supervisor_fmu.setFloat32([vrs_supervisor["trigger_optimization_threshold"]],[5.0]) # Standard is 10.0, but we reduce this one to have updates throughtout all the simulation

## For quicker functionality
# supervisor_fmu.setFloat32([vrs_supervisor["desired_temperature_parameter"]],[22.0])
# supervisor_fmu.setFloat32([vrs_supervisor["temperature_desired"]],[22.0])
# controller_fmu.setFloat32([vrs_controller["temperature_desired"]],[22.0])
# supervisor_fmu.setFloat32([vrs_supervisor["heating_time"]],[15.0])
# controller_fmu.setFloat32([vrs_controller["heating_time"]],[15.0])
# supervisor_fmu.setFloat32([vrs_supervisor["lower_bound"]],[1.0])
# controller_fmu.setFloat32([vrs_controller["lower_bound"]],[1.0])
# supervisor_fmu.setUInt32([vrs_supervisor["setpoint_achievements_parameter"]],[1])
# supervisor_fmu.setUInt32([vrs_supervisor["wait_til_supervising_timer"]],[10])
# supervisor_fmu.setFloat32([vrs_supervisor["trigger_optimization_threshold"]],[1.0])

## For different initial conditions (incubator)
# plant_fmu.setFloat32([vrs_plant["initial_box_temperature"]],[21.0])
# plant_fmu.setFloat32([vrs_plant["initial_heat_temperature"]],[21.0])
# plant_fmu.setFloat32([vrs_plant["initial_room_temperature"]],[21.0])

## For controller clock periodicity
controller_fmu.setIntervalDecimal([vrs_controller["controller_clock"]],[1.0])

# Updating outputs to initial values
heater_ctrl = controller_fmu.getBoolean([vrs_controller["heater_ctrl"]])[0]
temperature_desired = supervisor_fmu.getFloat32([vrs_supervisor["temperature_desired"]])[0]
heating_time = supervisor_fmu.getFloat32([vrs_supervisor["heating_time"]])[0]
T = plant_fmu.getFloat32([vrs_plant["T"]])[0]
T_heater = plant_fmu.getFloat32([vrs_plant["T_heater"]])[0]

# Get and set initial values
for connection_src,connection_sink in all_connections.items():
        connection_src_array = connection_src.split(".")
        # Get the current output
        #logger.info(f'connection_src_array: {connection_src_array}')
        if connection_src_array[0] == "plant":
            o = plant_fmu.getFloat32([vrs_plant[connection_src_array[1]]])[0]
        elif connection_src_array[0] == "controller":
            o = controller_fmu.getBoolean([vrs_controller[connection_src_array[1]]])[0]
        elif connection_src_array[0] == "supervisor":
            o = supervisor_fmu.getFloat32([vrs_supervisor[connection_src_array[1]]])[0]
        
        #logger.info(f'output: {o}')
        
        # Set the inputs
        for sink in connection_sink:
            sink_array = sink.split(".")
            #logger.info(f'sink_array: {sink_array}')
            if sink_array[0] == "plant":
                plant_fmu.setBoolean([vrs_plant[sink_array[1]]],[o])
            elif sink_array[0] == "controller":
                controller_fmu.setFloat32([vrs_controller[sink_array[1]]],[o])
            elif sink_array[0] == "supervisor":
                supervisor_fmu.setFloat32([vrs_supervisor[sink_array[1]]],[o])

# Get periodic clock from controller FMU
controller_clock_intervals,controller_clock_qualifiers = controller_fmu.getIntervalDecimal([vrs_controller["controller_clock"]])
controller_clock_interval = controller_clock_intervals[0]
print(f'controller_clock_interval: {controller_clock_interval}')

# Variable to store time event
step_mode = False
controller_time_event = False


# Exit initialization mode
plant_fmu.exitInitializationMode()
controller_fmu.exitInitializationMode()
supervisor_fmu.exitInitializationMode()

# Initialize periodic timer for controller clock
def on_tick():
    global controller_time_event
    controller_time_event = True

controller_clock_timer = ThreadedTimer(controller_clock_interval, on_tick)
controller_clock_timer.start()

# Co-simulation loop (loose coupling)
logger.info(f"Initializing co-simulation for {end_simulation_time} seconds, with step size {step_size}, and real-time {simulation_program_delay}")
while (sim_time < end_simulation_time):
    start_computation_time = time.perf_counter()
    step_mode = True
    for connection_src,connection_sink in timed_connections.items():
        connection_src_array = connection_src.split(".")
        # Get the current output
        #logger.info(f'connection_src_array (timed): {connection_src_array}')
        if connection_src_array[0] == "plant":
            o = plant_fmu.getFloat32([vrs_plant[connection_src_array[1]]])[0]
        elif connection_src_array[0] == "controller":
            o = controller_fmu.getBoolean([vrs_controller[connection_src_array[1]]])[0]
        elif connection_src_array[0] == "supervisor":
            o = supervisor_fmu.getFloat32([vrs_supervisor[connection_src_array[1]]])[0]
        
        # Set the inputs
        for sink in connection_sink:
            sink_array = sink.split(".")
            #logger.info(f'sink_array (timed): {sink_array}')
            if sink_array[0] == "plant":
                plant_fmu.setBoolean([vrs_plant[sink_array[1]]],[o])
            elif sink_array[0] == "controller":
                controller_fmu.setFloat32([vrs_controller[sink_array[1]]],[o])
            elif sink_array[0] == "supervisor":
                supervisor_fmu.setFloat32([vrs_supervisor[sink_array[1]]],[o])

    # Step all FMUs
    logger.info(f"Doing a step of size {step_size} at time {sim_time}")
    plant_event_needed,plant_terminate_sim,plant_early_return,plant_last_successful_time = plant_fmu.doStep(sim_time, step_size)
    controller_event_needed,controller_terminate_sim,controller_early_return,controller_last_successful_time = controller_fmu.doStep(sim_time, step_size)
    supervisor_event_needed,supervisor_terminate_sim,supervisor_early_return,supervisor_last_successful_time = supervisor_fmu.doStep(sim_time, step_size)

    if supervisor_event_needed:
        print("supervisor event needed")

    # Checking if event mode is needed
    if (controller_time_event and not supervisor_event_needed):
        logger.info("Controller time event ONLY")
        # Only controller
        controller_fmu.enterEventMode()
        controller_fmu.setClock([vrs_controller["controller_clock"]],[True])
        controller_time_event = False

        # Get current outputs and set inputs
        o = controller_fmu.getBoolean([vrs_controller["heater_ctrl"]])[0]
        plant_fmu.setBoolean([vrs_plant["in_heater_on"]],[o])

        # Update discrete states
        (controller_discrete_states_need_update,terminate_simulation,
        controller_nominals_of_continuous_states_changed,
        controller_values_of_continuous_states_changed,
        controller_next_event_time_defined,
        controller_next_event_time) = controller_fmu.updateDiscreteStates()

        # Read clocked outputs for logging
        heater_ctrl = controller_fmu.getBoolean([vrs_controller["heater_ctrl"]])[0]
        # Set continuous-time inputs
        # plant_fmu.setBoolean([vrs_plant["in_heater_on"]],[heater_ctrl]) # Double-check if we need to update after stepE
        
        # Get back to step mode
        controller_fmu.enterStepMode()

    elif (plant_event_needed or controller_event_needed or supervisor_event_needed or controller_time_event):
        # If controller and/or supervisor
        logger.info("Controller time event or supervisor event")

        # Set controller and supervisor into event mode (plant doesn't work in event mode)
        controller_fmu.enterEventMode()
        supervisor_fmu.enterEventMode()

        if controller_time_event:
            controller_fmu.setClock([vrs_controller["controller_clock"]],[True])
            controller_time_event = False
            

        supervisor_clock = supervisor_fmu.getClock([vrs_supervisor["supervisor_clock"]])[0]
        controller_clock = controller_fmu.getClock([vrs_controller["controller_clock"]])[0]

        # Get and set clocked variables
        for connection_src,connection_sink in clocked_connections.items():
            connection_src_array = connection_src.split(".")
            # Get the current output
            #logger.info(f'connection_src_array (clocked): {connection_src_array}')
            if connection_src_array[0] == "controller" and controller_clock:
                o = controller_fmu.getBoolean([vrs_controller[connection_src_array[1]]])[0]
            elif connection_src_array[0] == "supervisor" and supervisor_clock:
                o = supervisor_fmu.getFloat32([vrs_supervisor[connection_src_array[1]]])[0]
            
            # Set the inputs
            for sink in connection_sink:
                sink_array = sink.split(".")
                #logger.info(f'sink_array (clocked): {sink_array}')
                if sink_array[0] == "plant" and controller_clock:
                    plant_fmu.setBoolean([vrs_plant[sink_array[1]]],[o])
                elif sink_array[0] == "controller" and supervisor_clock:
                    controller_fmu.setFloat32([vrs_controller[sink_array[1]]],[o])

        # Update discrete states
        (controller_discrete_states_need_update,terminate_simulation,
        controller_nominals_of_continuous_states_changed,
        controller_values_of_continuous_states_changed,
        controller_next_event_time_defined,
        controller_next_event_time) = controller_fmu.updateDiscreteStates()
        
        (supervisor_discrete_states_need_update,terminate_simulation,
        supervisor_nominals_of_continuous_states_changed,
        supervisor_values_of_continuous_states_changed,
        supervisor_next_event_time_defined,
        supervisor_next_event_time) = supervisor_fmu.updateDiscreteStates()

        # Read clocked outputs for logging
        heater_ctrl = controller_fmu.getBoolean([vrs_controller["heater_ctrl"]])[0]
        temperature_desired = supervisor_fmu.getFloat32([vrs_supervisor["temperature_desired"]])[0]
        heating_time = supervisor_fmu.getFloat32([vrs_supervisor["heating_time"]])[0]

        # Get back to step mode
        controller_fmu.enterStepMode()
        supervisor_fmu.enterStepMode()

    # Read timed outputs for logging
    T = plant_fmu.getFloat32([vrs_plant["T"]])[0]
    T_heater = plant_fmu.getFloat32([vrs_plant["T_heater"]])[0]

    logger.info(f"Plant.T :  {T}")
    logger.info(f"Plant.T_heater :  {T_heater}")
    logger.info(f"Controller.heater_ctrl :  {heater_ctrl}")
    logger.info(f"Supervisor.temperature_desired :  {temperature_desired}")
    logger.info(f"Supervisor.heating_time :  {heating_time}")   

    # Store the data in the dataframe
    df.loc[len(df)] = [
        sim_time,
        supervisor_event_needed,
        T,
        T_heater,
        heater_ctrl,
        temperature_desired,
        heating_time
    ]

    sim_time += step_size
    step_mode = False
    end_computation_time = time.perf_counter()
    computation_time = end_computation_time - start_computation_time
    if (simulation_program_delay):
        sleeping_time = step_size-computation_time
        #logger.info(f'Sleeping for {sleeping_time} to follow real time')
        time.sleep(sleeping_time)
    


# Terminate instances
controller_clock_timer.stop()
plant_fmu.terminate()
plant_fmu.freeInstance()
controller_fmu.terminate()
controller_fmu.freeInstance()
supervisor_fmu.terminate()
supervisor_fmu.freeInstance()

# save the data
df.to_csv("data/simulation_data.csv", index=False)

# clean up
shutil.rmtree(unzipdir_plant, ignore_errors=True)
shutil.rmtree(unzipdir_controller, ignore_errors=True)
shutil.rmtree(unzipdir_supervisor, ignore_errors=True)