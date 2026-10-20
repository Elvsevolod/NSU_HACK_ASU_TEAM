# Журнал №31

G01: прочитаны глобальные/проектные инструкции, навыки версий и Karpathy, оба файла пользователя. DeepSeek не вызывается по прямому запрету. Хеши submission/ZIP30 и всех 10 TT-входов сверены. Новый код — самостоятельная копия №30; старые результаты не перенесены как результаты №31. Глобальная Goal активна; цели G01–G18 записаны.

Далее: новый offline baseline по неизменному снимку №30, затем S6 ledger и MRE.

2026-10-18T17:37:16.442473+00:00 G01 verified

{
  "evidence_paths": [
    "benchmark/stages/G01-parent30",
    "benchmark/overnight/G01/baseline-comparison.json",
    "development/protected-files.json",
    "development/input-sha256.json"
  ],
  "findings": [
    "Baseline submission is byte-identical to actual parent30; all 103 semantic witnesses match.",
    "Protected baseline contains 24138 files including parent30; ten TT input hashes match.",
    "G15 existing bundled real profiles have already been used; fresh complete source/skeleton/context/scenario/oracle prerequisite is not yet established."
  ],
  "actual_exit_status": 0,
  "tests_not_run": [
    "G01 manifest mutation and explicit guard tests will be recorded with early MRE controls"
  ],
  "next_action": "G02: preserved historical stage ledger and source/state first-loss reproduction"
}

2026-10-18T17:37:34.144403+00:00 G01 in_progress

{
  "findings": [
    "Correction: submission matches, but initial semantic check found differences at S2 steps6/7. The preceding verified entry was emitted before its assertion and is withdrawn; resolving differences before acceptance."
  ],
  "next_action": "Locate exact changed fields in S2 witnesses before baseline acceptance"
}

2026-10-18T17:37:57.073925+00:00 G01 in_progress

{
  "findings": [
    "Resolved raw difference: only ordering of limitations diagnostics in S2 steps6/7 differed. Sorting just those string diagnostic lists gives typed semantic equality for all103 steps; value/operation order is untouched."
  ],
  "next_action": "Complete manifest mutation/guard controls, then accept G01; do not repeat baseline"
}

2026-10-18T17:38:41.585897+00:00 G01 in_progress

{
  "commands": [
    [
      "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "-B",
      "checks/check_baseline_gate.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G01/baseline-gates"
}

2026-10-18T17:38:41.744475+00:00 G01 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G01/baseline-gates"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "baseline-gates",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:41:26.444155+00:00 G01 verified

{
  "evidence_paths": [
    "benchmark/overnight/G01/baseline-gates.json",
    "benchmark/overnight/G01/baseline-comparison-normalized.json"
  ],
  "tests_not_run": [],
  "next_action": "G02 preserved historical ledger and diagnostic-only invalidation/merge trace"
}

2026-10-18T17:42:46.788168+00:00 G02 in_progress

{
  "commands": [
    [
      "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "-B",
      "checks/s6_ledger.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G02/historical-ledger"
}

2026-10-18T17:42:46.855907+00:00 G02 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G02/historical-ledger"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "historical-ledger",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:42:46.885480+00:00 G03 in_progress

{
  "commands": [
    [
      "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_unknown_collection_iteration.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G03/before-unknown-foreach"
}

2026-10-18T17:42:47.676797+00:00 G03 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G03/before-unknown-foreach"
  ],
  "actual_exit_status": 2,
  "tests_run": [
    {
      "label": "before-unknown-foreach",
      "returncode": 2,
      "timed_out": false
    }
  ]
}

2026-10-18T17:43:30.788602+00:00 G02 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/s6_ledger.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G02/historical-ledger-v2"
}

2026-10-18T17:43:32.536874+00:00 G02 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G02/historical-ledger-v2"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "historical-ledger-v2",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:43:32.568427+00:00 G03 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_unknown_collection_iteration.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G03/before-unknown-foreach-v2"
}

2026-10-18T17:43:32.893473+00:00 G03 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G03/before-unknown-foreach-v2"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "before-unknown-foreach-v2",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:43:45.679945+00:00 G02 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_causal_diagnostics.py",
      "--code",
      "development/stages/G01-parent30/code",
      "--diagnostic-output",
      "benchmark/overnight/G02/causal-parent30/invalidations.json",
      "--",
      "--source",
      "../../tt-challenge/targets/trainticket",
      "--skeleton",
      "../../tt-challenge/skeleton/trainticket.json.gz",
      "--context",
      "../../tt-challenge/context",
      "--scenarios",
      "../../tt-challenge/scenarios/S6.json",
      "--output",
      "benchmark/overnight/G02/causal-parent30/submission.json",
      "--report",
      "benchmark/overnight/G02/causal-parent30/analysis-report.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G02/causal-parent30"
}

2026-10-18T17:44:05.674456+00:00 G02 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G02/causal-parent30"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "causal-parent30",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:44:36.128745+00:00 G03 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_unknown_collection_iteration.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G03/before-unknown-foreach-v3"
}

2026-10-18T17:44:37.110323+00:00 G03 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G03/before-unknown-foreach-v3"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "before-unknown-foreach-v3",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:44:54.219321+00:00 G03 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "a39c5c427bf80ef92399c567474bc134de1e0701c6d99e0ba0e18b99923ce255",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "a8ed21300a0cf516c5c0f30016c57f58ae862bd6890291ae3451b084b21022fc",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "17848320413dcf1ea6f9fd30151d8034cacf51509ddce9117105fa6a7d1ae862",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "c0b4824bfb7afff0143569e593779f4792a98a2e5816c6e59060a06f669e7a59",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "8d6317612ec10feeddde39699994b0def38579dfa3fea1d1c1b6355de5d94a63",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "f3a298c0255759aed497b9d83b1f6916b3bb08829dc09c4d835726c52d188a7b",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "bac8a9f908ec54af20108dcf753b43abdd08bf1d72a3a0d984d32cd8f189c58e",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "678b7262b8b6cf321229cd2a919a39cf255f88f7dffe493e572a7daa5f628caf",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "bbf33f3bfe8c591129cffce7351547e543781986796b4ef0bb7258aef4db025e",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "c23cce5e6d2d04103ff28e8eb3b07a22be4169be9c91a11d5138b3b55269282c",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "69456eec43258de6bdb49c1c3d8d8dce6c66f20b8385b60f4fbbcd94bb92f344",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G03-before"
  ],
  "findings": [
    "Opaque empty carrier reproduces false known absence; null enhanced-for skips required throw.",
    "The Collections.emptyList positive fixture exposed an unrelated unsupported factory; replaced by supported explicit ArrayList allocation before product edits."
  ],
  "next_action": "Add explicit unknown-iteration boundary with conservative reachable native heap effects; preserve null throw"
}

2026-10-18T17:44:54.320681+00:00 G03 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_unknown_collection_iteration.py",
      "code/tests/test_singleton_join_identity.py",
      "code/tests/test_hashset_membership.py",
      "code/tests/test_map_noop_filter.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G03/after-unknown-foreach"
}

2026-10-18T17:44:55.284642+00:00 G03 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G03/after-unknown-foreach"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "after-unknown-foreach",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:45:48.531969+00:00 G03 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_unknown_collection_iteration.py",
      "code/tests/test_singleton_join_identity.py",
      "code/tests/test_hashset_membership.py",
      "code/tests/test_map_noop_filter.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G03/expanded-unknown-foreach"
}

2026-10-18T17:45:49.032950+00:00 G03 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G03/expanded-unknown-foreach"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "expanded-unknown-foreach",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:45:49.124088+00:00 G03 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "ac113a9ed46cc6094e29f6eb3893be50cc1ce19049558c2433afd9170267b5ad",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "a8ed21300a0cf516c5c0f30016c57f58ae862bd6890291ae3451b084b21022fc",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "17848320413dcf1ea6f9fd30151d8034cacf51509ddce9117105fa6a7d1ae862",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "c0b4824bfb7afff0143569e593779f4792a98a2e5816c6e59060a06f669e7a59",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "8d6317612ec10feeddde39699994b0def38579dfa3fea1d1c1b6355de5d94a63",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "f3a298c0255759aed497b9d83b1f6916b3bb08829dc09c4d835726c52d188a7b",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "bac8a9f908ec54af20108dcf753b43abdd08bf1d72a3a0d984d32cd8f189c58e",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "678b7262b8b6cf321229cd2a919a39cf255f88f7dffe493e572a7daa5f628caf",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "bbf33f3bfe8c591129cffce7351547e543781986796b4ef0bb7258aef4db025e",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "c23cce5e6d2d04103ff28e8eb3b07a22be4169be9c91a11d5138b3b55269282c",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G03-local-accepted"
  ],
  "what_changed": [
    "Unknown enhanced-for now stops explicitly, widens reachable native aliases before skipped effects, and never interprets physical len0 as known absence.",
    "Null enhanced-for throws before its body."
  ],
  "unresolved": [
    "Full103 stage comparison is pending; conservative reachable-heap widening is an explicit precision cost."
  ],
  "next_action": "Measure G03 immutable stage; G04 consumer-contract paired MRE next"
}

2026-10-18T17:45:55.443747+00:00 G03 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G03-unknown-foreach"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G03/stage-measurement"
}

2026-10-18T17:47:05.468748+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/before-bulk-consumers"
}

2026-10-18T17:47:06.666422+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/before-bulk-consumers"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "before-bulk-consumers",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:47:07.141296+00:00 G03 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G03/stage-measurement"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "stage-measurement",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:48:06.829406+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/after-bulk-consumers"
}

2026-10-18T17:48:08.041235+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/after-bulk-consumers"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "after-bulk-consumers",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:50:34.148602+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py",
      "code/tests/test_hashset_membership.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/after-bulk-consumers-v2"
}

2026-10-18T17:50:34.661807+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/after-bulk-consumers-v2"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "after-bulk-consumers-v2",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:51:51.289474+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py",
      "code/tests/test_hashset_membership.py",
      "code/tests/test_inventory_collection_journey.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/after-bulk-consumers-v3"
}

2026-10-18T17:51:52.091828+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/after-bulk-consumers-v3"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "after-bulk-consumers-v3",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:52:34.482153+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py",
      "code/tests/test_hashset_membership.py",
      "code/tests/test_inventory_collection_journey.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/consumer-inventory-positive"
}

2026-10-18T17:52:35.316734+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/consumer-inventory-positive"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "consumer-inventory-positive",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:52:35.349151+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/early-full-regression"
}

2026-10-18T17:52:42.043247+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/early-full-regression"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "early-full-regression",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:53:26.658114+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_inventory_collection_journey.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/corrected-inventory-control"
}

2026-10-18T17:53:27.336194+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/corrected-inventory-control"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "corrected-inventory-control",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:53:59.529024+00:00 G04 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G04-bulk-consumers"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G04/stage-measurement"
}

2026-10-18T17:55:10.650594+00:00 G04 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G04/stage-measurement"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "stage-measurement",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:58:15.410083+00:00 G03 verified

{
  "evidence_paths": [
    "benchmark/stages/G03-unknown-foreach",
    "benchmark/comparisons/G01-parent30--G03-unknown-foreach.json",
    "benchmark/overnight/G03/expanded-unknown-foreach"
  ],
  "findings": [
    "37 focused tests passed; standalone full103 comparison saved. Earlier unknown rows now stop with explicit boundary instead of known absence.",
    "Conservative cost: reachable native heap widened before skipped effects; no generic loop summary or all-table invalidation introduced."
  ],
  "tests_not_run": [],
  "next_action": "G04 isolated consumer stage measurement; final downstream controls remain G14"
}

2026-10-18T17:58:39.797474+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_map_proof_casts.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/before-proof-casts"
}

2026-10-18T17:58:40.226378+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/before-proof-casts"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "before-proof-casts",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T17:59:17.552412+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_map_proof_casts.py",
      "code/tests/test_map_noop_filter.py",
      "code/tests/test_bulk_consumer_types.py",
      "code/tests/test_hashset_membership.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/after-proof-casts"
}

2026-10-18T17:59:18.793166+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/after-proof-casts"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "after-proof-casts",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T17:59:18.828668+00:00 G04 in_progress

{
  "evidence_paths": [
    "development/checkpoints/G04-local-accepted",
    "benchmark/overnight/G04/corrected-inventory-control"
  ],
  "findings": [
    "Checkpoint files were saved, but journal helper rejected a duplicate evidence_paths keyword; helper repaired and existing checkpoint retained without overwrite."
  ],
  "next_action": "Finish G04 full103 comparison and G02 isolated consumer ablation; G05A cast gate running"
}

2026-10-18T17:59:46.111213+00:00 G04 verified

{
  "evidence_paths": [
    "benchmark/stages/G04-bulk-consumers",
    "benchmark/comparisons/G01-parent30--G04-bulk-consumers.json",
    "benchmark/comparisons/G03-unknown-foreach--G04-bulk-consumers.json"
  ],
  "what_changed": [
    "Standard removeAll/retainAll Collection operand descriptors, source receiver declaration lookup, bounded scalar HashSet(Collection)."
  ],
  "tests_not_run": [],
  "next_action": "G05A cast soundness accepted locally; G05B bounded commuting removal proof"
}

2026-10-18T17:59:46.186196+00:00 G05 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "df335cd56e22b73c38a99c7377e50035d3fcb9c2685523640eb8d4eca6998634",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "a8ed21300a0cf516c5c0f30016c57f58ae862bd6890291ae3451b084b21022fc",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "17848320413dcf1ea6f9fd30151d8034cacf51509ddce9117105fa6a7d1ae862",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "c0b4824bfb7afff0143569e593779f4792a98a2e5816c6e59060a06f669e7a59",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "d384aa04ee917de563d12395f54d80927d1793eda9063631f0fdd3cb4474c170",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "f3a298c0255759aed497b9d83b1f6916b3bb08829dc09c4d835726c52d188a7b",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "bac8a9f908ec54af20108dcf753b43abdd08bf1d72a3a0d984d32cd8f189c58e",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "f14a50683456523444ce8b3d87ea1f81e66c00a638bc05522e4e290177ffec92",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "bbf33f3bfe8c591129cffce7351547e543781986796b4ef0bb7258aef4db025e",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G05A-cast-soundness",
    "benchmark/overnight/G05/before-proof-casts",
    "benchmark/overnight/G05/after-proof-casts"
  ],
  "findings": [
    "Pure shared native collection compatibility rejects JavaArray as List/Collection and admits HashSet as Collection.",
    "Proof-on/off cast and state/edge controls agree; unsafe no-op suppression reproduced before fix."
  ],
  "unresolved": [
    "G05B live Map filter remains pending."
  ],
  "next_action": "Measure G05A immutable stage, then bounded live filter with actual source callbacks"
}

2026-10-18T18:00:03.425910+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G05A-cast-soundness"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/stage-cast-soundness"
}

2026-10-18T18:01:14.056891+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/stage-cast-soundness"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "stage-cast-soundness",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:05:22.415407+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_proof_casts.py",
      "code/tests/test_map_noop_filter.py",
      "code/tests/test_inventory_collection_journey.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/first-live-filter"
}

2026-10-18T18:05:23.673117+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/first-live-filter"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "first-live-filter",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:06:46.114466+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_proof_casts.py",
      "code/tests/test_map_noop_filter.py",
      "code/tests/test_inventory_collection_journey.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/live-filter-consumer-context"
}

2026-10-18T18:06:47.919187+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/live-filter-consumer-context"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "live-filter-consumer-context",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:08:57.025054+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/guarded-live-full-regression"
}

2026-10-18T18:09:05.099105+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/guarded-live-full-regression"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "guarded-live-full-regression",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:11:40.000590+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_tt_causal_probes.py",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G05/tt-live-filter-probes/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/tt-live-filter-probes"
}

2026-10-18T18:11:49.200942+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/tt-live-filter-probes"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-live-filter-probes",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:15:22.867079+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/trace_map_certificates.py",
      "--diagnostics",
      "benchmark/overnight/G05/tt-certificate-refusals/certificates.json",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G05/tt-certificate-refusals/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/tt-certificate-refusals"
}

