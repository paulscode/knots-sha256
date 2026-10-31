#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots SHA256 developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test that -datacarriercost applies to block template order, not only to admission.

A transaction carrying witness data can have a higher feerate by real weight
and a lower one by cost-adjusted weight than a plain transaction. With the
cost on, the template must take the plain transaction first; with the cost
off (0.25, one weight unit per witness byte) the data transaction comes first.
"""
from decimal import Decimal

from test_framework.messages import (
    COIN,
    COutPoint,
    CTransaction,
    CTxIn,
    CTxInWitness,
    CTxOut,
)
from test_framework.script import CScript, OP_0, OP_1, OP_ENDIF, OP_IF
from test_framework.script_util import script_to_p2wsh_script
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_greater_than
from test_framework.wallet import MiniWallet


class DatacarrierCostMiningTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        datacarrier = ["-acceptnonstddatacarrier=1", "-datacarriersize=1000"]
        self.extra_args = [
            ["-datacarriercost=1"] + datacarrier,
            ["-datacarriercost=0.25"] + datacarrier,
        ]

    def template_order(self, node, txids):
        order = [t["txid"] for t in node.getblocktemplate({"rules": ["segwit"]})["transactions"]]
        return [order.index(txid) for txid in txids]

    def run_test(self):
        costed, uncosted = self.nodes
        wallet = MiniWallet(costed)
        self.generate(wallet, 110)

        self.log.info("Build a data transaction: an OP_0 OP_IF envelope of 400 bytes in a P2WSH witness")
        witness_script = CScript([OP_0, OP_IF, b'\xab' * 400, OP_ENDIF, OP_1])
        funding = wallet.send_to(from_node=costed, scriptPubKey=script_to_p2wsh_script(witness_script), amount=100_000)
        self.generate(costed, 1)
        data_tx = CTransaction()
        data_tx.version = 2
        data_tx.vin = [CTxIn(COutPoint(int(funding["txid"], 16), funding["sent_vout"]))]
        data_tx.vout = [CTxOut(0, wallet.get_output_script())]
        data_tx.wit.vtxinwit = [CTxInWitness()]
        data_tx.wit.vtxinwit[0].scriptWitness.stack = [bytes(witness_script)]
        real_vsize = data_tx.get_vsize()
        data_fee = 10 * real_vsize  # 10 sat/vB by real weight
        data_tx.vout[0].nValue = 100_000 - data_fee
        data_txid = costed.sendrawtransaction(data_tx.serialize().hex())
        uncosted.sendrawtransaction(data_tx.serialize().hex())

        costed_vsize = costed.getmempoolentry(data_txid)["vsize"]
        assert_equal(uncosted.getmempoolentry(data_txid)["vsize"], real_vsize)
        assert_greater_than(costed_vsize, 2 * real_vsize)

        self.log.info("Build a plain transaction between the data transaction's real and cost-adjusted feerates")
        plain_rate = (Decimal(data_fee) / real_vsize + Decimal(data_fee) / costed_vsize) / 2  # sat/vB
        plain = wallet.create_self_transfer(fee_rate=plain_rate * 1000 / COIN)
        plain_txid = costed.sendrawtransaction(plain["hex"])
        uncosted.sendrawtransaction(plain["hex"])

        self.log.info("With the cost on, the plain transaction is mined first")
        data_pos, plain_pos = self.template_order(costed, [data_txid, plain_txid])
        assert_greater_than(data_pos, plain_pos)

        self.log.info("With the cost off, the data transaction is mined first")
        data_pos, plain_pos = self.template_order(uncosted, [data_txid, plain_txid])
        assert_greater_than(plain_pos, data_pos)


if __name__ == '__main__':
    DatacarrierCostMiningTest(__file__).main()
