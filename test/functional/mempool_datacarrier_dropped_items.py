#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots SHA256 developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""-datacarrierdroppeditems: spent-stack items a script removes without reading them are data.

A script can start from up to 100 witness items of 80 bytes (or scriptSig pushes under P2SH) and throw them away
with OP_DROP / OP_2DROP / OP_NIP: the bytes ride along at the witness discount and no rule counted them. Mainnet
carried 51 such inputs of ~1.4 kB each in 144 blocks (2026-11-05, `<key> OP_CHECKSIGVERIFY OP_DROP...`).
Also -fakeoutputtext: an output program that is all printable text is data under -rejectfakeoutputs."""
from test_framework.key import ECKey, compute_xonly_pubkey, generate_privkey
from test_framework.messages import COutPoint, CTransaction, CTxIn, CTxInWitness, CTxOut, sha256
from test_framework.script import (
    CScript, OP_2DROP, OP_CHECKSIGVERIFY, OP_DROP, OP_DUP, OP_ENDIF, OP_EQUAL, OP_EQUALVERIFY, OP_IF, OP_NIP,
    OP_1ADD, OP_SHA256, OP_SIZE, OP_SWAP, OP_TOALTSTACK, OP_FROMALTSTACK, OP_TRUE, hash160, taproot_construct,
)
from test_framework.script_util import program_to_witness_script, script_to_p2sh_script, script_to_p2wsh_script
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal
from test_framework.wallet import MiniWallet

NONSTANDARD = "txn-datacarrier-nonstandard"
EXCEEDED = "txn-datacarrier-exceeded"
ITEM = bytes(range(32, 112))  # 80 bytes of text


class DataCarrierDroppedItemsTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 4
        self.setup_clean_chain = True
        self.extra_args = [
            ["-corepolicy=0"],                                                            # 0: our defaults (both off)
            ["-corepolicy=0", "-datacarrierdroppeditems=1", "-fakeoutputtext=1"],         # 1: both on
            ["-corepolicy=0", "-datacarrierdroppeditems=1", "-acceptnonstddatacarrier=1", "-datacarriersize=83"],  # 2: counted in the budget
            [],                                                                           # 3: the framework's -corepolicy turns it off
        ]

    def accept(self, node, tx):
        return node.testmempoolaccept([tx.serialize().hex()])[0]

    def check(self, node, tx, reason):
        r = self.accept(node, tx)
        if reason is None:
            assert r["allowed"], r
        else:
            assert not r["allowed"] and r["reject-reason"] == reason, r

    def fund(self, spk):
        utxo = self.wallet.send_to(from_node=self.nodes[0], scriptPubKey=spk, amount=100_000)
        self.generate(self.nodes[0], 1)
        return COutPoint(int(utxo["txid"], 16), utxo["sent_vout"])

    def spend(self, outpoint, stack=None, script_sig=b""):
        tx = CTransaction()
        tx.vin = [CTxIn(outpoint, CScript(script_sig))]
        tx.vout = [CTxOut(90_000, self.wallet.get_output_script())]
        if stack is not None:
            tx.wit.vtxinwit = [CTxInWitness()]
            tx.wit.vtxinwit[0].scriptWitness.stack = stack
        return tx

    def p2wsh(self, script, items):
        return self.spend(self.fund(script_to_p2wsh_script(script)), list(items) + [bytes(script)])

    def tapscript(self, script, items):
        tap = taproot_construct(compute_xonly_pubkey(generate_privkey())[0], [("leaf", script)])
        leaf = tap.leaves["leaf"]
        control = bytes([leaf.version | tap.negflag]) + tap.internal_pubkey + leaf.merklebranch
        return self.spend(self.fund(tap.scriptPubKey), list(items) + [bytes(script), control])

    def run_test(self):
        self.wallet = MiniWallet(self.nodes[0])
        self.generate(self.wallet, 110)
        off, on, budget, corepolicy = self.nodes

        self.log.info("Items dropped by a leading OP_2DROP run (P2WSH)")
        tx = self.p2wsh(CScript([OP_2DROP] * 9 + [OP_TRUE]), [ITEM] * 18)
        self.check(off, tx, None)
        self.check(on, tx, NONSTANDARD)
        self.check(budget, tx, EXCEEDED)
        self.check(corepolicy, tx, None)

        self.log.info("The mainnet shape: a signature check, then drops (tapscript); the signature itself is read")
        key = ECKey(); key.generate()
        xonly = compute_xonly_pubkey(key.get_bytes())[0]
        # No real signature is needed to see the counting: a non-empty one would have to be valid, an empty one fails
        # OP_CHECKSIGVERIFY, so the node refuses it either way, with the datacarrier reason first.
        tx = self.tapscript(CScript([xonly, OP_CHECKSIGVERIFY] + [OP_DROP] * 6 + [OP_TRUE]), [ITEM] * 6 + [bytes(64)])
        self.check(on, tx, NONSTANDARD)

        self.log.info("Evasions: copy then drop, move through the alt stack, swap, NIP, a branch on a witness flag")
        for script, items in [
            (CScript([OP_DUP, OP_2DROP, OP_DROP, OP_TRUE]), [ITEM, ITEM]),
            (CScript([OP_TOALTSTACK, OP_TOALTSTACK, OP_FROMALTSTACK, OP_FROMALTSTACK, OP_2DROP, OP_TRUE]), [ITEM, ITEM]),
            (CScript([OP_SWAP, OP_DROP, OP_DROP, OP_TRUE]), [ITEM, ITEM]),
            (CScript([OP_NIP, OP_NIP]), [ITEM, ITEM, b"\x01"]),
            (CScript([OP_IF, OP_2DROP, OP_ENDIF, OP_TRUE]), [ITEM, ITEM, b"\x01"]),
            (CScript([OP_SIZE, OP_DROP, OP_DROP, OP_TRUE]), [ITEM]),
        ]:
            tx = self.p2wsh(script, items)
            self.check(off, tx, None)
            self.check(on, tx, NONSTANDARD)

        self.log.info("Legacy P2SH: scriptSig pushes dropped by the redeem script")
        redeem = CScript([OP_2DROP, OP_TRUE])
        tx = self.spend(self.fund(script_to_p2sh_script(redeem)), script_sig=CScript([ITEM[:70], ITEM[:70], bytes(redeem)]))
        self.check(off, tx, None)
        self.check(on, tx, NONSTANDARD)

        self.log.info("Items the script reads are not data: a hash lock with an 80-byte preimage, a size check")
        preimage = ITEM
        tx = self.p2wsh(CScript([OP_SHA256, sha256(preimage), OP_EQUAL]), [preimage])
        self.check(on, tx, None)
        tx = self.p2wsh(CScript([OP_SIZE, 80, OP_EQUALVERIFY, OP_SHA256, sha256(preimage), OP_EQUAL]), [preimage])
        self.check(on, tx, None)

        self.log.info("Branches on computed values are followed: a hash comparison, arithmetic on a witness number")
        secret = b"open"
        tx = self.p2wsh(CScript([OP_SHA256, sha256(secret), OP_EQUAL, OP_IF, OP_2DROP, OP_ENDIF, OP_TRUE]), [ITEM, ITEM, secret])
        self.check(off, tx, None)
        self.check(on, tx, NONSTANDARD)
        tx = self.p2wsh(CScript([OP_1ADD, OP_IF, OP_2DROP, OP_ENDIF, OP_TRUE]), [ITEM, ITEM, b""])
        self.check(off, tx, None)
        self.check(on, tx, NONSTANDARD)

        self.log.info("The data cost weighs dropped items where non-standard data is accepted")
        tx = self.p2wsh(CScript([OP_DROP, OP_TRUE]), [ITEM[:30]])
        r_budget = self.accept(budget, tx)
        assert r_budget["allowed"], r_budget
        assert_equal(r_budget["vsize"], (tx.get_weight() + 30 * 7 + 3) // 4)  # cost 2: 8 - 1 extra weight per witness byte

        self.log.info("-fakeoutputtext: an output program of printable text")
        for program in [b"abcdefghijklmnopqrstuvwxyz012345", b'sfer","tick":"mske","amt":10000}']:
            tx = self.wallet.create_self_transfer()["tx"]
            tx.vout[0].nValue -= 2000
            tx.vout.append(CTxOut(1000, program_to_witness_script(0, program)))
            self.check(on, tx, NONSTANDARD)
            if program[0] == ord("a"):  # 32 distinct bytes: the -rejectfakeoutputs counts alone pass it
                self.check(off, tx, None)
        tx = self.wallet.create_self_transfer()["tx"]
        tx.vout[0].nValue -= 2000
        tx.vout.append(CTxOut(1000, program_to_witness_script(0, sha256(b"random"))))
        self.check(on, tx, None)

        self.log.info("-datacarriercost out of range is a start-up error (a negative value used to wrap)")
        self.stop_node(3)
        for bad in ["-1", "1000.01"]:
            self.nodes[3].assert_start_raises_init_error([f"-datacarriercost={bad}"], "Error: -datacarriercost must be between 0 and 1000")


if __name__ == "__main__":
    DataCarrierDroppedItemsTest(__file__).main()
