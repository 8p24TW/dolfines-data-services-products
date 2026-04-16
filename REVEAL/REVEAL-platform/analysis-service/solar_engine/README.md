# solar_engine/

Copy or symlink the following files from the original `REPAT/SCADA PV Analysis/` project:

```
repat_solar_scada_analysis.py ← main analysis engine (3000+ lines, unchanged)
run_jinja_report.py          ← report orchestrator
equipment_kb.py              ← equipment knowledge base
fault_knowledge_base.json    ← 200+ inverter fault codes
report/                      ← entire report/ subdirectory (templates, chart_factory, etc.)
```

## Quick setup (Windows)

```powershell
$src = "C:\Users\RichardMUSI\OneDrive - Dolfines\Bureau\AI\dolfines-data-services-products\REVEAL\SCADA PV Analysis"
$dst = "C:\Users\RichardMUSI\OneDrive - Dolfines\Bureau\AI\dolfines-data-services-products\REVEAL\REVEAL-platform\analysis-service\solar_engine"

Copy-Item (Get-ChildItem -LiteralPath $src -Filter "*scada_analysis.py").FullName (Join-Path $dst "repat_solar_scada_analysis.py")
Copy-Item "$src\run_jinja_report.py" $dst
Copy-Item "$src\equipment_kb.py" $dst
Copy-Item "$src\fault_knowledge_base.json" $dst
Copy-Item "$src\report" $dst -Recurse
```

The Python engine files are **not modified** — the FastAPI service wraps them as-is.
