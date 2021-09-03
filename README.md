# JSONSAM Overview

## Quickstart

The following is a minimal example of the JSONSAM CLI workflow:

```console
$ jsonsam my.json
Make edits to my-denorm.json and then rerun with modified file to generate updated JSON output
$ vim my-denorm.json 		# Add/delete/edit line-based paths
$ jsonsam my-denorm.json 	# Convert edits back to standard JSON
Updated JSON file written to my-denorm-norm.json
```

The finished product (the standard JSON file with edits applied) is
`my-denorm-norm.json`. See the [Command Line Examples](#command-line-examples)
section for extensive additional examples.

## Introduction

JSONSAM captures some of the techniques I've used over the years to slice and
dice large chunks (> 1MB) of highly nested JSON.  vim is still my preferred
editor and I like to use line-based shell primitives like sed and grep when
possible.  However, since conventional JSON is not line-framed and
JSON-streaming has multipath semantics, it is generally not amenable to direct
modification using conventional Unix utilities.

JSONSAM addresses this by converting JSON into an intermediate denormalized
format (not to be confused with JSON-streaming or new-line delimited JSON).
The denormalized format captures each path in a JSON list of line-delimited
paths.  These paths can then be edited with standard tools to add, delete,
modify, shift-up/down, reorder nested lists, etc.  Once desired edits are made,
the denormalized file is renormalized back into a standard JSON file.  JSONSAM
can also work on entire directories of files at once, allowing them to be
easily merged, split and modified.  Denormalized form might also be useful for
streaming if one is willing to trade data expansion for framing.

JSONSAM can also perform set arithmetic (union, intersection and difference)
against a pair of JSON input files.  This is useful when a template or
reference file exists and it's desired to extract, remove or augment another
JSON file based on this template.

Lastly, a random realistic dictionary generator is included as part of the test
infrastructure. It creates nested dictionaries and lists of random breadth and
width.

JSONSAM comprises the following components:

- jsonsam: Command line utility for processing JSON
- randdict: Command line utility for generating random dictionaries
- JsonSam: Denormalize, edit, normalize and perform set arithmetic on JSON files
- DictSam: Denormalize, edit, normalize and perform set arithmetic on nested dictionaries/lists
- DictGen: Generate random deeply nested dictionaries and lists with realistic data

## Installation

### Install from PyPi:

`pip install jsonsam`

### Importing

```python
>>> from jsonsam import DictSam # Dictionary denorm, norm, and set arithmetic
>>> from jsonsam import DictGen # Random realistic nested dictionary/list generator
```

# Command Line Examples

```console
# online help
$ jsonsam -h
```

Consider the following file `simple.json`:
```json
$ cat simple.json
{
  "Bad": true,
  "beer": 3.14,
  "rots": "Our",
  "young": {
    "guts": "but",
    "Vodka": [
      27,
      [
        "goes",
        2.718,
        {
          "Well": "water",
          "max": "plank"
        },
        "old"
      ]
    ],
    "bark": null,
    "last": 66
  }
}
```
This file is in normalized form.  First, we denormalize the file:

```console
$ jsonsam simple.json
Make edits to simple-denorm.json and then rerun with modified file to generate updated JSON output
```

The denormalized file, `simple-denorm.json`, now contains a list of paths.
Each line represents a path from root to leaf through the original JSON file
with non-terminal integers representing list indices:

```json
$ cat simple-denorm.json
["Bad", true]
["beer", 3.14]
["rots", "Our"]
["young", "Vodka", 0, 27]
["young", "Vodka", 1, 0, "goes"]
["young", "Vodka", 1, 1, 2.718]
["young", "Vodka", 1, 2, "Well", "water"]
["young", "Vodka", 1, 2, "max", "plank"]
["young", "Vodka", 1, 3, "old"]
["young", "bark", null]
["young", "guts", "but"]
["young", "last", 66]
```

All other rows can be arbitrarily mutated, added, removed and reordered
(non-terminal integers denote nested list indices).  When the desired result is
achieved, rerun `jsonsam` with the edited `simple-denorm.json` as input to
generate a renormalized `simple-denorm-norm.json` output file.  This represents
the original JSON file with the desired additions, deletions and mutations
applied.  Note that JSONSAM appends `-norm` and `-denorm` strings to the file
stem for convenience to avoid overwriting original files and track lineage.
This behavior can be overridden with the `-o <outputfile>` option.

**Unless otherwise noted all examples that follow will start from `simple.json`
and `simple-denorm.json`.**

## Relocate dictionary slice from nested lists
Suppose we want to shift-up the pair `"Well": "water"` out of the dictionary
nested in the list of lists.  This can be achieved by applying the following
single-line diff to `simple-denorm.json`:

```diff
 ["young", "Vodka", 0, 27]
 ["young", "Vodka", 1, 0, "goes"]
 ["young", "Vodka", 1, 1, 2.718]
-["young", "Vodka", 1, 2, "Well", "water"]
+["young", "Vodka", 2, "Well", "water"]
 ["young", "Vodka", 1, 2, "max", "plank"]
 ["young", "Vodka", 1, 3, "old"]
 ["young", "bark", null]
```

To apply the changes, we normalize the path list by rerunning JSONSAM:

```diff
$ jsonsam simple-denorm.json 
Updated JSON file written to simple-denorm-norm.json
$ diff --unified=20 <(cat simple.json |jq --sort-keys '.') <(cat simple-denorm-norm.json |jq --sort-keys '.')
 {
   "Bad": true,
   "beer": 3.14,
   "rots": "Our",
   "young": {
     "Vodka": [
       27,
       [
         "goes",
         2.718,
         {
-          "Well": "water",
           "max": "plank"
         },
         "old"
-      ]
+      ],
+      {
+        "Well": "water"
+      }
     ],
     "bark": null,
     "guts": "but",
     "last": 66
   }
 }
```

We see in the above JSON that indeed the `"Well": "water"` pair has been
plucked from the nested dictionary, and a new dictionary containing the pair
has been appended to the outer list.  `simple-denorm-norm.json` now represents
the finished product.

## Click to expand additional examples:

<details><summary>Remove an item, and convert a leaf string to a dictionary</summary>

## Remove an item, and convert a leaf string to a dictionary

In this case we do two things:

1. Remove the `young.bark.null` path
1. Convert `young.guts.but` path from a terminal string to a dictionary of
`young.guts.{but:dog, route:cat}`

This can be achieved by applying the following diff to `simple-denorm.json`:

```json
 ["young", "Vodka", 1, 2, "Well", "water"]
 ["young", "Vodka", 1, 2, "max", "plank"]
 ["young", "Vodka", 1, 3, "old"]
-["young", "bark", null]
-["young", "guts", "but"]
+["young", "guts", "but", "dog"]
+["young", "guts", "route", "cat"]
 ["young", "last", 66]
```

Looking at `simple-denorm-norm.json` we see `young.bark.null` has been removed
and we've converted `young.guts.but` from a terminal string into a dictionary
of `{but:dog, route:cat}`:

```json
$ jsonsam simple-denorm.json
Updated JSON file written to simple-denorm-norm.json
$ cat simple-denorm-norm.json
{
  "Bad": true,
  "beer": 3.14,
  "rots": "Our",
  "young": {
    "Vodka": [
      27,
      [
        "goes",
        2.718,
        {
          "Well": "water",
          "max": "plank"
        },
        "old"
      ]
    ],
    "guts": {
      "but": "dog",
      "route": "cat"
    },
    "last": 66
  }
}
```
</details>

<details><summary>Convert a terminal string to a list of dictionaries</summary>

## Convert a terminal string to a list of dictionaries

Here we convert the `young.guts` path to a list of dictionaries.
This can be achieved by applying the following diff to `simple-denorm.json`:

```json
 ["young", "Vodka", 1, 2, "max", "plank"]
 ["young", "Vodka", 1, 3, "old"]
 ["young", "bark", null]
-["young", "guts", "but"]
+["young", "guts", 0, "but", "dog"]
+["young", "guts", 1, "route", "dog"]
 ["young", "last", 66]
```

And the resulting normalized JSON:

```json
$ jsonsam simple-denorm.json
Updated JSON file written to simple-denorm-norm.json
$ cat simple-denorm-norm.json
{
  "Bad": true,
  "beer": 3.14,
  "rots": "Our",
  "young": {
    "Vodka": [
      27,
      [
        "goes",
        2.718,
        {
          "Well": "water",
          "max": "plank"
        },
        "old"
      ]
    ],
    "bark": null,
    "guts": [
      {
        "but": "dog"
      },
      {
        "route": "dog"
      }
    ],
    "last": 66
  }
}
```

</details>


<details><summary>Add path and reorder a list</summary>

### Add path and reorder a list

Three tasks here:
1. Add a new `jack.beanstock.happy.941` path
1. Move list item `young.Vodka.1.2` to `young.Vodka.2`
1. Add the string "append" to `young.Vodka` list


This can be achieved by applying the following diff to `simple-denorm.json`:

```json
 ["Bad", true]
 ["beer", 3.14]
 ["rots", "Our"]
+["jack", "beanstock", "happy", 941]
 ["young", "Vodka", 0, 27]
-["young", "Vodka", 1, 0, "goes"]
-["young", "Vodka", 1, 1, 2.718]
-["young", "Vodka", 1, 2, "Well", "water"]
-["young", "Vodka", 1, 2, "max", "plank"]
+["young", "Vodka", 1, 1, "goes"]
+["young", "Vodka", 1, 0, 2.718]
+["young", "Vodka", 2, "Well", "water"]
+["young", "Vodka", 2, "max", "plank"]
+["young", "Vodka", 3, "appended"]
 ["young", "Vodka", 1, 3, "old"]
 ["young", "bark", null]
 ["young", "guts", "but"]
```

Which results in:

```json
$ jsonsam simple-denorm.json
Updated JSON file written to simple-denorm-norm.json
$ cat simple-denorm-norm.json
{
  "Bad": true,
  "beer": 3.14,
  "jack": {
    "beanstock": {
      "happy": 941
    }
  },
  "rots": "Our",
  "young": {
    "Vodka": [
      27,
      [
        2.718,
        "goes",
        null,
        "old"
      ],
      {
        "Well": "water",
        "max": "plank"
      },
      "appended"
    ],
    "bark": null,
    "guts": "but",
    "last": 66
  }
}
```

Removed list elements become `null` to preserve the ordinal of retained
elements.
</details>

<details><summary>Unix pipeline processing</summary>

## Unix pipeline processing

If no input files are provided, jsonsam defaults to reading from stdin and
writing to stdout.  This allows use of standard Unix pipelines for editing JSON
files with line-based shell utilities like sed, grep, awk, etc.

In the below example, we use grep to remove all `Vodka` keys and sed to convert `beer` to `Whiskey`:

```json
$ cat simple.json |jsonsam |grep -v Vodka |sed 's/beer/Whiskey/g' |jsonsam
{
  "Bad": true,
  "Whiskey": 3.14,
  "rots": "Our",
  "young": {
    "bark": null,
    "guts": "but",
    "last": 66
  }
}
```

</details>

<details><summary>Transmogrify 7 JSON files into 11 JSON files, round-robin paths</summary>

### Transmogrify 7 JSON files into 11 JSON files, round-robin paths

In this example, we will generate 7 random JSON files.  Next we will merge them
and then split the merge into 11 files, round-robinning the paths across the 11
new JSON files:

```console
$ randdict -B5 -D5 -c 7 -o data.json
$ ls
data000.json  data001.json  data002.json  data003.json  data004.json  data005.json  data006.json
$ jsonsam *.json - |split -xn r/11
$ ls
data000.json  data001.json  data002.json  data003.json  data004.json  data005.json  data006.json  x00  x01  x02  x03  x04  x05  x06  x07  x08  x09  x0a
$ ls x* |xargs -IF jsonsam F
Updated JSON file written to x00-norm.json
Updated JSON file written to x01-norm.json
Updated JSON file written to x02-norm.json
Updated JSON file written to x03-norm.json
Updated JSON file written to x04-norm.json
Updated JSON file written to x05-norm.json
Updated JSON file written to x06-norm.json
Updated JSON file written to x07-norm.json
Updated JSON file written to x08-norm.json
Updated JSON file written to x09-norm.json
Updated JSON file written to x0a-norm.json
```

The 11 `x<num>-norm.json` files now contain all the data in the original 7
files, but split round-robin across 11 files.  Substituting `split -xn l/11`
for the split command would instead do a conventional partition rather than
round-robin.  Of course any intermediate mutations, additions and deletions
could also be made in the same pipeline.

</details>

## Comand Line Set Operations Examples

Set operations union `|`, intersection `&` and difference `-` can be performed
on JSON files specified with positional arguments (lhs) and `-F` (rhs) options.
The following examples will use the original `simple.json` file as the
left-hand operand and `simple_aux.json` as the right-hand operand:

```json
$ cat simple_aux.json
{
  "Bad": true,
  "beer": 3.1415,
  "NEW": "PATH",
  "young": {
    "Vodka": [
      27
    ],
    "bark": null,
    "guts": "but",
    "last": 66
  }
}
```

## Difference/except `simple.json - simple_aux.json`

In the following example we perform the set difference of `simple.json -
simple_aux.json`.  Paths common to both `simple.json` and `simple_aux.json` are
removed from `simple.json`.

Note the `-I` option can also be added for all operations to ignore leaf values
in comparison.  This is useful when one wishes to use an existing JSON file as
a template for paths to remove regardless of value.

Also note removed list elements become `null` to preserve the ordinal of
retained elements.

```diff
$ jsonsam simple.json -F simple_aux.json -e
Updated JSON file written to simple-norm.json
$ diff --unified=20 <(cat simple.json |jq --sort-keys '.') <(cat simple-norm.json |jq --sort-keys '.')
 {
-  "Bad": true,
   "beer": 3.14,
   "rots": "Our",
   "young": {
     "Vodka": [
-      27,
+      null,
       [
         "goes",
         2.718,
         {
           "Well": "water",
           "max": "plank"
         },
         "old"
       ]
-    ],
-    "bark": null,
-    "guts": "but",
-    "last": 66
+    ]
   }
 }
```

## Click to expand additional set examples:

<details><summary>Intersection (simple.json & simple_aux.json)</summary>

## Intersection `(simple.json & simple_aux.json)`

In this example we perform the intersection of the two JSON files.  Note that
`-I` is passed, so the leaf values are ignored allowing us to also intersect
with a slightly less precise value of pi.

```json
$ jsonsam simple.json -F simple_aux.json -iI
Updated JSON file written to simple-norm.json
$ cat simple-norm.json
{
  "Bad": true,
  "beer": 3.14,
  "young": {
    "Vodka": [
      27
    ],
    "bark": null,
    "guts": "but",
    "last": 66
  }
}
```

</details>

<details><summary> Union/merge (simple.json | simple_aux.json)</summary>

## Union/merge `(simple.json | simple_aux.json)`

In this example we perform the union of the two JSON files.  Note the
conflicting `beer` key is overwritten by the right-hand side's value and the
`NEW` item has been added.

```json
$ jsonsam simple.json -F simple_aux.json -u
Updated JSON file written to simple-norm.json
$ cat simple-norm.json
{
  "Bad": true,
  "beer": 3.1415,
  "rots": "Our",
  "young": {
    "Vodka": [
      27,
      [
        "goes",
        2.718,
        {
          "Well": "water",
          "max": "plank"
        },
        "old"
      ]
    ],
    "bark": null,
    "guts": "but",
    "last": 66
  },
  "NEW": "PATH"
}
```

</details>

## Random nested dictionary generator examples

A random dictionary generator is included in the package.  It generates deeply
nested dictionaries of realistic random data.  Random nested lists are also
supported.  The full range of JSON types are supported.  Each step in breadth
and depth is uniquely randomized.

To generate a random dictionary of max breadth 3, max depth 4 consisting of 40%
nested lists (compact form for brevity):

```json
$ randdict -B 3 -D 4 -l 40 |jq -c '.'
{"game":{"yourself":{"difficult":"0181 Aguilar Parkways","always":{"before":530982.9961689024,"leader":{"kid":0.41913904357146525,"available":523048.62318369857},"effect":-609888.9269447384}},"believe":[[{"ok":0.24842658485754932,"kind":"91390 Williams Forges Apt. 824","charge":0.7294452894392176},"482 Bonnie Route",{"cup":null,"hotel":-292649,"bill":0.6952953662736593}],[0.47409833741964447,"093 Becker Meadow"]]},"standard":[{"former":null,"make":270989.99712404597,"pay":245327},{"couple":"Ward-Wright","say":{"state":["Miller LLC","Simpson, Cooper and Cole","Baird, Wilson and Barnes"],"though":"76018 Peterson Keys Suite 971","better":0.28193072232673766},"you":{"expect":null,"matter":{"hear":"49746 Johnson Mountain","artist":"Carr Group","interest":"2366 Miller Mission"}}},{"often":{"reason":"68465 Rosario Drive Apt. 223","early":{"actually":null,"memory":null,"theory":null},"nor":"White, Campbell and Thomas"},"hope":{"poor":2548096.1722068526,"others":372384,"from":["Vaughn PLC","Pena, Singh and Bryant",322924]}}],"truth":[{"state":{"two":{"response":0.08053812548862638,"success":null,"protect":"Long, Ross and Garcia"},"institution":null,"assume":1888192},"cut":[null,{"audience":null,"grow":"Alexander Inc","blood":"Williams, Smith and Hernandez"},1358976.5609615073],"himself":["39624 Guzman Mountains",-2605707.399841271]},["Wilson Group",0.2127797923458118,{"man":{"media":null,"member":725008.2758262581},"forget":1022493.1525128945,"guess":"Thomas Ltd"}]]}
```

# API Example

The following example shows how to use the API to generate a random test
dictionary, pick two overlapping subsets of the dictionary, then take the
difference, union and intersection of these dictionaries:

```python
>>> from jsonsam import DictSam
>>> from jsonsam import DictGen
>>> test_dict = DictGen().gen_fake_dict(breadth_rng=(2, 4), depth_rng=(3, 5), list_dist=(3, 1))
>>> dict_sam_orig = DictSam(test_dict)
>>> dict_sam_a = dict_sam_orig.random_dict_pick(60)
>>> dict_sam_b = dict_sam_orig.random_dict_pick(80)
>>> diff = dict_sam_b - dict_sam_a
>>> union = dict_sam_b | dict_sam_a
>>> intersect = dict_sam_b & dict_sam_a
```

**NOTE: At the moment only JSON-serializable structures are supported by DictSam**

Full API readthedocs coming soon...

# Authors

See [AUTHORS](AUTHORS.md)
