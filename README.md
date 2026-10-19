# ComfyUI-Assert

Two nodes that work like `assert` statements: the condition says how things
*should* be. If it's true, the value passes through. If it's false, the
workflow stops and shows your error message.

Requires a ComfyUI version that includes the core **Math Expression** node
(it uses the same node API and the bundled `simpleeval` package).

## Install

Copy the `ComfyUI-Assert` folder into `ComfyUI/custom_nodes/` and restart ComfyUI.
Both nodes appear under **utilities → assert**.

## Assert(number)

| Socket / field | Description |
| --- | --- |
| **x** (input) | An INT or FLOAT to check and pass through. |
| **y, z, a, b, …** (inputs) | Extra INT/FLOAT/BOOLEAN values the test can use. A new slot appears each time you connect the last one (up to 26 variables in total, x through w). |
| **test** | A Math Expression-style expression that should be true, e.g. `x % y == 0`, `x >= 0 and x <= 1`. Supports the same functions as Math Expression (`abs`, `round`, `floor`, `sqrt`, `min`, `max`, …) plus `values`, a list of all inputs. |
| **error_message** | Shown if the test is false. `{x}`, `{y}`, etc. are replaced with input values; `{x:.3f}`-style formatting works too. Use `{{` and `}}` for literal braces. |
| **x as int** (output) | x itself if it's an INT; otherwise `int(x)`, which truncates toward zero. |
| **x as float** (output) | x itself if it's a FLOAT; otherwise `float(x)`. |

The default test, `x % y == 0`, checks whether x is divisible by y and assumes
both are integers. Replace it with your own test; for floats, something like
`abs(x - round(x)) < 0.001` is usually more appropriate than `%`.

If the test refers to an input that isn't connected, the node stops with an
error saying so.

## Assert

| Socket / field | Description |
| --- | --- |
| **x** (input) | Any value. |
| **condition** (input) | A BOOLEAN that should be true. Socket only, no toggle. |
| **error_message** | Shown if condition is false. `{x}` is replaced with the input value. |
| **x** (output) | x, unchanged. Its type follows whatever is connected to the input. |
