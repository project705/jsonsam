#!/usr/bin/python3

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

import json
import random
import argparse
import collections
from pathlib import Path

# Use sys.stdin/sys.stdout instead...
STDIN = Path('/dev/stdin')
STDOUT = Path('/dev/stdout')

class DictSam:
    '''
    Dictionary split and merge (DICTSAM) main class.
    '''
    ignore_leaves = False
    enforce_unique = False
    def __init__(self, data=None, denormed=False, enforce_unique=False, enforce_serdes=True):
        DictSam.enforce_unique = enforce_unique
        if not isinstance(data, (dict, list, type(None))):
            raise TypeError("Data must contain root of dictionary or list type")
        if denormed:
            self._data = self.normalize(data)
        else:
            self._data = data
        if enforce_serdes:
            # DictSam currently only supports JSON-serializable dictionaries
            # This is a hacky admission control mechanism to guarantee that.
            self._data = json.loads(json.dumps(self._data))

    @classmethod
    def set_ignore_leaves(cls, ignore_leaves):
        ''' Set ignore leaves behavior '''
        DictSam.ignore_leaves = ignore_leaves

    def denormalize(self, data=None):
        '''
        Convert a nested dictionary into a list of lists of paths
        '''
        denormed = []
        def helper(data, curr_path=None):
            if not curr_path:
                curr_path = []
            if isinstance(data, dict):
                for key, value in data.items():
                    helper(value, curr_path + [key])
            elif isinstance(data, list):
                # Convert nested lists to dicts for convenience
                for idx, value in enumerate(data):
                    helper(value, curr_path + [idx])
            else:
                denormed.append(curr_path + [data])
        if data:
            helper(data)
        else:
            helper(self._data)
        return denormed

    @classmethod
    def normalize(cls, data):
        '''
        Convert a list of lists of paths into a nested dictionary
        '''
        nested_dict = lambda: collections.defaultdict(nested_dict)
        cursor = cursor_root = collections.defaultdict(nested_dict)
        for path in data:
            assert len(path) > 1 # Dict consists of pairs
            key = None
            for key in path[:-1]:
                if not isinstance(cursor[key], dict):
                    if cls.enforce_unique:
                        raise RuntimeError('Path "{}" overwrites existing path'
                                           .format('.'.join([str(x) for x in path])))
                    # This is an overwrite of an existing leaf so smash it
                    cursor[key] = collections.defaultdict(nested_dict)
                cursor_prev = cursor
                cursor = cursor[key]
            cursor_prev[key] = path[-1]
            cursor = cursor_root
        return cls._restore_lists(cursor_root)

    def random_dict_pick(self, pct_pick):
        '''
        Returns a DictSam with a random selection of paths.

        pct_pick -- Percentage of paths to randomly select.  Note two calls
        with > 50 must contain some overlapping paths.
        '''

        denorm = self.denormalize()
        num_picks = pct_pick * len(denorm) // 100
        denorm = random.sample(denorm, num_picks)
        return DictSam(denorm, denormed=True)

    def get_data(self):
        ''' Get data dictionary '''
        return self._data

    def items(self):
        ''' Get data dictionary items '''
        return self._data.items()

    @classmethod
    def _restore_lists(cls, pure_dict, mixed_dict=None):
        '''
        Walk a nested dictionary and convert each subdictionary with integer
        keys into nested lists. Note that there is a slight loss of dictionary
        string integer semantics. Also converts defaultdicts back to dicts.

        pure_dict -- Pure nested dictionary (no lists) input
        mixed_dict -- Output dictionary consisting of nested dictionaries and lists
        '''
        if not mixed_dict:
            ints = all([cls._is_int(x) for x in pure_dict.keys()])
            if ints and pure_dict.keys():
                mixed_dict = [None] * (max(pure_dict.keys()) + 1)
            else:
                mixed_dict = {}
        for key, value in pure_dict.items():
            if isinstance(value, dict):
                # Discards list-as-dict semantics
                if all([cls._is_int(x) for x in value.keys()]):
                    # Fill sparse list indices with Nones
                    sorted_by_key_vals = [(k, value.get(k)) for k in range(max(value.keys()) + 1)]
                    mixed_dict[key] = [x[1] for x in sorted_by_key_vals]
                else:
                    mixed_dict[key] = dict(value)
                cls._restore_lists(value, mixed_dict[key])
            else:
                mixed_dict[key] = value
        return mixed_dict

    @staticmethod
    def _is_int(val):
        ''' Utility function to check for an integer string. '''
        try:
            int(val)
            return True
        except ValueError:
            return False

    @classmethod
    def _cmp_list(cls, left, right):
        '''
        Compare two lists element by element
        '''
        end = min(len(left), len(right))
        if DictSam.ignore_leaves:
            end -= 1
        left = left[:end]
        right = right[:end]
        for lelm, relm in zip(left, right):
            if lelm != relm:
                return False
        return True

    @classmethod
    def _cmp_lists(cls, left, right):
        '''
        Check if a list exists among a list of lists

        left - List of interest
        right -- List of lists against which to check
        '''
        assert not isinstance(left[0], list)
        for del_elm in right:
            if cls._cmp_list(left, del_elm):
                return True
        return False

    def _sub_and(self, other, is_or=True):
        data_a_denorm = self.denormalize()
        data_b_denorm = other.denormalize()
        outlist = []
        # Brute force for now; could use set instead...
        for data_a_elm in data_a_denorm:
            res = self._cmp_lists(data_a_elm, data_b_denorm)
            if is_or:
                res = not res

            if res:
                outlist.append(data_a_elm)

        return DictSam(outlist, True)

    def __getitem__(self, key):
        return self._data[key]

    def __sub__(self, other):
        return self._sub_and(other)

    def __and__(self, other):
        return self._sub_and(other, False)

    def __or__(self, other):
        return DictSam(self.denormalize() + other.denormalize(), True)

    def __eq__(self, other):
        return self.get_data() == other.get_data()