2026-10-18T18:15:47.998994+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/tt-certificate-refusals"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-certificate-refusals",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:20:27.480057+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/trace_map_certificates.py",
      "--diagnostics",
      "benchmark/overnight/G05/tt-certificate-refusals-v2/certificates.json",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G05/tt-certificate-refusals-v2/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/tt-certificate-refusals-v2"
}

2026-10-18T18:21:00.201884+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/tt-certificate-refusals-v2"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-certificate-refusals-v2",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:22:19.690005+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_proof_casts.py",
      "code/tests/test_map_noop_filter.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/closed-native-effects"
}

2026-10-18T18:22:21.459568+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/closed-native-effects"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "closed-native-effects",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:26:56.951048+00:00 G05 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "20699ae1663893da9a63fe1d747038b63273120df284d456328b9a1503e9d20d",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "a8ed21300a0cf516c5c0f30016c57f58ae862bd6890291ae3451b084b21022fc",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "17848320413dcf1ea6f9fd30151d8034cacf51509ddce9117105fa6a7d1ae862",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "c0b4824bfb7afff0143569e593779f4792a98a2e5816c6e59060a06f669e7a59",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "014829f90987e7f7592550afb9b7ec501e0168bb0511f48629873fd0ca8a2c15",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "f3a298c0255759aed497b9d83b1f6916b3bb08829dc09c4d835726c52d188a7b",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "bac8a9f908ec54af20108dcf753b43abdd08bf1d72a3a0d984d32cd8f189c58e",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "bbf33f3bfe8c591129cffce7351547e543781986796b4ef0bb7258aef4db025e",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G05B-commuting-filter-pilot",
    "benchmark/overnight/G05/guarded-live-full-regression",
    "benchmark/overnight/G05/closed-native-effects",
    "benchmark/overnight/G05/tt-live-filter-probes",
    "benchmark/overnight/G05/tt-certificate-refusals-v2"
  ],
  "findings": [
    "Bounded generic live filter preserves real source getter calls and matches all6 small reference orders. Unsafe aliases/writes/throws/target reads/nondeterministic native callbacks decline.",
    "Full suite before last closed-native-effect guard passed1811; focused tests cover final guard.",
    "Actual TT Basic242 certificate refused24 times: route.getStations consumer is U, contains/indexOf unresolved, so no normal completion proof. No TT filter success claimed.",
    "An additional erased-consumer gap at direct enhanced-for collection expression was reproduced and fixed without choosing values."
  ],
  "unresolved": [
    "TT Route.stations producer/typed value first loss is deferred to G13.",
    "Full103 final B stage comparison pending."
  ],
  "next_action": "Measure immutable G05B stage; complete G02 contract-only ablation and G06 bounded residual-state experiment, then cart G07"
}

2026-10-18T18:27:08.888036+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G05B-commuting-removals"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/stage-live-filter"
}

2026-10-18T18:28:32.188132+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/stage-live-filter"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "stage-live-filter",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:34:37.499793+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_noop_filter.py",
      "code/tests/test_inventory_collection_journey.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/known-read-preflight"
}

2026-10-18T18:34:39.619444+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/known-read-preflight"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "known-read-preflight",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:36:39.636846+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_residual_pilot_keys.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/residual-key-controls"
}

2026-10-18T18:36:40.760363+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/residual-key-controls"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "residual-key-controls",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:36:40.810411+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/residual_state_pilot.py",
      "--output",
      "benchmark/overnight/G06/residual-state-pilot/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/residual-state-pilot"
}

2026-10-18T18:36:41.079410+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/residual-state-pilot"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "residual-state-pilot",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:38:33.468234+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_residual_pilot_keys.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/corrected-residual-keys"
}

2026-10-18T18:38:33.871909+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/corrected-residual-keys"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "corrected-residual-keys",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:39:01.655384+00:00 G02 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G02-bulk-contract-only",
      "--existing-snapshot"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G02/bulk-contract-only-ablation"
}

2026-10-18T18:40:22.168859+00:00 G02 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G02/bulk-contract-only-ablation"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "bulk-contract-only-ablation",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:44:13.167188+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/residual_state_pilot.py",
      "--output",
      "benchmark/overnight/G06/residual-state-pilot-v2/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/residual-state-pilot-v2"
}

2026-10-18T18:44:13.574239+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/residual-state-pilot-v2"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "residual-state-pilot-v2",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:44:13.605109+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "checks/tests/test_residual_pilot_keys.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/checker-owned-key-controls"
}

2026-10-18T18:44:13.925097+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/checker-owned-key-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "checker-owned-key-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:46:21.830530+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/residual_state_pilot.py",
      "--output",
      "benchmark/overnight/G06/residual-state-pilot-v3/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/residual-state-pilot-v3"
}

2026-10-18T18:46:22.165061+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/residual-state-pilot-v3"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "residual-state-pilot-v3",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:48:54.937910+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/residual_state_pilot.py",
      "--output",
      "benchmark/overnight/G06/residual-state-pilot-v4/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/residual-state-pilot-v4"
}

2026-10-18T18:48:55.322334+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/residual-state-pilot-v4"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "residual-state-pilot-v4",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:49:13.404481+00:00 G06 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/residual_state_pilot.py",
      "--output",
      "benchmark/overnight/G06/residual-state-pilot-v5/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G06/residual-state-pilot-v5"
}

2026-10-18T18:49:13.812775+00:00 G06 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G06/residual-state-pilot-v5"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "residual-state-pilot-v5",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:52:37.797925+00:00 G05 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G05B2-known-reads"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G05/known-read-stage"
}

2026-10-18T18:52:49.539422+00:00 G06 experiment_rejected

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "20699ae1663893da9a63fe1d747038b63273120df284d456328b9a1503e9d20d",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "a8ed21300a0cf516c5c0f30016c57f58ae862bd6890291ae3451b084b21022fc",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "17848320413dcf1ea6f9fd30151d8034cacf51509ddce9117105fa6a7d1ae862",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "c0b4824bfb7afff0143569e593779f4792a98a2e5816c6e59060a06f669e7a59",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "7e1b7ec150a4a9fa154e0704624127d0d4e2719710ac6a73bfba07e6866dfad2",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "f3a298c0255759aed497b9d83b1f6916b3bb08829dc09c4d835726c52d188a7b",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "bac8a9f908ec54af20108dcf753b43abdd08bf1d72a3a0d984d32cd8f189c58e",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "bbf33f3bfe8c591129cffce7351547e543781986796b4ef0bb7258aef4db025e",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G06-residual-state-decision",
    "benchmark/overnight/G06/residual-state-pilot-v5",
    "benchmark/overnight/G06/checker-owned-key-controls"
  ],
  "findings": [
    "Opt-in checker pilot preserves all six source-order witnesses and datastore revision/effects; commuting and datastore modes 15→12 actual interpreter calls; order-dependent 15→15; throwing 3→3. Eleven key separation controls passed.",
    "Reject default integration: only completed independent apply boundaries were proven, not suspended Java continuations, active transactions or full browser/NL history. No optimized TT run or production speedup claimed."
  ],
  "unresolved": [
    "Core suspended-continuation soundness remains outside measured pilot scope."
  ],
  "next_goal": "G07",
  "next_action": "Version positive cart checker and explicit post-authentication application boundary; implement Stream.toList."
}

2026-10-18T18:53:48.927053+00:00 G05 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G05/known-read-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "known-read-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:55:07.041692+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_application_entry_boundary.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/entry-boundary-test"
}

2026-10-18T18:55:07.390890+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/entry-boundary-test"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "entry-boundary-test",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:55:41.948311+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "checks/tests/test_cart_evaluator_v2.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/positive-mutation-checker"
}

2026-10-18T18:55:42.223496+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/positive-mutation-checker"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "positive-mutation-checker",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:55:42.263433+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G07/cart-before-stream/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/cart-before-stream"
}

2026-10-18T18:55:43.839199+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/cart-before-stream"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-before-stream",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:56:00.906127+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "checks/tests/test_cart_evaluator_v2.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/per-step-edge-mutations"
}

2026-10-18T18:56:01.190319+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/per-step-edge-mutations"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "per-step-edge-mutations",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:56:46.013782+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "checks/tests/test_cart_evaluator_v2.py",
      "code/tests/test_application_entry_boundary.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/final-checker-controls"
}

2026-10-18T18:56:46.420317+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/final-checker-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "final-checker-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:57:19.166705+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_stream_materialization.py",
      "code/tests/test_java_streams.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/stream-contract-tests"
}

2026-10-18T18:57:19.739864+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/stream-contract-tests"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "stream-contract-tests",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:57:42.088010+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_stream_materialization.py",
      "code/tests/test_java_streams.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/corrected-opaque-dispatch"
}

2026-10-18T18:57:42.506458+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/corrected-opaque-dispatch"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "corrected-opaque-dispatch",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T18:58:09.615521+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_stream_materialization.py",
      "code/tests/test_java_streams.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/set-stream-iterator-contracts"
}

2026-10-18T18:58:09.997959+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/set-stream-iterator-contracts"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "set-stream-iterator-contracts",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:58:10.027866+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G08/cart-stream-frontier/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/cart-stream-frontier"
}

2026-10-18T18:58:11.217771+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/cart-stream-frontier"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-stream-frontier",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:59:24.416360+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_stream_materialization.py",
      "code/tests/test_review_records.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/record-mapper-source-values"
}

2026-10-18T18:59:24.866639+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/record-mapper-source-values"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "record-mapper-source-values",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T18:59:24.899745+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G08/cart-record-frontier/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/cart-record-frontier"
}

2026-10-18T18:59:26.406195+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/cart-record-frontier"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-record-frontier",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:00:01.413003+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/full-suite-materialization"
}

2026-10-18T19:00:09.982925+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/full-suite-materialization"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "full-suite-materialization",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:01:07.442023+00:00 G08 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G08-stream-materialization",
      "--existing-snapshot"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G08/materialization-stage"
}

2026-10-18T19:01:21.632143+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_optional_mapping.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/optional-map-contracts"
}

2026-10-18T19:01:21.957587+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/optional-map-contracts"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "optional-map-contracts",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:02:02.160827+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_optional_mapping.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/optional-type-contracts"
}

2026-10-18T19:02:04.265259+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/optional-type-contracts"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "optional-type-contracts",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:02:18.940819+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G08/materialization-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "materialization-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:02:40.440259+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_optional_mapping.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/optional-compiled-context"
}

2026-10-18T19:02:41.411071+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/optional-compiled-context"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "optional-compiled-context",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:03:22.926078+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_optional_mapping.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/optional-boxed-kind"
}

2026-10-18T19:03:23.396322+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/optional-boxed-kind"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "optional-boxed-kind",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:03:23.430457+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G09/optional-cart-before-mvc/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/optional-cart-before-mvc"
}

2026-10-18T19:03:24.312994+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/optional-cart-before-mvc"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "optional-cart-before-mvc",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:03:33.908800+00:00 G09 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "cf789eb073102041e6a716932e98c63bc933bcb2d3a194986482a480bcec4b15",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "a8ed21300a0cf516c5c0f30016c57f58ae862bd6890291ae3451b084b21022fc",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "7e1b7ec150a4a9fa154e0704624127d0d4e2719710ac6a73bfba07e6866dfad2",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "b34e5d991df38f81b60c98f9f150b042ebbaf7d37246ead2733330fd1882cc43",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "3416d7bb07340317029ba37f7c56cac0fc3f9c27ed3880fe7e23db8c9feb79bf",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G09A-optional-map",
    "benchmark/overnight/G09/optional-boxed-kind",
    "benchmark/overnight/G09/optional-cart-before-mvc"
  ],
  "findings": [
    "Optional.map validates mapper before presence; proven empty skips callback, present invokes source, null result becomes empty, unknown presence explicitly stops. Factory input boxed kind is retained. Fourteen Optional/stream typing tests passed."
  ],
  "next_action": "Implement proven MVC specificity and distinct servlet/exception parameter bindings."
}

2026-10-18T19:04:47.764180+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_mvc_specific_handlers.py",
      "code/tests/test_http_server_failures.py",
      "code/tests/test_application_entry_boundary.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/mvc-specificity-bindings"
}

2026-10-18T19:04:48.169777+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/mvc-specificity-bindings"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "mvc-specificity-bindings",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:04:48.204442+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "GET",
      "--url",
      "/api/payments/999",
      "--output",
      "benchmark/overnight/G09/clean-absent-payment/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/clean-absent-payment"
}

2026-10-18T19:04:48.414535+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/clean-absent-payment"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "clean-absent-payment",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:06:19.757845+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_mvc_specific_handlers.py",
      "code/tests/test_http_server_failures.py",
      "code/tests/test_application_entry_boundary.py",
      "code/tests/test_http_map_values.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/mvc-source-throwable"
}

2026-10-18T19:06:20.238032+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/mvc-source-throwable"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "mvc-source-throwable",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:06:20.269209+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "GET",
      "--url",
      "/api/payments/999",
      "--output",
      "benchmark/overnight/G09/clean-absent-source-constructor/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/clean-absent-source-constructor"
}

2026-10-18T19:06:20.465732+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/clean-absent-source-constructor"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "clean-absent-source-constructor",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:06:38.053625+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "GET",
      "--url",
      "/api/payments/999",
      "--output",
      "benchmark/overnight/G09/clean-absent-servlet-kind/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/clean-absent-servlet-kind"
}

2026-10-18T19:06:38.321440+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/clean-absent-servlet-kind"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "clean-absent-servlet-kind",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:06:38.351232+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/full-suite-mvc"
}

2026-10-18T19:06:46.831930+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/full-suite-mvc"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "full-suite-mvc",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:08:18.822672+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_hashset_membership.py",
      "code/tests/test_mvc_specific_handlers.py",
      "code/tests/test_stream_materialization.py",
      "code/tests/test_http_map_values.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/diamond-source-typing"
}

2026-10-18T19:08:19.411975+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/diamond-source-typing"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "diamond-source-typing",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:09:55.833746+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_cart_profile.py",
      "--trace",
      "benchmark/overnight/G08/cart-record-frontier/results",
      "--output",
      "benchmark/overnight/G07/real-failure-v2-check/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/real-failure-v2-check"
}

2026-10-18T19:09:55.994718+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/real-failure-v2-check"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "real-failure-v2-check",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:09:56.026749+00:00 G07 verified

{
  "evidence_paths": [
    "benchmark/overnight/G07/final-checker-controls",
    "benchmark/overnight/G07/real-failure-v2-check",
    "validation_inputs/shopping-cart/oracle-v2.json",
    "development/cart-historical30"
  ],
  "findings": [
    "Positive eight-step fixture accepted and 22 meaningful mutations plus historical failed trace rejected; application boundary test verifies default filters still run. Version2 evaluator now evaluates real explicit/NL traces honestly, retains physical child-row invariant without requiring unproved dirty SQL.",
    "Real profiles remain failed pending semantics/producer linkage; this goal is checker acceptance only, not cart success."
  ],
  "unresolved": [],
  "next_goal": "G08"
}

2026-10-18T19:09:56.028738+00:00 G08 in_progress

{
  "evidence_paths": [
    "benchmark/stages/G08-stream-materialization",
    "benchmark/comparisons/G01-parent30--G08-stream-materialization.json",
    "benchmark/overnight/G08/cart-record-frontier"
  ],
  "findings": [
    "Actual clean producer returns both payment IDs and all source fields after implicit record canonical constructor fix. Complete TT submission stays 7e287a825030905abae479fe4ae2fe433545f86fee85e50294482e1f25516a10.",
    "Later full suite found ArrayList diamond callback type loss; fixed by source-only Collection<T> constructor inference and tested in G09/diamond-source-typing. Final broader suite still required."
  ],
  "next_goal": "G09"
}

2026-10-18T19:10:04.985039+00:00 G07 in_progress

