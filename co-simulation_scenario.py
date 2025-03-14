# Author: Santiago Gil
from fmpy import read_model_description, extract
from fmpy.fmi3 import FMU3Slave,fmi3OK, fmi3ValueReference, fmi3Binary, fmi3Error
import shutil
import sys
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

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

# Exit initialization mode
plant_fmu.exitInitializationMode()
controller_fmu.exitInitializationMode()
supervisor_fmu.exitInitializationMode()


# Co-simulation parameters
end_simulation_time = 10000.0
start_simulation_time = 0.0
sim_time = start_simulation_time # Holds the current time of the simulation
step_size = 0.5
simulation_program_delay = False # Set to True for real-time simulation

# Connections for input/output ports
connections = {
		"plant.T": [
			"controller.box_air_temperature",
            "supervisor.T"
		],
		"plant.T_heater": [
			"supervisor.T_heater"
		],
		"controller.heater_ctrl": [
			"plant.in_heater_on"
		],
		"supervisor.heating_time": [
			"controller.heating_time"
		],
		"supervisor.temperature_desired": [
			"controller.temperature_desired"
		]
	}

# Co-simulation loop (loose coupling)
logger.info(f"Initializing co-simulation for {end_simulation_time} seconds, with step size {step_size}, and real-time {simulation_program_delay}")
while (sim_time < end_simulation_time):
    for connection_src,connection_sink in connections.items():
        connection_src_array = connection_src.split(".")
        # No need to check datatype because it's uniform for this example (only 1 known boolean)
        # Get the current output
        logger.info(f'connection_src_array: {connection_src_array}')
        if connection_src_array[0] == "plant":
            o = plant_fmu.getFloat32([vrs_plant[connection_src_array[1]]])[0]
        elif connection_src_array[0] == "controller":
            o = controller_fmu.getBoolean([vrs_controller[connection_src_array[1]]])[0]
        elif connection_src_array[0] == "supervisor":
            o = supervisor_fmu.getFloat32([vrs_supervisor[connection_src_array[1]]])[0]
        
        # Set the inputs
        for sink in connection_sink:
            sink_array = sink.split(".")
            logger.info(f'sink_array: {sink_array}')
            if sink_array[0] == "plant":
                plant_fmu.setBoolean([vrs_plant[sink_array[1]]],[o])
            elif sink_array[0] == "controller":
                controller_fmu.setFloat32([vrs_controller[sink_array[1]]],[o])
            elif sink_array[0] == "supervisor":
                supervisor_fmu.setFloat32([vrs_supervisor[sink_array[1]]],[o])

    # Step all FMUs
    logger.info(f"Doing a step of size {step_size} at time {sim_time}")
    plant_fmu.doStep(sim_time, step_size)
    controller_fmu.doStep(sim_time, step_size)
    supervisor_fmu.doStep(sim_time, step_size)


    # Read outputs for logging
    T = plant_fmu.getFloat32([vrs_plant["T"]])[0]
    T_heater = plant_fmu.getFloat32([vrs_plant["T_heater"]])[0]
    heater_ctrl = controller_fmu.getBoolean([vrs_controller["heater_ctrl"]])[0]
    temperature_desired = supervisor_fmu.getFloat32([vrs_supervisor["temperature_desired"]])[0]
    heating_time = supervisor_fmu.getFloat32([vrs_supervisor["heating_time"]])[0]

    logger.info(f"Plant.T :  {T}")
    logger.info(f"Plant.T_heater :  {T_heater}")
    logger.info(f"Controller.heater_ctrl :  {heater_ctrl}")
    logger.info(f"Supervisor.temperature_desired :  {temperature_desired}")
    logger.info(f"Supervisor.heating_time :  {heating_time}")        


    if (simulation_program_delay):
        time.sleep(step_size)
    sim_time += step_size

# Terminate instances
plant_fmu.terminate()
plant_fmu.freeInstance()
controller_fmu.terminate()
controller_fmu.freeInstance()
supervisor_fmu.terminate()
supervisor_fmu.freeInstance()

# clean up
shutil.rmtree(unzipdir_plant, ignore_errors=True)
shutil.rmtree(unzipdir_controller, ignore_errors=True)
shutil.rmtree(unzipdir_supervisor, ignore_errors=True)