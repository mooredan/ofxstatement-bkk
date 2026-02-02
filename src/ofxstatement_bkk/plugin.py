import csv
import re
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, TextIO

from ofxstatement.plugin import Plugin
from ofxstatement.parser import AbstractStatementParser
from ofxstatement.statement import Statement, StatementLine


class BkkPlugin(Plugin):
    """Bangkok Bank (BKK) plugin for ofxstatement"""

    def get_parser(self, filename: str) -> "BkkParser":
        return BkkParser(filename)


class BkkParser(AbstractStatementParser):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.statement = Statement()
        self.statement.bank_id = "BKKBTHBK"
        self.statement.currency = "THB"
        self.id_generator = IdGenerator()

    def parse_decimal(self, value: str) -> Decimal:
        """Parse localised numbers, cleaning up commas and spaces."""
        return Decimal(value.replace(",", "").replace(" ", ""))

    def parse_record(self, line: List[str]) -> Optional[StatementLine]:
        """Parse given transaction line and return StatementLine object"""
        # CSV Structure:
        # [0]: (Space or Header)
        # [1]: Date
        # [2]: Description
        # [3]: Debit
        # [4]: Credit
        # [5]: Balance
        # [6]: Channel
        # [7]: (Blank)

        # Basic validation
        if len(line) != 8:
            return None

        # Skip blank lines or lines that don't start with the expected spacer
        if not line[0] or line[0] != " " or line[7] != "":
            return None

        stmt_line = StatementLine()
        stmt_line.memo = line[2]

        # Amount parsing
        if line[3]:  # Debit
            stmt_line.amount = -self.parse_decimal(line[3])
        elif line[4]:  # Credit
            stmt_line.amount = self.parse_decimal(line[4])
        else:
            stmt_line.amount = Decimal(0)

        # Date parsing
        # Format: "dd MMM yyyy HH:mm"
        try:
            stmt_line.date = datetime.strptime(line[1][0:16], "%d %b %Y %H:%M")
        except ValueError:
            return None

        # Transaction Type Classification
        channel = line[6]
        memo = line[2]

        stmt_line.trntype = "UNKNOWN"

        if channel == "MOB":
            if memo.startswith("Payment for Goods /Services"):
                stmt_line.trntype = "PAYMENT"
            elif memo.startswith("Transfer") or memo.startswith("Interbank Transfer"):
                stmt_line.trntype = "XFER"
            elif memo.startswith("PromptPay Transfer/Top Up"):
                stmt_line.trntype = "PAYMENT"

        elif channel == "E-CHN":
            if memo.startswith("Purchase via e-Channels"):
                stmt_line.trntype = "PAYMENT"

        elif channel == "ATM":
            if memo.startswith("Cash Withdrawal"):
                stmt_line.trntype = "ATM"

        elif channel == "User":
            if memo.startswith("International Transfer"):
                stmt_line.trntype = "XFER"

        elif channel == "AUTO":
            if memo.startswith("Commission/Annual Fee"):
                stmt_line.trntype = "FEE"
            if memo.startswith("International Transfer"):
                stmt_line.trntype = "XFER"

        return stmt_line

    def parse(self) -> Statement:
        """Main entry point for parsers"""
        with open(self.filename, "r", encoding="utf-8") as fin:
            reader = csv.reader(fin)

            for csv_line in reader:
                if not csv_line:
                    continue

                # Handle Metadata Headers
                if csv_line[0] == "Account Number":
                    if len(csv_line) > 1:
                        self.statement.account_id = csv_line[1]
                    continue

                if (
                    csv_line[0] == "Account Nickname"
                    and len(csv_line) > 3
                    and csv_line[2] == "Ledger Balance"
                ):
                    # Redundant if Account Number was found, but safe
                    self.statement.account_id = csv_line[1]
                    self.statement.end_balance = self.parse_decimal(csv_line[3])
                    continue

                # Parse Transactions
                stmt_line = self.parse_record(csv_line)
                if stmt_line:
                    # NOTE: We cannot call assert_valid() here yet because
                    # the ID hasn't been generated. We do that after the loop.
                    self.statement.lines.append(stmt_line)

        self.statement.account_type = "SAVINGS"

        # Reverse lines to ensure chronological order (Oldest -> Newest)
        self.statement.lines.reverse()

        # Generate IDs sequentially AND Validate
        self.id_generator.reset()
        for line in self.statement.lines:
            if line.date:  # <--- Added check to satisfy mypy
                line.id = self.id_generator.create_id(line.date)

            # Now that ID is set, we can safely validate
            line.assert_valid()

        if self.statement.lines:
            self.statement.start_date = min(
                sl.date for sl in self.statement.lines if sl.date
            )
            self.statement.end_date = max(
                sl.date for sl in self.statement.lines if sl.date
            )

        return self.statement


class IdGenerator:
    """Generates unique IDs based on the date and sequence"""

    def __init__(self) -> None:
        self.date_count: dict[str, int] = {}

    def reset(self) -> None:
        self.date_count.clear()

    def create_id(self, date: datetime) -> str:
        date_str = date.strftime("%Y%m%d")
        self.date_count[date_str] = self.date_count.get(date_str, 0) + 1
        return f"{date_str}-{self.date_count[date_str]}"