{
  "findings": [
    "Withdrew premature verified journal entry: real evaluator exited 1 before emitting results; inspect recorded stderr and fix checker path/schema, then rerun before acceptance."
  ],
  "next_action": "Fix real-v2 checker runtime failure; require emitted evaluation and passing fixture/mutation gate before verified."
}

2026-10-18T19:10:14.587310+00:00 G07 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_cart_profile.py",
      "--trace",
      "benchmark/overnight/G08/cart-record-frontier/results",
      "--output",
      "benchmark/overnight/G07/missing-witnesses-are-failures/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G07/missing-witnesses-are-failures"
}

2026-10-18T19:10:14.673340+00:00 G07 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G07/missing-witnesses-are-failures"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "missing-witnesses-are-failures",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:10:41.974308+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/accepted-full-suite"
}

2026-10-18T19:10:50.391530+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/accepted-full-suite"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "accepted-full-suite",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:11:34.769881+00:00 G07 verified

{
  "evidence_paths": [
    "benchmark/overnight/G07/missing-witnesses-are-failures",
    "benchmark/overnight/G09/accepted-full-suite"
  ],
  "findings": [
    "Runtime schema failure fixed: missing NL state witnesses become explicit failures. Real evaluator emitted truthful failed explicit/NL profile; full fixture/mutation suite passes."
  ],
  "next_goal": "G08"
}

2026-10-18T19:11:34.772293+00:00 G08 verified

{
  "evidence_paths": [
    "benchmark/overnight/G09/accepted-full-suite",
    "benchmark/overnight/G09/diamond-source-typing"
  ],
  "findings": [
    "Full production/checker suite accepted after source diamond inference and nonintrusive HTTP body witness fix; Stream.toList values/types/immutability/source callbacks and both unordered alternatives retained. Remaining profile work is G09–G12, not terminal materialization."
  ],
  "next_goal": "G09"
}

2026-10-18T19:11:34.866791+00:00 G09 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "7b6242b394b6700f13011d74685e0d577318c8377a411ab097d488091185a443",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "7e1b7ec150a4a9fa154e0704624127d0d4e2719710ac6a73bfba07e6866dfad2",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "0cdc6ca97602b0622d727394bb9d82c1f7b32661e2b90852ac8d10c16a3968dc",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "2fefb804c5543363a3efbd9096fec1a7409d594d2a852896ddcd0406f9de378e",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "33b703f17e5c03fd280e493f9d22e28d174a8ffa82c4312e6a225ea7c2643533",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G09B-mvc-source-absence",
    "benchmark/overnight/G09/clean-absent-servlet-kind",
    "benchmark/overnight/G09/accepted-full-suite"
  ],
  "findings": [
    "Clean GET999 produces one source-derived 404 PAYMENT_NOT_FOUND, actual message and URI, no writes, no warnings. MVC specific hierarchy match and distinct servlet parameter binding proven.",
    "Error DTO nullable details remains unknown in current wire view; no false null/known-empty assertion. Repeat-refund 409 awaits transferred state G12."
  ],
  "unresolved": [
    "Repeat-refund refusal on transferred real cart state remains G12 acceptance dependency."
  ],
  "next_goal": "G10"
}

2026-10-18T19:11:34.909671+00:00 G09 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G09B-mvc-source-absence"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G09/mvc-source-stage"
}

2026-10-18T19:12:45.175268+00:00 G09 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G09/mvc-source-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "mvc-source-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:14:06.323399+00:00 G10 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "PATCH",
      "--url",
      "/api/payments/21/refund",
      "--output",
      "benchmark/overnight/G10/cart-patch-frontier/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G10/cart-patch-frontier"
}

2026-10-18T19:14:06.646518+00:00 G10 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G10/cart-patch-frontier"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-patch-frontier",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:15:46.364356+00:00 G10 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_patch_source_deployment.py",
      "code/tests/test_http_uri_templates.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G10/patch-source-port-controls"
}

2026-10-18T19:15:47.376944+00:00 G10 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G10/patch-source-port-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "patch-source-port-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:16:38.236929+00:00 G10 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_patch_source_deployment.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G10/patch-datastore-error-paths"
}

2026-10-18T19:16:38.693696+00:00 G10 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G10/patch-datastore-error-paths"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "patch-datastore-error-paths",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:16:38.727976+00:00 G10 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G10/full-suite-transport"
}

2026-10-18T19:16:47.828943+00:00 G10 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G10/full-suite-transport"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "full-suite-transport",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:17:21.196605+00:00 G10 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_patch_source_deployment.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G10/accepted-transport-controls"
}

2026-10-18T19:17:21.606309+00:00 G10 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G10/accepted-transport-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "accepted-transport-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:17:21.638677+00:00 G10 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G10-source-patch-deployment"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G10/transport-stage"
}

2026-10-18T19:18:32.483581+00:00 G10 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G10/transport-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "transport-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:19:01.492311+00:00 G10 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "b22e8bb0f66da35ff069a5076ebcf941a5d8f0865d186f61a379f2f4a5b50278",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "4ea10a9e8b5b40c3d0574820be1bc2900bd311da5ea078c616b5f793fc823b9f",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "7e1b7ec150a4a9fa154e0704624127d0d4e2719710ac6a73bfba07e6866dfad2",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "abe9fd838038e444f6532eed8dc5c2cc05ba70841b8a444d5d90492779a53727",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "b68ea07a309d0861cfccbae083bba350340b2cc7b63e775a9d91abc7e0f52119",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "7a96975dc39c1acef4b5ee6d7df10730b95f1b5ad2862d36479edb0bf388849c",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "33b703f17e5c03fd280e493f9d22e28d174a8ffa82c4312e6a225ea7c2643533",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G10-source-patch-contract",
    "benchmark/overnight/G10/accepted-transport-controls",
    "benchmark/overnight/G10/cart-patch-frontier",
    "validation_inputs/shopping-cart/deployment-context-v2.json"
  ],
  "findings": [
    "Ten transport tests pass: direct Apache @Bean/constructor proof, independent same-path servers on distinct ports, actual server callback with Void client discard, datastore change plus untouched row, wrong/colliding ports, unknown environment/factory, Simple factory no-send, server404/500.",
    "Real refund reaches correct order-service endpoint from source/config, stops at compact OrderId record constructor. No completed refund claim yet."
  ],
  "unresolved": [
    "Guard-only compact records and typed reduce/BigDecimal are next source frontiers in G11."
  ],
  "next_goal": "G11"
}

2026-10-18T19:19:49.221711+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_stream_materialization.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/compact-record-guards"
}

2026-10-18T19:19:49.654964+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/compact-record-guards"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "compact-record-guards",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:19:49.689319+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "PATCH",
      "--url",
      "/api/payments/21/refund",
      "--output",
      "benchmark/overnight/G11/cart-record-guard-frontier/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/cart-record-guard-frontier"
}

2026-10-18T19:19:50.258595+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/cart-record-guard-frontier"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-record-guard-frontier",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:23:23.327958+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_typed_reduce_records.py",
      "code/tests/test_stream_materialization.py",
      "code/tests/test_stream_parameter_types.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/reduce-record-numeric-contracts"
}

2026-10-18T19:23:24.460591+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/reduce-record-numeric-contracts"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "reduce-record-numeric-contracts",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:23:59.232744+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "order-service",
      "--verb",
      "GET",
      "--url",
      "/api/orders/11",
      "--output",
      "benchmark/overnight/G11/clean-order-response/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/clean-order-response"
}

2026-10-18T19:23:59.233013+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "PATCH",
      "--url",
      "/api/payments/21/refund",
      "--output",
      "benchmark/overnight/G11/refund-reduce-frontier/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/refund-reduce-frontier"
}

2026-10-18T19:23:59.699651+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/clean-order-response"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "clean-order-response",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:23:59.753863+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/refund-reduce-frontier"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "refund-reduce-frontier",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:27:57.299254+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "order-service",
      "--verb",
      "GET",
      "--url",
      "/api/orders/11",
      "--output",
      "benchmark/overnight/G11/nested-record-order-response/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/nested-record-order-response"
}

2026-10-18T19:27:57.649398+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/nested-record-order-response"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "nested-record-order-response",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:28:36.024086+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_typed_reduce_records.py",
      "code/tests/test_review_records.py",
      "code/tests/test_type_visibility.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/constructor-arity-projection"
}

2026-10-18T19:28:36.474051+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/constructor-arity-projection"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "constructor-arity-projection",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:28:36.507560+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "PATCH",
      "--url",
      "/api/payments/21/refund",
      "--output",
      "benchmark/overnight/G11/refund-after-source-arity/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/refund-after-source-arity"
}

2026-10-18T19:28:36.832765+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/refund-after-source-arity"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "refund-after-source-arity",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:29:14.028490+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "PATCH",
      "--url",
      "/api/payments/21/refund",
      "--output",
      "benchmark/overnight/G11/refund-finite-witness/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/refund-finite-witness"
}

2026-10-18T19:29:14.429879+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/refund-finite-witness"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "refund-finite-witness",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:31:12.391039+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/probe_cart_request.py",
      "--module",
      "payment-service",
      "--verb",
      "PATCH",
      "--url",
      "/api/payments/21/refund",
      "--output",
      "benchmark/overnight/G11/refund-storage-frontier/result.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/refund-storage-frontier"
}

2026-10-18T19:31:12.802142+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/refund-storage-frontier"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "refund-storage-frontier",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:31:12.837036+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/full-suite-source-response"
}

2026-10-18T19:31:21.325935+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/full-suite-source-response"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "full-suite-source-response",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:32:29.235394+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_core.py",
      "code/tests/test_written_composites.py",
      "code/tests/test_typed_reduce_records.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/existing-nested-composites-preserved"
}

2026-10-18T19:32:29.820751+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/existing-nested-composites-preserved"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "existing-nested-composites-preserved",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:32:29.852437+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G12/first-full-chain/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/first-full-chain"
}

2026-10-18T19:32:30.383733+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/first-full-chain"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "first-full-chain",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:33:05.912910+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G12/chain-with-valid-guard-events/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/chain-with-valid-guard-events"
}

2026-10-18T19:33:06.791716+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/chain-with-valid-guard-events"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "chain-with-valid-guard-events",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:33:12.387963+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_cart_profile.py",
      "--trace",
      "benchmark/overnight/G12/chain-with-valid-guard-events/results",
      "--output",
      "benchmark/overnight/G12/current-chain-evaluation/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/current-chain-evaluation"
}

2026-10-18T19:33:12.482315+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/current-chain-evaluation"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "current-chain-evaluation",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:33:23.646722+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/accepted-source-response-suite"
}

2026-10-18T19:33:32.194630+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/accepted-source-response-suite"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "accepted-source-response-suite",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:34:15.183456+00:00 G11 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "b212c65e9d1bc7c45ebd70533368328c969ce66d975736cbe49ce19dfed8e08d",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "81f812bf0fafcb242b1fcca61319fa35f53afa32f30badbdb0197b6af1f79b57",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "7f7fb11e4a0cc33280c0a7ab803f181d320b4a014daa1f2fb6b03287add08eae",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "7e1b7ec150a4a9fa154e0704624127d0d4e2719710ac6a73bfba07e6866dfad2",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "e06a2202bee3e212d3add3027c860116a018fa55c80512173c3373f6ae1fbffa",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "dc7170658fdca9b6dd39c258cd040c16ed4e5dd897ea5c9431624ea3cc473dcd",
    "analyzer/provenance.py": "5cbcaf87653a9ec1ddb4e409eb1fb23b4b604ba9551b80e1c8e274faaae4e124",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "a5a352771974be4fe202fd4e7b4cad29cfdfbb747975925563184ded9e05be92",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "e824389ddf4548ca85c95603f01f4deeca03875b1fefac3bfcd105a992882061",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "fedab04fb3796d9ec63277df01d7b735860a579dcbce23869d4b48457fa82f31",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G11-source-response-before-nl",
    "benchmark/overnight/G12/current-chain-evaluation",
    "benchmark/overnight/G11/accepted-source-response-suite",
    "benchmark/overnight/G11/reduce-record-numeric-contracts"
  ],
  "findings": [
    "Explicit cart chain accepted by v2 checker: source refund/revert, rereads, 409, 404, unchanged other rows and computed total12.50/detail6.25×2. Thirty-eight focused numeric/stream tests and full pre-storage-refinement suite evidence retained; latest refinements require full suite again.",
    "New bounded semantics: guard-only compact records, inherited record getters, unbound source method references, binary typed reduce, exact SQL decimal lexemes, nested source-only record type metadata without new method IDs, source-arity refinement, and scalar enum/association storage with unchanged child guards."
  ],
  "unresolved": [
    "Latest G11 edits require broader suite after storage and event-record schema fixes.",
    "NL still lacks status selection/focus/relation IDs and before-state/provenance witnesses."
  ],
  "next_goal": "G12"
}

2026-10-18T19:34:25.130966+00:00 G11 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G11-source-record-reduce-response"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G11/source-response-stage"
}

2026-10-18T19:35:14.947982+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G12/source-enum-focus-flow/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/source-enum-focus-flow"
}

2026-10-18T19:35:15.931759+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/source-enum-focus-flow"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "source-enum-focus-flow",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:35:38.299127+00:00 G11 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G11/source-response-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "source-response-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:36:18.047559+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G12/enum-adjective-producer/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/enum-adjective-producer"
}

2026-10-18T19:36:18.688970+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/enum-adjective-producer"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "enum-adjective-producer",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:38:00.993758+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/overnight/G12/state-and-producer-witness/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/state-and-producer-witness"
}

2026-10-18T19:38:01.734925+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/state-and-producer-witness"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "state-and-producer-witness",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:38:19.748096+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_cart_profile.py",
      "--trace",
      "benchmark/overnight/G12/state-and-producer-witness/results",
      "--output",
      "benchmark/overnight/G12/linked-full-chain-evaluation/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/linked-full-chain-evaluation"
}

2026-10-18T19:38:19.860526+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/linked-full-chain-evaluation"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "linked-full-chain-evaluation",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:39:47.318983+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_source_state_reference_flow.py",
      "checks/tests/test_cart_evaluator_v2.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/independent-state-focus-controls"
}

2026-10-18T19:39:48.310799+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/independent-state-focus-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "independent-state-focus-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:40:24.559235+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/full-suite-linked-state"
}

2026-10-18T19:40:33.199497+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/full-suite-linked-state"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "full-suite-linked-state",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:41:07.170673+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_tt_causal_probes.py",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G13/current-tt-causal-probes/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/current-tt-causal-probes"
}

2026-10-18T19:41:08.305362+00:00 G09 verified

{
  "evidence_paths": [
    "benchmark/overnight/G12/linked-full-chain-evaluation",
    "benchmark/overnight/G12/state-and-producer-witness",
    "benchmark/overnight/G12/full-suite-linked-state"
  ],
  "findings": [
    "Full explicit and NL real-source profile accepted: server result12.50/details, transferred 409 before save/remote, independent404, valid actual producer IDs and unchanged other rows. Required subset only; no full IoU or new holdout claim."
  ],
  "unresolved": [],
  "next_goal": "G12"
}

2026-10-18T19:41:08.308075+00:00 G10 verified

{
  "evidence_paths": [
    "benchmark/overnight/G12/linked-full-chain-evaluation",
    "benchmark/overnight/G12/state-and-producer-witness",
    "benchmark/overnight/G12/full-suite-linked-state"
  ],
  "findings": [
    "Full explicit and NL real-source profile accepted: server result12.50/details, transferred 409 before save/remote, independent404, valid actual producer IDs and unchanged other rows. Required subset only; no full IoU or new holdout claim."
  ],
  "unresolved": [],
  "next_goal": "G12"
}

2026-10-18T19:41:08.310492+00:00 G11 verified

