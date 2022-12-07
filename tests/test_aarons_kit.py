from algosdk.account import generate_account
from algosdk.atomic_transaction_composer import AccountTransactionSigner
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
    def setup_method(self):
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
    def test_set_manager(self):
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

    def test_set_manager_not_manager(self):
        """set manager without being current manager (txn should fail)"""
        new_manager = sandbox.get_accounts()[0]

        try:
            self.app_client.call(
                AaronsKit.set_manager,
                new_manager=new_manager.address,
                sender=new_manager.address,
                signer=AccountTransactionSigner(new_manager.private_key),
            )
            assert False
        except client.LogicException:
            pass

    # set_snapshots
    def test_set_snapshots(self):
        # set snapshots as manager
        donation_amount = 50_000_000
        self.donate(donation_amount)

        papers_scraped = 1000
        self.app_client.call(
            AaronsKit.set_snapshots,
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

    def test_set_snapshots_less_mbr(self):
        """set snapshots without being manager (txn should fail)"""
        papers_scraped = 1000

        try:
            self.app_client.call(
                AaronsKit.set_snapshots,
                papers_scraped=papers_scraped,
            )
            assert False
        except client.LogicException:
            pass

    def test_set_snapshots_not_manager(self):
        """set snapshots without being manager (txn should fail)"""
        donation_amount = 50_000_000
        self.donate(donation_amount)

        papers_scraped = 1000
        other_account = sandbox.get_accounts()[0]

        try:
            self.app_client.call(
                AaronsKit.set_snapshots,
                papers_scraped=papers_scraped,
                sender=other_account.address,
                signer=AccountTransactionSigner(other_account.private_key),
            )
            assert False
        except client.LogicException:
            pass

    # distribute_donations
    def test_distribute_donations(self):
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
            AaronsKit.set_snapshots,
            papers_scraped=total_papers_scraped,
        )

        sp = self.app_client.client.suggested_params()
        sp.fee = 5000

        self.app_client.call(
            AaronsKit.distribute_donations_4,
            papers_scraped_1=papers_scraped[0],
            papers_scraped_2=papers_scraped[1],
            papers_scraped_3=papers_scraped[2],
            papers_scraped_4=papers_scraped[3],
            scraper_addr_1=scraper_addresses[0],
            scraper_addr_2=scraper_addresses[1],
            scraper_addr_3=scraper_addresses[2],
            scraper_addr_4=scraper_addresses[3],
            suggested_params=sp,
        )

        sp.fee = 4000

        self.app_client.call(
            AaronsKit.distribute_donations_3,
            papers_scraped_1=papers_scraped[4],
            papers_scraped_2=papers_scraped[5],
            papers_scraped_3=papers_scraped[6],
            scraper_addr_1=scraper_addresses[4],
            scraper_addr_2=scraper_addresses[5],
            scraper_addr_3=scraper_addresses[6],
            suggested_params=sp,
        )

        sp.fee = 3000

        self.app_client.call(
            AaronsKit.distribute_donations_2,
            papers_scraped_1=papers_scraped[7],
            papers_scraped_2=papers_scraped[8],
            scraper_addr_1=scraper_addresses[7],
            scraper_addr_2=scraper_addresses[8],
            suggested_params=sp,
        )

        sp.fee = 2000

        self.app_client.call(
            AaronsKit.distribute_donations_1,
            papers_scraped_1=papers_scraped[9],
            scraper_addr_1=scraper_addresses[9],
            suggested_params=sp,
        )

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

    def test_distribute_donations_not_manager(self):
        """distribute donations without being manager (txn should fail"""
        other_account = sandbox.get_accounts()[0]
        donation_amount = 50_000_000
        self.donate(donation_amount)

        scraper_addresses = []
        for _ in range(4):
            _, address = generate_account()
            scraper_addresses.append(address)

        papers_scraped = [1623, 9384, 87, 902]
        total_papers_scraped = sum(papers_scraped)

        self.app_client.call(
            AaronsKit.set_snapshots,
            papers_scraped=total_papers_scraped,
        )

        sp = self.app_client.client.suggested_params()
        sp.fee = 5000

        try:
            self.app_client.call(
                AaronsKit.distribute_donations_4,
                papers_scraped_1=papers_scraped[0],
                papers_scraped_2=papers_scraped[1],
                papers_scraped_3=papers_scraped[2],
                papers_scraped_4=papers_scraped[3],
                scraper_addr_1=scraper_addresses[0],
                scraper_addr_2=scraper_addresses[1],
                scraper_addr_3=scraper_addresses[2],
                scraper_addr_4=scraper_addresses[3],
                suggested_params=sp,
                sender=other_account.address,
                signer=AccountTransactionSigner(other_account.private_key),
            )
            assert False
        except client.LogicException:
            pass

    # util
    def donate(self, donation_amount: int):
        sp = self.app_client.get_suggested_params()
        donor = sandbox.get_accounts()[0]

        donation_txn = transaction.PaymentTxn(
            sender=donor.address,
            receiver=self.app_client.app_addr,
            amt=donation_amount,
            sp=sp,
        )

        donation_txn = donation_txn.sign(donor.private_key)

        self.app_client.client.send_transaction(donation_txn)
