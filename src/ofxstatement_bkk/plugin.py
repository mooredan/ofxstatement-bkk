import sys

from os import path

from decimal import Decimal, Decimal as D
from datetime import datetime
import re
from typing import Dict, Optional, Any, Iterable, List, TextIO, TypeVar, Generic

from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser

from ofxstatement.parser import AbstractStatementParser
from ofxstatement.statement import Statement, StatementLine

import csv


class BkkPlugin(Plugin):
    """Sample plugin (for developers only)"""

    def get_parser(self, filename: str) -> "BkkParser":
        parser = BkkParser(filename)
        return parser


class BkkParser(AbstractStatementParser):
    statement: Statement
    fin: TextIO  # file input stream

    cur_record: int = 0

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.statement = Statement()
        self.statement.bank_id = "BKKBTHBK"
        self.statement.currency = "THB"
        self.id_generator = IdGenerator()

    def parse_decimal(self, value: str) -> D:
        # some plugins pass localised numbers, clean them up
        return D(value.replace(",", "").replace(" ", ""))

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object"""

        stmt_line = StatementLine()

        # line[0 ] : ,
        # line[1 ] : Date,
        # line[2 ] : Description,
        # line[3 ] : Debit,
        # line[4 ] : Credit,
        # line[5 ] : Balance,
        # line[6 ] : Channel,
        # line[7 ] : ,

        # msg = f"self.cur_record: {self.cur_record}"
        # print(msg, file=sys.stderr)

        # there must be exactly 8 fields
        line_length = len(line)
        if line_length != 8:
            return None

        # skip blank lines
        if not line[0]:
            return None

        # first field must be one space
        if not line[0] == " ":
            return None

        # last field must be blank
        if not line[7] == "":
            return None

        # memo
        stmt_line.memo = line[2]

        # amount
        field = "amount"
        if line[3]:
            rawvalue = line[3]
            value = self.parse_decimal(rawvalue)
            value = -value
            setattr(stmt_line, field, value)
        if line[4]:
            rawvalue = line[4]
            value = self.parse_decimal(rawvalue)
            setattr(stmt_line, field, value)

        # date
        date = datetime.strptime(line[1][0:16], "%d %b %Y %H:%M")
        stmt_line.date = date
        id = self.id_generator.create_id(date)
        stmt_line.id = id

        # trntype
        stmt_line.trntype = "UNKNOWN"

        match_result = re.match(r"^Payment for Goods /Services", line[2])
        if match_result and line[6] == "MOB":
            stmt_line.trntype = "PAYMENT"

        match_result = re.match(r"^Purchase via e-Channels", line[2])
        if match_result and line[6] == "E-CHN":
            stmt_line.trntype = "PAYMENT"

        match_result = re.match(r"^Cash Withdrawal - .* ATM", line[2])
        if match_result and line[6] == "ATM":
            stmt_line.trntype = "ATM"

        match_result = re.match(r"^International Transfer", line[2])
        if match_result and line[6] == "User":
            stmt_line.trntype = "XFER"

        match_result = re.match(r"^Commission/Annual Fee", line[2])
        if match_result and line[6] == "AUTO":
            stmt_line.trntype = "FEE"

        match_result = re.match(r"^Transfer", line[2])
        if match_result and line[6] == "MOB":
            stmt_line.trntype = "XFER"

        match_result = re.match(r"^PromptPay Transfer/Top Up", line[2])
        if match_result and line[6] == "MOB":
            stmt_line.trntype = "PAYMENT"

        return stmt_line

    # parse the CSV file and return a Statement
    def parse(self) -> Statement:
        """Main entry point for parsers"""
        with open(self.filename, "r") as fin:

            self.fin = fin
            reader = csv.reader(self.fin)

            # loop through the CSV file lines
            for csv_line in reader:
                # print(f"{csv_line}")
                self.cur_record += 1

                if not csv_line:
                    continue

                if csv_line[0] == "Account Number":
                    self.statement.account_id = csv_line[1]
                    continue

                if (
                    csv_line[0] == "Account Nickname"
                    and csv_line[2] == "Ledger Balance"
                ):
                    self.statement.account_id = csv_line[1]
                    rawvalue = csv_line[3]
                    value = self.parse_decimal(rawvalue)
                    self.statement.end_balance = value
                    continue

                if not csv_line[0] == " ":
                    continue

                stmt_line = self.parse_record(csv_line)
                if stmt_line:
                    stmt_line.assert_valid()
                    self.statement.lines.append(stmt_line)
                    # print(f"{stmt_line}")

            # this is a Savings account
            self.statement.account_type = "SAVINGS"

            # reverse the lines
            self.statement.lines.reverse()

            # reset the date count in the id generator
            self.id_generator.reset()

            # after reversing the lines in the list, update the id
            for line in self.statement.lines:
                date = line.date
                new_id = self.id_generator.create_id(date)
                line.id = new_id

            # figure out start_date and end_date for the statement
            self.statement.start_date = min(
                sl.date for sl in self.statement.lines if sl.date is not None
            )
            self.statement.end_date = max(
                sl.date for sl in self.statement.lines if sl.date is not None
            )

            # print(f"{self.statement}")
            return self.statement


class IdGenerator:
    """Generates a unique ID based on the date

    Hopefully any JSON file that we get will have all the transactions for a
    given date, and hopefully in the same order each time so that these IDs
    will match up across exports.
    """

    def __init__(self) -> None:
        self.date_count: Dict[str, int] = {}

    def reset(self) -> None:
        self.date_count.clear()

    def create_id(self, date) -> str:
        date_str = datetime.strftime(date, "%Y%m%d")
        self.date_count[date_str] = self.date_count.get(date_str, 0) + 1
        return f"{date_str}-{self.date_count[date_str]}"
