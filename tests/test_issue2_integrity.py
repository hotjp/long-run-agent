#!/usr/bin/env python3
"""
回归测试：GitHub issue #2 修复

覆盖的根因：
1. ID 分配用"任务数量+1"而非"最大序号+1" → 删除历史任务后新任务撞号
2. create_task_file 返回值被丢弃 → 模板损坏时任务进 task_list 但没有任务书
3. 读取时静默命中重复 ID → worker 拿到别的任务的任务书
4. 模板 YAML 语法错误被伪装成"模板不存在"
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lra.config import Config
from lra.task_manager import TaskManager
from lra.template_manager import TemplateManager


class TempProjectTestCase(unittest.TestCase):
    """在临时目录里建项目，避免污染真实工作区"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self._origin_cwd = os.getcwd()
        os.chdir(self.test_dir)
        Config.ensure_dirs()
        self.tm = TaskManager()
        self.tm.init_project("test-project", "task")

    def tearDown(self):
        os.chdir(self._origin_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def task_ids(self):
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        return [t["id"] for t in data["tasks"]]

    def md_path(self, task_id):
        return os.path.join(Config.get_tasks_dir(), f"{task_id}.md")


class TestIdAllocation(TempProjectTestCase):
    """ID 分配：永不撞号"""

    def test_sequential_ids_do_not_collide(self):
        for i in range(12):
            ok, task = self.tm.create(f"任务{i}")
            self.assertTrue(ok, task)
        ids = self.task_ids()
        self.assertEqual(len(ids), len(set(ids)), "批量创建产生了重复 ID")

    def test_id_not_reused_after_deletion(self):
        """核心回归：删除中间任务后，新任务不得复用被删的 ID"""
        self.tm.create("任务A")
        self.tm.create("任务B")
        self.tm.create("任务C")
        self.assertEqual(self.task_ids(), ["task_001", "task_002", "task_003"])

        self.assertTrue(self.tm.delete("task_002"))
        self.assertEqual(self.task_ids(), ["task_001", "task_003"])

        ok, task = self.tm.create("新任务")
        self.assertTrue(ok, task)

        # 新任务必须拿到一个全新的 ID，而不是撞上仍然存在的 task_003
        self.assertNotEqual(task["id"], "task_003")
        self.assertIn(task["id"], ["task_004", "task_005"])
        self.assertEqual(len(self.task_ids()), len(set(self.task_ids())), "新任务与存量撞号")

    def test_id_does_not_overwrite_existing_task_file(self):
        """task_list 里删掉了任务，但 tasks/ 下的 md 还在 → 不得覆盖它"""
        self.tm.create("任务A")
        self.tm.create("任务B")
        self.tm.delete("task_001")
        # task_001.md 仍在磁盘上（孤儿任务书）
        self.assertTrue(os.path.exists(self.md_path("task_001")))

        ok, task = self.tm.create("新任务")
        self.assertTrue(ok, task)
        self.assertNotEqual(task["id"], "task_001")

        # 原任务书内容未被覆盖
        with open(self.md_path("task_001"), encoding="utf-8") as f:
            self.assertIn("task_001", f.read())

    def test_subtask_ids_do_not_collide_after_deletion(self):
        """子任务 ID 同样不能因为删除而撞号"""
        self.tm.create("父任务")
        ok, parent = self.tm.create("父任务")
        pid = parent["id"]
        for i in range(3):
            self.tm.create(f"子任务{i}", parent_id=pid)

        children = [i for i in self.task_ids() if i.startswith(f"{pid}_")]
        self.assertEqual(len(children), 3)

        self.tm.delete(children[1])  # 删掉中间的子任务
        ok, child = self.tm.create("新子任务", parent_id=pid)
        self.assertTrue(ok, child)
        self.assertNotIn(child["id"], [c for c in self.task_ids() if c != child["id"]])
        self.assertEqual(len(self.task_ids()), len(set(self.task_ids())))


class TestTaskFileIntegrity(TempProjectTestCase):
    """任务书必须落盘才算创建成功"""

    def test_broken_template_rolls_back_task(self):
        """模板损坏时：创建失败 + task_list 不留残留"""
        template_path = os.path.join(Config.get_metadata_dir(), "templates", "task.yaml")
        with open(template_path, "w", encoding="utf-8") as f:
            # 语法非法的 YAML：_ensure_builtin_templates 解析失败会保留原文件
            f.write("name: task\nstructure: \"# {{ id }}\n  bad: [unclosed\n")

        ok, result = self.tm.create("会失败的任务")
        self.assertFalse(ok, "模板损坏时创建居然成功了")
        self.assertEqual(result.get("error"), "task_file_create_failed")
        self.assertIn("detail", result)

        # task_list 不能留下"有元数据、无任务书"的僵尸任务
        self.assertEqual(self.task_ids(), [], "失败的创建在 task_list 里留下了残留")

    def test_missing_template_rolls_back_task(self):
        """请求不存在的模板时必须失败，而不是静默套用别的模板"""
        ok, result = self.tm.create("会失败的任务", template="no-such-template")
        self.assertFalse(ok, "模板不存在时创建居然成功了")
        self.assertEqual(result.get("error"), "task_file_create_failed")
        self.assertEqual(self.task_ids(), [])

    def test_successful_create_writes_task_file(self):
        ok, task = self.tm.create("正常任务")
        self.assertTrue(ok, task)
        self.assertTrue(os.path.exists(self.md_path(task["id"])), "任务书没有落盘")


class TestDuplicateIdDetection(TempProjectTestCase):
    """重复 ID 必须显式报错，不能静默命中"""

    def _inject_duplicate(self):
        """人为制造一条重复 ID 的记录（模拟历史撞号留下的脏数据）"""
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        clone = dict(data["tasks"][0])
        clone["description"] = "另一条同 ID 的记录"
        data["tasks"].append(clone)
        with open(self.tm.task_list_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def test_find_duplicates_detects(self):
        self.tm.create("任务A")
        self._inject_duplicate()
        dups = self.tm.find_duplicates()
        self.assertIn("task_001", dups)
        self.assertEqual(len(dups["task_001"]), 2)

    def test_get_unique_reports_duplicate(self):
        self.tm.create("任务A")
        self._inject_duplicate()
        task, err = self.tm.get_unique("task_001")
        self.assertIsNone(task)
        self.assertIsNotNone(err)
        self.assertTrue(err.startswith("duplicate_task_id"))
        self.assertIn("2", err)

    def test_get_unique_returns_task_when_no_duplicate(self):
        self.tm.create("任务A")
        task, err = self.tm.get_unique("task_001")
        self.assertIsNone(err)
        self.assertEqual(task["id"], "task_001")

    def test_get_unique_reports_not_found(self):
        task, err = self.tm.get_unique("task_999")
        self.assertIsNone(task)
        self.assertIsNone(err)  # 不存在不是"重复"，由调用方按 not_found 处理


class TestTemplateLoadErrors(TempProjectTestCase):
    """模板加载失败必须能区分原因"""

    def test_broken_yaml_is_reported_as_parse_error(self):
        template_path = os.path.join(Config.get_metadata_dir(), "templates", "task.yaml")
        with open(template_path, "w", encoding="utf-8") as f:
            f.write("name: task\nstructure: [unclosed\n")

        tm = TemplateManager()
        template, err = tm.load_template_detailed("task")
        self.assertIsNone(template)
        self.assertIsNotNone(err)
        self.assertIn("template_parse_error", err)

    def test_missing_template_is_reported_as_not_found(self):
        tm = TemplateManager()
        template, err = tm.load_template_detailed("no_such_template")
        self.assertIsNone(template)
        self.assertEqual(err, "template_not_found")

    def test_render_error_does_not_raise(self):
        """模板渲染异常应返回失败原因，而不是抛栈"""
        template_path = os.path.join(Config.get_metadata_dir(), "templates", "task.yaml")
        with open(template_path, "w", encoding="utf-8") as f:
            # version 99.0 防止被内置模板覆盖（内置版本 2.1）
            f.write('name: task\nversion: "99.0"\nstructure: "{% for x in %}"\n')

        tm = TemplateManager()
        ok, detail = tm.create_task_file("probe", "task", "desc", {})
        self.assertFalse(ok)
        self.assertIn("template_render_error", detail)


class TestCliOutputContract(TempProjectTestCase):
    """输出契约：stdout 末行锚点 + 子命令级 --json"""

    def _run_cli(self, argv):
        from lra.cli import main

        buf = io.StringIO()
        old = sys.argv
        sys.argv = ["lra"] + argv
        try:
            with redirect_stdout(buf):
                main()
        finally:
            sys.argv = old
        return buf.getvalue()

    def test_created_anchor_is_last_line(self):
        out = self._run_cli(["create", "任务A"])
        lines = [ln for ln in out.strip().split("\n") if ln.strip()]
        self.assertTrue(
            lines[-1].startswith("Created: task_"),
            f"末行不是 Created 锚点，实际末行: {lines[-1]!r}",
        )

    def test_anchor_survives_dependency_ids_in_output(self):
        """输出里出现依赖项 ID 时，末行锚点仍指向新任务"""
        self.tm.create("被依赖的任务")
        out = self._run_cli(["create", "新任务", "--dependencies", "task_001"])
        lines = [ln for ln in out.strip().split("\n") if ln.strip()]
        self.assertTrue(lines[-1].startswith("Created: task_"))
        self.assertTrue(lines[-1].endswith("task_002"))

    def test_subcommand_json_output(self):
        out = self._run_cli(["create", "任务A", "--json"])
        data = json.loads(out.strip())
        self.assertTrue(data["ok"])
        self.assertEqual(data["id"], "task_001")
        self.assertEqual(data["task"]["id"], "task_001")

    def test_global_json_still_works(self):
        """全局 --json（写在子命令前）不能被子命令的默认覆盖"""
        out = self._run_cli(["--json", "create", "任务A"])
        data = json.loads(out.strip())
        self.assertTrue(data["ok"])
        self.assertEqual(data["id"], "task_001")


class TestDoctorDedupeFix(TempProjectTestCase):
    """lra doctor --fix：检测并重新编号重复 ID（内置去重，不另开 dedupe 命令）"""

    def _inject_duplicate(self):
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        clone = dict(data["tasks"][0])
        clone["description"] = "另一条同 ID 的记录"
        data["tasks"].append(clone)
        with open(self.tm.task_list_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _records(self):
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        return data["tasks"]

    def test_doctor_detects_duplicate_ids(self):
        from lra.doctor import check_duplicate_task_ids

        self.tm.create("任务A")
        self._inject_duplicate()
        result = check_duplicate_task_ids(".")
        self.assertEqual(result.status, "error")
        self.assertIn("task_001", result.detail)

    def test_doctor_reports_ok_when_no_duplicates(self):
        from lra.doctor import check_duplicate_task_ids

        self.tm.create("任务A")
        result = check_duplicate_task_ids(".")
        self.assertEqual(result.status, "ok")

    def test_fix_renumbers_duplicate_and_keeps_task_book_with_its_owner(self):
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("任务A")
        self._inject_duplicate()
        original_md = self.md_path("task_001")
        self.assertTrue(os.path.exists(original_md))

        result = fix_duplicate_task_ids(".")
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)

        ids = [t["id"] for t in self._records()]
        self.assertEqual(len(ids), len(set(ids)), "修复后仍有重复 ID")
        self.assertIn("task_001", ids)

        new_id = result["fixed"][0]["new_id"]
        self.assertNotEqual(new_id, "task_001")
        # 任务书原地不动（主人保留原 ID），文件不会被搬走或丢失
        self.assertTrue(os.path.exists(original_md))
        self.assertFalse(os.path.exists(self.md_path(new_id)))
        # 换 ID 的那条没有自己的任务书 → task_file 清空，避免串台
        rec = [t for t in self._records() if t["id"] == new_id][0]
        self.assertEqual(rec["task_file"], "")
        # 主人那条仍然指向原任务书
        owner = [t for t in self._records() if t["id"] == "task_001"][0]
        self.assertEqual(owner["task_file"], "tasks/task_001.md")

    def test_fix_assigns_id_to_the_record_that_owns_the_task_book(self):
        """真实撞号场景：后来的任务把任务书覆盖了 → 后来那条才是主人"""
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("旧任务")
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        newer = dict(data["tasks"][0])
        newer["description"] = "新任务"
        newer["created_at"] = "2099-01-01T00:00:00"
        data["tasks"].append(newer)
        with open(self.tm.task_list_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 模拟撞号：任务书被新任务覆盖
        with open(self.md_path("task_001"), "w", encoding="utf-8") as f:
            f.write("# task_001\n\n## 描述\n\n新任务\n")

        result = fix_duplicate_task_ids(".")
        self.assertTrue(result["ok"])
        new_id = result["fixed"][0]["new_id"]
        records = {t["id"]: t for t in self._records()}
        # 持有任务书的那条保留 task_001
        self.assertEqual(records["task_001"]["description"], "新任务")
        self.assertEqual(records["task_001"]["task_file"], "tasks/task_001.md")
        # 旧的那条换新 ID 且没有任务书
        self.assertEqual(records[new_id]["description"], "旧任务")
        self.assertEqual(records[new_id]["task_file"], "")

    def test_fix_keeps_first_record_untouched(self):
        """保留第一条 → 现有依赖/父子关系的行为不变"""
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("任务A")
        self._inject_duplicate()
        fix_duplicate_task_ids(".")
        first = self._records()[0]
        self.assertEqual(first["id"], "task_001")
        self.assertEqual(first["description"], "任务A")

    def test_fix_dry_run_does_not_mutate(self):
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("任务A")
        self._inject_duplicate()
        result = fix_duplicate_task_ids(".", dry_run=True)
        self.assertTrue(result["dry_run"])
        ids = [t["id"] for t in self._records()]
        self.assertNotEqual(len(ids), len(set(ids)), "dry-run 竟然修改了数据")
        self.assertEqual(ids.count("task_001"), 2)

    def test_fix_creates_backup(self):
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("任务A")
        self._inject_duplicate()
        fix_duplicate_task_ids(".")
        backup_dir = os.path.join(Config.get_metadata_dir(), Config.BACKUP_DIR)
        backups = [f for f in os.listdir(backup_dir) if f.startswith("task_list.json.pre-dedupe")]
        self.assertTrue(backups, "修复前没有生成备份")

    def test_fix_is_idempotent(self):
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("任务A")
        self._inject_duplicate()
        fix_duplicate_task_ids(".")
        again = fix_duplicate_task_ids(".")
        self.assertTrue(again["ok"])
        self.assertEqual(again["count"], 0)

    def test_fix_renumbers_duplicate_subtask_under_same_parent(self):
        from lra.doctor import fix_duplicate_task_ids

        self.tm.create("父任务")
        ok, child = self.tm.create("子任务", parent_id="task_001")
        self.assertTrue(ok, child)
        child_id = child["id"]
        self.assertTrue(child_id.startswith("task_001_"))

        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        clone = dict([t for t in data["tasks"] if t["id"] == child_id][0])
        data["tasks"].append(clone)
        with open(self.tm.task_list_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        result = fix_duplicate_task_ids(".")
        self.assertTrue(result["ok"])
        new_id = result["fixed"][0]["new_id"]
        self.assertTrue(new_id.startswith("task_001_"), f"子任务新 ID 丢了父级前缀: {new_id}")
        self.assertNotEqual(new_id, child_id)
        ids = [t["id"] for t in self._records()]
        self.assertEqual(len(ids), len(set(ids)))


class TestMissingTaskFileRebuild(TempProjectTestCase):
    """lra doctor --fix：用模板重建缺失的任务书（僵尸任务的解药）"""

    def _records(self):
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        return data["tasks"]

    def test_doctor_reports_missing_task_file(self):
        from lra.doctor import check_task_files

        self.tm.create("任务A")
        os.unlink(self.md_path("task_001"))
        result = check_task_files(".")
        self.assertEqual(result.status, "error")
        self.assertIn("task_001", result.detail)

    def test_doctor_reports_task_without_task_file(self):
        from lra.doctor import check_task_files

        self.tm.create("任务A")
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        data["tasks"][0]["task_file"] = ""
        with open(self.tm.task_list_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        result = check_task_files(".")
        self.assertEqual(result.status, "error")
        self.assertIn("No task_file", result.detail)

    def test_fix_rebuilds_missing_task_file(self):
        from lra.doctor import fix_missing_task_files

        self.tm.create("任务A")
        os.unlink(self.md_path("task_001"))

        result = fix_missing_task_files(".")
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertTrue(os.path.exists(self.md_path("task_001")))
        with open(self.md_path("task_001"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("任务A", content)
        self.assertIn("task_001", content)

    def test_fix_rebuilds_unbound_task_file_and_relinks_record(self):
        from lra.doctor import fix_missing_task_files

        self.tm.create("任务A")
        data = json.load(open(self.tm.task_list_path, encoding="utf-8"))
        data["tasks"][0]["task_file"] = ""
        with open(self.tm.task_list_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.unlink(self.md_path("task_001"))

        result = fix_missing_task_files(".")
        self.assertTrue(result["ok"])
        self.assertTrue(os.path.exists(self.md_path("task_001")))
        self.assertEqual(self._records()[0]["task_file"], "tasks/task_001.md")

    def test_fix_leaves_existing_task_files_untouched(self):
        from lra.doctor import fix_missing_task_files

        self.tm.create("任务A")
        with open(self.md_path("task_001"), "w", encoding="utf-8") as f:
            f.write("手写内容，不要动我")

        result = fix_missing_task_files(".")
        self.assertEqual(result["count"], 0)
        with open(self.md_path("task_001"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "手写内容，不要动我")

    def test_fix_dry_run_does_not_write(self):
        from lra.doctor import fix_missing_task_files

        self.tm.create("任务A")
        os.unlink(self.md_path("task_001"))
        result = fix_missing_task_files(".", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["count"], 1)
        self.assertFalse(os.path.exists(self.md_path("task_001")))

    def test_fix_reports_failure_when_template_is_broken(self):
        from lra.doctor import fix_missing_task_files

        self.tm.create("任务A")
        os.unlink(self.md_path("task_001"))
        # 破坏模板：渲染必然失败
        with open(
            os.path.join(Config.get_templates_dir(), "task.yaml"), "w", encoding="utf-8"
        ) as f:
            f.write("name: task\nstructure: \"{{ broken\n")

        result = fix_missing_task_files(".")
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(result["failed"][0]["id"], "task_001")
        self.assertFalse(os.path.exists(self.md_path("task_001")))

    def test_variables_are_persisted_and_restored_on_rebuild(self):
        """创建时的 requirements/design 会被记录下来，重建时原样还原"""
        from lra.doctor import fix_missing_task_files

        self.tm.create(
            "任务A",
            variables={"design": "设计要点XYZ", "requirements": "需求要点ABC"},
        )
        record = self._records()[0]
        self.assertEqual(record["variables"]["design"], "设计要点XYZ")

        os.unlink(self.md_path("task_001"))
        result = fix_missing_task_files(".")
        self.assertEqual(result["count"], 1)
        with open(self.md_path("task_001"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("设计要点XYZ", content)
        self.assertIn("需求要点ABC", content)


if __name__ == "__main__":
    unittest.main()
