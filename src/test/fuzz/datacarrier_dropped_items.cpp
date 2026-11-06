// Copyright (c) 2026 The Bitcoin Knots SHA256 developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <coins.h>
#include <policy/policy.h>
#include <primitives/transaction.h>
#include <script/script.h>
#include <test/fuzz/FuzzedDataProvider.h>
#include <test/fuzz/fuzz.h>
#include <test/fuzz/util.h>
#include <test/util/random.h>

#include <cassert>
#include <numeric>
#include <vector>

// -datacarrierdroppeditems reads attacker-chosen scripts and stacks before any validation: it must not crash, must
// never count more than the spent stack holds, and must not depend on anything but its inputs.
FUZZ_TARGET(datacarrier_dropped_items)
{
    FuzzedDataProvider fdp(buffer.data(), buffer.size());
    const bool tapscript{fdp.ConsumeBool()};
    std::vector<std::vector<unsigned char>> items;
    const size_t n{fdp.ConsumeIntegralInRange<size_t>(0, 32)};
    for (size_t i{0}; i < n && fdp.remaining_bytes(); ++i) {
        items.push_back(ConsumeRandomLengthByteVector(fdp, 600));
    }
    const CScript script{ConsumeScript(fdp)};
    const size_t total{std::accumulate(items.begin(), items.end(), size_t{0}, [](size_t a, const auto& v) { return a + v.size(); })};
    const size_t dropped{DroppedStackItemBytes(script, items, tapscript)};
    assert(dropped <= total);
    assert(dropped == DroppedStackItemBytes(script, items, tapscript));
}

// The per-transaction data accounting over attacker-chosen transactions and spent coins, with every option toggled:
// no crash, extra weight never negative, and the spent-script exemption only ever lowers the fake-output count.
// no crash, extra weight never negative, and the spent-script exemption only ever lowers the fake-output count.
FUZZ_TARGET(datacarrier_policy)
{
    SeedRandomStateForTest(SeedRand::ZEROS);  // the coins cache salts its hasher
    FuzzedDataProvider fdp(buffer.data(), buffer.size());
    const auto mtx{ConsumeDeserializable<CMutableTransaction>(fdp, TX_WITH_WITNESS)};
    if (!mtx) return;
    const CTransaction tx{*mtx};
    CCoinsViewCache coins{&CoinsViewEmpty::Get()};
    for (const CTxIn& txin : tx.vin) {
        coins.AddCoin(txin.prevout, Coin{CTxOut{ConsumeMoney(fdp), ConsumeScript(fdp)}, 1, false}, /*possible_overwrite=*/true);
    }
    const bool saved[]{g_datacarrier_dropped_items, g_fake_output_text, g_reject_fake_outputs, g_datacarrier_dust_runs};
    g_datacarrier_dropped_items = fdp.ConsumeBool();
    g_fake_output_text = fdp.ConsumeBool();
    g_reject_fake_outputs = fdp.ConsumeBool();
    g_datacarrier_dust_runs = fdp.ConsumeBool();
    const auto with_view{DataOutputBytes(tx, &coins)};
    const auto without_view{DataOutputBytes(tx, nullptr)};
    assert(with_view.size() == tx.vout.size() && without_view.size() == tx.vout.size());
    for (size_t i{0}; i < tx.vout.size(); ++i) assert(with_view[i] <= without_view[i]);
    (void)DatacarrierBytes(tx, coins, with_view);
    const unsigned int weight_per_data_byte{fdp.ConsumeIntegralInRange<unsigned int>(0, 4000)};
    assert(CalculateExtraTxWeight(tx, coins, weight_per_data_byte, with_view) >= 0);
    g_datacarrier_dropped_items = saved[0];
    g_fake_output_text = saved[1];
    g_reject_fake_outputs = saved[2];
    g_datacarrier_dust_runs = saved[3];
}