{
  "evidence_paths": [
    "benchmark/overnight/G12/linked-full-chain-evaluation",
    "benchmark/overnight/G12/state-and-producer-witness",
    "benchmark/overnight/G12/full-suite-linked-state"
  ],
  "findings": [
    "Full explicit and NL real-source profile accepted: server result12.50/details, transferred 409 before save/remote, independent404, valid actual producer IDs and unchanged other rows. Required subset only; no full IoU or new holdout claim."
  ],
  "unresolved": [],
  "next_goal": "G12"
}

2026-10-18T19:41:08.382856+00:00 G12 in_progress

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "a98d02eafdbd5e12feada731d138d6183626ca37bb3ea9074faae9f0a7501119",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "034d60f7655d5425b1e73879a8a7d6c5c16fe1661bcc232290a409c22e52ab85",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "1e8de7b81313666ec52ba56aec749c0382af271c3a2d153a54d343596934d318",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "7e1b7ec150a4a9fa154e0704624127d0d4e2719710ac6a73bfba07e6866dfad2",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "e06a2202bee3e212d3add3027c860116a018fa55c80512173c3373f6ae1fbffa",
    "analyzer/portable.py": "3d2f99534b751a7ad21f81d845fd3ee04c01e0dd2e86003486ee325a5d18dfeb",
    "analyzer/project.py": "dc7170658fdca9b6dd39c258cd040c16ed4e5dd897ea5c9431624ea3cc473dcd",
    "analyzer/provenance.py": "ac977443481bc2f8c55ea1101fe02377fa9f0cf8a14532d1403a2e0ee2b5975b",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "ee4376750b982b3a97f5134101a9a6eb58e9d4870c2fde5b197d217e5ed9b783",
    "analyzer/source_conversions.py": "0a086d40e2ebe82fd1226a735e523aead65bd916a44c3d234c44fe65084ab58b",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "e824389ddf4548ca85c95603f01f4deeca03875b1fefac3bfcd105a992882061",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "2266901751079becc6e2e717980aa0f30758d81d45ef01178465e0bfeb27b472",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "d86d2a2001319a2ff6e3c62d13b741d607d98a6fa856c88007966fc5a12f848f",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_state_reference_flow.py": "b0d731b15aec885fefae79640f7080beb2175490218b8ba45d607a3a5389686e",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "fedab04fb3796d9ec63277df01d7b735860a579dcbce23869d4b48457fa82f31",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G12-linked-explicit-and-nl",
    "benchmark/overnight/G12/linked-full-chain-evaluation",
    "benchmark/overnight/G12/independent-state-focus-controls",
    "benchmark/overnight/G12/full-suite-linked-state"
  ],
  "findings": [
    "Both eight-step profiles accepted with actual typed source bindings; independent enum/focus/related-ID/order negatives passed and full1908-test suite passed.",
    "NL before/after states and selected-object provenance are exposed. Checker now compares modeled application state at ambiguity, excluding analysis-only diagnostic notes; frozen SQL/state/effect obligations remain."
  ],
  "unresolved": [
    "Run final post-regression cart mutations and broader independent journeys in G14; G12 final gate then verified."
  ],
  "next_goal": "G13"
}

2026-10-18T19:41:13.712486+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/current-tt-causal-probes"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "current-tt-causal-probes",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:44:50.237184+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_ordered_association_columns.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/ordered-association-contracts"
}

2026-10-18T19:44:51.388522+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/ordered-association-contracts"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "ordered-association-contracts",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:44:51.421970+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_tt_causal_probes.py",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G13/tt-known-route-order/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/tt-known-route-order"
}

2026-10-18T19:44:59.027319+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/tt-known-route-order"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-known-route-order",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:45:54.489407+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_ordered_association_columns.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/force-source-association-load"
}

2026-10-18T19:45:54.869851+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/force-source-association-load"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "force-source-association-load",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:45:54.914615+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/trace_map_certificates.py",
      "--diagnostics",
      "benchmark/overnight/G13/tt-map-after-order-refusals/certificates.json",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G13/tt-map-after-order-refusals/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/tt-map-after-order-refusals"
}

2026-10-18T19:46:24.463169+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/tt-map-after-order-refusals"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-map-after-order-refusals",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:48:16.635486+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_proof_casts.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/generated-getter-proof-controls"
}

2026-10-18T19:48:18.996225+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/generated-getter-proof-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "generated-getter-proof-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:48:19.029672+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_tt_causal_probes.py",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G13/tt-generated-field-getters/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/tt-generated-field-getters"
}

2026-10-18T19:48:28.422078+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/tt-generated-field-getters"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-generated-field-getters",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:49:28.016107+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_proof_casts.py",
      "code/tests/test_ordered_association_columns.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/generated-accessor-consumer-contracts"
}

2026-10-18T19:49:29.888061+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/generated-accessor-consumer-contracts"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "generated-accessor-consumer-contracts",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:49:29.920056+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_tt_causal_probes.py",
      "--challenge",
      "../../tt-challenge",
      "--output",
      "benchmark/overnight/G13/tt-generated-setter-consumer/probes.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/tt-generated-setter-consumer"
}

2026-10-18T19:49:38.309879+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/tt-generated-setter-consumer"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "tt-generated-setter-consumer",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:49:57.806232+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests/test_bulk_consumer_types.py",
      "code/tests/test_commuting_map_filter.py",
      "code/tests/test_map_proof_casts.py",
      "code/tests/test_ordered_association_columns.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/declared-lombok-accessor-controls"
}

2026-10-18T19:49:59.592768+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/declared-lombok-accessor-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "declared-lombok-accessor-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:51:27.798008+00:00 G02 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/order_completion_probe.py",
      "--output",
      "benchmark/overnight/G02/isolated-order-completion-counters/results"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G02/isolated-order-completion-counters"
}

2026-10-18T19:51:28.480152+00:00 G02 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G02/isolated-order-completion-counters"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "isolated-order-completion-counters",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:52:04.021131+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/accepted-map-order-suite"
}

2026-10-18T19:52:12.753829+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/accepted-map-order-suite"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "accepted-map-order-suite",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:53:18.655077+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G13-live-route-filter"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/accepted-tt-integration-stage"
}

2026-10-18T19:53:19.767331+00:00 G02 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/finish_s6_ledger.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G02/reconciled-causal-ledger"
}

2026-10-18T19:53:19.821498+00:00 G02 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G02/reconciled-causal-ledger"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "reconciled-causal-ledger",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:54:51.956610+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/accepted-tt-integration-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "accepted-tt-integration-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:55:17.648472+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/compare_public_corpus.py",
      "--fixtures",
      "validation_inputs/legacy-real",
      "--output",
      "benchmark/legacy-final",
      "--candidate-only"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/legacy-public-controls"
}

2026-10-18T19:55:18.284267+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/legacy-public-controls"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "legacy-public-controls",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:56:00.578933+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_regression_gate.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/independent-profile-regressions"
}

2026-10-18T19:56:02.463309+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/independent-profile-regressions"
  ],
  "actual_exit_status": 1,
  "tests_run": [
    {
      "label": "independent-profile-regressions",
      "returncode": 1,
      "timed_out": false
    }
  ]
}

2026-10-18T19:58:25.356688+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/compare_public_corpus.py",
      "--fixtures",
      "validation_inputs/legacy-real",
      "--output",
      "benchmark/legacy-refined",
      "--candidate-only"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/legacy-null-association-rerun"
}

2026-10-18T19:58:26.045930+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/legacy-null-association-rerun"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "legacy-null-association-rerun",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:58:26.080036+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_additional_journey.py",
      "--input",
      "validation_inputs/piggymetrics",
      "--output",
      "benchmark/additional-refined"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/partial-typed-symbol-rerun"
}

2026-10-18T19:58:26.355913+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/partial-typed-symbol-rerun"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "partial-typed-symbol-rerun",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:59:09.080252+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_legacy_state.py",
      "--reports",
      "benchmark/legacy-refined",
      "--output",
      "benchmark/legacy-refined/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/legacy-refined-state-gate"
}

2026-10-18T19:59:09.148635+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/legacy-refined-state-gate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "legacy-refined-state-gate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:59:09.181519+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_additional_journey.py",
      "--input",
      "validation_inputs/piggymetrics",
      "--oracle",
      "development/oracles/parent29/piggymetrics-additional.oracle-v3.json",
      "--trace",
      "benchmark/additional-refined/trace.json",
      "--output",
      "benchmark/additional-refined/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/additional-refined-value-gate"
}

2026-10-18T19:59:09.229317+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/additional-refined-value-gate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "additional-refined-value-gate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T19:59:09.259917+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_semantic_projection.py",
      "--input",
      "validation_inputs/piggymetrics",
      "--oracle",
      "development/oracles/parent29/piggymetrics-additional.oracle-v3.json",
      "--trace",
      "benchmark/additional-refined/trace.json",
      "--output",
      "benchmark/additional-refined/semantic-checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/additional-refined-semantic-gate"
}

2026-10-18T19:59:09.312519+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/additional-refined-semantic-gate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "additional-refined-semantic-gate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:03:12.214142+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_additional_mutations.py",
      "--input",
      "validation_inputs/piggymetrics",
      "--oracle",
      "development/oracles/parent29/piggymetrics-additional.oracle-v3.json",
      "--trace",
      "benchmark/additional-refined/trace.json",
      "--output",
      "benchmark/additional-refined/mutations"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/additional-refined-mutations"
}

2026-10-18T20:03:12.499463+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/additional-refined-mutations"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "additional-refined-mutations",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:04:06.488494+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "code/tests/test_typed_reduce_records.py",
      "code/tests/test_aggregate_null_save.py",
      "checks/tests/test_cart_evaluator_v2.py",
      "checks/tests/test_cart_evaluator_v3.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/refined-regression-counterexamples"
}

2026-10-18T20:04:07.017293+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/refined-regression-counterexamples"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "refined-regression-counterexamples",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:04:19.780318+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_cart_profile.py",
      "--output",
      "benchmark/cart-transfer-final"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/cart-final-source-chain"
}

2026-10-18T20:04:20.447952+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/cart-final-source-chain"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-final-source-chain",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:04:47.202236+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_cart_profile.py",
      "--trace",
      "benchmark/cart-transfer-final",
      "--output",
      "benchmark/cart-transfer-final/checks.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/cart-final-evaluator-v3"
}

2026-10-18T20:04:47.320409+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/cart-final-evaluator-v3"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-final-evaluator-v3",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:06:12.099732+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/final-code-and-checker-suite"
}

2026-10-18T20:06:20.802283+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/final-code-and-checker-suite"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "final-code-and-checker-suite",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:07:24.120205+00:00 G12 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_cart_mutations.py",
      "--trace",
      "benchmark/cart-transfer-final",
      "--output",
      "benchmark/cart-transfer-final/mutations"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G12/cart-final-actual-mutations"
}

2026-10-18T20:07:24.661531+00:00 G12 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G12/cart-final-actual-mutations"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "cart-final-actual-mutations",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:07:24.717284+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/reconcile_stages.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/all-stage-baseline-and-predecessor"
}

2026-10-18T20:07:42.144053+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/all-stage-baseline-and-predecessor"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "all-stage-baseline-and-predecessor",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:07:53.448841+00:00 G02 verified

{
  "evidence_paths": [
    "benchmark/overnight/G02/causal-ledger-v2",
    "benchmark/overnight/G02/isolated-order-completion-counters",
    "benchmark/comparisons/G01-parent30--G02-bulk-contract-only.json"
  ],
  "findings": [
    "Observer preserves exact parent30 S6 prediction; station/train_type first invalidated by AnalysisBoundary writable-closure fallback (events9/122), later joins propagate unknown. No SQL write inferred from widening.",
    "Historical six union removals first C1 step8; twelve other step1 removals persist step7. Single-contract ablation and isolated order/completion-reserve MRE distinguish three causes."
  ],
  "unresolved": [
    "Default order/completion reserve remains coupled; G06 integration rejected. Hidden per-edge S6 truth unavailable."
  ],
  "next_goal": "G05"
}

2026-10-18T20:07:53.452373+00:00 G05 verified

{
  "evidence_paths": [
    "benchmark/overnight/G13/declared-lombok-accessor-controls",
    "benchmark/overnight/G13/tt-generated-setter-consumer",
    "benchmark/stages/G13-live-route-filter"
  ],
  "findings": [
    "Shared reference compatibility rejects Array-as-List no-op proof. Live six-group source Map filter executes using source-generated getter contracts and known values; effectful/throw/opaque cases retain explicit boundaries."
  ],
  "next_goal": "G12"
}

2026-10-18T20:07:53.549126+00:00 G12 verified

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "a98d02eafdbd5e12feada731d138d6183626ca37bb3ea9074faae9f0a7501119",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "034d60f7655d5425b1e73879a8a7d6c5c16fe1661bcc232290a409c22e52ab85",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "1e8de7b81313666ec52ba56aec749c0382af271c3a2d153a54d343596934d318",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "c4552180dd0b2cef2c1a59271c8e1f323108b6cbea16360f2510613fe8d60f61",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/measurements.py": "c664b282ec668fc14c2f150a42521d54902592e51438566c55ec55c16c5e8ebe",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "f45bcb247222e87c2fe57a8754dbadd1e589c2ea6e0f86764ddc8efe1ce8c82b",
    "analyzer/portable.py": "de8bd68da8fe548c63ee4e1639f5fc26d520a7e2898e7897e14f199a712152dd",
    "analyzer/project.py": "949cf6569bca9510b6afe6072b82264e266ee22b51b65faa40efb802d112a971",
    "analyzer/provenance.py": "ac977443481bc2f8c55ea1101fe02377fa9f0cf8a14532d1403a2e0ee2b5975b",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/reporting.py": "62fa877894af6f8d377a3e6ca9355855809cf4e9c62a2a0431e7f4a89ce5e76e",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "ee4376750b982b3a97f5134101a9a6eb58e9d4870c2fde5b197d217e5ed9b783",
    "analyzer/source_conversions.py": "80b0967423c036ced1c8e2ac36c2c2d8a3c0ec8881e0bdf0f693120be45b38cc",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "d04804692e8693d9ced18717d8fa478d90f191786031a633f857da48c2d53864",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_aggregate_null_save.py": "12f8c9eecb6fe0cbe96455d507b643c0037e653c2d5e386b9a00c04e2f549793",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "41e03742b3b4196ebd32012fdd925eeef52119c3167127b6c0089ddbbdf3a98e",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "9f6c3d8b2e98f67ca010655c7fb2bcddff7d3394c428aa89de5536970714f2a0",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_ordered_association_columns.py": "57c44f693e26f2c47de150e6b7638902530ec584bab964562f6358417d517a8a",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_reporting_measurements.py": "a20435bdad05b657a2814d6bae03a828eccd0febd73c1156404695b79956942f",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_state_reference_flow.py": "b0d731b15aec885fefae79640f7080beb2175490218b8ba45d607a3a5389686e",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "056d21470a9fdcb3caf0bcae2ad55b1b6dccdc1caffbe6557dc5aa41e5c7a892",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G12-cart-v3-actual-pass",
    "benchmark/cart-transfer-final",
    "benchmark/overnight/G14/final-code-and-checker-suite"
  ],
  "findings": [
    "Explicit and NL eight-step cart both pass version3 values/native Long arguments/controller/wire/state/remote/source mapper obligations; 47 actual-trace mutations rejected before NL normalization.",
    "Version3 adds source-derived postimplementation regression obligations; it is not a fresh blind oracle."
  ],
  "unresolved": [
    "JWT/security outside explicit application-after-authentication boundary. Required graph subset, not complete precision/IoU."
  ],
  "next_goal": "G14"
}

2026-10-18T20:07:53.597663+00:00 G16 in_progress

{
  "what_changed": [
    "Platform-aware raw RSS units shared by portable and prepared runner; finite diagnostic cycle references preserve inference heap."
  ],
  "next_action": "Run unchanged parent30 and candidate serially in the same Python process environment, then repeated prepared analysis."
}

2026-10-18T20:07:53.651181+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G16-parent30-paired",
      "--existing-snapshot"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/fair-parent30"
}

