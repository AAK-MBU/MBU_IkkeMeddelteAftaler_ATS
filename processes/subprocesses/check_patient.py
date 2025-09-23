"""
Runs checks on patient, to if person should be handled or not
"""

import logging

import pandas as pd
import uiautomation as auto
from mbu_dev_shared_components.solteqtand.application import SolteqTandApp
from mbu_dev_shared_components.solteqtand.application.exceptions import (
    ManualProcessingRequiredError,
)

logger = logging.getLogger(__name__)


class NoAppointmentFoundError(Exception):
    """Custom exception"""

    def __init__(self, message="Error occurred while finding appointment."):
        super().__init__(message)


class ORAppointmentFoundError(Exception):
    """Custom exception"""

    def __init__(self, message="Error occurred while finding appointment."):
        super().__init__(message)


def check_patient(SSN: str, solteq_app: SolteqTandApp) -> auto.Control:
    """Function to check different requirements for patient before patient is handled.

    Args:
        orchestrator_connection (OrchestratorConnection): The connection to OpenOrchestrator
        solteq_app (SolteqTandApp): The SolteqTand application instance
        SSN (str): CPR number of the current patient

    returns:
        appointment_control (auto.Control): Control of the appointment to handle
    """
    appointment_control = None
    appointments = check_or_aftale_meddelt(
        solteq_app=solteq_app,
        return_dict=True,
    )
    logger.info("Ingen 'OR aftale meddelt' fundet")
    # Find first ikke_meddelt_aftale
    appointment_control = select_first_appointment(
        appointments=appointments,
        appointment_to_select="Ikke meddelt aftale",
    )

    if appointment_control:
        return appointment_control

    raise ManualProcessingRequiredError


def select_first_appointment(
    appointments: dict,
    appointment_to_select: str,
):
    """
    Searches for appointment in sorted dataframe.
    Raises NoAppointmentFoundError if appointment type cannot be found"""
    try:
        appointments_df = appointments["dataframe"]
        first_ikke_meddelt = appointments_df[
            (
                (appointments_df["Status"] == appointment_to_select)
                & (appointments_df["Klinik"] == "121")
            )
        ].index[0]
        appointment_control = appointments["controls"][first_ikke_meddelt]

        return appointment_control
    except IndexError as e:
        logger.error(f"Ingen {appointment_to_select} found")
        raise NoAppointmentFoundError from e


def check_or_aftale_meddelt(
    solteq_app: SolteqTandApp,
    return_dict: bool = False,
):
    # Get list of appointments
    logger.info("Tjekker om der er en OR aftale meddelt")
    appointments = solteq_app.get_list_of_appointments()
    # Wrap code below in function appointments_as_df(self,sort: str | None = None)
    appointments_df = pd.DataFrame(appointments)  # As dataframe
    appointments_df["Starttid"] = pd.to_datetime(
        appointments_df["Starttid"], format="%d-%m-%Y %H:%M"
    )  # Format as timestamps
    appointments_df.sort_values(
        by="Starttid",
        ascending=True,
        inplace=True,  # Sort first to latest (to find first ikke-meddelt)
    )
    appointments["dataframe"] = appointments_df

    if "OR Aftale meddelt" in appointments["Status"]:
        logger.info("'OR aftale meddelt' fundet")
        raise ORAppointmentFoundError

    if return_dict:
        return appointments
