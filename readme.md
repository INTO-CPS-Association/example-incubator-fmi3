# Example incubator using UniFMU with FMI3 and clocks

Creation of the FMUs with UniFMU:
```
cargo run generate python generated_fmus/supervisor fmi3
cargo run generate python generated_fmus/controller fmi3
cargo run generate python generated_fmus/plant fmi3

./unifmu generate python supervisor fmi3
./unifmu generate python controller fmi3
./unifmu generate python plant fmi3
```

Wrap the models as FMUs:
```
./wrap_fmus.sh
```

Execution of the co-simulation scenario:
```
python3 co-simulation_scenario.py
```