# FMI Tutorial - Example incubator using UniFMU with FMI3 and clocks

![FMI-tutorial-logo](figures/FMI-tutorial-logo.png)

This repository contains the agenda and materials for the Tutorial on FMI3 co-simulation with UniFMU presented at the [16th International Modelica & FMI Conference](https://modelica.org/events/modelica2025/).

## Table of Contents
- [Agenda](#agenda).
- [Introduction to FMI 3 and Clocks, and UniFMU](#introduction-to-fmi-3-and-clocks-and-unifmu).
  - [Schedule](#schedule).
  - [Q&A](#qa).
  - [Break](#break).
- [Demo and Recreation of the Running Example](#demo-and-recreation-of-the-running-example).
  - [Prerequisites](#prerequisites).
  - [Schedule](#schedule-1).
  - [Co-simulation Scenario](#co-simulation-scenario).
  - [Clocks](#clocks).
  - [Step-by-Step Implementation (Locally)](#step-by-step-implementation-locally).
    - [Plot the results](#plot-the-results).
  - [Q&A](#qa-1).
- [Acknowledgments](#acknowledgments).

## Agenda

| Time  | Topic                                        |
| ----- | -------------------------------------------- |
| 13:30 | Introduction to FMI 3 and Clocks, and UniFMU |
| 14:45 | Q&A                                          |
| 15:00 | Break                                        |
| 15:30 | Demo and Recreation of the Running Example   |
| 16:30 | Q&A                                          |
| 16:40 | End Tutorial                                 |

## Introduction to FMI 3 and Clocks, and UniFMU

### Schedule
- Brief introduction to FMI3 and clocks.
- Introduction to UniFMU.
- Introduction to creating FMI3 FMUs with UniFMU.

### Q&A

### Break

## Demo and Recreation of the Running Example

This demo replicates some of the functionality of [the incubator Digital Twin](https://github.com/INTO-CPS-Association/example_digital-twin_incubator) using FMI3 FMUs created with [UniFMU](https://github.com/INTO-CPS-Association/unifmu). It is also inspired by [this demo of synchronous clocked FMUs](https://github.com/clagms/synchronous-clock-fmus).

In this demo, we use three FMUs featuring the *plant*, the *controller*, and the *supervisor*, for a closed-loop on/off control of the incubator.
Instead of using the original behavior of the incubator example that uses an optimizator to fine-tune the controller parameters, we are just updating some parameters randomly when a given condition (*event*) happens.

### Prerequisites
Attendees are required to:
**If running the example locally:**
- Be able to execute commands from the command line.
- Have `Python` and `pip` installed on their machines with the corresponding `path` settings to run these from the terminal.
- Be able to create `Python` virtual environments and install new `Python` packages.

**If using Jupyter Notebook (on Google Colab):**
- Have a Google account.

### Schedule
- Demonstration with the running example (Incubator).
    - Explanation of the co-simulation scenario.
    - Dealing with initial parameters.
    - Plots.
- Recreating the example from the initial templates.
- Updating the logic inside the Supervisor FMU.

### Co-simulation Scenario

The scenario is as follows:

![incubator_scenario](figures/incubator_scenario.svg)

### Clocks
The *supervisor* has associated a `triggered clock`, which is triggered every time the desired temperature has been reached 3 times.
The *controller* receives this `triggered clock` from the supervisor, and additionally has a `periodic clock` that updates the on/off output to the plant.

### Step-by-Step Implementation (Locally)

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
    pip install -r requirements.txt
    cp fmpy/fmi3.py venv/lib/python<version>/site-packages/fmpy/
    ```
    **Windows:**
    ```
    python -m venv venv
    source venv/Scripts/activate
    pip install -r requirements.txt
    Copy-Item fmpy\fmi3.py venv\lib\python<version>\site-packages\fmpy
    ```

4. With the virtual environment activated, execute the co-simulation scenario with the `co-simulation_scenario.py` script. Feel free to adapt the co-simulation parameters `end_simulation_time`, `start_simulation_time`, `step_size`, `simulation_program_delay`, and other co-simulation parameters while in initialization mode:
    ```
    python co-simulation_scenario.py
    ```

#### Plot the results
Once you have executed the co-simulation scenario with your updates, you can plot the obtained results with the following command (within the virtual environment):
```
python plots/plot.py data/simulation_data.csv --save
```
Use the `--save` flag to store the resulting plot in `plots/plot.pdf` and `plots/plot.png`. You can also change the input csv file as needed.

### Q&A


## Acknowledgments

We are thankful to [Aleksander Ross Møller](https://github.com/DisasterlyDisco) for his contributions to this tutorial.

In addition, part of this work has been supported by the DIGIT-Bench project (case no. 640222-497272), funded by the Energy Technology Development and Demonstration Programme (EUDP).
