# Agentic System
TBC


__[PDF Report](./report/report.pdf)__

## How to run the project
- GitHub Link: https://github.com/umscai/zc06-agentic-ai-sys
- The project __tested__ with Python version `3.13.14`, and __recommended__ to use python version `3.13 or above`

1. __Clone__ the repo using the above link (if you have access), or unzip the provided compressed file.
2. __Install__ dependencies using `pip install -r requirements.txt`, or if using uv: `uv add -r requirements.txt`
3. __IMPORTANT-1__: run  `pip install -e .` or if using uv `uv pip install -e .`, to avoid path resolution especially for `.env` file
4. __IMPORTANT-2__: This project depends on the parameters in .env located on the project root folder
    - See instruction and required parameters in sample `.env` file: [sample.env](./sample.env)
5. __Run__: `uv run agentic_system.py --asset 3 --test 1 --sample 2` or `python agentic_system.py --asset 3 --test 1 --sample 2`
6. __Expected Results__:

![Sample-Run](./report/latex/img/sample-run.png)


7. __Script Help__: `uv run agentic_system.py -h` or `uv run agentic_system.py --help`
```console
max@m223:~/x/zc06-agentic-ai-sys$ uv run python agentic_system.py -h
usage: agentic_system.py [-h] [-v] [-f {jsonl,txt}] [-a {1,2,3}] [-t {1,2,3,4}] [-s SAMPLES]

Arg Parser

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose output (pretty-print logs to console)
  -f, --format {jsonl,txt}
                        The storage format for the logs
  -a, --asset {1,2,3}   asset-id/index to get normal operational parameters,...(default: 1)
  -t, --test {1,2,3,4}  Test-Case number (default: 1)
  -s, --samples SAMPLES
                        Number of telemetry samples to generate and inject to system(default: 1)
max@m223:~/x/zc06-agentic-ai-sys$
```
More details
- asset is the equipment id/index, currently 1,2,3
- test is the test-case number currently 1,2,3,4 (There are anomaly in case 1,2,3, but 4 is a place holder for extension, and currently is not anomaly)
- number of samples is number of samples to generate between start and end values in the test case
- test-case values (start and end, and the asset info) are saved in [test_case_and_asset_info.csv](./data/test_case_and_asset_info.csv)


## Folder and File Structure
Project folder and file structures are shown below, where `agentic_system.py` is main script, and all supporting functions collected `src`, and `out` folder will be generated with shown structures for 3 used databases and the log files while `data` folder is devoted to asset and test-case info, and `report` folder contains report related files, while pdf report will be in details, result are also collected in the a `test_result.ipynb` under `notebook` folder for quick review.

```console
├max@m223:~/x/tmp/zc06test$ tree -L 3
.
├── agentic_system.py
├── data
│   ├── test_case_and_asset_info_colored.xlsx
│   └── test_case_and_asset_info.csv
├── LICENSE
├── main.py
├── minimal_req.ini
├── notebook
│   └── test_result.ipynb
├── out
│   ├── db_checkpoint
│   │   └── checkpoint_db
│   ├── db_ltm
│   │   └── ltm.db
│   ├── db_telemetry
│   │   └── telemetry.db
│   └── logs
│       └── log.jsonl
├── README.md
├── report
│   ├── latex
│   │   └── img
│   ├── report.pdf
│   └── test_result.html
├── requirements.txt
├── sample.env
├── src
│   ├── agents
│   │   ├── agent_anomaly_detector.py
│   │   ├── agent_class0_shutdown.py
│   │   ├── agent_class1_control.py
│   │   ├── agent_class2_escalate.py
│   │   ├── agent_classifier.py
│   │   ├── agent_common.py
│   │   ├── agent_ltm_update.py
│   │   └── __init__.py
│   ├── config.py
│   ├── db_model
│   │   ├── ltm_model.py
│   │   └── telemetry_model.py
│   ├── orchestration
│   │   ├── assistant.py
│   │   ├── graph.py
│   │   └── __init__.py
│   ├── tools
│   │   ├── anomaly_detector_tool.py
│   │   ├── checkpoint_db_analytics.py
│   │   ├── __init__.py
│   │   ├── ltm_db_tools.py
│   │   ├── severity_bands_tools.py
│   │   └── telemetry_db_tools.py
│   └── utils.py
└── use_ltm.sh
```

# Normal and Anomaly Region
![Severity-Bands](./report/latex/img/severity_bands.drawio.png)

# Workflow Graph
![Graph](./report/latex/img/workflow-details.drawio.png)


# Sample Results CLASS_0
![CLASS_0](./report/latex/img/a1t3.png)

![CLASS_0a](./report/latex/img/a1t3s2.png)


# Sample Results CLASS_1
![CLASS_1](./report/latex/img/a3t2.png)

![CLASS_1a](./report/latex/img/a3t2s2.png)


# Sample Results CLASS_2
![CLASS_2](./report/latex/img/a2t2.png)

![CLASS_2a](./report/latex/img/a2t2s2.png)


# Analytics
![Token-Usage](./report/latex/img/token_usage.png)

![Tool-Usage](./report/latex/img/tool_usage.png)

![Function-Usage](./report/latex/img/func_usage.png)





