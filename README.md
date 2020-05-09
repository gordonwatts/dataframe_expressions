# dataframe_expressions

 Simple accumulating of expressions for dataframe operations

## Expression Samples

You start with a top level data frame:

```python
from dataframe_expressions import DataFrame
d = DataFrame()
```

Now you can mask it with simple operations:

```python
d1 = d[d.x > 10]
```

The operators `<,>, <=, >=, ==,` and `!=` are all supported. You can also combine logical expressions, though watch for operator precedence:

```python
d1 = d[(d.x > 10) & (d.x < 20)]
```

Of course, chaining is also allowed:

```python
d1 = d[dx > 10]
d2 = d1[d1.x < 20]
```

And `d2` will be identical to d1 of the last example.

The basic 4 binary math operators work as well

```python
d1 = d.x/1000.0
```

Extension functions are supported:

```python
d1 = d.x.count()
```

And, much the same way, `numpy` functions are supported:

```python
import numpy as np
d1 = np.sin(d.x)
```

as well as some python function:

```python
d1 = abs(d.x)
```

Internally, this is rendered as `d.x.sin()`.

## Lambda functions and captured variables

It is possible to use lambda's that capture variables, allowing combinations of objects. For example:

```python
d.jets.map(lambda j: d.eles.map(lambda e: j.DeltaR(e)))
```

Would produce a stream of `DataFrame`'s for each jet with each electron. It is up to the backend how a function like `map` is used (and of course `DeltaR`). Further, the backend must run the parsing as arguments can be arbitrary, so `dataframe_expressions` can't figure out the meaning on its own. The function `map` here, for example, has no special meaning in this library.

## Backend Functions

Sometimes the backend defines some functions which are directly callable. For example, `DataR` which might take several parameters. With some hints, these are encoded as direct function calls in the final `ast`:

```python
from dataframe_expressions import user_func

@user_func
def calc_it (pt1: float) -> float:
    assert False, 'Should never be called'

calced = calc_it(d.jets.pt)
```

In this case, `calced` would be expected to be a column of jet `pt`'s that were all put together.

## Filter Functions

If a filter gets to be too complex (the code between a `[` and a `]`), then it might be simpler to put it in a separate function.

```python
def good_jet(j):
    (j.pt > 30) & (abs(j.eta) < 2.4)

good_jets_pt = df.jets[good_jet].pt
```

## Adding computed expressions to the Data Model

There are two ways to define _new columns_ in the data model. In both cases the idea is that a new computation expression can replace the old one. The first method looks more `pandas` like, and the second one looks more like a regular expression substitution. The second method is quite general, powerful, and thus quite likely to take your foot off. Not sure it will survive the prototype.

### Adding a new computed expression column

This is the most common way to add a new expression to the data model: one provides a lambda function that is computed during rendering by `dataframe_expressions`:

```python
df.jets['ptgev'] = lambda j: j.pt / 1000.0
```

By default the argument is everything that proceeds the brackets - in this case `df.jets`. All the rules about capturing variables apply here, so it is possible to add a set of tracks near the jet, for example, using this (as long as it is implemented by the backend). For example:

```python
def near(tks, j):
    return tks[tks.map(lambda t: DeltaR(t, j) < 0.4)]

df.jets['tracks'] = lambda j: near(df.tracks, j)

# This will now get you the number of tracks near each jet:
df.jets.tracks.Count()
```

The above assumes a lot of backend implementation: `DeltaR`, `map`, `Count`, along with the detector data model that has jets and tracks, but hopefully gives one an idea of the power available.

### Replacing the contents of a column

It is possible to graft one part of the data model into another part of the data model, when necessary. It can be done with the above lambda expression as well, but this is a short cut:

```python
df.jets['mcs'] = df.mcs[df.mcs.pdgId == 11]

how_many_mcs = df.jets.mcs.Count()
```

Though that would have the same number for every jet.

Because of the way rendering works, the following also does what you expect:

