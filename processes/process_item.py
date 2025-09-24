"""Module to handle item processing"""

import json
import logging

from mbu_dev_shared_components.solteqtand.application import SolteqTandApp
from mbu_dev_shared_components.solteqtand.application.exceptions import (
    ManualProcessingRequiredError,
    NotMatchingError,
    PatientNotFoundError,
)
from mbu_rpa_core.exceptions import BusinessError

from processes.application_handler import get_app
from processes.subprocesses.call_database import insert_manual_list
from processes.subprocesses.check_patient import (
    NoAppointmentFoundError,
    ORAppointmentFoundError,
    check_patient,
)
from processes.subprocesses.get_appointments import get_start_end_dates

logger = logging.getLogger(__name__)


def process_item(item_data: dict, item_reference: str):
    """Docstring"""
    sql_info = get_sql_info(item_data, item_reference)
    solteq_app = get_app()
    # This try-except catches all errors, and adds patient to manual list
    try:
        handle_patient(item_data, item_reference, solteq_app)
    except Exception as e:
        sql_info["description_var"] = str(e)
        # Connects to RPA sql
        logger.info("Tilføjer person til manuel liste")

        start_date, _ = get_start_end_dates()

        insert_manual_list(
            sql_info=sql_info,
            date=start_date,
        )

        raise BusinessError(
            "Person tilføjet til manuel liste"
        ) from e  # Raises BusinessError in maun file to handle workitem status


def handle_patient(item_data: dict, item_reference: str, solteq_app: SolteqTandApp):
    """
    Function to process items in Ikke meddelte aftaler.
    Process changes status of appointments and sends out messages to patient.
    If any business error, queue element is added to a manual list in an SQL database.
    """

    # Find the patient
    SSN = item_data["Cpr"].replace("-", "")
    logger.info("Indtaster CPR og laver opslag")
    try:
        solteq_app.open_patient(SSN)
        # solteq_app.open_tab("Stamkort")
        logger.info("Patientjournalen blev åbnet")
    except TimeoutError as e:
        missing_contact_info = solteq_app.find_element_by_property(
            control=solteq_app.app_window, name="Manglende kontaktoplysninger"
        )
        if missing_contact_info:
            raise BusinessError("Intet telefonnummer knyttet til patienten.") from e
        else:
            raise e from e
    except (NotMatchingError, PatientNotFoundError, Exception) as e:
        logger.error(str(e))
        raise BusinessError("Fejl ved åbning af patient") from e

    patient_window = solteq_app.app_window

    # Here to check that patient fulfills criteria.
    # If OR aftale meddelt: close and put on manual
    try:
        appointment_control = check_patient(
            solteq_app=solteq_app,
            SSN=SSN,
        )
        solteq_app.change_appointment_status(
            appointment_control=appointment_control,
            set_status="OR Aftale meddelt",
            send_msg=True,
        )
    except (
        NotMatchingError,
        ORAppointmentFoundError,
        NoAppointmentFoundError,
        ManualProcessingRequiredError,
        Exception,
    ) as e:
        logger.info("Lukker patientvindue")
        solteq_app.app_window = patient_window
        solteq_app.close_patient_window()
        e_string = set_error_string(e)
        raise BusinessError(e_string) from e


def set_error_string(error):
    if isinstance(error, NotMatchingError):
        e_string = "Indtastet CPR matcher ikke CPR fra den åbnede journal."
    elif isinstance(error, ORAppointmentFoundError):
        e_string = "'OR aftale meddelt' fundet"
    elif isinstance(error, NoAppointmentFoundError):
        e_string = "Ingen 'Ikke meddelt aftale' fundet"
    elif isinstance(error, ManualProcessingRequiredError):
        e_string = "Advarsel da aftale gemtes"
    else:
        e_string = "Ukendt fejl, tjek status på aftalen"

    return e_string


def get_sql_info(item_data: dict, item_reference: str):
    """Function to get SQL info for manual list from queue element"""
    item_data = json.loads(item_data) if not isinstance(item_data, dict) else item_data
    sql_info = {
        "name_var": item_data["Navn"],
        "cpr_var": item_data["Cpr"],
        "item_reference": item_reference,
        "appointment_type_var": item_data["Aftaletype"],
        "description_var": "",
    }
    return sql_info
