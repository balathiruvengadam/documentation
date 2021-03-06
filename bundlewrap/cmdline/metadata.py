# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from json import dumps

from ..metadata import MetadataJSONEncoder, value_at_key_path
from ..utils import Fault
from ..utils.cmdline import get_node, get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, force_text, mark_for_translation as _, red
from ..utils.ui import io, page_lines


def bw_metadata(repo, args):
    if args['table']:
        if not args['keys']:
            io.stdout(_("{x} at least one key is required with --table").format(x=red("!!!")))
            exit(1)
        target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
        key_paths = [path.strip().split(" ") for path in " ".join(args['keys']).split(",")]
        table = [[bold(_("node"))] + [bold(" ".join(path)) for path in key_paths], ROW_SEPARATOR]
        for node in target_nodes:
            values = []
            for key_path in key_paths:
                try:
                    value = value_at_key_path(node.metadata, key_path)
                except KeyError:
                    value = red(_("<missing>"))
                if isinstance(value, (dict, list, tuple)):
                    value = ", ".join([str(item) for item in value])
                elif isinstance(value, set):
                    value = ", ".join(sorted(value))
                elif isinstance(value, (bool, float, int, Decimal, Fault)):
                    value = str(value)
                values.append(value)
            table.append([bold(node.name)] + values)
        page_lines(render_table(table))
    else:
        node = get_node(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
        for line in dumps(
            value_at_key_path(node.metadata, args['keys']),
            cls=MetadataJSONEncoder,
            indent=4,
            sort_keys=True,
        ).splitlines():
            io.stdout(force_text(line))