2026-10-18T20:09:20.932222+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/fair-parent30"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "fair-parent30",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:09:39.743959+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G16-candidate-final"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/fair-candidate"
}

2026-10-18T20:09:53.588142+00:00 G15 not_run

{
  "evidence_paths": [
    "benchmark/holdout-availability.json"
  ],
  "findings": [
    "No complete genuinely new real Java/Spring source package with an already supplied skeleton, initial context, explicit+NL scenarios and a source-frozen independent checker/oracle was supplied or found in the checked input corpus."
  ],
  "unresolved": [
    "new real application source/config at a pinned revision",
    "ready graph skeleton for that application",
    "declared deployment/authentication boundary and initial DB/context",
    "explicit and NL stateful selection→mutation→remote→reread scenarios including refusal/ambiguity",
    "source-derived pre-result oracle and negative-mutation checker"
  ],
  "tests_not_run": [
    "Fresh independent real application holdout; required complete input package is absent."
  ],
  "next_goal": "G16"
}

2026-10-18T20:11:20.641510+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/fair-candidate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "fair-candidate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:11:44.128324+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/repeat_prepared.py",
      "--source",
      "../../tt-challenge/targets/trainticket",
      "--skeleton",
      "../../tt-challenge/skeleton/trainticket.json.gz",
      "--context",
      "../../tt-challenge/context",
      "--scenarios",
      "../../tt-challenge/scenarios",
      "--expected",
      "benchmark/stages/G16-candidate-final/submission.json",
      "--output",
      "benchmark/repeated-analysis-final.json",
      "--repetitions",
      "2"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/repeated-prepared-final"
}

2026-10-18T20:13:39.524061+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/repeated-prepared-final"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "repeated-prepared-final",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:13:56.368267+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/profile_report_write.py",
      "--stage",
      "G16-candidate-final",
      "--output",
      "benchmark/report-phase-profile"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/report-phase-local-pair"
}

2026-10-18T20:14:04.463086+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/report-phase-local-pair"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "report-phase-local-pair",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:14:29.615259+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "code/tests/test_reporting_measurements.py",
      "checks/tests/test_archive_support.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/report-fastpath-and-archive-controls"
}

2026-10-18T20:14:29.958448+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/report-fastpath-and-archive-controls"
  ],
  "actual_exit_status": 2,
  "tests_run": [
    {
      "label": "report-fastpath-and-archive-controls",
      "returncode": 2,
      "timed_out": false
    }
  ]
}

2026-10-18T20:14:38.428600+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "code/tests/test_reporting_measurements.py",
      "checks/tests/test_archive_support.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/report-fastpath-and-archive-controls-v2"
}

2026-10-18T20:14:39.446225+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/report-fastpath-and-archive-controls-v2"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "report-fastpath-and-archive-controls-v2",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:14:49.804086+00:00 G16 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/stage_benchmark.py",
      "G16-report-fastpath"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G16/report-fastpath-accepted-stage"
}

2026-10-18T20:16:22.254612+00:00 G16 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G16/report-fastpath-accepted-stage"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "report-fastpath-accepted-stage",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:16:50.442155+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "code/tests",
      "checks/tests"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/exact-final-all-unit-checkers"
}

2026-10-18T20:16:50.445702+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/run_regression_gate.py",
      "--output",
      "benchmark/regressions-final"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/exact-final-independent-gate"
}

2026-10-18T20:16:54.818304+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/exact-final-independent-gate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "exact-final-independent-gate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:16:59.763174+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/exact-final-all-unit-checkers"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "exact-final-all-unit-checkers",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:17:44.738563+00:00 G18 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/prepare_final.py",
      "--stage",
      "G16-report-fastpath"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G18/freeze-measured-candidate"
}

2026-10-18T20:17:44.909710+00:00 G18 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G18/freeze-measured-candidate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "freeze-measured-candidate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:17:57.819331+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_integrity.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/final-protected-integrity"
}

2026-10-18T20:17:57.823017+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_scope.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/final-scope-review"
}

2026-10-18T20:17:57.826950+00:00 G13 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/summarize_tt_frontier.py",
      "--stage",
      "G16-report-fastpath",
      "--output",
      "benchmark/tt-frontier.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G13/final-TT-source-frontier"
}

2026-10-18T20:17:58.091695+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/final-scope-review"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "final-scope-review",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:17:59.004492+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/compare_stages.py",
      "G01-parent30",
      "G16-report-fastpath"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/compare-final-from-G01-parent30"
}

2026-10-18T20:17:59.700102+00:00 G13 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G13/final-TT-source-frontier"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "final-TT-source-frontier",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:18:00.898652+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/compare-final-from-G01-parent30"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "compare-final-from-G01-parent30",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:18:00.932969+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/compare_stages.py",
      "G13-live-route-filter",
      "G16-report-fastpath"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/compare-final-from-G13-live-route-filter"
}

2026-10-18T20:18:02.983254+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/compare-final-from-G13-live-route-filter"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "compare-final-from-G13-live-route-filter",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:18:03.017298+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/compare_stages.py",
      "G16-candidate-final",
      "G16-report-fastpath"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/compare-final-from-G16-candidate-final"
}

2026-10-18T20:18:04.175105+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/final-protected-integrity"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "final-protected-integrity",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:18:04.955511+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/compare-final-from-G16-candidate-final"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "compare-final-from-G16-candidate-final",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:19:06.552455+00:00 G14 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/final_acceptance.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G14/final-acceptance-v31"
}

2026-10-18T20:19:07.624054+00:00 G13 verified

{
  "evidence_paths": [
    "benchmark/tt-frontier.json",
    "benchmark/comparisons/G01-parent30--G16-report-fastpath.json",
    "benchmark/overnight/G13/tt-generated-setter-consumer"
  ],
  "findings": [
    "Live six-group Map filter observed on known search inputs. Full103 source/value/completion comparison and real UI payment payload provenance recorded.",
    "Acceptance follows G13 alternative: precise remaining TT producer frontier, not a completed NL search→booking→payment chain. Isolated payment probes remain distinct."
  ],
  "unresolved": [
    "Source Set<Ticket> equality/hash, remaining distance/list consumers and earlier S6 unknown state stop the full TT chain. No hidden IoU claim."
  ],
  "next_goal": "G14"
}

2026-10-18T20:19:07.671434+00:00 G16 verified

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "a98d02eafdbd5e12feada731d138d6183626ca37bb3ea9074faae9f0a7501119",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "034d60f7655d5425b1e73879a8a7d6c5c16fe1661bcc232290a409c22e52ab85",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "1e8de7b81313666ec52ba56aec749c0382af271c3a2d153a54d343596934d318",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "c4552180dd0b2cef2c1a59271c8e1f323108b6cbea16360f2510613fe8d60f61",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/measurements.py": "c664b282ec668fc14c2f150a42521d54902592e51438566c55ec55c16c5e8ebe",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "f45bcb247222e87c2fe57a8754dbadd1e589c2ea6e0f86764ddc8efe1ce8c82b",
    "analyzer/portable.py": "4f535b1932568fee40dac328fd829c6452056362876a0920e50ad6d2f855feb7",
    "analyzer/project.py": "949cf6569bca9510b6afe6072b82264e266ee22b51b65faa40efb802d112a971",
    "analyzer/provenance.py": "ac977443481bc2f8c55ea1101fe02377fa9f0cf8a14532d1403a2e0ee2b5975b",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/reporting.py": "06a46d0d3c92f3bd957dae0ffb828e3d270ca6e3a488025ebf1af3e2426b88f6",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "ee4376750b982b3a97f5134101a9a6eb58e9d4870c2fde5b197d217e5ed9b783",
    "analyzer/source_conversions.py": "80b0967423c036ced1c8e2ac36c2c2d8a3c0ec8881e0bdf0f693120be45b38cc",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "d04804692e8693d9ced18717d8fa478d90f191786031a633f857da48c2d53864",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_aggregate_null_save.py": "12f8c9eecb6fe0cbe96455d507b643c0037e653c2d5e386b9a00c04e2f549793",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "41e03742b3b4196ebd32012fdd925eeef52119c3167127b6c0089ddbbdf3a98e",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "9f6c3d8b2e98f67ca010655c7fb2bcddff7d3394c428aa89de5536970714f2a0",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_ordered_association_columns.py": "57c44f693e26f2c47de150e6b7638902530ec584bab964562f6358417d517a8a",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_reporting_measurements.py": "9a19519a404776cdd340bc4abc139f18a15ddb62770a40a7caf392bdb5c3d0f0",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_state_reference_flow.py": "b0d731b15aec885fefae79640f7080beb2175490218b8ba45d607a3a5389686e",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "056d21470a9fdcb3caf0bcae2ad55b1b6dccdc1caffbe6557dc5aa41e5c7a892",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G16-final-measured-report-fastpath",
    "benchmark/cost-comparison.json",
    "benchmark/repeated-analysis-final.json",
    "benchmark/report-phase-profile/results.json",
    "benchmark/prepared-report-only-delta.json"
  ],
  "findings": [
    "Same-host parent30/candidate flags and inputs; parent analysis67.2669/end85.1187 s/RSS459784192, accepted analysis65.6669/end89.3956 s/RSS557957120. Report serialization remains17.0455 s versus parent11.4885 s; no speedup trend claimed.",
    "Prepared analyses53.7874/52.3608 s preserve exact submission and typed witness fingerprints, initial DB/context unchanged; no report phase. Platform RSS raw units are explicit.",
    "Report-phase local pair4.2318→3.1017 s exact bytes; accepted fast path uses cycle-only fallback. G06 not integrated."
  ],
  "unresolved": [
    "One local paired environment and two prepared repetitions; background desktop/OS cache uncontrolled. Full diagnostic scope grew and memory/end-to-end remain higher."
  ],
  "next_goal": "G17"
}

2026-10-18T20:19:07.924819+00:00 G14 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G14/final-acceptance-v31"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "final-acceptance-v31",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:20:37.959946+00:00 G14 verified

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "a98d02eafdbd5e12feada731d138d6183626ca37bb3ea9074faae9f0a7501119",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "034d60f7655d5425b1e73879a8a7d6c5c16fe1661bcc232290a409c22e52ab85",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "1e8de7b81313666ec52ba56aec749c0382af271c3a2d153a54d343596934d318",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "c4552180dd0b2cef2c1a59271c8e1f323108b6cbea16360f2510613fe8d60f61",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/measurements.py": "c664b282ec668fc14c2f150a42521d54902592e51438566c55ec55c16c5e8ebe",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "f45bcb247222e87c2fe57a8754dbadd1e589c2ea6e0f86764ddc8efe1ce8c82b",
    "analyzer/portable.py": "4f535b1932568fee40dac328fd829c6452056362876a0920e50ad6d2f855feb7",
    "analyzer/project.py": "949cf6569bca9510b6afe6072b82264e266ee22b51b65faa40efb802d112a971",
    "analyzer/provenance.py": "ac977443481bc2f8c55ea1101fe02377fa9f0cf8a14532d1403a2e0ee2b5975b",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/reporting.py": "06a46d0d3c92f3bd957dae0ffb828e3d270ca6e3a488025ebf1af3e2426b88f6",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "ee4376750b982b3a97f5134101a9a6eb58e9d4870c2fde5b197d217e5ed9b783",
    "analyzer/source_conversions.py": "80b0967423c036ced1c8e2ac36c2c2d8a3c0ec8881e0bdf0f693120be45b38cc",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "d04804692e8693d9ced18717d8fa478d90f191786031a633f857da48c2d53864",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_aggregate_null_save.py": "12f8c9eecb6fe0cbe96455d507b643c0037e653c2d5e386b9a00c04e2f549793",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "41e03742b3b4196ebd32012fdd925eeef52119c3167127b6c0089ddbbdf3a98e",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "9f6c3d8b2e98f67ca010655c7fb2bcddff7d3394c428aa89de5536970714f2a0",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_ordered_association_columns.py": "57c44f693e26f2c47de150e6b7638902530ec584bab964562f6358417d517a8a",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_reporting_measurements.py": "9a19519a404776cdd340bc4abc139f18a15ddb62770a40a7caf392bdb5c3d0f0",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_state_reference_flow.py": "b0d731b15aec885fefae79640f7080beb2175490218b8ba45d607a3a5389686e",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "056d21470a9fdcb3caf0bcae2ad55b1b6dccdc1caffbe6557dc5aa41e5c7a892",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G14-exact-final-all-gates",
    "benchmark/final/witness-check.json",
    "benchmark/regressions-final",
    "benchmark/overnight/G14/exact-final-all-unit-checkers",
    "benchmark/legacy-graph-review.json",
    "benchmark/protected-integrity.json"
  ],
  "tests_run": [
    "1953 own Python unit/checker tests pass; duplicate-ZIP warning is an intentional negative fixture.",
    "PiggyMetrics main8/additional3, Petclinic legacy state, inventory/document, actor/frontend/formatter/absence/singleton/order controls; actual explicit+NL cart and47 mutations."
  ],
  "findings": [
    "Legacy graph extras versus the old oracle are unchanged from parent30: source formatter toString/getters in Petclinic and MVC validation handler in Piggy. Exact state profiles pass after fixing new hydration/aggregate regressions.",
    "Final local acceptance has all true checks, with nonempty remote/data real-source profiles and separately exact small-case oracles."
  ],
  "unresolved": [
    "No full precision/IoU for required-edge subset oracles. New holdout unavailable."
  ],
  "next_goal": "G17"
}

2026-10-18T20:20:37.964598+00:00 G17 in_progress

{
  "next_action": "Package code-gated exact ZIP, replay from clean extraction, submit once and restore unchanged best5 with receipts."
}

2026-10-18T20:23:47.746466+00:00 G18 in_progress

{
  "next_action": "Write factual pre-site documents, freeze judge ZIP, replay exact bytes; analytical package follows site/restore evidence."
}

2026-10-18T20:23:47.836246+00:00 G18 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/build_implementation_report.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G18/pre-site-factual-documents"
}

2026-10-18T20:23:47.959442+00:00 G18 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G18/pre-site-factual-documents"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "pre-site-factual-documents",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:23:48.011494+00:00 G17 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/package_final.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G17/immutable-judge-package"
}

2026-10-18T20:23:48.213256+00:00 G17 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G17/immutable-judge-package"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "immutable-judge-package",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:24:12.388135+00:00 G17 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/replay_archive.py",
      "--archive",
      "solution.zip",
      "--source",
      "../../tt-challenge/targets/trainticket",
      "--skeleton",
      "../../tt-challenge/skeleton/trainticket.json.gz",
      "--context",
      "../../tt-challenge/context",
      "--scenarios",
      "../../tt-challenge/scenarios",
      "--output",
      "benchmark/archive-replay"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G17/exact-judged-zip-replay"
}

2026-10-18T20:24:13.586490+00:00 G17 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_replay_failures.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G17/durable-replay-negative-fixtures"
}

2026-10-18T20:24:13.925685+00:00 G17 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G17/durable-replay-negative-fixtures"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "durable-replay-negative-fixtures",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:25:50.599568+00:00 G17 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G17/exact-judged-zip-replay"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "exact-judged-zip-replay",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:31:33.021877+00:00 G17 verified

{
  "evidence_paths": [
    "benchmark/archive-replay/replay.json",
    "benchmark/replay-negative/checks.json",
    "benchmark/site-score.json",
    "benchmark/server-verification.json",
    "benchmark/site-best-restored.json"
  ],
  "findings": [
    "Exact judged ZIP SHA90ff2b37... byte-identical to downloaded1665875, A0.39232. Overall +0.01963 vs30; S6 falls0.43871457→0.37967987 (−0.05903470), S5 unchanged. No hidden causal quality claim.",
    "Clean archive replay returns all eight exact answers,1894 code tests pass, no network/process/reference read. Wrapper negative failures/timeouts persisted and temp directories removed.",
    "Unchanged best5 restored as1665877, A0.90987; downloaded ZIP exactly matches original f574de..."
  ],
  "unresolved": [
    "S6 site quality remains below parent30; accepted source-generic fixes are not fitted to scenario IDs."
  ],
  "next_goal": "G18"
}

