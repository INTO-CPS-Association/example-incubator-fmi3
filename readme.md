# Example incubator using UniFMU with FMI3 and clocks
This demo replicates some of the functionality of [the incubator Digital Twin](https://github.com/INTO-CPS-Association/example_digital-twin_incubator) using FMI3 FMUs created with [UniFMU](https://github.com/INTO-CPS-Association/unifmu). It is also inspired by [this demo of synchronous clocked FMUs](https://github.com/clagms/synchronous-clock-fmus).

In this demo, we use three FMUs featuring the *plant*, the *controller*, and the *supervisor*, for a closed-loop on/off control of the incubator.
Instead of using the original behavior of the incubator example that uses an optimizator to fine-tune the controller parameters, we are just updating some parameters randomly when a given condition (*event*) happens.

## Scenario

The scenario is as follows:

![incubator_scenario](figures/incubator_scenario.svg)

## Clocks
The *supervisor* has associated a `triggered clock`, which is triggered every time the desired temperature has been reached 3 times.
The *controller* receives this `triggered clock` from the supervisor, and additionally has a `periodic clock` that updates the on/off output to the plant.

## Implementation

1. Creation of the FMUs with UniFMU. This creates the Python templates. The existing folders [plant](/plant), [controller](controller/), and [supervisor](supervisor/) already contain the worked-out logic for the example; feel free to update it as needed.
    ```
    ./unifmu generate python supervisor fmi3
    ./unifmu generate python controller fmi3
    ./unifmu generate python plant fmi3
    ```

2. Wrap the models as FMUs using the `wrap_fmus.sh` script:
    ```
    ./wrap_fmus.sh
    ```

3. Create a virtual environment, install the requirements, and update the FMPy library for its `fmi3.py` that we have updated to be able to run the FMI3 co-simulation.

    **Linux:**
    ```
    python3 -m venv venv
    . venv/bin/activate
    cp fmpy/fmi3.py venv/lib/python<version>/site-packages/fmpy/
    ```
    **Windows:**
    ```
    python -m venv venv
    source venv/Scripts/activate
    Copy-Item fmpy\fmi3.py venv\lib\python<version>\site-packages\fmpy
    ```

4. With the virtual environment activated, execute the co-simulation scenario with the `co-simulation_scenario.py` script. Feel free to adapt the co-simulation parameters `end_simulation_time`, `start_simulation_time`, `step_size`, `simulation_program_delay`, and other co-simulation parameters while in initialization mode:
    ```
    python co-simulation_scenario.py
    ```

## Cite this work
TBD