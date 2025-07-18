import pickle
from fractions import Fraction
from enum import IntFlag

class Model:
    def __init__(
            self,
            instance_name,
            instantiation_token,
            resource_path,
            visible,
            logging_on,
            event_mode_used,
            early_return_allowed,
            required_intermediate_variables,
    ) -> None:
        self.instance_name = instance_name
        self.instantiation_token = instantiation_token
        self.resource_path = resource_path
        self.visible = visible
        self.logging_on = logging_on
        self.event_mode_used = event_mode_used
        self.early_return_allowed = early_return_allowed
        self.required_intermediate_variables = required_intermediate_variables
        self.state = FMIState.FMIInstantiatedState

        # Replicating ControllerPhysical of the incubator without using the fan
        # Controller tunable parameters
        self.lower_bound = 5.0
        # self.heating_time = 20.0
        self.heating_gap = 20.0

        # Inputs
        self.box_air_temperature = 0.0
        self.temperature_desired = 35.0
        self.heating_time = 20.0
        # self.room_temperature = 0.0

        # Outputs
        self.heater_ctrl = False

        # State
        self.controller_state = ControllerState.Cooling
        self.next_action_timer = -1.0
        self.cached_heater_on = False
        self.condition = 0.0 # For passing condition from step mode to event mode

        self.clock_reference_to_interval = {
            1001: 1.0,
        }

        self.reference_to_attribute = {
            999: "time",
            0: "box_air_temperature",
            # 1: "heater_ctrl",
            # 2: "temperature_desired",
            # 3: "heating_time",
        }

        self.clocked_variables = {
            1001: "controller_clock",
            1002: "supervisor_clock",
            1: "heater_ctrl",
            2: "temperature_desired",
            3: "heating_time",
        }

        self.parameters = {
            
        }

        self.tunable_parameters = {
            # 100: "temperature_desired",
            101: "lower_bound",
            # 102: "heating_time",
            103: "heating_gap",
        }

        self.tunable_structural_parameters = {
        }

        self.all_references = {**self.tunable_structural_parameters,
                               **self.parameters,
                               **self.tunable_parameters,
                               **self.clocked_variables,
                               **self.reference_to_attribute}
        
        self.all_parameters = {**self.tunable_structural_parameters,
                               **self.parameters,
                               **self.tunable_parameters}

    # ================= FMI3 =================

    # ================= doStep and updateDiscreteStates =================
    def fmi3DoStep(
            self,
            current_communication_point: float,
            communication_step_size: float,
            no_set_fmu_state_prior_to_current_point: bool,
    ):

        event_handling_needed = False
        terminate_simulation = False
        early_return = False
        last_successful_time = current_communication_point + communication_step_size

        self.condition = current_communication_point + communication_step_size

        if self.controller_state == ControllerState.Cooling:
            assert self.cached_heater_on is False
            if self.box_air_temperature <= self.temperature_desired - self.lower_bound:
                self.next_action_timer = self.condition + self.heating_time
            
        if self.controller_state == ControllerState.Heating:
            assert self.cached_heater_on is True
            if 0 < self.next_action_timer <= self.condition:
                self.next_action_timer = self.condition + self.heating_gap
            elif self.box_air_temperature > self.temperature_desired:
                self.next_action_timer = -1.0
            
        if self.controller_state == ControllerState.Waiting:
            assert self.cached_heater_on is False
            if 0 < self.next_action_timer <= self.condition:
                if self.box_air_temperature <= self.temperature_desired:
                    self.next_action_timer = self.condition + self.heating_time
                else:
                    self.next_action_timer = -1.0
     
        return (
            Fmi3Status.ok,
            event_handling_needed,
            terminate_simulation,
            early_return,
            last_successful_time,
        )
    
    def fmi3UpdateDiscreteStates(self):
        status = Fmi3Status.ok
        discrete_states_need_update = False
        terminate_simulation = False
        nominals_continuous_states_changed = False
        values_continuous_states_changed = False
        next_event_time_defined = True
        next_event_time = 1.0


        if self.controller_state == ControllerState.Cooling:
            assert self.cached_heater_on is False
            if self.box_air_temperature <= self.temperature_desired - self.lower_bound:
                self.controller_state = ControllerState.Heating
                self.cached_heater_on = True
                #self.next_action_timer = current_communication_point + communication_step_size + self.heating_time
            
        if self.controller_state == ControllerState.Heating:
            assert self.cached_heater_on is True
            if 0 < self.next_action_timer <= self.condition:
                self.controller_state = ControllerState.Waiting
                self.cached_heater_on = False
                #self.next_action_timer = current_communication_point + communication_step_size + self.heating_gap
            elif self.box_air_temperature > self.temperature_desired:
                self.controller_state = ControllerState.Cooling
                self.cached_heater_on = False
                #self.next_action_timer = -1.0
            
        if self.controller_state == ControllerState.Waiting:
            assert self.cached_heater_on is False
            if 0 < self.next_action_timer <= self.condition:
                if self.box_air_temperature <= self.temperature_desired:
                    self.controller_state = ControllerState.Heating
                    self.cached_heater_on = True
                    #self.next_action_timer = current_communication_point + communication_step_size + self.heating_time
                else:
                    self.controller_state = ControllerState.Cooling
                    self.cached_heater_on = False
                    #self.next_action_timer = -1.0

        # Resetting the clock
        if (self.controller_clock):
            self.controller_clock = False

        # Setting outputs
        self.heater_ctrl = self.cached_heater_on

        return (status, discrete_states_need_update, terminate_simulation, nominals_continuous_states_changed,
                values_continuous_states_changed, next_event_time_defined, next_event_time)

    # ================= Initialization, Enter, Termination, and Reset =================

    def fmi3EnterInitializationMode(
            self,
            tolerance_defined: bool,
            tolerance: float,
            start_time: float,
            stop_time_defined: bool,
            stop_time: float
    ):
        self.state = FMIState.FMIInitializationModeState
        return Fmi3Status.ok

    def fmi3ExitInitializationMode(self):
        self.state = FMIState.FMIEventModeState if self.event_mode_used else FMIState.FMIStepModeState
        return Fmi3Status.ok

    def fmi3EnterEventMode(self):
        self.state = FMIState.FMIEventModeState
        return Fmi3Status.ok

    def fmi3EnterStepMode(self):
        self.state = FMIState.FMIStepModeState
        return Fmi3Status.ok
    
    def fmi3EnterConfigurationMode(self):
        if len(self.tunable_structural_parameters)>0:
            self.state = FMIState.FMIConfigurationModeState if self.state == FMIState.FMIInstantiatedState else FMIState.FMIReconfigurationModeState
        else:
            return Fmi3Status.error
        return Fmi3Status.ok

    def fmi3ExitConfigurationMode(self):
        if self.state == FMIState.FMIConfigurationModeState:
            self.state = FMIState.FMIInstantiatedState
        elif self.state == FMIState.FMIReconfigurationModeState:
            self.state = FMIState.FMIStepModeState
        else:
            return Fmi3Status.error
        return Fmi3Status.ok

    def fmi3Terminate(self):
        self.state = FMIState.FMITerminatedState
        return Fmi3Status.ok

    def fmi3Reset(self):
        self.state = FMIState.FMIInstantiatedState
        self.temperature_desired = 35.0
        self.lower_bound = 5.0
        self.heating_time = 20.0
        self.heating_gap = 20.0
        self.box_air_temperature = 0.0
        self.heater_ctrl = False
        self.controller_state = ControllerState.Cooling
        self.next_action_timer = -1.0
        self.cached_heater_on = False
        self.controller_clock = False
        self.supervisor_clock = False
        
        self.clock_reference_to_interval = {
            1001: 1.0,
        }
        return Fmi3Status.ok

    # ================= Serialization =================

    def fmi3SerializeFmuState(self):

        bytes = pickle.dumps(
            (
                self.temperature_desired,
                self.lower_bound,
                self.heating_time,
                self.heating_gap,
                self.box_air_temperature,
                self.heater_ctrl,
                self.controller_state,
                self.next_action_timer,
                self.cached_heater_on,
                self.clock_reference_to_interval,
                self.controller_clock,
                self.supervisor_clock,
            )
        )
        return Fmi3Status.ok, bytes

    def fmi3DeserializeFmuState(self, bytes: bytes):
        (
            temperature_desired,
            lower_bound,
            heating_time,
            heating_gap,
            box_air_temperature,
            heater_ctrl,
            controller_state,
            next_action_timer,
            cached_heater_on,
            clock_reference_to_interval,
            controller_clock,
            supervisor_clock,
        ) = pickle.loads(bytes)
        self.temperature_desired = temperature_desired
        self.lower_bound = lower_bound
        self.heating_time = heating_time
        self.heating_gap = heating_gap
        self.box_air_temperature = box_air_temperature
        self.heater_ctrl = heater_ctrl
        self.controller_state = controller_state
        self.next_action_timer = next_action_timer
        self.cached_heater_on = cached_heater_on
        self.clock_reference_to_interval = clock_reference_to_interval
        self.controller_clock = controller_clock
        self.supervisor_clock = supervisor_clock
        return Fmi3Status.ok
    
    # ================= Getters =================

    def fmi3GetFloat32(self, value_references):
        return self._get_value(value_references)

    def fmi3GetFloat64(self, value_references):
        return self._get_value(value_references)

    def fmi3GetInt8(self, value_references):
        return self._get_value(value_references)

    def fmi3GetUInt8(self, value_references):
        return self._get_value(value_references)

    def fmi3GetInt16(self, value_references):
        return self._get_value(value_references)

    def fmi3GetUInt16(self, value_references):
        return self._get_value(value_references)

    def fmi3GetInt32(self, value_references):
        return self._get_value(value_references)

    def fmi3GetUInt32(self, value_references):
        return self._get_value(value_references)

    def fmi3GetInt64(self, value_references):
        return self._get_value(value_references)

    def fmi3GetUInt64(self, value_references):
        return self._get_value(value_references)

    def fmi3GetBoolean(self, value_references):
        return self._get_value(value_references)

    def fmi3GetString(self, value_references):
        return self._get_value(value_references)

    def fmi3GetBinary(self, value_references):
        return self._get_value(value_references)

    def fmi3GetClock(self, value_references):
        return self._get_value(value_references)

    def fmi3GetIntervalDecimal(self, value_references):
        intervals = []
        qualifiers = []

        for r in value_references:
            intervals.append(self.clock_reference_to_interval[r])
            qualifiers.append(2)

        return Fmi3Status.ok, intervals, qualifiers
    
    def fmi3GetIntervalFraction(self, value_references):
        counters = []
        resolutions = []
        qualifiers = []

        for r in value_references:
            fraction = Fraction(str(self.clock_reference_to_interval[r]))
            numerator = fraction.numerator
            denominator = fraction.denominator
            counters.append(numerator)
            resolutions.append(denominator)
            qualifiers.append(2)

        return Fmi3Status.ok, counters, resolutions, qualifiers
    
    def fmi3GetShiftDecimal(self, value_references):
        shifts = []

        for r in value_references:
            shifts.append(self.clock_reference_to_shift[r])

        return Fmi3Status.ok, shifts
    
    def fmi3GetShiftFraction(self, value_references):
        counters = []
        resolutions = []

        for r in value_references:
            fraction = Fraction(str(self.clock_reference_to_shift[r]))
            numerator = fraction.numerator
            denominator = fraction.denominator
            counters.append(numerator)
            resolutions.append(denominator)

        return Fmi3Status.ok, counters, resolutions
    
    # ================= Setters =================

    def fmi3SetFloat32(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetFloat64(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetInt8(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetUInt8(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetInt16(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetUInt16(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetInt32(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetUInt32(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetInt64(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetUInt64(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetBoolean(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetString(self, value_references, values):
        return self._set_value(value_references, values)

    def fmi3SetBinary(self, value_references, value_sizes, values):
        # Store 'value_sizes' somewhere if needed
        return self._set_value(value_references, values)

    def fmi3SetClock(self, value_references, values):
        status = self._set_value(value_references, values)
        return status
    
    def fmi3SetIntervalDecimal(self, value_references, intervals):
        for idx,r in enumerate(value_references):
            self.clock_reference_to_interval[r] = intervals[idx]
        return Fmi3Status.ok
    
    def fmi3SetIntervalFraction(self, value_references, counters, resolutions):
        for idx,r in enumerate(value_references):
            self.clock_reference_to_interval[r] = float(counters[idx])/float(resolutions[idx])
        return Fmi3Status.ok
    
    def fmi3SetShiftDecimal(self, value_references, shifts):
        for idx,r in enumerate(value_references):
            self.clock_reference_to_shift[r] = shifts[idx]
        return Fmi3Status.ok
    
    def fmi3SetShiftFraction(self, value_references, counters, resolutions):
        for idx,r in enumerate(value_references):
            self.clock_reference_to_shift[r] = float(counters[idx])/float(resolutions[idx])
        return Fmi3Status.ok

    

    # ================= Helpers =================

    def _set_value(self, references, values):
        for r, v in zip(references, values):
            if (r in self.clocked_variables or r in self.tunable_parameters):
                if (self.state == FMIState.FMIEventModeState or self.state == FMIState.FMIInitializationModeState):
                    pass
                else:
                    return Fmi3Status.error
            elif (r in self.tunable_structural_parameters):
                if (self.state == FMIState.FMIConfigurationModeState or self.state == FMIState.FMIReconfigurationModeState or self.state == FMIState.FMIInitializationModeState):
                    pass
                else:
                    return Fmi3Status.error
            elif (r in self.parameters):
                if (self.state == FMIState.FMIInitializationModeState):
                    pass
                else:
                    return Fmi3Status.error
            setattr(self, self.all_references[r], v)
        return Fmi3Status.ok

    def _get_value(self, references):

        values = []
        for r in references:
            if r in self.clocked_variables:
                if not ((self.state == FMIState.FMIEventModeState) or (self.state == FMIState.FMIInitializationModeState)):
                    return Fmi3Status.error
            values.append(getattr(self, self.all_references[r]))

        return Fmi3Status.ok, values


class Fmi3Status():
    """
    Represents the status of an FMI3 FMU or the results of function calls.

    Values:
        * ok: all well
        * warning: an issue has arisen, but the computation can continue.
        * discard: an operation has resulted in invalid output, which must be discarded
        * error: an error has ocurred for this specific FMU instance.
        * fatal: an fatal error has ocurred which has corrupted ALL FMU instances.
    """

    ok = 0
    warning = 1
    discard = 2
    error = 3
    fatal = 4

class FMIState(IntFlag):
    FMIStartAndEndState         = 1 << 0,
    FMIInstantiatedState        = 1 << 1,
    FMIInitializationModeState  = 1 << 2,
    FMITerminatedState          = 1 << 3,
    FMIConfigurationModeState   = 1 << 4,
    FMIReconfigurationModeState = 1 << 5,
    FMIEventModeState           = 1 << 6,
    FMIContinuousTimeModeState  = 1 << 7,
    FMIStepModeState            = 1 << 8,
    FMIClockActivationMode      = 1 << 9

class ControllerState():
    Initialized = 0
    Cooling = 1
    Heating = 2
    Waiting = 3

