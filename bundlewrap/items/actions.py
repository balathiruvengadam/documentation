# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from bundlewrap.exceptions import ActionFailure, BundleError
from bundlewrap.items import format_comment, Item
from bundlewrap.utils import Fault
from bundlewrap.utils.ui import io
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import blue, bold, wrap_question


class Action(Item):
    """
    A command that is run on a node.
    """
    BUNDLE_ATTRIBUTE_NAME = 'actions'
    ITEM_ATTRIBUTES = {
        'command': None,
        'data_stdin': None,
        'expected_stderr': None,
        'expected_stdout': None,
        'expected_return_code': 0,
        'interactive': None,
    }
    ITEM_TYPE_NAME = 'action'
    REQUIRED_ATTRIBUTES = ['command']

    def _get_result(
        self,
        autoskip_selector="",
        my_soft_locks=(),
        other_peoples_soft_locks=(),
        interactive=False,
        interactive_default=True,
    ):

        if self.covered_by_autoskip_selector(autoskip_selector):
            io.debug(_(
                "autoskip matches {item} on {node}"
            ).format(item=self.id, node=self.node.name))
            return (self.STATUS_SKIPPED, [_("cmdline")])

        if self._skip_with_soft_locks(my_soft_locks, other_peoples_soft_locks):
            return (self.STATUS_SKIPPED, [_("soft locked")])

        if interactive is False and self.attributes['interactive'] is True:
            return (self.STATUS_SKIPPED, [_("interactive only")])

        if self.triggered and not self.has_been_triggered:
            io.debug(_("skipping {} because it wasn't triggered").format(self.id))
            return (self.STATUS_SKIPPED, [_("no trigger")])

        if self.unless:
            with io.job(_("  {node}  {bundle}  {item}  checking 'unless' condition...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            )):
                unless_result = self.bundle.node.run(
                    self.unless,
                    may_fail=True,
                )
            if unless_result.return_code == 0:
                io.debug(_("{node}:{bundle}:action:{name}: failed 'unless', not running").format(
                    bundle=self.bundle.name,
                    name=self.name,
                    node=self.bundle.node.name,
                ))
                return (self.STATUS_SKIPPED, ["unless"])

        question_body = ""
        if self.attributes['data_stdin'] is not None:
            question_body += "<" + _("data") + "> | "
        question_body += self.attributes['command']
        if self.comment:
            question_body += format_comment(self.comment)

        if (
            interactive and
            self.attributes['interactive'] is not False and
            not io.ask(
                wrap_question(
                    self.id,
                    question_body,
                    _("Run action {}?").format(
                        bold(self.name),
                    ),
                    prefix="{x} {node} ".format(
                        node=bold(self.node.name),
                        x=blue("?"),
                    ),
                ),
                interactive_default,
                epilogue="{x} {node}".format(
                    node=bold(self.node.name),
                    x=blue("?"),
                ),
            )
        ):
            return (self.STATUS_SKIPPED, [_("interactive")])
        try:
            self.run()
            return (self.STATUS_ACTION_SUCCEEDED, None)
        except ActionFailure as exc:
            return (self.STATUS_FAILED, [str(exc)])

    def apply(self, *args, **kwargs):
        return self.get_result(*args, **kwargs)

    def cdict(self):
        raise AttributeError(_("actions don't have cdicts"))

    def get_result(self, *args, **kwargs):
        self.node.repo.hooks.action_run_start(
            self.node.repo,
            self.node,
            self,
        )
        start_time = datetime.now()

        status_code = self._get_result(*args, **kwargs)

        self.node.repo.hooks.action_run_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status=status_code[0],
        )

        return status_code

    def run(self):
        if self.attributes['data_stdin'] is not None:
            data_stdin = self.attributes['data_stdin']
            # Allow users to use either a string/unicode object or raw
            # bytes -- or Faults.
            if isinstance(data_stdin, Fault):
                data_stdin = data_stdin.value
            if type(data_stdin) is not bytes:
                data_stdin = data_stdin.encode('UTF-8')
        else:
            data_stdin = None

        with io.job(_("  {node}  {bundle}  {item}  running...").format(
            bundle=self.bundle.name,
            item=self.id,
            node=self.node.name,
        )):
            result = self.bundle.node.run(
                self.attributes['command'],
                data_stdin=data_stdin,
                may_fail=True,
            )

        if self.attributes['expected_return_code'] is not None and \
                not result.return_code == self.attributes['expected_return_code']:
            raise ActionFailure(_("wrong return code: {}").format(result.return_code))

        if self.attributes['expected_stderr'] is not None and \
                result.stderr_text != self.attributes['expected_stderr']:
            raise ActionFailure(_("wrong stderr"))

        if self.attributes['expected_stdout'] is not None and \
                result.stdout_text != self.attributes['expected_stdout']:
            raise ActionFailure(_("wrong stdout"))

        return result

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('interactive', None) not in (True, False, None):
            raise BundleError(_(
                "invalid interactive setting for action '{item}' in bundle '{bundle}'"
            ).format(item=item_id, bundle=bundle.name))