class JsonSam(DictSam):
    '''
    JSON split and merge (DICTSAM) main class.
    '''
    def __init__(self, fname, fname_aux=None, ignore_leaves=False, enforce_unique=False):
        (denormed_input, data) = self._load_data(fname)
        super().__init__(data, True, enforce_unique)
        self.donorm = denormed_input
        self.denorm_accum = data
        self.is_std = False
        if fname_aux and fname_aux[0]:
            self.json_sam_aux = JsonSam(fname_aux, enforce_unique=enforce_unique)

        self.set_ignore_leaves(ignore_leaves)

    def process(self, fname, fname_aux=None, outfile=None, set_op=None):
        '''
        Process a normalized or denormalized JSON file
        '''
        if fname[0] == STDIN and not outfile:
            self.is_std = True
            mkfn = lambda f, s: STDOUT
        elif outfile:
            mkfn = lambda f, s: outfile
            if outfile == STDOUT:
                self.is_std = True
        else:
            mkfn = lambda f, s: f.parent / Path(f.stem + s).with_suffix(f.suffix)

        if fname_aux[0]:
            ret = self._do_set_op(set_op)
            outpath = mkfn(fname[0], '-norm')
            self._write_normed(ret.get_data(), outpath)
        else:
            if set_op:
                raise NotImplementedError('Operand file (-F) required for "{}" operation'
                                          .format(set_op))
            if self.donorm:
                outpath = mkfn(fname[0], '-norm')
                self._write_normed(self.get_data(), outpath)
            else:
                outpath = mkfn(fname[0], '-denorm')
                self._write_denormed(outpath)

    def _do_set_op(self, set_op):
        if set_op == 'union':
            return self | self.json_sam_aux
        if set_op == 'except':
            return self - self.json_sam_aux
        if set_op == 'intersect':
            return self & self.json_sam_aux

        raise NotImplementedError('Invalid set operation "{}"'.format(set_op))

    def _load_data(self, files):
        '''
        Loads either a standard JSON file (normalized) or a mutable
        denormalized json file.  Denormalized files detected from header.

        path -- Input file name

        '''

        ret = []
        denormed_input = None
        for fname in files:
            with open(fname, 'r') as handle:
                raw_data = handle.read()
            try:
                data = json.loads(raw_data)
                if not isinstance(data, (dict, list)):
                    raise TypeError("{} must contain root of dictionary or list type"
                                    .format(fname))
                # Note this can alias a valid single-line path as a normalized input...
                ret += self.denormalize(data)
                if denormed_input is None:
                    denormed_input = False
                elif denormed_input is True:
                    raise TypeError("{} must be normalized consistent with other input files"
                                    .format(fname))
            except json.decoder.JSONDecodeError:
                for json_path in raw_data.split('\n'):
                    if json_path:
                        try:
                            ret.append(json.loads(json_path))
                        except json.decoder.JSONDecodeError:
                            # Allow denormed prefix for some edge cases (eg onepath)
                            ret.append(json.loads(json_path[1:]))

                if denormed_input is None:
                    denormed_input = True
                elif denormed_input is False:
                    raise TypeError("{} must be denormalized consistent with other input files"
                                    .format(fname))

        # Unfortunately results in lexicographic sort of integers because all
        # elms need to convert to strings to avoid "int < str" exceptions, and
        # python3 no longer allows passing a comparator function.
        return (denormed_input, sorted(ret, key=lambda a: [str(x) for x in a]))

    def _write_normed(self, data, outpath):
        ''' Write normalized json file to disk '''
        mixed_dict = data
        out_json = json.dumps(mixed_dict, indent=2)

        if not self.is_std and not outpath.suffix:
            outpath = outpath.with_suffix('.json')
        with open(outpath, 'w') as handle:
            handle.write(out_json)
        if not self.is_std:
            print("Updated JSON file written to {}".format(outpath))

    def _write_denormed(self, outpath):
        ''' Write denormalized json file to disk '''
        denormed = self.denorm_accum
        out_txt = ''
        for path in denormed:
            out_txt += json.dumps(path) + '\n'
        if len(out_txt) > 0:
            out_txt = out_txt[:-1]
        if len(denormed) == 1:
            # Disambiguate from valid single JSON input list
            out_txt = '_' + out_txt

        if not self.is_std and not outpath.suffix:
            outpath = outpath.with_suffix('.json')
        with open(outpath, 'w') as handle:
            handle.write(out_txt)
        if not self.is_std:
            print("Make edits to {} and then rerun with modified file to generate "
                  "updated JSON output"
                  .format(outpath))

