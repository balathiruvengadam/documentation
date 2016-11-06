# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os import environ

from bundlewrap.utils.testing import host_os, make_repo, run


def test_any_content_create(tmpdir):
    if not environ.get('TRAVIS', False):
        # only run this test on Travis
        return

    make_repo(
        tmpdir,
        bundles={
            "test": {
                'groups': {
                    "bwtestgroup1": {
                        'gid': 1234,
                    },
                    "bwtestgroup2": {
                        'gid': 4321,
                    },
                },
                'users': {
                    "bwtestuser": {
                        'uid': 1234,
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )

    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0

    make_repo(
        tmpdir,
        bundles={
            "test": {
                'groups': {
                    "bwtestgroup1": {
                        'gid': 1234,
                    },
                    "bwtestgroup2": {
                        'gid': 4321,
                    },
                },
                'users': {
                    "bwtestuser": {
                        'uid': 1234,
                        'groups': ["bwtestgroup2"],
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )

    stdout, stderr, rcode = run("bw apply -i localhost | yes", path=str(tmpdir))
    assert rcode == 0
