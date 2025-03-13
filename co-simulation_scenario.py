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