// Copyright (c) 2020-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <key.h>
#include <key_io.h>
#include <test/util/setup_common.h>
#include <script/solver.h>
#include <wallet/scriptpubkeyman.h>
#include <wallet/wallet.h>
#include <wallet/test/util.h>

#include <boost/test/unit_test.hpp>

namespace wallet {
BOOST_FIXTURE_TEST_SUITE(scriptpubkeyman_tests, BasicTestingSetup)

BOOST_AUTO_TEST_CASE(DescriptorScriptPubKeyManTests)
{
    std::unique_ptr<interfaces::Chain>& chain = m_node.chain;

    CWallet keystore(chain.get(), "", CreateMockableWalletDatabase());
    auto key_scriptpath = GenerateRandomKey();

    // Verify that a SigningProvider for a pubkey is only returned if its corresponding private key is available
    auto key_internal = GenerateRandomKey();
    std::string desc_str = "tr(" + EncodeSecret(key_internal) + ",pk(" + HexStr(key_scriptpath.GetPubKey()) + "))";
    auto spk_man1 = CreateDescriptor(keystore, desc_str, true);
    BOOST_CHECK(spk_man1 != nullptr);
    auto signprov_keypath_spendable = spk_man1->GetSigningProvider(key_internal.GetPubKey());
    BOOST_CHECK(signprov_keypath_spendable != nullptr);

    desc_str = "tr(" + HexStr(XOnlyPubKey::NUMS_H) + ",pk(" + HexStr(key_scriptpath.GetPubKey()) + "))";
    auto spk_man2 = CreateDescriptor(keystore, desc_str, true);
    BOOST_CHECK(spk_man2 != nullptr);
    auto signprov_keypath_nums_h = spk_man2->GetSigningProvider(XOnlyPubKey::NUMS_H.GetEvenCorrespondingCPubKey());
    BOOST_CHECK(signprov_keypath_nums_h == nullptr);
}

BOOST_AUTO_TEST_CASE(Descriptor_IsKeyActive)
{
    CWallet wallet(m_node.chain.get(), "", CreateMockableWalletDatabase());
    {
        LOCK(wallet.cs_wallet);
        wallet.SetWalletFlag(WALLET_FLAG_DESCRIPTORS);
        wallet.m_keypool_size = 10;
        wallet.SetupDescriptorScriptPubKeyMans();
    }
    DescriptorScriptPubKeyMan* spkm = dynamic_cast<DescriptorScriptPubKeyMan*>(wallet.GetScriptPubKeyMan(OutputType::BECH32, /*internal=*/false));

    // Start off with 10 pre-generated keys, 1 script each
    auto scripts1 = spkm->GetScriptPubKeys();
    BOOST_CHECK_EQUAL(scripts1.size(), 10);

    // All keys are active
    for (const CScript& script : scripts1) {
        BOOST_CHECK(spkm->IsKeyActive(script));
    }

    // Requesting single key from spkm should not deactivate key
    auto dest1 = spkm->GetNewDestination(OutputType::BECH32);
    CScript script = GetScriptForDestination(dest1.value());
    BOOST_CHECK(spkm->IsKeyActive(script));

    // Key pool size did not change
    auto scripts2 = spkm->GetScriptPubKeys();
    BOOST_CHECK_EQUAL(scripts2.size(), 10);

    // Use key that is not the next key
    // (i.e. address gap in wallet recovery)
    {
        LOCK(spkm->cs_desc_man);
        WalletDescriptor descriptor = spkm->GetWalletDescriptor();
        FlatSigningProvider provider;
        std::vector<CScript> scripts3;
        descriptor.descriptor->ExpandFromCache(/*pos=*/5, descriptor.cache, scripts3, provider);

        BOOST_CHECK_EQUAL(scripts3.size(), 1);
        spkm->MarkUnusedAddresses(scripts3.front());
    }

    // Key pool size increased to replace used keys
    auto scripts4 = spkm->GetScriptPubKeys();
    BOOST_CHECK_EQUAL(scripts4.size(), 16);

    // All keys are still active
    for (const CScript& script : scripts4) {
        BOOST_CHECK(spkm->IsKeyActive(script));
    }

    // When user encrypts wallet for the first time,
    // all existing keys are removed from active keypool
    {
        LOCK(wallet.cs_wallet);
        // called by EncryptWallet()
        wallet.SetupDescriptorScriptPubKeyMans();
    }

    // This SPKM is not affected
    for (const CScript& script : scripts4) {
        BOOST_CHECK(spkm->IsKeyActive(script));
    }

    // ...but at the wallet level all the keys from that SPKM are deactivated
    int num_script_keys_not_found = 0;
    for (const CScript& script : scripts4) {
        if (!wallet.IsDestinationActive(WitnessV0ScriptHash(script))) {
            ++num_script_keys_not_found;
        }
    }
    BOOST_CHECK_EQUAL(num_script_keys_not_found, 16);
}

BOOST_AUTO_TEST_SUITE_END()
} // namespace wallet
