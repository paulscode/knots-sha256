#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots SHA256 developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Our shipped policy defaults, filter by filter, side by side with -corepolicy=1 (Core's policy).

The functional test framework starts every node with -corepolicy, so most tests never see our defaults; this one
starts node 0 with -corepolicy=0 and node 1 with -corepolicy=1. Each case is refused by node 0 for its stated
reason and relayed by node 1: a default that changes, or a -corepolicy reset that goes missing, fails here
(series/knobs-decisions.yaml, decisions/0013, 0024, 0025)."""
from test_framework.key import ECKey
from test_framework.messages import COutPoint, CTransaction, CTxIn, CTxInWitness, CTxOut
from test_framework.script import CScript, OP_1, OP_2, OP_13, OP_CHECKMULTISIG, OP_CHECKSIG, OP_DUP, OP_EQUALVERIFY, OP_RETURN, OP_TRUE
from test_framework.script_util import program_to_witness_script, script_to_p2wsh_script
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_greater_than
from test_framework.wallet import MiniWallet


class PolicyDefaultsTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [["-corepolicy=0"], ["-corepolicy=1"]]

    def with_outputs(self, outputs, locktime=0, fee=2000):
        tx = self.wallet.create_self_transfer()["tx"]
        tx.nLockTime = locktime
        for value, spk in outputs:
            tx.vout.append(CTxOut(value, spk))
        tx.vout[0].nValue -= sum(v for v, _ in outputs) + fee
        return tx

    def check(self, name, tx, reason):
        ours, core = (n.testmempoolaccept([tx.serialize().hex()])[0] for n in self.nodes)
        self.log.info(f"{name}: ours {ours.get('reject-reason', 'accept')}, core {core.get('reject-reason', 'accept')}")
        assert not ours["allowed"] and ours["reject-reason"] == reason, (name, ours)
        assert core["allowed"], (name, core)

    def run_test(self):
        self.wallet = MiniWallet(self.nodes[0])
        self.generate(self.wallet, 120)
        key = ECKey(); key.generate()
        pk = key.get_pubkey().get_bytes()

        self.check("P2PK output (-permitbarepubkey=0)", self.with_outputs([(10_000, CScript([pk, OP_CHECKSIG]))]), "bare-pubkey")
        self.check("bare multisig output (-permitbaremultisig=0)", self.with_outputs([(10_000, CScript([OP_1, pk, pk, OP_2, OP_CHECKMULTISIG]))]), "bare-multisig")
        self.check("OP_RETURN of 41 bytes, 43-byte script (-datacarriersize=42)", self.with_outputs([(0, CScript([OP_RETURN, b"x" * 41]))]), "datacarrier")
        self.check("two OP_RETURN outputs (-datacarriermultiple=0)", self.with_outputs([(0, CScript([OP_RETURN, b"a" * 10])), (0, CScript([OP_RETURN, b"b" * 10]))]), "multi-op-return")
        self.check("Runes message (-rejecttokens=1)", self.with_outputs([(0, CScript([OP_RETURN, OP_13, b"\x00" * 5]))]), "tokens-runes")
        self.check("nLockTime 21 (-rejectparasites=1)", self.with_outputs([], locktime=21), "parasite-cat21")
        self.check("witness v2 output (-acceptunknownwitness=0, decisions/0025)", self.with_outputs([(10_000, program_to_witness_script(2, b"y" * 40))]), "scriptpubkey-unknown-witnessversion")
        self.check("padded P2WSH program (-rejectfakeoutputs=1)", self.with_outputs([(10_000, program_to_witness_script(0, bytes(8) + b"\x5a" * 24))]), "txn-datacarrier-nonstandard")

        self.log.info("-minrelaytxfee 1 sat/vB (Core 0.1)")
        tx = self.wallet.create_self_transfer(fee_rate=0)["tx"]
        tx.vout[0].nValue -= tx.get_vsize() // 2  # 0.5 sat/vB
        self.check("0.5 sat/vB", tx, "min relay fee not met")

        self.log.info("-maxscriptsize 1650 (Core: 3600 for a P2WSH script)")
        # ~2.1 kB, 9 opcodes: four 520-byte pushes, each checked against itself (nothing is dropped unread)
        big = CScript([x for _ in range(4) for x in (b"\x42" * 520, OP_DUP, OP_EQUALVERIFY)] + [OP_TRUE])
        fund = self.wallet.send_to(from_node=self.nodes[0], scriptPubKey=script_to_p2wsh_script(big), amount=100_000)
        self.generate(self.nodes[0], 1)
        spend = CTransaction()
        spend.vin = [CTxIn(COutPoint(int(fund["txid"], 16), fund["sent_vout"]))]
        spend.vout = [CTxOut(90_000, self.wallet.get_output_script())]
        spend.wit.vtxinwit = [CTxInWitness()]
        spend.wit.vtxinwit[0].scriptWitness.stack = [bytes(big)]
        r = self.nodes[0].testmempoolaccept([spend.serialize().hex()])[0]
        assert not r["allowed"] and r["reject-reason"] == "bad-witness-witness-size", r  # Knots applies it to the whole witness stack
        assert self.nodes[1].testmempoolaccept([spend.serialize().hex()])[0]["allowed"]

        self.log.info("-datacarriercost 2 (decisions/0024): our policy size of a 40-byte OP_RETURN payment is larger")
        tx = self.with_outputs([(0, CScript([OP_RETURN, b"z" * 40]))])
        ours, core = (n.testmempoolaccept([tx.serialize().hex()])[0] for n in self.nodes)
        assert ours["allowed"] and core["allowed"], (ours, core)
        assert_equal(ours["vsize"] - core["vsize"], 42)  # 42 script bytes, 4 extra WU each = 42 vbytes

        self.log.info("Both nodes relay an ordinary payment")
        tx = self.with_outputs([(10_000, program_to_witness_script(1, bytes.fromhex("9f537de0a7f7403067880d3d62d3f8d20889c4f77b74b612406d7d5ce0a9b206")))])
        for n in self.nodes:
            assert n.testmempoolaccept([tx.serialize().hex()])[0]["allowed"]


if __name__ == "__main__":
    PolicyDefaultsTest(__file__).main()