```python
df.jets['ptgev'] = df.jets.pt/1000.0

jetpt_in_gev = df.jets.ptgev
```

This is because in the current `dataframe_expressions` model, every single appearance of a common expression, like `df.jets` corresponds to the same same set of jets. In sort, implied iterators are common here. In this prototype it isn't obvious this should be here.

All of this will work even through a filter, as you might expect:

```python
df.jets['ptgev'] = df.jets.pt / 1000.0

jetpt_in_gev = df.jets[df.jets.ptgev > 30].ptgev
```

The prototype implementation is particularly fragile - but that is due to poor design rather than a technical limitation.

### Adding to the data model using objects

Another way to do this is build an object. For example, lets say you want to make it easy to do 3-vector operations. You might write something like this:

```python
class vec(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, df)

    @property
    def x(self) -> DataFrame:
        return self.x
    @property
    def y(self) -> DataFrame:
        return self.y
    @property
    def z(self) -> DataFrame:
        return self.z

    @property
    def xy(self) -> DataFrame:
        import numpy as np
        return np.sqrt(self.x*self.x + self.y*self.y)
```

Now you can write `v.xy` and you have the `L_xy` distance from the origin. It is also possible to implement vector operations. This library doesn't help you with that, but it isn't difficult.

You can add the class decorator `exclusive_class` if you only want the supplied properties to be available (so `v.zz` would cause an error).

The extra work to support this is almost trivial - see test cases, even one with vector addition, in the file `test_object.py` for further examples.

### Adding to the data model using an Alias

This is a simple feature which allows you to invent short hand for more complex expressions. This makes it easy to use. Further, the backend never knows about these short-hand scripts - they are just substituted in on the fly as the DAG is built. For example, in the ATLAS experiment I to access jet pT in GeV i need to always divide by 1000. So:

```python
define_alias('', 'pt', lambda o: o.pt / 1000.0)
```

Now if one enters `d.jets.pt`, the backend will see it as if I typed `df.jets.pt/1000.0`. The same can be done for collections. For example:

```python
define_alias('.', 'eles', lambda e: e.Electrons("Electrons"))
```

And when one enters `d.eles.pt` the backend will see `df.Electrons("Electrons").pt / 1000.0`.

The aliases can reference each other (though no recursion is allowed), so fairly complex expressions can be built up. This library's alias resolution is quite simple (it is a prototype). Matching is possible. For example, if the first argument is a `.`, then only references directly off the dataframe are translated. This feature could be used to define a _personality_ module for an analysis for an experiment.

## Usage with a backend

While the above shows you want the library can track, it says nothing about how you use it. The following steps are necessary.

1. Subclass `dataframe_expressions.DataFrame` with your class. Make sure you initialize the `DataFrame` sub class. However, no need to pass any arguments. For this discussion lets call this `MyDF`

1. Users build expression as you would expect, `df = MyDF(...)`, and `df1 = df.jets[df.jets.pt > 10]`

1. Users trigger rendering of the expression in your library in some way that makes sense, `get_data(df1)`

1. When you get control with the top level `DataFrame` expression, you can now do the following to render it:

```python
from dataframe_expressions import render
expression = render(df1)
```

`expression` is an `ast.AST` that describes what is being looked at (e.g. `df.jets.pt`). If the expression is something like `df.jets.pt` then the ast is a chain of python `ast.Attribute` nodes, and the bottom one will be a special `ast_Dataframe` object that contains a member `dataframe` which points to your original sub-classed `MyDF`.

If there are filters, there is another special ast object you need to be able to process, `ast_Filter`. For example, `df[df.met > 50].jets.pt`, will have `expression` starting with two `ast.Attribute` nodes, followed by a `ast_Filter` node. There are two members there, one is `expr` and in this case it will contain the `df`, or the `ast_Dataframe` that points to `df`. The second member is `filter` which points to an expression that is the filter. It should evaluate to true or false. As long as there is repeated phrase, like `df` in `df[df.met > 50].jets.pt` or `df.jets` in `df.jets[df.jets.count() == 2]`, they will point to the same `ast.AST` object - so you can use that in walking the tree to recognize the same expression(s).

