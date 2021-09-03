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

import sys
import json
import random
import string
import argparse
from pathlib import Path
from faker import Faker

class DictGen:
    '''
    Random dictionary generator
    '''
    def __init__(self, seed=7):
        self.fake = Faker()
        random.seed(seed)
        Faker.seed(seed)

    @staticmethod
    def _gen_rand_str(maxlen):
        chars = string.ascii_letters + string.digits + '-_ '
        return lambda: ''.join(random.choices(chars, k=random.randint(3, maxlen)))

    def gen_dict(self, breadth_rng, depth_rng, list_dist=(1, 1), leaf_fcn=None,
                 inner_fcn=None, curr_depth=0, gen_out=None):
        '''
        Generic random nested dictionary generator. Includes nested lists.
        '''
        if gen_out is None:
            gen_out = {}
        if not leaf_fcn:
            leaf_fcn = self._gen_rand_str(24)
        if not inner_fcn:
            inner_fcn = self._gen_rand_str(8)

        for _ in range(random.randint(*breadth_rng)):
            if curr_depth < random.randint(max(curr_depth, depth_rng[0]), depth_rng[1]):
                new_val = {} if random.choices((True, False), list_dist)[0] else []
                if isinstance(gen_out, dict):
                    k = inner_fcn()
                    gen_out[k] = new_val
                    self.gen_dict(breadth_rng, depth_rng, list_dist, leaf_fcn, inner_fcn,
                                  curr_depth + 1, gen_out[k])
                else:
                    assert isinstance(gen_out, list)
                    gen_out.append(new_val)
                    self.gen_dict(breadth_rng, depth_rng, list_dist, leaf_fcn, inner_fcn,
                                  curr_depth + 1, gen_out[-1])
            else:
                if isinstance(gen_out, dict):
                    gen_out[inner_fcn()] = leaf_fcn()
                else:
                    assert isinstance(gen_out, list)
                    gen_out.append(leaf_fcn())

        return gen_out

    def gen_fake_dict(self, breadth_rng=(2, 3), depth_rng=(2, 4), list_dist=(1, 1)):
        '''
        Generate random dictionary using various faker methods
        '''
        ngen = lambda: None
        fgen = lambda: random.gauss(0, 2**20)
        igen = lambda: round(random.gauss(0, 2**20))
        leaf_choices = (self.fake.street_address, self.fake.company,
                        random.random, ngen, fgen, igen)
        leaf_fcn = lambda: random.choice(leaf_choices)()

        inner_choices = (self.fake.word,)
        inner_fcn = lambda: random.choice(inner_choices)()

        return self.gen_dict(breadth_rng, depth_rng, list_dist, inner_fcn=inner_fcn,
                             leaf_fcn=leaf_fcn)

def main():
    ''' CLI entry point '''
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-a', dest='args', required=False,
                            action='store_true', default=False,
                            help='Include args in output dictionary')
    arg_parser.add_argument('-b', dest='breadth_min', required=False,
                            default=2, type=int,
                            help='Minimum breadth')
    arg_parser.add_argument('-B', dest='breadth_max', required=False,
                            default=3, type=int,
                            help='Maximum breadth')
    arg_parser.add_argument('-c', dest='count', required=False,
                            default=1, type=int,
                            help='Number of JSON files to generate')
    arg_parser.add_argument('-d', dest='depth_min', required=False,
                            default=2, type=int,
                            help='Minimum depth')
    arg_parser.add_argument('-D', dest='depth_max', required=False,
                            default=4, type=int,
                            help='Maximum depth')
    arg_parser.add_argument('-i', dest='indent', required=False,
                            default=2, type=int,
                            help='Output indent level (0 for compact)')
    arg_parser.add_argument('-l', dest='pct_lists', required=False,
                            default=50, type=int,
                            help='Percent nested lists')
    arg_parser.add_argument('-o', dest='outfile', required=False,
                            default=None, type=Path,
                            help='Output file')
    arg_parser.add_argument('-s', dest='seed', required=False,
                            default=7, type=int,
                            help='PRNG seed')
    args = arg_parser.parse_args()

    breadth = (args.breadth_min, args.breadth_max)
    if breadth[0] >= breadth[1]:
        print("-b value must be less than -B")
        sys.exit(1)

    depth = (args.depth_min, args.depth_max)
    if depth[0] >= depth[1]:
        print("-d value must be less than -D")
        sys.exit(1)

    if not 0 <= args.pct_lists < 100:
        print("-l value must be in the range [0, 100)")
        sys.exit(1)
    pct_lists = (100 - args.pct_lists, args.pct_lists)

    if args.outfile:
        outfile = args.outfile
    else:
        outfile = Path('/dev/stdout')

    if args.count == 1:
        outfiles = [outfile]
    else:
        mkfn = lambda f, s: f.parent / Path(f.stem + s).with_suffix(f.suffix)
        outfiles = [mkfn(outfile, '{:03d}'.format(n)) for n in range(args.count)]

    dict_gen = DictGen(args.seed)
    for outfile in outfiles:
        out_dict = dict_gen.gen_fake_dict(breadth, depth, pct_lists)
        if args.args:
            out_dict['__argv__'] = sys.argv
        with open(outfile, 'w') as handle:
            json.dump(out_dict, handle, indent=args.indent if args.indent else None)

if __name__ == "__main__":
    main()
