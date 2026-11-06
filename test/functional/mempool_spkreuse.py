#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots SHA256 developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""-spkreuse=conflict: an unconfirmed pubkey script is exclusive to one transaction.

Covers the four rejections (twin outputs, change to the spent script, reuse that conflicts, and the chained case
where the conflict is the transaction's own ancestor), RBF over a reuse conflict, ignore_rejects, and that
txn-spk-reused-chained cannot be ignored (it would leave a transaction spending a coin removed with its parent)."""
from decimal import Decimal

from test_framework.messages import COIN, COutPoint, CTransaction, CTxIn, CTxInWitness, CTxOut
from test_framework.script import CScript, OP_EQUAL
from test_framework.script_util import script_to_p2wsh_script
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error
from test_framework.wallet import MiniWallet


def lock(n):
    return CScript([n, OP_EQUAL])


def spk(n):
    return script_to_p2wsh_script(lock(n))


class SpkReuseTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [[], ["-spkreuse=conflict"]]

    def setup_network(self):
        self.setup_nodes()  # not connected: only blocks are synced, by hand

    def fund(self, n, amount=100_000):
        out = self.wallet.send_to(from_node=self.nodes[0], scriptPubKey=spk(n), amount=amount)
        return {"outpoint": COutPoint(int(out["txid"], 16), out["sent_vout"]), "n": n, "value": amount}

    def tx(self, coins, outputs):
        tx = CTransaction()
        tx.vin = [CTxIn(c["outpoint"]) for c in coins]
        tx.vout = [CTxOut(v, s) for v, s in outputs]
        tx.wit.vtxinwit = []
        for c in coins:
            w = CTxInWitness()
            w.scriptWitness.stack = [CScript([c["n"]])[1:] if c["n"] > 16 else bytes([c["n"]]), bytes(lock(c["n"]))]
            tx.wit.vtxinwit.append(w)
        return tx

    def send(self, node, tx, ignore=None):
        return node.sendrawtransaction(hexstring=tx.serialize().hex(), maxfeerate=0, ignore_rejects=ignore or [])

    def run_test(self):
        allow, conflict = self.nodes
        self.wallet = MiniWallet(allow)
        self.generate(self.wallet, 110, sync_fun=self.no_op)
        coins = [self.fund(n) for n in range(1, 11)]
        self.generate(allow, 1, sync_fun=self.no_op)
        for b in range(conflict.getblockcount() + 1, allow.getblockcount() + 1):
            conflict.submitblock(allow.getblock(allow.getblockhash(b), 0))
        assert_equal(conflict.getbestblockhash(), allow.getbestblockhash())

        self.log.info("Twin outputs to one script")
        tx = self.tx([coins[0]], [(40_000, spk(100)), (40_000, spk(100))])
        assert_raises_rpc_error(-26, "txn-spk-reused-twinoutputs", self.send, conflict, tx)
        assert_equal(allow.testmempoolaccept([tx.serialize().hex()])[0]["allowed"], True)
        self.send(conflict, tx, ["txn-spk-reused"])  # ignorable: the whole rule off for this transaction
        assert tx.txid_hex in conflict.getrawmempool()

        self.log.info("Change back to the script being spent")
        tx = self.tx([coins[1]], [(90_000, spk(coins[1]["n"]))])
        assert_raises_rpc_error(-26, "txn-spk-reused-change", self.send, conflict, tx)

        self.log.info("A second unconfirmed payment to one script conflicts with the first; RBF rules decide")
        first = self.tx([coins[2]], [(90_000, spk(200))])
        self.send(conflict, first)
        cheaper = self.tx([coins[3]], [(91_000, spk(200))])  # pays less fee than the first
        assert_raises_rpc_error(-26, "insufficient fee", self.send, conflict, cheaper)
        richer = self.tx([coins[3]], [(80_000, spk(200))])
        self.send(conflict, richer)
        mempool = conflict.getrawmempool()
        assert richer.txid_hex in mempool and first.txid_hex not in mempool

        self.log.info("Reuse that conflicts with the transaction's own ancestor (chained), not ignorable")
        parent = self.tx([coins[4]], [(45_000, spk(300)), (45_000, spk(301))])
        self.send(conflict, parent)
        # The child conflicts with its parent (both pay script 301); it outbids the parent so that the replacement
        # fee rules pass and the ancestor check is what decides
        child = self.tx([{"outpoint": COutPoint(parent.txid_int, 0), "n": 300}], [(10_000, spk(301))])
        assert_raises_rpc_error(-26, "txn-spk-reused-chained", self.send, conflict, child)
        assert_raises_rpc_error(-26, "txn-spk-reused-chained", self.send, conflict, child, ["txn-spk-reused-chained"])
        assert parent.txid_hex in conflict.getrawmempool()
        # With the whole rule ignored the child is no reuse conflict at all
        self.send(conflict, child, ["txn-spk-reused"])
        assert {parent.txid_hex, child.txid_hex} <= set(conflict.getrawmempool())

        self.log.info("-spkreuse=allow (the default) relays all of it")
        tx = self.tx([coins[5]], [(40_000, spk(400)), (40_000, spk(400))])
        self.send(allow, tx)


if __name__ == "__main__":
    SpkReuseTest(__file__).main()
