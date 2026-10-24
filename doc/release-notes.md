Bitcoin Knots SHA256 31.1.knots-sha256.20261018rc2 Release Notes
=================================================================

Bitcoin Knots SHA256 version 31.1.knots-sha256.20261018rc2 is now available from:

  <https://github.com/paulscode/knots-sha256/releases/tag/v31.1.knots-sha256.20261018rc2>

This is a **release candidate**. Please test it and report problems at
<https://github.com/paulscode/knots-sha256/issues> before the final release.

This release is based on Bitcoin Core 31.1
(<https://bitcoincore.org/en/releases/31.1/>) with the Bitcoin Knots patch series
inherited from Bitcoin Knots 29.3.knots20260507 and maintained for the SHA256 (Bitcoin)
network. Coming from Knots 29.x means skipping two Bitcoin Core major versions, so
the Bitcoin Core 30.0 and 31.0 release notes are worth a read too:
<https://bitcoincore.org/en/releases/30.0/> and <https://bitcoincore.org/en/releases/31.0/>.

Consensus is identical to Bitcoin Core: this node accepts every block Bitcoin Core
accepts. It does not include BIP110 / RDTS or the BLAKE2b proof-of-work change, and it
follows the same chain as Bitcoin Core. What differs is policy, meaning what the node
relays and what it mines, which follows Bitcoin Knots' stricter defaults (tables
below). Every default has a one-flag override, and `-corepolicy=1` restores Bitcoin
Core's relay and mining policy in one step.

The node identifies itself to peers as `/Satoshi:31.1.0/KnotsSHA256:20261018rc2/`.

How to Upgrade
==============

If you are running an older version, shut it down. Wait until it has completely shut
down (which might take a few minutes in some cases), then run the installer (on
Windows) or just copy over `/Applications/Bitcoin-Qt` (on macOS) or
`bitcoind`/`bitcoin-qt` (on Linux).

### Which Knots release are you upgrading from?

Check with `bitcoind -version` (or Help, About in the GUI). Two different releases
are called 29.3, and only one of them is pre-RDTS.

- **29.3.knots20260507 or earlier:** your data directory works as it is. Read the
  rest of this section for options and wallets.
- **A release ending in `.knots20260508`** (29.3.knots20260508, 29.4, 29.4.1,
  29.4.2): these enforce BIP110 (RDTS), and 29.4.1 and 29.4.2 also use BLAKE2b.
  - From 29.4.1 or 29.4.2 (BLAKE2b): start with a **fresh data directory** and copy
    your wallets across. Their data directory holds BLAKE2b blocks, which this
    release cannot load.
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

### Options that are gone

These options no longer exist. **In `bitcoin.conf` or `bitcoin_rw.conf` they are
ignored without any effect** (debug.log says "Ignoring unknown configuration value");
on the command line they stop the node from starting. Either way, the setting no
longer does anything, so check what you relied on:

| option | what changed |
|---|---|
| `-consensusrules` | BIP110 / RDTS setting; this release has no such rules |
| `-blockprioritysize` | Bitcoin Core 31's block builder has no priority area |
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
private keys. `getbalance` now follows Bitcoin Core 31 (no watch-only balance; see
the Core 30.0 and 31.0 notes).

### Coming from Bitcoin Core

From Bitcoin Core 30 or later: nothing to migrate. From an older Core, the option and
wallet notes above apply too. Expect the policy differences listed below;
`-corepolicy=1` gives you Bitcoin Core's relay and mining policy.

Compatibility
=============

Built for the same platforms as Bitcoin Core 31.1 (Linux kernel 3.17, macOS 14 and
Windows 10 version 1903, or newer). This release candidate has been tested by this
project on Linux x86_64. GUI builds require Qt 6.

Notable changes
===============

### Policy defaults that differ from Bitcoin Core

Options that both Bitcoin Core and this release have, with different defaults.
`-corepolicy=1` sets all of these to Bitcoin Core's values:

