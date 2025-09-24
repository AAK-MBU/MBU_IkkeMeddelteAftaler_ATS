"""Module to hande queue population"""

import asyncio
import logging
from datetime import datetime

from automation_server_client import Workqueue

from helpers import config
from processes.application_handler import close, startup
from processes.subprocesses.get_appointments import get_appointments

logger = logging.getLogger(__name__)


def retrieve_items_for_queue() -> list[dict]:
    """Function to populate queue"""
    startup()
    appointments = get_appointments()
    data = list(appointments.values())
    # ruff: noqa: DTZ005
    references = [f"{datetime.now().strftime('%d%m%Y')}_{k}" for k in appointments]

    items = [
        {"reference": ref, "data": d} for ref, d in zip(references, data, strict=True)
    ]
    close()
    return items


async def concurrent_add(workqueue: Workqueue, items: list[dict]) -> None:
    """
    Populate the workqueue with items to be processed.
    Uses concurrency and retries with exponential backoff.

    Args:
        workqueue (Workqueue): The workqueue to populate.
        items (list[dict]): List of items to add to the queue.
        logger (logging.Logger): Logger for logging messages.

    Returns:
        None

    Raises:
        Exception: If adding an item fails after all retries.
    """
    sem = asyncio.Semaphore(config.MAX_CONCURRENCY)

    async def add_one(it: dict):
        reference = str(it.get("reference") or "")
        data = {"item": it}

        async with sem:
            for attempt in range(1, config.MAX_RETRIES + 1):
                try:
                    await asyncio.to_thread(workqueue.add_item, data, reference)
                    return True
                except Exception as e:
                    if attempt >= config.MAX_RETRIES:
                        logger.error(
                            f"Failed to add item {reference} after {attempt} attempts: {e}"
                        )
                        return False
                    backoff = config.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"Error adding {reference} (attempt {attempt}/{config.MAX_RETRIES}). "
                        f"Retrying in {backoff:.2f}s... {e}"
                    )
                    await asyncio.sleep(backoff)

    if not items:
        logger.info("No new items to add.")
        return

    results = await asyncio.gather(*(add_one(i) for i in items))
    successes = sum(1 for r in results if r)
    failures = len(results) - successes
    logger.info(
        f"Summary: {successes} succeeded, {failures} failed out of {len(results)}"
    )
