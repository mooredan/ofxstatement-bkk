# ofxstatement-bkk

Bangkok Bank (BKK) plugin for [ofxstatement](https://github.com/kedder/ofxstatement).

This tool converts Bangkok Bank CSV export files into OFX format, suitable for importing into GnuCash, Microsoft Money, or other personal finance software.

## Installation

### For Users
If you simply want to use the plugin, install it directly from the source:

```bash
pip3 install --user .

```

### For Developers

To set up a development environment to modify the code or run tests:

```bash
# Install in editable mode
pip3 install --user -e .

# Install build/test dependencies
pip3 install build pytest mypy

```

*(Note: If you prefer `pipenv`, you can still use `pipenv sync --dev` and `pipenv shell` as configured in the Pipfile.)*

## Configuration

After installation, configure `ofxstatement` to use this plugin. Add the following section to your configuration file (usually located at `~/.config/ofxstatement/config.ini`):

```ini
[bkk]
plugin = bkk
# The BKK CSV usually comes in UTF-8, but if you have issues, 
# you can specify the encoding here.
# encoding = utf-8

```

## Usage

Download your transaction history from Bangkok Bank Online Banking as a CSV file.


### Convert to OFX

Run the `ofxstatement` tool:

```bash
ofxstatement convert -t bkk BKK_Export.csv statement.ofx

```

### Import

Import the resulting `statement.ofx` file into GnuCash or your preferred finance software.

## Development & Contributing
This project uses pyproject.toml for dependency management.

### Running Tests

This project uses `pytest` and a `Makefile` for convenience. The test suite includes an iterative runner that checks all CSV files found in the `tests/` directory.

```bash
make test

```

### Packaging

To build a distributable wheel:

```bash
python3 -m build

```

### Reporting Bugs & Missing Transactions

If you encounter a transaction type that causes a crash or is not parsed correctly:

1. **Obfuscate your data:** Do **not** upload raw financial statements to GitHub.


## References

* [OFX Specification (v2.3)](https://financialdataexchange.org/common/Uploaded%20files/OFX%20files/OFX%20Banking%20Specification%20v2.3.pdf)
* [ofxstatement Documentation](https://github.com/kedder/ofxstatement)

```

