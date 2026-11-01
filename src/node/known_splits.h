// Copyright (c) 2026 The Bitcoin Knots developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef BITCOIN_NODE_KNOWN_SPLITS_H
#define BITCOIN_NODE_KNOWN_SPLITS_H

#include <kernel/cs_main.h>
#include <sync.h>
#include <uint256.h>
#include <util/translation.h>

#include <optional>
#include <span>

enum class ChainType;

namespace node {
class BlockManager;

/** A chain split that other software followed and Bitcoin did not. */
struct KnownSplit {
    int height;            //!< first height at which the two branches differ
    uint256 bitcoin_block; //!< Bitcoin's block at that height
};

/** The known splits of a chain. Mainnet: block 961632, 2026-08-08. */
std::span<const KnownSplit> KnownSplits(ChainType chain);

/**
 * Startup check of the block index. It is not a validation rule: no block is
 * validated differently because of it.
 *
 * Software that enforces the other branch's rules records Bitcoin's block at
 * the split as invalid in the block index (Bitcoin Knots 29.4 does so at
 * startup, `invalidateblock` does so by hand). The mark persists, so a node
 * started on that data directory would silently stay off the Bitcoin chain.
 * Returns the error to show when Bitcoin's block at a known split is in the
 * block index and marked invalid; std::nullopt otherwise. A data directory
 * that only followed the other branch, without that mark, needs nothing: the
 * node reorganizes to Bitcoin as it would for any chain with more work.
 */
std::optional<bilingual_str> CheckKnownSplits(const BlockManager& blockman, std::span<const KnownSplit> splits)
    EXCLUSIVE_LOCKS_REQUIRED(::cs_main);
} // namespace node

#endif // BITCOIN_NODE_KNOWN_SPLITS_H
