"""This module contains functions related to handling the list of patients to be handled manually"""

import json
import logging
import os
from io import BytesIO

import openpyxl
from itk_dev_shared_components.smtp import smtp_util
from mbu_dev_shared_components.database.connection import RPAConnection

from processes.subprocesses.call_database import get_manual_list
from processes.subprocesses.get_appointments import get_start_end_dates

logger = logging.getLogger(__name__)


def delete_temp_files(path):
    """Function to delete temp files if any exists"""
    # Check path exists
    if os.path.exists(path):
        # List files in path
        tmp_files = os.listdir(path)
        # Delete all files in path
        if len(tmp_files) > 0:
            logger.info(
                f"Temp-folderen er ikke tom. {len(tmp_files)} fil(er) i mappen slettes"
            )
            for tmp_file in tmp_files:
                logger.info(f"Sletter filen: {tmp_file}")
                os.remove(os.path.join(path, tmp_file))


def create_excel_sheet(path):
    """Function to create excel sheet from sql table"""
    start_date, end_date = get_start_end_dates()
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    logger.info(f"Periode: {start_date_str} - {end_date_str}")
    manual_list = get_manual_list(
        start_date=start_date,
        end_date=end_date,
    )

    filename = (
        f"Ikke meddelte aftaler - Manuelliste {start_date_str}_{end_date_str}.xlsx"
    )
    filepath = os.path.join(path, filename)
    if not os.path.exists(path):
        os.makedirs(path)
    # Remove cell border fix
    manual_list = manual_list.T.reset_index().T
    manual_list.to_excel(filepath, header=False, index=False)

    logger.info("Manuel liste dannet.")

    return filepath


def send_manual_list(filepath: str):
    """Function to send email with manual list"""
    filename = filepath.split("\\")[-1]

    start_date, end_date = get_start_end_dates()
    start_date = start_date.strftime("%d.%m.%Y")
    end_date = end_date.strftime("%d.%m.%Y")

    # Read excel file into BytesIO object
    wb = openpyxl.load_workbook(filepath)

    # Select the active worksheet (or specify the sheet name)
    ws = wb.active

    # Get the number of rows
    number_of_rows = ws.max_row

    excel_buffer = BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    with RPAConnection(db_env="PROD", commit=False) as rpa_conn:
        email_sender = rpa_conn.get_constant("e-mail_noreply").get("value", "")
        smtp_server = rpa_conn.get_constant("smtp_adm_server").get("value", "")
        smtp_port = rpa_conn.get_constant("smtp_port").get("value", "")
        procargs = json.loads(
            rpa_conn.get_constant("ikkemeddelteaftaler_procargs").get("value", "")
        )

    email_recipient = procargs["email_receiver"]
    email_subject = f"Manuel liste for perioden {start_date}-{end_date}"
    email_body = procargs["email_body"]
    attachments = [smtp_util.EmailAttachment(file=excel_buffer, file_name=filename)]
    smtp_util.send_email(
        receiver=email_recipient,
        sender=email_sender,
        subject=email_subject,
        body=email_body,
        html_body=True,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        attachments=attachments if attachments else None,
    )

    logger.info(
        f"E-mail med manuel liste ({number_of_rows - 1} rækker) afsendt til {email_recipient}."
    )
