from os import getenv

from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)
from algosdk.v2client import algod
from beaker import client
from dotenv import load_dotenv

from contracts.aarons_kit import AaronsKit

# Current contract details in testnet (already deployed):
# * App ID = 151578019
# * Address = ZH6QHCFO4UKUHDKFMTJDAQDMENWOFRKAKQCOC4RWBE54MJKCOBXCPO6OHE
# * Tx ID = YVTD7FVNT7TMED6RZ75QQLPVU4M2MBAJT7CXYSJSBFNSFGN6QEVQ

load_dotenv(".env")

# Deploying to testnet only for now
algod_url = getenv("ALGOD_URL_TESTNET")
algod_token = getenv("NODE_API_KEY")
headers = {
    "X-API-Key": algod_token,
}

algod_client = algod.AlgodClient(algod_token, algod_url, headers)

app_client = client.ApplicationClient(
    client=algod_client,
    app=AaronsKit(version=7),
    signer=AccountTransactionSigner(getenv("DEPLOYMENT_PRIVATE")),
)

app_id, app_addr, app_txid = app_client.create()
print(
    """
    Deployed contract with:
    * App ID = {}
    * Address = {}
    * Tx ID = {}
    """.format(
        app_id, app_addr, app_txid
    )
)
