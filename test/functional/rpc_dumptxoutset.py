#!/usr/bin/env python3
# Copyright (c) 2019-present The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test the generation of UTXO snapshots using `dumptxoutset`.
"""

from test_framework.blocktools import COINBASE_MATURITY
from test_framework.messages import COIN
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    assert_raises_rpc_error,
    sha256sum_file,
)


class DumptxoutsetTest(BitcoinTestFramework):
    def set_test_params(self):
        self.setup_clean_chain = True
        self.num_nodes = 1

    def test_dumptxoutset_with_fork(self):
        node = self.nodes[0]
        tip = node.getbestblockhash()
        target_height = node.getblockcount() - 10
        target_hash = node.getblockhash(target_height)

        # Create a fork of two blocks at the target height
        invalid_block = node.getblockhash(target_height + 1)
        node.invalidateblock(invalid_block)
        # Reset mocktime to not regenerate the same blockhash
        node.setmocktime(0)
        self.generate(node, 2)

        # Move back on to actual main chain
        node.reconsiderblock(invalid_block)
        self.wait_until(lambda: node.getbestblockhash() == tip)

        # Use dumptxoutset at the forked height
        out = node.dumptxoutset("txoutset_fork.dat", "rollback", {"rollback": target_height})

        # Verify the snapshot was created at the target height and not the fork tip
        assert_equal(out['base_height'], target_height)
        assert_equal(out['base_hash'], target_hash)

        # Cover the same case as above with an in-memory database
        out_mem = node.dumptxoutset("txoutset_fork_mem.dat", "rollback", {"rollback": target_height, "in_memory": True})
        assert_equal(out_mem['base_height'], target_height)
        assert_equal(out_mem['base_hash'], target_hash)


    @staticmethod
    def dump_ascii(node, name, **params):
        out = node.dumptxoutset(path=f"{name}_txoutset.txt", **params)
        # Text mode: the platform EOL (and only the platform EOL) becomes \n
        with open(node.chain_path / f"{name}_txoutset.txt", 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
        return out, lines

    def test_human_readable(self):
        node = self.nodes[0]
        fields = ['txid', 'vout', 'value', 'coinbase', 'height', 'scriptPubKey']
        tip_hash = node.getbestblockhash()
        tip_height = node.getblockcount()

        self.log.info("Test the human-readable (ASCII) format with all items")
        out, lines = self.dump_ascii(node, 'all_data', type='latest', format=[])
        assert_equal(lines[0], f"#(blockhash {tip_hash} ) " + ",".join(fields))
        rows = [line.split(',') for line in lines[1:]]
        assert_equal(len(rows), out['coins_written'])
        for txid, vout, value, coinbase, height, spk in rows:
            utxo = node.gettxout(txid, int(vout))
            assert_equal(int(value), int(utxo['value'] * COIN))
            assert_equal(spk, utxo['scriptPubKey']['hex'])
            assert_equal(coinbase == '1', utxo['coinbase'])
            assert_equal(int(height), tip_height - utxo['confirmations'] + 1)

        self.log.info("Test selected items, in the requested order (repeats allowed)")
        for name, fmt in [('partial_data_1', ['txid']),
                          ('partial_data_order', ['height', 'vout']),
                          ('partial_data_double', ['scriptPubKey', 'scriptPubKey'])]:
            _, plines = self.dump_ascii(node, name, type='latest', format=fmt)
            assert_equal(plines[0], f"#(blockhash {tip_hash} ) " + ",".join(fmt))
            assert_equal(plines[1:], [",".join(row[fields.index(f)] for f in fmt) for row in rows])

        self.log.info("Test show_header and separator")
        _, no_header = self.dump_ascii(node, 'no_header', type='latest', format=[], show_header=False)
        assert_equal(no_header, lines[1:])
        _, separated = self.dump_ascii(node, 'separator', type='latest', format=[], separator=':')
        assert_equal(separated, [line.replace(',', ':') for line in lines])
        _, all_options = self.dump_ascii(node, 'all_options', type='latest', format=[], show_header=False, separator=':')
        assert_equal(all_options, [line.replace(',', ':') for line in lines[1:]])

        self.log.info("Test the human-readable format on the rollback path (temporary UTXO database)")
        target_height = tip_height - 10
        out, rb_lines = self.dump_ascii(node, 'rollback_data', type='rollback', rollback=target_height, format=['txid', 'vout'])
        assert_equal(out['base_height'], target_height)
        assert_equal(rb_lines[0], f"#(blockhash {node.getblockhash(target_height)} ) txid,vout")
        assert_equal(len(rb_lines) - 1, out['coins_written'])

        assert_raises_rpc_error(
            -8, 'unable to find item \'sample\'', node.dumptxoutset, path='xxx', type='latest', format=['sample'])

    def run_test(self):
        """Test a trivial usage of the dumptxoutset RPC command."""
        node = self.nodes[0]
        mocktime = node.getblockheader(node.getblockhash(0))['time'] + 1
        node.setmocktime(mocktime)
        self.generate(node, COINBASE_MATURITY)

        FILENAME = 'txoutset.dat'
        out = node.dumptxoutset(FILENAME, "latest")
        expected_path = node.chain_path / FILENAME

        assert expected_path.is_file()

        assert_equal(out['coins_written'], 100)
        assert_equal(out['base_height'], 100)
        assert_equal(out['path'], str(expected_path))
        # Blockhash should be deterministic based on mocked time.
        assert_equal(
            out['base_hash'],
            '220aee93f0f5409631f35488898258f0930952bd620063cb4d7d87f7c28a8f50')

        # UTXO snapshot hash should be deterministic based on mocked time.
        assert_equal(
            sha256sum_file(str(expected_path)).hex(),
            'e8c59b1bc1f19061c67eb7a392f4ea17eea83af58646ea2909e270546699c36c')

        assert_equal(
            out['txoutset_hash'], '771d773b5c27b6f35f598ce764652a2cf28fbc268341eb1827844e416c629c7d')
        assert_equal(out['nchaintx'], 101)

        # Specifying a path to an existing or invalid file will fail.
        assert_raises_rpc_error(
            -8, '{} already exists'.format(FILENAME),  node.dumptxoutset, FILENAME, "latest")
        invalid_path = node.datadir_path / "invalid" / "path"
        assert_raises_rpc_error(
            -8, "Couldn't open file {}.incomplete for writing".format(invalid_path), node.dumptxoutset, invalid_path, "latest")

        self.log.info("Test that dumptxoutset with unknown dump type fails")
        assert_raises_rpc_error(
            -8, 'Invalid snapshot type "bogus" specified. Please specify "rollback" or "latest"', node.dumptxoutset, 'utxos.dat', "bogus")

        self.test_human_readable()

        self.log.info("Testing dumptxoutset with chain fork at target height")
        self.test_dumptxoutset_with_fork()


if __name__ == '__main__':
    DumptxoutsetTest(__file__).main()
