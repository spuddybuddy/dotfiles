#!/usr/bin/env python3
"""Unit tests for gerrit_comment_reply.py."""

import json
import unittest
from unittest import mock

import gerrit_comment_reply as gcr


class GerritCommentReplyTest(unittest.TestCase):
    def setUp(self):
        self.sample_comments = {
            "foo/bar.cc": [
                {
                    "id": "c_root",
                    "line": 42,
                    "range": {
                        "start_line": 42,
                        "start_character": 0,
                        "end_line": 42,
                        "end_character": 10,
                    },
                    "side": "REVISION",
                    "patch_set": 2,
                    "message": "Please fix this.",
                    "unresolved": True,
                },
                {
                    "id": "c_child_no_line",
                    "in_reply_to": "c_root",
                    "patch_set": 2,
                    "message": "Why?",
                    "unresolved": True,
                },
                {
                    "id": "c_file_level",
                    "patch_set": 1,
                    "message": "General file comment.",
                    "unresolved": False,
                },
            ],
            "/PATCHSET_LEVEL": [
                {
                    "id": "c_patchset",
                    "patch_set": 2,
                    "message": "LGTM",
                    "unresolved": False,
                }
            ],
        }

    def test_normalize_host(self):
        self.assertEqual(
            "https://chromium-review.googlesource.com",
            gcr.normalize_host("chromium-review.googlesource.com"),
        )
        self.assertEqual(
            "https://chromium-review.googlesource.com",
            gcr.normalize_host("https://chromium-review.googlesource.com/"),
        )

    def test_find_comment_by_id(self):
        file_path, comment = gcr.find_comment_by_id(self.sample_comments, "c_root")
        self.assertEqual("foo/bar.cc", file_path)
        self.assertIsNotNone(comment)
        self.assertEqual(42, comment["line"])

        file_path, comment = gcr.find_comment_by_id(self.sample_comments, "non_existent")
        self.assertIsNone(file_path)
        self.assertIsNone(comment)

    def test_get_comment_thread_context_direct_line(self):
        file_path, parent, context = gcr.get_comment_thread_context(
            self.sample_comments, "c_root"
        )
        self.assertEqual("foo/bar.cc", file_path)
        self.assertEqual(42, context["line"])
        self.assertEqual(2, context["patch_set"])
        self.assertEqual("REVISION", context["side"])
        self.assertIn("range", context)

    def test_get_comment_thread_context_inherited_from_ancestor(self):
        file_path, parent, context = gcr.get_comment_thread_context(
            self.sample_comments, "c_child_no_line"
        )
        self.assertEqual("foo/bar.cc", file_path)
        self.assertEqual(42, context["line"])
        self.assertEqual(2, context["patch_set"])
        self.assertEqual("REVISION", context["side"])
        self.assertIn("range", context)

    def test_get_comment_thread_context_file_level(self):
        file_path, parent, context = gcr.get_comment_thread_context(
            self.sample_comments, "c_file_level"
        )
        self.assertEqual("foo/bar.cc", file_path)
        self.assertNotIn("line", context)
        self.assertNotIn("range", context)
        self.assertEqual(1, context["patch_set"])

    def test_get_comment_thread_context_patchset_level(self):
        file_path, parent, context = gcr.get_comment_thread_context(
            self.sample_comments, "c_patchset"
        )
        self.assertEqual("/PATCHSET_LEVEL", file_path)
        self.assertNotIn("line", context)
        self.assertEqual(2, context["patch_set"])

    def test_build_comment_object_reply_inherits_line_and_range(self):
        item = {
            "reply_to": "c_root",
            "message": "Fixed!",
            "unresolved": False,
        }
        target_file, comment_obj, context = gcr.build_comment_object(
            item, self.sample_comments, "12345"
        )
        self.assertEqual("foo/bar.cc", target_file)
        self.assertEqual("c_root", comment_obj["in_reply_to"])
        self.assertEqual("Fixed!", comment_obj["message"])
        self.assertFalse(comment_obj["unresolved"])
        self.assertEqual(42, comment_obj["line"])
        self.assertIn("range", comment_obj)
        self.assertEqual("REVISION", comment_obj["side"])

    def test_build_comment_object_child_inherits_root_line(self):
        # Replying to a child comment that didn't have line set
        item = {
            "reply_to": "c_child_no_line",
            "done": True,
        }
        target_file, comment_obj, context = gcr.build_comment_object(
            item, self.sample_comments, "12345"
        )
        self.assertEqual("foo/bar.cc", target_file)
        self.assertEqual("c_child_no_line", comment_obj["in_reply_to"])
        self.assertEqual("Done", comment_obj["message"])
        self.assertFalse(comment_obj["unresolved"])
        self.assertEqual(42, comment_obj["line"])

    def test_build_comment_object_shortcuts(self):
        # Done shortcut
        _, obj_done, _ = gcr.build_comment_object(
            {"reply_to": "c_root", "done": True},
            self.sample_comments,
            "12345",
        )
        self.assertEqual("Done", obj_done["message"])
        self.assertFalse(obj_done["unresolved"])

        # Ack shortcut
        _, obj_ack, _ = gcr.build_comment_object(
            {"reply_to": "c_root", "ack": True},
            self.sample_comments,
            "12345",
        )
        self.assertEqual("Ack", obj_ack["message"])
        self.assertFalse(obj_ack["unresolved"])

    def test_build_comment_object_patchset_comment(self):
        target_file, comment_obj, _ = gcr.build_comment_object(
            {"patchset_comment": True, "message": "PTAL"},
            self.sample_comments,
            "12345",
        )
        self.assertEqual("/PATCHSET_LEVEL", target_file)
        self.assertEqual("PTAL", comment_obj["message"])
        self.assertNotIn("line", comment_obj)

    def test_build_comment_object_new_inline(self):
        target_file, comment_obj, _ = gcr.build_comment_object(
            {"file": "foo/bar.cc", "line": 100, "message": "New note"},
            self.sample_comments,
            "12345",
        )
        self.assertEqual("foo/bar.cc", target_file)
        self.assertEqual(100, comment_obj["line"])
        self.assertEqual("New note", comment_obj["message"])

    def test_build_comment_object_not_found(self):
        with self.assertRaises(ValueError):
            gcr.build_comment_object(
                {"reply_to": "unknown_id", "message": "Hi"},
                self.sample_comments,
                "12345",
            )

    def test_parse_batch_input_list(self):
        raw = [
            {"reply_to": "c_root", "message": "Done"},
            {"reply_to": "c_child_no_line", "ack": True},
        ]
        msg, items, extra = gcr.parse_batch_input(raw)
        self.assertIsNone(msg)
        self.assertEqual(2, len(items))
        self.assertEqual("c_root", items[0]["reply_to"])

    def test_parse_batch_input_dict_with_comments_list(self):
        raw = {
            "message": "Top level review",
            "tag": "autogenerated:review",
            "comments": [
                {"reply_to": "c_root", "done": True},
            ],
        }
        msg, items, extra = gcr.parse_batch_input(raw)
        self.assertEqual("Top level review", msg)
        self.assertEqual("autogenerated:review", extra.get("tag"))
        self.assertEqual(1, len(items))
        self.assertEqual("c_root", items[0]["reply_to"])

    def test_parse_batch_input_dict_with_comments_map(self):
        raw = {
            "comments": {
                "foo/bar.cc": [
                    {"in_reply_to": "c_root", "message": "Done"}
                ]
            }
        }
        msg, items, extra = gcr.parse_batch_input(raw)
        self.assertEqual(1, len(items))
        self.assertEqual("foo/bar.cc", items[0]["file"])
        self.assertEqual("c_root", items[0]["in_reply_to"])

    def test_parse_batch_input_mapping(self):
        raw = {
            "c_root": "Done",
            "c_child_no_line": {"message": "Ack", "unresolved": False},
        }
        msg, items, extra = gcr.parse_batch_input(raw)
        self.assertEqual(2, len(items))
        root_item = next(i for i in items if i["reply_to"] == "c_root")
        child_item = next(i for i in items if i["reply_to"] == "c_child_no_line")
        self.assertEqual("Done", root_item["message"])
        self.assertEqual("Ack", child_item["message"])
        self.assertFalse(child_item["unresolved"])

    @mock.patch("gerrit_comment_reply.call_gerrit_client")
    def test_create_draft(self, mock_client):
        mock_client.return_value = {"id": "d1"}
        draft_input = {
            "path": "foo/bar.cc",
            "line": 42,
            "message": "Draft comment",
            "in_reply_to": "c_root",
        }
        res = gcr.create_draft("https://host.example.com", "123", draft_input, revision="2")
        self.assertEqual({"id": "d1"}, res)
        mock_client.assert_called_once_with(
            "https://host.example.com",
            "rawapi",
            [
                "--path",
                "changes/123/revisions/2/drafts",
                "--method",
                "PUT",
                "--body",
                json.dumps(draft_input),
            ],
        )

    @mock.patch("gerrit_comment_reply.post_review")
    def test_publish_drafts(self, mock_post_review):
        mock_post_review.return_value = {}
        gcr.publish_drafts("https://host.example.com", "123", message="All done!", revision="current")
        mock_post_review.assert_called_once_with(
            "https://host.example.com",
            "123",
            {"drafts": "PUBLISH_ALL_REVISIONS", "message": "All done!"},
            revision="current",
        )


if __name__ == "__main__":
    unittest.main()

