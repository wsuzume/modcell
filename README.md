# modcell

`modcell` enables a Jupyter notebook cell as a module. It allows you to import a cell from another ipynb file by using `modcell` keyword.

# Usage

`modcell` searches `ipynb` files registered in `sys.path`. `modcell` identifies `# modcell` comment in top of a cell and imports it as a module.

# Installation

```
pip install modcell
```

# How to use modcell


You import the modecell in a file where you import a cell from another ipynb file.

For example in hello.ipynb:

```python
import modcell as mods

import test_module as mod

x = mod.TestModule()
x.hello()
```

In test_module.ipynb:

```python
# modcell
class TestModule:
    def __init__(self):
        pass

    def hello(self):
        print('Hello from TestModule')
```

Output:
```
Hello from TestModule
```

## Importing from a subdirectory

You can import a file from a sub-directory:

```python
from mydir import sub_file as mod

x = mod.SubTestModule()
x.hello()
```

`sub_file` under `mydir`:

```python
# modcell
class SubTestModule:
    def __init__(self):
        pass

    def hello(self):
        print('Hello from SubTestModule')
```

Output:
```
Hello from SubTestModule
```

## Importing from other directory

Add the directory path to `sys.path`.

In sub_receiver.ipynb in parent directory:

```python
import sys
sys.path.append('..')

import modcell as mods

import test_module as mod

x = mod.TestModule()
x.hello()
```

Output:
```
Hello from TestModule
```
