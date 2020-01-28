// Copyright (c) 2016-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <crypto/siphash.h>

#include <crypto/common.h>
#include <uint256.h>

#include <algorithm>
#include <cassert>
#include <span>

CSipHasher::CSipHasher(uint64_t k0, uint64_t k1) : m_state{k0, k1} {}

CSipHasher& CSipHasher::Write(uint64_t data)
{
    assert(m_count % 8 == 0);
    m_state.Compress2(data);
    m_count += 8;
    return *this;
}

/// Load a uint64_t from 0 to 7 bytes.
static inline uint64_t ReadU64ByLenLE(const unsigned char* data, size_t len)
{
    assert(len < 8);
    uint64_t out = 0;
    for (size_t i = 0; i < len; ++i) {
        out |= (uint64_t)data[i] << (i * 8);
    }
    return out;
}

CSipHasher& CSipHasher::Write(std::span<const unsigned char> data)
{
    SipHashState state{m_state.Copy()};
    uint64_t tail{m_tmp};
    const size_t ntail{size_t{m_count} & 0x07};
    m_count = static_cast<uint8_t>(m_count + data.size()); // wraps exactly like the byte-at-a-time count

    size_t needed{0};
    if (ntail != 0) {
        needed = 8 - ntail;
        tail |= ReadU64ByLenLE(data.data(), std::min(data.size(), needed)) << 8 * ntail;
        if (data.size() < needed) {
            m_tmp = tail;
            return *this;
        }
        state.Compress2(tail);
    }

    const size_t len{data.size() - needed};
    const size_t left{len & 0x07};
    size_t i{needed};
    while (i < len - left) {
        state.Compress2(ReadLE64(data.data() + i));
        i += 8;
    }

    m_state = state;
    m_tmp = ReadU64ByLenLE(data.data() + i, left);

    return *this;
}

uint64_t CSipHasher::Finalize() const
{
    return m_state.Copy()
                  .Compress2(m_tmp | (uint64_t{m_count} << 56))
                  .Finalize4();
}

SipHasher13UJ& SipHasher13UJ::Write(uint64_t data) noexcept
{
    m_state.Compress1(data);
    return *this;
}

SipHasher13UJ& SipHasher13UJ::WriteJumbo(const uint256& hash) noexcept
{
    m_state.Compress1Jumbo(hash);
    return *this;
}

uint64_t SipHasher13UJ::Finalize() const noexcept
{
    return m_state.Copy().Finalize3U();
}

uint64_t PresaltedSipHasher::operator()(const uint256& val) const noexcept
{
    return m_state.Copy()
                  .Compress2(val.GetUint64(0))
                  .Compress2(val.GetUint64(1))
                  .Compress2(val.GetUint64(2))
                  .Compress2(val.GetUint64(3))
                  .Compress2(uint64_t{32} << 56)
                  .Finalize4();
}

uint64_t PresaltedSipHasher::operator()(const uint256& val, uint32_t extra) const noexcept
{
    return m_state.Copy()
                  .Compress2(val.GetUint64(0))
                  .Compress2(val.GetUint64(1))
                  .Compress2(val.GetUint64(2))
                  .Compress2(val.GetUint64(3))
                  .Compress2((uint64_t{36} << 56) | extra)
                  .Finalize4();
}
