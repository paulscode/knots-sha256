Bitcoin Knots SHA256 32.1.knots-sha256.20261113rc1 Release Notes
====================================================================

**This is a release candidate.** Please test it and report problems before the final release.

Bitcoin Knots SHA256 version 32.1.knots-sha256.20261113rc1 is now available from:

  <https://github.com/paulscode/knots-sha256/releases/tag/v32.1.knots-sha256.20261113rc1>

Please report problems at <https://github.com/paulscode/knots-sha256/issues>.

This release is based on Bitcoin Core 32.1
(<https://bitcoincore.org/en/releases/32.1/>) with the Bitcoin Knots patch series
inherited from Bitcoin Knots 29.3.knots20260507 and maintained for the SHA256 (Bitcoin)
network. Bitcoin Core 32.0 was tagged but never released, so 32.1 is the first release
of Bitcoin Core 32; its release notes cover the whole 32 series. Coming from Knots 29.x
means skipping three Bitcoin Core major versions, so the Bitcoin Core 30.0 and 31.0
release notes are worth a read too: <https://bitcoincore.org/en/releases/30.0/> and
<https://bitcoincore.org/en/releases/31.0/>.

Consensus is identical to Bitcoin Core: this node accepts every block Bitcoin Core
accepts. It does not include BIP110 / RDTS or the BLAKE2b proof-of-work change, and it
follows the same chain as Bitcoin Core. What differs is policy, meaning what the node
relays and what it mines, which follows Bitcoin Knots' stricter defaults (tables
below). Every default has a one-flag override, and `-corepolicy=1` restores Bitcoin
Core's relay and mining policy in one step.

The node identifies itself to peers as `/Satoshi:32.1.0/KnotsSHA256:20261113rc1/`.

How to Upgrade
==============

If you are running an older version, shut it down. Wait until it has completely shut
down (which might take a few minutes in some cases), then run the installer (on
Windows) or just copy over `/Applications/Bitcoin-Qt` (on macOS) or `bin/` and
`libexec/` (on Linux).

