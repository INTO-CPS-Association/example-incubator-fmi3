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

        # Replicates the FourParameterIncubatorPlant model

        # Parameters
        self.C_air = 267.55929458
        self.G_box = 0.5763498
        self.C_heater = 329.25376821
        self.G_heater = 1.67053237
        self.V_heater = 12.15579391 # == in_heater_voltage
        self.I_heater = 1.53551347 # == initial_heat_current
        self.initial_box_temperature = 21.0
        self.initial_heat_temperature = 21.0
        self.initial_room_temperature = 21.0
        

        # Inputs
        self.in_heater_on = False

        # Outputs
        self.T = self.initial_box_temperature # Temperature in the box
        self.T_heater = self.initial_heat_temperature # Temperature in the heater        

    
        self.reference_to_attribute = {
            999: "time",
            0: "in_heater_on",
            1: "T",
            2: "T_heater",         
        }

        self.clocked_variables = {
        }

        self.parameters = {
            10: "initial_box_temperature",
            11: "initial_heat_temperature",
            12: "initial_room_temperature",
        }

        self.tunable_parameters = {
            100: "C_air",
            101: "G_box",
            102: "C_heater",
            103: "G_heater",
            104: "V_heater",
            105: "I_heater",
        }

        self.tunable_structural_parameters = {
        }

        self.all_references = {**self.tunable_structural_parameters,
                               **self.tunable_parameters,
                               **self.clocked_variables,
                               **self.reference_to_attribute}
        
        self.all_parameters = {**self.tunable_structural_parameters,
                               **self.parameters,
                               **self.tunable_parameters}



    # ================= FMI3 =================

    def fmi3DoStep(
            self,
            current_communication_point: float,
            communication_step_size: float,
            no_set_fmu_state_prior_to_current_point: bool,
    ):
        power_in = self.V_heater * self.I_heater if self.in_heater_on else 0.0
        power_out_box = self.G_box * (self.T - self.initial_room_temperature)
        power_transfer_heat = self.G_heater * (self.T_heater - self.T)
        total_power_box = power_transfer_heat - power_out_box
        total_power_heater = power_in - power_transfer_heat
        

        #der_T = lambda : (1.0 / self.C_air) * total_power_box # Derivative of T
        der_T = lambda t,y: (1.0 / self.C_air) * y # Derivative of T
        #der_T_heater = lambda: (1.0 / self.C_heater) * total_power_heater # Derivative of T_heater
        der_T_heater = lambda t,y: (1.0 / self.C_heater) * y # Derivative of T_heater

        # Runge-Kutta 45
        k1_T = der_T(current_communication_point, total_power_box)
        k2_T = der_T(current_communication_point+(communication_step_size/2), total_power_box+communication_step_size*(k1_T/2))
        k3_T = der_T(current_communication_point+(communication_step_size/2), total_power_box+communication_step_size*(k2_T/2))
        k4_T = der_T(current_communication_point+communication_step_size, total_power_box+communication_step_size*k3_T)
        self.T += communication_step_size*(k1_T + 2*k2_T + 2*k3_T + k4_T)/6
        #print(self.T)

        k1_T_heater = der_T_heater(current_communication_point, total_power_heater)
        k2_T_heater = der_T_heater(current_communication_point+(communication_step_size/2), total_power_heater+communication_step_size*(k1_T_heater/2))
        k3_T_heater = der_T_heater(current_communication_point+(communication_step_size/2), total_power_heater+communication_step_size*(k2_T_heater/2))
        k4_T_heater = der_T_heater(current_communication_point+communication_step_size, total_power_heater+communication_step_size*k3_T_heater)
        self.T_heater += communication_step_size*(k1_T_heater + 2*k2_T_heater + 2*k3_T_heater + k4_T_heater)/6
        #print(self.T_heater)

        event_handling_needed = False
        terminate_simulation = False
        early_return = False
        last_successful_time = current_communication_point + communication_step_size

        return (
            Fmi3Status.ok,
            event_handling_needed,
            terminate_simulation,
            early_return,
            last_successful_time,
        )

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
        self.state = FMIState.FMIConfigurationModeState if self.state == FMIState.FMIInstantiatedState else FMIState.FMIReconfigurationModeState
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
        self.C_air = 267.55929458
        self.G_box = 0.5763498
        self.C_heater = 329.25376821
        self.G_heater = 1.67053237
        self.V_heater = 12.15579391
        self.I_heater = 1.53551347
        self.initial_box_temperature = 21.0
        self.initial_heat_temperature = 21.0
        self.initial_room_temperature = 21.0
        self.in_heater_on = False
        self.T = self.initial_box_temperature
        self.T_heater = self.initial_heat_temperature      

        return Fmi3Status.ok

    def fmi3SerializeFmuState(self):

        bytes = pickle.dumps(
            (
                self.C_air,
                self.G_box,
                self.C_heater,
                self.G_heater,
                self.V_heater,
                self.I_heater,
                self.initial_box_temperature,
                self.initial_heat_temperature,
                self.initial_room_temperature,
                self.in_heater_on,
                self.T,
                self.T_heater,
            )
        )
        return Fmi3Status.ok, bytes

    def fmi3DeserializeFmuState(self, bytes: bytes):
        (
            C_air,
            G_box,
            C_heater,
            G_heater,
            V_heater,
            I_heater,
            initial_box_temperature,
            initial_heat_temperature,
            initial_room_temperature,
            in_heater_on,
            T,
            T_heater,
        ) = pickle.loads(bytes)
        self.C_air = C_air
        self.G_box = G_box
        self.C_heater = C_heater
        self.G_heater = G_heater
        self.V_heater = V_heater
        self.I_heater = I_heater
        self.initial_box_temperature = initial_box_temperature
        self.initial_heat_temperature = initial_heat_temperature
        self.initial_room_temperature = initial_room_temperature
        self.in_heater_on = in_heater_on
        self.T = T
        self.T_heater = T_heater

        return Fmi3Status.ok

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

    def fmi3SetBinary(self, value_references, values):
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

    def fmi3UpdateDiscreteStates(self):
        status = Fmi3Status.ok
        discrete_states_need_update = False
        terminate_simulation = False
        nominals_continuous_states_changed = False
        values_continuous_states_changed = False
        next_event_time_defined = True
        next_event_time = 1.0



        return (status, discrete_states_need_update, terminate_simulation, nominals_continuous_states_changed,
                values_continuous_states_changed, next_event_time_defined, next_event_time)

    # ================= Helpers =================

    def _set_value(self, references, values):
        if (self.state == FMIState.FMIConfigurationModeState or self.state == FMIState.FMIReconfigurationModeState):
            for r, v in zip(references, values):
                if (r in self.clocked_variables) or (r in self.reference_to_attribute):
                    return Fmi3Status.error 
                setattr(self, self.all_references[r], v)
        elif (self.state == FMIState.FMIEventModeState):
            for r, v in zip(references, values):
                if (r in self.reference_to_attribute) or (r in self.tunable_structural_parameters):
                    return Fmi3Status.error 
                setattr(self, self.all_references[r], v)
        else:
            for r, v in zip(references, values):
                if ((self.event_mode_used) and (r in self.tunable_parameters)) or (r in self.clocked_variables) or (r in self.tunable_structural_parameters) or (r in self.parameters):
                    return Fmi3Status.error              
                setattr(self, self.reference_to_attribute[r], v)
        return Fmi3Status.ok

    def _get_value(self, references):

        values = []
        for r in references:
            if (self.state != FMIState.FMIEventModeState and (r in self.clocked_variables)):
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


if __name__ == "__main__":
    m = Model("plant",
            "1234",
            "",
            False,
            False,
            False,
            False,
            None
            )
    m.in_heater_on = True
    assert m.fmi3DoStep(0.0, 1.0, False)[0] == Fmi3Status.ok
    assert m.fmi3DoStep(1.0, 1.0, False)[0] == Fmi3Status.ok