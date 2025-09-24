"""This file contains functions with calls to SQL database"""

from datetime import datetime, time

import pandas as pd
from mbu_dev_shared_components.database.connection import RPAConnection


def get_manual_list(start_date: str, end_date: str):
    """
    Function to get the manual list from the SQL database.

    Args:
        orcestrator_connection (OrchestratorConnection): OpenOrchestrator connection
        start_date (datetime): start date for current period handled
        end_date (datetime): end date for current period handled

    Returns:
        manual_list (pd.DataFrame): Dataframe with the manual list
    """

    # Set time range to 00:00:00 - 23:59:59 (start_date to end_date)
    start_date = datetime.combine(start_date, time.min)
    end_date = datetime.combine(end_date, time.max)
    manual_list = None

    with RPAConnection(db_env="PROD", commit=False) as rpa_conn:
        query = """
            SELECT
                Name
                ,CPR
                ,AppointmentType
                ,Description
            FROM [RPA].[rpa].[MBU006IkkeMeddelteAftaler]
            WHERE Date BETWEEN ? AND ?
        """
        res = rpa_conn.execute_query(query, (start_date, end_date))
        # Get all rows from query
        rows = res.fetchall()

        # Package in pandas
        manual_list = pd.DataFrame.from_records(
            rows, columns=[col[0] for col in res.description]
        )

    return manual_list


def insert_manual_list(sql_info: dict, date: datetime):
    """
    Function to insert queue info into manual list due to business error.

    Args:
        orchestrator_connection (OrchestratorConnection): Open Orchestrator connection
        sql_info (dict): Dictionary with info to be inserted in sql database"""
    rpa_conn = RPAConnection(db_env="PROD", commit=True)

    with rpa_conn:
        query = """
            USE [RPA]

            INSERT INTO [rpa].[MBU006IkkeMeddelteAftaler]
                (Name,
                CPR,
                AppointmentType,
                Description,
                OrchestratorTransactionNumber,
                OrchestratorReference,
                Date)
            VALUES
                (?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?)
        """
        rpa_conn.execute_query(
            query,
            (
                sql_info["name_var"],
                sql_info["cpr_var"],
                sql_info["appointment_type_var"],
                sql_info["description_var"],
                "",
                sql_info["item_reference"],
                date,
            ),
        )