2026-10-18T20:32:50.266461+00:00 G18 in_progress

{
  "next_action": "Build compact analytical ZIP with current score/restore receipts; verify extraction, runnable profiles and full manifest."
}

2026-10-18T20:32:50.356888+00:00 G18 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/build_implementation_report.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G18/post-site-factual-documents"
}

2026-10-18T20:32:50.538695+00:00 G18 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G18/post-site-factual-documents"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "post-site-factual-documents",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:32:50.589236+00:00 G18 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/check_integrity.py",
      "--output",
      "benchmark/protected-integrity-final.json"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G18/protected-after-site-and-index"
}

2026-10-18T20:32:56.355508+00:00 G18 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G18/protected-after-site-and-index"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "protected-after-site-and-index",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:34:25.102816+00:00 G18 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "checks/package_analysis.py",
      "--output",
      "../../exports/solution_31_analysis_candidate.zip"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G18/analytical-package-candidate"
}

2026-10-18T20:34:43.164570+00:00 G18 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G18/analytical-package-candidate"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "analytical-package-candidate",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:35:50.544274+00:00 G18 verified

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "a98d02eafdbd5e12feada731d138d6183626ca37bb3ea9074faae9f0a7501119",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "034d60f7655d5425b1e73879a8a7d6c5c16fe1661bcc232290a409c22e52ab85",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "1e8de7b81313666ec52ba56aec749c0382af271c3a2d153a54d343596934d318",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "c4552180dd0b2cef2c1a59271c8e1f323108b6cbea16360f2510613fe8d60f61",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/measurements.py": "c664b282ec668fc14c2f150a42521d54902592e51438566c55ec55c16c5e8ebe",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "f45bcb247222e87c2fe57a8754dbadd1e589c2ea6e0f86764ddc8efe1ce8c82b",
    "analyzer/portable.py": "4f535b1932568fee40dac328fd829c6452056362876a0920e50ad6d2f855feb7",
    "analyzer/project.py": "949cf6569bca9510b6afe6072b82264e266ee22b51b65faa40efb802d112a971",
    "analyzer/provenance.py": "ac977443481bc2f8c55ea1101fe02377fa9f0cf8a14532d1403a2e0ee2b5975b",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/reporting.py": "06a46d0d3c92f3bd957dae0ffb828e3d270ca6e3a488025ebf1af3e2426b88f6",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "ee4376750b982b3a97f5134101a9a6eb58e9d4870c2fde5b197d217e5ed9b783",
    "analyzer/source_conversions.py": "80b0967423c036ced1c8e2ac36c2c2d8a3c0ec8881e0bdf0f693120be45b38cc",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "d04804692e8693d9ced18717d8fa478d90f191786031a633f857da48c2d53864",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_aggregate_null_save.py": "12f8c9eecb6fe0cbe96455d507b643c0037e653c2d5e386b9a00c04e2f549793",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "41e03742b3b4196ebd32012fdd925eeef52119c3167127b6c0089ddbbdf3a98e",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "9f6c3d8b2e98f67ca010655c7fb2bcddff7d3394c428aa89de5536970714f2a0",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_ordered_association_columns.py": "57c44f693e26f2c47de150e6b7638902530ec584bab964562f6358417d517a8a",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_reporting_measurements.py": "9a19519a404776cdd340bc4abc139f18a15ddb62770a40a7caf392bdb5c3d0f0",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_state_reference_flow.py": "b0d731b15aec885fefae79640f7080beb2175490218b8ba45d607a3a5389686e",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "056d21470a9fdcb3caf0bcae2ad55b1b6dccdc1caffbe6557dc5aa41e5c7a892",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G18-analytical-extracted-verified",
    "benchmark/analytical-first-verification.json",
    "benchmark/analytical-first-verification-logs",
    "PACKAGE_OMISSIONS.json",
    "benchmark/protected-integrity-final.json"
  ],
  "findings": [
    "Analytical ZIP extracted to a new temp tree; every member hash and embedded judged ZIP matched. All1953 tests/checkers and full independent profile gate passed from that extracted tree, outside repository layout.",
    "Complete new variant plus necessary source profiles/oracles/deltas/source snapshots/full baseline+final reports and complete historical S6 projections; redundant intermediate full reports explicitly listed by exact hash.",
    "Final publication archive will only update closure documentation/state; exact runnable-content hash reuses the already successful extracted checks."
  ],
  "unresolved": [
    "No complete TT NL chain/new holdout claim; G13 frontier and G15 not_run remain explicit."
  ],
  "next_action": "Publish final analytical archive with all18 factual statuses; verify its manifest and exact runnable hash, then complete native Goal."
}

2026-10-18T20:38:08.815838+00:00 G18 in_progress

{
  "findings": [
    "Final link audit caught an overly broad packaging omission rule: ordinary G02/G13 evidence directories without run.json were incorrectly treated as active controller output. Earlier ZIP manifest/runnable tests passed but evidence completeness failed.",
    "Native Goal was marked complete before checking the failed command result; no new Goal created. Work continues to correct the actual outstanding packaging requirement."
  ],
  "unresolved": [
    "Publish corrected archive after checking all relative document links and extracted profile/tests; supersede the earlier analytical ZIP explicitly."
  ],
  "next_action": "Remove erroneous directory omission; add the link audit to packaging gate and regression test; rebuild candidate then final v2."
}

2026-10-18T20:38:08.950460+00:00 G18 in_progress

{
  "commands": [
    [
      "/Users/elvsevolod/Desktop/учеба/Учёба 4 курс/хакатон нск октябрь/.venv/bin/python",
      "-B",
      "-m",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "checks/tests/test_analysis_links.py"
    ]
  ],
  "next_action": "Inspect command result in benchmark/overnight/G18/packaging-evidence-regression"
}

2026-10-18T20:38:09.228817+00:00 G18 in_progress

{
  "evidence_paths": [
    "benchmark/overnight/G18/packaging-evidence-regression"
  ],
  "actual_exit_status": 0,
  "tests_run": [
    {
      "label": "packaging-evidence-regression",
      "returncode": 0,
      "timed_out": false
    }
  ]
}

2026-10-18T20:41:19.001430+00:00 G18 verified

