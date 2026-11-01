// Copyright (c) 2026 The Bitcoin Knots developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <chain.h>
#include <node/blockstorage.h>
#include <node/known_splits.h>
#include <test/util/setup_common.h>
#include <util/chaintype.h>
#include <validation.h>

#include <boost/test/unit_test.hpp>

using node::CheckKnownSplits;
using node::KnownSplit;
using node::KnownSplits;

BOOST_FIXTURE_TEST_SUITE(known_splits_tests, TestChain100Setup)

BOOST_AUTO_TEST_CASE(mainnet_table)
{
    const auto main{KnownSplits(ChainType::MAIN)};
    BOOST_REQUIRE_EQUAL(main.size(), 1U);
    BOOST_CHECK_EQUAL(main[0].height, 961632);
    BOOST_CHECK_EQUAL(main[0].bitcoin_block.ToString(), "00000000000000000000d1e01392faa65ceeaed307f0a3159144b84146ff24ba");
    for (const ChainType chain : {ChainType::TESTNET, ChainType::TESTNET4, ChainType::SIGNET, ChainType::REGTEST}) {
        BOOST_CHECK(KnownSplits(chain).empty());
    }
}

BOOST_AUTO_TEST_CASE(refuses_only_a_marked_bitcoin_block)
{
    LOCK(cs_main);
    auto& blockman{m_node.chainman->m_blockman};
    CBlockIndex* const block{m_node.chainman->ActiveChain()[50]};
    const KnownSplit at_50[]{{50, block->GetBlockHash()}};

    // Bitcoin's block is on our chain and not marked: nothing to do.
    BOOST_CHECK(!CheckKnownSplits(blockman, at_50));

    // Bitcoin's block is not in the block index (only the other branch was ever seen), or the split is above our
    // tip: nothing to do either, the node reorganizes to the most-work chain on its own.
    const KnownSplit unknown[]{{50, uint256::ONE}, {1000, uint256::ONE}};
    BOOST_CHECK(!CheckKnownSplits(blockman, unknown));

    // Marked invalid (as invalidateblock or Bitcoin Knots 29.4 leave it): refused, with the way out.
    const uint32_t status{block->nStatus};
    for (const uint32_t mark : {uint32_t{BLOCK_FAILED_VALID}, uint32_t{BLOCK_FAILED_CHILD}}) {
        block->nStatus = status | mark;
        const auto error{CheckKnownSplits(blockman, at_50)};
        BOOST_REQUIRE(error);
        BOOST_CHECK(error->original.find("block 50") != std::string::npos);
        BOOST_CHECK(error->original.find(block->GetBlockHash().ToString()) != std::string::npos);
        BOOST_CHECK(error->original.find("-reindex") != std::string::npos);
    }
    block->nStatus = status;
    BOOST_CHECK(!CheckKnownSplits(blockman, at_50));

    // A marked block that is not Bitcoin's block at a known split is ordinary invalid data: not refused.
    CBlockIndex* const other{m_node.chainman->ActiveChain()[60]};
    const uint32_t other_status{other->nStatus};
    other->nStatus |= BLOCK_FAILED_VALID;
    BOOST_CHECK(!CheckKnownSplits(blockman, at_50));
    other->nStatus = other_status;
}

BOOST_AUTO_TEST_SUITE_END()
