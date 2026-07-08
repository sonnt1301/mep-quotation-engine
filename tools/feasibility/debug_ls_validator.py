import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.feasibility.ls_profile.validator import is_valid_ls_code

def main():
    test_codes = ["LB63N", "1P+N", "1PN", "3P+N", "3PN", "BK05S-T3", "2P", "4P", "AUXILIARY"]
    for c in test_codes:
        print(f"Code: {c} -> Cleaned: {c.replace('+', '')} -> Is Valid: {is_valid_ls_code(c.replace('+', ''))}")

if __name__ == "__main__":
    main()
