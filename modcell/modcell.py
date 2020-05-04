import io, os, sys, types, importlib

from IPython import get_ipython
from nbformat import read
from IPython.core.interactiveshell import InteractiveShell

import re

__pg_mgcmd = re.compile('\s*[!%]')
__pg_tag = re.compile('\s*#\s*(?P<cmd>\w+)\s*:\s*(?P<tag>\w+)')
__pg = re.compile('\s*#\s*(?P<cmd>\w+)')


def parseCodeCell(cell):
    buf = io.StringIO(cell.source)
    cmd = None
    tag = None
    code_lines = []

    reading_content = False
    for line in buf.readlines():
        m = __pg_mgcmd.match(line)
        if m is not None:
            # IPython magic commands
            continue
        if reading_content:
            code_lines.append(line)
        else:
            m = __pg_tag.match(line)
            if m is not None:
                cmd = m.group('cmd')
                tag = m.group('tag')
                reading_content = True
            m = __pg.match(line)
            if m is not None:
                cmd = m.group('cmd')
                reading_content = True

    return cmd, tag, ''.join(code_lines)

def extractCells(path, cell_type='code'):
    # load the notebook object
    with io.open(path, 'r', encoding='utf-8') as f:
        nb = read(f, 4)

    ret = []
    for cell in nb.cells:
        if cell.cell_type == cell_type:
            ret.append(cell)
    return ret

class CodeCell:
    def __init__(self, path, cmd, tag, content):
        self.path = path
        self.cmd = cmd
        self.tag = tag
        self.content = content

    def exec(self, globals):
        # extra work to ensure that magics that would affect the user_ns
        # actually affect the notebook module's ns
        shell = InteractiveShell.instance()
        save_user_ns = shell.user_ns
        shell.user_ns = globals

        try:
            code = shell.input_transformer_manager.transform_cell(self.content)
            exec(code, globals)
        finally:
            shell.user_ns = save_user_ns

class ModCell:
    def __init__(self):
        self.cells = {}

    def source(self, path, cmd='modcell', tag=None):
        if path not in self.cells:
            self.cells[path] = []

        for cell in extractCells(path):
            cell_cmd, cell_tag, content = parseCodeCell(cell)
            if cmd is None or cmd == cell_cmd:
                if tag is None or tag == cell_tag:
                    self.cells[path].append(CodeCell(path, cmd, tag, content))

    def _exec(self, globals, key=None):
        if key is None:
            for k, cells in self.cells.items():
                for cell in cells:
                    cell.exec(globals)
            return

        if key not in self.cells:
            return

        for cell in self.cells[key]:
            cell.exec(globals)
        return


    def _import(self, fullname, path=None, cmd='modcell', tag=None):
        spec = _default_finder.find_spec(fullname, path)
        if spec is None:
            return

        mod = spec.loader.create_module(spec)
        return spec.loader.exec_module(mod, cmd=cmd, tag=tag, modcell=self)

    def compile(self, out, source_info=True):
        for path, cells in self.cells.items():
            if source_info:
                out.write(f'# {path} ---------\n')
                out.write('# ---\n')

            for cell in cells:
                out.write('\n')
                out.write(cell.content)
                out.write('\n')
                if source_info:
                    out.write('\n# ---\n')

            if source_info:
                out.write(f'# --------- {path}\n')


# original codes can be seen in "https://jupyter-notebook.readthedocs.io/en/stable/examples/Notebook/Importing%20Notebooks.html"

def find_notebook(fullname, path=None):
    """find a notebook, given its fully qualified name and an optional path

    This turns "foo.bar" into "foo/bar.ipynb"
    and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
    does not exist.
    """
    name = fullname.rsplit('.', 1)[-1]
    if not path:
        path = ['']
    for d in path:
        nb_path = os.path.join(d, name + ".ipynb")
        if os.path.isfile(nb_path):
            return nb_path
        # let import Notebook_Name find "Notebook Name.ipynb"
        nb_path = nb_path.replace("_", " ")
        if os.path.isfile(nb_path):
            return nb_path

class NotebookLoader(object):
    """Module Loader for Jupyter Notebooks"""
    def __init__(self):
        pass

    def create_module(self, spec):
        mod = types.ModuleType(spec.name)
        mod.__file__ = spec.origin
        mod.__loader__ = self
        mod.__dict__['get_ipython'] = get_ipython
        sys.modules[spec.name] = mod

        return mod

    def exec_module(self, mod, cmd='modcell', tag=None, modcell=None):
        if modcell is None:
            modcell = _default_modcell
        # load the notebook object
        modcell.source(mod.__file__, cmd=cmd, tag=tag)

        modcell._exec(mod.__dict__, key=mod.__file__)

        return mod

class NotebookFinder(importlib.abc.MetaPathFinder):
    """Module finder that locates Jupyter Notebooks"""
    def __init__(self):
        self.loaders = {}

    def find_spec(self, fullname, path=None, target=None):
        nb_path = find_notebook(fullname, path)
        if not nb_path:
            return

        key = path
        if path:
            # lists aren't hashable
            key = os.path.sep.join(path)

        if key not in self.loaders:
            self.loaders[key] = NotebookLoader()

        return importlib.machinery.ModuleSpec(name=fullname,
                                                loader=self.loaders[key],
                                                origin=nb_path)

    def invalidate_caches(self):
        return None

def _import(fullname, path=None, cmd='modcell', tag=None):
    spec = _default_finder.find_spec(fullname, path)
    if spec is None:
        return

    mod = spec.loader.create_module(spec)
    return spec.loader.exec_module(mod, cmd=cmd, tag=tag)

def compile(out, source_info=True):
    _default_modcell.compile(out, source_info)

def default():
    return _default_modcell

_default_modcell = ModCell()
_default_finder = NotebookFinder()
sys.meta_path.append(_default_finder)
