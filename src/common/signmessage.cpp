// Copyright (c) 2009-2010 Satoshi Nakamoto
// Copyright (c) 2009-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <common/signmessage.h>
#include <hash.h>
#include <key.h>
#include <key_io.h>
#include <addresstype.h>
#include <outputtype.h>
#include <pubkey.h>
#include <uint256.h>
#include <util/strencodings.h>

#include <cassert>
#include <optional>
#include <string>
#include <variant>
#include <vector>

/**
 * Text used to signify that a signed message follows and to prevent
 * inadvertently signing a transaction.
 */
const std::string MESSAGE_MAGIC = "Bitcoin Signed Message:\n";

namespace {
//! Destination a message-signing key stands for, per output type (BIP 137 / Electrum): the former Core
//! GetDestinationForKey(), removed upstream as unused (bitcoin@fafee85358) — kept here for message verification only.
CTxDestination DestinationForSigningKey(const CPubKey& key, OutputType type)
{
    switch (type) {
    case OutputType::LEGACY: return PKHash(key);
    case OutputType::P2SH_SEGWIT:
    case OutputType::BECH32: {
        if (!key.IsCompressed()) return PKHash(key);
        CTxDestination witdest = WitnessV0KeyHash(key);
        CScript witprog = GetScriptForDestination(witdest);
        if (type == OutputType::P2SH_SEGWIT) {
            return ScriptHash(witprog);
        } else {
            return witdest;
        }
    }
    case OutputType::BECH32M:
    case OutputType::UNKNOWN: {} // never used for these; fall through to the assert
    } // no default case, so the compiler can warn about missing cases
    assert(false);
}
} // namespace

MessageVerificationResult MessageVerify(
    const std::string& address,
    const std::string& signature,
    const std::string& message)
{
    CTxDestination destination = DecodeDestination(address);
    if (!IsValidDestination(destination)) {
        return MessageVerificationResult::ERR_INVALID_ADDRESS;
    }

    OutputType signed_for_outputtype;
    if (std::holds_alternative<PKHash>(destination)) {
        signed_for_outputtype = OutputType::LEGACY;
    } else if (std::holds_alternative<ScriptHash>(destination)) {
        signed_for_outputtype = OutputType::P2SH_SEGWIT;
    } else if (std::holds_alternative<WitnessV0KeyHash>(destination)) {
        signed_for_outputtype = OutputType::BECH32;
    } else {
        return MessageVerificationResult::ERR_ADDRESS_NO_KEY;
    }

    auto signature_bytes = DecodeBase64(signature);
    if (!signature_bytes) {
        return MessageVerificationResult::ERR_MALFORMED_SIGNATURE;
    }

    uint8_t sigtype{(*signature_bytes)[0]};
    if (sigtype < 27 || sigtype > 42) {
        return MessageVerificationResult::ERR_PUBKEY_NOT_RECOVERED;
    }
    sigtype = (sigtype - 27) >> 2;
    if (sigtype == 3) {
        (*signature_bytes)[0] -= 8;
        signed_for_outputtype = OutputType::BECH32;
    } else if (sigtype == 2) {
        (*signature_bytes)[0] -= 4;
        signed_for_outputtype = OutputType::P2SH_SEGWIT;
    }

    CPubKey pubkey;
    if (!pubkey.RecoverCompact(MessageHash(message), *signature_bytes)) {
        return MessageVerificationResult::ERR_PUBKEY_NOT_RECOVERED;
    }

    CTxDestination recovered_dest = DestinationForSigningKey(pubkey, signed_for_outputtype);

    if (!(recovered_dest == destination)) {
        return MessageVerificationResult::ERR_NOT_SIGNED;
    }

    return MessageVerificationResult::OK;
}

bool MessageSign(
    const CKey& privkey,
    const std::string& message,
    std::string& signature)
{
    std::vector<unsigned char> signature_bytes;

    if (!privkey.SignCompact(MessageHash(message), signature_bytes)) {
        return false;
    }

    signature = EncodeBase64(signature_bytes);

    return true;
}

uint256 MessageHash(const std::string& message)
{
    HashWriter hasher{};
    hasher << MESSAGE_MAGIC << message;

    return hasher.GetHash();
}

std::string SigningResultString(const SigningResult res)
{
    switch (res) {
        case SigningResult::OK:
            return "No error";
        case SigningResult::PRIVATE_KEY_NOT_AVAILABLE:
            return "Private key not available";
        case SigningResult::SIGNING_FAILED:
            return "Sign failed";
        // no default case, so the compiler can warn about missing cases
    }
    assert(false);
}
