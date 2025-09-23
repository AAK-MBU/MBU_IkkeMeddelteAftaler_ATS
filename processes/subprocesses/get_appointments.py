"""Module for functions related to retrieving appointments for the queue"""

import calendar
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from helpers import config
from processes.application_handler import get_app

logger = logging.getLogger(__name__)


def get_appointments():
    """Get appointmets of ikke meddelte aftaler"""

    solteq_app = get_app()

    # Open view with list of appointments
    logger.info("Åbner aftalebog")
    solteq_app.open_from_main_menu(menu_item="Aftalebog")

    solteq_app.open_tab("Oversigt")

    # Set dates, clinic and status to get correct appointments
    logger.info("Sætter dato")
    start_date, end_date = get_start_end_dates()
    logger.info(f"{start_date.strftime('%d/%m-%Y')}-{end_date.strftime('%d/%m-%Y')}")

    solteq_app.set_date_in_aftalebog(from_date=start_date, to_date=end_date)

    logger.info("Datoer er sat korrekt")

    solteq_app.pick_appointment_types_aftalebog(appointment_types="Ikke meddelt aftale")

    logger.info("'Ikke meddelt aftale' valgt")

    solteq_app.pick_clinic_aftalebog(clinic="Aarhus Tandregulering")

    # Retrieve appointments in view
    logger.info("Henter aftaler")

    appointments = solteq_app.get_appointments_aftalebog(
        close_after=True, headers_to_keep=["Navn", "Cpr", "Aftaletype"]
    )

    if len(appointments) > 0:
        list_keys = list(appointments.keys())
        list_values = list(appointments.values())

        # Remove appointments with no name (seemingly notes put in the aftalebog...)
        popped = [
            appointments.pop(list_keys[j])
            for j, v in enumerate(list_values)
            if '"Navn": " "' in json.dumps(v)
        ]

        logger.info(f"{len(popped)} aftaler uden navn fjernet fra listen")
        logger.info(f"{len(appointments)} aftaler hentet")

    return appointments


def get_start_end_dates() -> tuple[datetime, datetime]:
    """Function to get start and end dates for period to handle.
    If today is between the 1st and 15th, then 1st to 15th of next month is selected.
    If today is after the 15th, then 16th to end of next month is selected"""
    # Get the current date
    current_date = datetime.now(tz=ZoneInfo("Europe/Copenhagen"))

    # Check if the current day of the month is between 1 and 15 (not including. Allowing for cron to run on 3rd specific weekday of month)
    if config.MONTH_START <= current_date.day < config.MONTH_MID:
        # Set start_date to 1st of next month
        start_date = current_date.replace(day=config.MONTH_START) + timedelta(
            days=calendar.monthrange(current_date.year, current_date.month)[1]
        )
        # Set end_date to 15th of next month
        end_date = start_date.replace(day=config.MONTH_MID)
    else:
        # Set start_date to 16th of next month
        start_date = current_date.replace(day=config.MONTH_MID + 1) + timedelta(
            days=calendar.monthrange(current_date.year, current_date.month)[1]
        )
        # Set end_date to end of next month
        end_date = start_date.replace(
            day=calendar.monthrange(start_date.year, start_date.month)[1]
        )

    return start_date, end_date
