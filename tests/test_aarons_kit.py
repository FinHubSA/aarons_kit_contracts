from algosdk.abi import Method
from algosdk.account import generate_account
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AtomicTransactionResponse,
    TransactionWithSigner,
)
from algosdk.encoding import encode_address
from algosdk.future import transaction
from beaker import *
from beaker.client import state_decode
from contracts.aarons_kit import AaronsKit

from util.sandbox import call_sandbox_command


# uncomment to reset sandbox before tests
# requires sandbox to already be up
# def setup_module(_):
#     print("Setting up sandbox...")
#     call_sandbox_command("reset")


class TestAaronsKit:
    def setup_method(self) -> None:
        self.deployment_account = sandbox.get_accounts().pop()

        self.app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AaronsKit(version=7),
            signer=self.deployment_account.signer,
        )

        self.app_id, self.app_addr, self.app_txid = self.app_client.create()

        print(
            f"""
            Deployed aarons_kit app in txid {self.app_txid}
            App ID: {self.app_id} 
            App Address: {self.app_addr} 
            """
        )

    # set_manager
    def test_set_manager(self) -> None:
        """set manager as current manager"""
        new_manager_address = sandbox.get_accounts()[0].address

        self.app_client.call(
            AaronsKit.set_manager,
            new_manager=new_manager_address,
        )

        global_state = state_decode.decode_state(
            self.app_client.client.application_info(self.app_id)["params"][
                "global-state"
            ]
        )

        assert global_state is not None
        assert (
            encode_address(bytes.fromhex(global_state["manager"]))
            == new_manager_address
        )

    # set_snapshots
    def test_take_snapshot(self) -> None:
        # set snapshots as manager
        donation_amount = 50_000_000
        self.donate(donation_amount)

        papers_scraped = 1000
        self.app_client.call(
            AaronsKit.take_snapshot,
            papers_scraped=papers_scraped,
        )

        global_state = state_decode.decode_state(
            self.app_client.client.application_info(self.app_id)["params"][
                "global-state"
            ]
        )

        assert global_state is not None
        assert global_state["donations_snapshot"] == donation_amount - 100_000
        assert global_state["papers_scraped_snapshot"] == papers_scraped
        assert (
            encode_address(bytes.fromhex(global_state["manager"]))
            == self.deployment_account.address
        )

    def test_take_snapshot_less_mbr(self) -> None:
        """set snapshots without being manager (txn should fail)"""
        papers_scraped = 1000

        try:
            self.app_client.call(
                AaronsKit.take_snapshot,
                papers_scraped=papers_scraped,
            )
            assert False
        except client.LogicException:
            pass

    # distribute_donations
    def test_distribute_donations(self) -> None:
        """distribute donations as manager"""
        donation_amount = 50_000_000
        self.donate(donation_amount)

        scraper_addresses = []
        for _ in range(10):
            _, address = generate_account()
            scraper_addresses.append(address)

        papers_scraped = [
            1623,
            9384,
            87,
            902,
            24_771,
            7198,
            102,
            5349,
            72_094,
            885,
        ]
        total_papers_scraped = sum(papers_scraped)

        self.app_client.call(
            AaronsKit.take_snapshot,
            papers_scraped=total_papers_scraped,
        )

        self.distribute_donations(scraper_addresses, papers_scraped)

        expected_payments = list(
            map(
                lambda payment: payment if payment >= 100_000 else 0,
                map(
                    lambda scraped: (scraped * (donation_amount - 100_000))
                    // total_papers_scraped,
                    papers_scraped,
                ),
            )
        )

        for i in range(len(scraper_addresses)):
            actual_amount = self.app_client.client.account_info(scraper_addresses[i])[
                "amount"
            ]
            assert actual_amount == expected_payments[i]

        global_state = state_decode.decode_state(
            self.app_client.client.application_info(self.app_id)["params"][
                "global-state"
            ]
        )

        assert global_state is not None
        assert global_state["total_distributed"] == sum(expected_payments)

    # util
    def donate(self, donation_amount: int) -> None:
        sp = self.app_client.get_suggested_params()
        donor = sandbox.get_accounts()[0]

        donation_txn = transaction.PaymentTxn(
            sender=donor.address,
            receiver=self.app_client.app_addr,
            amt=donation_amount,
            sp=sp,
        )

        donation_txn = donation_txn.sign(donor.private_key)

        tx_id = self.app_client.client.send_transaction(donation_txn)
        transaction.wait_for_confirmation(self.app_client.client, tx_id, 5)

    def distribute_donations(
        self,
        scraper_addresses: list[str],
        papers_scraped: list[int],
    ) -> AtomicTransactionResponse:
        sp = self.app_client.client.suggested_params()

        atc = AtomicTransactionComposer()
        start_index = 0

        method = Method.from_signature("distribute_donations()void")

        while start_index < len(scraper_addresses):
            end_index = start_index + min(4, len(scraper_addresses) - start_index)

            accounts = scraper_addresses[start_index:end_index]
            scraped = papers_scraped[start_index:end_index]
            scraped.insert(0, method.get_selector())

            sp.fee = 1000 + (len(accounts) * 1000)

            atc.add_transaction(
                TransactionWithSigner(
                    transaction.ApplicationNoOpTxn(
                        sender=self.deployment_account.address,
                        sp=sp,
                        index=self.app_id,
                        app_args=scraped,
                        accounts=accounts,
                    ),
                    self.deployment_account.signer,
                )
            )

            start_index = end_index

        return atc.execute(self.app_client.client, 5)