TODO: This example is a bit sloppy, as we have the usual problem of how to parse at collection vs leaf level. When we have something working, come back and make this more clean.

## Technology Choices

Not sure these are the right thing, but...

- Using the python `ast` module to record expressions. Mostly because it is already complete and there are nice visitor objects that make walking it easy. Down side is that python does change the ast every few versions.

- An attribute on DataFrame refers to some data. A method call, however, does not refer to data. So, you can say `d.pt` to get at the pt, but if you said `d.pt()` that would be "bad". The reason for this is so that we can add functions that do things in a fluent way. For example, `d.jets.count()` to count the number of jets. Or `d.jets[d.jets.pt > 100].count()` or similar. Really, the back end can interpret this, but the front-end semantics sort-of make this assumption.

## Architecture Questions

This isn't an exhaustive list. Just a list of some choices I had to make to get this off the ground.

- Should there be a `Column` and `Dataset`?
  - Yes - turns out we have rediscovered why there is a Mask and a column distinction in numpy. So the Column object is really a Mask object. This is bad naming, but hopefully for this prototype that won't make much of a difference. So we should definitely think a bit about why a Mask has to be treated differently from a `DataFrame` - it isn't intuitively obvious until you get into the code.
  - No - since things can return "bool" values and we don't know it because we have no type system, they are identical to a column, except we assume they are a df: `df[df.hasProdVtx & df.hasDecayVtx]`, for example.
  - We should get rid of the concept of a parent, dynamic, and replace it with ast_DataFrame - we have it in here already - so why not just stick to that rather than having both it and `p`.

- Should we allow for "&" and "|" as logical operators, redefining what they mean in python? numpy defines several logical operators which should translate, but those aren't implemented yet.

- I currently have a parent as "p" in the expression, but then we have a dataframe ast and column ast - which makes it not needed. Why not just convert to using the same thing to refer to a df in an ast?
  - Internally, the "parent" dataframe is represented as `p` - which means nothing can ever have a `p` object on it or all hell is likely to break loose. A very good argument for not doing it this way.

- For typing I do not know how to forward declare so I can use COlumn and DataFrame inside my method definitions. Static type checkers should pick this up for now by simple logic.

- Using BitAnd and BitOr for and and or - but should I use the logical and and or here to make it clear in the AST what we are talking about?

- What does `d1[d[d.x > 0].jets.pt > 20].pt` mean? Is this where we are hitting the limit of things? I'd say it means nothing and should create an error. Something like `d1[(d[d.x > 0].jets.pt > 20).count()].pt` works, however. TODO - make this sort of expression an error (the first of these two!) Actually even the above - what does that mean? Isn't the right way to do that is `d1[(d[d.x > 0].jets[d.jets.pt>0].count())]` or similar? Ugh. Ok - the thing to do for now is be strict, and we can add things which make life easier later.

- Sometimes functions are defined in places they make no sense. For example, the `abs` (or any `numpy` function) is defined always, even if your `DataFrame` represents a collection of jets. A reason to have `columns` and `collections` as different objects to help the user, and help editors guess possibilities.

- There should be no concept of `parent` in a `DataFrame`. The expression should be everything, and point to any referenced objects. This will be especially true if multiple root `DataFrame`'s are ever to be used.

- Is it important to define new columns using the '=' sign? e.g. `df.jets.ptgev = df.jets.pt/1000.0`?

- The rule that every expression that is the same implies the same implied iterator. That means the current code can't do 2 jets, for example. There are several ways to "fix" this, however, the biggest question: is this reasonable?

- The ability to have an `exclusive_object` is implemented at runtime - perhaps we can come up with a scheme where we just define objects and they "fit" in correctly? Thus editors, etc., would be able to tag this as a problem.
