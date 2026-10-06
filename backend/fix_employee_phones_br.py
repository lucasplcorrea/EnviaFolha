from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "scripts" / "maintenance" / "fix_employee_phones_br.py"
    runpy.run_path(str(target), run_name="__main__")