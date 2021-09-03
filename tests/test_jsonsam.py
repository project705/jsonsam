'''
Copyright (c) 2021 Eric D. Cohen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import re
import json
import random
import operator
import tempfile
import subprocess as sp

from pathlib import Path
from deepdiff import DeepDiff
import pytest

from jsonsam import __version__
from jsonsam import DictSam, DictGen

MYWD = Path().absolute()
SCRIPTDIR = Path(__file__).parent.absolute()

SDIR = SCRIPTDIR / 'data'
CLI_PY = SCRIPTDIR.parents[0] / 'jsonsam' / 'jsonsam.py'
DICT_PY = SCRIPTDIR.parents[0] / 'jsonsam' / 'randdict.py'

class Utils:
    @staticmethod
    def run_rand_ops(seed, opfn):
        stringify_elms = lambda l: [str(x) for x in l]
        stringify_list = lambda ll: [','.join(stringify_elms(x)) for x in ll]
        test_dict = DictGen(seed).gen_fake_dict(breadth_rng=(2, 4), depth_rng=(3, 5))
        dict_sam = DictSam(test_dict)
        dict_sam_a = dict_sam.random_dict_pick(75)
        dict_sam_b = dict_sam.random_dict_pick(55)
        dict_sam_a_denorm = dict_sam_a.denormalize()
        dict_sam_b_denorm = dict_sam_b.denormalize()
        reference = opfn(set(stringify_list(dict_sam_a_denorm)),
                         set(stringify_list(dict_sam_b_denorm)))
        assert len(reference) != 0

        res = opfn(dict_sam_a, dict_sam_b)
        res_denorm = res.denormalize()
        res_denorm_set = set(stringify_list(res_denorm))
        diff = res_denorm_set - reference
        # Account for the fact that we populate missing list elms with Nones, whereas
        # the raw denormed will just have the missing elms nonexistent
        assert all([re.search('None', x) for x in diff])

class TestJsonSam:
    @classmethod
    def setup_class(cls):
        seed = 1031
        random.seed(seed)
        print("Version {}".format(__version__))
        print("Using PRNG seed {}".format(seed))
        cls.utils = Utils

    def test_gen_dict(self):
        test_dict = DictGen().gen_fake_dict()
        assert len(test_dict.keys()) != 0

    def test_identity(self):
        test_dict = DictGen().gen_fake_dict()
        dict_sam = DictSam(test_dict)
        denormed = dict_sam.denormalize()
        # Basic heuristic
        assert len(test_dict) < len(denormed)

        ddiff = DeepDiff(test_dict, dict_sam.get_data())
        assert len(ddiff) == 0

    @pytest.mark.parametrize("data", [{}, []])
    def test_empty(self, data):
        dict_sam = DictSam(data)
        denormed = dict_sam.denormalize()
        # Basic heuristic
        assert len(denormed) == 0

        ddiff = DeepDiff(data, dict_sam.get_data())
        assert len(ddiff) == 0

    @pytest.mark.parametrize("data", ['"asdf"', 'true', '27', '3.14'])
    def test_invalid(self, data):
        jdata = json.loads(data)
        with pytest.raises(TypeError):
            DictSam(jdata)

    def test_unsupported_types(self):
        with pytest.raises(TypeError):
            DictSam({'setdata': set(range(5))})

        with pytest.raises(TypeError):
            DictSam({'clsdata': self.utils})

    def test_sub(self):
        test_dict = DictGen().gen_fake_dict()
        dict_sam = DictSam(test_dict)
        sub_key = random.choice(list(test_dict.keys()))
        dict_sam_sub = DictSam({sub_key: test_dict[sub_key]})

        res = dict_sam - dict_sam_sub
        ddiff = DeepDiff(test_dict, res.get_data())
        assert len(ddiff['dictionary_item_removed']) == 1

        res = dict_sam - dict_sam_sub
        ddiff = DeepDiff(test_dict, res.get_data())
        assert len(ddiff['dictionary_item_removed']) == 1

    def test_or(self):
        test_dict_a = DictGen().gen_fake_dict()
        test_dict_b = DictGen(11).gen_fake_dict()
        dict_sam_a = DictSam(test_dict_a)
        dict_sam_b = DictSam(test_dict_b)
        res = dict_sam_a | dict_sam_b
        ddiff = DeepDiff(test_dict_a, res.get_data())
        assert len(ddiff['dictionary_item_added']) != 0

    def test_and(self):
        test_dict_a = DictGen().gen_fake_dict()
        test_dict_b = DictGen(11).gen_fake_dict()
        dict_sam_a = DictSam(test_dict_a)
        and_key = random.choice(list(test_dict_a.keys()))
        test_dict_b = {}
        test_dict_b[and_key] = test_dict_a[and_key]
        dict_sam_b = DictSam(test_dict_b)
        res = dict_sam_a & dict_sam_b
        ddiff = DeepDiff(test_dict_a, res.get_data())
        assert len(ddiff['dictionary_item_removed']) == len(test_dict_a) - 1

    def test_eq(self):
        test_dict_a = DictGen().gen_fake_dict()
        test_dict_b = DictGen(11).gen_fake_dict()
        dict_sam_a = DictSam(test_dict_a)
        dict_sam_b = DictSam(test_dict_b)
        assert dict_sam_a != dict_sam_b
        dict_sam_c = DictSam(test_dict_a)
        assert dict_sam_a == dict_sam_c

    def test_rand_ops(self, num_iters=32):
        for idx in range(num_iters):
            opfn = random.choice([operator.and_, operator.or_, operator.sub])
            self.utils.run_rand_ops(idx, opfn)

    def test_overwrite(self):
        denorm_data = [["eat", "floor", "board", 0, "CRUD"],
                       ["eat", "floor", "board", 0, "set", 0.21]]
        dict_sam = DictSam()
        norm_data = dict_sam.normalize(denorm_data)
        assert norm_data['eat']['floor']['board'][0]['set'] == 0.21

        dict_sam = DictSam(enforce_unique=True)
        with pytest.raises(RuntimeError):
            dict_sam.normalize(denorm_data)

    @pytest.mark.parametrize("stem", ['test', 'test_root_list', 'onepath'])
    def test_cli_json_ident(self, stem):
        cmd = [CLI_PY, SDIR / (stem + '.json')]
        sp.run(cmd, check=True)
        cmd = [CLI_PY, SDIR / (stem + '-denorm.json')]
        sp.run(cmd, check=True)
        with open(SDIR / (stem + '.json'), 'r') as hand0,\
             open(SDIR / (stem + '-denorm-norm.json'), 'r') as hand1:
            test_dict = json.load(hand0)
            test_dict_norm = json.load(hand1)

        ddiff = DeepDiff(test_dict, test_dict_norm)
        assert len(ddiff) == 0

    def test_cli_rand_json_ident(self, num_iters=5):
        for idx in range(num_iters):
            tmpdict = '/tmp/_tmpdict'
            cmd = [DICT_PY, '-B', '6', '-D', '6', '-s', str(idx), '-o', tmpdict]
            sp.run(cmd, check=True)
            cmd = [CLI_PY, tmpdict]
            sp.run(cmd, check=True)
            cmd = [CLI_PY, tmpdict + '-denorm.json']
            sp.run(cmd, check=True)
            with open(tmpdict, 'r') as hand0,\
                 open(tmpdict + '-denorm-norm.json', 'r') as hand1:
                test_dict = json.load(hand0)
                test_dict_norm = json.load(hand1)

            ddiff = DeepDiff(test_dict, test_dict_norm)
            assert len(ddiff) == 0

    def test_cli_json_std_ident(self):
        cmd = ['cat', SDIR / 'test.json']
        proc = sp.Popen(cmd, stdout=sp.PIPE)
        cmd = [CLI_PY]
        proc = sp.Popen(cmd, stdin=proc.stdout, stdout=sp.PIPE)
        cmd = [CLI_PY]
        proc = sp.Popen(cmd, stdin=proc.stdout, stdout=sp.PIPE)
        (cmdout, cmderr) = proc.communicate()
        assert not cmderr
        test_dict_norm = json.loads(cmdout)
        with open(SDIR / 'test.json', 'r') as hand0:
            test_dict = json.load(hand0)

        ddiff = DeepDiff(test_dict, test_dict_norm)
        assert len(ddiff) == 0

    def test_cli_json_merge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            print("Using directory {}".format(tmpdir))
            cmd = "{} -B5 -D5 -c 7 -o {}/data.json".format(DICT_PY, tmpdir)
            print(cmd)
            sp.check_output(cmd, shell=True)
            cmd = "{0} {1}/*.json -".format(CLI_PY, tmpdir)
            print(cmd)
            norm_ret = sp.check_output(cmd, shell=True)
            # merge-->norm-->denorm-->norm cycle
            cmd = "{0} {1}/*.json - | {0} | {0}".format(CLI_PY, tmpdir)
            print(cmd)
            norm_norm_ret = sp.check_output(cmd, shell=True)
            assert len(norm_ret) > 10000 # Sanity, make sure we got something
            # Verify basic consistency for merge/norm-->denorm-->norm cycle
            assert norm_ret == norm_norm_ret

    def test_cli_json_intersect(self):
        cmd = [CLI_PY, '-F', SDIR / 'test_sub1.json', '-i', SDIR / 'test.json']
        sp.run(cmd, check=True)
        with open(SDIR / 'test.json', 'r') as hand0, open(SDIR / 'test-norm.json', 'r') as hand1:
            test_dict = json.load(hand0)
            test_dict_norm = json.load(hand1)

        ddiff = DeepDiff(test_dict, test_dict_norm)
        assert len(ddiff['iterable_item_removed']) != 0

    def test_cli_json_except(self):
        cmd = [CLI_PY, '-F', SDIR / 'test_sub1.json', '-e', SDIR / 'test.json']
        sp.run(cmd, check=True)
        with open(SDIR / 'test.json', 'r') as hand0, open(SDIR / 'test-norm.json', 'r') as hand1:
            test_dict = json.load(hand0)
            test_dict_norm = json.load(hand1)

        ddiff = DeepDiff(test_dict, test_dict_norm)
        assert len(ddiff['dictionary_item_removed']) == 3
        assert len(test_dict_norm) == 1

    def test_cli_json_union(self):
        cmd = [CLI_PY, '-F', SDIR / 'test_add1.json', '-u', SDIR / 'test.json']
        sp.run(cmd, check=True)
        with open(SDIR / 'test.json', 'r') as hand0, open(SDIR / 'test-norm.json', 'r') as hand1:
            test_dict = json.load(hand0)
            test_dict_norm = json.load(hand1)

        ddiff = DeepDiff(test_dict, test_dict_norm)
        assert len(ddiff['dictionary_item_added']) == 1

    def test_cli_json_intersect_ignore_leaves(self):
        cmd = [CLI_PY, '-F', SDIR / 'simple_leafmod.json', '-i', SDIR / 'simple.json']
        sp.run(cmd, check=True)
        with open(SDIR / 'simple.json', 'r') as hand0,\
             open(SDIR / 'simple-norm.json', 'r') as hand1:
            test_dict = json.load(hand0)
            test_dict_norm = json.load(hand1)

        ddiff = DeepDiff(test_dict, test_dict_norm)

        # List deltas appears as type change to null/None
        assert len(ddiff['type_changes']) == 1
        assert len(ddiff['dictionary_item_removed']) == 1

        cmd.append('-I') # Enable ignore leaves
        sp.run(cmd, check=True)
        with open(SDIR / 'simple.json', 'r') as hand0,\
             open(SDIR / 'simple-norm.json', 'r') as hand1:
            test_dict = json.load(hand0)
            test_dict_norm = json.load(hand1)

        ddiff = DeepDiff(test_dict, test_dict_norm)
        assert len(ddiff) == 0
