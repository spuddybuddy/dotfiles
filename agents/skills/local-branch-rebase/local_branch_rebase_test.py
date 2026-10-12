#!/usr/bin/env python3
"""Unit tests for local_branch_rebase.py."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from unittest import mock

import local_branch_rebase as lbr


def _git(repo: str, *args: str) -> str:
    res = subprocess.run(
        ["git"] + list(args),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return res.stdout.strip()


class LocalBranchRebaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = self.tmpdir.name
        _git(self.repo, "init", "-b", "main")
        _git(self.repo, "config", "user.name", "Test User")
        _git(self.repo, "config", "user.email", "test@chromium.org")

        # Initial commit on main (c1)
        self._commit_file("README.md", "base\n", "Initial commit on main")
        self.c1_main = _git(self.repo, "rev-parse", "HEAD")

        # Advance main to c2
        self._commit_file("main_only.txt", "main update\n", "Advance main")
        self.c2_main = _git(self.repo, "rev-parse", "HEAD")

        # Create lkgr at c2 and advance it to c3
        _git(self.repo, "checkout", "-b", "lkgr", "main")
        self._commit_file("lkgr_only.txt", "lkgr update\n", "Advance lkgr")
        self.c3_lkgr = _git(self.repo, "rev-parse", "HEAD")

        # Return to c1 to create an untracked feature branch (simulating plain `git checkout -b`)
        _git(self.repo, "checkout", "-b", "my-feature", self.c1_main)
        self._commit_file("feature.cc", "int x = 1;\n", "Add feature")
        self.feature_orig = _git(self.repo, "rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _commit_file(self, relpath: str, content: str, message: str) -> str:
        full_path = os.path.join(self.repo, relpath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        _git(self.repo, "add", relpath)
        _git(self.repo, "commit", "-m", message)
        return _git(self.repo, "rev-parse", "HEAD")

    def test_default_rebase_onto_main_sets_tracking_and_base_config(self) -> None:
        result = lbr.rebase_and_update_branch(
            cwd=self.repo,
            offline=True,
        )
        self.assertEqual(result.branch, "my-feature")
        self.assertEqual(result.upstream, "main")
        self.assertEqual(result.upstream_sha, self.c2_main)
        self.assertNotEqual(result.new_head, self.feature_orig)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD^"), self.c2_main)

        self.assertEqual(_git(self.repo, "config", "branch.my-feature.remote"), ".")
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.merge"), "refs/heads/main"
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.base"), self.c2_main
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.base-upstream"),
            "refs/heads/main",
        )

    def test_switch_to_branch_and_rebase_onto_lkgr(self) -> None:
        # Checkout main first so script must switch to `my-feature` before rebasing onto `lkgr`
        _git(self.repo, "checkout", "main")
        result = lbr.rebase_and_update_branch(
            cwd=self.repo,
            branch="my-feature",
            upstream="lkgr",
            offline=True,
        )
        self.assertEqual(result.switched_from, "main")
        self.assertEqual(
            _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"), "my-feature"
        )
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD^"), self.c3_lkgr)
        self.assertEqual(_git(self.repo, "config", "branch.my-feature.remote"), ".")
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.merge"), "refs/heads/lkgr"
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.base"), self.c3_lkgr
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.base-upstream"),
            "refs/heads/lkgr",
        )

    def test_unstack_from_parent_feature_branch_onto_other_local_branch(self) -> None:
        # Create parent-branch with a commit not on main or lkgr
        _git(self.repo, "checkout", "-b", "parent-branch", self.c1_main)
        parent_sha = self._commit_file("parent.cc", "parent\n", "Parent commit")

        # Stack child-branch on parent-branch and set depot_tools base metadata
        _git(self.repo, "checkout", "-b", "child-branch", "parent-branch")
        self._commit_file("child.cc", "child\n", "Child commit")
        _git(self.repo, "config", "branch.child-branch.remote", ".")
        _git(
            self.repo,
            "config",
            "branch.child-branch.merge",
            "refs/heads/parent-branch",
        )
        _git(self.repo, "config", "branch.child-branch.base", parent_sha)
        _git(
            self.repo,
            "config",
            "branch.child-branch.base-upstream",
            "refs/heads/parent-branch",
        )

        # Create another local branch `new-parent` off main
        _git(self.repo, "checkout", "-b", "new-parent", "main")
        new_parent_sha = self._commit_file("new_parent.cc", "new\n", "New parent")

        # Rebase `child-branch` onto `new-parent`: should transplant ONLY child.cc (not parent.cc!)
        result = lbr.rebase_and_update_branch(
            cwd=self.repo,
            branch="child-branch",
            upstream="new-parent",
            offline=True,
        )
        self.assertEqual(result.used_onto_base, parent_sha)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD^"), new_parent_sha)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "parent.cc")))
        self.assertTrue(os.path.exists(os.path.join(self.repo, "child.cc")))
        self.assertTrue(os.path.exists(os.path.join(self.repo, "new_parent.cc")))
        self.assertEqual(
            _git(self.repo, "config", "branch.child-branch.merge"),
            "refs/heads/new-parent",
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.child-branch.base"), new_parent_sha
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.child-branch.base-upstream"),
            "refs/heads/new-parent",
        )

    def test_syncs_and_preserves_gerrit_config_keys(self) -> None:
        _git(self.repo, "config", "branch.my-feature.gerritissue", "8546218")
        _git(
            self.repo,
            "config",
            "branch.my-feature.gerritserver",
            "https://chromium-review.googlesource.com",
        )
        _git(self.repo, "config", "branch.my-feature.gerritpatchset", "3")
        _git(
            self.repo,
            "config",
            "branch.my-feature.gerritsquashhash",
            "1111111111111111111111111111111111111111",
        )
        _git(
            self.repo,
            "config",
            "branch.my-feature.last-upload-hash",
            self.feature_orig,
        )

        with mock.patch.object(
            lbr,
            "query_gerrit_current_revision",
            return_value=(4, "2222222222222222222222222222222222222222"),
        ):
            result = lbr.rebase_and_update_branch(
                cwd=self.repo,
                branch="my-feature",
                upstream="main",
                offline=False,
            )

        self.assertTrue(result.gerrit_synced)
        self.assertEqual(_git(self.repo, "config", "branch.my-feature.gerritissue"), "8546218")
        self.assertEqual(_git(self.repo, "config", "branch.my-feature.gerritpatchset"), "4")
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.gerritsquashhash"),
            "2222222222222222222222222222222222222222",
        )
        self.assertEqual(
            _git(self.repo, "config", "branch.my-feature.last-upload-hash"),
            self.feature_orig,
        )

    def test_dry_run_makes_no_mutations(self) -> None:
        result = lbr.rebase_and_update_branch(
            cwd=self.repo,
            branch="my-feature",
            upstream="lkgr",
            offline=True,
            dry_run=True,
        )
        self.assertTrue(result.dry_run)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), self.feature_orig)
        self.assertIsNone(lbr.get_branch_config_value(self.repo, "my-feature", "base"))


if __name__ == "__main__":
    unittest.main()
