# Example incubator using UniFMU with FMI3 and clocks


```
cargo run generate python generated_fmus/supervisor fmi3
cargo run generate python generated_fmus/controller fmi3
cargo run generate python generated_fmus/plant fmi3

./unifmu generate python supervisor fmi3
./unifmu generate python controller fmi3
./unifmu generate python plant fmi3
```