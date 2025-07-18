import pickle
from fractions import Fraction
from enum import IntFlag
import numpy as np

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
        
        # Replicating the SupervisorThresholdSM behavior of the incubator
        # # Plant --> Supervisor
        # self.supervisor.T = self.plant.out_T
        # self.supervisor.T_heater = self.plant.out_T_heater

        # Parameters
        self.desired_temperature_parameter = 35.0
        self.max_t_heater = 60.0
        self.trigger_optimization_threshold = 10.0
        self.heater_underused_threshold = 10.0
        self.wait_til_supervising_timer = 100
        self.setpoint_achievements_parameter = 1

        # Inputs
        self.T = 0.0 # Temperature in the box
        self.T_heater = 0.0 # Temperature in the heater  

        # Outputs
        self.temperature_desired = 35.0
        self.lower_bound = 5.0
        self.heating_time = 20.0
        self.heating_gap = 20.0

        # State
        self.next_action_timer = self.wait_til_supervising_timer
        self.supervisor_state = SupervisorState.Waiting
        self.setpoint_achievements = 0 # Counter for simple (random) update of the temperature setpoint
        self.previous_T = 0.0
        self.previous_previous_T = 0.0
        self.previous_desired_temperature_parameter = self.desired_temperature_parameter
        self.derivative_positive = False
        self.cooldown_flag = False
        
        self.supervisor_clock = False
        self.clock_reference_to_interval = {
        }


        self.reference_to_attribute = {
            999: "time",
            0: "T",
            1: "T_heater",
            #2: "temperature_desired",
            3: "lower_bound",
            #4: "heating_time",
            5: "heating_gap",  
            
        }

        self.clocked_variables = {
            1001: "supervisor_clock",
            2: "temperature_desired",
            4: "heating_time",
            8: "setpoint_achievements",
        }

        self.parameters = {
            
        }

        self.tunable_parameters = {
            100: "desired_temperature_parameter",
            101: "max_t_heater",
            102: "trigger_optimization_threshold",
            103: "heater_underused_threshold",
            104: "wait_til_supervising_timer",
            105: "setpoint_achievements_parameter",
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

        if self.supervisor_state == SupervisorState.Waiting:
            if self.next_action_timer > 0:
                self.next_action_timer -= 1

            if self.next_action_timer == 0:
                event_handling_needed = True

        if self.supervisor_state == SupervisorState.Listening:
            heater_safe = self.T_heater < self.max_t_heater
            heater_underused = (self.max_t_heater - self.T_heater) > self.heater_underused_threshold
            temperature_residual_above_threshold = np.absolute(self.T - self.desired_temperature_parameter) > self.trigger_optimization_threshold
            if heater_safe and heater_underused and temperature_residual_above_threshold:
                event_handling_needed = True

        if (self.T > self.previous_T > self.previous_previous_T):
            # Derivative is possitive
            self.derivative_positive = True        
        elif (self.T < self.previous_T < self.previous_previous_T):
            # Derivative is negative
            self.derivative_positive = False

        if ((self.T >= self.desired_temperature_parameter) and (self.derivative_positive) and (not self.cooldown_flag)):
            event_handling_needed = True
        elif (self.T < self.desired_temperature_parameter) and (not self.derivative_positive) and (self.cooldown_flag):
            event_handling_needed = True                    

        if (self.setpoint_achievements >= self.setpoint_achievements_parameter):
            event_handling_needed = True

        if(event_handling_needed):
            self.supervisor_clock = True

        # Preserving the two last states of the temperature to identify derivative direction
        self.previous_previous_T = self.previous_T
        self.previous_T = self.T        

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
        next_event_time = 0.0


        if self.supervisor_state == SupervisorState.Waiting:

            if self.next_action_timer == 0:
                self.supervisor_state = SupervisorState.Listening
                self.next_action_timer = -1

        if self.supervisor_state == SupervisorState.Listening:
            heater_safe = self.T_heater < self.max_t_heater
            heater_underused = (self.max_t_heater - self.T_heater) > self.heater_underused_threshold
            temperature_residual_above_threshold = np.absolute(self.T - self.desired_temperature_parameter) > self.trigger_optimization_threshold
            if heater_safe and heater_underused and temperature_residual_above_threshold:
                # Reoptimize controller and then go into waiting
                # self.controller_optimizer.optimize_controller() # -> This is we are to use the actual incubator optimizer
                # For now, we use a simpler approach for the supervisor
            
                rand_number = np.random.rand(1)[0] * 0.1 - 0.05
                self.heating_time += rand_number # Updating heating time around +-0.05 of the current heating time       
                self.supervisor_state = SupervisorState.Waiting
                self.next_action_timer = self.wait_til_supervising_timer # Resetting the cooldown
    
        if ((self.T >= self.desired_temperature_parameter) and (self.derivative_positive) and (not self.cooldown_flag)):
            self.setpoint_achievements +=1
            self.cooldown_flag = True        
        elif (self.T < self.desired_temperature_parameter) and (not self.derivative_positive) and (self.cooldown_flag):
            self.cooldown_flag = False # Resetting the cooldown

        if (self.setpoint_achievements >= self.setpoint_achievements_parameter):
            # Updating the setpoint for a random value within +- 1.0 of the current setpoint
            self.previous_desired_temperature_parameter = self.desired_temperature_parameter
            rand_number = np.random.rand(1)[0] * 2 - 1.0
            self.desired_temperature_parameter += rand_number
            self.temperature_desired += rand_number
            self.setpoint_achievements = 0 # Resetting the counter

        self.supervisor_clock = False



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
        self.desired_temperature_parameter = 35.0
        self.max_t_heater = 60.0
        self.trigger_optimization_threshold = 10.0
        self.heater_underused_threshold = 10.0
        self.wait_til_supervising_timer = 100
        self.setpoint_achievements_parameter = 1
        self.T = 0.0
        self.T_heater = 0.0 
        self.temperature_desired = self.desired_temperature_parameter
        self.lower_bound = 5.0
        self.heating_time = 20.0
        self.heating_gap = 20.0
        self.setpoint_achievements = 0
        self.next_action_timer = self.wait_til_supervising_timer
        self.supervisor_state = SupervisorState.Waiting
        self.supervisor_clock = False
        return Fmi3Status.ok

    # ================= Serialization =================

    def fmi3SerializeFmuState(self):

        bytes = pickle.dumps(
            (
                self.state,
                self.desired_temperature_parameter,
                self.max_t_heater,
                self.trigger_optimization_threshold,
                self.heater_underused_threshold,
                self.wait_til_supervising_timer,
                self.setpoint_achievements_parameter,
                self.T,
                self.T_heater,
                self.temperature_desired,
                self.lower_bound,
                self.heating_time,
                self.heating_gap,
                self.setpoint_achievements,
                self.next_action_timer,
                self.supervisor_state,
                self.supervisor_clock,
            )
        )
        return Fmi3Status.ok, bytes

    def fmi3DeserializeFmuState(self, bytes: bytes):
        (
            state,
            desired_temperature_parameter,
            max_t_heater,
            trigger_optimization_threshold,
            heater_underused_threshold,
            wait_til_supervising_timer,
            setpoint_achievements_parameter,
            T,
            T_heater,
            temperature_desired,
            lower_bound,
            heating_time,
            heating_gap,
            setpoint_achievements,
            next_action_timer,
            supervisor_state,
            supervisor_clock,
        ) = pickle.loads(bytes)
        self.state = state
        self.desired_temperature_parameter = desired_temperature_parameter
        self.max_t_heater = max_t_heater
        self.trigger_optimization_threshold = trigger_optimization_threshold
        self.heater_underused_threshold = heater_underused_threshold
        self.wait_til_supervising_timer = wait_til_supervising_timer
        self.setpoint_achievements_parameter = setpoint_achievements_parameter
        self.T = T
        self.T_heater = T_heater
        self.temperature_desired = temperature_desired
        self.lower_bound = lower_bound
        self.heating_time = heating_time
        self.heating_gap = heating_gap
        self.setpoint_achievements = setpoint_achievements
        self.next_action_timer = next_action_timer
        self.supervisor_state = supervisor_state
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

class SupervisorState():
    Initialized = 0
    Waiting = 1
    Listening = 2

