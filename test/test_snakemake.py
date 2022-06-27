# Copyright 2022 CRS4.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import shutil

import pytest
from repo2rocrate.snakemake import find_workflow, get_lang_version, make_crate


SNAKEMAKE_ID = "https://w3id.org/workflowhub/workflow-ro-crate#snakemake"


def test_find_workflow(tmpdir):
    root = tmpdir / "snakemake-repo"
    workflow_dir = root / "workflow"
    workflow_dir.mkdir(parents=True)
    with pytest.raises(RuntimeError):
        find_workflow(root)
    wf_path = workflow_dir / "Snakefile"
    wf_path.touch()
    assert find_workflow(root) == wf_path
    new_wf_path = root / "Snakefile"
    shutil.move(wf_path, new_wf_path)
    assert find_workflow(root) == new_wf_path


def test_get_lang_version(tmpdir):
    v = "0.1.0"
    wf_path = tmpdir / "Snakefile"
    for arg_part in f'("{v}")', f"( '{v}')":
        with open(wf_path, "wt") as f:
            f.write(f'# comment\nfrom x import y\nmin_version{arg_part}\n')
        assert get_lang_version(wf_path) == v


def test_fair_crcc_send_data(data_dir):
    repo_name = "fair-crcc-send-data"
    root = data_dir / repo_name
    repo_url = f"https://github.com/crs4/{repo_name}"
    wf_version = "0.1"  # made up
    lang_version = "6.5.0"
    license = "GPL-3.0"
    ci_workflow = "main.yml"
    crate = make_crate(root, repo_url=repo_url, wf_version=wf_version, license=license, ci_workflow=ci_workflow)
    assert crate.root_dataset["license"] == license
    # workflow
    workflow = crate.mainEntity
    assert workflow.id == "workflow/Snakefile"
    assert workflow["name"] == repo_name
    assert workflow["version"] == wf_version
    image = crate.get("images/rulegraph.svg")
    assert image
    assert set(image.type) == {"File", "ImageObject"}
    assert workflow["image"] is image
    language = workflow["programmingLanguage"]
    assert language.id == SNAKEMAKE_ID
    assert language["version"] == lang_version
    assert workflow["url"] == crate.root_dataset["isBasedOn"] == repo_url
    # workflow testing metadata
    suite = crate.root_dataset["mentions"]
    assert suite
    if isinstance(suite, list):
        assert len(suite) == 1
        suite = suite[0]
    assert suite.type == "TestSuite"
    assert suite["mainEntity"] is workflow
    instance = suite["instance"]
    assert instance
    if isinstance(instance, list):
        assert len(instance) == 1
        instance = instance[0]
    assert instance.type == "TestInstance"
    assert instance["url"] == "https://api.github.com"
    assert instance["resource"] == f"repos/crs4/{repo_name}/actions/workflows/{ci_workflow}"
    # layout
    expected_data_entities = [
        ("LICENSE", "File"),
        ("README.md", "File"),
        ("config", "Dataset"),
        (".tests/integration", "Dataset"),
        ("workflow/rules", "Dataset"),
        ("workflow/schemas", "Dataset"),
        ("workflow/scripts", "Dataset"),
    ]
    for relpath, type_ in expected_data_entities:
        entity = crate.get(relpath)
        assert entity, f"{relpath} not listed in crate metadata"
        assert entity.type == type_
