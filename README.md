# dataframe_expressions
 Simple accumulating of expressions for dataframe operations

## Technology Choices

Not sure these are the right thing, but...

- Using the python `ast` module to record expressions. Mostly because it is already complete and there are nice visitor objects that make walking it easy. Down side is that python does change the ast every few versions.

- Should there be a `Column` and `Dataset`?

- Should we allow for "&" and "|" as logical operators, redefining what they mean in python?

- I currently have a parent as "p" in the expression, but then we have a dataframe ast and column ast - which makes it not needed. Why not just convert to using the same thing to refer to a df in an ast?

- For typing I do not know how to forward declare so I can use COlumn and DataFrame inside my method definitions. Static type checkers should pick this up for now by simple logic.