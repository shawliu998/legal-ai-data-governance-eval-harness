import json
from pathlib import Path

from legal_eval_harness.io_excel import load_dataset
from legal_eval_harness.practice_benchmark_importer import SOURCE_FILENAMES, prepare_practice_benchmark_dataset
from legal_eval_harness.runner import build_run_plan


def _write_sources(source_dir: Path) -> None:
    source_dir.mkdir(parents=True)
    case_item = {
        "label": "合同纠纷",
        "context": "甲乙签订服务合同，乙方延期交付，甲方要求解除合同并赔偿。",
        "question": "请按结论、案情简述、分析过程和依据法条分析甲方请求。",
        "rubrics": [
            {"criterion": "【结论得分】\n(+5分) 说明甲方是否有权解除合同。", "points": "5", "tags": "结论得分"},
            {"criterion": "【案情简述得分】\n(+5分) 概括合同、延期和解除通知事实。", "points": "5", "tags": "案情简述得分"},
            {"criterion": "【分析过程得分】\n(+10分) 连接违约事实和解除条件。", "points": "10", "tags": "分析过程得分"},
            {"criterion": "【依据法条得分】\n(+5分) 说明合同履行和解除依据。", "points": "5", "tags": "依据法条得分"},
        ],
    }
    (source_dir / SOURCE_FILENAMES["case"]).write_text(json.dumps(case_item, ensure_ascii=False) + "\n", "utf-8")
    consultation_item = {
        "id": 1,
        "conversation": "我被公司调岗降薪，想知道能不能直接不去上班。",
        "rubrics": "总分：5分\n1.(+3 分) 是否询问劳动合同岗位、薪资约定和调岗通知？\n2.(+2 分) 是否询问考勤、沟通记录和仲裁时效？",
        "score": "",
    }
    (source_dir / SOURCE_FILENAMES["consultation"]).write_text(
        json.dumps([consultation_item], ensure_ascii=False), "utf-8"
    )
    document_item = {
        "id": 1,
        "tag": "买卖合同纠纷",
        "conversation": "请根据被告陈述起草答辩状。",
        "Rubrics": "总分：20分\n一、答辩意见（10分）\n得分点：说明不同意全部诉请。（6分）\n二、证据目录（10分）\n得分点：列明合同、付款和沟通证据。（6分）",
        "score": 20,
    }
    (source_dir / SOURCE_FILENAMES["defendant_statement"]).write_text(
        json.dumps([document_item], ensure_ascii=False), "utf-8"
    )
    (source_dir / SOURCE_FILENAMES["plaintiff_statement"]).write_text(
        json.dumps([document_item], ensure_ascii=False), "utf-8"
    )


def test_prepare_practice_benchmark_dataset_outputs_loadable_manifest(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "pilot"
    _write_sources(source_dir)

    paths = prepare_practice_benchmark_dataset(
        output_dir=output_dir,
        source_dir=source_dir,
        download=False,
        case_limit=1,
        consultation_limit=1,
        document_limit=2,
    )

    bundle = load_dataset(paths["manifest"])
    assert len(bundle.eval_input) == 4
    assert set(bundle.eval_input["task_category"]) == {"case_analysis", "consultation", "document_drafting"}
    assert "key_missing_facts" not in bundle.eval_input.columns
    assert len(bundle.rubric_items) >= 8

    config = {
        "models": [{"alias": "Model_A", "provider": "mock", "model": "mock"}],
        "run_plan": {"full_samples": "all", "full_versions": ["V0", "V1", "V3"], "deep_samples": []},
    }
    assert len(build_run_plan(bundle, config)) == 12
