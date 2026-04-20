# Execution with maestro

To execcute the model with maestro a config file must be created describing all the connections, parameters etc.
This can be done using the INTO-CPS-Application https://github.com/INTO-CPS-Association/into-cps-application/releases however as this is only for FMI2 a small projection is needed to make FMI3 look like FMI2.

The current a projection can be made by running:

```bash
python3 convert.py
```

This will create FMUs which is the projected FMUs. The INTO-CPS-Application can now be opened in this folder and configured. A mm-new config is already present.


## Simulation

Note that 'unifmu' requires python and python dependencies

```bash
python3 -m venv .venv
source .ven/bin/activate
pip install -f ../requirements.txt
```

Maestro can be used to run a FMI3 simulation with clocks as this model. To do so we need to run import the config produced above but using the real FMI3 models (`../` is what points to the folder where the real FMUs exist. In this case a folders and not `.fmu` files which also could be the case).

```bash
wget https://github.com/INTO-CPS-Association/maestro/releases/download/Release%2F4.1.0/maestro-4.1.0-jar-with-dependencies.jar
```


```bash
java -jar maestro-4.1.0-jar-with-dependencies.jar import sg1 Multi-models/mm-new/mm.json Multi-models/mm-new/co-sim/coe.json --fmu-search-path ../  -output simulation --interpret -di -udsp
```

After this the results of the simulation is in `simulation` and in this case also the generated mabl spec used. The `outputs.csv` is the recorded output values.