def main():
    ''' CLI entry point '''
    arg_parser = argparse.ArgumentParser()
    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument('-e', dest='set_op', required=False, default=None,
                       action='store_const', const='except',
                       help='Except (subtract/remove)')
    arg_parser.add_argument('-E', dest='enforce_unique', required=False,
                            action='store_true', default=False,
                            help='Enforce unique paths on normalization (no overwrite)')
    arg_parser.add_argument('-F', dest='infileaux', required=False,
                            default=None, type=Path,
                            help='Operand input JSON file')
    arg_parser.add_argument('-I', dest='ignore_leaves', required=False,
                            action='store_true', default=False,
                            help='Ignore leaf values for set operations')
    group.add_argument('-i', dest='set_op', required=False, default=None,
                       action='store_const', const='intersect',
                       help='Intersect')
    arg_parser.add_argument('-o', dest='outfile', required=False,
                            default=None, type=Path,
                            help='Output JSON file (autogenerated name if omitted)')
    group.add_argument('-u', dest='set_op', required=False, default=None,
                       action='store_const', const='union',
                       help='Union (add/merge)')
    arg_parser.add_argument('infiles', nargs='*', default=[STDIN],
                            help='Input files ("-" for last file outputs to stdout)')
    args = arg_parser.parse_args()

    infiles = [Path(x) for x in args.infiles]
    infileaux = [args.infileaux]

    if infiles[-1] == Path('-'):
        infiles.pop()
        outfile = STDOUT
    else:
        outfile = args.outfile

    json_sam = JsonSam(infiles, infileaux, args.ignore_leaves, args.enforce_unique)
    json_sam.process(infiles, infileaux, outfile, args.set_op)

if __name__ == "__main__":
    main()
