from os import getenv
import sys

from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)
from algosdk.v2client import algod
from beaker import client
from dotenv import load_dotenv

from contracts.aarons_kit import AaronsKit

load_dotenv(".env")

algod_token = getenv("NODE_API_KEY")
headers = {
    "X-API-Key": algod_token,
}
algod_client = None


def deploy(algod_client):
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


if __name__ == "__main__":
    args = sys.argv

    if len(args) > 1 and args[1] == "mainnet":
        algod_url = getenv("ALGOD_URL_MAINNET")
        print("Deploying to mainnet...")
    else:
        print("Deploying to testnet...")
        algod_url = getenv("ALGOD_URL_TESTNET")

    algod_client = algod.AlgodClient(algod_token, algod_url, headers)

    deploy(algod_client)
