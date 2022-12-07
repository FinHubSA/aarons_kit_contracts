# Aaron's kit Smart Contracts

# Description
This repository contains the Algorand smart contract(s) used for distributing donations to those who have contributed to Aaron's Kit (via its CLI) and have opted to receive such donations in ALGO.

# Testing
1. Make sure you have the [algorand sandbox](https://github.com/algorand/sandbox) up and running
1. Make sure you have an environment variable called ALGORAND_SANDBOX_PATH that points to the sandbox _executable_ (not directory)
1. Clone this repo
1. Create a Python virtual environment in the directory you've cloned to, e.g., `python3 -m venv .venv`
1. Run `pytest` or `pytest -s` for logs regardless of pass/fail