{
  "code_hashes": {
    "analyzer/__init__.py": "a9d2ae92b2216c555c07e7cc5d9b96b0b058b6318c745659a08713bffdc31235",
    "analyzer/__main__.py": "a98d02eafdbd5e12feada731d138d6183626ca37bb3ea9074faae9f0a7501119",
    "analyzer/absence_contracts.py": "c61f27c67aa01e2afd51ea63262114791dff70d74815afa4e31a966e1ad5b2ec",
    "analyzer/actors.py": "83f766a783e4ed3cef2d58842470e4e7bcdc0397b7af0c16da4343c86511a4ea",
    "analyzer/bean_initialization.py": "bb35e748a73a78da64a985704a4d671eee1d612953cb6fc6e8949706155d2b04",
    "analyzer/bean_lifecycle.py": "f058cd090e777bde73d6f884994ea40e905c72f8c7d45caefc390d4ed20040c2",
    "analyzer/bean_properties.py": "11e504245aa51b37e4aedd63f82c8c3157e85a5c39b77a1678b064258ec0be05",
    "analyzer/boxed_values.py": "491e4d8d6845409109561b4b71b5627c6b399762fe2959baec19dc9f73cdb468",
    "analyzer/call_effects.py": "004f8ded4f4bbd8b39631aa21d9504d9e11f56ac55b0960c68a5e968c3b87615",
    "analyzer/constraints.py": "65a8efc44dd649ddee975ccf2cc454313ef949f7447d28f1730b03f380d0f870",
    "analyzer/context.py": "e5625803a9b86a9f07ef4da594c1bf2af1ed83584f0fdbaa390047ccf9ce467a",
    "analyzer/context_choices.py": "5afc27b653c2b7f6f6804af26ee8f8b0839901c2a08c7c584ef706c2fbf59b0a",
    "analyzer/context_key.py": "3ecfcfd4e53a2799095f18515a2344e330ce9f1fe0e3d2a4a6de690a4b7d3e19",
    "analyzer/contracts.py": "034d60f7655d5425b1e73879a8a7d6c5c16fe1661bcc232290a409c22e52ab85",
    "analyzer/credential_scopes.py": "873ce6ad89a8d24374d01fb5100bcd7218072057fbb84c245cbd7415cabc6ae2",
    "analyzer/engine.py": "3e63c357596b084c4d4e8c6b64f7b52e9a121c8bfe3ce2e635efb15046ebda72",
    "analyzer/event_values.py": "1a75549330e9227949c2741c12a00573cb8feb860f7ae7c92a7386990280f540",
    "analyzer/feign_client.py": "700de2ad63db37a50d7b2c1e305e185f8e9352b4935cb99f576f52089f2080c1",
    "analyzer/form_flow.py": "4a4a3dfe68fd5bc1e8dfeeb3a115ac1c43554c17f92c4b83f629ccbbec13bc0f",
    "analyzer/frontend.py": "f1e7c0ae5ac95c23ca489eca3b0ad7a7794326f1201e7aba6a2f13bbcfe63033",
    "analyzer/frontend_angular.py": "40fc7108021a2e2e6da6824b67bd49159e02f364cb01d8c2dd90b9a83a26c82c",
    "analyzer/generic_types.py": "1a6cccf2a40786106ff70444f0c9f4025576348a13f18f9d0b5aa68a24065812",
    "analyzer/getter_effects.py": "dc32ebd00467e8a12881a99bd54ff002d91f391ca08db785238d510c23e849df",
    "analyzer/grounding.py": "043d4aba69245cce6e7ad85095377c068fa4b3f5dd3121dc2df44ac6e0fbbc1a",
    "analyzer/hashing.py": "5df57caf8ca696ac86deb35964047c5b76123cc433e8a3342adcdfa6e4f6458c",
    "analyzer/heap_join.py": "4a3fa0a1aaad771d6a327cec160557fe3400c261526a209ec18696f64c6105dc",
    "analyzer/history_refs.py": "1e8de7b81313666ec52ba56aec749c0382af271c3a2d153a54d343596934d318",
    "analyzer/html_options.py": "56c050d13c9bd0f6848d774fde62b5dc97f7eff2a2a0163247dd72f478826dfe",
    "analyzer/html_rows.py": "db35b7dfefd16e39f56fb96bafe8c64e655f7b5c721331a07eeb751b99667b53",
    "analyzer/http_binding.py": "6e7ceb27c04f15ca04ee46e6c7bfd72e1e5dc2173eaf61edf4fa0aeb52305b40",
    "analyzer/http_contracts.py": "4ac33592262e9c341aaba684afbde333adbf00d337ecaa017d9fdc5f7032a1b7",
    "analyzer/http_json.py": "17fe5b6f74ad996100a989d94ccc380fcd52914cdc3d59d95a500925cd27426a",
    "analyzer/http_validation.py": "c836c604e93e28c9367c3f6e1820bcc78118c6930ad1358bdbb8db8a9b66bbb9",
    "analyzer/java_collections.py": "524274647c6891aee0dfe05d4bd5cce1d843464fa88f09bf7bf0f97d1178ebde",
    "analyzer/java_exceptions.py": "ba790cb0a08c97e8c729b216483282981ad71bb9c7a4116688b3894e7ab42f90",
    "analyzer/java_lists.py": "b11cc0871ea721b3298f80175d7404e7e19b49b0016e84a751cc2828edacea58",
    "analyzer/java_numbers.py": "e914dfa759258249a9a337749adcb169b697193f3153402ab23c94459f45a5fd",
    "analyzer/java_sets.py": "ac216fe50434b0e99e81d5a6f2a070fb3b4fcbde2c84ff67735c86cf2e6e0bda",
    "analyzer/java_strings.py": "3c22c2ec7b1e9634cfcc8d5945aab558b101d9d24be6784d00ede4877b8c1344",
    "analyzer/jjwt.py": "b34b9eecbce5c2d35abb7ecfe214ca078e6f47957711b3c39a76c68def0bf7e6",
    "analyzer/jsflow.py": "3faaee76b587b728e4fbb8e42a600df2b7ec13aa07e6c8b799045b77e07f091a",
    "analyzer/json_codec.py": "0b0814517798250eaa079fe11f1e5e72f7a455df63e94e2ae8e956fdb575c117",
    "analyzer/library_versions.py": "6789333b311d34525bc77db599c95c014a70f0adc87e35681b611e5c4015b36d",
    "analyzer/map_filter_proof.py": "c4552180dd0b2cef2c1a59271c8e1f323108b6cbea16360f2510613fe8d60f61",
    "analyzer/map_keys.py": "567f11809ed953ee5aa271ac6b51b8d6f325aa933ea4570db2ddd5814a250d58",
    "analyzer/map_loop_proof.py": "b5380702b2ba4a3cb1d6e777894b7d28bf9c02966948b5358bfc929793b6ace9",
    "analyzer/map_views.py": "a4b77324e16e12a5ab4aa43aa7231f797af52fe8bf6ba0dda3d459e4cac168fb",
    "analyzer/measurements.py": "c664b282ec668fc14c2f150a42521d54902592e51438566c55ec55c16c5e8ebe",
    "analyzer/models.py": "177b948d889acb284c00d97a702e6801fa60f17816e41730956c31a3fbcc14d3",
    "analyzer/native_arrays.py": "5c24e53aa25107b96b3122c6c342b77e7721c55d9d8bbad405343b6389a45e9f",
    "analyzer/native_contracts.py": "0773bcffecb4a0bb7ce5f5dbdc07f54c1e4381351beb45ada1f5abb8dbf64efd",
    "analyzer/native_storage.py": "fffd10b3a7ff8af35792c11d808db1fc649b89d681b9056283a2b7eb8483a9c3",
    "analyzer/nl_inputs.py": "a065fb040d6387923680a6d7471ceb6a7335da131f6d1de15448542442496020",
    "analyzer/option_sources.py": "be5e2a99636abc1e092750a837a7ac0dac2b849068ef1f52d39ff3f31afa2cc1",
    "analyzer/paths.py": "39a76dc2dca8259df4d415c764c284205080d991b700d6fa18ed5b970f333bca",
    "analyzer/persistence.py": "f45bcb247222e87c2fe57a8754dbadd1e589c2ea6e0f86764ddc8efe1ce8c82b",
    "analyzer/portable.py": "4f535b1932568fee40dac328fd829c6452056362876a0920e50ad6d2f855feb7",
    "analyzer/project.py": "949cf6569bca9510b6afe6072b82264e266ee22b51b65faa40efb802d112a971",
    "analyzer/provenance.py": "ac977443481bc2f8c55ea1101fe02377fa9f0cf8a14532d1403a2e0ee2b5975b",
    "analyzer/record_guards.py": "03c1f7ff742838bdc2edb879d5bbb3765f3ec13c4af905535c100425e0cc868d",
    "analyzer/records.py": "a73f35e2098a776b97cef1a7e4ff702a985a7a29e6daae63f5f79cc0768bc842",
    "analyzer/reference_scalars.py": "dce821d680e54a7407ad6e6eaadb25132bc379057b609effd568770d1ec8dddc",
    "analyzer/reference_types.py": "d0132fd8d338e147839b5d9b38ab3615080a79bf1756186ec6d564781219f97b",
    "analyzer/reporting.py": "06a46d0d3c92f3bd957dae0ffb828e3d270ca6e3a488025ebf1af3e2426b88f6",
    "analyzer/repository_values.py": "02a5ef6b456a095fe10ea93c167fd16278218544462343d1cfff3396807f6351",
    "analyzer/request.py": "b881b3d2438b47d4f63ea246290803d49147bc438cf963b57e648202ab5a3f8b",
    "analyzer/request_inputs.py": "2f0847dc393b05b3094a5495379ec5731f8d350cff5599cfa080c4841db6cebe",
    "analyzer/request_semantics.py": "220a58a368997662675c3b29ecaa6542d30f9b20ee6c7d5f5f0c60c60ae881eb",
    "analyzer/request_url.py": "4d1f75714e852b6d2417e47d49d5a3319fa53a4c2537611d3abd6045a0f34996",
    "analyzer/resource_effects.py": "b4e942b7860d5e9eb5655f2ada3f3627213de54b22b061ec001b8f898c0bff67",
    "analyzer/response_arrays.py": "eab7dc8d973b70e997aa2cde6510dda18c410da8de9c59a6b6abb152725763a4",
    "analyzer/result_contracts.py": "5349ee445f37d1fa0d02c41db50e0812bbd831aab5545386c40b742b8a87ebfc",
    "analyzer/row_arguments.py": "4e9b50f8014f46582603d614bcdd97eda72d28c4cc273cb9563db4a6a3b2aee8",
    "analyzer/row_events.py": "600e7b2b40c54c8620f014fe0be5c9b6a0e035ac66ec22554c909a467bd15701",
    "analyzer/scenario_literals.py": "97167c515c32ef25301795480523ec2294903cfce06cd9dce06ce3059efc2589",
    "analyzer/script_flow.py": "5edfecfa52fc3f65d53f6269a7928b7e981f725d1f93e623b98c183ef835da2f",
    "analyzer/script_vars.py": "7def38314930e1173e8ec6b31a08d0c2e2ccf2a0c718b5a2ba0b2af2853bfa21",
    "analyzer/security.py": "947410cec4cc2ecd0e0a5a0345aef6476c7fb27c8d65ac6123581e59d75e93ba",
    "analyzer/selection.py": "ee4376750b982b3a97f5134101a9a6eb58e9d4870c2fde5b197d217e5ed9b783",
    "analyzer/source_conversions.py": "80b0967423c036ced1c8e2ac36c2c2d8a3c0ec8881e0bdf0f693120be45b38cc",
    "analyzer/source_generics.py": "644b2c2905b4064cb072ae8028272c5bcdffd86e26b369691f55a0ec1a208013",
    "analyzer/source_labels.py": "50722f1565c35ec03aa78954c11b5e4ea3ecd21f196bb15f94f2d85d5076ea19",
    "analyzer/source_literals.py": "4fd9036966a36d66e21020f7b5d8ab00e6c7e5bfa1bc71cc7753e02cda20b7e1",
    "analyzer/spring_client_config.py": "52c48a656a341b7a0b963e526956c7a3064b3942b093ab10c1ceefdfb09c6378",
    "analyzer/spring_formatter.py": "4010232a50cfe031abda87ad52acba15b78fcf23b44bfcec139133e519efe450",
    "analyzer/state.py": "d04804692e8693d9ced18717d8fa478d90f191786031a633f857da48c2d53864",
    "analyzer/structured_literals.py": "f4f6af760b1d9e13495fc92a70fa7632bb4614c25e6a8a5e9bb8408325443e2b",
    "analyzer/symbolic_text.py": "cdf09cc414e7cdb5cb15ac1c798d42c7a042a6940728c92349de552317374bcb",
    "analyzer/table_store.py": "ef32e3aa31e605599e65fd34ff7b7bb8ac4289fa6632bed3077a63863d21af07",
    "analyzer/units.py": "43ef7a6e7979350fa74bd4b60aa6779fc5334d08c07447dbdc69fcd1bbb3694b",
    "baseline_closure.py": "51d4a54aacc57e42b6c77e92c7ec8bc34fefb08f3bddb4005b1fff5f467805ce",
    "baseline_nlp.py": "57421a72d098ce80eaa837d652dde49640c7cb7e533d1c010c2b12d4983eeae8",
    "check_generalization.py": "8d4699f1a1fb5ad9d8bb38eadc3382ec2bc4edda28a8cf08089507e9b7259745",
    "offline_run.py": "ae73e5f8e1579499ef52c7cd49706e4bc614a71a5a1e6581b0c15f76181a9e69",
    "package_solution.py": "254c4198982d00ea12277c044948846e95e91f7613f7c0a9d9b3da26932732a0",
    "run.py": "271ffde3e848e5a5dfda387cd0129850b036114e5d6b549d1a5069c75471402c",
    "tests/builders.py": "0ecae2d37a6cfb37489b3a4e69d1c51968ff7c7cbf16d258666b4d507f2f9ce8",
    "tests/test_absence_consumer_equivalence.py": "366c299d1be432b41ae57a2be1dbaf3d1c8f01fe94a0cd45f6bf1c8ec912b499",
    "tests/test_absence_escape.py": "b581412a26b61661ab86463c6b95a4043f538056321a2d12d1a68363b22db034",
    "tests/test_actor_credentials_flow.py": "091b42133d116cbba12493d4026e46390bc2332fd6f3b5cd03dfd0995c0cea92",
    "tests/test_aggregate_null_save.py": "12f8c9eecb6fe0cbe96455d507b643c0037e653c2d5e386b9a00c04e2f549793",
    "tests/test_angular_legacy_session.py": "54cf630316170146b97245def7bf181b0674ae46cb544f31764349c22fb76dd1",
    "tests/test_application_entry_boundary.py": "0262f7bb3bd26f178bf042bc5b6280e30839977ca1ada02e4b25d50daa152f6e",
    "tests/test_backed_map_views.py": "0cff60d2f366b5687b1417a6fdfd73d4569d4412b9c548b8857c9ac8c65693de",
    "tests/test_bean_properties.py": "c118045fab4c8bdff8a66f71434050c214fd33c178c71754bd65eb89ecec1983",
    "tests/test_boxed_heap_flow.py": "5871ccea9a4730826705a97741c91721c812d30e601c0b71edbceae231e4540a",
    "tests/test_browser_soundness.py": "4d8009813adc93fd36de0206543c11b7e8f839b8d827220f8a4d3a37c255e200",
    "tests/test_bulk_consumer_types.py": "41e03742b3b4196ebd32012fdd925eeef52119c3167127b6c0089ddbbdf3a98e",
    "tests/test_collection_equality.py": "1b9dc6786a8bd53338bc7649751613970751dc33e18155c79adc274ac92a91f3",
    "tests/test_collection_request_scope.py": "98f07a41a869ba527d11dd70e089778588f6d0ac2c77138ae1b401640dc16e30",
    "tests/test_collection_state_boundaries.py": "4eba7eff96c8c280a31f06a1587a502e717f7fea2d5da2ea4b3d6f2ad1f06751",
    "tests/test_commuting_map_copy.py": "6bda1d12e437d6048a4baba840d84ff9f0ad712d369d640ca59e2997bdc99360",
    "tests/test_commuting_map_filter.py": "9f6c3d8b2e98f67ca010655c7fb2bcddff7d3394c428aa89de5536970714f2a0",
    "tests/test_concrete_dispatch.py": "1d203a565b21bdee0c8c5ae5bd66941b129a214a4bd764b918df671afed2fc02",
    "tests/test_constraints.py": "7698ce6056fa6bd887eb6f289ac50f7010a89278eaa05ba0f9439efb6091724f",
    "tests/test_context_choices.py": "22b63047c62b827a3e3c660c3f4d63703c47a2d98d737a885c9e996faef4919d",
    "tests/test_contracts.py": "a86708dee10a2fe23ed63931df3ae0e1b2f3a34a9d0ed436ec1290ac7cc97ea4",
    "tests/test_core.py": "766fdb5c7a85d0a0f76ebb425b54c74ba941e52936a0dad3b8eb84a8e9255346",
    "tests/test_deepseek_dom_adversarial.py": "94eb962b0131cf8bd85687d41c32940013b48cf7d19b9dad7362573e0a4e98d6",
    "tests/test_deepseek_option_sources.py": "a36dce7d266bbcb17c198325446283342ff8b49b2645708687ed04b4bfb22678",
    "tests/test_deepseek_response_arrays.py": "4272970d6be6a6625e960e5755a8a602675fc8149da9e93678d1a1c1b90cd8d1",
    "tests/test_deepseek_routes.py": "a809e9ec59002bfadc94060f2a4617c7939fe5a118ae24e77c460b60f14a771a",
    "tests/test_deepseek_row_arguments.py": "e9e4e01bd767c81ce8d00128e80abd7d91b8748ba4c03ec52c21c3e5d90bdba6",
    "tests/test_deepseek_row_events.py": "316d7e1f9da4f5f10164842f274b4e278846910b93c4e9de41565252eb893527",
    "tests/test_deepseek_source_labels.py": "a48a3fe075eeb026154bc7f151e4a30a4414210de1994f75347d5971a0c56f60",
    "tests/test_deepseek_structured_literals.py": "f75abbc53e2dc0c4a20071297df5f4553a759cf0e9c298ba8b1fccaf24c03a8f",
    "tests/test_deepseek_symbolic_text.py": "757270d519b9505dc52e5883782f13bbd3ed859318cc6d5d4b4325d1ffc10891",
    "tests/test_document_array_journey.py": "8ec0eb5a042818521dac7eb117144dda6d90e5d2a1160c885ae78e397a191403",
    "tests/test_dom_choices.py": "4b28728f5e438663e747a1812abe8dd925f94aaf59375cca5504b502bda5408f",
    "tests/test_dom_preparation.py": "5f86c04fc4a3249d4629cb157a6abd0351f81d540d9c1d216142d1b47ca723c8",
    "tests/test_enum_field_runtime_kind.py": "0bdf90e40ed643b11c0948b6b13ad91ee41a6e3475de1743629f1a0adac0c6be",
    "tests/test_enum_namespaces.py": "fe153423b1e6873955ef2cbcf27d1f847307f32224de0976cfb3c7502219faf7",
    "tests/test_expression_key_types.py": "059db28e5154e953cd94e465f038ea1678e2505bf0836eef0c6e99e801d64947",
    "tests/test_fallback_read_effects.py": "cf78ce72c18b35057501ae46e2672e78a0c403fb1e0d583b33a27fa795552909",
    "tests/test_form_flow.py": "8808fb9caa13fb0505f5d6123906cde2e5ffd56565c5b8a59fc4f80ae07e1a9a",
    "tests/test_framework.py": "1cd50759bb77ff4b63ec9c0bacd74b8e2fc78efa9c36d80f80bcf88597a7bfa0",
    "tests/test_framework_boundaries.py": "7af53e9308d00af6f535875c5805982e59109abaa294025b1c32b9f4fe0ae84f",
    "tests/test_frontend_contracts.py": "9ad2e260bcca35d08c21c85790fad5ea8bb1e4600f9745a64bc0cd09ea6662a7",
    "tests/test_full_state_evidence.py": "6401e6b58a471e99bbd3e09d34e01e7332da3fc02070ab542e273ac3eb84d6b8",
    "tests/test_generic_json_types.py": "48280ef49260ca11eb2fcc09f43ce642c71a0b4bf1c76e06ec3b952d2a13eb2c",
    "tests/test_generic_member_flow.py": "b3802f523842107db2dcdc8f31d4a708050932e2cab4458ec4d60976088dddfd",
    "tests/test_grounding.py": "3f550239e454dcd11a954fb3b8bdead9d618ea3820d1774443695ca63957fe6d",
    "tests/test_guaranteed_access_failures.py": "d80f20f320ce0bbe337039f2b744bb01b5997c9bb2107a9329aea0a0bba6ab81",
    "tests/test_hashset_membership.py": "289206aa68eeb7f5cce229baf236dad5a9323990688231cade1a514f68216f57",
    "tests/test_heap_alias_join.py": "148659997576d56be7aa7a3e7573065ec4c15ed94c6151ca0c62b3092ee9a1d6",
    "tests/test_historical_creation.py": "8eabd359469047492aa1bf52c818e8e4424828f2bbefb6a45a04d32e63183104",
    "tests/test_html_rows.py": "2ca05fe572143b7ab5006cfb6d70da3d30c14d369481f617fdb5dae12d6fce44",
    "tests/test_http_map_values.py": "323630ece65ca8783b8357be971e80a6689e00a1e87183d662ee78491e813a6d",
    "tests/test_http_nested_collections.py": "fa00831147b0c593ae174638b53559e915c55fde0aba41e372b23dd0f86d3337",
    "tests/test_http_request_boundary.py": "954e0604c0f9f3c6d3bdac6bad8be4973824d2de883d98133c80ac01c7c29e19",
    "tests/test_http_server_failures.py": "cfd9d5c4be08037db87453de5b512c62173df80183a5c9bfc34f93559aa134b3",
    "tests/test_http_type_boundaries.py": "8483fd6445b39d674db3030dd6d88837dccb5f4b06157f49916d4b33e0c593e4",
    "tests/test_http_uri_templates.py": "c9eea23a6ea51b9e115a2aca8802c275248047e7e4fbcdb0436dc6da036be470",
    "tests/test_inherited_entity_state.py": "9a9b845bc35722b7827d59e3df9f7af219c765317b148d2ac00bd2a4db36c28e",
    "tests/test_inherited_json_generics.py": "20b2e453a751ae4bb2e3d223793980fa560cf249ccf24705ba3be334f78cecca",
    "tests/test_input_replay_isolation.py": "74c574bfd91d6c1ab00d2cc9e55ad5203e1f3993d4292fa8750fe488a11b076c",
    "tests/test_inventory_collection_journey.py": "e495762a73a2be17f12c2837befcaf99804d5a44a486a5dea5e2fbcdb2be3d19",
    "tests/test_java_date_text.py": "76574983bba10c03fdf90499afff3a8404ddb7c9a3de26f9e9f60278bd28b0ef",
    "tests/test_java_parse_integer.py": "0e77afba1d5c8afa13295f9c6d9b253a0522c6a3a937669ad2db64676ed3c929",
    "tests/test_java_streams.py": "beb4d30ae4a7b84abcd2e29e6fca02b823fad785c8625c0d74bca0b2c150501e",
    "tests/test_jjwt_authenticated_requests.py": "a04a49db8222f18213919f373694f4f4d5c4416c4a7e2aa9e11cff5cf06767ef",
    "tests/test_jsflow_soundness.py": "4a204b2d86d5b8c295861e7a9c19eaf68784d68357cfc4a6762a4acc059f40f1",
    "tests/test_json_bean_lifecycle.py": "b93199aa21c50108383f786f681df4c01d578faa369f4db53b0882bf17014a0e",
    "tests/test_json_business_metadata.py": "a4528ec595e515b0ed425fddf2ecf04b24ea2e0cc88509c35a3f30d47a8c41ff",
    "tests/test_json_codec_boundaries.py": "791cb39143d6cc9a4e4c893e942b80a139aca7e80b2fd608828de36be9592449",
    "tests/test_json_enum_boundary.py": "a65f878cda5e42af93394427919be0dddd5fb73e21711a63530fdafaf59650c5",
    "tests/test_json_java_arrays.py": "94615767ec15375e7783a1938f2351e4dd0cdce0f84ac4debc6612bc86fcb525",
    "tests/test_json_model_boundaries.py": "f6dbcd29a4bc722915bbfff57c04a2658e9808101ae9c39923f85652a34d555e",
    "tests/test_json_record_provenance.py": "72fb94cd816b5e95f3f890f2e1163da0dfd3bb23e8281ba7d4f28323d4cc2e96",
    "tests/test_json_uuid_values.py": "a61dd18d12e0b18666db2d398540be8d4fa01fdea383b9efdefd094c5750ad5a",
    "tests/test_lexical_bindings.py": "17835e87e8342fb92ac05e197aa0b7bd1f9ae41e5b021e620b7f2fec4f3434cd",
    "tests/test_loop_variable_types.py": "40a32c7d71d4152ca027d337f546cad5a69775e64d9cf0b9f1423ab8ad87937c",
    "tests/test_lvalue_evaluation.py": "0cd19e234f07c1f0284524628603c5c005337c2859de916f09cabb38e093adff",
    "tests/test_map_initializers.py": "ba39412fff67b71b55380406f7554ef73e0424929402733c04ea9c7e39260853",
    "tests/test_map_noop_filter.py": "ddb299d64002cbed97e094953803b5680de11a585d94e553522274059c28df46",
    "tests/test_map_proof_casts.py": "98b130ea222a08830802375d4f2887d42760c8d72458b60fd71b72de30d010c9",
    "tests/test_map_value_classes.py": "bc7d2d98b39b6986b41e05b198f039fa17702b180888d37626ea962462cc3193",
    "tests/test_map_view_boundaries.py": "6b5e79505a0181aa94c989c997deca7b4ab8140376a5a8c84e9452cd31e15a91",
    "tests/test_map_view_iteration.py": "3351743632bc9b9d8ab6e12ff4361a03e791f4ce11150127e5b7422370485f5e",
    "tests/test_map_view_json.py": "8ac166bb7e517e3045a8046986c211d18a99cf10ade470b49bae092ab4f8760a",
    "tests/test_mvc_specific_handlers.py": "2a07b0c90eabc06f744fd7c80358c7b4755ef45a62da72e71b8d33d2bf61c61a",
    "tests/test_native_number_boundaries.py": "cc0968a4716361fed51f27f7a878bd2bffb1165bc9141cb3263977adcac405de",
    "tests/test_native_observer_continuation.py": "3d3bfca0fdc5cb3e20b57e5de701993bfb3155a9307359a11aa905353a3a0b38",
    "tests/test_native_option_text.py": "2fee9caffeac9d25879e16e288c553fae36f063b9acfcb42421e56ba000b5187",
    "tests/test_native_storage.py": "439e8848e7a7d8e671a4b57bd905b9370b96e94473473b0476f12840f28aab12",
    "tests/test_nested_required_checked_exit.py": "c6a77a114e864e4bfb39bef1f47aa31093444649ac51d0d20132ca7e6325bb96",
    "tests/test_null_unboxing_flow.py": "efc888d0eee879bb8d64e7d8963ee8279e2bd183d6a95a10ce968e17150315af",
    "tests/test_numeric_promotion.py": "e933a07b7310346ff02912387745e30be7e7e9f479f9a607b2a87d6c186d26e7",
    "tests/test_operation_diagnostics.py": "c5d3ff867a0cca1f0025d91ef064c5bbbc47c355defdd7444bdaec2e25d1faa7",
    "tests/test_option_source_soundness.py": "7d4ae5900895248bedb5d823b0621dd2d8482be06492c03890151b683c82a0f7",
    "tests/test_optional_mapping.py": "53417250c710e651fbca6176fb6f4918d08a4343e199f832c7dba99fa13b5627",
    "tests/test_ordered_association_columns.py": "57c44f693e26f2c47de150e6b7638902530ec584bab964562f6358417d517a8a",
    "tests/test_owned_json_codec.py": "51f45eac747af5089d15b7ddfa494dd48edf93bf0867749ea356d30dd2397fba",
    "tests/test_partial_dto_footprint.py": "ac9aa2603448b3579510b2be178946b38f0078157e91d143791d9cd165b9f984",
    "tests/test_patch_source_deployment.py": "d28bd85026fa117b57d0206ec42cd9328db9444b9690b7090a39c8331b1c7f28",
    "tests/test_provenance_binding.py": "326fb37d745527978d3143dc0ee09e86b8da3e8714447ed48c21491658c94e28",
    "tests/test_query_numeric_predicates.py": "6ee8942425ddbdb6946e74e1263e727a347c1f2a6aaeb40cc6d2a9d0306ba1c7",
    "tests/test_query_parentheses.py": "14da4150c798ea2e1e1dc4994c7df44f224502805c10fb5be5ee4890a72de609",
    "tests/test_regression_additional_risks.py": "0bc0f7361c558ba6b842d24404b46c876e2aa075886ec6a837d79e33dce6c260",
    "tests/test_regression_adopt.py": "6a886f9d10f7f22d1183008d23939a4266c33cdc138eeea541d27dcf24ed6299",
    "tests/test_regression_authentication.py": "c0663ed2f8a98f3c1f34c75a42c010d09724acf984ebf8d78f444dae2cf5455f",
    "tests/test_regression_history_positions.py": "013fb0e97911411d2bea14e64b21022095906b3dc287fa871da69b3f997dd528",
    "tests/test_regression_inputs_and_guards.py": "a30efd1d68593f33cbfa050f633c1ade6069921dc32d02d5db687ecc751d48fe",
    "tests/test_regression_logger.py": "6ddea4f76b24cfd9986258c7c7a3d7f2afe6c38e0b0b82f26588af955c2fbb1b",
    "tests/test_regression_remote_prefix.py": "7b2e1f311b2da0b3efa21877a0e0bcc5fec0cb25587fcb3e4aecb344416daf3f",
    "tests/test_regression_result_semantics.py": "4dfdf3851d7920cf11ab340469284256690211dbdcf13d456a82866f2c9c40ed",
    "tests/test_regression_strings.py": "a51240a9a94797b7a7293ca65160aa60c2d29fd460e0d218172e8b2f3b9253d8",
    "tests/test_regression_token_headers.py": "f322b651ac886a77fdeb14111a16d09067d48defe50b3071d07b3ee942bc16c9",
    "tests/test_regression_unknown_enum.py": "7270140a30794d96e630fb50be9ab5999ae3cbf63461faf58cf379d4aecf67fb",
    "tests/test_regression_wire_fields.py": "26013dcfdb59f447e2b23f92a91af511e7d1695b9d7f96ee9cc194ecfc070462",
    "tests/test_related_reference_scope.py": "99bfe595f35e2d1d00878fdb44a2f902923554a8b8b827bebed154616e4f18f7",
    "tests/test_rendered_options.py": "8b5d67e256b5593501db194b00aff91eb0a9bf4e51b97365126463ae33c39c95",
    "tests/test_reported_regressions.py": "11f11256bcd4165a3defbf73d4775db2218e5de4447b974b1e3273cce9c374dc",
    "tests/test_reporting_measurements.py": "9a19519a404776cdd340bc4abc139f18a15ddb62770a40a7caf392bdb5c3d0f0",
    "tests/test_repository_unknown_wrappers.py": "720b1016b6fd6990c891228a2afa206178d86d0943d5b9b08bf384c6532ab5bb",
    "tests/test_request_components.py": "49e5ebc2804bcde08c6cc11396ca61a1657ccd7c96eb965e79ebe9f50357a36b",
    "tests/test_request_isolation.py": "2dbf8d484cf5fc2d7e9ca5c3166c1a9745a5508c5b9d9188bfd104d30493622f",
    "tests/test_response_array_state.py": "8db2e81312bbd00fa9a428bd4a2eaa1ac5341e00d7b3995e68b9022b407f1c94",
    "tests/test_review10_execution.py": "bf720a2719e4abbf0e7b28788e59a5060c01f6eb54ca5e517622194a0797b3e2",
    "tests/test_review10_inputs.py": "0753f5c6e9b8f90f1856057c5b350bd9943726c1e3459e566decb8abc6f34125",
    "tests/test_review_alternatives.py": "38a3121e1c8a986a0d62c753b54453ec8d739da4cc5da6f02d385b952b4291a7",
    "tests/test_review_effects.py": "58eec6e1b5735331087b348009db62f38dc9285a8edc0ced7ca9a03843ff4f5f",
    "tests/test_review_events.py": "8297545beefaf8f574f3f28e578994af0f93fa4e9a4ebf387bbdee63d294ecb8",
    "tests/test_review_history.py": "33face50cb9f944d35051f8bc0235b4c41a44088e58b19c106c8479fc40b9ca8",
    "tests/test_review_java_control.py": "a30b371ace8c8994a187f0d56d32e95b7d199e21027ef466518e1ec7e447e345",
    "tests/test_review_persistence.py": "5e643b0a03ac889463538bcc148ef10e60b21a27f2bd9392a4b335b7711efa41",
    "tests/test_review_projection.py": "1d0395bfc2889c35e2f3959fc296b4908175c90448284662b0156cdbbaf48d49",
    "tests/test_review_public_mechanisms.py": "487710c41131bd96c0598f39134225504a3b0fc18a80cfd0faa8f12d13eb84ce",
    "tests/test_review_records.py": "74496fdad77fe5df0364d94a1e1c043b7fa21573e64bed842c76c17f21cf3879",
    "tests/test_review_request.py": "e152344da032d8527455f452f2458447fc136616161137a92ea0e1ed4bce8666",
    "tests/test_review_snapshot.py": "3edbe03c55481cae8a0fd275dfe5372db2b344b649383b4991f416aba6b77c4f",
    "tests/test_review_summaries.py": "e1037f0560cab8def7b873c775a5bf479524776ca1e2af1446e54a2300fb153f",
    "tests/test_review_table_store.py": "f42ccf044b99a91417806845ed594c19f03b069de952505aeb4bda8d7a605040",
    "tests/test_route_specificity.py": "a55d209853324fb87c21bb56d500c1f4408484e586c50ee1022f3d8ced99e0b8",
    "tests/test_row_event_soundness.py": "4ec1b6051f9a90a7017bb61d2bf2e77708d9b238243098b7446d48fd3f6e5612",
    "tests/test_row_request_binding.py": "7dcfdd6777cb319276a5c84aca1c4a0b95d9dd4431b67a1b545b611059626d9b",
    "tests/test_scalar_record_boundaries.py": "1885f3c6c270f6a01c7782ab0ae4f25b972c7e680ea9c21bed8417cccc56020e",
    "tests/test_script_flow_boundaries.py": "c15300a03196732cd8cd34db715a7c263dc6b3df09c2802fa44f586dd20abdad",
    "tests/test_script_graph_journey.py": "bb8fab3bb779724f5c64d6be2ceabfbfde149f76e2d132bbd3ae005318734b20",
    "tests/test_script_ownership.py": "f9c7ab6d08e69cf90fdf7e18107fe9de6b3cc5acd36951a733607aed83623ea4",
    "tests/test_script_state.py": "643a7e466f458d49cb91b1a2b5d11340aba21caf3949656449479675f02639ec",
    "tests/test_script_vars_independent.py": "8ef9f3fbfbdf5bb2684f40b014573ce89b5e07fd439a2adaee2fcaacc373d6c8",
    "tests/test_selection_state.py": "4e7c9aeaea3ee5283e5ff45f822597acd13068fe1cab20947ff2a81f9040fcce",
    "tests/test_singleton_join_identity.py": "d86532cc19092f2c3f9f738acec8c8f1f212e82541c577261a97761f11d9fa07",
    "tests/test_source_bean_startup.py": "04754d950e60711900b9450138196b4a2c7b2df5e8f490bffec93b6654d3fcaf",
    "tests/test_source_inputs.py": "33dd30c686ff0e5e2a875d0dd959891cf3ea6b5d855e6f1028b7e9a5f9e0a469",
    "tests/test_source_label_soundness.py": "090bbe57dd62d992203bbd6928126f45469bf60f6a72d0268c85e3517a7de7d3",
    "tests/test_source_object_identity.py": "1d3fe73459d18af42bd734da2b7226599f4ec8dd4a3de0de4d639099bff62d5f",
    "tests/test_source_select_guards.py": "2f0b9de97aff7407a4a581135f80cea50e170c8e7da018bf5037ed156607e69d",
    "tests/test_source_state_reference_flow.py": "b0d731b15aec885fefae79640f7080beb2175490218b8ba45d607a3a5389686e",
    "tests/test_source_uuid_generators.py": "0542d07c77cc68b85aa0e60aa65ab763aedc9b14a46cfe31466d4123fa46190f",
    "tests/test_speculative_state.py": "8ce3ff9f0068a5284481abb5703703dc188bd020f7da4e8be98194cd6585a953",
    "tests/test_spring_formatter_effects.py": "7c7234b6b6e576417d0c7b977f99a6c959e21795d7745bfd4b49612a3359635b",
    "tests/test_state_certainty.py": "ba18eb409efc47a97cc910b0ded1a61468389e78facd34c5f721683e1d9b1b3d",
    "tests/test_storage_consumer_diagnostic.py": "9a1fef79ce15175000917c2f5848536eed4a2b5ea74480fe5c0127ed49a51cfc",
    "tests/test_stream_materialization.py": "bfebf95653c3694bd95fccead753278a3b9635da496e15f682989bf46090e8ba",
    "tests/test_stream_parameter_types.py": "e0f498e6556d78714c4c9b02fcf8ebd69eaf9c04a71f9644c206771794a1a1e3",
    "tests/test_structured_inputs.py": "7007b12da9e5b443ef6c276d67314b83af16318cc12b416631ae4a857a03b811",
    "tests/test_symbolic_primary_keys.py": "ec4a325c7b93de4f5215f1b765567372203dde496dbda13564b5d0dfeefbf0f7",
    "tests/test_symbolic_request_state.py": "ffcf1f4198a685c4c753ff1290a08a05fa76bfa1502fbc6a9e1bc6a51823ad1a",
    "tests/test_type_parameter_shadowing.py": "db8c5cfade9ee97e9a62f01e14c82e19eb0c1291ac6090000ff40e22ab6c7622",
    "tests/test_type_visibility.py": "894895b5dd679d622f3350763fb156c7fc613f4d2fe28e229fc7227424c33685",
    "tests/test_typed_map_keys.py": "be9f5c8b6dc14ef4c994f9426ca88385e0098d08362a22c2c58346906a3a0d0e",
    "tests/test_typed_reduce_records.py": "056d21470a9fdcb3caf0bcae2ad55b1b6dccdc1caffbe6557dc5aa41e5c7a892",
    "tests/test_unknown_collection_iteration.py": "e87b3bcb2c476aae2e46d27c9a286c003b16baba4b7d6f50d3779079f5933aca",
    "tests/test_uuid_conversions.py": "778a97fd76c50fad7b8a0d5c4bd1d42f9ccb27790516c565a471aaac783053ae",
    "tests/test_vue_requests.py": "7229436e36d18d673ce62bc4cd3d514f3670b4766678714f7544ac3d866b55db",
    "tests/test_written_composites.py": "830fb7af6fc496b49dfcc02652d380ce67c9f9db02c7f9a8de95dc96d5ab9165",
    "verify_run.py": "9d982b66946d2071f4064d3465851d1524166b200e725cdbde44edbd8959e5a6"
  },
  "evidence_paths": [
    "development/checkpoints/G18-corrected-link-gated-archive",
    "benchmark/analytical-corrected-verification.json",
    "benchmark/analytical-corrected-verification-logs",
    "benchmark/analytical-package-defect.json"
  ],
  "tests_run": [
    "Corrected ZIP extracted and all1955 tests plus full regression profiles passed. Every relative delivery-document link resolves, and complete G02/S6 evidence is included."
  ],
  "findings": [
    "Erroneous active-controller exclusion removed; new regression controls reject missing document evidence and preserve ordinary artifact directories lacking run.json. Earlier incomplete analytical ZIP explicitly superseded.",
    "Assessed analyzer/code/submission/judge ZIP and verified site/restore results unchanged."
  ],
  "unresolved": [
    "TT full NL chain remains partial, G06 experiment rejected, G15 missing-input not_run; no false completion of those claims."
  ],
  "next_action": "Publish corrected analytical v2 with identical extracted-verified runnable content; then deliver it."
}

2026-10-18T20:41:58.045332+00:00 G18 verified

{
  "evidence_paths": [
    "benchmark/delivery-receipt.json",
    "exports/solution_31_typed_collection_continuations_analysis_v2.zip",
    "exports/solution_31_typed_collection_continuations_analysis_v2.check.json"
  ],
  "findings": [
    "Corrected final v2 verified: all member hashes, every relative delivery-document link, complete S6 ledger/erratum and exact judged ZIP. Runnable hash matches corrected extracted1955-test/full-profile proof."
  ],
  "actual_exit_status": 0,
  "next_action": "Queue closed. Deliver only corrected v2 analytical archive and factual limitations; no further implementation work remains in the authorized queue."
}
