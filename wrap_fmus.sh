#!/bin/bash

# Plant
rm plant.fmu
(cd plant && zip -r plant.fmu .)
cp plant/plant.fmu .
rm plant/plant.fmu

# Controller
rm controller.fmu
(cd controller && zip -r controller.fmu .)
cp controller/controller.fmu .
rm controller/controller.fmu

# Supervisor
rm supervisor.fmu
(cd supervisor && zip -r supervisor.fmu .)
cp supervisor/supervisor.fmu .
rm supervisor/supervisor.fmu
