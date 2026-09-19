Example prompt for the write step. The real prompt lives in the private config repo.

You will be given a list of facts, each already assigned a placeholder token in curly braces
(for example {{run1:fred.us10y:0}}). Write one short, plain paragraph for the named section
using only these facts. Refer to every number or quote strictly by its placeholder token —
never write the value, the quote, or any other number yourself. Do not add facts, context or
opinions that weren't given to you. Return JSON that matches the schema.
