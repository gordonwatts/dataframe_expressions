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

NO CLUE... Yet.

## Technology Choices

Not sure these are the right thing, but...

- Using the python `ast` module to record expressions. Mostly because it is already complete and there are nice visitor objects that make walking it easy. Down side is that python does change the ast every few versions.

- An attribute on DataFrame refers to some data. A method call, however, does not refer to data. So, you can say `d.pt` to get at the pt, but if you said `d.pt()` that would be "bad". The reason for this is so that we can add functions that do things in a fluent way. For example, `d.jets.count()` to coune the number of jets. Or `d.jets[d.jets.pt > 100].count()` or similar. Really, the back end can interpret this, but the front-end semantics sort-of make this assumption.

## Architecture Questions

This isn't an exhaustive list. Just a list of some choices I had to make to get this off the ground.

- Should there be a `Column` and `Dataset`?

- Should we allow for "&" and "|" as logical operators, redefining what they mean in python? numpy defines several logical operators which should translate, but those aren't implemented yet.

- I currently have a parent as "p" in the expression, but then we have a dataframe ast and column ast - which makes it not needed. Why not just convert to using the same thing to refer to a df in an ast?

- For typing I do not know how to forward declare so I can use COlumn and DataFrame inside my method definitions. Static type checkers should pick this up for now by simple logic.

- Using BitAnd and BitOr for and and or - but should I use the logical and and or here to make it clear in the AST what we are talking about?