| option | Bitcoin Core 31.1 | this release | what it does |
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
| `-datacarriercost` * | 1 | virtual bytes charged per byte of data |
| `-datacarrierfullcount` * | 1 | apply `-datacarriersize` to every data-carrying method, not only OP_RETURN |
| `-acceptnonstddatacarrier` * | 0 | relay data hidden in non-OP_RETURN scripts |
| `-rejectparasites` * | 1 | reject inscription-style envelopes and similar overlay protocols |
| `-rejecttokens` * | 1 | reject known token protocols |
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
| `-acceptunknownwitness` | 1 | relay transactions paying to future witness versions (same behaviour as Bitcoin Core) |
| `-dustdynamic` | off | dynamic dust threshold |
| `-minrelaycoinblocks` | 0 | coin-age relay floor |
| `-minrelaymaturity` | 0 | input-maturity relay floor |
| `-spkreuse` * | allow | relay transactions that reuse addresses |
| `-blockreconstructionextratxnsize` * | 10 | memory cap for the extra-transaction pool (MB) |
| `-softwareexpiry` | 1857151480 | see "Software expiry" below |

Other defaults that differ from Bitcoin Core (not changed by `-corepolicy`):

| option | Bitcoin Core 31.1 | this release |
|---|---|---|
| `-dbcache` | 450 MiB, or 1 GiB with 4 GiB of RAM or more | a quarter of the RAM above 2 GiB, between 100 MiB and 2 GiB |
| `-dbbatchsize` | 33554432 | 67108864 |
| `-peerbloomfilters` | 0 | localhost only |
| `-txconfirmtarget` | 6 | 144 (wallet fee target, blocks) |

Other options carried from Bitcoin Knots (no policy effect): `-confrw`, `-lowmem`,
`-pruneduringinit`, `-statsenable`, `-statsmaxmemorytarget`, `-torexecute`,
`-uaappend`, `-uaspoof`, `-v2onlyclearnet`, `-feefilter`, `-dbfilesize`,
`-rpcauthfile`, `-signetblocktime`, `-guisettingsdir`, and the `-zmqpub*wallettx`
notifications. `-blockfilterindex` also accepts `v0`, a filter type from Bitcoin
Knots, besides Bitcoin Core's `basic`.

### Changes since 31.1.knots-sha256.20261018rc1

- New: the node refuses to start on a data directory that records Bitcoin's block
  at the BIP110 split (961,632) as invalid, as Bitcoin Knots 29.4 or `invalidateblock`
  leave it, and says how to recover (see "How to Upgrade"). Before, it started and
  silently stayed off the Bitcoin chain. This is a startup check: it does not change
  which blocks the node accepts.
- Fixed: a negative `-softwareexpiry` showed an "expired" warning; like 0, it turns
  expiry off.
- `libbitcoinconsensus` on Linux exports only its API functions (it also exported
  C++ standard library symbols).
- macOS: the signing command for the command-line tarball now covers `libexec` and
  `lib` (the rc1 notes left them out).
- The source tarball is now the Guix one the binaries were built from, and the Guix
  build's own hash list is published with it (see "Verifying this release").

### Changes compared with Bitcoin Knots 29.3.knots20260507

- `-datacarriersize` defaults to 42 bytes (40 bytes of data), Knots' long-standing
  default before 29.2.
- One OP_RETURN output per transaction stays the default, as in 29.3, now as an
  option: `-datacarriermultiple=1` allows several within `-datacarriersize`.
- `-rejecttokens` is on by default.
- Checkpoints are gone, as in Bitcoin Core 30 and later.
- The block priority area (`-blockprioritysize`) is gone; Bitcoin Core 31's cluster
  mempool block builder replaced the code it relied on.
- The legacy (BDB) wallet and the RPCs listed under "Wallets" are gone.
- GUI builds require Qt 6, as in Bitcoin Core 31.
- An expired node no longer rejects block headers: expiry never changes which blocks
  the node accepts (see "Software expiry").
- Fixed: a node that stopped uncleanly (power cut, crash) within about an hour after
  finishing its initial sync could fail to start again without
  `-reindex-chainstate`. The chainstate sync after initial block download now writes
  the block index first.
- Fixed: "Reset options" in the GUI could delete `bitcoin_rw.conf` without the
  backup it promises. It now keeps the file and tells you when the backup cannot be
  made, and settings are only ever replaced by a completely written copy.

Not yet in this series, planned for a later 31.x revision: UPnP (`-upnp`; NAT-PMP via
`-natpmp` works), the GUI dialog for settings kept in `bitcoin_rw.conf`,
`importaddress` for descriptor wallets (use `importdescriptors`, see "Wallets"), and
`-walletimplicitsegwit`.

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

Consensus-identical to Bitcoin Core 31.1. Accepted consensus divergences: none.

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
