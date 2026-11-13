#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots SHA256 developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Lightning must keep working at our defaults and with every policy option we may turn on.

Every script a Lightning implementation spends in normal operation, force closes and penalties, from BOLT 3 (anchor
channels, P2WSH) and LND's simple taproot channels (tapscript), is funded and spent with valid signatures, and so are
LDK's zero-fee commitment packages; each is put to testmempoolaccept (submitpackage) on:

  0  our defaults (-corepolicy=0)
  1  defaults + -datacarrierdroppeditems=1 -fakeoutputtext=1 (both our defaults since decisions/0028; kept explicit)
  2  defaults + -datacarrierunprovenkeys=1 (knots#422 knob)
  3  defaults + -bytespersigopstrict=51 (-acceptunknownwitness=0 is our default since decisions/0025)
  4  -corepolicy=1 (Core's policy, the reference)

Every node must accept every spend. A refusal on node 4 means the test itself is wrong.
"""
import hashlib

from test_framework.key import ECKey, compute_xonly_pubkey, generate_privkey, sign_schnorr
from test_framework.messages import COutPoint, CTransaction, CTxIn, CTxInWitness, CTxOut
from test_framework.script import (
    CScript, OP_0, OP_1, OP_2, OP_16, OP_CHECKLOCKTIMEVERIFY, OP_CHECKMULTISIG, OP_CHECKSEQUENCEVERIFY, OP_CHECKSIG,
    OP_CHECKSIGVERIFY, OP_DROP, OP_DUP, OP_ELSE, OP_ENDIF, OP_EQUAL, OP_EQUALVERIFY, OP_HASH160, OP_IF, OP_IFDUP,
    OP_NOTIF, OP_SIZE, OP_SWAP, OP_TRUE, SIGHASH_ALL, SegwitV0SignatureHash, TaprootSignatureHash, hash160,
    taproot_construct,
)
from test_framework.script_util import script_to_p2wsh_script
from test_framework.test_framework import BitcoinTestFramework
from test_framework.wallet import MiniWallet

FUNDING = 100_000
# Known, by design of knots#487 at our -datacarriersize=42: each LND revocation leaf counts 34 bytes against the data
# budget, so a justice transaction sweeping two revoked commitments at once (68 bytes) is refused; one per
# transaction relays. Core policy (node 4) relays both. Kept by decision (decisions/0025 item 6).
EXCEEDED = "txn-datacarrier-exceeded"
KNOWN_AT_42 = {"taproot to_local, PENALTY x2 inputs (one tx)": [EXCEEDED, EXCEEDED, EXCEEDED, EXCEEDED, "OK"]}
DELAY = 6          # to_self_delay
CLTV = 230         # HTLC expiry height (below the tip when spent)


def ripemd160(b):
    return hashlib.new("ripemd160", b).digest()


def ec():
    k = ECKey(); k.generate(compressed=True); return k


def xo():
    p = generate_privkey(); return p, compute_xonly_pubkey(p)[0]


class LnPolicyDefaultsTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 5
        self.setup_clean_chain = True
        self.extra_args = [["-corepolicy=0"], ["-corepolicy=0", "-datacarrierdroppeditems=1", "-fakeoutputtext=1"],
                           ["-corepolicy=0", "-datacarrierunprovenkeys=1"],
                           ["-corepolicy=0", "-acceptunknownwitness=0", "-bytespersigopstrict=51"], ["-corepolicy=1"]]

    def run_test(self):
        self.wallet = MiniWallet(self.nodes[0])
        self.generate(self.wallet, 210)
        preimage = b"\x42" * 32
        ph = hashlib.sha256(preimage).digest()
        cases = []

        def wsh(name, script, wit, seq=0xfffffffe, locktime=0):
            cases.append(dict(name=name, kind="wsh", script=script, wit=wit, seq=seq, lt=locktime))

        def tap(name, leaf, wit, siblings=(), seq=0xfffffffe, locktime=0, n=1):
            cases.append(dict(name=name, kind="tap", leaf=leaf, wit=wit, siblings=siblings, seq=seq, lt=locktime, n=n))

        # ---- BOLT 3, anchor channels (P2WSH) ----
        a, b = ec(), ec()
        pks = sorted([a.get_pubkey().get_bytes(), b.get_pubkey().get_bytes()])
        funding = CScript([OP_2, pks[0], pks[1], OP_2, OP_CHECKMULTISIG])
        wsh("funding 2-of-2 (commitment / mutual close)", funding,
            lambda s: [b"", *[k.sign_ecdsa(s) + bytes([SIGHASH_ALL]) for k in sorted([a, b], key=lambda k: k.get_pubkey().get_bytes())]])
        rev, dly = ec(), ec()
        to_local = CScript([OP_IF, rev.get_pubkey().get_bytes(), OP_ELSE, DELAY, OP_CHECKSEQUENCEVERIFY, OP_DROP,
                            dly.get_pubkey().get_bytes(), OP_ENDIF, OP_CHECKSIG])
        wsh("to_local, delayed sweep", to_local, lambda s: [dly.sign_ecdsa(s) + bytes([SIGHASH_ALL]), b""], seq=DELAY)
        wsh("to_local, PENALTY (revocation)", to_local, lambda s: [rev.sign_ecdsa(s) + bytes([SIGHASH_ALL]), b"\x01"])
        rem = ec()
        to_remote = CScript([rem.get_pubkey().get_bytes(), OP_CHECKSIGVERIFY, OP_1, OP_CHECKSEQUENCEVERIFY])
        wsh("to_remote (anchors, 1 block CSV)", to_remote, lambda s: [rem.sign_ecdsa(s) + bytes([SIGHASH_ALL])], seq=1)
        fk = ec()
        anchor = CScript([fk.get_pubkey().get_bytes(), OP_CHECKSIG, OP_IFDUP, OP_NOTIF, OP_16, OP_CHECKSEQUENCEVERIFY, OP_ENDIF])
        wsh("anchor, owner (CPFP bump)", anchor, lambda s: [fk.sign_ecdsa(s) + bytes([SIGHASH_ALL])])
        wsh("anchor, anyone after 16 blocks", anchor, lambda s: [b""], seq=16)
        rk, lh, rh = ec(), ec(), ec()
        revh = ripemd160(hashlib.sha256(rk.get_pubkey().get_bytes()).digest())
        offered = CScript([OP_DUP, OP_HASH160, revh, OP_EQUAL, OP_IF, OP_CHECKSIG, OP_ELSE, rh.get_pubkey().get_bytes(),
                           OP_SWAP, OP_SIZE, 32, OP_EQUAL, OP_NOTIF, OP_DROP, OP_2, OP_SWAP, lh.get_pubkey().get_bytes(), OP_2,
                           OP_CHECKMULTISIG, OP_ELSE, OP_HASH160, ripemd160(ph), OP_EQUALVERIFY, OP_CHECKSIG, OP_ENDIF,
                           OP_1, OP_CHECKSEQUENCEVERIFY, OP_DROP, OP_ENDIF])
        wsh("offered HTLC, PENALTY (revocation)", offered,
            lambda s: [rk.sign_ecdsa(s) + bytes([SIGHASH_ALL]), rk.get_pubkey().get_bytes()])
        wsh("offered HTLC, timeout (2-of-2, HTLC-timeout tx)", offered,
            lambda s: [b"", rh.sign_ecdsa(s) + bytes([SIGHASH_ALL]), lh.sign_ecdsa(s) + bytes([SIGHASH_ALL]), b""], seq=1)
        wsh("offered HTLC, remote claims with preimage", offered,
            lambda s: [rh.sign_ecdsa(s) + bytes([SIGHASH_ALL]), preimage], seq=1)
        received = CScript([OP_DUP, OP_HASH160, revh, OP_EQUAL, OP_IF, OP_CHECKSIG, OP_ELSE, rh.get_pubkey().get_bytes(),
                            OP_SWAP, OP_SIZE, 32, OP_EQUAL, OP_IF, OP_HASH160, ripemd160(ph), OP_EQUALVERIFY, OP_2, OP_SWAP,
                            lh.get_pubkey().get_bytes(), OP_2, OP_CHECKMULTISIG, OP_ELSE, OP_DROP, CLTV,
                            OP_CHECKLOCKTIMEVERIFY, OP_DROP, OP_CHECKSIG, OP_ENDIF, OP_1, OP_CHECKSEQUENCEVERIFY, OP_DROP,
                            OP_ENDIF])
        wsh("received HTLC, success (2-of-2 + preimage, HTLC-success tx)", received,
            lambda s: [b"", rh.sign_ecdsa(s) + bytes([SIGHASH_ALL]), lh.sign_ecdsa(s) + bytes([SIGHASH_ALL]), preimage], seq=1)
        wsh("received HTLC, remote timeout (CLTV)", received,
            lambda s: [rh.sign_ecdsa(s) + bytes([SIGHASH_ALL]), b""], seq=1, locktime=CLTV)
        wsh("received HTLC, PENALTY (revocation)", received,
            lambda s: [rk.sign_ecdsa(s) + bytes([SIGHASH_ALL]), rk.get_pubkey().get_bytes()])

        # ---- LND simple taproot channels (tapscript) ----
        dp, dx = xo(); rp, rx = xo(); remp, remx = xo(); lhp, lhx = xo(); rhp, rhx = xo()
        delay_leaf = CScript([dx, OP_CHECKSIG, DELAY, OP_CHECKSEQUENCEVERIFY, OP_DROP])
        revoke_leaf = CScript([dx, OP_DROP, rx, OP_CHECKSIG])
        tap("taproot to_local, delayed sweep", delay_leaf, [dp], siblings=[revoke_leaf], seq=DELAY)
        tap("taproot to_local, PENALTY (revocation leaf)", revoke_leaf, [rp], siblings=[delay_leaf])
        tap("taproot to_local, PENALTY x2 inputs (one tx)", revoke_leaf, [rp], siblings=[delay_leaf], n=2)
        tap("taproot to_remote", CScript([remx, OP_CHECKSIG, OP_1, OP_CHECKSEQUENCEVERIFY, OP_DROP]), [remp], seq=1)
        tap("taproot anchor, anyone after 16 blocks", CScript([OP_16, OP_CHECKSEQUENCEVERIFY]), [], seq=16)
        off_timeout = CScript([lhx, OP_CHECKSIGVERIFY, rhx, OP_CHECKSIG])
        off_success = CScript([OP_SIZE, 32, OP_EQUALVERIFY, OP_HASH160, ripemd160(ph), OP_EQUALVERIFY, rhx, OP_CHECKSIG,
                               OP_1, OP_CHECKSEQUENCEVERIFY, OP_DROP])
        tap("taproot offered HTLC, timeout (2 sigs)", off_timeout, [rhp, lhp], siblings=[off_success])
        tap("taproot offered HTLC, remote success (preimage)", off_success, [rhp, "preimage"], siblings=[off_timeout], seq=1)
        acc_timeout = CScript([rhx, OP_CHECKSIG, OP_1, OP_CHECKSEQUENCEVERIFY, OP_DROP, CLTV, OP_CHECKLOCKTIMEVERIFY, OP_DROP])
        acc_success = CScript([OP_SIZE, 32, OP_EQUALVERIFY, OP_HASH160, ripemd160(ph), OP_EQUALVERIFY, lhx,
                               OP_CHECKSIGVERIFY, rhx, OP_CHECKSIG])
        tap("taproot accepted HTLC, remote timeout (CLTV)", acc_timeout, [rhp], siblings=[acc_success], seq=1, locktime=CLTV)
        tap("taproot accepted HTLC, success (2 sigs + preimage)", acc_success, [rhp, lhp, "preimage"], siblings=[acc_timeout])

        # fund everything, then let the CSV delays mature
        for j, c in enumerate(cases):
            if j % 8 == 7:
                self.generate(self.wallet, 1)      # keep unconfirmed chains short
            if c["kind"] == "wsh":
                c["spk"] = script_to_p2wsh_script(c["script"])
            else:
                c["tr"] = taproot_construct(compute_xonly_pubkey(generate_privkey())[0],
                                            [("leaf", c["leaf"])] + [(f"s{i}", s) for i, s in enumerate(c["siblings"])])
                c["spk"] = c["tr"].scriptPubKey
            c["outs"] = [self.wallet.send_to(from_node=self.nodes[0], scriptPubKey=c["spk"], amount=FUNDING) for _ in range(c.get("n", 1))]
        self.generate(self.wallet, 30)
        assert self.nodes[0].getblockcount() > CLTV

        bad = []
        self.log.info("%-58s %-12s %-12s %-12s %-12s %s", "spend", "defaults", "+dropped", "+unproven", "+unkwit", "corepolicy")
        for c in cases:
            tx = CTransaction(); tx.version = 2; tx.nLockTime = c["lt"]
            tx.vin = [CTxIn(COutPoint(int(o["txid"], 16), o["sent_vout"]), nSequence=c["seq"]) for o in c["outs"]]
            tx.vout = [CTxOut(FUNDING * len(tx.vin) - 5_000, script_to_p2wsh_script(CScript([OP_TRUE])))]
            tx.wit.vtxinwit = [CTxInWitness() for _ in tx.vin]
            for i in range(len(tx.vin)):
                if c["kind"] == "wsh":
                    s = SegwitV0SignatureHash(c["script"], tx, i, SIGHASH_ALL, FUNDING)
                    tx.wit.vtxinwit[i].scriptWitness.stack = c["wit"](s) + [bytes(c["script"])]
                else:
                    tr = c["tr"]; info = tr.leaves["leaf"]
                    sh = TaprootSignatureHash(tx, [CTxOut(FUNDING, c["spk"])] * len(tx.vin), 0, i, scriptpath=True, leaf_script=c["leaf"], codeseparator_pos=0xffffffff)
                    stack = [preimage if w == "preimage" else sign_schnorr(w, sh) for w in c["wit"]]
                    control = bytes([info.version | tr.negflag]) + tr.internal_pubkey + info.merklebranch
                    tx.wit.vtxinwit[i].scriptWitness.stack = stack + [bytes(c["leaf"]), control]
            hx = tx.serialize().hex()
            res = [n.testmempoolaccept([hx])[0] for n in self.nodes]
            v = ["OK" if r["allowed"] else r["reject-reason"] for r in res]
            self.log.info("%-58s %-12s %-12s %-12s %-12s %s", c["name"], *v)
            want = KNOWN_AT_42.get(c["name"])
            bad.extend((c["name"], i, x) for i, x in enumerate(v) if x != (want[i] if want else "OK"))
        assert not bad, f"Lightning spends refused (spend, node, reason): {bad}"

        # ---- zero-fee commitment channels (LDK 0.2+): v3 parent paying 0 with one pay-to-anchor, v3 child pays both ----
        op_true = CScript([OP_TRUE]); true_spk = script_to_p2wsh_script(op_true)
        p2a = CScript([OP_1, bytes.fromhex("4e73")])
        for anchor_value in (0, 100, 240):
            v = []
            for n in self.nodes:
                ins = [self.wallet.send_to(from_node=self.nodes[0], scriptPubKey=true_spk, amount=FUNDING) for _ in range(2)]
                self.generate(self.wallet, 1, sync_fun=self.sync_blocks)  # mempools differ by design here
                parent = CTransaction(); parent.version = 3
                parent.vin = [CTxIn(COutPoint(int(ins[0]["txid"], 16), ins[0]["sent_vout"]))]
                parent.vout = [CTxOut(FUNDING - anchor_value, true_spk), CTxOut(anchor_value, p2a)]
                parent.wit.vtxinwit = [CTxInWitness()]; parent.wit.vtxinwit[0].scriptWitness.stack = [bytes(op_true)]
                child = CTransaction(); child.version = 3
                child.vin = [CTxIn(COutPoint(int(parent.txid_hex, 16), 1)), CTxIn(COutPoint(int(ins[1]["txid"], 16), ins[1]["sent_vout"]))]
                child.vout = [CTxOut(FUNDING + anchor_value - 5_000, true_spk)]
                child.wit.vtxinwit = [CTxInWitness(), CTxInWitness()]; child.wit.vtxinwit[1].scriptWitness.stack = [bytes(op_true)]
                try:
                    r = n.submitpackage([parent.serialize().hex(), child.serialize().hex()])
                    errs = [x.get("error") for x in r["tx-results"].values() if x.get("error")]
                    v.append("OK" if r["package_msg"] == "success" else (errs[0] if errs else r["package_msg"]))
                except Exception as e:
                    v.append(str(e)[:40])
            self.log.info("%-58s %-12s %-12s %-12s %-12s %s", f"zero-fee commitment package, {anchor_value}-sat anchor", *v)
            # Knots' -permitephemeral default takes zero-value anchors only; LDK nodes whose anchors carry trimmed
            # HTLC dust set -permitephemeral=anchor,send,dust (documented in the Lightning node notes). A 0-sat anchor
            # must relay everywhere.
            # 240 sat is the pay-to-anchor dust threshold: not dust, so it relays everywhere too.
            want = ["dust-nonzero"] * 4 + ["OK"] if 0 < anchor_value < 240 else ["OK"] * 5
            assert v == want, f"zero-fee commitment package ({anchor_value}-sat anchor): {v}, expected {want}"


if __name__ == "__main__":
    LnPolicyDefaultsTest(__file__).main()
