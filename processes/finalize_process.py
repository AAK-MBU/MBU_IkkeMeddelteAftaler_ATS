"""Module to handle process finalization"""

import logging

from automation_server_client import Workqueue

from helpers import config
from helpers.ats_functions import get_workqueue_items

# from helpers.process_args import get_procargs
from processes.subprocesses.handle_manual_list import (
    create_excel_sheet,
    delete_temp_files,
    send_manual_list,
)

logger = logging.getLogger(__name__)


class QueueNotEmptyError(Exception):
    """Exception to handle non-empty queue"""

    def __init__(self, message="Error wile creating manual list. Queue not empty."):
        super().__init__(message)


def finalize_process(workqueue: Workqueue):
    """Function to finalize robot process by preparing and sending manual list as excel"""
    logger.info("Finalizing.")
    # procargs = get_procargs()
    logger.info("Checking if queue is empty.")
    queue = get_workqueue_items(workqueue, return_data=True)
    if any(b.get("status") in ("new", "in progress") for b in queue.values()):
        raise QueueNotEmptyError(
            message=f"Køen var ikke tom da den manuelle liste skulle dannes men indeholdte {len(queue)} elementer."
        )
    path = config.TMP_PATH
    logger.info(f"Deleting existing files from {path}")
    delete_temp_files(path)

    logger.info("Creating excel sheet with manual list")
    filepath = create_excel_sheet(path)

    logger.info("Sending manual list")
    send_manual_list(
        filepath=filepath
    )  # Add procargs as argument if we go back from having it in constants table

    logger.info(f"Deleting files from {path}")
    delete_temp_files(path)
