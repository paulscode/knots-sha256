#!/usr/bin/env python3
# Copyright (c) 2019-present The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test the generation of UTXO snapshots using `dumptxoutset`.
"""

from test_framework.blocktools import COINBASE_MATURITY
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    assert_raises_rpc_error,
    sha256sum_file,
)
import hashlib
import os


class DumptxoutsetTest(BitcoinTestFramework):
    def set_test_params(self):
        self.setup_clean_chain = True
        self.num_nodes = 1

    def check_expected_network(self, node, active):
        rev_file = node.blocks_path / "rev00000.dat"
        bogus_file = node.blocks_path / "bogus.dat"
        rev_file.rename(bogus_file)
        assert_raises_rpc_error(
            -1, 'Could not roll back to requested height.', node.dumptxoutset, 'utxos.dat', rollback=99)
        assert_equal(node.getnetworkinfo()['networkactive'], active)

        # Cleanup
        bogus_file.rename(rev_file)

    @staticmethod
    def check_output_file(path, is_human_readable, expected_digest):
        with open(str(path), 'rb') as f:
            content = f.read()

            if is_human_readable:
                # Normalise platform EOL to \n, while making sure any stray \n becomes a literal backslash+n to avoid a false positive
                # This ensures the platform EOL and only the platform EOL produces the expected hash
                linesep = os.linesep.encode('utf8')
                content = b'\n'.join(line.replace(b'\n', b'\\n') for line in content.split(linesep))

            digest = hashlib.sha256(content).hexdigest()
            # UTXO snapshot hash should be deterministic based on mocked time.
            assert_equal(digest, expected_digest)

    def test_dump_file(self, testname, params, expected_digest):
        node = self.nodes[0]

        self.log.info(testname)
        filename = testname + '_txoutset.dat'
        is_human_readable = not params.get('format') is None

        out = node.dumptxoutset(path=filename, type="latest", **params)
        expected_path = node.chain_path / filename

        assert expected_path.is_file()

        assert_equal(out['coins_written'], 100)
        assert_equal(out['base_height'], 100)
        assert_equal(out['path'], str(expected_path))
        # Blockhash should be deterministic based on mocked time.
        assert_equal(
            out['base_hash'],
            '6885775faa46290bedfa071f22d0598c93f1d7e01f24607c4dedd69b9baa4a8f')

        self.check_output_file(expected_path, is_human_readable, expected_digest)

        assert_equal(
            out['txoutset_hash'], 'd4453995f4f20db7bb3a604afd10d7128e8ee11159cde56d5b2fd7f55be7c74c')
        assert_equal(out['nchaintx'], 101)

        self.log.info("Test that a path to an existing or invalid file will fail")
        assert_raises_rpc_error(
            -8, '{} already exists'.format(filename),  node.dumptxoutset, filename, "latest")
        invalid_path = node.datadir_path / "invalid" / "path"
        assert_raises_rpc_error(
            -8, "Couldn't open file {}.incomplete for writing".format(invalid_path), node.dumptxoutset, invalid_path, "latest")

        self.log.info("Test that dumptxoutset with unknown dump type fails")
        assert_raises_rpc_error(
            -8, 'Invalid snapshot type "bogus" specified. Please specify "rollback" or "latest"', node.dumptxoutset, 'utxos.dat', "bogus")

        self.log.info("Test that dumptxoutset failure does not leave the network activity suspended when it was on previously")
        self.check_expected_network(node, True)

        self.log.info("Test that dumptxoutset failure leaves the network activity suspended when it was off")
        node.setnetworkactive(False)
        self.check_expected_network(node, False)
        node.setnetworkactive(True)

        if params.get('format') == ():
            with open(expected_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
                sep = params.get('separator', ',')
                if params.get('show_header', True):
                    assert_equal(content.pop(0).rstrip(),
                        "#(blockhash 6885775faa46290bedfa071f22d0598c93f1d7e01f24607c4dedd69b9baa4a8f ) txid{s}vout{s}value{s}coinbase{s}height{s}scriptPubKey".format(s=sep))
                assert_equal(content[0].rstrip(),
                    "bd539bfffb4206d874f3fc58748e3d3986d51875f7514500d8391db794458905{s}0{s}5000000000{s}1{s}74{s}76a9142b4569203694fc997e13f2c0a1383b9e16c77a0d88ac".format(s=sep))

    def run_test(self):
        """Test a trivial usage of the dumptxoutset RPC command."""
        node = self.nodes[0]
        mocktime = node.getblockheader(node.getblockhash(0))['time'] + 1
        node.setmocktime(mocktime)
        self.generate(node, COINBASE_MATURITY)

        self.test_dump_file('no_option',           {},
                            'd9506d541437f5e2892d6b6ea173f55233de11601650c157a27d8f2b9d08cb6f')
        self.test_dump_file('all_data',            {'format': ()},
                            '744dcf65d5a3f69656dc6876a8ef82bfc25afa7c9fb0b183717c05cb91a2379d')
        self.test_dump_file('partial_data_1',      {'format': ('txid',)},
                            '61c3edc7732051f3c49f66c860bf4a1929e293bebad09b663a2f91b8bb73d78d')
        self.test_dump_file('partial_data_order',  {'format': ('height', 'vout')},
                            '2ffd6d4c9da2b9a08299622401a6f9eb706656c2ec9c8dbc3bea4b696d68a51a')
        self.test_dump_file('partial_data_double', {'format': ('scriptPubKey', 'scriptPubKey')},
                            '79d8f34e0224177a317d002aaab253b4d367163dc148e067884199c1ffbe2ab0')
        self.test_dump_file('no_header',           {'format': (), 'show_header': False},
                            '787015e5008c190565e2d3e2f9b3e74c555c3713c71645cdaca830d9e1c84311')
        self.test_dump_file('separator',           {'format': (), 'separator': ':'},
                            '19c935e8ce0a8f13135bbacd9f5aaeef7ebfdd98d56abf4ceb5a1620a693e3fe')
        self.test_dump_file('all_options',         {'format': (), 'show_header': False, 'separator': ':'},
                            '3d98d75970e3966fddd07f4be4bab5a05f60fe04d0cdf7681324a65c667616a0')

        # Other failing tests
        assert_raises_rpc_error(
            -8, 'unable to find item \'sample\'',  node.dumptxoutset, path='xxx', type='latest', format=['sample'])

if __name__ == '__main__':
    DumptxoutsetTest(__file__).main()
