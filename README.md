# dataframe_expressions
 Simple accumulating of expressions for dataframe operations

## Expression Samples

You start with a top level data frame:

```
from dataframe_expressions import DataFrame
d = DataFrame()
```

Now you can mask it with simple operations:

```
d1 = d[d.x > 10]
```

The operators `<,>, <=, >=, ==,` and `!=` are all supported. You can also combine logical expressions, though watch for operator precidence:

```
d1 = d[(d.x > 10) & (d.x < 20)]
```

Of cousre, chaining is also allowed:

```
d1 = d[dx > 10]
d2 = d1[d1.x < 20]
```

And `d2` will be identical to d1 of the last example.

The basic 4 binary math operators work as well

```
d1 = d.x/1000.0
```

Extension functions are supported:

```
d1 = d.x.count()
```

And, much the same way, `numpy` functions are supported:

```
import numpy as np
d1 = np.sin(d.x)
```

Internally, this is rendered as `d.x.sin()`.

## Usage with a backend

While the above shows you want the libaray can track, it says nothing about how you use it. The following steps are necessary.

1. Subclass `dataframe_expressions.DataFrame` with your class. Make sure you initalize the `DataFrame` sub class. However, no need to pass any arguments. For this discussion lets call this `MyDF`

1. Users build expression as you would expect, `df = MyDF(...)`, and `df1 = df.jets[df.jets.pt > 10]`

1. Users trigger rendering of the expression in your libaray in some way that makes sense, `get_data(df1)`

1. When you get control with the toplevel `DataFrame` expression, you can now do the following to render it:

```
from dataframe_expressions import render
expression, filter = render(df1)
```

`expression` is an `ast.AST` that describes what is being looked at (e.g. `df.jets.pt`). `filter` tells you what rows of the dataframe to look at (e.g. `df.jets.pt > 10 & df.jets.eta.abs() < 1.2`). In each of these there will be custom `ast.AST` nodes called `ast_DataFrame`. If you look at the `dataframe` member of that `ast.AST` node, you'll get back your originally created. You can then use python's `ast` tools to move through the expression parsing and performing the actions as needed.

TODO: This example is a bit sloppy, as we have the usual problem of how to parse at collection vs leaf level. When we have something working, come back and make this more clean.

## Technology Choices

Not sure these are the right thing, but...

- Using the python `ast` module to record expressions. Mostly because it is already complete and there are nice visitor objects that make walking it easy. Down side is that python does change the ast every few versions.

- An attribute on DataFrame refers to some data. A method call, however, does not refer to data. So, you can say `d.pt` to get at the pt, but if you said `d.pt()` that would be "bad". The reason for this is so that we can add functions that do things in a fluent way. For example, `d.jets.count()` to coune the number of jets. Or `d.jets[d.jets.pt > 100].count()` or similar. Really, the back end can interpret this, but the front-end semantics sort-of make this assumption.

## Architecture Questions

This isn't an exhaustive list. Just a list of some choices I had to make to get this off the ground.

- Should there be a `Column` and `Dataset`?
    - Yes - turns out we have rediscovered why there is a Mask and a column distinction in numpy. So the Column object is really a Mask object. This is bad naming, but hopefully for this prototype that won't make much of a difference. So we should definately think a bit about why a Mask has to be treated differently from a `DataFrame` - it isn't intuitively obvious until you get into the code.

- Should we allow for "&" and "|" as logical operators, redefining what they mean in python? numpy defines several logical operators which should translate, but those aren't implemented yet.

- I currently have a parent as "p" in the expression, but then we have a dataframe ast and column ast - which makes it not needed. Why not just convert to using the same thing to refer to a df in an ast?
   - Internally, the "parent" dataframe is represented as `p` - which means nothing can ever have a `p` object on it or all hell is likely to break loose. A very good argument for not doing it this way.

- For typing I do not know how to forward declare so I can use COlumn and DataFrame inside my method definitions. Static type checkers should pick this up for now by simple logic.

- Using BitAnd and BitOr for and and or - but should I use the logical and and or here to make it clear in the AST what we are talking about?

