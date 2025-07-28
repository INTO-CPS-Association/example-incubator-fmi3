@echo off

REM Plant
if exist plant.fmu del plant.fmu
pushd plant
powershell -Command "Compress-Archive -Path * -DestinationPath plant.zip"
popd
move /Y plant\plant.zip plant.fmu

REM Controller
if exist controller.fmu del controller.fmu
pushd controller
powershell -Command "Compress-Archive -Path * -DestinationPath controller.zip"
popd
move /Y controller\controller.zip controller.fmu

REM Supervisor
if exist supervisor.fmu del supervisor.fmu
pushd supervisor
powershell -Command "Compress-Archive -Path * -DestinationPath supervisor.zip"
popd
move /Y supervisor\supervisor.zip supervisor.fmu
