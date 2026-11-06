#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots SHA256 developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""-datacarriercost: our default of 2 (decisions/0024), its rounding, the 1 sat/vB floor and RBF.

An OP_RETURN script's bytes weigh 4 WU each in consensus; at a cost of C they weigh ceil-to-WU(4*C), so the extra
weight per byte is that minus 4 (none at or below 1). The policy size is what feerates are measured against
everywhere, admission and replacement included."""
from decimal import Decimal

from test_framework.messages import CTxOut
from test_framework.script import CScript, OP_RETURN
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error
from test_framework.wallet import MiniWallet

PAYLOAD = b"x" * 40           # within our -datacarriersize=42 (OP_RETURN + push + 40)
DATA = CScript([OP_RETURN, PAYLOAD])


class DataCarrierCostDefaultTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 5
        self.setup_clean_chain = True
        self.extra_args = [
            ["-corepolicy=0"],                          # 0: our default, 2 -> 8 WU per byte
            ["-corepolicy=0", "-datacarriercost=1"],    # 1: Knots' default, 4 WU: no extra
            ["-corepolicy=0", "-datacarriercost=1.01"], # 2: rounds up to 5 WU
            ["-corepolicy=0", "-datacarriercost=0.3"],  # 3: rounds to 2 WU, below consensus: no extra for outputs
            ["-corepolicy=1"],                          # 4: Core's 0.25
        ]

    def setup_network(self):
        self.setup_nodes()  # each node judges on its own; blocks are synced by hand

    def run_test(self):
        self.wallet = MiniWallet(self.nodes[0])
        self.generate(self.wallet, 120, sync_fun=self.no_op)
        for n in self.nodes[1:]:
            for h in range(n.getblockcount() + 1, self.nodes[0].getblockcount() + 1):
                n.submitblock(self.nodes[0].getblock(self.nodes[0].getblockhash(h), 0))

        self.log.info("Policy size of a 40-byte OP_RETURN payment at each cost")
        tx = self.wallet.create_self_transfer(confirmed_only=True)["tx"]
        tx.vout[0].nValue -= 2000
        tx.vout.append(CTxOut(0, DATA))
        w = tx.get_weight()
        n = len(DATA)
        res = [node.testmempoolaccept([tx.serialize().hex()])[0] for node in self.nodes]
        assert all(r["allowed"] for r in res), res
        assert_equal(res[0]["vsize"], (w + n * 4 + 3) // 4)
        assert_equal(res[1]["vsize"], (w + 3) // 4)
        assert_equal(res[2]["vsize"], (w + n * 1 + 3) // 4)
        assert_equal(res[3]["vsize"], (w + 3) // 4)
        assert_equal(res[4]["vsize"], (w + 3) // 4)
        assert_equal(res[0]["vsize_bip141"], (w + 3) // 4)

        self.log.info("At 1 sat per raw vbyte a data transaction is under our floor; at 1 sat per policy vbyte it is not")
        for pays_policy_size in (False, True):
            utxo = self.wallet.get_utxo(confirmed_only=True)
            t = self.wallet.create_self_transfer(utxo_to_spend=utxo, fee_rate=0)["tx"]
            t.vout.append(CTxOut(0, DATA))
            size = (t.get_weight() + 3) // 4 + (n if pays_policy_size else 0)
            t.vout[0].nValue = int(utxo["value"] * 100_000_000) - size  # 1 sat per vbyte of that size
            r = self.nodes[0].testmempoolaccept([t.serialize().hex()])[0]
            if pays_policy_size:
                assert r["allowed"], r
            else:
                assert_equal(r["reject-reason"], "min relay fee not met")
            assert self.nodes[1].testmempoolaccept([t.serialize().hex()])[0]["allowed"]  # cost 1: raw size is the policy size

        self.log.info("RBF: a data replacement that wins on raw feerate but loses on policy feerate")
        utxo = self.wallet.get_utxo(confirmed_only=True)
        original = self.wallet.create_self_transfer(utxo_to_spend=utxo, fee_rate=Decimal("0.00013"))["tx"]
        replacement = self.wallet.create_self_transfer(utxo_to_spend=utxo, fee_rate=Decimal("0.00001"))["tx"]
        replacement.vout.append(CTxOut(0, DATA))
        v_orig = original.get_vsize()
        v_raw = (replacement.get_weight() + 3) // 4
        v_policy = (replacement.get_weight() + n * 4 + 3) // 4
        fee_orig = int(utxo["value"] * 100_000_000) - sum(o.nValue for o in original.vout)
        fee_repl = int(13.6 * v_raw) + 1
        replacement.vout[0].nValue = int(utxo["value"] * 100_000_000) - fee_repl
        assert fee_repl / v_raw > fee_orig / v_orig > fee_repl / v_policy, (fee_repl, v_raw, v_policy, fee_orig, v_orig)
        assert fee_repl - fee_orig >= v_policy  # pays the incremental relay fee for its policy size too
        for node in (self.nodes[0], self.nodes[1]):
            node.sendrawtransaction(original.serialize().hex())
        assert_raises_rpc_error(-26, "insufficient fee", self.nodes[0].sendrawtransaction, replacement.serialize().hex())
        self.nodes[1].sendrawtransaction(replacement.serialize().hex())


if __name__ == "__main__":
    DataCarrierCostDefaultTest(__file__).main()
