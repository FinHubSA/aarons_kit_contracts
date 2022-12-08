from typing import Final

from beaker import *
from pyteal import *


class AaronsKit(Application):
    manager: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="The address of the account that can manage this contract.",
        default=Txn.sender(),
    )

    total_distributed: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The total amount of donations distributed by this contract.",
        default=Int(0),
    )

    donations_snapshot: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The latest snapshot of the donations for this contract.",
        default=Int(0),
    )

    papers_scraped_snapshot: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="The latest snapshot of the number of papers scraped.",
        default=Int(0),
    )

    @create
    def create(self):
        return Seq(
            self.initialize_application_state(),
        )

    @opt_in
    def opt_in(self):
        return Reject()

    @close_out
    def close_out(self):
        return Reject()

    @update
    def update(self):
        return Assert(Txn.sender() == self.manager.get())

    @delete
    def delete(self):
        return Assert(Txn.sender() == self.manager.get())

    @external
    def set_manager(self, new_manager: abi.Address):
        return Seq(
            Assert(Txn.sender() == self.manager.get()),
            self.manager.set(new_manager.get()),
        )

    @external
    def take_snapshot(
        self,
        papers_scraped: abi.Uint64,
    ):
        """
        We must distribute funds from a snapshot of the number of papers scraped
        and current donation balance. This way we avoid updates of the live values
        from interfering with the distribution math.
        """

        return Seq(
            Assert(Txn.sender() == self.manager.get()),
            Assert(Balance(Global.current_application_address()) > Int(0)),
            self.donations_snapshot.set(
                Balance(Global.current_application_address())
                - MinBalance(Global.current_application_address())
            ),
            self.papers_scraped_snapshot.set(papers_scraped.get()),
        )

    @external
    def distribute_donations_4(
        self,
        papers_scraped_1: abi.Uint64,
        papers_scraped_2: abi.Uint64,
        papers_scraped_3: abi.Uint64,
        papers_scraped_4: abi.Uint64,
        scraper_addr_1: abi.Account,
        scraper_addr_2: abi.Account,
        scraper_addr_3: abi.Account,
        scraper_addr_4: abi.Account,
    ):
        """
        Distribute donations to four accounts
        """

        return self._distribute_donations()

    @external
    def distribute_donations_3(
        self,
        papers_scraped_1: abi.Uint64,
        papers_scraped_2: abi.Uint64,
        papers_scraped_3: abi.Uint64,
        scraper_addr_1: abi.Account,
        scraper_addr_2: abi.Account,
        scraper_addr_3: abi.Account,
    ):
        """
        Distribute donations to three accounts
        """

        return self._distribute_donations()

    @external
    def distribute_donations_2(
        self,
        papers_scraped_1: abi.Uint64,
        papers_scraped_2: abi.Uint64,
        scraper_addr_1: abi.Account,
        scraper_addr_2: abi.Account,
    ):
        """
        Distribute donations to two accounts
        """

        return self._distribute_donations()

    @external
    def distribute_donations_1(
        self,
        papers_scraped_1: abi.Uint64,
        scraper_addr_1: abi.Account,
    ):
        """
        Distribute donations to one account
        """

        return self._distribute_donations()

    @internal(TealType.none)
    def _distribute_donations(self):
        """
        Distribute donations
        """

        return Seq(
            Assert(Txn.sender() == self.manager.get()),
            For(
                (i := ScratchVar()).store(Int(1)),
                i.load() < Txn.accounts.length() + Int(1),
                i.store(i.load() + Int(1)),
            ).Do(
                (amount := ScratchVar()).store(
                    (
                        Btoi(Txn.application_args[i.load()])
                        * self.donations_snapshot.get()
                    )
                    / self.papers_scraped_snapshot.get()
                ),
                If(
                    And(
                        amount.load() > Int(0),
                        Not(
                            And(
                                amount.load() < Int(100_000),
                                Balance(Txn.accounts[i.load()]) == Int(0),
                            ),
                        ),
                    ),
                ).Then(
                    self.total_distributed.set(
                        self.total_distributed.get() + amount.load()
                    ),
                    InnerTxnBuilder.Execute(
                        {
                            TxnField.type_enum: TxnType.Payment,
                            TxnField.sender: Global.current_application_address(),
                            TxnField.receiver: Txn.accounts[i.load()],
                            TxnField.amount: amount.load(),
                            TxnField.fee: Int(0),
                        }
                    ),
                ),
            ),
        )