**From 31.2.knots-sha256.20261031 or 31.1.knots-sha256.20261018:** nothing to migrate,
and no option is gone. Several policy defaults change (see "Policy defaults that change
in this release"). If your `bitcoin.conf` sets one of them, your setting stays in force.
In particular, a `datacarriercost=1` line keeps the old data cost of 1; remove it to get
the new default of 2. The Umbrel and StartOS packages raise a stored 1 to 2 once when
they update; set 1 again afterwards if you want it, and it stays.

If you are coming from 31.1 and did not yet do the `getprioritisedtransactions` check
from the 31.2 notes, do it once: any entry you did not create with
`prioritisetransaction` is a leftover of a 31.1 bug.

### Which Knots release are you upgrading from?

Check with `bitcoind -version` (or Help, About in the GUI). Two different releases
are called 29.3, and only one of them is pre-RDTS.

- **29.3.knots20260507 or earlier:** your data directory works as it is. Read the
  rest of this section for options and wallets.
- **A release ending in `.knots20260508`** (29.3.knots20260508, 29.4, 29.4.1,
  29.4.2, and later 29.x releases with that ending): these enforce BIP110 (RDTS),
  and 29.4.1 and 29.4.2 also use BLAKE2b.
  - From 29.4.1 or 29.4.2 (BLAKE2b), or any later release that uses BLAKE2b: start
    with a **fresh data directory** and copy your wallets across. Their data
    directory holds BLAKE2b blocks, which this release cannot load.
  - From 29.4, or if you ever ran `invalidateblock` to leave the Bitcoin chain: the
    data directory records Bitcoin's block 961,632 as invalid. This release checks for
    that when it starts and, if it finds it, stops with a message saying so. Start it
    once with `-reindex` (not `-reindex-chainstate`, which keeps that record), or use
    a fresh data directory. A pruned node downloads the whole chain again either way.
  - From 29.3.knots20260508 without that record: nothing to do. The node moves back
    to the Bitcoin chain by itself (the BIP110 branch it followed is 8 blocks long).
  - Wallet transactions made on the RDTS or BLAKE2b chain after the split (block
    961,632, 2026-08-08) are not on the Bitcoin chain. They will show as unconfirmed
    and the wallet will try to rebroadcast them; `abandontransaction` frees their
    inputs.

### Options that are gone (coming from Knots 29.x)

These options no longer exist. **In `bitcoin.conf` or `bitcoin_rw.conf` they are
ignored without any effect** (debug.log says "Ignoring unknown configuration value");
on the command line they stop the node from starting. Either way, the setting no
longer does anything, so check what you relied on:

| option | what changed |
|---|---|
| `-consensusrules` | BIP110 / RDTS setting; this release has no such rules |
| `-blockprioritysize` | the cluster mempool block builder (Bitcoin Core 31 and later) has no priority area |
| `-maxorphantx` | orphans are limited per peer since Bitcoin Core 30; the option was removed in 31 |
| `-paytxfee` | deprecated in Bitcoin Core 30, removed in 31 (with `settxfee` and Knots' `setfeerate`). Your wallet now estimates fees (default target 144 blocks) unless you pass `fee_rate` or set `-fallbackfee` |
| `-upnp` | not yet available in this series (see below); `-natpmp` works |
| `-walletimplicitsegwit` | not yet available in this series (see below) |
| `-dblogsize`, `-flushwallet`, `-privdb`, `-swapbdbendian` | legacy wallet options, removed with the legacy wallet in Bitcoin Core 30 |

The `bitcoin-wallet` tool no longer has `-descriptors`, `-legacy`, `-format` or
`-withinternalbdb`.

**Tor users:** the network name `tor` is no longer accepted; it is `onion`. Change
`onlynet=tor` to `onlynet=onion` and `proxy=<addr>=tor` to `proxy=<addr>=onion`.
Unlike the options above, these **stop the node from starting**, also from
`bitcoin.conf`.

`-checkpoints`, `-limitancestorsize` and `-limitdescendantsize` are still accepted
but only print a warning; they no longer have any effect.

### Wallets

**Legacy (BDB) wallets must be migrated.** Bitcoin Core 30 removed the legacy wallet
type, so a wallet created as a legacy wallet by Knots 29.x opens only after
`migratewallet`. Back up the wallet file before migrating. Descriptor wallets need
nothing.

These wallet RPCs from Knots 29.3 are gone: `importaddress`, `importprivkey`,
`importpubkey`, `importmulti`, `importwallet`, `dumpprivkey`, `dumpwallet`,
`dumpmasterprivkey`, `sethdseed`, `upgradewallet`, `newkeypool`,
`addmultisigaddress`, `getunconfirmedbalance`, `settxfee` and `setfeerate`. Use
`importdescriptors` instead of the import calls (for a watch-only address:
`importdescriptors '[{"desc":"addr(<address>)#<checksum>","timestamp":"now"}]'`,
with the checksum from `getdescriptorinfo`), and `listdescriptors true` to see
private keys. `getbalance` follows Bitcoin Core (no watch-only balance; see the
Core 30.0 and 31.0 notes).

### Coming from Bitcoin Core

From Bitcoin Core 30 or later: nothing to migrate. From an older Core, the option and
wallet notes above apply too. Expect the policy differences listed below;
`-corepolicy=1` gives you Bitcoin Core's relay and mining policy.

Compatibility
=============

Built for the same platforms as Bitcoin Core 32.1 (Linux kernel 3.17, macOS 14 and
Windows 10 version 1903, or newer). This release has been tested by this
project on Linux x86_64. GUI builds require Qt 6.

Notable changes
===============

### Changes in this release (since 31.2.knots-sha256.20261031)

**Bitcoin Core 32.1.** All of Bitcoin Core's 32 changes are included; see its release
notes. Among them: transaction relay is rate-limited through one global backlog
(`-txsendrate`), and `-maxconnections` defaults to 200, with the added slots used for
block-relay-only connections and at most half of the inbound slots relaying
transactions (`-inboundrelaypercent=50`).

**Security.** This release includes the fixes for the three vulnerabilities Bitcoin Core disclosed on 2026-11-10:
CVE-2025-62861 (a reorg could make TRUC sibling eviction corrupt the mempool, so that a mining node could not build
block templates until restarted), CVE-2025-62859 (a peer could stall block processing with a malleated compact block)
and CVE-2025-62860 (inbound Tor connections could receive `-whitelist` permissions). Our 31.x releases already
contained them too. With the default `-mempooltruc=accept` the first cannot occur at all, because TRUC sibling eviction
does not run.

#### Policy defaults that change in this release

| option | 31.2 | 32.1 | why | to restore the old behaviour |
|---|---|---|---|---|
| `-datacarriercost` | 1 | **2** | each data byte now counts as at least 2 virtual bytes (was 1), at admission and for mining order, eviction and fee bumping | `-datacarriercost=1` |
| `-acceptunknownwitness` | 1 | **0** | outputs to witness versions 2 to 16, or to witness v1 programs that are neither taproot nor a pay-to-anchor, have no use before a soft fork defines one, and carry data that no filter examines. They are refused as `scriptpubkey-unknown-witnessversion`; this includes sends from the built-in wallet to such addresses. After a future soft fork that defines one, payments to it relay only once an update ships or the option is set | `-acceptunknownwitness=1` or `-corepolicy=1` |
| `-datacarrierunprovenkeys` | 0 | **1** | multisig keys that no signature proves (beyond ten per script), and odd-sized pushes in key slots, count as 33 data bytes each against `-datacarriersize`. A seven-day survey of the Bitcoin chain found no genuine multisig spend that it refuses | `-datacarrierunprovenkeys=0` |
| `-datacarrierdroppeditems` | (new) | **1** | witness items that a script drops without using them count as data | `-datacarrierdroppeditems=0` |
| `-fakeoutputtext` | (new) | **1** | an output whose hash or key is all printable text counts as data | `-fakeoutputtext=0` |
| `-maxconnections` | 125 | **200** | Bitcoin Core 32's default (see above) | `-maxconnections=125 -inboundrelaypercent=100` |
| `-dbcache` | RAM-adaptive (Knots) | **Bitcoin Core's**: 1 GiB with 4 GiB of RAM or more (64-bit builds), else 450 MiB | performance only | `-dbcache=<MiB>` |

`-corepolicy=1` resets the first five to Bitcoin Core's behaviour.

#### New spam filters (from Bitcoin Knots and an outside review)

All on by default and refused as `txn-datacarrier-nonstandard` once the data passes
`-datacarriersize`; each is switched off by its own option or by `-corepolicy=1`:

- **`-rejectfakeoutputs`** (knots#389, default 1): outputs whose hash or key is data
  (text, or runs of one repeated byte) count as data carrier bytes. Its dust-run rule
  sits behind `-datacarrierdustruns` (default 0), because a Lightning commitment with
  three or more equal in-flight HTLCs has the same layout. During the soak this caught
  a payment burned to a "key hash" spelling out a web address.
- **`-datacarrierdroppeditems`** and **`-fakeoutputtext`** (see the table above).
- **Token messages** (knots#489): JSON and Omni token messages are refused under
  `-rejecttokens` (`tokens-json`, `tokens-omni`).

LND's taproot revocation leaf (knots#487) now relays within `-datacarriersize`. At our
42 bytes one such input per transaction relays; a justice transaction sweeping two
revoked commitments at once is refused (`-datacarriersize=83` relays two).

#### Miners

- A data-carrying transaction near the end of a template must fit with its data cost,
  as in 31.x and Bitcoin Knots (Bitcoin Core 32 fits by real weight). The block's real
  weight is still what is capped.
- IPC mining clients cannot override `-blockmaxsize`, `-blockmaxweight` or
  `-blockmintxfee` per request (Bitcoin Core 32's IPC schema); RPC `getblocktemplate`
  still can. Out-of-range per-request weight and reserved values now return an error
  instead of being clamped (Bitcoin Core 32); a per-request `blockmaxsize` is still
  clamped to the valid range.

#### Wallet

- With the data cost of 2, a transaction with an OP_RETURN output needs 1 sat per
  *policy* vbyte (`vsize_adjusted` in the mempool RPCs), which the built-in wallet does
  not add: pay a little above the minimum, or run with `-datacarriercost=1`.

#### Network

- `-v2onlyclearnet` (knots#454) now also disconnects inbound v1 (unencrypted) peers on
  IPv4/IPv6 (local and private addresses are exempt), and can be used with `-listen`.
  In 31.2 it only stopped outbound v1 connections. Without a `-bind=...=onion`
  listener the node assumes that inbound connections on its first `-bind` came
  through Tor; under `-v2onlyclearnet` it now checks their source address, so a
  clearnet v1 peer cannot pass as an onion one.

#### GUI

- Warnings (such as an expiring release or unknown new rules) show on every tab
  instead of only on the overview (knots#301).
- The RPC console stays on its wallet (knots#344); dates follow the locale (knots#336).

#### Fixes from Bitcoin Knots

- `dumptxoutset` takes its type from `bitcoin-cli`, and a rollback with a format but no
  type works (knots#472); positional and named RPC options mix correctly (knots#471).
- A Tor the node started is stopped, and not waited on, at shutdown (knots#462, #464).
- A wallet descriptor range can no longer overflow (knots#458).
- After a failed seek or a short read or write, block and undo files no longer keep a
  stale file position (knots#491), and preallocating space in a block file no longer
  lets buffered data land in the wrong place. 32-bit builds seek correctly in files
  larger than 2 GiB.
- `bitcoind -help` and `-version` no longer touch the data directory, and
  `contrib/devtools/gen-bitcoin-conf.sh` no longer uses the default data directory.
- The deprecated `vsize` field of the mempool RPCs is the policy size, including the
  data cost (use `vsize_bip141` for BIP 141 vsize, `vsize_adjusted` for the policy size).

Bitcoin Core 32.1 already contains several fixes that Bitcoin Knots carries as patches
(a `getblockfrompeer` crash, a reindex deadlock at startup, `dumptxoutset` rollback
without invalidating blocks); they are in this release through Bitcoin Core.

#### Robustness

- The data-carrier analyses only read scripts that the spent output commits to, so a
  peer can no longer make them do costly work on invalid transactions.
- `-datacarriercost` outside 0 to 1000 is a startup error.
- Prune locks no longer wrap on a reorg to genesis.
- `-spkreuse=conflict`'s chained rejection can no longer be ignored into an
  inconsistent mempool, and it also holds between the transactions of a package
  (`txn-spk-reused-package`). A package's cluster size limit can no longer be ignored in
  `testmempoolaccept`.
- `-corepolicy` now gives Bitcoin Core's own legacy-sigop limit (2500) instead of none.

#### Lightning operators

- Every BOLT 3 and LND simple-taproot spend relays at the defaults (tested), except an
  LND justice transaction that sweeps two revocation leaves at once (see knots#487
  above). LDK zero-fee commitment channels whose anchor carries sub-dust value need
  `-permitephemeral=anchor,dust` (`send` is not needed, and would also admit
  non-anchor dust).

### Policy defaults that differ from Bitcoin Core

Options that both Bitcoin Core and this release have, with different defaults.
`-corepolicy=1` sets all of these to Bitcoin Core's values:

| option | Bitcoin Core 32.1 | this release | what it does |
|---|---|---|---|
| `-datacarriersize` | 100000 | 42 | largest data payload relayed or mined (bytes) |
| `-minrelaytxfee` | 0.000001 | 0.00001 | lowest fee rate relayed (1 sat/vB) |
| `-incrementalrelayfee` | 0.000001 | 0.00001 | fee bump needed to replace or evict (1 sat/vB) |
| `-blockmintxfee` | 0.00000001 | 0.00001 | lowest fee rate put in a block template |
| `-blockmaxweight` | 4000000 | 1200000 | block template size (weight) |
| `-permitbaremultisig` | 1 | 0 | relay bare multisig outputs |
| `-blockreconstructionextratxn` | 100 | 32768 | extra transactions kept for compact block reconstruction |

`-acceptnonstdtxn` (default 0 in both) can also be set on mainnet here; Bitcoin Core
allows it only on test networks.

Options this release adds on top of Bitcoin Core, with their defaults. Those marked
with * are set to Bitcoin Core's behaviour by `-corepolicy=1`; the others already
behave like Bitcoin Core by default, or have no Core equivalent:

| option | default | what it does |
|---|---|---|
| `-corepolicy` | 0 | set to 1 to use Bitcoin Core's policy defaults |
| `-datacarriermultiple` * | 0 | 0: at most one OP_RETURN output per transaction (as in Knots 29.3); 1: several, within `-datacarriersize` |
| `-datacarriercost` * | 2 | virtual bytes charged per byte of data, at admission and for mining, eviction and fee bumping (`-corepolicy=1` sets 0.25, Bitcoin Core's witness discount) |
| `-datacarrierfullcount` * | 1 | apply `-datacarriersize` to every data-carrying method, not only OP_RETURN |
| `-acceptnonstddatacarrier` * | 0 | relay data hidden in non-OP_RETURN scripts |
| `-rejectparasites` * | 1 | reject CAT-21 transactions (inscription envelopes are refused by `-acceptnonstddatacarrier=0`) |
| `-rejecttokens` * | 1 | reject known token protocols (Runes, OLGA stamps, Counterparty, JSON and Omni token messages) |
| `-rejectbpub` * | 1 | reject files hidden in multisig keys (BPUB) |
| `-rejectdeadbranches` * | 1 | count data in script branches that can never run |
| `-rejectfakeoutputs` * | 1 | count output hashes and keys that are data as data |
| `-datacarrierdustruns` | 0 | with `-rejectfakeoutputs`, also count runs of equal dust outputs as data |
| `-datacarrierunprovenkeys` * | 1 | count multisig keys no signature proves as data |
| `-datacarrierdroppeditems` * | 1 | count witness items a script drops unused as data |
| `-fakeoutputtext` * | 1 | count output hashes and keys that are all printable text as data |
| `-acceptunknownwitness` * | 0 | relay transactions paying to future witness versions |
| `-permitbarepubkey` * | 0 | relay bare pubkey (P2PK) outputs |
| `-permitbaredatacarrier` * | 0 | relay transactions whose only outputs are OP_RETURN |
| `-permitbareanchor` | 1 | relay anchor-only transactions |
| `-permitephemeral` * | anchor,-send,-dust | which ephemeral outputs are relayed |
| `-maxscriptsize` * | 1650 | largest script (including witness) relayed (bytes) |
| `-maxtxlegacysigops` * | 2500 | legacy signature-operation limit per transaction |
| `-bytespersigopstrict` * | 20 | strict bytes-per-sigop accounting |
| `-blockmaxsize` * | 300000 | block template size (serialized bytes) |
| `-subdustfeepenalty` * | 1 | dust outputs reduce a transaction's effective fee |
| `-mempoolreplacement` | fee,-optin | replacement policy: full RBF, as in Bitcoin Core; `fee,optin` honours opt-in signalling instead |
| `-mempoolfullrbf` | 1 | older alias of `-mempoolreplacement` |
| `-mempooltruc` * | accept | `accept`: v3 (TRUC) transactions are relayed like any other, but TRUC's topology limits are not enforced (Bitcoin Core enforces them; `enforce` matches Core, `reject` refuses v3) |
| `-dustdynamic` | off | dynamic dust threshold |
| `-minrelaycoinblocks` | 0 | coin-age relay floor |
| `-minrelaymaturity` | 0 | input-maturity relay floor |
| `-spkreuse` * | allow | relay transactions that reuse addresses |
| `-blockreconstructionextratxnsize` * | 10 | memory cap for the extra-transaction pool (MB) |
| `-softwareexpiry` | 1857151480 | see "Software expiry" below |

Other defaults that differ from Bitcoin Core (not changed by `-corepolicy`):

| option | Bitcoin Core 32.1 | this release |
|---|---|---|
| `-dbbatchsize` | 33554432 | 67108864 |
| `-peerbloomfilters` | 0 | localhost only |
| `-txconfirmtarget` | 6 | 144 (wallet fee target, blocks) |

Other options carried from Bitcoin Knots (no policy effect): `-confrw`, `-lowmem`,
`-pruneduringinit`, `-statsenable`, `-statsmaxmemorytarget`, `-torexecute`,
`-uaappend`, `-uaspoof`, `-v2onlyclearnet`, `-feefilter`, `-dbfilesize`,
`-rpcauthfile`, `-signetblocktime`, `-guisettingsdir`, and the `-zmqpub*wallettx`
notifications. `-blockfilterindex` also accepts `v0`, a filter type from Bitcoin
Knots, besides Bitcoin Core's `basic`.

### Changes compared with Bitcoin Knots 29.3.knots20260507

- `-datacarriersize` defaults to 42 bytes (40 bytes of data), Knots' long-standing
  default before 29.2.
- `-datacarriercost` defaults to 2 (Knots: 1).
- `-acceptunknownwitness` defaults to 0 (Knots: 1).
- `-datacarrierunprovenkeys`, `-datacarrierdroppeditems` and `-fakeoutputtext` are
  options of this release, on by default.
- One OP_RETURN output per transaction stays the default, as in 29.3, now as an
  option: `-datacarriermultiple=1` allows several within `-datacarriersize`.
- `-rejecttokens` is on by default.
- `-dbcache` and `-maxconnections` follow Bitcoin Core 32.
- Checkpoints are gone, as in Bitcoin Core 30 and later.
- The block priority area (`-blockprioritysize`) is gone; the cluster mempool block
  builder replaced the code it relied on.
- The legacy (BDB) wallet and the RPCs listed under "Wallets" are gone.
- GUI builds require Qt 6, as in Bitcoin Core 31 and later.
- An expired node no longer rejects block headers: expiry never changes which blocks
  the node accepts (see "Software expiry").
- Fixed: a node that stopped uncleanly (power cut, crash) within about an hour after
  finishing its initial sync could fail to start again without
  `-reindex-chainstate`. The chainstate sync after initial block download now writes
  the block index first.
- Fixed: "Reset options" in the GUI could delete `bitcoin_rw.conf` without the
  backup it promises. It now keeps the file and tells you when the backup cannot be
  made, and settings are only ever replaced by a completely written copy.
- New: the node refuses to start on a data directory that records Bitcoin's block
  at the BIP110 split (961,632) as invalid, as Bitcoin Knots 29.4 or `invalidateblock`
  leave it, and says how to recover (see "How to Upgrade"). This is a startup check:
  it does not change which blocks the node accepts.
- Fixed: a negative `-softwareexpiry` showed an "expired" warning; like 0, it turns
  expiry off.
- `libbitcoinconsensus` on Linux exports only its API functions.

Not yet in this series: UPnP (`-upnp`; NAT-PMP via `-natpmp` works), the GUI dialog
for settings kept in `bitcoin_rw.conf`, `importaddress` for descriptor wallets (use
`importdescriptors`, see "Wallets"), and `-walletimplicitsegwit`.

### Binaries

- Linux (x86_64, aarch64, riscv64), Windows (x86_64) and macOS (x86_64, arm64), built
  reproducibly with Guix, using the same toolchain and macOS SDK as Bitcoin Core's
  own builds. 32-bit ARM (`arm-linux-gnueabihf`) is built but not published until its
  tests can run on that architecture.
- The release also includes `libbitcoinconsensus`, which Bitcoin Core no longer
  ships.
- **Nothing is code-signed by Apple or Microsoft.** Every file is covered by the
  signed `SHA256SUMS` instead (see "Verifying this release"); verify first.
  - **macOS:** remove the download quarantine and sign the files yourself (ad hoc, no
    Apple account needed). On Apple Silicon macOS refuses to run unsigned programs
    at all, so this step is required there:
    `xattr -dr com.apple.quarantine Bitcoin-Qt.app && codesign --force --deep -s - Bitcoin-Qt.app`
    For the command-line tarball, run the same two commands on the extracted folder
    (`xattr -dr com.apple.quarantine <folder>` and
    `codesign --force -s - <folder>/bin/* <folder>/libexec/* <folder>/lib/*.dylib`).
  - **Windows:** SmartScreen warns about the unsigned installer; choose "More info",
    then "Run anyway".
- The Windows installer's default folder is Bitcoin Core's (`Program Files\Bitcoin`);
  choose another folder to keep both. On macOS the app has Bitcoin Core's name and
  bundle identifier (`Bitcoin-Qt.app`), so copying it to Applications replaces
  Bitcoin Core's app. Data directories are not touched either way.

### Software expiry

This release has a built-in expiry at 2028-11-06 19:24 UTC (POSIX time 1857151480),
with a warning from 2028-10-09.

- At the expiry time a running node shows an error and its `getblocktemplate` RPC
  stops working, but the node keeps running and validating.
- After that it **will not start again**, so an unattended node fails to come back
  after its next restart. Upgrade before then.
- To override, set `-softwareexpiry=0` (no expiry) or a later POSIX timestamp. The
  value is a number of seconds, not a date: `-softwareexpiry=2029-01-01` is read as
  the number 2029 and makes the node refuse to start.
- Expiry never changes which blocks the node accepts.

### Consensus

Consensus-identical to Bitcoin Core 32.1. Accepted consensus divergences: none.

Verifying this release
======================

`SHA256SUMS` is signed by FF76 D484 3EBD 7FA0 6D92  DC0C B8AB 7B8E 7E28 0E1A (Paul Lamb).
Public key: <https://paulscode.com/.well-known/paulscode.asc>

    gpg --verify SHA256SUMS.asc SHA256SUMS && sha256sum --ignore-missing -c SHA256SUMS

The source tarball is the one the binaries were built from, made by the reproducible
Guix build (as Bitcoin Core publishes it). `guix-noncodesigned.SHA256SUMS` lists the
hash of every file that build produced; building the tagged commit with
`contrib/guix/guix-build` should give you the same hashes.

Credits
=======

Bitcoin Knots SHA256 is built on the work of the Bitcoin Core developers and of
Luke Dashjr and the Bitcoin Knots contributors, whose patches are carried here with
their original authorship.
