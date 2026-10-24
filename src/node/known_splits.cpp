// Copyright (c) 2026 The Bitcoin Knots developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <node/known_splits.h>

#include <chain.h>
#include <node/blockstorage.h>
#include <tinyformat.h>
#include <util/chaintype.h>

namespace node {
namespace {
const KnownSplit MAINNET_SPLITS[]{
    // Bitcoin Knots 29.3.knots20260508 and 29.4 required a version-bit signal
    // from this height; Bitcoin's block here does not signal. The other branch's
    // block at this height is 0000000000000000000169eb6f811ddbd0daf343af7b62180cdb13e7c78dbc16.
    {961632, uint256{"00000000000000000000d1e01392faa65ceeaed307f0a3159144b84146ff24ba"}},
};
} // namespace

std::span<const KnownSplit> KnownSplits(ChainType chain)
{
    if (chain == ChainType::MAIN) return MAINNET_SPLITS;
    return {};
}

std::optional<bilingual_str> CheckKnownSplits(const BlockManager& blockman, std::span<const KnownSplit> splits)
{
    AssertLockHeld(::cs_main);
    for (const KnownSplit& split : splits) {
        const CBlockIndex* bitcoin_block{blockman.LookupBlockIndex(split.bitcoin_block)};
        if (!bitcoin_block || !(bitcoin_block->nStatus & (BLOCK_FAILED_VALID | BLOCK_FAILED_CHILD))) continue;
        return strprintf(_("This data directory was used by software that left the Bitcoin chain at block %d. It marked "
                           "Bitcoin's block there (%s) invalid, and with that mark in place this node cannot follow "
                           "the Bitcoin chain.\n\n"
                           "Restart once with -reindex (not -reindex-chainstate) to rebuild the block index from the "
                           "block files, or use a fresh data directory. A pruned node downloads the chain again. "
                           "Wallets are not affected."),
                         split.height, split.bitcoin_block.ToString());
    }
    return std::nullopt;
}
} // namespace node
